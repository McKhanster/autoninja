#!/usr/bin/env python3
"""
Test script to invoke the Quality Validator Bedrock Agent end-to-end
"""
import boto3
import json
import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.utils.rate_limiter import BedrockRateLimiter

# Configuration
AGENT_ID = "HJXCE9QZIU"  # Quality Validator agent ID
AGENT_ALIAS_ID = "TIQHTBVGQW"  # production alias
REGION = "us-east-2"

# Initialize rate limiter (60 second intervals for Bedrock on-demand to avoid throttling)
rate_limiter = BedrockRateLimiter(min_interval_seconds=60)

def invoke_agent(prompt: str, session_id: str = None):
    """
    Invoke the Quality Validator Bedrock Agent
    
    Args:
        prompt: The user prompt to send to the agent
        session_id: Optional session ID for conversation continuity
    """
    if not session_id:
        session_id = f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Track operation start time for rate limiting
    operation_start = time.time()
    
    print(f"\n{'='*80}")
    print(f"INVOKING BEDROCK AGENT")
    print(f"{'='*80}")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Alias ID: {AGENT_ALIAS_ID}")
    print(f"Session ID: {session_id}")
    print(f"Region: {REGION}")
    print(f"\nPrompt: {prompt[:200]}...")
    print(f"{'='*80}\n")
    
    # Create Bedrock Agent Runtime client
    client = boto3.client('bedrock-agent-runtime', region_name=REGION)
    
    try:
        # Invoke the agent
        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=prompt
        )
        
        # Process the streaming response
        print("Agent Response:")
        print("-" * 80)
        
        full_response = ""
        event_stream = response['completion']
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)
            
            elif 'trace' in event:
                trace = event['trace']
                trace_type = trace.get('trace', {})
                
                # Print trace information for debugging
                if 'orchestrationTrace' in trace_type:
                    orch_trace = trace_type['orchestrationTrace']
                    if 'invocationInput' in orch_trace:
                        inv_input = orch_trace['invocationInput']
                        if 'actionGroupInvocationInput' in inv_input:
                            action_input = inv_input['actionGroupInvocationInput']
                            print(f"\n\n[TRACE] Invoking action: {action_input.get('actionGroupName')} - {action_input.get('apiPath')}")
                    
                    if 'observation' in orch_trace:
                        observation = orch_trace['observation']
                        if 'actionGroupInvocationOutput' in observation:
                            action_output = observation['actionGroupInvocationOutput']
                            print(f"[TRACE] Action completed")
        
        print("\n" + "-" * 80)
        print(f"\n✅ Agent invocation completed successfully!")
        print(f"Total response length: {len(full_response)} characters")
        
        # Apply rate limiting to ensure 30-second intervals
        wait_time = rate_limiter.wait_if_needed(operation_start)
        if wait_time > 0:
            print(f"⏱️  Rate limiting: waited {wait_time:.1f}s (total operation time: {time.time() - operation_start:.1f}s)")
        
        return {
            'success': True,
            'response': full_response,
            'session_id': session_id
        }
        
    except Exception as e:
        print(f"\n❌ Error invoking agent: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Still apply rate limiting even on error
        wait_time = rate_limiter.wait_if_needed(operation_start)
        if wait_time > 0:
            print(f"⏱️  Rate limiting: waited {wait_time:.1f}s after error")
        
        return {
            'success': False,
            'error': str(e),
            'session_id': session_id
        }


def test_validate_code():
    """Test the validate_code action"""
    print("\n" + "="*80)
    print("TEST 1: Validate Code")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Sample code with good quality
    code = '''
def lambda_handler(event, context):
    """Lambda handler function"""
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
'''
    
    prompt = f"""Please validate the code quality for job {job_name}.

Code to validate:
{code}

Please check for syntax errors, error handling, logging, and code structure."""
    
    result = invoke_agent(prompt)
    
    if result['success']:
        print("\n✅ TEST PASSED: validate_code")
        return True
    else:
        print("\n❌ TEST FAILED: validate_code")
        return False


def test_security_scan():
    """Test the security_scan action"""
    print("\n" + "="*80)
    print("TEST 2: Security Scan")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Sample code with security issues
    code = '''
def lambda_handler(event, context):
    # Hardcoded credential (security issue)
    api_key = "sk-1234567890abcdef"
    
    # Using eval (security issue)
    result = eval(event['expression'])
    
    return {'statusCode': 200}
'''
    
    prompt = f"""Please perform a security scan for job {job_name}.

Code to scan:
{code}

IAM policies:
{{"Statement": [{{"Effect": "Allow", "Action": "*", "Resource": "*"}}]}}

Please check for hardcoded credentials, injection vulnerabilities, and IAM permission issues."""
    
    result = invoke_agent(prompt)
    
    if result['success']:
        print("\n✅ TEST PASSED: security_scan")
        return True
    else:
        print("\n❌ TEST FAILED: security_scan")
        return False


def test_compliance_check():
    """Test the compliance_check action"""
    print("\n" + "="*80)
    print("TEST 3: Compliance Check")
    print("="*80)
    
    job_name = f"job-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Sample code with compliance issues
    code = '''
def myFunction(event, context):
  result = processData(event)
  return result
'''
    
    prompt = f"""Please check compliance for job {job_name}.

Code to check:
{code}

Please validate against AWS best practices, Lambda best practices, and Python PEP 8 standards."""
    
    result = invoke_agent(prompt)
    
    if result['success']:
        print("\n✅ TEST PASSED: compliance_check")
        return True
    else:
        print("\n❌ TEST FAILED: compliance_check")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("QUALITY VALIDATOR BEDROCK AGENT END-TO-END TESTS")
    print("="*80)
    print("Note: Rate limiter ensures 60-second intervals between invocations to avoid throttling")
    
    # Wait for agent alias to be ready
    print("\nWaiting for agent alias to be ready...")
    time.sleep(5)
    
    results = []
    
    # Test 1: Validate Code
    results.append(("Validate Code", test_validate_code()))
    # Rate limiter handles timing automatically
    
    # Test 2: Security Scan
    results.append(("Security Scan", test_security_scan()))
    # Rate limiter handles timing automatically
    
    # Test 3: Compliance Check
    results.append(("Compliance Check", test_compliance_check()))
    # Rate limiter handles timing automatically
    
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
        print("1. Verify DynamoDB records were created")
        print("2. Verify S3 artifacts were saved")
        print("3. Check CloudWatch logs for any issues")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
