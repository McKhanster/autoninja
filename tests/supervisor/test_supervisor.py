#!/usr/bin/env python3
"""
Test script for AutoNinja Supervisor Agent
Tests the supervisor agent invocation and multi-agent collaboration
"""

import boto3
import json
import time
import uuid
import logging
import os
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration - can be overridden via environment variables
AGENT_ID = os.environ.get('SUPERVISOR_AGENT_ID', 'DAQAIWIYYE')
ALIAS_ID = os.environ.get('SUPERVISOR_ALIAS_ID', 'PB8TEAYL1T')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')

def invoke_supervisor_agent(agent_id, alias_id, prompt, session_id=None):
    """
    Invoke the supervisor agent with a given prompt
    """
    if not session_id:
        session_id = f"test-session-{int(time.time())}"

    client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
    
    try:
        logger.info(f"Invoking supervisor agent {agent_id} with alias {alias_id}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Prompt: {prompt}")
        
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            enableTrace=True,
            sessionId=session_id,
            inputText=prompt,
            streamingConfigurations={
                "applyGuardrailInterval": 50,
                "streamFinalResponse": False
            }
        )
        
        completion = ""
        trace_events = []
        
        # Process the response stream
        for event in response.get("completion", []):
            # Collect agent output
            if 'chunk' in event:
                chunk = event["chunk"]
                completion += chunk["bytes"].decode()
            
            # Log trace output
            if 'trace' in event:
                trace_event = event.get("trace")
                trace = trace_event.get('trace', {})
                trace_events.append(trace)
                
                # Log orchestration steps
                if 'orchestrationTrace' in trace:
                    orch_trace = trace['orchestrationTrace']
                    if 'invocationInput' in orch_trace:
                        logger.info(f"Orchestration Input: {orch_trace['invocationInput']}")
                    if 'modelInvocationInput' in orch_trace:
                        logger.info(f"Model Input: {orch_trace['modelInvocationInput']}")
                    if 'modelInvocationOutput' in orch_trace:
                        logger.info(f"Model Output: {orch_trace['modelInvocationOutput']}")
        
        logger.info("=== SUPERVISOR AGENT RESPONSE ===")
        logger.info(completion)
        logger.info("=== END RESPONSE ===")
        
        return {
            'completion': completion,
            'trace_events': trace_events,
            'session_id': session_id
        }
        
    except ClientError as e:
        logger.error(f"Error invoking supervisor agent: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def test_supervisor_basic():
    """
    Test basic supervisor agent functionality
    """
    # Test prompt
    prompt = "Build a simple friend agent for emotional support"

    logger.info("=== TESTING SUPERVISOR AGENT ===")
    logger.info(f"Agent ID: {AGENT_ID}")
    logger.info(f"Alias ID: {ALIAS_ID}")
    
    try:
        result = invoke_supervisor_agent(AGENT_ID, ALIAS_ID, prompt)

        # Verify response
        assert result['completion'], "No completion received from supervisor"
        assert result['session_id'], "No session ID returned"

        logger.info("✅ Supervisor agent test PASSED")
        return True

    except Exception as e:
        logger.error(f"❌ Supervisor agent test FAILED: {e}")
        return False

def test_supervisor_job_generation():
    """
    Test that supervisor generates proper job_name
    """
    prompt = "Create a customer service agent for insurance claims"

    logger.info("=== TESTING JOB NAME GENERATION ===")
    
    try:
        result = invoke_supervisor_agent(AGENT_ID, ALIAS_ID, prompt)
        
        # Check if response mentions job_name
        completion = result['completion'].lower()
        
        # Look for job name pattern in response
        if 'job-' in completion or 'job_name' in completion:
            logger.info("✅ Job name generation test PASSED")
            return True
        else:
            logger.warning("⚠️  Job name not clearly mentioned in response")
            return False
            
    except Exception as e:
        logger.error(f"❌ Job name generation test FAILED: {e}")
        return False

def main():
    """
    Run all supervisor agent tests
    """
    logger.info("Starting AutoNinja Supervisor Agent Tests")
    
    tests = [
        ("Basic Supervisor Test", test_supervisor_basic),
        ("Job Generation Test", test_supervisor_job_generation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"TEST RESULTS: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED!")
        return True
    else:
        logger.error("❌ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)