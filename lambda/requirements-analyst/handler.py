"""
Requirements Analyst Lambda Function
Extracts, analyzes, and validates requirements from user requests
"""
import json
import os
import time
from typing import Dict, Any, List, Optional

# Import shared utilities from Lambda Layer
from shared.persistence.dynamodb_client import DynamoDBClient
from shared.persistence.s3_client import S3Client
from shared.utils.logger import get_logger
from shared.models.requirements import Requirements


# Initialize clients
dynamodb_client = DynamoDBClient()
s3_client = S3Client()
logger = get_logger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Requirements Analyst agent.
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
        action_group = event.get('actionGroup', 'requirements-analyst-actions')
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
            agent_name='requirements-analyst',
            action_name=api_path
        )
        
        logger.info(f"Processing request for apiPath: {api_path}")
        
        # Route to appropriate action handler
        if api_path == '/extract-requirements':
            result = handle_extract_requirements(event, params, session_id, start_time)
        elif api_path == '/analyze-complexity':
            result = handle_analyze_complexity(event, params, session_id, start_time)
        elif api_path == '/validate-requirements':
            result = handle_validate_requirements(event, params, session_id, start_time)
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
                'actionGroup': event.get('actionGroup', 'requirements-analyst-actions'),
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


def invoke_bedrock_model(prompt: str, model_id: str = None) -> str:
    """
    Invoke Bedrock model with the given prompt.
    
    Args:
        prompt: The prompt to send to the model
        model_id: Optional model ID (defaults to Claude Sonnet 4)
        
    Returns:
        The model's response text
    """
    if model_id is None:
        model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    # Prepare request body for Claude
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    }
    
    try:
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract text from Claude response
        if 'content' in response_body and len(response_body['content']) > 0:
            return response_body['content'][0]['text']
        else:
            raise ValueError("Unexpected response format from Bedrock")
            
    except Exception as e:
        logger.error(f"Error invoking Bedrock model: {str(e)}")
        raise


def extract_requirements_with_bedrock(user_request: str, job_name: str) -> Dict[str, Any]:
    """
    Use Bedrock to extract comprehensive requirements from user request.
    
    Args:
        user_request: The user's natural language request
        job_name: Job identifier for logging
        
    Returns:
        Dict with all requirements fields
    """
    prompt = f"""You are a requirements analyst for an AI agent generation system. Your task is to extract comprehensive requirements from a user's request for an AI agent.

User Request: "{user_request}"

Extract and generate the following requirements in JSON format:

1. agent_purpose: A clear description of what this agent should do
2. capabilities: List of specific capabilities the agent needs (array of strings)
3. interactions: List of how users will interact with the agent (array of strings)
4. data_needs: List of data storage or persistence needs (array of strings)
5. integrations: List of external systems or services to integrate with (array of strings)
6. system_prompts: Detailed system prompt instructions for the agent (string)
7. lambda_requirements: Object with:
   - runtime: "python3.12"
   - memory: memory in MB (number)
   - timeout: timeout in seconds (number)
   - environment_variables: object with any needed env vars
   - actions: array of action objects with name, description, parameters
8. architecture_requirements: Object with:
   - compute: object with lambda_functions count, memory_mb, timeout_seconds
   - storage: object with dynamodb_tables count, s3_buckets count
   - bedrock: object with agent_count, foundation_model, action_groups count
   - iam: object with roles_needed array, policies array
9. deployment_requirements: Object with:
   - deployment_method: "cloudformation"
   - region: AWS region
   - stack_name_prefix: prefix for stack name
   - tags: object with tags
   - post_deployment: object with create_alias, alias_name, run_tests
10. complexity: "simple", "moderate", or "complex"
11. additional_notes: Any additional observations or recommendations

Generate comprehensive, production-ready requirements. Be specific and detailed.

Respond ONLY with valid JSON, no other text."""

    logger.info(f"Sending prompt to Bedrock (length: {len(prompt)} chars)")
    
    # Call Bedrock
    response_text = invoke_bedrock_model(prompt)
    
    logger.info(f"Received response from Bedrock (length: {len(response_text)} chars)")
    
    # Parse JSON response
    try:
        # Try to extract JSON from response (in case model adds extra text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            requirements_data = json.loads(json_str)
        else:
            requirements_data = json.loads(response_text)
        
        logger.info(f"Successfully parsed requirements JSON")
        return requirements_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response as JSON: {str(e)}")
        logger.error(f"Response text: {response_text[:500]}")
        
        # Fallback to simple extraction
        logger.warning("Falling back to simple keyword-based extraction")
        return {
            "agent_purpose": f"AI agent based on user request: {user_request}",
            "capabilities": extract_capabilities(user_request),
            "interactions": extract_interactions(user_request),
            "data_needs": extract_data_needs(user_request),
            "integrations": extract_integrations(user_request),
            "system_prompts": generate_system_prompts_requirements(user_request),
            "lambda_requirements": extract_lambda_requirements(user_request),
            "architecture_requirements": extract_architecture_requirements(user_request),
            "deployment_requirements": extract_deployment_requirements(user_request),
            "complexity": assess_initial_complexity(user_request),
            "additional_notes": f"Extracted from user request: {user_request}"
        }


