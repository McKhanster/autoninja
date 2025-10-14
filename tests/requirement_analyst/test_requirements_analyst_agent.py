#!/usr/bin/env python3
"""
Test script to invoke the Requirements Analyst Bedrock Agent
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
AGENT_ID = "TBGRRXIBMM"
AGENT_ALIAS_ID = "TSTALIASID"  # test alias pointing to DRAFT
REGION = "us-east-2"

def invoke_agent(prompt: str, session_id: str = None):
    """
    Invoke the Requirements Analyst Bedrock Agent
    
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


def test_extract_requirements():
    """Test the extract_requirements action"""
    print("\n" + "="*80)
    print("TEST 1: Extract Requirements")
    print("="*80)
    
    prompt = """I would like you to extract requirements for a friend agent. 
    
The agent should be able to:
- Have natural conversations with users
- Remember user preferences and past conversations
- Provide emotional support and companionship
- Suggest activities based on user interests

Please extract comprehensive requirements for this agent."""
    
    result = invoke_agent(prompt)
    return result


def test_analyze_complexity():
    """Test the analyze_complexity action"""
    print("\n" + "="*80)
    print("TEST 2: Analyze Complexity")
    print("="*80)
    
    prompt = """Please analyze the complexity of building an agent with these requirements:
- Natural language conversation
- User preference storage
- Emotional support capabilities
- Activity recommendations
- Integration with calendar APIs
- Multi-language support

What is the complexity level and what are the key challenges?"""
    
    result = invoke_agent(prompt)
    return result


def test_validate_requirements():
    """Test the validate_requirements action"""
    print("\n" + "="*80)
    print("TEST 3: Validate Requirements")
    print("="*80)
    
    prompt = """Please validate these requirements for completeness:

Agent Purpose: Friend agent for companionship
Capabilities: Conversation, emotional support
Interactions: Text-based chat
System Prompts: Be friendly and supportive

Are these requirements complete? What's missing?"""
    
    result = invoke_agent(prompt)
    return result


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("BEDROCK AGENT TEST SUITE - Requirements Analyst")
    print("="*80)
    print("\nNote: Bedrock on-demand models have strict rate limits (~1 RPM for Claude Sonnet 4.5)")
    print("Maintaining 60-second intervals between tests to avoid throttling...")
    print("This test will take approximately 3 minutes to complete.\n")
    
    # Initialize rate limiter (60 seconds between calls)
    rate_limiter = BedrockRateLimiter(min_interval_seconds=60)
    
    results = []
    
    # Test 1: Extract Requirements
    start_time = time.time()
    result1 = test_extract_requirements()
    results.append(("Extract Requirements", result1['success']))
    
    # Wait to maintain 60-second interval (pass start_time, not duration)
    wait_time = rate_limiter.wait_if_needed(start_time)
    print(f"\n⏱️  Waited {wait_time:.1f} seconds to maintain rate limit")
    
    # Test 2: Analyze Complexity
    start_time = time.time()
    result2 = test_analyze_complexity()
    results.append(("Analyze Complexity", result2['success']))
    
    # Wait to maintain 60-second interval (pass start_time, not duration)
    wait_time = rate_limiter.wait_if_needed(start_time)
    print(f"\n⏱️  Waited {wait_time:.1f} seconds to maintain rate limit")
    
    # Test 3: Validate Requirements
    start_time = time.time()
    result3 = test_validate_requirements()
    results.append(("Validate Requirements", result3['success']))
    
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
