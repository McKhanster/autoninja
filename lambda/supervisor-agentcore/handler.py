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
        job_name = params.get('job_name', 'unknown')
        
        # Set logger context
        logger.set_context(
            job_name=job_name,
            agent_name='supervisor',
            action_name=api_path
        )
        
        # Apply rate limiting before processing
        apply_rate_limiting('supervisor')
        
        # Log raw input to DynamoDB immediately
        raw_request = json.dumps(event, default=str)
        logger.info(f"RAW REQUEST for {job_name}: {raw_request}")
        
        logger.info(f"Processing request for apiPath: {api_path}")
        logger.info(f"Parameters: {params}")
        
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


def handle_orchestrate(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle orchestrate action.
    Orchestrates 5 collaborator agents using direct Lambda invocation with AgentCore Memory rate limiting.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (user_request)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with final orchestration results
    """
    user_request = params.get('user_request')
    
    if not user_request:
        raise ValueError("Missing required parameter: user_request")
    
    # Generate unique job_name
    job_name = generate_job_name(user_request)
    
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
        logger.info(f"Starting direct Lambda orchestration for job: {job_name}")
        logger.info(f"User request: {user_request}")
        
        results = {}
        
        # Step 1: Requirements Analyst (3 sequential calls)
        logger.info("=== STEP 1: Requirements Analyst ===")
        
        # Step 1a: Extract Requirements
        logger.info("=== STEP 1a: Extract Requirements ===")
        apply_rate_limiting('supervisor-to-requirements-extract')
        
        requirements_extract = invoke_agent_lambda(
            'requirements-analyst',
            '/extract-requirements',
            job_name,
            {'user_request': user_request}
        )
        logger.info(f"Requirements extraction completed: {type(requirements_extract).__name__}")
        
        # Step 1b: Analyze Complexity
        logger.info("=== STEP 1b: Analyze Complexity ===")
        apply_rate_limiting('requirements-extract-to-complexity')
        
        complexity_analysis = invoke_agent_lambda(
            'requirements-analyst',
            '/analyze-complexity',
            job_name,
            {
                'requirements': json.dumps(requirements_extract) if isinstance(requirements_extract, dict) else str(requirements_extract)
            }
        )
        logger.info(f"Complexity analysis completed: {type(complexity_analysis).__name__}")
        
        # Step 1c: Validate Requirements
        logger.info("=== STEP 1c: Validate Requirements ===")
        apply_rate_limiting('complexity-to-validation')
        
        requirements_validation = invoke_agent_lambda(
            'requirements-analyst',
            '/validate-requirements',
            job_name,
            {
                'requirements': json.dumps(requirements_extract) if isinstance(requirements_extract, dict) else str(requirements_extract)
            }
        )
        logger.info(f"Requirements validation completed: is_valid={requirements_validation.get('is_valid')}")
        
        # Combine all Requirements Analyst results
        requirements = {
            'extract': requirements_extract,
            'complexity': complexity_analysis,
            'validation': requirements_validation
        }
        results['requirements'] = requirements
        logger.info(f"Requirements Analyst phase completed with 3 interactions")
        
        # Step 2: Solution Architect (3 sequential calls)
        logger.info("=== STEP 2: Solution Architect ===")
        
        # Step 2a: Design Architecture
        logger.info("=== STEP 2a: Design Architecture ===")
        apply_rate_limiting('requirements-to-architecture-design')
        
        architecture_design = invoke_agent_lambda(
            'solution-architect',
            '/design-architecture',
            job_name,
            {
                'requirements': json.dumps(requirements['extract']) if isinstance(requirements['extract'], dict) else str(requirements['extract']),
                'code_file_references': '{}'
            }
        )
        logger.info(f"Architecture design completed: {type(architecture_design).__name__}")
        
        # Step 2b: Select Services
        logger.info("=== STEP 2b: Select Services ===")
        apply_rate_limiting('architecture-design-to-services')
        
        service_selection = invoke_agent_lambda(
            'solution-architect',
            '/select-services',
            job_name,
            {
                'requirements': json.dumps(requirements['extract']) if isinstance(requirements['extract'], dict) else str(requirements['extract'])
            }
        )
        logger.info(f"Service selection completed: {type(service_selection).__name__}")
        
        # Step 2c: Generate IaC
        logger.info("=== STEP 2c: Generate Infrastructure as Code ===")
        apply_rate_limiting('services-to-iac')
        
        iac_generation = invoke_agent_lambda(
            'solution-architect',
            '/generate-iac',
            job_name,
            {
                'architecture': json.dumps(architecture_design) if isinstance(architecture_design, dict) else str(architecture_design),
                'code_references': '{}'
            }
        )
        logger.info(f"IaC generation completed: {type(iac_generation).__name__}")
        
        # Combine all Solution Architect results
        architecture = {
            'design': architecture_design,
            'services': service_selection,
            'iac': iac_generation
        }
        results['architecture'] = architecture
        logger.info(f"Solution Architect phase completed with 3 interactions")
        
        # Step 3: Code Generator (3 sequential calls)
        logger.info("=== STEP 3: Code Generator ===")
        
        # Step 3a: Generate Lambda Code
        logger.info("=== STEP 3a: Generate Lambda Code ===")
        apply_rate_limiting('architecture-to-lambda-code')
        
        lambda_code = invoke_agent_lambda(
            'code-generator',
            '/generate-lambda-code',
            job_name,
            {
                'requirements': json.dumps(requirements['extract']) if isinstance(requirements['extract'], dict) else str(requirements['extract']),
                'function_spec': json.dumps(architecture['design']) if isinstance(architecture['design'], dict) else str(architecture['design'])
            }
        )
        logger.info(f"Lambda code generation completed: {type(lambda_code).__name__}")
        
        # Step 3b: Generate Agent Config
        logger.info("=== STEP 3b: Generate Agent Config ===")
        apply_rate_limiting('lambda-code-to-agent-config')
        
        agent_config = invoke_agent_lambda(
            'code-generator',
            '/generate-agent-config',
            job_name,
            {
                'requirements': json.dumps(requirements['extract']) if isinstance(requirements['extract'], dict) else str(requirements['extract'])
            }
        )
        logger.info(f"Agent config generation completed: {type(agent_config).__name__}")
        
        # Step 3c: Generate OpenAPI Schema
        logger.info("=== STEP 3c: Generate OpenAPI Schema ===")
        apply_rate_limiting('agent-config-to-openapi')
        
        openapi_schema = invoke_agent_lambda(
            'code-generator',
            '/generate-openapi-schema',
            job_name,
            {
                'action_group_spec': json.dumps(agent_config) if isinstance(agent_config, dict) else str(agent_config)
            }
        )
        logger.info(f"OpenAPI schema generation completed: {type(openapi_schema).__name__}")
        
        # Combine all Code Generator results
        code = {
            'lambda_code': lambda_code,
            'agent_config': agent_config,
            'openapi_schema': openapi_schema
        }
        results['code'] = code
        logger.info(f"Code Generator phase completed with 3 interactions")
        
        # Step 4: Quality Validator (3 sequential calls)
        logger.info("=== STEP 4: Quality Validator ===")
        
        # Step 4a: Validate Code
        logger.info("=== STEP 4a: Validate Code ===")
        apply_rate_limiting('code-to-validation')
        
        code_validation = invoke_agent_lambda(
            'quality-validator',
            '/validate-code',
            job_name,
            {
                'code': json.dumps(code['lambda_code']) if isinstance(code['lambda_code'], dict) else str(code['lambda_code']),
                'language': 'python'
            }
        )
        logger.info(f"Code validation completed: is_valid={code_validation.get('is_valid')}")
        
        # Step 4b: Security Scan
        logger.info("=== STEP 4b: Security Scan ===")
        apply_rate_limiting('validation-to-security')
        
        security_scan = invoke_agent_lambda(
            'quality-validator',
            '/security-scan',
            job_name,
            {
                'code': json.dumps(code['lambda_code']) if isinstance(code['lambda_code'], dict) else str(code['lambda_code']),
                'architecture': json.dumps(architecture['design']) if isinstance(architecture['design'], dict) else str(architecture['design'])
            }
        )
        logger.info(f"Security scan completed: {type(security_scan).__name__}")
        
        # Step 4c: Compliance Check
        logger.info("=== STEP 4c: Compliance Check ===")
        apply_rate_limiting('security-to-compliance')
        
        compliance_check = invoke_agent_lambda(
            'quality-validator',
            '/compliance-check',
            job_name,
            {
                'code': json.dumps(code['lambda_code']) if isinstance(code['lambda_code'], dict) else str(code['lambda_code']),
                'requirements': json.dumps(requirements['extract']) if isinstance(requirements['extract'], dict) else str(requirements['extract'])
            }
        )
        logger.info(f"Compliance check completed: {type(compliance_check).__name__}")
        
        # Combine all Quality Validator results
        validation = {
            'code_validation': code_validation,
            'security_scan': security_scan,
            'compliance_check': compliance_check,
            'is_valid': code_validation.get('is_valid', False)  # Overall validation status
        }
        results['validation'] = validation
        logger.info(f"Quality Validator phase completed with 3 interactions: is_valid={validation.get('is_valid')}")
        
        # Step 5: Deployment Manager (4 sequential calls - only if validation passes)
        if validation.get('is_valid', False):
            logger.info("=== STEP 5: Deployment Manager (Validation Passed) ===")
            
            # Step 5a: Generate CloudFormation
            logger.info("=== STEP 5a: Generate CloudFormation ===")
            apply_rate_limiting('validation-to-cloudformation')
            
            cloudformation_gen = invoke_agent_lambda(
                'deployment-manager',
                '/generate-cloudformation',
                job_name,
                {
                    'requirements': json.dumps(requirements['extract']) if isinstance(requirements['extract'], dict) else str(requirements['extract']),
                    'code': json.dumps(code['lambda_code']) if isinstance(code['lambda_code'], dict) else str(code['lambda_code']),
                    'architecture': json.dumps(architecture['design']) if isinstance(architecture['design'], dict) else str(architecture['design']),
                    'validation_status': 'passed'
                }
            )
            logger.info(f"CloudFormation generation completed: {type(cloudformation_gen).__name__}")
            
            # Step 5b: Deploy Stack
            logger.info("=== STEP 5b: Deploy Stack ===")
            apply_rate_limiting('cloudformation-to-deploy')
            
            stack_deployment = invoke_agent_lambda(
                'deployment-manager',
                '/deploy-stack',
                job_name,
                {
                    'cloudformation_template': json.dumps(cloudformation_gen) if isinstance(cloudformation_gen, dict) else str(cloudformation_gen),
                    'stack_name': f"{job_name}-stack"
                }
            )
            logger.info(f"Stack deployment completed: {type(stack_deployment).__name__}")
            
            # Step 5c: Configure Agent
            logger.info("=== STEP 5c: Configure Agent ===")
            apply_rate_limiting('deploy-to-configure')
            
            agent_configuration = invoke_agent_lambda(
                'deployment-manager',
                '/configure-agent',
                job_name,
                {
                    'agent_config': json.dumps(code['agent_config']) if isinstance(code['agent_config'], dict) else str(code['agent_config']),
                    'lambda_arns': json.dumps(stack_deployment) if isinstance(stack_deployment, dict) else str(stack_deployment)
                }
            )
            logger.info(f"Agent configuration completed: {type(agent_configuration).__name__}")
            
            # Step 5d: Test Deployment
            logger.info("=== STEP 5d: Test Deployment ===")
            apply_rate_limiting('configure-to-test')
            
            deployment_test = invoke_agent_lambda(
                'deployment-manager',
                '/test-deployment',
                job_name,
                {
                    'agent_id': agent_configuration.get('agent_id') if isinstance(agent_configuration, dict) else 'test-agent-id',
                    'alias_id': agent_configuration.get('alias_id') if isinstance(agent_configuration, dict) else 'test-alias-id',
                    'test_inputs': json.dumps(requirements['extract']) if isinstance(requirements['extract'], dict) else str(requirements['extract'])
                }
            )
            logger.info(f"Deployment testing completed: {type(deployment_test).__name__}")
            
            # Combine all Deployment Manager results
            deployment = {
                'cloudformation': cloudformation_gen,
                'stack_deployment': stack_deployment,
                'agent_configuration': agent_configuration,
                'deployment_test': deployment_test
            }
            results['deployment'] = deployment
            logger.info(f"Deployment Manager phase completed with 4 interactions")
            
            final_result = {
                "job_name": job_name,
                "status": "deployed",
                "agent_arn": deployment.get('agent_configuration', {}).get('agent_arn', 'generated'),
                "results": results,
                "workflow_completed": True
            }
            logger.info(f"=== ORCHESTRATION COMPLETED SUCCESSFULLY ===")
            
        else:
            logger.warning("=== ORCHESTRATION STOPPED: Validation Failed ===")
            final_result = {
                "job_name": job_name,
                "status": "validation_failed",
                "validation_issues": validation.get('issues', []),
                "results": results,
                "workflow_completed": False
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
    
    logger.info(f"Invoking {agent_name} Lambda: {function_name}")
    logger.info(f"API Path: {api_path}")
    logger.info(f"Parameters: {list(params.keys())}")
    
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
                logger.warning(f"Unexpected Lambda response format from {agent_name}")
                logger.info(f"Response keys: {list(response_payload.keys())}")
                return {"response": str(response_payload), "status": "success", "agent_name": agent_name}
        else:
            error_msg = f"Lambda invocation failed with status {status_code}"
            logger.error(f"{agent_name}: {error_msg}")
            logger.error(f"Response: {response_payload}")
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