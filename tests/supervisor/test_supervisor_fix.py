#!/usr/bin/env python3
"""
Quick test to verify supervisor fix for empty responses
"""

import boto3
import json
import time
import os

# Configuration
SUPERVISOR_AGENT_ID = os.environ.get('SUPERVISOR_AGENT_ID', 'DAQAIWIYYE')
SUPERVISOR_ALIAS_ID = os.environ.get('SUPERVISOR_ALIAS_ID', 'PB8TEAYL1T')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')
AWS_PROFILE = os.environ.get('AWS_PROFILE', 'AdministratorAccess-784327326356')

def test_supervisor():
    """Test supervisor with simple request"""
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    bedrock_agent_runtime = session.client('bedrock-agent-runtime')
    
    session_id = f"test-fix-{int(time.time())}"
    prompt = "Build a simple hello world agent"
    
    print(f"Testing supervisor with session: {session_id}")
    print(f"Prompt: {prompt}")
    
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=SUPERVISOR_AGENT_ID,
            agentAliasId=SUPERVISOR_ALIAS_ID,
            sessionId=session_id,
            inputText=prompt,
            enableTrace=True
        )
        
        completion = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                completion += event['chunk']['bytes'].decode('utf-8')
        
        print(f"Response length: {len(completion)}")
        print(f"Response preview: {completion[:500]}...")
        
        if completion.strip():
            print("✓ SUCCESS: Got non-empty response")
            return True
        else:
            print("✗ FAILURE: Still getting empty response")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_supervisor()
    exit(0 if success else 1)