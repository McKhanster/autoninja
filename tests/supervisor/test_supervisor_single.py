#!/usr/bin/env python3
"""
Single test for AutoNinja Supervisor Agent
Tests one full workflow with extended timeout
"""

import boto3
import json
import time
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def invoke_supervisor_agent(agent_id, alias_id, prompt, session_id=None):
    """
    Invoke the supervisor agent with a given prompt
    """
    if not session_id:
        session_id = f"test-session-{int(time.time())}"

    client = boto3.client('bedrock-agent-runtime', region_name='us-east-2')

    try:
        logger.info(f"Invoking supervisor agent {agent_id} with alias {alias_id}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Prompt: {prompt}")
        logger.info("NOTE: This will take 5-10 minutes to complete the full workflow")

        start_time = time.time()
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
        logger.info("Processing response stream...")
        for event in response.get("completion", []):
            # Collect agent output
            if 'chunk' in event:
                chunk = event["chunk"]
                chunk_text = chunk["bytes"].decode()
                completion += chunk_text
                logger.info(f"Received chunk: {chunk_text[:100]}...")

            # Log trace output
            if 'trace' in event:
                trace_event = event.get("trace")
                trace = trace_event.get('trace', {})
                trace_events.append(trace)

                # Log orchestration steps
                if 'orchestrationTrace' in trace:
                    orch_trace = trace['orchestrationTrace']
                    if 'modelInvocationOutput' in orch_trace:
                        logger.info(f"Model invocation completed")

        elapsed = time.time() - start_time
        logger.info(f"Stream processing completed in {elapsed:.1f} seconds")
        logger.info("=== SUPERVISOR AGENT RESPONSE ===")
        logger.info(completion)
        logger.info("=== END RESPONSE ===")

        return {
            'completion': completion,
            'trace_events': trace_events,
            'session_id': session_id,
            'elapsed_seconds': elapsed
        }

    except ClientError as e:
        logger.error(f"Error invoking supervisor agent: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def main():
    """
    Run single supervisor agent test
    """
    logger.info("Starting AutoNinja Supervisor Agent Single Test")

    # Supervisor agent details from deployment
    agent_id = "YCUCZDC5KM"
    alias_id = "TSTALIASID"

    # Test prompt
    prompt = "Build a simple friend agent for emotional support"

    logger.info("=== TESTING SUPERVISOR AGENT ===")
    logger.info(f"Agent ID: {agent_id}")
    logger.info(f"Alias ID: {alias_id}")

    try:
        result = invoke_supervisor_agent(agent_id, alias_id, prompt)

        # Verify response
        if not result['completion']:
            logger.error("❌ No completion received from supervisor")
            return False

        if not result['session_id']:
            logger.error("❌ No session ID returned")
            return False

        logger.info(f"✅ Test completed successfully in {result['elapsed_seconds']:.1f} seconds")

        # Check if response mentions job_name (indicating workflow started)
        if 'job-' in result['completion'].lower() or 'job_name' in result['completion'].lower():
            logger.info("✅ Response includes job name - workflow appears to have executed")
        else:
            logger.warning("⚠️  No job name mentioned in response")

        return True

    except Exception as e:
        logger.error(f"❌ Supervisor agent test FAILED: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
