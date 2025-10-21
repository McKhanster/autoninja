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
foundational_model = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Now import the handler
import importlib.util
spec = importlib.util.spec_from_file_location("handler", "lambda/code-generator/handler.py")
handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler)


def create_bedrock_event(api_path: str, params: dict) -> dict:
    """
    Create a mock Bedrock Agent event
    
    Args:
        api_path: The API path (e.g., '/generate-lambda-code')
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
            'name': 'code-generator',
            'id': 'TEST123',
            'alias': 'PROD',
            'version': '1'
        },
        'inputText': 'Test input',
        'sessionId': 'test-session-123',
        'actionGroup': 'code-generator-actions',
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


def test_generate_lambda_code():
    """Test generate_lambda_code action"""
    requirements = {
        "agent_purpose": "Test agent",
        "capabilities": ["Test capability"],
        "lambda_requirements": {
            "runtime": "python3.12",
            "memory": 512,
            "timeout": 60,
            "actions": [
                {
                    "name": "test_action",
                    "description": "Test action",
                    "parameters": ["param1"]
                }
            ]
        }
    }
    
    event = create_bedrock_event(
        '/generate-lambda-code',
        {
            'job_name': 'job-test-20250101-120000',
            'requirements': json.dumps(requirements),
            'function_spec': '{}'
        }
    )
    
    context = Mock()
    
    # Mock the DynamoDB and S3 clients
    with patch.object(handler.dynamodb_client, 'log_inference_input') as mock_log_input, \
         patch.object(handler.dynamodb_client, 'log_inference_output') as mock_log_output, \
         patch.object(handler.s3_client, 'save_converted_artifact') as mock_save_artifact, \
         patch.object(handler.s3_client, 'save_raw_response') as mock_save_raw, \
         patch.object(handler.s3_client, 'get_s3_uri') as mock_get_uri:
        
        mock_log_input.return_value = {'timestamp': '2025-01-01T12:00:00Z'}
        mock_get_uri.return_value = 's3://test-bucket/test-key'
        
        response = handler.lambda_handler(event, context)
        
        # Verify response structure
        assert response['messageVersion'] == '1.0'
        assert response['response']['httpStatusCode'] == 200
        assert response['response']['actionGroup'] == 'code-generator-actions'
        assert response['response']['apiPath'] == '/generate-lambda-code'
        
        # Parse response body
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['job_name'] == 'job-test-20250101-120000'
        assert body['status'] == 'success'
        assert 'lambda_code' in body
        assert 'requirements_txt' in body
        
        # Verify logging was called
        assert mock_log_input.called
        assert mock_log_output.called
        assert mock_save_artifact.called
        assert mock_save_raw.called


def test_generate_agent_config():
    """Test generate_agent_config action"""
    requirements = {
        "agent_purpose": "Test agent for testing",
        "system_prompts": "You are a test agent",
        "architecture_requirements": {
            "bedrock": {
                "foundation_model": foundational_model,
                "action_groups": 1
            }
        }
    }
    
    event = create_bedrock_event(
        '/generate-agent-config',
        {
            'job_name': 'job-test-20250101-120000',
            'requirements': json.dumps(requirements)
        }
    )
    
    context = Mock()
    
    # Mock the DynamoDB and S3 clients
    with patch.object(handler.dynamodb_client, 'log_inference_input') as mock_log_input, \
         patch.object(handler.dynamodb_client, 'log_inference_output') as mock_log_output, \
         patch.object(handler.s3_client, 'save_converted_artifact') as mock_save_artifact, \
         patch.object(handler.s3_client, 'save_raw_response') as mock_save_raw, \
         patch.object(handler.s3_client, 'get_s3_uri') as mock_get_uri:
        
        mock_log_input.return_value = {'timestamp': '2025-01-01T12:00:00Z'}
        mock_get_uri.return_value = 's3://test-bucket/test-key'
        
        response = handler.lambda_handler(event, context)
        
        # Verify response structure
        assert response['messageVersion'] == '1.0'
        assert response['response']['httpStatusCode'] == 200
        
        # Parse response body
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['job_name'] == 'job-test-20250101-120000'
        assert body['status'] == 'success'
        assert 'agent_config' in body
        
        # Verify agent config structure
        agent_config = body['agent_config']
        assert 'agentName' in agent_config
        assert 'foundationModel' in agent_config
        assert 'instruction' in agent_config
        assert 'actionGroups' in agent_config


def test_generate_openapi_schema():
    """Test generate_openapi_schema action"""
    action_group_spec = {
        "agent_name": "test-agent",
        "actions": [
            {
                "name": "test_action",
                "description": "Test action",
                "parameters": ["param1", "param2"]
            }
        ]
    }
    
    event = create_bedrock_event(
        '/generate-openapi-schema',
        {
            'job_name': 'job-test-20250101-120000',
            'action_group_spec': json.dumps(action_group_spec)
        }
    )
    
    context = Mock()
    
    # Mock the DynamoDB and S3 clients
    with patch.object(handler.dynamodb_client, 'log_inference_input') as mock_log_input, \
         patch.object(handler.dynamodb_client, 'log_inference_output') as mock_log_output, \
         patch.object(handler.s3_client, 'save_converted_artifact') as mock_save_artifact, \
         patch.object(handler.s3_client, 'save_raw_response') as mock_save_raw, \
         patch.object(handler.s3_client, 'get_s3_uri') as mock_get_uri:
        
        mock_log_input.return_value = {'timestamp': '2025-01-01T12:00:00Z'}
        mock_get_uri.return_value = 's3://test-bucket/test-key'
        
        response = handler.lambda_handler(event, context)
        
        # Verify response structure
        assert response['messageVersion'] == '1.0'
        assert response['response']['httpStatusCode'] == 200
        
        # Parse response body
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['job_name'] == 'job-test-20250101-120000'
        assert body['status'] == 'success'
        assert 'openapi_schema' in body
        
        # Verify OpenAPI schema contains expected elements
        schema = body['openapi_schema']
        assert 'openapi: 3.0.0' in schema
        assert 'test-agent' in schema.lower()
        assert 'test_action' in schema or 'test-action' in schema


def test_error_handling():
    """Test error handling for invalid requests"""
    # Missing required parameter
    event = create_bedrock_event(
        '/generate-lambda-code',
        {
            'job_name': 'job-test-20250101-120000'
            # Missing 'requirements' parameter
        }
    )
    
    context = Mock()
    
    with patch.object(handler.dynamodb_client, 'log_inference_input') as mock_log_input:
        mock_log_input.return_value = {'timestamp': '2025-01-01T12:00:00Z'}
        
        response = handler.lambda_handler(event, context)
        
        # Verify error response
        assert response['messageVersion'] == '1.0'
        assert response['response']['httpStatusCode'] == 500
        
        # Parse error body
        body = json.loads(response['response']['responseBody']['application/json']['body'])
        assert body['status'] == 'error'
        assert 'error' in body


def test_unknown_api_path():
    """Test handling of unknown API path"""
    event = create_bedrock_event(
        '/unknown-action',
        {
            'job_name': 'job-test-20250101-120000'
        }
    )
    
    context = Mock()
    
    response = handler.lambda_handler(event, context)
    
    # Verify error response
    assert response['response']['httpStatusCode'] == 500
    body = json.loads(response['response']['responseBody']['application/json']['body'])
    assert 'error' in body
    assert 'Unknown apiPath' in body['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
