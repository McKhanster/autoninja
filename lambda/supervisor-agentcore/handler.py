"""
Enhanced Bedrock Agent supervisor with AgentCore Memory rate limiting.
Orchestrates 5 collaborator agents sequentially with global rate limiting.
"""
import boto3
import json
import time
import random
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
bedrock_agentcore_data = boto3.client('bedrock-agentcore')
bedrock_agentcore_control = boto3.client('bedrock-agentcore-control')
s3 = boto3.client('s3')

# Configuration
# For AgentCore Runtime, memory ID is available through environment or can be retrieved from AgentCore
MEMORY_ID = os.environ.get('MEMORY_ID') or os.environ.get('BEDROCK_AGENTCORE_MEMORY_ID') or "autoninja_supervisor_mem-Fj5viaEP75"
MIN_INTERVAL_SECONDS = 30  # 30 seconds minimum between ANY model invocations
MAX_RETRIES = 5
BASE_DELAY = 1.0
RATE_LIMIT_ACTOR_ID = "rate-limiter"
RATE_LIMIT_SESSION_ID = "global-model-invocations"

def lambda_handler(event, context):
    """
    Enhanced Bedrock Agent supervisor with AgentCore Memory rate limiting.
    
    Args:
        event: Dict with 'inputText' key containing user request
        
    Returns:
        Dict with final deployed agent ARN and results
    """
    try:
        # Extract user request from Bedrock Agent event
        user_request = event.get("inputText", "")
        session_id = event.get("sessionId", f"session-{int(time.time())}")
        
        logger.info(f"Starting orchestration for request: {user_request[:100]}...")
        
        # Generate unique job_name
        job_name = generate_job_name(user_request)
        
        # Log start of orchestration
        log_to_cloudwatch(f"Starting orchestration for job: {job_name}")
        
        # Sequential orchestration with rate limiting
        results = {}
        
        # 1. Requirements Analyst
        requirements = invoke_collaborator_with_rate_limiting(
            agent_id=get_agent_id("requirements-analyst"),
            alias_id=get_alias_id("requirements-analyst"),
            session_id=job_name,
            input_text=f"job_name: {job_name}\nrequest: {user_request}",
            agent_name="requirements-analyst"
        )
        results['requirements'] = requirements
        
        # 2. Code Generator
        code = invoke_collaborator_with_rate_limiting(
            agent_id=get_agent_id("code-generator"),
            alias_id=get_alias_id("code-generator"),
            session_id=job_name,
            input_text=f"job_name: {job_name}\nrequirements: {json.dumps(requirements)}",
            agent_name="code-generator"
        )
        results['code'] = code
        
        # 3. Solution Architect
        architecture = invoke_collaborator_with_rate_limiting(
            agent_id=get_agent_id("solution-architect"),
            alias_id=get_alias_id("solution-architect"),
            session_id=job_name,
            input_text=f"job_name: {job_name}\nrequirements: {json.dumps(requirements)}\ncode: {json.dumps(code)}",
            agent_name="solution-architect"
        )
        results['architecture'] = architecture
        
        # 4. Quality Validator
        validation = invoke_collaborator_with_rate_limiting(
            agent_id=get_agent_id("quality-validator"),
            alias_id=get_alias_id("quality-validator"),
            session_id=job_name,
            input_text=f"job_name: {job_name}\ncode: {json.dumps(code)}\narchitecture: {json.dumps(architecture)}",
            agent_name="quality-validator"
        )
        results['validation'] = validation
        
        # 5. Deployment Manager (only if validation passes)
        if validation.get('is_valid', False):
            deployment = invoke_collaborator_with_rate_limiting(
                agent_id=get_agent_id("deployment-manager"),
                alias_id=get_alias_id("deployment-manager"),
                session_id=job_name,
                input_text=f"job_name: {job_name}\nall_artifacts: {json.dumps(results)}",
                agent_name="deployment-manager"
            )
            results['deployment'] = deployment
            
            return {
                "job_name": job_name,
                "agent_arn": deployment.get('agent_arn'),
                "status": "deployed",
                "results": results
            }
        else:
            return {
                "job_name": job_name,
                "status": "validation_failed",
                "validation_issues": validation.get('issues', []),
                "results": results
            }
            
    except Exception as e:
        log_to_cloudwatch(f"Error in supervisor orchestration: {str(e)}")
        logger.error(f"Orchestration error: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

def invoke_collaborator_with_rate_limiting(
    agent_id: str, 
    alias_id: str, 
    session_id: str, 
    input_text: str,
    agent_name: str
) -> Dict[str, Any]:
    """
    Invoke a collaborator agent with rate limiting and retry logic.
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Check and enforce GLOBAL rate limiting (applies to ALL agents including supervisor)
            wait_time = check_and_enforce_global_rate_limit()
            if wait_time > 0:
                log_to_cloudwatch(f"Global rate limiting: waiting {wait_time}s before invoking {agent_name}")
                time.sleep(wait_time)
            
            # Update global rate limiter timestamp BEFORE making the call
            update_global_rate_limiter_timestamp(agent_name)
            
            # Invoke the collaborator
            response = bedrock_agent_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=True
            )
            
            # Parse streaming response
            result = ""
            for event in response.get('completion', []):
                if 'chunk' in event:
                    result += event['chunk']['bytes'].decode('utf-8')
            
            log_to_cloudwatch(f"Successfully invoked {agent_name} on attempt {attempt + 1}")
            return json.loads(result) if result else {}
            
        except Exception as e:
            if "throttlingException" in str(e) and attempt < MAX_RETRIES - 1:
                # Exponential backoff with jitter
                delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                log_to_cloudwatch(f"Throttling detected for {agent_name}, retrying in {delay:.2f}s (attempt {attempt + 1})")
                time.sleep(delay)
                continue
            else:
                log_to_cloudwatch(f"Failed to invoke {agent_name} after {attempt + 1} attempts: {str(e)}")
                raise e
    
    raise Exception(f"Failed to invoke {agent_name} after {MAX_RETRIES} attempts")

def check_and_enforce_global_rate_limit() -> float:
    """
    Check global rate limiter using AgentCore Memory for ANY model invocation.
    This applies to ALL agents including the supervisor.
    
    Returns:
        float: Seconds to wait (0 if no wait needed)
    """
    try:
        # Retrieve global rate limiting data from AgentCore Memory using correct API
        response = bedrock_agentcore_data.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace="/rate-limiting/global",
            searchCriteria={
                'searchQuery': 'last model invocation timestamp',
                'topK': 1
            }
        )
        
        if response.get('memoryRecords'):
            memory_record = response['memoryRecords'][0]
            # Extract content from conversational format
            content_text = memory_record['content']['conversational']['content']['text']
            content = json.loads(content_text)
            last_invocation = datetime.fromisoformat(content['last_invocation'])
            elapsed = (datetime.now() - last_invocation).total_seconds()
            
            if elapsed < MIN_INTERVAL_SECONDS:
                wait_time = MIN_INTERVAL_SECONDS - elapsed
                log_to_cloudwatch(f"Global rate limit: waiting {wait_time:.2f}s since last model invocation")
                return wait_time
        
        return 0.0
        
    except Exception as e:
        log_to_cloudwatch(f"Error checking global rate limit: {str(e)}")
        return 0.0

def update_global_rate_limiter_timestamp(agent_name: str):
    """
    Update the global rate limiter timestamp for ANY model invocation using AgentCore Memory.
    This records that ANY agent (including supervisor) made a model call.
    """
    try:
        # Create event in AgentCore Memory to track rate limiting using correct format
        event_payload = [
            {
                'conversational': {
                    'content': {
                        'text': json.dumps({
                            "last_invocation": datetime.now().isoformat(),
                            "last_agent": agent_name,
                            "invocation_count": 1,
                            "created_at": datetime.now().isoformat()
                        })
                    },
                    'role': 'ASSISTANT'
                }
            }
        ]
        
        # Store rate limiting event in AgentCore Memory
        bedrock_agentcore_data.create_event(
            memoryId=MEMORY_ID,
            actorId=RATE_LIMIT_ACTOR_ID,
            sessionId=RATE_LIMIT_SESSION_ID,
            eventTimestamp=datetime.now(),
            payload=event_payload
        )
        
        log_to_cloudwatch(f"Updated global rate limiter: {agent_name} made model invocation")
    except Exception as e:
        log_to_cloudwatch(f"Error updating global rate limiter for {agent_name}: {str(e)}")

def generate_job_name(user_request: str) -> str:
    """Generate unique job_name from user request"""
    # Extract keyword from request
    keyword = extract_keyword(user_request)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"job-{keyword}-{timestamp}"

def extract_keyword(request: str) -> str:
    """Extract a keyword from the user request"""
    # Simple keyword extraction
    words = request.lower().split()
    keywords = ['friend', 'customer', 'support', 'chat', 'assistant', 'agent']
    
    for word in words:
        if word in keywords:
            return word
    
    return 'agent'  # default

def get_agent_id(agent_name: str) -> str:
    """Get agent ID from environment or CloudFormation outputs"""
    # These would be set as environment variables during deployment
    agent_ids = {
        'requirements-analyst': os.environ.get('REQUIREMENTS_ANALYST_AGENT_ID'),
        'code-generator': os.environ.get('CODE_GENERATOR_AGENT_ID'),
        'solution-architect': os.environ.get('SOLUTION_ARCHITECT_AGENT_ID'),
        'quality-validator': os.environ.get('QUALITY_VALIDATOR_AGENT_ID'),
        'deployment-manager': os.environ.get('DEPLOYMENT_MANAGER_AGENT_ID')
    }
    return agent_ids.get(agent_name)

def get_alias_id(agent_name: str) -> str:
    """Get alias ID from environment or CloudFormation outputs"""
    # These would be set as environment variables during deployment
    alias_ids = {
        'requirements-analyst': os.environ.get('REQUIREMENTS_ANALYST_ALIAS_ID'),
        'code-generator': os.environ.get('CODE_GENERATOR_ALIAS_ID'),
        'solution-architect': os.environ.get('SOLUTION_ARCHITECT_ALIAS_ID'),
        'quality-validator': os.environ.get('QUALITY_VALIDATOR_ALIAS_ID'),
        'deployment-manager': os.environ.get('DEPLOYMENT_MANAGER_ALIAS_ID')
    }
    return alias_ids.get(agent_name)

def log_to_cloudwatch(message: str):
    """Log message to CloudWatch"""
    timestamp = datetime.now().isoformat()
    logger.info(f"[{timestamp}] {message}")
    print(f"[{timestamp}] {message}")