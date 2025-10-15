#!/usr/bin/env python3
"""
Unit tests for Quality Validator Lambda handler
Tests the handler directly without requiring Bedrock Agent deployment
"""
import json
import sys
import os
import pytest
from datetime import datetime

# Set required environment variables before importing handler
os.environ['DYNAMODB_TABLE_NAME'] = 'autoninja-inference-records-production'
os.environ['S3_BUCKET_NAME'] = f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID', '784327326356')}-production"
os.environ['AWS_REGION'] = 'us-east-2'

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import the handler (use importlib to avoid 'lambda' keyword issue)
import importlib.util
spec = importlib.util.spec_from_file_location("handler", "lambda/quality-validator/handler.py")
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


def create_test_event(api_path: str, job_name: str, params: dict) -> dict:
    """
    Create a test Bedrock Agent event.
    
    Args:
        api_path: API path (e.g., '/validate-code')
        job_name: Job identifier
        params: Additional parameters
        
    Returns:
        Bedrock Agent event dict
    """
    properties = [
        {"name": "job_name", "type": "string", "value": job_name}
    ]
    
    # Add additional parameters
    for key, value in params.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        properties.append({"name": key, "type": "string", "value": value})
    
    return {
        "messageVersion": "1.0",
        "agent": {
            "name": "quality-validator",
            "id": "TEST123",
            "alias": "TEST",
            "version": "DRAFT"
        },
        "inputText": f"Test request for {api_path}",
        "sessionId": f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "actionGroup": "quality-validator-actions",
        "apiPath": api_path,
        "httpMethod": "POST",
        "requestBody": {
            "content": {
                "application/json": {
                    "properties": properties
                }
            }
        }
    }


