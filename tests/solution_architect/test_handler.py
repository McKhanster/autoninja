#!/usr/bin/env python3
"""
Unit tests for Solution Architect Lambda handler
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
spec = importlib.util.spec_from_file_location("handler", "lambda/solution-architect/handler.py")
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


def create_test_event(api_path: str, job_name: str, params: dict) -> dict:
    """
    Create a test Bedrock Agent event.
    
    Args:
        api_path: API path (e.g., '/design-architecture')
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
            "name": "solution-architect",
            "id": "TEST123",
            "alias": "TEST",
            "version": "DRAFT"
        },
        "inputText": f"Test request for {api_path}",
        "sessionId": f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "actionGroup": "solution-architect-actions",
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


def test_design_architecture():
    """Test the design_architecture action"""
    print("\n" + "="*80)
    print("TEST: Design Architecture")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    requirements = {
        "agent_purpose": "Friend agent for companionship",
        "capabilities": ["Natural conversation", "Emotional support"],
        "data_needs": ["User preferences", "Conversation history"],
        "lambda_requirements": {
            "runtime": "python3.12",
            "memory": 512,
            "timeout": 60,
            "actions": [
                {"name": "chat", "description": "Handle chat"}
            ]
        },
        "architecture_requirements": {
            "compute": {"lambda_functions": 1, "memory_mb": 512, "timeout_seconds": 60},
            "storage": {"dynamodb_tables": 1, "s3_buckets": 0},
            "bedrock": {
                "agent_count": 1,
                "foundation_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                "action_groups": 1
            }
        }
    }
    
    event = create_test_event(
        api_path='/design-architecture',
        job_name=job_name,
        params={
            'requirements': requirements,
            'code_file_references': 'lambda_handler.py, agent_config.json'
        }
    )
    
    # Mock context
    class Context:
        function_name = "test-solution-architect"
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
        assert 'architecture' in body
        assert 'diagram' in body
        assert 'status' in body
        assert body['status'] == 'success'
        
        # Verify architecture structure
        architecture = body['architecture']
        assert 'services' in architecture
        assert 'resources' in architecture
        assert 'iam_policies' in architecture
        assert 'integration_points' in architecture
        
        # Verify services include expected AWS services
        services = architecture['services']
        assert 'AWS Bedrock Agent' in services
        assert 'AWS Lambda' in services
        
        # Verify resources
        resources = architecture['resources']
        assert 'bedrock_agent' in resources
        assert 'lambda_functions' in resources
        
        print("\n✅ TEST PASSED: design_architecture")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_select_services():
    """Test the select_services action"""
    print("\n" + "="*80)
    print("TEST: Select Services")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    requirements = {
        "agent_purpose": "Customer support agent",
        "capabilities": ["Answer questions", "Create tickets"],
        "data_needs": ["Ticket storage"],
        "integrations": ["Zendesk API"]
    }
    
    event = create_test_event(
        api_path='/select-services',
        job_name=job_name,
        params={'requirements': requirements}
    )
    
    class Context:
        function_name = "test-solution-architect"
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
        assert 'services' in body
        assert 'rationale' in body
        assert 'status' in body
        assert body['status'] == 'success'
        
        print("\n✅ TEST PASSED: select_services")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_generate_iac():
    """Test the generate_iac action"""
    print("\n" + "="*80)
    print("TEST: Generate IaC")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    architecture = {
        "services": ["AWS Bedrock Agent", "AWS Lambda"],
        "resources": {
            "bedrock_agent": {
                "name": "test-agent",
                "foundation_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
            },
            "lambda_functions": [
                {"name": "test-lambda", "runtime": "python3.12"}
            ]
        }
    }
    
    event = create_test_event(
        api_path='/generate-iac',
        job_name=job_name,
        params={'architecture': architecture}
    )
    
    class Context:
        function_name = "test-solution-architect"
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
        
        print("\nResponse Body (truncated):")
        print(json.dumps({k: v[:200] if isinstance(v, str) and len(v) > 200 else v 
                         for k, v in body.items()}, indent=2))
        
        # Verify response contains expected fields
        assert 'job_name' in body
        assert 'cloudformation_template' in body
        assert 'status' in body
        assert body['status'] == 'success'
        
        # Verify CloudFormation template contains key elements
        template = body['cloudformation_template']
        assert 'AWSTemplateFormatVersion' in template
        assert 'Resources' in template
        assert 'LambdaExecutionRole' in template
        
        print("\n✅ TEST PASSED: generate_iac")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("SOLUTION ARCHITECT LAMBDA HANDLER UNIT TESTS")
    print("="*80)
    
    results = []
    
    # Test 1: Design Architecture
    results.append(("Design Architecture", test_design_architecture()))
    
    # Test 2: Select Services
    results.append(("Select Services", test_select_services()))
    
    # Test 3: Generate IaC
    results.append(("Generate IaC", test_generate_iac()))
    
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
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
