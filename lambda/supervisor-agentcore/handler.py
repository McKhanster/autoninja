"""
Supervisor Agent Lambda Function
Orchestrates 5 collaborator agents using direct Lambda invocation with AgentCore Memory rate limiting
"""
import json
import os
import time
import boto3
from typing import Dict, Any
from datetime import datetime
from botocore.config import Config

# Import shared utilities from Lambda Layer
from shared.persistence.dynamodb_client import DynamoDBClient
from shared.persistence.s3_client import S3Client
from shared.utils.logger import get_logger
from shared.utils.agentcore_rate_limiter import apply_rate_limiting

# Initialize clients with extended timeouts for Lambda invocations
config = Config(
    read_timeout=300,  # 5 minutes
    connect_timeout=60,  # 1 minute
    retries={'max_attempts': 3}
)

dynamodb_client = DynamoDBClient()
s3_client = S3Client()
logger = get_logger(__name__)
lambda_client = boto3.client('lambda', config=config)

# Agent Lambda function names
AGENT_LAMBDA_FUNCTIONS = {
    'requirements-analyst': os.environ.get('REQUIREMENTS_ANALYST_LAMBDA_NAME', 'autoninja-requirements-analyst-production'),
    'code-generator': os.environ.get('CODE_GENERATOR_LAMBDA_NAME', 'autoninja-code-generator-production'),
    'solution-architect': os.environ.get('SOLUTION_ARCHITECT_LAMBDA_NAME', 'autoninja-solution-architect-production'),
    'quality-validator': os.environ.get('QUALITY_VALIDATOR_LAMBDA_NAME', 'autoninja-quality-validator-production'),
    'deployment-manager': os.environ.get('DEPLOYMENT_MANAGER_LAMBDA_NAME', 'autoninja-deployment-manager-production')
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Supervisor agent.
    Routes requests to appropriate action handlers based on apiPath.
    
    Args:
        event: Bedrock Agent input event
        context: Lambda context
        
    Returns:
        Bedrock Agent response event
    """
    start_time = time.time()
    job_name = None
    timestamp = None
    
    try:
        # Parse Bedrock Agent event
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', 'POST')
        action_group = event.get('actionGroup', 'supervisor-orchestration')
        session_id = event.get('sessionId', 'unknown')
        
        # Extract parameters from request body
        request_body = event.get('requestBody', {})
        content = request_body.get('content', {})
        json_content = content.get('application/json', {})
        properties = json_content.get('properties', [])
        
        # Convert properties array to dict
        params = {prop['name']: prop['value'] for prop in properties}
        job_name = params.get('job_name')
        
        # Generate job_name if not provided or unknown
        if not job_name or job_name == 'unknown':
            user_request = params.get('user_request', '')
            job_name = generate_job_name(user_request) if user_request else f"job-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Set logger context
        logger.set_context(
            job_name=job_name,
            agent_name='supervisor',
            action_name=api_path
        )
        
        # Apply rate limiting before processing
        apply_rate_limiting('supervisor')
        
        # Add job_name to params for downstream handlers
        params['job_name'] = job_name
        
        # Log raw input to DynamoDB immediately
        raw_request = json.dumps(event, default=str)
        logger.info(f"RAW REQUEST for {job_name}: {raw_request}")
        
        # logger.info(f"Processing request for apiPath: {api_path}")
        # logger.info(f"Parameters: {params}")
        
        # Route to appropriate action handler
        if api_path == '/orchestrate':
            result = handle_orchestrate(event, params, session_id, start_time)
        else:
            raise ValueError(f"Unknown apiPath: {api_path}")
        
        # Format successful response
        response = {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': http_method,
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result)
                    }
                }
            }
        }
        
        # Log raw output
        raw_response = json.dumps(result, default=str)
        logger.info(f"RAW RESPONSE for {job_name}: {raw_response}")
        
        # logger.info(f"Request completed successfully in {time.time() - start_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", error=str(e))
        
        # Log error to DynamoDB if we have job_name and timestamp
        if job_name and timestamp:
            try:
                dynamodb_client.log_error_to_dynamodb(
                    job_name=job_name,
                    timestamp=timestamp,
                    error_message=str(e),
                    duration_seconds=time.time() - start_time
                )
            except Exception as log_error:
                logger.error(f"Failed to log error to DynamoDB: {str(log_error)}")
        
        # Return error response
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'supervisor-orchestration'),
                'apiPath': event.get('apiPath', '/'),
                'httpMethod': event.get('httpMethod', 'POST'),
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': str(e),
                            'status': 'error'
                        })
                    }
                }
            }
        }


def generate_requirements_as_supervisor(job_name: str, user_request: str) -> Dict[str, Any]:
    """
    Supervisor generates requirements directly (absorbing RA role).
    Uses Bedrock with comprehensive RA prompt to analyze user request.
    
    Args:
        job_name: Unique job identifier
        user_request: User's natural language request
        
    Returns:
        Dict with structured requirements for all agents
    """
    from shared.utils.supervisor_parser import extract_json_from_supervisor_response, split_requirements_for_agents
    
    start_time = time.time()
    
    logger.info(f"=== Supervisor Requirements Generation ===")
    logger.info(f"Analyzing user request: {user_request}")
    
    # Apply rate limiting
    apply_rate_limiting('supervisor-requirements')
    
    try:
        # TODO: Replace with actual Bedrock call using RA prompt from S3
        # For now, simulate supervisor response with embedded JSON
        
        # Parse the supervisor response to extract JSON
        
        
        logger.info("✓ Requirements generated and parsed by Supervisor")
        logger.info(f"Generated requirements for {len(agent_requirements)} agents")
        
        # Return the complete requirements JSON (not split)
        return requirements_json
        
    except Exception as e:
        logger.error(f"Supervisor requirements generation failed: {str(e)}")
        raise ValueError(f"Requirements generation failed: {str(e)}")


def orchestrate_solution_architect(job_name: str, requirements: Dict[str, Any], max_retries: int = 1) -> Dict[str, Any]:
    """Orchestrate Solution Architect (quality validation disabled, no retries)"""
    from collaborators import solution_architect
    
    for attempt in range(max_retries):
        try:
            logger.info(f"=== Solution Architect (Attempt {attempt + 1}/{max_retries}) ===")
            
            # Call solution architect module directly
            session_id = f"{job_name}-solution-architect"
            result = solution_architect.design(
                job_name, 
                requirements,
                session_id
            )
            
            architecture = result.get('architecture', {})
            
            # Skip quality validation - return architecture directly
            logger.info("✓ Architecture completed (quality validation skipped)")
            return architecture
                    
        except Exception as e:
            logger.error(f"Solution Architect attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                continue
            else:
                raise ValueError(f"Architecture design failed after {max_retries} attempts: {str(e)}")


def orchestrate_code_generator(job_name: str, requirements: Dict[str, Any], max_retries: int = 1) -> Dict[str, Any]:
    """Orchestrate Code Generator (quality validation disabled, no retries)"""
    from collaborators import code_generator
    
    for attempt in range(max_retries):
        try:
            logger.info(f"=== Code Generator (Attempt {attempt + 1}/{max_retries}) ===")
            
            # Call code generator module directly
            session_id = f"{job_name}-code-generator"
            result = code_generator.generate(
                job_name,
                requirements,
                session_id
            )
            
            code = result.get('code', {})
            
            logger.info("✓ Code completed (quality validation skipped)")
            return code
                    
        except Exception as e:
            logger.error(f"Code Generator attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                continue
            else:
                raise ValueError(f"Code generation failed after {max_retries} attempts: {str(e)}")


def orchestrate_deployment_manager(job_name: str, dm_requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrate Deployment Manager - single deploy action"""
    from collaborators import deployment_manager
    
    try:
        # logger.info("=== Deployment Manager ===")
        
        # Rate limit before DM call
        apply_rate_limiting('code-to-deployment')
        
        # Call deployment manager module directly
        session_id = f"{job_name}-deployment-manager"
        result = deployment_manager.deploy(job_name, dm_requirements, session_id)
        
        logger.info(f"Deployment completed: {result.get('stack_status')}")
        return result
        
    except Exception as e:
        logger.error(f"Deployment Manager failed: {str(e)}")
        raise ValueError(f"Deployment failed: {str(e)}")


def handle_orchestrate(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle orchestrate action.
    Orchestrates 5 agents using modular functions with proper error handling.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (user_request)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with final orchestration results
    """
    from shared.utils.supervisor_parser import extract_json_from_supervisor_response, split_requirements_for_agents

    user_request = params.get('user_request')
    job_name = params.get('job_name')
    
    if not user_request:
        raise ValueError("Missing required parameter: user_request")
    requirements_json = extract_json_from_supervisor_response(supervisor_response)
        
        # Split requirements for different agents
    agent_requirements = split_requirements_for_agents(requirements_json)
    # Log input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='supervisor',
        action_name='orchestrate',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # logger.info(f"Starting orchestration with quality gates for job: {job_name}")
        logger.info(f"User request: {user_request}")
        
        
        # The Bedrock Agent will provide JSON output directly in the event
        logger.info("Requirements parsed from Bedrock Agent event")
        
        # Step 2: Solution Architect
        sa_requirements = agent_requirements.get('solution_architect_requirements', {})
        architecture = orchestrate_solution_architect(job_name, sa_requirements)
        logger.info("Solution Architect phase completed")
        
        # Step 3: Code Generator  
        cg_requirements = agent_requirements.get('code_generator_requirements', {})
        code = orchestrate_code_generator(job_name, cg_requirements)
        logger.info("Code Generator phase completed")
        
        # Step 4: Deploy
        dm_requirements = agent_requirements.get('deployment_manager_requirements', {})
        deployment = orchestrate_deployment_manager(job_name, dm_requirements)
        # logger.info("Deployment completed successfully")
        
        final_result = {
            "job_name": job_name,
            "status": "deployed",
            "requirements": req_data,
            "architecture": architecture,
            "code": code,
            "deployment": deployment
        }
        
        # Log final output to DynamoDB
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='orchestration',
            agent_name='supervisor',
            filename='final_orchestration_result.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(final_result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save final result to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='orchestration',
            agent_name='supervisor',
            artifact=final_result,
            filename='final_orchestration_result.json',
            content_type='application/json'
        )
        
        logger.info(f"Orchestration completed for job {job_name} in {duration:.2f}s")
        
        return final_result
        
    except Exception as e:
        # Log error to DynamoDB
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )
        raise


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
    keywords = ['friend', 'customer', 'support', 'chat', 'assistant', 'agent', 'service', 'help']
    
    for word in words:
        if word in keywords:
            return word
    
    # Fallback to first meaningful word
    for word in words:
        if len(word) > 3 and word.isalpha():
            return word[:10]  # Limit length
    
    return 'agent'  # default


def invoke_agent_lambda(agent_name: str, api_path: str, job_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke an agent Lambda function directly with proper event structure.
    
    Args:
        agent_name: Name of the agent (e.g., 'requirements-analyst')
        api_path: API path for the action (e.g., '/extract-requirements')
        job_name: Job identifier
        params: Parameters to pass to the agent
        
    Returns:
        Dict with agent response
    """
    function_name = AGENT_LAMBDA_FUNCTIONS.get(agent_name)
    if not function_name:
        raise ValueError(f"Unknown agent: {agent_name}")
    
    # Create proper Bedrock Agent event structure
    event = create_agent_event(api_path, job_name, params)
    
    # logger.info(f"Invoking {agent_name} Lambda: {function_name}")
    # logger.info(f"API Path: {api_path}")
    # logger.info(f"Parameters: {list(params.keys())}")
    
    try:
        invoke_start = time.time()
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        invoke_time = time.time() - invoke_start
        
        # Parse Lambda response
        response_payload = json.loads(response['Payload'].read())
        status_code = response.get('StatusCode', 0)
        
        logger.info(f"{agent_name} Lambda invocation completed in {invoke_time:.2f}s (status: {status_code})")
        
        if status_code == 200:
            # Extract result from Lambda response
            if 'response' in response_payload and 'responseBody' in response_payload['response']:
                body = response_payload['response']['responseBody']['application/json']['body']
                result = json.loads(body)
                logger.info(f"Successfully parsed {agent_name} response")
                return result
            else:
                # logger.warning(f"Unexpected Lambda response format from {agent_name}")
                logger.info(f"Response keys: {list(response_payload.keys())}")
                return {"response": str(response_payload), "status": "success", "agent_name": agent_name}
        else:
            error_msg = f"Lambda invocation failed with status {status_code}"
            logger.error(f"{agent_name}: {error_msg}")
            # logger.error(f"Response: {response_payload}")
            raise Exception(f"{error_msg}: {response_payload}")
            
    except Exception as e:
        logger.error(f"Failed to invoke {agent_name} Lambda: {str(e)}")
        raise e


def create_agent_event(api_path: str, job_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a proper Bedrock Agent event structure for Lambda invocation.
    
    Args:
        api_path: API path for the action
        job_name: Job identifier
        params: Parameters to include
        
    Returns:
        Dict with proper Bedrock Agent event structure
    """
    # Add job_name to parameters
    all_params = {'job_name': job_name}
    all_params.update(params)
    
    # Convert to Bedrock Agent event format
    properties = [
        {'name': key, 'value': value}
        for key, value in all_params.items()
    ]
    
    event = {
        'apiPath': api_path,
        'httpMethod': 'POST',
        'sessionId': f"{job_name}-{api_path.replace('/', '').replace('-', '')}",
        'requestBody': {
            'content': {
                'application/json': {
                    'properties': properties
                }
            }
        }
    }
    
    return event