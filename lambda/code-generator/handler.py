"""
Code Generator Lambda Function
Generates Lambda code, agent configurations, and OpenAPI schemas
"""
import json
import os
import time
from typing import Dict, Any, List, Optional

# Import shared utilities from Lambda Layer
from shared.persistence.dynamodb_client import DynamoDBClient
from shared.persistence.s3_client import S3Client
from shared.utils.logger import get_logger
from shared.models.code_artifacts import CodeArtifacts


# Initialize clients
dynamodb_client = DynamoDBClient()
s3_client = S3Client()
logger = get_logger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Code Generator agent.
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
        action_group = event.get('actionGroup', 'code-generator-actions')
        session_id = event.get('sessionId', 'unknown')
        
        # Extract parameters from request body
        request_body = event.get('requestBody', {})
        content = request_body.get('content', {})
        json_content = content.get('application/json', {})
        properties = json_content.get('properties', [])
        
        # Convert properties array to dict
        params = {prop['name']: prop['value'] for prop in properties}
        job_name = params.get('job_name', 'unknown')
        
        # Set logger context
        logger.set_context(
            job_name=job_name,
            agent_name='code-generator',
            action_name=api_path
        )
        
        logger.info(f"Processing request for apiPath: {api_path}")
        
        # Route to appropriate action handler
        if api_path == '/generate-lambda-code':
            result = handle_generate_lambda_code(event, params, session_id, start_time)
        elif api_path == '/generate-agent-config':
            result = handle_generate_agent_config(event, params, session_id, start_time)
        elif api_path == '/generate-openapi-schema':
            result = handle_generate_openapi_schema(event, params, session_id, start_time)
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
        
        logger.info(f"Request completed successfully in {time.time() - start_time:.2f}s")
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
                'actionGroup': event.get('actionGroup', 'code-generator-actions'),
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


def handle_generate_lambda_code(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle generate_lambda_code action.
    Generates Python Lambda function code with error handling.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, requirements, function_spec)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, lambda_code, requirements_txt, and status
    """
    job_name = params.get('job_name')
    requirements_str = params.get('requirements')
    function_spec_str = params.get('function_spec', '{}')
    
    if not job_name or not requirements_str:
        raise ValueError("Missing required parameters: job_name and requirements")
    
    # Parse requirements if it's a string
    if isinstance(requirements_str, str):
        try:
            requirements = json.loads(requirements_str)
        except json.JSONDecodeError:
            requirements = {}
    else:
        requirements = requirements_str or {}
    
    # Parse function_spec if it's a string
    if isinstance(function_spec_str, str):
        try:
            function_spec = json.loads(function_spec_str)
        except json.JSONDecodeError:
            function_spec = {}
    else:
        function_spec = function_spec_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='code-generator',
        action_name='generate_lambda_code',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Generate Lambda code based on requirements
        logger.info(f"Generating Lambda code for job: {job_name}")
        
        lambda_code = generate_lambda_handler_code(requirements, function_spec)
        requirements_txt = generate_requirements_txt(requirements)
        
        # Prepare response
        result = {
            "job_name": job_name,
            "lambda_code": lambda_code,
            "requirements_txt": requirements_txt,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            filename='lambda_code.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save generated code files to S3
        for filename, code_content in lambda_code.items():
            s3_client.save_converted_artifact(
                job_name=job_name,
                phase='code',
                agent_name='code-generator',
                artifact=code_content,
                filename=filename,
                content_type='text/plain'
            )
        
        # Save requirements.txt to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            artifact=requirements_txt,
            filename='requirements.txt',
            content_type='text/plain'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            response=result,
            filename='generate_lambda_code_raw_response.json'
        )
        
        logger.info(f"Lambda code generated successfully for job {job_name}")
        return result
        
    except Exception as e:
        # Log error to DynamoDB
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )
        raise


def generate_lambda_handler_code(requirements: Dict[str, Any], function_spec: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate Lambda handler code based on requirements.
    
    Returns:
        Dict mapping filename to code content
    """
    agent_purpose = requirements.get('agent_purpose', 'AI agent')
    capabilities = requirements.get('capabilities', [])
    lambda_reqs = requirements.get('lambda_requirements', {})
    actions = lambda_reqs.get('actions', [])
    
    # Generate main handler.py
    handler_code = f'''"""
Generated Lambda Function
Purpose: {agent_purpose}
"""
import json
import os
import time
from typing import Dict, Any, Optional

# Initialize logger
import logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for generated agent.
    
    Args:
        event: Bedrock Agent input event
        context: Lambda context
        
    Returns:
        Bedrock Agent response event
    """
    start_time = time.time()
    
    try:
        # Parse Bedrock Agent event
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', 'POST')
        action_group = event.get('actionGroup', 'generated-actions')
        session_id = event.get('sessionId', 'unknown')
        
        # Extract parameters from request body
        request_body = event.get('requestBody', {{}})
        content = request_body.get('content', {{}})
        json_content = content.get('application/json', {{}})
        properties = json_content.get('properties', [])
        
        # Convert properties array to dict
        params = {{prop['name']: prop['value'] for prop in properties}}
        
        logger.info(f"Processing request for apiPath: {{api_path}}")
        
        # Route to appropriate action handler
        result = handle_action(api_path, params, session_id)
        
        # Format successful response
        response = {{
            'messageVersion': '1.0',
            'response': {{
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': http_method,
                'httpStatusCode': 200,
                'responseBody': {{
                    'application/json': {{
                        'body': json.dumps(result)
                    }}
                }}
            }}
        }}
        
        logger.info(f"Request completed successfully in {{time.time() - start_time:.2f}}s")
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {{str(e)}}")
        
        # Return error response
        return {{
            'messageVersion': '1.0',
            'response': {{
                'actionGroup': event.get('actionGroup', 'generated-actions'),
                'apiPath': event.get('apiPath', '/'),
                'httpMethod': event.get('httpMethod', 'POST'),
                'httpStatusCode': 500,
                'responseBody': {{
                    'application/json': {{
                        'body': json.dumps({{
                            'error': str(e),
                            'status': 'error'
                        }})
                    }}
                }}
            }}
        }}


def handle_action(api_path: str, params: Dict[str, str], session_id: str) -> Dict[str, Any]:
    """
    Handle action based on API path.
    
    Args:
        api_path: The API path from the request
        params: Extracted parameters
        session_id: Bedrock session ID
        
    Returns:
        Dict with action results
    """
    # Implement action logic here
    user_input = params.get('user_input', '')
    
    # Process the request based on capabilities
    # Capabilities: {', '.join(capabilities)}
    
    result = {{
        'response': f"Processed request: {{user_input}}",
        'session_id': session_id,
        'status': 'success'
    }}
    
    return result
'''
    
    return {
        'handler.py': handler_code
    }


