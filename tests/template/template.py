#!/usr/bin/env python3
"""
Test script to invoke the {{AGENT_TITLE}} Bedrock Agent
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

# Configuration - Update these after deploying the {{AGENT_TITLE}} agent
AGENT_ID = "{{AGENT_ID}}"  # {{AGENT_TITLE}} Agent ID
AGENT_ALIAS_ID = "{{AGENT_ALIAS_ID}}"  # test alias pointing to DRAFT
REGION = "us-east-2"

def invoke_agent(prompt: str, session_id: str = None):
    """
    Invoke the {{AGENT_TITLE}} Bedrock Agent
    
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


# {{TEST_FUNCTIONS}}


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("BEDROCK AGENT TEST SUITE - {{AGENT_TITLE}}")
    print("="*80)
    
    # Check if agent ID is configured
    if AGENT_ID == "{{AGENT_ID}}":
        print("\n❌ ERROR: Please update AGENT_ID in this script with your deployed {{AGENT_TITLE}} agent ID")
        print("Deploy the {{AGENT_TITLE}} agent first, then update the AGENT_ID constant at the top of this file.")
        return 1
    
    print("\nNote: Bedrock on-demand models have strict rate limits (~1 RPM for Claude Sonnet 4.5)")
    print("Maintaining 60-second intervals between tests to avoid throttling...")
    print("This test will take approximately 3 minutes to complete.\n")
    
    # Initialize rate limiter (60 seconds between calls)
    rate_limiter = BedrockRateLimiter(min_interval_seconds=60)
    
    results = []
    
# {{TEST_EXECUTION}}
    
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
