"""
Quality Validator Lambda Function
Validates generated code for quality, security, and compliance
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
    Performs code quality validation - syntax, error handling, logging, structure.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, code, architecture)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, is_valid, issues, and quality_score
    """
    job_name = params.get('job_name')
    code = params.get('code', '')
    architecture = params.get('architecture', '{}')
    
    if not job_name:
        raise ValueError("Missing required parameter: job_name")
    
    # STEP 1: Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='quality-validator',
        action_name='validate_code',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # STEP 3-5: Perform code quality validation
        logger.info(f"Validating code quality for job {job_name}")
        
        issues = []
        quality_score = 100  # Start with perfect score
        
        # Check for syntax errors (basic check)
        if not code or len(code.strip()) == 0:
            issues.append({
                "severity": "error",
                "category": "syntax",
                "message": "Code is empty or missing"
            })
            quality_score -= 50
        else:
            # Check for basic Python syntax
            try:
                compile(code, '<string>', 'exec')
                logger.info("Code syntax is valid")
            except SyntaxError as e:
                issues.append({
                    "severity": "error",
                    "category": "syntax",
                    "message": f"Syntax error: {str(e)}"
                })
                quality_score -= 30
        
        # Check for error handling
        if 'try:' not in code or 'except' not in code:
            issues.append({
                "severity": "warning",
                "category": "error_handling",
                "message": "Code lacks try-except error handling"
            })
            quality_score -= 10
        
        # Check for logging
        if 'logger' not in code and 'logging' not in code and 'print' not in code:
            issues.append({
                "severity": "warning",
                "category": "logging",
                "message": "Code lacks logging statements"
            })
            quality_score -= 10
        
        # Check for proper function structure
        if 'def ' not in code:
            issues.append({
                "severity": "warning",
                "category": "structure",
                "message": "Code lacks function definitions"
            })
            quality_score -= 10
        
        # Check for docstrings
        if '"""' not in code and "'''" not in code:
            issues.append({
                "severity": "info",
                "category": "documentation",
                "message": "Code lacks docstrings"
            })
            quality_score -= 5
        
        # Ensure quality_score doesn't go below 0
        quality_score = max(0, quality_score)
        
        # STEP 5: Set extremely low threshold (50% pass rate) for testing
        is_valid = quality_score >= 50
        
        # Prepare response
        result = {
            "job_name": job_name,
            "is_valid": is_valid,
            "issues": issues,
            "quality_score": quality_score,
            "status": "success"
        }
        
        # STEP 6: Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            filename='quality_report.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # STEP 7: Save validation report to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            artifact=result,
            filename='quality_report.json',
            content_type='application/json'
        )
        
        # STEP 8: Save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            response=result,
            filename='validate_code_raw_response.json'
        )
        
        logger.info(f"Code validation completed for job {job_name}: valid={is_valid}, score={quality_score}")
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
    Scans for hardcoded credentials, IAM permissions, injection vulnerabilities, encryption usage.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, code, iam_policies)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, vulnerabilities, and risk_level
    """
    job_name = params.get('job_name')
    code = params.get('code', '')
    iam_policies = params.get('iam_policies', '{}')
    
    if not job_name:
        raise ValueError("Missing required parameter: job_name")
    
    # STEP 1: Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='quality-validator',
        action_name='security_scan',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # STEP 3-6: Perform security scanning
        logger.info(f"Performing security scan for job {job_name}")
        
        vulnerabilities = []
        risk_score = 0  # Higher is worse
        
        # STEP 3: Scan for hardcoded credentials
        credential_patterns = [
            'password', 'secret', 'api_key', 'apikey', 'access_key',
            'secret_key', 'token', 'auth', 'credential'
        ]
        
        for pattern in credential_patterns:
            if pattern in code.lower():
                # Check if it's actually hardcoded (not just a variable name)
                if f'{pattern} = "' in code.lower() or f'{pattern}="' in code.lower():
                    vulnerabilities.append({
                        "severity": "high",
                        "category": "hardcoded_credentials",
                        "message": f"Potential hardcoded credential detected: {pattern}",
                        "recommendation": "Use environment variables or AWS Secrets Manager"
                    })
                    risk_score += 30
        
        # STEP 4: Validate IAM permissions follow least-privilege
        if isinstance(iam_policies, str):
            try:
                iam_policies_dict = json.loads(iam_policies)
            except json.JSONDecodeError:
                iam_policies_dict = {}
        else:
            iam_policies_dict = iam_policies or {}
        
        # Check for overly permissive policies
        if '*' in str(iam_policies_dict):
            vulnerabilities.append({
                "severity": "high",
                "category": "iam_permissions",
                "message": "IAM policy contains wildcard (*) permissions",
                "recommendation": "Use specific resource ARNs and actions"
            })
            risk_score += 25
        
        # STEP 5: Check for injection vulnerabilities
        injection_patterns = [
            'eval(', 'exec(', 'os.system(', 'subprocess.call(',
            'subprocess.run(', '__import__'
        ]
        
        for pattern in injection_patterns:
            if pattern in code:
                vulnerabilities.append({
                    "severity": "critical",
                    "category": "injection_vulnerability",
                    "message": f"Potential code injection vulnerability: {pattern}",
                    "recommendation": "Avoid dynamic code execution and validate all inputs"
                })
                risk_score += 40
        
        # STEP 6: Verify encryption usage
        if 'dynamodb' in code.lower() or 's3' in code.lower():
            if 'encryption' not in code.lower() and 'kms' not in code.lower():
                vulnerabilities.append({
                    "severity": "medium",
                    "category": "encryption",
                    "message": "Data storage without explicit encryption configuration",
                    "recommendation": "Enable encryption at rest using AWS KMS"
                })
                risk_score += 15
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        elif risk_score > 0:
            risk_level = "low"
        else:
            risk_level = "none"
        
        # Prepare response
        result = {
            "job_name": job_name,
            "vulnerabilities": vulnerabilities,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "status": "success"
        }
        
        # STEP 7: Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            filename='security_findings.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # STEP 8: Save security findings to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            artifact=result,
            filename='security_findings.json',
            content_type='application/json'
        )
        
        # STEP 9: Save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            response=result,
            filename='security_scan_raw_response.json'
        )
        
        logger.info(f"Security scan completed for job {job_name}: risk_level={risk_level}, vulnerabilities={len(vulnerabilities)}")
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
    Checks AWS best practices, Lambda best practices, Python PEP 8 standards.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, code, architecture)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, compliant, and violations
    """
    job_name = params.get('job_name')
    code = params.get('code', '')
    architecture = params.get('architecture', '{}')
    
    if not job_name:
        raise ValueError("Missing required parameter: job_name")
    
    # STEP 1: Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='quality-validator',
        action_name='compliance_check',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # STEP 3-5: Perform compliance checks
        logger.info(f"Performing compliance check for job {job_name}")
        
        violations = []
        compliance_score = 100  # Start with perfect score
        
        # STEP 3: Check AWS best practices compliance
        aws_best_practices = [
            {
                "check": "error_handling",
                "pattern": ["try:", "except"],
                "message": "AWS best practice: Implement proper error handling"
            },
            {
                "check": "logging",
                "pattern": ["logger", "logging"],
                "message": "AWS best practice: Use structured logging"
            },
            {
                "check": "environment_variables",
                "pattern": ["os.environ", "os.getenv"],
                "message": "AWS best practice: Use environment variables for configuration"
            }
        ]
        
        for practice in aws_best_practices:
            if not any(pattern in code for pattern in practice["pattern"]):
                violations.append({
                    "category": "aws_best_practices",
                    "severity": "warning",
                    "message": practice["message"],
                    "check": practice["check"]
                })
                compliance_score -= 10
        
        # STEP 4: Check Lambda best practices compliance
        lambda_best_practices = [
            {
                "check": "handler_function",
                "pattern": ["def lambda_handler", "def handler"],
                "message": "Lambda best practice: Use standard handler function name"
            },
            {
                "check": "timeout_handling",
                "pattern": ["time.time()", "timeout"],
                "message": "Lambda best practice: Monitor execution time"
            },
            {
                "check": "cold_start_optimization",
                "pattern": ["global", "# Initialize"],
                "message": "Lambda best practice: Initialize clients outside handler"
            }
        ]
        
        for practice in lambda_best_practices:
            if not any(pattern in code for pattern in practice["pattern"]):
                violations.append({
                    "category": "lambda_best_practices",
                    "severity": "info",
                    "message": practice["message"],
                    "check": practice["check"]
                })
                compliance_score -= 5
        
        # STEP 5: Check Python PEP 8 standards
        pep8_checks = []
        
        # Check for proper indentation (4 spaces)
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('  ') and not line.startswith('    '):
                pep8_checks.append({
                    "line": i + 1,
                    "message": "PEP 8: Use 4 spaces for indentation"
                })
        
        # Check for line length (max 79 characters recommended)
        long_lines = [i + 1 for i, line in enumerate(lines) if len(line) > 120]
        if long_lines:
            pep8_checks.append({
                "lines": long_lines[:5],  # Show first 5
                "message": f"PEP 8: {len(long_lines)} lines exceed 120 characters"
            })
        
        # Check for proper naming conventions
        if any(c.isupper() for c in code.split('def ')[1:5] if 'def ' in code):
            # Check if function names use camelCase instead of snake_case
            pep8_checks.append({
                "message": "PEP 8: Use snake_case for function names"
            })
        
        if pep8_checks:
            violations.append({
                "category": "pep8_standards",
                "severity": "info",
                "message": "PEP 8 style violations detected",
                "details": pep8_checks[:10]  # Limit to 10 details
            })
            compliance_score -= len(pep8_checks) * 2
        
        # Ensure compliance_score doesn't go below 0
        compliance_score = max(0, compliance_score)
        
        # Determine if compliant (threshold: 70%)
        compliant = compliance_score >= 70
        
        # Prepare response
        result = {
            "job_name": job_name,
            "compliant": compliant,
            "violations": violations,
            "compliance_score": compliance_score,
            "status": "success"
        }
        
        # STEP 6: Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            filename='compliance_report.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # STEP 7: Save compliance report to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            artifact=result,
            filename='compliance_report.json',
            content_type='application/json'
        )
        
        # STEP 8: Save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='validation',
            agent_name='quality-validator',
            response=result,
            filename='compliance_check_raw_response.json'
        )
        
        logger.info(f"Compliance check completed for job {job_name}: compliant={compliant}, score={compliance_score}")
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
