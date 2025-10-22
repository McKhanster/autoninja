"""
AgentCore Memory Rate Limiter
Coordinates rate limiting across all AutoNinja agents using shared AgentCore Memory
"""
import boto3
import time
import os
import logging
from botocore.config import Config
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiting configuration
AGENT_INVOKE_DELAY = 10.0  # 10 seconds between agent invocations
MAX_RETRIES = 5
MEMORY_ID = os.environ.get('MEMORY_ID', 'autoninja_rate_limiter_production')

# Initialize AgentCore client with extended timeouts
config = Config(
    read_timeout=300,  # 5 minutes
    connect_timeout=60,  # 1 minute
    retries={'max_attempts': 3}
)

bedrock_agentcore = boto3.client('bedrock-agentcore', config=config)


def apply_rate_limiting(agent_name: str, custom_delay: Optional[float] = None):
    """
    Apply rate limiting using AgentCore Memory to coordinate across all agents.
    Ensures minimum delay between agent invocations to prevent burst patterns.
    
    Args:
        agent_name: Name of the agent applying rate limiting
        custom_delay: Optional custom delay override (defaults to AGENT_INVOKE_DELAY)
    """
    delay = custom_delay or AGENT_INVOKE_DELAY
    
    try:
        # Check last invocation time from AgentCore Memory
        current_time = time.time()
        
        # Retrieve last invocation records
        try:
            response = bedrock_agentcore.retrieve_memory_records(
                memoryId=MEMORY_ID,
                namespace='rate_limiting',
                searchCriteria={
                    'searchQuery': 'lastInvocation',
                    'topK': 10
                }
            )
            
            records = response.get('memoryRecords', [])
            last_invocation_time = 0
            
            # Find the most recent invocation
            for record in records:
                # Memory records from RetrieveMemoryRecords have different structure
                summary = record.get('summary', '')
                content = record.get('content', '')
                
                # Check both summary and content for our invocation data
                text_to_check = f"{summary} {content}"
                if 'lastInvocation' in text_to_check:
                    try:
                        # Parse format: lastInvocation:{timestamp}:agent:{agent_name}
                        # Look for the pattern in either summary or content
                        for text in [summary, content]:
                            if 'lastInvocation' in text:
                                parts = text.split(':')
                                if len(parts) >= 2:
                                    record_time = float(parts[1])
                                    last_invocation_time = max(last_invocation_time, record_time)
                                    break
                    except (ValueError, IndexError):
                        continue
            
            # Calculate required delay
            time_since_last = current_time - last_invocation_time
            if time_since_last < delay:
                sleep_time = delay - time_since_last
                logger.info(f'Rate limiting: sleeping {sleep_time:.2f}s before {agent_name} invocation')
                time.sleep(sleep_time)
            else:
                logger.info(f'No rate limiting needed for {agent_name} (last invocation {time_since_last:.2f}s ago)')
            
        except Exception as memory_error:
            # If memory retrieval fails, apply default delay
            logger.warning(f'Memory retrieval failed for {agent_name}, applying default delay: {str(memory_error)}')
            time.sleep(delay)
        
        # Record this invocation in AgentCore Memory
        try:
            from datetime import datetime
            current_time = time.time()  # Get fresh timestamp after any delays
            bedrock_agentcore.create_event(
                memoryId=MEMORY_ID,
                actorId=f'autoninja-{agent_name}',
                sessionId=f'rate-limiting-session',
                eventTimestamp=datetime.fromtimestamp(current_time),  # Use datetime object
                payload=[{
                    'conversational': {  # lowercase 'conversational'
                        'role': 'system',
                        'content': f'lastInvocation:{current_time}:agent:{agent_name}'
                    }
                }]
            )
            logger.info(f'Recorded {agent_name} invocation at {current_time}')
        except Exception as record_error:
            logger.warning(f'Failed to record invocation for {agent_name}: {str(record_error)}')
            
    except Exception as e:
        logger.error(f'Rate limiting failed for {agent_name}: {str(e)}')
        # Apply fallback delay
        time.sleep(delay)


def get_last_invocation_time() -> float:
    """
    Get the timestamp of the last agent invocation from AgentCore Memory.
    
    Returns:
        Timestamp of last invocation, or 0 if none found
    """
    try:
        response = bedrock_agentcore.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace='rate_limiting',
            searchCriteria={
                'searchQuery': 'lastInvocation',
                'topK': 10
            }
        )
        
        records = response.get('memoryRecords', [])
        last_invocation_time = 0
        
        for record in records:
            # Memory records from RetrieveMemoryRecords have different structure
            summary = record.get('summary', '')
            content = record.get('content', '')
            
            # Check both summary and content for our invocation data
            text_to_check = f"{summary} {content}"
            if 'lastInvocation' in text_to_check:
                try:
                    # Parse format: lastInvocation:{timestamp}:agent:{agent_name}
                    for text in [summary, content]:
                        if 'lastInvocation' in text:
                            parts = text.split(':')
                            if len(parts) >= 2:
                                record_time = float(parts[1])
                                last_invocation_time = max(last_invocation_time, record_time)
                                break
                except (ValueError, IndexError):
                    continue
        
        return last_invocation_time
        
    except Exception as e:
        logger.error(f'Failed to get last invocation time: {str(e)}')
        return 0


def clear_rate_limit_history():
    """
    Clear rate limiting history from AgentCore Memory.
    Useful for testing or resetting the rate limiter state.
    """
    try:
        # Note: AgentCore Memory doesn't have a direct clear method
        # Records will expire based on EventExpiryDuration (30 days)
        logger.info('Rate limit history will expire automatically based on AgentCore Memory configuration')
    except Exception as e:
        logger.error(f'Failed to clear rate limit history: {str(e)}')


def set_rate_limit_delay(delay_seconds: float):
    """
    Set a custom rate limiting delay.
    
    Args:
        delay_seconds: Delay in seconds between agent invocations
    """
    global AGENT_INVOKE_DELAY
    AGENT_INVOKE_DELAY = delay_seconds
    logger.info(f'Rate limiting delay set to {delay_seconds} seconds')