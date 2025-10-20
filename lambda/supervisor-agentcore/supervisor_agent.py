"""
AgentCore Runtime supervisor agent entry point.
This file serves as the entry point for the AgentCore Runtime supervisor.
"""
from handler import lambda_handler

# AgentCore Runtime entry point
def main(event, context):
    """
    Main entry point for AgentCore Runtime supervisor.
    Delegates to the lambda_handler for processing.
    """
    return lambda_handler(event, context)

if __name__ == "__main__":
    # For local testing
    test_event = {
        "inputText": "I would like a friend agent",
        "sessionId": "test-session"
    }
    result = main(test_event, None)
    print(f"Result: {result}")