"""
AgentCore-based global rate limiter for AutoNinja agents.
Enforces 30-second minimum intervals between any model invocations across all agents using shared AgentCore Memory.
"""
import json
import time
from datetime import datetime
from typing import Optional
import boto3
import os

# Constants
MIN_INTERVAL_SECONDS = 30  # 30 seconds minimum between ANY model invocations
MAX_RETRIES = 5
BASE_DELAY = 1.0
RATE_LIMIT_ACTOR_ID = "rate-limiter"
GLOBAL_RATE_LIMIT_SESSION_ID = "global-model-invocations"

# AWS client (lazy init)
_bedrock_agentcore_data = None

def _get_agentcore_client():
    global _bedrock_agentcore_data
    if _bedrock_agentcore_data is None:
        _bedrock_agentcore_data = boto3.client('bedrock-agentcore')
    return _bedrock_agentcore_data

def get_memory_id() -> str:
    """Get AgentCore Memory ID from environment."""
    memory_id = os.environ.get('MEMORY_ID') or os.environ.get('BEDROCK_AGENTCORE_MEMORY_ID')
    if not memory_id:
        raise ValueError("MEMORY_ID environment variable not set")
    return memory_id

def check_and_enforce_global_rate_limit() -> float:
    """
    Check global rate limiter using AgentCore Memory for ANY model invocation.
    This applies to ALL agents including the supervisor.
    
    Returns:
        float: Seconds to wait (0 if no wait needed)
    """
    try:
        memory_id = get_memory_id()
        client = _get_agentcore_client()
        
        # Retrieve global rate limiting data from AgentCore Memory
        response = client.retrieve_memory_records(
            memoryId=memory_id,
            namespace="/rate-limiting/global",
            searchCriteria={
                'searchQuery': 'last model invocation timestamp',
                'topK': 1
            }
        )
        
        wait_time = 0.0
        if response.get('memoryRecords'):
            memory_record = response['memoryRecords'][0]
            # Extract content from conversational format
            content_text = memory_record['content']['conversational']['content']['text']
            content = json.loads(content_text)
            last_invocation = datetime.fromisoformat(content['last_invocation'])
            elapsed = (datetime.now() - last_invocation).total_seconds()
            
            if elapsed < MIN_INTERVAL_SECONDS:
                wait_time = MIN_INTERVAL_SECONDS - elapsed
                print(f"Global rate limit: waiting {wait_time:.2f}s since last model invocation")
        
        return wait_time
        
    except Exception as e:
        print(f"Error checking global rate limit: {str(e)}")
        return 0.0

def update_global_rate_limiter_timestamp(agent_name: str):
    """
    Update the global rate limiter timestamp for ANY model invocation using AgentCore Memory.
    This records that ANY agent (including supervisor) made a model call.
    """
    try:
        memory_id = get_memory_id()
        client = _get_agentcore_client()
        
        # Create event in AgentCore Memory to track rate limiting using correct format
        event_payload = [
            {
                'conversational': {
                    'content': {
                        'text': json.dumps({
                            "last_invocation": datetime.now().isoformat(),
                            "last_agent": agent_name,
                            "invocation_count": 1,
                            "created_at": datetime.now().isoformat()
                        })
                    },
                    'role': 'ASSISTANT'
                }
            }
        ]
        
        # Store rate limiting event in AgentCore Memory
        client.create_event(
            memoryId=memory_id,
            actorId=RATE_LIMIT_ACTOR_ID,
            sessionId=GLOBAL_RATE_LIMIT_SESSION_ID,
            eventTimestamp=datetime.now(),
            payload=event_payload
        )
        
        print(f"Updated global rate limiter: {agent_name} made model invocation")
    except Exception as e:
        print(f"Error updating global rate limiter for {agent_name}: {str(e)}")

def enforce_rate_limit_before_call(agent_name: str):
    """
    Convenience function: Check and wait if needed, then update timestamp.
    Use before any model invocation.
    """
    wait_time = check_and_enforce_global_rate_limit()
    if wait_time > 0:
        time.sleep(wait_time)
    update_global_rate_limiter_timestamp(agent_name)