def handle_extract_requirements(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle extract_requirements action.
    Extracts comprehensive requirements for ALL sub-agents from user request.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, user_request)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, requirements, and status
    """
    job_name = params.get('job_name')
    user_request = params.get('user_request')
    
    if not job_name or not user_request:
        raise ValueError("Missing required parameters: job_name and user_request")
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='requirements-analyst',
        action_name='extract_requirements',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Extract requirements using simple logic (no Bedrock call needed)
        logger.info(f"Extracting requirements for: {user_request}")
        requirements_data = {
            "agent_purpose": f"AI agent based on user request: {user_request}",
            "capabilities": extract_capabilities(user_request),
            "interactions": extract_interactions(user_request),
            "data_needs": extract_data_needs(user_request),
            "integrations": extract_integrations(user_request),
            "system_prompts": generate_system_prompts_requirements(user_request),
            "lambda_requirements": extract_lambda_requirements(user_request),
            "architecture_requirements": extract_architecture_requirements(user_request),
            "deployment_requirements": extract_deployment_requirements(user_request),
            "complexity": assess_initial_complexity(user_request),
            "additional_notes": f"Extracted from user request: {user_request}"
        }
        
        # Create Requirements object
        requirements = Requirements(**requirements_data)
        
        # Prepare response
        result = {
            "job_name": job_name,
            "requirements": requirements.to_dict(),
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            filename='requirements.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save requirements JSON to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            artifact=requirements.to_dict(),
            filename='requirements.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            response=result,
            filename='raw_response.json'
        )
        
        logger.info(f"Requirements extracted successfully for job {job_name}")
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


def extract_capabilities(user_request: str) -> List[str]:
    """Extract agent capabilities from user request."""
    # Simple keyword-based extraction
    capabilities = []
    
    if 'conversation' in user_request.lower() or 'chat' in user_request.lower() or 'talk' in user_request.lower():
        capabilities.append("Natural language conversation")
    if 'friend' in user_request.lower():
        capabilities.append("Friendly interaction and companionship")
        capabilities.append("Emotional support")
    if 'help' in user_request.lower() or 'assist' in user_request.lower():
        capabilities.append("User assistance")
    if 'answer' in user_request.lower() or 'question' in user_request.lower():
        capabilities.append("Question answering")
    
    # Default capability if none detected
    if not capabilities:
        capabilities.append("General purpose interaction")
    
    return capabilities


def extract_interactions(user_request: str) -> List[str]:
    """Extract interaction patterns from user request."""
    interactions = [
        "Text-based conversation via Bedrock Agent API",
        "Stateful sessions with conversation history",
        "Natural language input and response"
    ]
    return interactions


def extract_data_needs(user_request: str) -> List[str]:
    """Extract data requirements from user request."""
    data_needs = []
    
    if 'remember' in user_request.lower() or 'store' in user_request.lower():
        data_needs.append("Persistent storage for user preferences")
        data_needs.append("DynamoDB table for data persistence")
    if 'history' in user_request.lower():
        data_needs.append("Conversation history storage")
    
    # Default data needs
    if not data_needs:
        data_needs.append("Session state management (handled by Bedrock)")
    
    return data_needs


def extract_integrations(user_request: str) -> List[str]:
    """Extract integration requirements from user request."""
    integrations = []
    
    if 'api' in user_request.lower():
        integrations.append("External API integration")
    if 'database' in user_request.lower() or 'db' in user_request.lower():
        integrations.append("Database integration")
    if 'email' in user_request.lower():
        integrations.append("Email service integration")
    
    # Default integrations
    if not integrations:
        integrations.append("AWS Bedrock Agent runtime")
    
    return integrations


def generate_system_prompts_requirements(user_request: str) -> str:
    """Generate system prompt requirements based on user request."""
    return f"""System prompt should instruct the agent to:
