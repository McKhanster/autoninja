"""
Test Requirements Analyst with Bedrock inference
"""
import json
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))

# Set environment variables
os.environ['DYNAMODB_TABLE_NAME'] = os.environ.get('DYNAMODB_TABLE_NAME', 'autoninja-inference-records')
os.environ['S3_BUCKET_NAME'] = os.environ.get('S3_BUCKET_NAME', f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID', '784327326356')}")
os.environ['AWS_REGION'] = os.environ.get('AWS_REGION', 'us-east-2')


def test_bedrock_inference():
    """Test requirements extraction with Bedrock"""
    print("\n" + "="*80)
    print("BEDROCK INFERENCE TEST: Requirements Extraction")
    print("="*80)
    
    # Test with a simple request first
    user_request = "I would like a friend agent that can have conversations and remember user preferences"
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"\nJob Name: {job_name}")
    print(f"User Request: {user_request}")
    print(f"\nCalling Bedrock to extract requirements...")
    print("-" * 80)
    
    try:
        from handler import extract_requirements_with_bedrock
        
        requirements = extract_requirements_with_bedrock(user_request, job_name)
        
        print(f"\n✅ SUCCESS! Requirements extracted via Bedrock")
        print("\n" + "="*80)
        print("EXTRACTED REQUIREMENTS")
        print("="*80)
        
        print(f"\n📋 Agent Purpose:")
        print(f"   {requirements.get('agent_purpose', 'N/A')}")
        
        print(f"\n🎯 Capabilities ({len(requirements.get('capabilities', []))}):")
        for i, cap in enumerate(requirements.get('capabilities', [])[:5], 1):
            print(f"   {i}. {cap}")
        if len(requirements.get('capabilities', [])) > 5:
            print(f"   ... and {len(requirements.get('capabilities', [])) - 5} more")
        
        print(f"\n💬 Interactions ({len(requirements.get('interactions', []))}):")
        for i, interaction in enumerate(requirements.get('interactions', [])[:3], 1):
            print(f"   {i}. {interaction}")
        
        print(f"\n💾 Data Needs ({len(requirements.get('data_needs', []))}):")
        for i, need in enumerate(requirements.get('data_needs', [])[:3], 1):
            print(f"   {i}. {need}")
        
        print(f"\n🔌 Integrations ({len(requirements.get('integrations', []))}):")
        for i, integration in enumerate(requirements.get('integrations', [])[:3], 1):
            print(f"   {i}. {integration}")
        
        print(f"\n📝 System Prompts:")
        system_prompts = requirements.get('system_prompts', 'N/A')
        if len(system_prompts) > 200:
            print(f"   {system_prompts[:200]}...")
        else:
            print(f"   {system_prompts}")
        
        print(f"\n⚙️  Lambda Requirements:")
        lambda_reqs = requirements.get('lambda_requirements', {})
        print(f"   Runtime: {lambda_reqs.get('runtime', 'N/A')}")
        print(f"   Memory: {lambda_reqs.get('memory', 'N/A')} MB")
        print(f"   Timeout: {lambda_reqs.get('timeout', 'N/A')} seconds")
        print(f"   Actions: {len(lambda_reqs.get('actions', []))}")
        
        print(f"\n🏗️  Architecture Requirements:")
        arch_reqs = requirements.get('architecture_requirements', {})
        compute = arch_reqs.get('compute', {})
        storage = arch_reqs.get('storage', {})
        bedrock = arch_reqs.get('bedrock', {})
        print(f"   Lambda Functions: {compute.get('lambda_functions', 'N/A')}")
        print(f"   DynamoDB Tables: {storage.get('dynamodb_tables', 'N/A')}")
        print(f"   S3 Buckets: {storage.get('s3_buckets', 'N/A')}")
        print(f"   Foundation Model: {bedrock.get('foundation_model', 'N/A')}")
        
        print(f"\n🚀 Deployment Requirements:")
        deploy_reqs = requirements.get('deployment_requirements', {})
        print(f"   Method: {deploy_reqs.get('deployment_method', 'N/A')}")
        print(f"   Region: {deploy_reqs.get('region', 'N/A')}")
        
        print(f"\n📊 Complexity: {requirements.get('complexity', 'N/A')}")
        
        print(f"\n📌 Additional Notes:")
        notes = requirements.get('additional_notes', 'N/A')
        if len(notes) > 200:
            print(f"   {notes[:200]}...")
        else:
            print(f"   {notes}")
        
        print("\n" + "="*80)
        print("Full JSON Response:")
        print("="*80)
        print(json.dumps(requirements, indent=2))
        
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_full_lambda_with_bedrock():
    """Test full Lambda handler with Bedrock"""
    print("\n" + "="*80)
    print("FULL LAMBDA TEST: Extract Requirements with Bedrock")
    print("="*80)
    
    job_name = f"job-friend-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    user_request = "I want a friendly AI agent that can chat with users, remember their preferences, and provide personalized recommendations"
    
    event = {
        'messageVersion': '1.0',
        'agent': {
            'name': 'requirements-analyst',
            'id': 'TEST123',
            'alias': 'TEST',
            'version': '1'
        },
        'inputText': user_request,
        'sessionId': f'test-session-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'actionGroup': 'requirements-analyst-actions',
        'apiPath': '/extract-requirements',
        'httpMethod': 'POST',
        'requestBody': {
            'content': {
                'application/json': {
                    'properties': [
                        {'name': 'job_name', 'type': 'string', 'value': job_name},
                        {'name': 'user_request', 'type': 'string', 'value': user_request}
                    ]
                }
            }
        }
    }
    
    class MockContext:
        request_id = 'test-request-123'
        function_name = 'requirements-analyst-lambda'
        function_version = '1'
        memory_limit_in_mb = 512
        
        def get_remaining_time_in_millis(self):
            return 60000
    
    print(f"\nJob Name: {job_name}")
    print(f"User Request: {user_request}")
    print(f"\nInvoking Lambda handler...")
    print("-" * 80)
    
    try:
        from handler import lambda_handler
        
        response = lambda_handler(event, MockContext())
        
        print(f"\n✅ Lambda invocation successful!")
        print(f"HTTP Status: {response['response']['httpStatusCode']}")
        
        if response['response']['httpStatusCode'] == 200:
            body = json.loads(response['response']['responseBody']['application/json']['body'])
            
            print(f"\n📦 Response Summary:")
            print(f"   Job Name: {body.get('job_name')}")
            print(f"   Status: {body.get('status')}")
            
            if 'requirements' in body:
                reqs = body['requirements']
                print(f"\n   Requirements extracted:")
                print(f"   - Purpose: {reqs.get('agent_purpose', 'N/A')[:60]}...")
                print(f"   - Capabilities: {len(reqs.get('capabilities', []))} items")
                print(f"   - Complexity: {reqs.get('complexity', 'N/A')}")
            
            print(f"\n✅ Test PASSED - Requirements extracted successfully via Bedrock!")
            return True
        else:
            error_body = json.loads(response['response']['responseBody']['application/json']['body'])
            print(f"\n❌ Lambda returned error: {error_body.get('error')}")
            return False
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "="*80)
    print("REQUIREMENTS ANALYST - BEDROCK INFERENCE TEST SUITE")
    print("="*80)
    print(f"\nEnvironment:")
    print(f"  - AWS Region: {os.environ.get('AWS_REGION')}")
    print(f"  - AWS Profile: {os.environ.get('AWS_PROFILE', 'default')}")
    
    # Test 1: Direct Bedrock call
    result1 = test_bedrock_inference()
    
    # Test 2: Full Lambda handler (only if DynamoDB/S3 exist)
    print("\n\nNote: Full Lambda test requires DynamoDB table and S3 bucket to exist.")
    print("Skipping full Lambda test for now. Run after infrastructure is deployed.")
    result2 = True  # Skip for now
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"  1. Bedrock Inference: {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"  2. Full Lambda Handler: ⏭️  SKIPPED (requires infrastructure)")
    print("="*80)
    
    sys.exit(0 if result1 else 1)
