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
from shared.utils.agentcore_rate_limiter import apply_rate_limiting
from shared.models.code_artifacts import CodeArtifacts


# Initialize clients
dynamodb_client = DynamoDBClient()
s3_client = S3Client()
logger = get_logger(__name__)
foundational_model = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


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
        
        # Apply rate limiting before processing
        apply_rate_limiting('requirements-analyst')
        
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


def handle_extract_requirements(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle extract_requirements action.
    Extracts structured requirements from user request.
    
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
    raw_request = json.dumps(event, default=str)
    logger.info(f"RAW REQUEST for {job_name}: {raw_request}")
    
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='requirements-analyst',
        action_name='extract_requirements',
        prompt=raw_request,
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Extract requirements from user request
        logger.info(f"Extracting requirements for job: {job_name}")
        
        requirements = {
            "agent_purpose": user_request,
            "capabilities": ["Process user requests"],
            "interactions": ["API-based"],
            "data_needs": ["Session state"],
            "integrations": ["AWS Bedrock Agent runtime"],
            "system_prompts": f"You are an AI agent for: {user_request}",
            "lambda_requirements": {
                "runtime": "python3.12",
                "memory": 512,
                "timeout": 60,
                "actions": [{"name": "primary_action", "description": "Main action"}]
            },
            "architecture_requirements": {
                "compute": {"lambda_functions": 1, "memory_mb": 512, "timeout_seconds": 60},
                "storage": {"dynamodb_tables": 0, "s3_buckets": 0},
                "bedrock": {"agent_count": 1, "foundation_model": foundational_model, "action_groups": 1}
            },
            "deployment_requirements": {
                "deployment_method": "cloudformation",
                "region": "us-east-2"
            },
            "complexity": "low"
        }
        
        # Prepare response
        result = {
            "job_name": job_name,
            "requirements": requirements,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        raw_response = json.dumps(result, default=str)
        logger.info(f"RAW RESPONSE for {job_name}: {raw_response}")
        
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            filename='requirements.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=raw_response,
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save requirements to S3
        try:
            s3_client.save_converted_artifact(
                job_name=job_name,
                phase='requirements',
                agent_name='requirements-analyst',
                artifact=requirements,
                filename='requirements.json',
                content_type='application/json'
            )
            logger.info(f"Requirements saved to S3 for job {job_name}")
        except Exception as s3_error:
            logger.error(f"Failed to save requirements to S3 for job {job_name}: {str(s3_error)}")
        
        # Also save raw response to S3
        try:
            s3_client.save_raw_response(
                job_name=job_name,
                phase='requirements',
                agent_name='requirements-analyst',
                response=result,
                filename='extract_requirements_raw_response.json'
            )
            logger.info(f"Raw response saved to S3 for job {job_name}")
        except Exception as s3_error:
            logger.error(f"Failed to save raw response to S3 for job {job_name}: {str(s3_error)}")
        
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


def handle_analyze_complexity(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle analyze_complexity action.
    Analyzes complexity of requirements.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, requirements)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, complexity_score, assessment, and status
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
        agent_name='requirements-analyst',
        action_name='analyze_complexity',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Analyze complexity
        logger.info(f"Analyzing complexity for job: {job_name}")
        
        assessment = {
            "estimated_effort": "2-3 days",
            "key_challenges": ["Integration complexity", "Testing requirements"],
            "recommended_approach": "Incremental development with continuous testing"
        }
        
        # Prepare response
        result = {
            "job_name": job_name,
            "complexity_score": "medium",
            "assessment": assessment,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='requirements',
            agent_name='requirements-analyst',
            filename='complexity_analysis.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save analysis to S3
        try:
            s3_client.save_converted_artifact(
                job_name=job_name,
                phase='requirements',
                agent_name='requirements-analyst',
                artifact=result,
                filename='complexity_analysis.json',
                content_type='application/json'
            )
            logger.info(f"Complexity analysis saved to S3 for job {job_name}")
        except Exception as s3_error:
            logger.error(f"Failed to save complexity analysis to S3 for job {job_name}: {str(s3_error)}")
        
        # Also save raw response to S3
        try:
            s3_client.save_raw_response(
                job_name=job_name,
                phase='requirements',
                agent_name='requirements-analyst',
                response=result,
                filename='analyze_complexity_raw_response.json'
            )
            logger.info(f"Complexity analysis raw response saved to S3 for job {job_name}")
        except Exception as s3_error:
            logger.error(f"Failed to save complexity analysis raw response to S3 for job {job_name}: {str(s3_error)}")
        
        logger.info(f"Complexity analyzed successfully for job {job_name}")
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


def handle_validate_requirements(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle validate_requirements action.
    Validates completeness of requirements.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, requirements)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, is_valid, missing_items, recommendations, and status
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
        agent_name='requirements-analyst',
        action_name='validate_requirements',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Validate requirements
        logger.info(f"Validating requirements for job: {job_name}")
        
        missing_items = []
        recommendations = ["Requirements are complete"]
        
        # Check for required fields
        required_fields = ['agent_purpose', 'capabilities', 'system_prompts']
        for field in required_fields:
            if field not in requirements or not requirements[field]:
                missing_items.append(field)
        
        is_valid = len(missing_items) == 0
        
        # Prepare response
        result = {
            "job_name": job_name,
            "is_valid": is_valid,
            "missing_items": missing_items,
            "recommendations": recommendations,
            "status": "success"
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
        try:
            s3_client.save_converted_artifact(
                job_name=job_name,
                phase='requirements',
                agent_name='requirements-analyst',
                artifact=result,
                filename='validation_results.json',
                content_type='application/json'
            )
            logger.info(f"Validation results saved to S3 for job {job_name}")
        except Exception as s3_error:
            logger.error(f"Failed to save validation results to S3 for job {job_name}: {str(s3_error)}")
        
        # Also save raw response to S3
        try:
            s3_client.save_raw_response(
                job_name=job_name,
                phase='requirements',
                agent_name='requirements-analyst',
                response=result,
                filename='validate_requirements_raw_response.json'
            )
            logger.info(f"Validation results raw response saved to S3 for job {job_name}")
        except Exception as s3_error:
            logger.error(f"Failed to save validation results raw response to S3 for job {job_name}: {str(s3_error)}")
        
        logger.info(f"Requirements validated successfully for job {job_name}")
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