1. Understand and respond to user requests related to: {user_request}
2. Maintain a helpful and friendly tone
3. Provide clear and accurate responses
4. Handle errors gracefully
5. Stay within the scope of its defined capabilities"""


def extract_lambda_requirements(user_request: str) -> Dict[str, Any]:
    """Extract Lambda function requirements."""
    return {
        "runtime": "python3.12",
        "memory": 512,
        "timeout": 60,
        "environment_variables": {
            "LOG_LEVEL": "INFO"
        },
        "actions": [
            {
                "name": "primary_action",
                "description": f"Handle requests related to: {user_request}",
                "parameters": ["user_input", "session_id"]
            }
        ]
    }


def extract_architecture_requirements(user_request: str) -> Dict[str, Any]:
    """Extract architecture requirements for Solution Architect."""
    return {
        "compute": {
            "lambda_functions": 1,
            "memory_mb": 512,
            "timeout_seconds": 60
        },
        "storage": {
            "dynamodb_tables": 0,  # Only if needed
            "s3_buckets": 0  # Only if needed
        },
        "bedrock": {
            "agent_count": 1,
            "foundation_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "action_groups": 1
        },
        "iam": {
            "roles_needed": ["lambda_execution_role", "bedrock_agent_role"],
            "policies": ["lambda_basic_execution", "bedrock_invoke_model"]
        }
    }


def extract_deployment_requirements(user_request: str) -> Dict[str, Any]:
    """Extract deployment requirements for Deployment Manager."""
    return {
        "deployment_method": "cloudformation",
        "region": os.environ.get('AWS_REGION', 'us-east-2'),
        "stack_name_prefix": "generated-agent",
        "tags": {
            "Project": "AutoNinja",
            "GeneratedFrom": "Requirements Analyst"
        },
        "post_deployment": {
            "create_alias": True,
            "alias_name": "prod",
            "run_tests": True
        }
    }


def assess_initial_complexity(user_request: str) -> str:
    """Assess initial complexity of the request."""
    word_count = len(user_request.split())
    
    if word_count < 10:
        return "simple"
    elif word_count < 30:
        return "moderate"
    else:
        return "complex"


def handle_analyze_complexity(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle analyze_complexity action.
    Analyzes requirements complexity and generates assessment.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, requirements)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, complexity_score, and assessment
    """
    job_name = params.get('job_name')
    requirements_str = params.get('requirements')
    
    if not job_name:
        raise ValueError("Missing required parameter: job_name")
    
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
        agent_name='requirements-analyst',
        action_name='analyze_complexity',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Analyze complexity based on requirements
        complexity_score = calculate_complexity_score(requirements)
        assessment = generate_complexity_assessment(requirements, complexity_score)
        
        # Prepare response
        result = {
            "job_name": job_name,
            "complexity_score": complexity_score,
            "assessment": assessment
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            filename='complexity_assessment.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save assessment to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            artifact=result,
            filename='complexity_assessment.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            response=result,
            filename='analyze_complexity_raw_response.json'
        )
        
        logger.info(f"Complexity analysis completed for job {job_name}: {complexity_score}")
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