def generate_requirements_txt(requirements: Dict[str, Any]) -> str:
    """
    Generate requirements.txt for Lambda function.
    
    Returns:
        String content of requirements.txt
    """
    # Base dependencies
    dependencies = [
        'boto3>=1.28.0',
        'botocore>=1.31.0'
    ]
    
    # Add additional dependencies based on requirements
    integrations = requirements.get('integrations', [])
    
    if any('email' in integration.lower() for integration in integrations):
        dependencies.append('email-validator>=2.0.0')
    
    if any('api' in integration.lower() for integration in integrations):
        dependencies.append('requests>=2.31.0')
    
    return '\n'.join(dependencies)


def handle_generate_agent_config(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle generate_agent_config action.
    Generates Bedrock Agent configuration JSON.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, requirements)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, agent_config, and status
    """
    job_name = params.get('job_name')
    requirements_str = params.get('requirements')
    
    if not job_name or not requirements_str:
        raise ValueError("Missing required parameters: job_name and requirements")
    
    # Parse requirements if it's a string
    if isinstance(requirements_str, str):
        try:
            requirements = json.loads(requirements_str)
        except json.JSONDecodeError:
            requirements = {}
    else:
        requirements = requirements_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='code-generator',
        action_name='generate_agent_config',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Generate agent configuration
        logger.info(f"Generating agent configuration for job: {job_name}")
        
        agent_config = generate_bedrock_agent_config(requirements)
        
        # Prepare response
        result = {
            "job_name": job_name,
            "agent_config": agent_config,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            filename='agent_config.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save agent config to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            artifact=agent_config,
            filename='agent_config.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            response=result,
            filename='generate_agent_config_raw_response.json'
        )
        
        logger.info(f"Agent configuration generated successfully for job {job_name}")
        return result
        
    except Exception as e:
        # Log error to DynamoDB
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )
        raise


def generate_bedrock_agent_config(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate Bedrock Agent configuration based on requirements.
    
    Returns:
        Dict with agent configuration
    """
    agent_purpose = requirements.get('agent_purpose', 'AI agent')
    system_prompts = requirements.get('system_prompts', '')
    arch_reqs = requirements.get('architecture_requirements', {})
    bedrock_config = arch_reqs.get('bedrock', {})
    
    foundation_model = bedrock_config.get('foundation_model', 'anthropic.claude-sonnet-4-5-20250929-v1:0')
    
    # Generate agent name from purpose
    agent_name = agent_purpose.lower().replace(' ', '-')[:50]
    
    config = {
        'agentName': agent_name,
        'foundationModel': foundation_model,
        'instruction': system_prompts,
        'description': agent_purpose,
        'idleSessionTTLInSeconds': 1800,
        'actionGroups': [
            {
                'actionGroupName': f'{agent_name}-actions',
                'description': f'Action group for {agent_purpose}',
                'actionGroupExecutor': {
                    'lambda': '${LambdaFunctionArn}'
                },
                'apiSchema': {
                    's3': {
                        's3BucketName': '${SchemaBucket}',
                        's3ObjectKey': f'{agent_name}-schema.yaml'
                    }
                }
            }
        ]
    }
    
    return config


