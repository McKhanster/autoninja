#!/usr/bin/env python3
"""
Test script to invoke the Code Generator Bedrock Agent
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

# Configuration - Update these after deploying the Code Generator agent
AGENT_ID = "JYHLGG522G"  # Code Generator Agent ID
AGENT_ALIAS_ID = "TSTALIASID"  # test alias pointing to DRAFT
REGION = "us-east-2"

def invoke_agent(prompt: str, session_id: str = None):
    """
    Invoke the Code Generator Bedrock Agent
    
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


def test_generate_lambda_code():
    """Test the generate_lambda_code action"""
    print("\n" + "="*80)
    print("TEST 1: Generate Lambda Code")
    print("="*80)
    
    # Sample requirements from Requirements Analyst
    requirements = {
        "agent_purpose": "Friend agent for companionship",
        "capabilities": ["Natural language conversation", "Emotional support"],
        "interactions": ["Text-based conversation"],
        "data_needs": ["Session state management"],
        "integrations": ["AWS Bedrock Agent runtime"],
        "system_prompts": "Be friendly and supportive",
        "lambda_requirements": {
            "runtime": "python3.12",
            "memory": 512,
            "timeout": 60,
            "environment_variables": {"LOG_LEVEL": "INFO"},
            "actions": [
                {
                    "name": "chat",
                    "description": "Handle chat interactions",
                    "parameters": ["user_input", "session_id"]
                }
            ]
        }
    }
    
    prompt = f"""Please generate Lambda function code for a friend agent with these requirements:

{json.dumps(requirements, indent=2)}

Generate production-ready Python code with error handling and logging."""
    
    result = invoke_agent(prompt)
    return result


def test_generate_agent_config():
    """Test the generate_agent_config action"""
    print("\n" + "="*80)
    print("TEST 2: Generate Agent Config")
    print("="*80)
    
    requirements = {
        "agent_purpose": "Friend agent for companionship",
        "system_prompts": "You are a friendly AI companion. Be supportive and engaging.",
        "architecture_requirements": {
            "bedrock": {
                "foundation_model": "anthropic.claude-sonnet-4-5-20250929-v1:0",
                "action_groups": 1
            }
        }
    }
    
    prompt = f"""Please generate Bedrock Agent configuration for a friend agent with these requirements:

{json.dumps(requirements, indent=2)}

Include agent name, instructions, foundation model, and action groups."""
    
    result = invoke_agent(prompt)
    return result


def test_generate_openapi_schema():
    """Test the generate_openapi_schema action"""
    print("\n" + "="*80)
    print("TEST 3: Generate OpenAPI Schema")
    print("="*80)
    
    action_group_spec = {
        "agent_name": "friend-agent",
        "actions": [
            {
                "name": "chat",
                "description": "Handle chat interactions with the user",
                "parameters": ["user_input", "session_id"]
            },
            {
                "name": "get_mood",
                "description": "Get the user's current mood",
                "parameters": ["session_id"]
            }
        ]
    }
    
    prompt = f"""Please generate an OpenAPI 3.0 schema for this action group:

{json.dumps(action_group_spec, indent=2)}

Include all endpoints, parameters, and request/response schemas."""
    
    result = invoke_agent(prompt)
    return result


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("BEDROCK AGENT TEST SUITE - Code Generator")
    print("="*80)
    
    # Check if agent ID is configured
    if AGENT_ID == "YOUR_CODE_GENERATOR_AGENT_ID":
        print("\n❌ ERROR: Please update AGENT_ID in this script with your deployed Code Generator agent ID")
        print("Deploy the Code Generator agent first, then update the AGENT_ID constant at the top of this file.")
        return 1
    
    print("\nNote: Bedrock on-demand models have strict rate limits (~1 RPM for Claude Sonnet 4.5)")
    print("Maintaining 60-second intervals between tests to avoid throttling...")
    print("This test will take approximately 3 minutes to complete.\n")
    
    # Initialize rate limiter (60 seconds between calls)
    rate_limiter = BedrockRateLimiter(min_interval_seconds=60)
    
    results = []
    
    # Test 1: Generate Lambda Code
    start_time = time.time()
    result1 = test_generate_lambda_code()
    results.append(("Generate Lambda Code", result1['success']))
    
    # Wait to maintain 60-second interval
    wait_time = rate_limiter.wait_if_needed(start_time)
    print(f"\n⏱️  Waited {wait_time:.1f} seconds to maintain rate limit")
    
    # Test 2: Generate Agent Config
    start_time = time.time()
    result2 = test_generate_agent_config()
    results.append(("Generate Agent Config", result2['success']))
    
    # Wait to maintain 60-second interval
    wait_time = rate_limiter.wait_if_needed(start_time)
    print(f"\n⏱️  Waited {wait_time:.1f} seconds to maintain rate limit")
    
    # Test 3: Generate OpenAPI Schema
    start_time = time.time()
    result3 = test_generate_openapi_schema()
    results.append(("Generate OpenAPI Schema", result3['success']))
    
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