def calculate_complexity_score(requirements: Dict[str, Any]) -> str:
    """
    Calculate complexity score based on requirements.
    
    Returns: "simple", "moderate", or "complex"
    """
    score = 0
    
    # Check capabilities count
    capabilities = requirements.get('capabilities', [])
    if len(capabilities) > 5:
        score += 2
    elif len(capabilities) > 2:
        score += 1
    
    # Check integrations count
    integrations = requirements.get('integrations', [])
    if len(integrations) > 3:
        score += 2
    elif len(integrations) > 1:
        score += 1
    
    # Check data needs
    data_needs = requirements.get('data_needs', [])
    if len(data_needs) > 3:
        score += 2
    elif len(data_needs) > 1:
        score += 1
    
    # Check lambda requirements
    lambda_reqs = requirements.get('lambda_requirements', {})
    actions = lambda_reqs.get('actions', [])
    if len(actions) > 3:
        score += 2
    elif len(actions) > 1:
        score += 1
    
    # Check architecture requirements
    arch_reqs = requirements.get('architecture_requirements', {})
    storage = arch_reqs.get('storage', {})
    if storage.get('dynamodb_tables', 0) > 0 or storage.get('s3_buckets', 0) > 0:
        score += 1
    
    # Determine complexity level
    if score <= 2:
        return "simple"
    elif score <= 5:
        return "moderate"
    else:
        return "complex"


def generate_complexity_assessment(requirements: Dict[str, Any], complexity_score: str) -> Dict[str, Any]:
    """
    Generate detailed complexity assessment.
    
    Returns:
        Dict with estimated_effort, key_challenges, and recommended_approach
    """
    capabilities = requirements.get('capabilities', [])
    integrations = requirements.get('integrations', [])
    data_needs = requirements.get('data_needs', [])
    
    # Estimate effort
    effort_map = {
        "simple": "1-2 hours",
        "moderate": "3-5 hours",
        "complex": "6-10 hours"
    }
    estimated_effort = effort_map.get(complexity_score, "Unknown")
    
    # Identify key challenges
    key_challenges = []
    
    if len(capabilities) > 5:
        key_challenges.append("Multiple capabilities requiring careful orchestration")
    
    if len(integrations) > 2:
        key_challenges.append("Multiple external integrations requiring proper error handling")
    
    if len(data_needs) > 2:
        key_challenges.append("Complex data persistence requirements")
    
    lambda_reqs = requirements.get('lambda_requirements', {})
    if lambda_reqs.get('timeout', 60) > 120:
        key_challenges.append("Long-running operations requiring timeout management")
    
    if not key_challenges:
        key_challenges.append("Standard implementation with minimal complexity")
    
    # Recommend approach
    if complexity_score == "simple":
        recommended_approach = "Single Lambda function with basic action group. Minimal storage requirements. Straightforward deployment."
    elif complexity_score == "moderate":
        recommended_approach = "Multiple Lambda functions or actions. Consider DynamoDB for state. Implement proper error handling and retries."
    else:
        recommended_approach = "Modular architecture with multiple Lambda functions. Implement comprehensive error handling, monitoring, and logging. Consider Step Functions for orchestration if needed."
    
    return {
        "estimated_effort": estimated_effort,
        "key_challenges": key_challenges,
        "recommended_approach": recommended_approach
    }


