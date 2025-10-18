"""
Custom Orchestration Lambda for AWS Bedrock Agents
Enforces sequential tool execution with rate limiting to prevent throttling
"""
import json
import os
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Configuration
MIN_INTERVAL_SECONDS = int(os.environ.get('MIN_INTERVAL_SECONDS', '60'))

# In-memory state for rate limiting (persists across warm starts)
last_converse_time = {}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Custom orchestration handler for Bedrock Agents.
    Enforces sequential tool execution with rate limiting.

    Args:
        event: Bedrock Agent orchestration event
        context: Lambda context

    Returns:
        Orchestration response with next action
    """
    start_time = time.time()

    try:
        # Log incoming event
        logger.info(json.dumps({
            'event': 'orchestration_invoked',
            'agent_id': event.get('agentId'),
            'session_id': event.get('sessionId'),
            'orchestration_state': event.get('orchestrationState'),
            'timestamp': datetime.utcnow().isoformat()
        }))

        # Extract key fields
        orchestration_state = event.get('orchestrationState')
        agent_id = event.get('agentId')
        session_id = event.get('sessionId')

        # Route to appropriate handler based on state
        if orchestration_state == 'START':
            response = handle_start(event, agent_id, session_id)
        elif orchestration_state == 'MODEL_INVOKED':
            response = handle_model_invoked(event, agent_id, session_id)
        elif orchestration_state == 'TOOL_INVOKED':
            response = handle_tool_invoked(event, agent_id, session_id)
        else:
            # Unknown state, return event as-is
            logger.warning(f"Unknown orchestration state: {orchestration_state}")
            response = event

        # Log completion
        duration = time.time() - start_time
        logger.info(json.dumps({
            'event': 'orchestration_completed',
            'agent_id': agent_id,
            'session_id': session_id,
            'duration_seconds': round(duration, 2),
            'timestamp': datetime.utcnow().isoformat()
        }))

        return response

    except Exception as e:
        logger.error(json.dumps({
            'event': 'orchestration_error',
            'error': str(e),
            'agent_id': event.get('agentId'),
            'session_id': event.get('sessionId'),
            'timestamp': datetime.utcnow().isoformat()
        }))
        raise


def handle_start(event: Dict[str, Any], agent_id: str, session_id: str) -> Dict[str, Any]:
    """
    Handle START state - initial user input received.
    Invoke model to analyze input and plan actions.

    Args:
        event: Orchestration event
        agent_id: Agent ID
        session_id: Session ID

    Returns:
        Response indicating to invoke model
    """
    logger.info(json.dumps({
        'event': 'handle_start',
        'agent_id': agent_id,
        'session_id': session_id,
        'action': 'invoke_model_for_planning'
    }))

    # Apply rate limiting before invoking model
    apply_rate_limiting(agent_id, session_id)

    # Return event to indicate model should be invoked
    # Bedrock will automatically invoke the model
    return event


def handle_model_invoked(event: Dict[str, Any], agent_id: str, session_id: str) -> Dict[str, Any]:
    """
    Handle MODEL_INVOKED state - model has returned a response with potential tool calls.
    Extract tool calls and enforce SEQUENTIAL execution (return only first tool).

    Args:
        event: Orchestration event
        agent_id: Agent ID
        session_id: Session ID

    Returns:
        Response with single tool to execute
    """
    logger.info(json.dumps({
        'event': 'handle_model_invoked',
        'agent_id': agent_id,
        'session_id': session_id,
        'action': 'extract_and_execute_first_tool'
    }))

    # Check if model wants to invoke tools
    model_output = event.get('modelInvocationOutput', {})
    tool_use = model_output.get('toolUse')

    if not tool_use:
        # No tool calls, return final response
        logger.info(json.dumps({
            'event': 'no_tools_needed',
            'agent_id': agent_id,
            'session_id': session_id,
            'action': 'return_final_response'
        }))
        return event

    # Extract tool calls (could be multiple)
    tool_calls = tool_use if isinstance(tool_use, list) else [tool_use]

    if len(tool_calls) > 1:
        logger.info(json.dumps({
            'event': 'multiple_tools_requested',
            'agent_id': agent_id,
            'session_id': session_id,
            'tool_count': len(tool_calls),
            'action': 'enforce_sequential_execution'
        }))

        # CRITICAL: Return only the first tool to enforce sequential execution
        # The rest will be executed after this one completes
        first_tool = tool_calls[0]
        event['modelInvocationOutput']['toolUse'] = first_tool

        logger.info(json.dumps({
            'event': 'executing_first_tool',
            'agent_id': agent_id,
            'session_id': session_id,
            'tool_name': first_tool.get('name'),
            'tool_id': first_tool.get('toolUseId')
        }))
    else:
        logger.info(json.dumps({
            'event': 'single_tool_requested',
            'agent_id': agent_id,
            'session_id': session_id,
            'tool_name': tool_calls[0].get('name'),
            'tool_id': tool_calls[0].get('toolUseId')
        }))

    return event


def handle_tool_invoked(event: Dict[str, Any], agent_id: str, session_id: str) -> Dict[str, Any]:
    """
    Handle TOOL_INVOKED state - a tool has completed execution.
    Apply rate limiting, then check if more tools are needed.

    Args:
        event: Orchestration event
        agent_id: Agent ID
        session_id: Session ID

    Returns:
        Response indicating next action
    """
    tool_result = event.get('actionGroupInvocationOutput', {})
    tool_name = tool_result.get('agentActionGroup', 'unknown')

    logger.info(json.dumps({
        'event': 'handle_tool_invoked',
        'agent_id': agent_id,
        'session_id': session_id,
        'tool_name': tool_name,
        'action': 'check_if_more_tools_needed'
    }))

    # Apply rate limiting before potentially invoking model again
    apply_rate_limiting(agent_id, session_id)

    # Check if we need to invoke model again to determine next steps
    # Bedrock will automatically handle this based on conversation state
    # If more tools are needed, model will be invoked again
    # If done, final response will be returned

    logger.info(json.dumps({
        'event': 'tool_completed',
        'agent_id': agent_id,
        'session_id': session_id,
        'tool_name': tool_name,
        'action': 'proceed_to_next_step'
    }))

    return event


def apply_rate_limiting(agent_id: str, session_id: str) -> None:
    """
    Apply rate limiting to prevent throttling.
    Enforces minimum interval between Converse API calls.

    Args:
        agent_id: Agent ID
        session_id: Session ID
    """
    global last_converse_time

    key = f"{agent_id}:{session_id}"
    current_time = time.time()

    if key in last_converse_time:
        elapsed = current_time - last_converse_time[key]

        if elapsed < MIN_INTERVAL_SECONDS:
            wait_time = MIN_INTERVAL_SECONDS - elapsed

            logger.info(json.dumps({
                'event': 'rate_limiting',
                'agent_id': agent_id,
                'session_id': session_id,
                'elapsed_seconds': round(elapsed, 2),
                'wait_seconds': round(wait_time, 2),
                'action': 'sleeping'
            }))

            time.sleep(wait_time)

            logger.info(json.dumps({
                'event': 'rate_limiting_complete',
                'agent_id': agent_id,
                'session_id': session_id,
                'waited_seconds': round(wait_time, 2)
            }))

    # Update last invocation time
    last_converse_time[key] = time.time()

    # Clean up old entries (keep only last 100)
    if len(last_converse_time) > 100:
        oldest_keys = sorted(last_converse_time.keys(),
                           key=lambda k: last_converse_time[k])[:50]
        for old_key in oldest_keys:
            del last_converse_time[old_key]