def test_validate_code():
    """Test the validate_code action"""
    print("\n" + "="*80)
    print("TEST: Validate Code")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Sample code with good quality
    code = '''
def lambda_handler(event, context):
    """
    Lambda handler function
    """
    try:
        logger.info("Processing request")
        result = process_data(event)
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def process_data(event):
    """Process the event data"""
    return {"status": "success"}
'''
    
    architecture = {
        "services": ["AWS Lambda", "AWS Bedrock Agent"],
        "resources": {
            "lambda_functions": [{"name": "test-lambda"}]
        }
    }
    
    event = create_test_event(
        api_path='/validate-code',
        job_name=job_name,
        params={
            'code': code,
            'architecture': architecture
        }
    )
    
    # Mock context
    class Context:
        function_name = "test-quality-validator"
        memory_limit_in_mb = 512
        invoked_function_arn = "arn:aws:lambda:us-east-2:123456789012:function:test"
        aws_request_id = "test-request-id"
    
    try:
        response = handler.lambda_handler(event, Context())
        
        print("\nResponse:")
        print(json.dumps(response, indent=2))
        
        # Verify response structure
        assert response['messageVersion'] == '1.0'
        assert response['response']['httpStatusCode'] == 200
        
        # Parse response body
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        
        print("\nResponse Body:")
        print(json.dumps(body, indent=2))
        
        # Verify response contains expected fields
        assert 'job_name' in body
        assert 'is_valid' in body
        assert 'issues' in body
        assert 'quality_score' in body
        assert 'status' in body
        assert body['status'] == 'success'
        
        # Verify quality score is reasonable (should be high for good code)
        assert body['quality_score'] >= 50, f"Quality score too low: {body['quality_score']}"
        
        print(f"\n✅ TEST PASSED: validate_code (score: {body['quality_score']}, valid: {body['is_valid']})")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_security_scan():
    """Test the security_scan action"""
    print("\n" + "="*80)
    print("TEST: Security Scan")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Sample code with some security issues
    code = '''
def lambda_handler(event, context):
    # Hardcoded credential (security issue)
    api_key = "sk-1234567890abcdef"
    
    # Using eval (security issue)
    result = eval(event['expression'])
    
    # DynamoDB without explicit encryption mention
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('my-table')
    
    return {'statusCode': 200}
'''
    
    iam_policies = {
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "*",  # Overly permissive
                "Resource": "*"
            }
        ]
    }
    
    event = create_test_event(
        api_path='/security-scan',
        job_name=job_name,
        params={
            'code': code,
            'iam_policies': iam_policies
        }
    )
    
    class Context:
        function_name = "test-quality-validator"
        memory_limit_in_mb = 512
        invoked_function_arn = "arn:aws:lambda:us-east-2:123456789012:function:test"
        aws_request_id = "test-request-id"
    
    try:
        response = handler.lambda_handler(event, Context())
        
        print("\nResponse:")
        print(json.dumps(response, indent=2))
        
        # Verify response structure
        assert response['messageVersion'] == '1.0'
        assert response['response']['httpStatusCode'] == 200
        
        # Parse response body
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        
        print("\nResponse Body:")
        print(json.dumps(body, indent=2))
        
        # Verify response contains expected fields
        assert 'job_name' in body
        assert 'vulnerabilities' in body
        assert 'risk_level' in body
        assert 'status' in body
        assert body['status'] == 'success'
        
        # Verify vulnerabilities were detected
        assert len(body['vulnerabilities']) > 0, "Should detect security vulnerabilities"
        
        # Verify risk level is not 'none' (we have issues)
        assert body['risk_level'] != 'none', "Risk level should be elevated"
        
        print(f"\n✅ TEST PASSED: security_scan (risk: {body['risk_level']}, vulnerabilities: {len(body['vulnerabilities'])})")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_compliance_check():
    """Test the compliance_check action"""
    print("\n" + "="*80)
    print("TEST: Compliance Check")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Sample code with compliance issues
    code = '''
def myFunction(event, context):
  result = processData(event)
  return result

def processData(event):
  return {"status": "ok"}
'''
    
    architecture = {
        "services": ["AWS Lambda"],
        "resources": {
            "lambda_functions": [{"name": "test-lambda"}]
        }
    }
    
    event = create_test_event(
        api_path='/compliance-check',
        job_name=job_name,
        params={
            'code': code,
            'architecture': architecture
        }
    )
    
    class Context:
        function_name = "test-quality-validator"
        memory_limit_in_mb = 512
        invoked_function_arn = "arn:aws:lambda:us-east-2:123456789012:function:test"
        aws_request_id = "test-request-id"
    
    try:
        response = handler.lambda_handler(event, Context())
        
        print("\nResponse:")
        print(json.dumps(response, indent=2))
        
        # Verify response structure
        assert response['messageVersion'] == '1.0'
        assert response['response']['httpStatusCode'] == 200
        
        # Parse response body
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        
        print("\nResponse Body:")
        print(json.dumps(body, indent=2))
        
        # Verify response contains expected fields
        assert 'job_name' in body
        assert 'compliant' in body
        assert 'violations' in body
        assert 'compliance_score' in body
        assert 'status' in body
        assert body['status'] == 'success'
        
        # Verify violations were detected (code has issues)
        assert len(body['violations']) > 0, "Should detect compliance violations"
        
        print(f"\n✅ TEST PASSED: compliance_check (compliant: {body['compliant']}, score: {body['compliance_score']})")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("QUALITY VALIDATOR LAMBDA HANDLER UNIT TESTS")
    print("="*80)
    
    results = []
    
    # Test 1: Validate Code
    results.append(("Validate Code", test_validate_code()))
    
    # Test 2: Security Scan
    results.append(("Security Scan", test_security_scan()))
    
    # Test 3: Compliance Check
    results.append(("Compliance Check", test_compliance_check()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {name}: {status}")
    print("="*80)
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nNext steps:")
        print("1. Verify DynamoDB records with:")
        print("   aws dynamodb scan --table-name autoninja-inference-records-production \\")
        print("     --filter-expression \"agent_name = :agent AND begins_with(job_name, :job)\" \\")
        print("     --expression-attribute-values '{\":agent\":{\"S\":\"quality-validator\"}, \":job\":{\"S\":\"job-test-\"}}' \\")
        print("     --region us-east-2 --query 'Count'")
        print("\n2. Verify S3 artifacts were saved")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
