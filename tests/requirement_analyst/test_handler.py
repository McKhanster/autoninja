"""
Integration test for Requirements Analyst Lambda handler
Tests the Lambda function with actual AWS resources (DynamoDB, S3)
"""
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import handler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))

# Set environment variables for testing
os.environ['DYNAMODB_TABLE_NAME'] = os.environ.get('DYNAMODB_TABLE_NAME', 'autoninja-inference-records')
os.environ['S3_BUCKET_NAME'] = os.environ.get('S3_BUCKET_NAME', f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID', '784327326356')}")
os.environ['AWS_REGION'] = os.environ.get('AWS_REGION', 'us-east-2')


def create_test_event(api_path: str, job_name: str, **params) -> dict:
    """Create a test Bedrock Agent event"""
    properties = [
        {'name': 'job_name', 'type': 'string', 'value': job_name}
    ]
    
    # Add additional parameters
    for key, value in params.items():
        if isinstance(value, dict):
            properties.append({'name': key, 'type': 'object', 'value': json.dumps(value)})
        else:
            properties.append({'name': key, 'type': 'string', 'value': str(value)})
    
    return {
        'messageVersion': '1.0',
        'agent': {
            'name': 'requirements-analyst',
            'id': 'TEST123',
            'alias': 'TEST',
            'version': '1'
        },
        'inputText': f'Test request for {api_path}',
        'sessionId': f'test-session-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'actionGroup': 'requirements-analyst-actions',
        'apiPath': api_path,
        'httpMethod': 'POST',
        'requestBody': {
            'content': {
                'application/json': {
                    'properties': properties
                }
            }
        }
    }


class MockContext:
    """Mock Lambda context"""
    request_id = 'test-request-123'
    function_name = 'requirements-analyst-lambda'
    function_version = '1'
    memory_limit_in_mb = 512
    
    def get_remaining_time_in_millis(self):
        return 30000


def test_extract_requirements():
    """Test extract_requirements action"""
    print("\n" + "="*80)
    print("TEST 1: Extract Requirements")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    user_request = "I would like a friend agent that can have conversations and remember user preferences"
    
    event = create_test_event(
        '/extract-requirements',
        job_name,
        user_request=user_request
    )
    
    print(f"\nJob Name: {job_name}")
    print(f"User Request: {user_request}")
    print(f"\nInvoking Lambda function...")
    
    try:
        from handler import lambda_handler
        response = lambda_handler(event, MockContext())
        
        print(f"\n✅ SUCCESS!")
        print(f"HTTP Status: {response['response']['httpStatusCode']}")
        
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        print(f"\nResponse Summary:")
        print(f"  - Job Name: {body.get('job_name')}")
        print(f"  - Status: {body.get('status')}")
        
        if 'requirements' in body:
            reqs = body['requirements']
            print(f"\nExtracted Requirements:")
            print(f"  - Agent Purpose: {reqs.get('agent_purpose', 'N/A')[:80]}...")
            print(f"  - Capabilities: {len(reqs.get('capabilities', []))} items")
            print(f"  - Interactions: {len(reqs.get('interactions', []))} items")
            print(f"  - Data Needs: {len(reqs.get('data_needs', []))} items")
            print(f"  - Complexity: {reqs.get('complexity', 'N/A')}")
        
        return body
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_analyze_complexity(requirements: dict = None):
    """Test analyze_complexity action"""
    print("\n" + "="*80)
    print("TEST 2: Analyze Complexity")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    if not requirements:
        requirements = {
            "agent_purpose": "Test agent",
            "capabilities": ["capability1", "capability2"],
            "interactions": ["interaction1"],
            "data_needs": ["data1"],
            "integrations": ["integration1"],
            "system_prompts": "Test prompts",
            "lambda_requirements": {"actions": [{"name": "test"}]},
            "architecture_requirements": {},
            "deployment_requirements": {}
        }
    
    event = create_test_event(
        '/analyze-complexity',
        job_name,
        requirements=requirements
    )
    
    print(f"\nJob Name: {job_name}")
    print(f"Analyzing requirements with {len(requirements.get('capabilities', []))} capabilities")
    print(f"\nInvoking Lambda function...")
    
    try:
        from handler import lambda_handler
        response = lambda_handler(event, MockContext())
        
        print(f"\n✅ SUCCESS!")
        print(f"HTTP Status: {response['response']['httpStatusCode']}")
        
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        print(f"\nComplexity Analysis:")
        print(f"  - Complexity Score: {body.get('complexity_score')}")
        
        if 'assessment' in body:
            assessment = body['assessment']
            print(f"  - Estimated Effort: {assessment.get('estimated_effort')}")
            print(f"  - Key Challenges: {len(assessment.get('key_challenges', []))} items")
            print(f"  - Recommended Approach: {assessment.get('recommended_approach', 'N/A')[:80]}...")
        
        return body
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_validate_requirements(requirements: dict = None):
    """Test validate_requirements action"""
    print("\n" + "="*80)
    print("TEST 3: Validate Requirements")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    if not requirements:
        requirements = {
            "agent_purpose": "Test agent",
            "capabilities": ["capability1"],
            "interactions": ["interaction1"],
            "system_prompts": "Test prompts for the agent",
            "lambda_requirements": {"runtime": "python3.12", "actions": [{"name": "test"}]},
            "architecture_requirements": {"bedrock": {}, "iam": {}},
            "deployment_requirements": {"deployment_method": "cloudformation"}
        }
    
    event = create_test_event(
        '/validate-requirements',
        job_name,
        requirements=requirements
    )
    
    print(f"\nJob Name: {job_name}")
    print(f"Validating requirements...")
    print(f"\nInvoking Lambda function...")
    
    try:
        from handler import lambda_handler
        response = lambda_handler(event, MockContext())
        
        print(f"\n✅ SUCCESS!")
        print(f"HTTP Status: {response['response']['httpStatusCode']}")
        
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        print(f"\nValidation Results:")
        print(f"  - Is Valid: {body.get('is_valid')}")
        print(f"  - Missing Items: {len(body.get('missing_items', []))} items")
        
        if body.get('missing_items'):
            print(f"\n  Missing Items:")
            for item in body['missing_items'][:5]:
                print(f"    - {item}")
        
        if body.get('recommendations'):
            print(f"\n  Recommendations:")
            for rec in body['recommendations'][:3]:
                print(f"    - {rec}")
        
        return body
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "="*80)
    print("REQUIREMENTS ANALYST LAMBDA - INTEGRATION TEST SUITE")
    print("="*80)
    print(f"\nEnvironment:")
    print(f"  - DynamoDB Table: {os.environ.get('DYNAMODB_TABLE_NAME')}")
    print(f"  - S3 Bucket: {os.environ.get('S3_BUCKET_NAME')}")
    print(f"  - AWS Region: {os.environ.get('AWS_REGION')}")
    print(f"  - AWS Profile: {os.environ.get('AWS_PROFILE', 'default')}")
    
    # Test 1: Extract Requirements
    result1 = test_extract_requirements()
    
    # Test 2: Analyze Complexity (using requirements from test 1 if available)
    requirements = result1.get('requirements') if result1 else None
    result2 = test_analyze_complexity(requirements)
    
    # Test 3: Validate Requirements (using requirements from test 1 if available)
    result3 = test_validate_requirements(requirements)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"  1. Extract Requirements: {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"  2. Analyze Complexity: {'✅ PASSED' if result2 else '❌ FAILED'}")
    print(f"  3. Validate Requirements: {'✅ PASSED' if result3 else '❌ FAILED'}")
    print("="*80)
    
    all_passed = all([result1, result2, result3])
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Check logs above for details")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