def handle_generate_openapi_schema(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle generate_openapi_schema action.
    Generates OpenAPI 3.0 schema for action groups.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, action_group_spec)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, openapi_schema, and status
    """
    job_name = params.get('job_name')
    action_group_spec_str = params.get('action_group_spec')
    
    if not job_name or not action_group_spec_str:
        raise ValueError("Missing required parameters: job_name and action_group_spec")
    
    # Parse action_group_spec if it's a string
    if isinstance(action_group_spec_str, str):
        try:
            action_group_spec = json.loads(action_group_spec_str)
        except json.JSONDecodeError:
            action_group_spec = {}
    else:
        action_group_spec = action_group_spec_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='code-generator',
        action_name='generate_openapi_schema',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Generate OpenAPI schema
        logger.info(f"Generating OpenAPI schema for job: {job_name}")
        
        openapi_schema = generate_openapi_yaml(action_group_spec)
        
        # Prepare response
        result = {
            "job_name": job_name,
            "openapi_schema": openapi_schema,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            filename='openapi_schema.yaml'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save OpenAPI schema to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            artifact=openapi_schema,
            filename='openapi_schema.yaml',
            content_type='application/x-yaml'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='code',
            agent_name='code-generator',
            response=result,
            filename='generate_openapi_schema_raw_response.json'
        )
        
        logger.info(f"OpenAPI schema generated successfully for job {job_name}")
        return result
        
    except Exception as e:
        # Log error to DynamoDB
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )
        raise


def generate_openapi_yaml(action_group_spec: Dict[str, Any]) -> str:
    """
    Generate OpenAPI 3.0 schema in YAML format.
    
    Returns:
        String containing YAML schema
    """
    agent_name = action_group_spec.get('agent_name', 'generated-agent')
    actions = action_group_spec.get('actions', [])
    
    # If no actions specified, create a default action
    if not actions:
        actions = [
            {
                'name': 'primary_action',
                'description': 'Primary action for the agent',
                'parameters': ['user_input', 'session_id']
            }
        ]
    
    # Build OpenAPI schema
    schema = f"""openapi: 3.0.0
info:
  title: {agent_name.replace('-', ' ').title()} Action Group API
  description: API for {agent_name} agent actions
  version: 1.0.0

paths:
"""
    
    # Add paths for each action
    for action in actions:
        action_name = action.get('name', 'action')
        action_desc = action.get('description', f'{action_name} action')
        parameters = action.get('parameters', [])
        
        path = f"/{action_name.replace('_', '-')}"
        
        schema += f"""  {path}:
    post:
      summary: {action_desc}
      description: {action_desc}
      operationId: {action_name}
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
"""
        
        # Add required parameters
        for param in parameters:
            schema += f"                - {param}\n"
        
        schema += f"""              properties:
"""
        
        # Add parameter definitions
        for param in parameters:
            schema += f"""                {param}:
                  type: string
                  description: {param.replace('_', ' ').title()}
"""
        
        schema += f"""      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  response:
                    type: string
                    description: Action response
                  session_id:
                    type: string
                    description: Session identifier
                  status:
                    type: string
                    description: Status of operation
        '400':
          description: Invalid request
        '500':
          description: Internal server error

"""
    
    return schema
