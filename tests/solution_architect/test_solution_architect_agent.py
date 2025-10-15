#!/usr/bin/env python3
"""
Test script to invoke the Solution Architect Bedrock Agent
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
AGENT_ID = "XXXXXXXXXX"  # TODO: Update with actual Solution Architect agent ID
AGENT_ALIAS_ID = "TSTALIASID"  # test alias pointing to DRAFT
REGION = "us-east-2"

def invoke_agent(prompt: str, session_id: str = None):
    """
    Invoke the Solution Architect Bedrock Agent
    
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
                            print(f"[TRACE] Action completed with status: {action_output.get('text', 'N/A')[:100]}")
        
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


def test_design_architecture():
    """Test the design_architecture action"""
    print("\n" + "="*80)
    print("TEST 1: Design Architecture")
    print("="*80)
    
    # Sample requirements JSON
    requirements = {
        "agent_purpose": "Friend agent for companionship and emotional support",
        "capabilities": ["Natural language conversation", "Emotional support", "Activity recommendations"],
        "data_needs": ["User preferences storage", "Conversation history"],
        "lambda_requirements": {
            "runtime": "python3.12",
            "memory": 512,
            "timeout": 60,
            "actions": [
                {"name": "chat", "description": "Handle chat interactions"},
                {"name": "get_preferences", "description": "Retrieve user preferences"}
            ]
        },
        "architecture_requirements": {
            "compute": {"lambda_functions": 1, "memory_mb": 512, "timeout_seconds": 60},
            "storage": {"dynamodb_tables": 1, "s3_buckets": 0},
            "bedrock": {"agent_count": 1, "foundation_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "action_groups": 1}
        }
    }
    
    prompt = f"""Please design the AWS architecture for this agent.

Job Name: job-friend-test-{datetime.now().strftime('%Y%m%d%H%M%S')}

Requirements:
{json.dumps(requirements, indent=2)}

Code File References: (code files from Code Generator will be available in S3)

Please design a complete AWS architecture including all necessary services, resources, and IAM policies."""
    
    result = invoke_agent(prompt)
    return result


def test_select_services():
    """Test the select_services action"""
    print("\n" + "="*80)
    print("TEST 2: Select Services")
    print("="*80)
    
    requirements = {
        "agent_purpose": "Customer support agent",
        "capabilities": ["Answer questions", "Create tickets", "Search knowledge base"],
        "data_needs": ["Ticket storage", "Knowledge base"],
        "integrations": ["Zendesk API", "Slack API"]
    }
    
    prompt = f"""Please select appropriate AWS services for this agent.

Job Name: job-support-test-{datetime.now().strftime('%Y%m%d%H%M%S')}

Requirements:
{json.dumps(requirements, indent=2)}

What AWS services should we use and why?"""
    
    result = invoke_agent(prompt)
    return result


def test_generate_iac():
    """Test the generate_iac action"""
    print("\n" + "="*80)
    print("TEST 3: Generate Infrastructure as Code")
    print("="*80)
    
    architecture = {
        "services": ["AWS Bedrock Agent", "AWS Lambda", "Amazon DynamoDB"],
        "resources": {
            "bedrock_agent": {
                "name": "test-agent",
                "foundation_model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                "action_groups": 1
            },
            "lambda_functions": [
                {"name": "test-lambda", "runtime": "python3.12", "memory": 512, "timeout": 60}
            ],
            "dynamodb_tables": [
                {"name": "test-table", "partition_key": "id", "sort_key": "timestamp"}
            ]
        }
    }
    
    prompt = f"""Please generate CloudFormation template for this architecture.

Job Name: job-iac-test-{datetime.now().strftime('%Y%m%d%H%M%S')}

Architecture:
{json.dumps(architecture, indent=2)}

Generate a complete CloudFormation template."""
    
    result = invoke_agent(prompt)
    return result


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("BEDROCK AGENT TEST SUITE - Solution Architect")
    print("="*80)
    print("\nNote: Bedrock on-demand models have strict rate limits (~1 RPM for Claude Sonnet 4.5)")
    print("Maintaining 60-second intervals between tests to avoid throttling...")
    print("This test will take approximately 3 minutes to complete.\n")
    
    # Initialize rate limiter (60 seconds between calls)
    rate_limiter = BedrockRateLimiter(min_interval_seconds=60)
    
    results = []
    
    # Test 1: Design Architecture
    start_time = time.time()
    result1 = test_design_architecture()
    results.append(("Design Architecture", result1['success']))
    
    # Wait to maintain 60-second interval
    wait_time = rate_limiter.wait_if_needed(start_time)
    print(f"\n⏱️  Waited {wait_time:.1f} seconds to maintain rate limit")
    
    # Test 2: Select Services
    start_time = time.time()
    result2 = test_select_services()
    results.append(("Select Services", result2['success']))
    
    # Wait to maintain 60-second interval
    wait_time = rate_limiter.wait_if_needed(start_time)
    print(f"\n⏱️  Waited {wait_time:.1f} seconds to maintain rate limit")
    
    # Test 3: Generate IaC
    start_time = time.time()
    result3 = test_generate_iac()
    results.append(("Generate IaC", result3['success']))
    
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
