#!/usr/bin/env python3
"""
Test script for AutoNinja Supervisor Agent
"""
import boto3
import json
import uuid
import time

def test_supervisor_agent():
    """Test the supervisor agent invocation"""
    
    # Agent details from deployment
    agent_id = "9KW7MIXTF9"
    agent_alias_id = "OOML66ARUI"
    region = "us-east-2"
    
    # Create bedrock agent runtime client
    client = boto3.client('bedrock-agent-runtime', region_name=region)
    
    # Generate unique session ID
    session_id = f"test-session-{int(time.time())}"
    
    print(f"Testing Supervisor Agent:")
    print(f"  Agent ID: {agent_id}")
    print(f"  Alias ID: {agent_alias_id}")
    print(f"  Session ID: {session_id}")
    print(f"  Region: {region}")
    print()
    
    try:
        # Test input
        input_text = "Build a simple friend agent for emotional support"
        
        print(f"Input: {input_text}")
        print("Invoking agent...")
        print()
        
        # Invoke the agent
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text,
            enableTrace=True
        )
        
        # Process the streaming response
        event_stream = response['completion']
        
        print("Response:")
        print("-" * 50)
        
        full_response = ""
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    print(chunk_text, end='', flush=True)
                    full_response += chunk_text
            
            elif 'trace' in event:
                trace = event['trace']
                if 'orchestrationTrace' in trace:
                    orch_trace = trace['orchestrationTrace']
                    if 'invocationInput' in orch_trace:
                        print(f"\n[TRACE] Invocation Input: {orch_trace['invocationInput'].get('text', '')}")
                    elif 'observation' in orch_trace:
                        print(f"\n[TRACE] Observation: {orch_trace['observation'].get('text', '')}")
                    elif 'rationale' in orch_trace:
                        print(f"\n[TRACE] Rationale: {orch_trace['rationale'].get('text', '')}")
        
        print()
        print("-" * 50)
        print(f"✅ Agent invocation completed successfully!")
        print(f"Full response length: {len(full_response)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Error invoking agent: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_supervisor_agent()
    exit(0 if success else 1)