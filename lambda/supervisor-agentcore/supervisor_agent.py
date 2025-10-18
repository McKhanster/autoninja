"""
AutoNinja Supervisor Agent for Amazon Bedrock AgentCore Runtime

This supervisor agent orchestrates 5 collaborator Bedrock Agents in a sequential
workflow to transform natural language requests into fully deployed AI agents.

Architecture:
- Supervisor: Deployed to AgentCore Runtime (this file)
- Collaborators: 5 Regular Bedrock Agents with Lambda action groups
- Orchestration: Sequential logical workflow (Requirements → Code → Architecture → Validation → Deployment)
"""

from bedrock_agentcore import BedrockAgentCoreApp
import boto3
import json
import time
import re
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize AgentCore app
app = BedrockAgentCoreApp()

# Initialize AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-2'))
dynamodb = boto3.client('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-2'))
s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-east-2'))

# Collaborator agent configuration (from environment variables set by CloudFormation outputs)
COLLABORATORS = {
    'requirements_analyst': {
        'agent_id': os.environ.get('REQUIREMENTS_ANALYST_AGENT_ID', ''),
        'alias_id': os.environ.get('REQUIREMENTS_ANALYST_ALIAS_ID', ''),
        'name': 'Requirements Analyst'
    },
    'code_generator': {
        'agent_id': os.environ.get('CODE_GENERATOR_AGENT_ID', ''),
        'alias_id': os.environ.get('CODE_GENERATOR_ALIAS_ID', ''),
        'name': 'Code Generator'
    },
    'solution_architect': {
        'agent_id': os.environ.get('SOLUTION_ARCHITECT_AGENT_ID', ''),
        'alias_id': os.environ.get('SOLUTION_ARCHITECT_ALIAS_ID', ''),
        'name': 'Solution Architect'
    },
    'quality_validator': {
        'agent_id': os.environ.get('QUALITY_VALIDATOR_AGENT_ID', ''),
        'alias_id': os.environ.get('QUALITY_VALIDATOR_ALIAS_ID', ''),
        'name': 'Quality Validator'
    },
    'deployment_manager': {
        'agent_id': os.environ.get('DEPLOYMENT_MANAGER_AGENT_ID', ''),
        'alias_id': os.environ.get('DEPLOYMENT_MANAGER_ALIAS_ID', ''),
        'name': 'Deployment Manager'
    }
}

# Mock mode for local testing
MOCK_MODE = os.environ.get('MOCK_MODE', 'false').lower() == 'true'