def handle_validate_requirements(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle validate_requirements action.
    Validates requirements completeness and identifies missing items.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, requirements)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, is_valid, missing_items, and recommendations
    """
    job_name = params.get('job_name')
    requirements_str = params.get('requirements')
    
    if not job_name:
        raise ValueError("Missing required parameter: job_name")
    
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
        agent_name='requirements-analyst',
        action_name='validate_requirements',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Validate requirements completeness
        validation_result = validate_requirements_completeness(requirements)
        
        # Prepare response
        result = {
            "job_name": job_name,
            "is_valid": validation_result['is_valid'],
            "missing_items": validation_result['missing_items'],
            "recommendations": validation_result['recommendations']
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            filename='validation_results.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save validation results to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            artifact=result,
            filename='validation_results.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            response=result,
            filename='validate_requirements_raw_response.json'
        )
        
        logger.info(f"Requirements validation completed for job {job_name}: valid={result['is_valid']}")
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


def validate_requirements_completeness(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that requirements are complete and identify missing items.
    
    Returns:
        Dict with is_valid, missing_items, and recommendations
    """
    missing_items = []
    recommendations = []
    
    # Check required fields
    required_fields = [
        'agent_purpose',
        'capabilities',
        'interactions',
        'system_prompts',
        'lambda_requirements',
        'architecture_requirements',
        'deployment_requirements'
    ]
    
    for field in required_fields:
        if field not in requirements or not requirements[field]:
            missing_items.append(f"Missing or empty field: {field}")
    
    # Check capabilities
    capabilities = requirements.get('capabilities', [])
    if not capabilities:
        missing_items.append("No capabilities defined")
        recommendations.append("Define at least one capability for the agent")
    elif len(capabilities) < 2:
        recommendations.append("Consider adding more capabilities for a more useful agent")
    
    # Check interactions
    interactions = requirements.get('interactions', [])
    if not interactions:
        missing_items.append("No interaction patterns defined")
        recommendations.append("Define how users will interact with the agent")
    
    # Check system prompts
    system_prompts = requirements.get('system_prompts', '')
    if not system_prompts or len(system_prompts) < 50:
        missing_items.append("System prompts are missing or too brief")
        recommendations.append("Provide detailed system prompts to guide agent behavior")
    
    # Check lambda requirements
    lambda_reqs = requirements.get('lambda_requirements', {})
    if not lambda_reqs:
        missing_items.append("Lambda requirements not defined")
    else:
        if 'runtime' not in lambda_reqs:
            missing_items.append("Lambda runtime not specified")
        if 'actions' not in lambda_reqs or not lambda_reqs['actions']:
            missing_items.append("No Lambda actions defined")
            recommendations.append("Define at least one action for the Lambda function")
    
    # Check architecture requirements
    arch_reqs = requirements.get('architecture_requirements', {})
    if not arch_reqs:
        missing_items.append("Architecture requirements not defined")
    else:
        if 'bedrock' not in arch_reqs:
            missing_items.append("Bedrock configuration not specified")
            recommendations.append("Specify Bedrock agent configuration including foundation model")
        if 'iam' not in arch_reqs:
            missing_items.append("IAM requirements not specified")
            recommendations.append("Define required IAM roles and policies")
    
    # Check deployment requirements
    deploy_reqs = requirements.get('deployment_requirements', {})
    if not deploy_reqs:
        missing_items.append("Deployment requirements not defined")
    else:
        if 'deployment_method' not in deploy_reqs:
            recommendations.append("Specify deployment method (CloudFormation, Terraform, etc.)")
        if 'region' not in deploy_reqs:
            recommendations.append("Specify target AWS region for deployment")
    
    # Determine if valid (valid if no critical missing items)
    is_valid = len(missing_items) == 0
    
    # Add general recommendations
    if is_valid:
        recommendations.append("Requirements are complete and ready for next phase")
    else:
        recommendations.append("Address missing items before proceeding to design phase")
    
    return {
        'is_valid': is_valid,
        'missing_items': missing_items,
        'recommendations': recommendations
    }
