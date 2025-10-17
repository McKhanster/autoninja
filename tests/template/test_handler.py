#!/usr/bin/env python3
"""
Unit tests for Code Generator Lambda handler
Tests the handler directly without invoking Bedrock Agent
"""
import json
import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Mock the shared modules before importing handler
sys.modules['shared.persistence.dynamodb_client'] = MagicMock()
sys.modules['shared.persistence.s3_client'] = MagicMock()
sys.modules['shared.utils.logger'] = MagicMock()
sys.modules['shared.models.code_artifacts'] = MagicMock()

# Now import the handler
import importlib.util
spec = importlib.util.spec_from_file_location("handler", "lambda/{{AGENT_NAME}}/handler.py")
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


def create_bedrock_event(api_path: str, params: dict) -> dict:
    """
    Create a mock Bedrock Agent event
    
    Args:
        api_path: The API path (e.g., '{{SAMPLE_API_PATH}}')
        params: Dict of parameters to include
        
    Returns:
        Mock Bedrock Agent event dict
    """
    properties = [
        {'name': key, 'value': value}
        for key, value in params.items()
    ]
    
    return {
        'messageVersion': '1.0',
        'agent': {
            'name': '{{AGENT_NAME}}',
            'id': 'TEST123',
            'alias': 'PROD',
            'version': '1'
        },
        'inputText': 'Test input',
        'sessionId': 'test-session-123',
        'actionGroup': '{{AGENT_NAME}}-actions',
        'apiPath': api_path,
        'httpMethod': 'POST',
        'parameters': properties,
        'requestBody': {
            'content': {
                'application/json': {
                    'properties': properties
                }
            }
        }
    }


{{TEST_FUNCTIONS}}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