@app.entrypoint
def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervisor agent entrypoint for orchestrating collaborator agents.
    
    This function implements the complete AutoNinja workflow:
    1. Generate unique job_name
    2. Invoke Requirements Analyst
    3. Invoke Code Generator with requirements
    4. Invoke Solution Architect with requirements + code
    5. Invoke Quality Validator with all artifacts
    6. Check validation gate (is_valid == True?)
    7. If valid, invoke Deployment Manager
    8. Return final deployed agent ARN
    
    Args:
        payload: Dict with 'prompt' key containing user request
        
    Returns:
        Dict with final deployed agent ARN and results
    """
    job_name = None
    
    try:
        # Extract user request
        user_request = payload.get("prompt", "")
        if not user_request:
            return {
                "error": "No prompt provided in payload",
                "status": "error",
                "help": "Payload must contain 'prompt' key with user request"
            }
        
        # Generate unique job_name
        job_name = generate_job_name(user_request)
        print(f"[SUPERVISOR] Starting job: {job_name}")
        print(f"[SUPERVISOR] User request: {user_request}")
        
        # Initialize results dictionary
        results = {
            "job_name": job_name,
            "user_request": user_request,
            "timestamp": datetime.utcnow().isoformat(),
            "collaborators": {}
        }
        
        # STEP 1: Requirements Analyst
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] STEP 1: Requirements Analyst")
        print(f"[SUPERVISOR] ========================================")
        requirements = invoke_collaborator(
            collaborator='requirements_analyst',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "user_request": user_request,
                "action": "extract_requirements"
            }
        )
        results['collaborators']['requirements_analyst'] = requirements
        print(f"[SUPERVISOR] Requirements Analyst complete ✓")
        
        # STEP 2: Code Generator
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] STEP 2: Code Generator")
        print(f"[SUPERVISOR] ========================================")
        code = invoke_collaborator(
            collaborator='code_generator',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "requirements": json.dumps(requirements) if isinstance(requirements, dict) else requirements,
                "action": "generate_lambda_code"  # Start with lambda code
            }
        )
        results['collaborators']['code_generator'] = code
        print(f"[SUPERVISOR] Code Generator complete ✓")
        
        # STEP 3: Solution Architect
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] STEP 3: Solution Architect")
        print(f"[SUPERVISOR] ========================================")
        
        # Get S3 bucket name
        s3_bucket = os.environ.get('S3_BUCKET_NAME', f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID', 'unknown')}-production")
        
        architecture = invoke_collaborator(
            collaborator='solution_architect',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "requirements": json.dumps(requirements) if isinstance(requirements, dict) else requirements,
                "code_file_references": json.dumps({
                    "lambda_code": f"s3://{s3_bucket}/{job_name}/code/lambda_handler.py",
                    "agent_config": f"s3://{s3_bucket}/{job_name}/code/agent_config.json",
                    "openapi_schemas": f"s3://{s3_bucket}/{job_name}/code/openapi_schema.yaml"
                }),
                "action": "design_architecture"
            }
        )
        results['collaborators']['solution_architect'] = architecture
        print(f"[SUPERVISOR] Solution Architect complete ✓")
        
        # STEP 4: Quality Validator
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] STEP 4: Quality Validator")
        print(f"[SUPERVISOR] ========================================")
        validation = invoke_collaborator(
            collaborator='quality_validator',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "requirements": json.dumps(requirements) if isinstance(requirements, dict) else requirements,
                "code": json.dumps(code) if isinstance(code, dict) else code,
                "architecture": json.dumps(architecture) if isinstance(architecture, dict) else architecture,
                "action": "validate_code"
            }
        )
        results['collaborators']['quality_validator'] = validation
        print(f"[SUPERVISOR] Quality Validator complete ✓")
        
        # STEP 5: Check validation gate
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] VALIDATION GATE")
        print(f"[SUPERVISOR] ========================================")
        
        # Extract is_valid from validation response
        is_valid = False
        if isinstance(validation, dict):
            is_valid = validation.get('is_valid', False)
        elif isinstance(validation, str):
            try:
                validation_dict = json.loads(validation)
                is_valid = validation_dict.get('is_valid', False)
            except:
                pass
        
        if not is_valid:
            print(f"[SUPERVISOR] Validation FAILED ✗")
            print(f"[SUPERVISOR] Stopping workflow - deployment not allowed")
            return {
                "job_name": job_name,
                "status": "validation_failed",
                "message": "Quality validation failed. Deployment blocked.",
                "validation_issues": validation.get('issues', []) if isinstance(validation, dict) else [],
                "quality_score": validation.get('quality_score', 0) if isinstance(validation, dict) else 0,
                "results": results
            }
        
        print(f"[SUPERVISOR] Validation PASSED ✓")
        print(f"[SUPERVISOR] Proceeding to deployment...")
        
        # STEP 6: Deployment Manager (only if validation passed)
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] STEP 5: Deployment Manager")
        print(f"[SUPERVISOR] ========================================")
        deployment = invoke_collaborator(
            collaborator='deployment_manager',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "requirements": json.dumps(requirements) if isinstance(requirements, dict) else requirements,
                "code": json.dumps(code) if isinstance(code, dict) else code,
                "architecture": json.dumps(architecture) if isinstance(architecture, dict) else architecture,
                "validation_status": "passed",
                "action": "generate_cloudformation"
            }
        )
        results['collaborators']['deployment_manager'] = deployment
        print(f"[SUPERVISOR] Deployment Manager complete ✓")
        
        # Extract agent ARN from deployment response
        agent_arn = None
        if isinstance(deployment, dict):
            agent_arn = deployment.get('agent_arn')
        elif isinstance(deployment, str):
            try:
                deployment_dict = json.loads(deployment)
                agent_arn = deployment_dict.get('agent_arn')
            except:
                pass
        
        # Return final result
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] WORKFLOW COMPLETE ✓")
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] Job: {job_name}")
        print(f"[SUPERVISOR] Agent ARN: {agent_arn or 'Not available'}")
        
        return {
            "job_name": job_name,
            "status": "deployed",
            "agent_arn": agent_arn,
            "agent_alias_id": deployment.get('alias_id') if isinstance(deployment, dict) else None,
            "endpoints": deployment.get('endpoints', {}) if isinstance(deployment, dict) else {},
            "message": "Agent successfully generated and deployed!",
            "results": results
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] ERROR ✗")
        print(f"[SUPERVISOR] ========================================")
        print(f"[SUPERVISOR] {error_msg}")
        
        return {
            "error": error_msg,
            "status": "error",
            "job_name": job_name if job_name else "unknown",
            "message": "Workflow failed. Check CloudWatch logs for details."
        }


def generate_job_name(user_request: str) -> str:
    """
    Generate unique job_name from user request.
    
    Format: job-{keyword}-{YYYYMMDD-HHMMSS}
    
    Algorithm:
    1. Extract words from user request
    2. Filter out stop words
    3. Take first meaningful word (length > 2)
    4. Append UTC timestamp
    5. Prefix with "job-"
    
    Args:
        user_request: User's natural language request
        
    Returns:
        Unique job name string
        
    Examples:
        "I would like a friend agent" → "job-friend-20250115-143022"
        "Create a customer support agent" → "job-customer-20250115-143045"
        "Build an invoice processing agent" → "job-invoice-20250115-143102"
    """
    # Extract words from request (alphanumeric only)
    words = re.findall(r'\b\w+\b', user_request.lower())
    
    # Filter out common stop words
    stop_words = {'i', 'want', 'need', 'would', 'like', 'a', 'an', 'the', 'to', 'for', 'create', 'build', 'make'}
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Take first meaningful word, or default to 'agent'
    keyword = keywords[0] if keywords else 'agent'
    
    # Generate timestamp in UTC
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    
    return f"job-{keyword}-{timestamp}"


def invoke_collaborator(
    collaborator: str,
    session_id: str,
    input_data: Dict[str, Any],
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Invoke a collaborator Bedrock Agent via InvokeAgent API.
    
    This function:
    1. Formats input data as JSON text
    2. Calls bedrock-agent-runtime InvokeAgent API
    3. Parses streaming response
    4. Retries on failure with exponential backoff
    
    Args:
        collaborator: Name of collaborator ('requirements_analyst', 'code_generator', etc.)
        session_id: Session ID (use job_name for consistency)
        input_data: Input data to pass to collaborator
        max_retries: Maximum number of retry attempts
        
    Returns:
        Parsed response from collaborator
        
    Raises:
        Exception: If invocation fails after all retries
    """
    # Check for mock mode (local testing)
    if MOCK_MODE:
        print(f"[SUPERVISOR] MOCK MODE: Returning mock response for {collaborator}")
        return get_mock_response(collaborator, input_data)
    
    # Get collaborator configuration
    config = COLLABORATORS.get(collaborator)
    if not config:
        raise ValueError(f"Unknown collaborator: {collaborator}")
    
    agent_id = config['agent_id']
    alias_id = config['alias_id']
    agent_name = config['name']
    
    # Validate configuration
    if not agent_id or not alias_id:
        raise ValueError(f"Missing configuration for {agent_name}. Check environment variables.")
    
    # Format input as text (Bedrock Agents expect text input)
    input_text = json.dumps(input_data)
    
    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        try:
            print(f"[SUPERVISOR] Invoking {agent_name} (attempt {attempt + 1}/{max_retries})...")
            print(f"[SUPERVISOR] Agent ID: {agent_id}, Alias ID: {alias_id}")
            
            # Invoke the collaborator agent
            response = bedrock_agent_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=True  # Enable tracing for debugging
            )
            
            # Parse streaming response
            result = parse_streaming_response(response)
            
            print(f"[SUPERVISOR] {agent_name} invocation successful")
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[SUPERVISOR] {agent_name} invocation failed (attempt {attempt + 1}): {error_msg}")
            
            if attempt < max_retries - 1:
                # Exponential backoff: 2^attempt seconds
                wait_time = 2 ** attempt
                print(f"[SUPERVISOR] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # All retries exhausted
                raise Exception(f"Failed to invoke {agent_name} after {max_retries} attempts: {error_msg}")


def parse_streaming_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse streaming response from InvokeAgent API.
    
    The InvokeAgent API returns a streaming response with chunks.
    This function collects all chunks and attempts to parse as JSON.
    
    Args:
        response: Response from bedrock_agent_runtime.invoke_agent()
        
    Returns:
        Parsed result as dictionary (or dict with 'result' key if not JSON)
    """
    result_text = ""
    
    # Process streaming response
    for event in response.get('completion', []):
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                result_text += chunk['bytes'].decode('utf-8')
    
    # Try to parse as JSON
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        # If not JSON, return as text in a dict
        return {"result": result_text}


def get_mock_response(collaborator: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get mock response for local testing.
    
    This function returns realistic mock responses for each collaborator
    to enable local testing without deploying to AWS.
    
    Args:
        collaborator: Name of collaborator
        input_data: Input data (for context)
        
    Returns:
        Mock response dictionary
    """
    job_name = input_data.get('job_name', 'job-test-20250115-000000')
    
    mock_responses = {
        'requirements_analyst': {
            "job_name": job_name,
            "requirements": {
                "agent_purpose": "Friendly conversational agent",
                "capabilities": ["casual_conversation", "emotional_support"],
                "system_prompts": "You are a friendly agent that provides emotional support...",
                "lambda_requirements": {"runtime": "python3.12", "memory": 512},
                "architecture_requirements": {"services": ["Bedrock Agent", "Lambda", "CloudWatch"]}
            },
            "status": "success"
        },
        'code_generator': {
            "job_name": job_name,
            "lambda_code": "def lambda_handler(event, context): return {'statusCode': 200}",
            "agent_config": {"agent_name": "friend-agent", "foundation_model": "claude-sonnet-4"},
            "openapi_schema": "openapi: 3.0.0\ninfo:\n  title: Friend Agent API",
            "status": "success"
        },
        'solution_architect': {
            "job_name": job_name,
            "architecture": {
                "services": ["Bedrock Agent", "Lambda", "CloudWatch", "IAM"],
                "iac_template": "AWSTemplateFormatVersion: '2010-09-09'..."
            },
            "status": "success"
        },
        'quality_validator': {
            "job_name": job_name,
            "is_valid": True,
            "quality_score": 85,
            "issues": [],
            "security_findings": [],
            "status": "success"
        },
        'deployment_manager': {
            "job_name": job_name,
            "agent_arn": f"arn:aws:bedrock:us-east-2:123456789012:agent/mock-agent-{job_name}",
            "alias_id": "MOCK123",
            "endpoints": {"invoke_url": "https://bedrock.us-east-2.amazonaws.com/..."},
            "status": "success"
        }
    }
    
    return mock_responses.get(collaborator, {"error": f"No mock response for {collaborator}"})


if __name__ == "__main__":
    # For local testing
    print("[SUPERVISOR] Starting in local mode...")
    print("[SUPERVISOR] Set MOCK_MODE=true to use mock collaborators")
    app.run()
