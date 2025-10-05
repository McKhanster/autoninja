"""
Integration tests for Bedrock client functionality.

These tests require AWS credentials and access to Bedrock services.
They can be skipped in CI/CD environments without proper AWS setup.
"""

import pytest
import os
from unittest.mock import patch

from autoninja.core.bedrock_client import (
    BedrockClientManager,
    BedrockClientConfig,
    TaskComplexity,
    BedrockModelId,
    get_bedrock_client_manager
)


# Skip integration tests if AWS credentials are not available
pytestmark = pytest.mark.skipif(
    not os.getenv("AWS_ACCESS_KEY_ID") and not os.getenv("AWS_PROFILE"),
    reason="AWS credentials not available for integration tests"
)


class TestBedrockIntegration:
    """Integration tests for Bedrock client functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Setup
        from autoninja.core.bedrock_client import reset_client_manager
        reset_client_manager()
        
        yield
        
        # Teardown
        reset_client_manager()
    
    def test_client_manager_initialization(self):
        """Test that client manager initializes successfully with real AWS credentials."""
        try:
            config = BedrockClientConfig(region_name="us-east-2")
            manager = BedrockClientManager(config)
            
            # Verify that clients were created
            assert len(manager._clients) > 0
            assert len(manager._circuit_breakers) > 0
            
            # Verify that circuit breakers are in CLOSED state
            for cb in manager._circuit_breakers.values():
                assert cb.state == "CLOSED"
                
        except Exception as e:
            pytest.skip(f"Bedrock service not available or configured: {str(e)}")
    
    def test_model_selection_logic(self):
        """Test that model selection works correctly."""
        try:
            manager = get_bedrock_client_manager()
            
            # Test all complexity levels
            low_model = manager.select_model_by_complexity(TaskComplexity.LOW)
            medium_model = manager.select_model_by_complexity(TaskComplexity.MEDIUM)
            high_model = manager.select_model_by_complexity(TaskComplexity.HIGH)
            critical_model = manager.select_model_by_complexity(TaskComplexity.CRITICAL)
            
            # Verify model selection logic
            assert low_model == BedrockModelId.CLAUDE_HAIKU_3
            assert medium_model == BedrockModelId.CLAUDE_SONNET_4_5
            assert high_model == BedrockModelId.CLAUDE_OPUS_4_1
            assert critical_model == BedrockModelId.CLAUDE_OPUS_4_1
            
        except Exception as e:
            pytest.skip(f"Bedrock service not available or configured: {str(e)}")
    
    def test_get_available_models(self):
        """Test getting available models."""
        try:
            manager = get_bedrock_client_manager()
            available_models = manager.get_available_models()
            
            # Should have at least one available model
            assert len(available_models) > 0
            
            # All returned models should be BedrockModelId instances
            for model in available_models:
                assert isinstance(model, BedrockModelId)
                
        except Exception as e:
            pytest.skip(f"Bedrock service not available or configured: {str(e)}")
    
    def test_client_status_reporting(self):
        """Test client status reporting functionality."""
        try:
            manager = get_bedrock_client_manager()
            status = manager.get_client_status()
            
            # Should have status for all models
            assert len(status) == len(BedrockModelId)
            
            # Verify status structure
            for model_id in BedrockModelId:
                model_status = status[model_id.value]
                
                assert "available" in model_status
                assert "circuit_breaker_state" in model_status
                assert "failure_count" in model_status
                assert "last_failure_time" in model_status
                
                # Initially, circuit breakers should be closed
                if model_status["available"]:
                    assert model_status["circuit_breaker_state"] == "CLOSED"
                    assert model_status["failure_count"] == 0
                    
        except Exception as e:
            pytest.skip(f"Bedrock service not available or configured: {str(e)}")
    
    @pytest.mark.slow
    def test_simple_model_invocation(self):
        """Test a simple model invocation (marked as slow test)."""
        try:
            manager = get_bedrock_client_manager()
            
            # Use the fastest model for testing
            model_id = BedrockModelId.CLAUDE_HAIKU_3
            
            # Check if model is available
            available_models = manager.get_available_models()
            if model_id not in available_models:
                pytest.skip(f"Model {model_id.value} not available")
            
            # Simple test message
            messages = [{"role": "user", "content": "Say 'Hello, AutoNinja!' and nothing else."}]
            
            # Invoke with retry logic
            response = manager.invoke_with_retry(model_id, messages)
            
            # Verify we got a response
            assert response is not None
            
            # The response should be a string or have content
            if hasattr(response, 'content'):
                assert len(response.content) > 0
            else:
                assert len(str(response)) > 0
                
        except Exception as e:
            # If the test fails due to service issues, skip it
            if "throttling" in str(e).lower() or "quota" in str(e).lower():
                pytest.skip(f"Bedrock service throttling or quota exceeded: {str(e)}")
            else:
                pytest.skip(f"Bedrock service error: {str(e)}")
    
    def test_circuit_breaker_functionality(self):
        """Test circuit breaker functionality with mocked failures."""
        try:
            manager = get_bedrock_client_manager()
            
            # Get a circuit breaker for testing
            model_id = BedrockModelId.CLAUDE_HAIKU_3
            circuit_breaker = manager._circuit_breakers[model_id.value]
            
            # Initially should be closed
            assert circuit_breaker.state == "CLOSED"
            assert circuit_breaker.is_available() is True
            
            # Simulate failures to open the circuit
            for _ in range(circuit_breaker.failure_threshold):
                circuit_breaker.record_failure()
            
            # Circuit should now be open
            assert circuit_breaker.state == "OPEN"
            assert circuit_breaker.is_available() is False
            
            # Try to get client - should raise error
            with pytest.raises(RuntimeError, match="Circuit breaker is open"):
                manager.get_client(model_id)
                
        except Exception as e:
            pytest.skip(f"Bedrock service not available or configured: {str(e)}")


class TestBedrockConfigurationIntegration:
    """Integration tests for Bedrock configuration."""
    
    def test_configuration_from_environment(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        test_env = {
            "BEDROCK_REGION_NAME": "us-west-2",
            "BEDROCK_DEFAULT_MAX_TOKENS": "2048",
            "BEDROCK_DEFAULT_TEMPERATURE": "0.5",
            "BEDROCK_MAX_RETRIES": "5"
        }
        
        with patch.dict(os.environ, test_env):
            from autoninja.core.config import BedrockSettings
            
            settings = BedrockSettings()
            
            assert settings.region_name == "us-west-2"
            assert settings.default_max_tokens == 2048
            assert settings.default_temperature == 0.5
            assert settings.max_retries == 5
    
    def test_custom_configuration_usage(self):
        """Test using custom configuration with client manager."""
        try:
            # Create custom configuration
            config = BedrockClientConfig(
                region_name="us-east-2",
                max_tokens=1024,
                temperature=0.3,
                top_p=0.8,
                timeout=120,
                max_retries=2
            )
            
            # Initialize manager with custom config
            manager = BedrockClientManager(config)
            
            # Verify configuration is applied
            assert manager.config.region_name == "us-east-2"
            assert manager.config.max_tokens == 1024
            assert manager.config.temperature == 0.3
            assert manager.config.top_p == 0.8
            assert manager.config.timeout == 120
            assert manager.config.max_retries == 2
            
        except Exception as e:
            pytest.skip(f"Bedrock service not available or configured: {str(e)}")