#!/usr/bin/env python3
"""
Test script to invoke the Deployment Manager Bedrock Agent
"""
import boto3
from botocore.config import Config
import json
import sys
import os
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.utils.rate_limiter import BedrockRateLimiter

# Configuration - Update these after deploying the Deployment Manager agent
AGENT_ID = "D6D54EATNC"  # Deployment Manager Agent ID
AGENT_ALIAS_ID = "TSTALIASID"  # test alias pointing to DRAFT
REGION = "us-east-2"

def invoke_agent(prompt: str, session_id: str = None):
    """
    Invoke the Deployment Manager Bedrock Agent
    
    Args:
        prompt: The user prompt to send to the agent
        session_id: Optional session ID for conversation continuity
    """
    if not session_id:
        session_id = f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"\n{'='*80}")
    print(f"INVOKING BEDROCK AGENT")
    print(f"{'='*80}")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Alias ID: {AGENT_ALIAS_ID}")
    print(f"Session ID: {session_id}")
    print(f"Region: {REGION}")
    print(f"\nPrompt: {prompt}")
    print(f"{'='*80}\n")
    
    # Create Bedrock Agent Runtime client with longer timeout
    config = Config(
        read_timeout=300,
        connect_timeout=60,
        retries={'max_attempts': 3}
    )
    client = boto3.client('bedrock-agent-runtime', region_name=REGION, config=config)
    
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
                            print(f"[TRACE] Action completed with status: {action_output.get('text', 'N/A')}")
        
        print("\n" + "-" * 80)
        print(f"\n✅ Agent invocation completed successfully!")
        print(f"Total response length: {len(full_response)} characters")
        
        return {
            'success': True,
            'response': full_response,
            'session_id': session_id
        }
        
    except Exception as e:
        print(f"\n❌ Error invoking agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'session_id': session_id
        }


def test_generate_cloudformation():
    """Test the generate_cloudformation action"""
    print("\n" + "="*80)
    print("TEST 1: Generate CloudFormation")
    print("="*80)
    
    requirements = {"agent_purpose": "Friend agent"}
    code = {"handler.py": "def lambda_handler(event, context): return {'statusCode': 200}"}
    architecture = {"services": ["AWS Bedrock Agent", "AWS Lambda"]}
    
    prompt = f"""Please generate a CloudFormation template.

Job Name: job-test-cfn-20251016-001122
Requirements: {json.dumps(requirements)}
Code: {json.dumps(code)}
Architecture: {json.dumps(architecture)}
Validation Status: green light

Generate complete CloudFormation template."""
    
    result = invoke_agent(prompt)
    return result


def test_deploy_stack():
    """Test the deploy_stack action"""
    print("\n" + "="*80)
    print("TEST 2: Deploy Stack")
    print("="*80)
    
    template = "AWSTemplateFormatVersion: '2010-09-09'\\nResources:\\n  TestResource:\\n    Type: AWS::S3::Bucket"
    
    prompt = f"""Please deploy this CloudFormation stack.

Job Name: job-test-deploy-20251016-001122
CloudFormation Template: {template}
Stack Name: test-friend-agent-stack

Deploy the stack to AWS."""
    
    result = invoke_agent(prompt)
    return result


def test_configure_agent():
    """Test the configure_agent action"""
    print("\n" + "="*80)
    print("TEST 3: Configure Agent")
    print("="*80)
    
    agent_config = {"agent_name": "test-agent", "instructions": "Be helpful", "foundation_model": "claude-sonnet"}
    lambda_arns = {"actions": "arn:aws:lambda:us-east-2:123456789012:function:test"}
    
    prompt = f"""Please configure the Bedrock Agent.

Job Name: job-test-configure-20251016-001122
Agent Config: {json.dumps(agent_config)}
Lambda ARNs: {json.dumps(lambda_arns)}

Configure the agent with action groups."""
    
    result = invoke_agent(prompt)
    return result


def test_test_deployment():
    """Test the test_deployment action"""
    print("\n" + "="*80)
    print("TEST 4: Test Deployment")
    print("="*80)
    
    prompt = """Please test the deployed agent.

Job Name: job-test-testing-20251016-001122
Agent ID: AGENTID123
Alias ID: ALIASID456
Test Inputs: ["Hello", "How are you?"]

Test the deployed agent functionality."""
    
    result = invoke_agent(prompt)
    return result


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("BEDROCK AGENT TEST SUITE - Deployment Manager")
    print("="*80)
    
    # Check if agent ID is configured
    if AGENT_ID == "AGENT_ID_PLACEHOLDER":
        print("\n❌ ERROR: Please update AGENT_ID in this script with your deployed Deployment Manager agent ID")
        print("Deploy the Deployment Manager agent first, then update the AGENT_ID constant at the top of this file.")
        return 1
    
    print("\nNote: Bedrock on-demand models have strict rate limits (~1 RPM for Claude Sonnet 4.5)")
    print("Maintaining 60-second intervals between tests to avoid throttling...")
    print("This test will take approximately 3 minutes to complete.\n")
    
    # Initialize rate limiter (60 seconds between calls)
    rate_limiter = BedrockRateLimiter(min_interval_seconds=60)
    
    results = []
    
    # Test 1: Generate CloudFormation
    rate_limiter.wait_if_needed()
    print("\n⏳ Running Test 1...")
    result1 = test_generate_cloudformation()
    results.append(("Generate CloudFormation", result1['success']))
    
    # Test 2: Deploy Stack
    rate_limiter.wait_if_needed()
    print("\n⏳ Running Test 2...")
    result2 = test_deploy_stack()
    results.append(("Deploy Stack", result2['success']))
    
    # Test 3: Configure Agent
    rate_limiter.wait_if_needed()
    print("\n⏳ Running Test 3...")
    result3 = test_configure_agent()
    results.append(("Configure Agent", result3['success']))
    
    # Test 4: Test Deployment
    rate_limiter.wait_if_needed()
    print("\n⏳ Running Test 4...")
    result4 = test_test_deployment()
    results.append(("Test Deployment", result4['success']))
    
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
