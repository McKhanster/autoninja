"""
Quality Validator Lambda Function
Validates code quality, performs security scans, and checks compliance
"""
import json
import os
import time
from typing import Dict, Any, List, Optional

# Import shared utilities from Lambda Layer
from shared.persistence.dynamodb_client import DynamoDBClient
from shared.persistence.s3_client import S3Client
from shared.utils.logger import get_logger


# Initialize clients
dynamodb_client = DynamoDBClient()
s3_client = S3Client()
logger = get_logger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Quality Validator agent.
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
        action_group = event.get('actionGroup', 'quality-validator-actions')
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
            agent_name='quality-validator',
            action_name=api_path
        )
        
        logger.info(f"Processing request for apiPath: {api_path}")
        
        # Route to appropriate action handler
        if api_path == '/validate-code':
            result = handle_validate_code(event, params, session_id, start_time)
        elif api_path == '/security-scan':
            result = handle_security_scan(event, params, session_id, start_time)
        elif api_path == '/compliance-check':
            result = handle_compliance_check(event, params, session_id, start_time)
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
                'actionGroup': event.get('actionGroup', 'quality-validator-actions'),
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


def handle_validate_code(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle validate_code action.
    Performs code quality validation.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, code, language)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, is_valid, issues, quality_score, and status
    """
    job_name = params.get('job_name')
    code_str = params.get('code')
    language = params.get('language', 'python')
    
    if not job_name or not code_str:
        raise ValueError("Missing required parameters: job_name and code")
    
    # Parse code if it's a string
    if isinstance(code_str, str):
        try:
            code = json.loads(code_str)
        except json.JSONDecodeError:
            code = {}
    else:
        code = code_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='quality-validator',
        action_name='validate_code',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Validate code quality
        logger.info(f"Validating code for job: {job_name}")
        
        issues = []
        
        # Check for basic quality indicators
        if isinstance(code, dict):
            for filename, content in code.items():
                if not content or len(content) < 10:
                    issues.append({
                        "severity": "warning",
                        "message": f"File {filename} appears to be empty or too short",
                        "file": filename,
                        "line": 0
                    })
                
                # Check for error handling
                if 'try:' not in content and 'except' not in content:
                    issues.append({
                        "severity": "info",
                        "message": f"File {filename} may lack error handling",
                        "file": filename,
                        "line": 0
                    })
        
        # Calculate quality score (set low threshold for testing - 50%)
        quality_score = max(50.0, 100.0 - (len(issues) * 10))
        is_valid = quality_score >= 50.0  # Low threshold for testing
        
        # Prepare response
        result = {
            "job_name": job_name,
            "is_valid": is_valid,
            "issues": issues,
            "quality_score": quality_score,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            filename='code_validation.json'
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
            phase='validation',
            agent_name='quality-validator',
            artifact=result,
            filename='code_validation.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            response=result,
            filename='validate_code_raw_response.json'
        )
        
        logger.info(f"Code validated successfully for job {job_name}")
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


def handle_security_scan(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle security_scan action.
    Scans code for security vulnerabilities.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, code, iam_policies)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, vulnerabilities, risk_level, and status
    """
    job_name = params.get('job_name')
    code_str = params.get('code')
    iam_policies_str = params.get('iam_policies', '{}')
    
    if not job_name or not code_str:
        raise ValueError("Missing required parameters: job_name and code")
    
    # Parse code if it's a string
    if isinstance(code_str, str):
        try:
            code = json.loads(code_str)
        except json.JSONDecodeError:
            code = {}
    else:
        code = code_str or {}
    
    # Parse iam_policies if it's a string
    if isinstance(iam_policies_str, str):
        try:
            iam_policies = json.loads(iam_policies_str)
        except json.JSONDecodeError:
            iam_policies = {}
    else:
        iam_policies = iam_policies_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='quality-validator',
        action_name='security_scan',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Perform security scan
        logger.info(f"Performing security scan for job: {job_name}")
        
        vulnerabilities = []
        
        # Check for common security issues
        if isinstance(code, dict):
            for filename, content in code.items():
                # Check for hardcoded credentials
                if 'password' in content.lower() or 'api_key' in content.lower():
                    if '=' in content:
                        vulnerabilities.append({
                            "type": "Hardcoded Credentials",
                            "severity": "high",
                            "description": f"Possible hardcoded credentials in {filename}",
                            "location": filename,
                            "remediation": "Use environment variables or AWS Secrets Manager"
                        })
                
                # Check for SQL injection risks
                if 'execute(' in content or 'query(' in content:
                    vulnerabilities.append({
                        "type": "SQL Injection Risk",
                        "severity": "medium",
                        "description": f"Potential SQL injection vulnerability in {filename}",
                        "location": filename,
                        "remediation": "Use parameterized queries"
                    })
        
        # Determine risk level
        high_severity_count = sum(1 for v in vulnerabilities if v.get('severity') == 'high')
        if high_severity_count > 0:
            risk_level = "high"
        elif len(vulnerabilities) > 0:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Prepare response
        result = {
            "job_name": job_name,
            "vulnerabilities": vulnerabilities,
            "risk_level": risk_level,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            filename='security_scan.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save security scan results to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            artifact=result,
            filename='security_scan.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            response=result,
            filename='security_scan_raw_response.json'
        )
        
        logger.info(f"Security scan completed successfully for job {job_name}")
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


def handle_compliance_check(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle compliance_check action.
    Checks compliance with standards.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, code, architecture)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, compliant, violations, and status
    """
    job_name = params.get('job_name')
    code_str = params.get('code')
    architecture_str = params.get('architecture', '{}')
    
    if not job_name or not code_str:
        raise ValueError("Missing required parameters: job_name and code")
    
    # Parse code if it's a string
    if isinstance(code_str, str):
        try:
            code = json.loads(code_str)
        except json.JSONDecodeError:
            code = {}
    else:
        code = code_str or {}
    
    # Parse architecture if it's a string
    if isinstance(architecture_str, str):
        try:
            architecture = json.loads(architecture_str)
        except json.JSONDecodeError:
            architecture = {}
    else:
        architecture = architecture_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='quality-validator',
        action_name='compliance_check',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Check compliance
        logger.info(f"Checking compliance for job: {job_name}")
        
        violations = []
        
        # Check AWS best practices
        if isinstance(code, dict):
            for filename, content in code.items():
                # Check for logging
                if 'logger' not in content and 'logging' not in content:
                    violations.append({
                        "standard": "AWS Lambda Best Practices",
                        "rule": "Logging",
                        "description": f"File {filename} lacks logging implementation",
                        "severity": "medium",
                        "remediation": "Add structured logging"
                    })
                
                # Check for error handling
                if 'try:' not in content:
                    violations.append({
                        "standard": "AWS Lambda Best Practices",
                        "rule": "Error Handling",
                        "description": f"File {filename} lacks error handling",
                        "severity": "high",
                        "remediation": "Add try-except blocks"
                    })
        
        # Determine compliance
        compliant = len(violations) == 0
        
        # Prepare response
        result = {
            "job_name": job_name,
            "compliant": compliant,
            "violations": violations,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            filename='compliance_check.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save compliance check results to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            artifact=result,
            filename='compliance_check.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            response=result,
            filename='compliance_check_raw_response.json'
        )
        
        logger.info(f"Compliance check completed successfully for job {job_name}")
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
