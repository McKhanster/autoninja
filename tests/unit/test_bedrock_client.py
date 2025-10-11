"""
Unit tests for Bedrock client configuration and management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from autoninja.core.bedrock_client import (
    BedrockClientManager,
    BedrockClientConfig,
    BedrockCircuitBreaker,
    TaskComplexity,
    BedrockModelId,
    get_bedrock_client_manager,
    reset_client_manager
)


class TestBedrockCircuitBreaker:
    """Test cases for BedrockCircuitBreaker."""
    
    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        cb = BedrockCircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.is_available() is True
        assert cb.failure_count == 0
    
    def test_record_success_resets_failures(self):
        """Test that recording success resets failure count."""
        cb = BedrockCircuitBreaker()
        cb.failure_count = 3
        cb.record_success()
        
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"
    
    def test_record_failure_increments_count(self):
        """Test that recording failure increments failure count."""
        cb = BedrockCircuitBreaker()
        cb.record_failure()
        
        assert cb.failure_count == 1
        assert cb.last_failure_time is not None
    
    def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after reaching failure threshold."""
        cb = BedrockCircuitBreaker(failure_threshold=3)
        
        # Record failures up to threshold
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == "OPEN"
        assert cb.is_available() is False
    
    def test_circuit_transitions_to_half_open(self):
        """Test that circuit transitions to HALF_OPEN after recovery timeout."""
        cb = BedrockCircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        # Open the circuit
        cb.record_failure()
        assert cb.state == "OPEN"
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Should transition to HALF_OPEN
        assert cb.is_available() is True
        assert cb.state == "HALF_OPEN"


class TestBedrockClientConfig:
    """Test cases for BedrockClientConfig."""
    
    def test_default_config_values(self):
        """Test that default configuration values are set correctly."""
        config = BedrockClientConfig()
        
        assert config.region_name == "us-east-2"
        assert config.max_tokens == 4096
        assert config.temperature == 0.1
        assert config.top_p == 0.9
        assert config.timeout == 300
        assert config.max_retries == 3
    
    def test_custom_config_values(self):
        """Test that custom configuration values are set correctly."""
        config = BedrockClientConfig(
            region_name="us-west-2",
            max_tokens=2048,
            temperature=0.5,
            top_p=0.8,
            timeout=180,
            max_retries=5
        )
        
        assert config.region_name == "us-west-2"
        assert config.max_tokens == 2048
        assert config.temperature == 0.5
        assert config.top_p == 0.8
        assert config.timeout == 180
        assert config.max_retries == 5


class TestBedrockClientManager:
    """Test cases for BedrockClientManager."""
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    @patch('autoninja.core.bedrock_client.ChatBedrock')
    def test_initialization_success(self, mock_chat_bedrock, mock_session):
        """Test successful client manager initialization."""
        # Mock AWS session and credentials
        mock_credentials = Mock()
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock ChatBedrock client
        mock_client = Mock()
        mock_chat_bedrock.return_value = mock_client
        
        config = BedrockClientConfig()
        manager = BedrockClientManager(config)
        
        # Verify clients were created for each model
        assert len(manager._clients) == len(BedrockModelId)
        assert len(manager._circuit_breakers) == len(BedrockModelId)
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    def test_initialization_no_credentials(self, mock_session):
        """Test initialization failure when no AWS credentials are found."""
        # Mock no credentials
        mock_session.return_value.get_credentials.return_value = None
        
        with pytest.raises(ValueError, match="AWS credentials not found"):
            BedrockClientManager()
    
    def test_model_selection_by_complexity(self):
        """Test model selection based on task complexity."""
        with patch('autoninja.core.bedrock_client.boto3.Session'), \
             patch('autoninja.core.bedrock_client.ChatBedrock'):
            
            # Mock credentials
            with patch.object(BedrockClientManager, '_initialize_clients'):
                manager = BedrockClientManager()
            
            # Test complexity mappings
            assert manager.select_model_by_complexity(TaskComplexity.LOW) == BedrockModelId.CLAUDE_SONNET_4_5
            assert manager.select_model_by_complexity(TaskComplexity.MEDIUM) == BedrockModelId.CLAUDE_SONNET_4_5
            assert manager.select_model_by_complexity(TaskComplexity.HIGH) == BedrockModelId.CLAUDE_SONNET_4_5
            assert manager.select_model_by_complexity(TaskComplexity.CRITICAL) == BedrockModelId.CLAUDE_SONNET_4_5
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    @patch('autoninja.core.bedrock_client.ChatBedrock')
    def test_get_client_success(self, mock_chat_bedrock, mock_session):
        """Test successful client retrieval."""
        # Mock AWS session and credentials
        mock_credentials = Mock()
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock ChatBedrock client
        mock_client = Mock()
        mock_chat_bedrock.return_value = mock_client
        
        manager = BedrockClientManager()
        client = manager.get_client(BedrockModelId.CLAUDE_SONNET_4_5)
        
        assert client is not None
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    @patch('autoninja.core.bedrock_client.ChatBedrock')
    def test_get_client_circuit_breaker_open(self, mock_chat_bedrock, mock_session):
        """Test client retrieval when circuit breaker is open."""
        # Mock AWS session and credentials
        mock_credentials = Mock()
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock ChatBedrock client
        mock_client = Mock()
        mock_chat_bedrock.return_value = mock_client
        
        manager = BedrockClientManager()
        
        # Open the circuit breaker
        model_key = BedrockModelId.CLAUDE_SONNET_4_5.value
        manager._circuit_breakers[model_key].state = "OPEN"
        
        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            manager.get_client(BedrockModelId.CLAUDE_SONNET_4_5)
    
    def test_get_client_not_available(self):
        """Test client retrieval for unavailable model."""
        with patch.object(BedrockClientManager, '_initialize_clients'):
            manager = BedrockClientManager()
            manager._clients = {}  # No clients available
            
            with pytest.raises(ValueError, match="Client not available"):
                manager.get_client(BedrockModelId.CLAUDE_SONNET_4_5)
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    @patch('autoninja.core.bedrock_client.ChatBedrock')
    def test_invoke_with_retry_success(self, mock_chat_bedrock, mock_session):
        """Test successful model invocation with retry logic."""
        # Mock AWS session and credentials
        mock_credentials = Mock()
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock ChatBedrock client
        mock_client = Mock()
        mock_response = Mock()
        mock_client.invoke.return_value = mock_response
        mock_chat_bedrock.return_value = mock_client
        
        manager = BedrockClientManager()
        
        messages = [{"role": "user", "content": "Hello"}]
        response = manager.invoke_with_retry(BedrockModelId.CLAUDE_SONNET_4_5, messages)
        
        assert response == mock_response
        mock_client.invoke.assert_called_once_with(messages)
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    @patch('autoninja.core.bedrock_client.ChatBedrock')
    def test_invoke_with_retry_circuit_breaker_open(self, mock_chat_bedrock, mock_session):
        """Test model invocation when circuit breaker is open."""
        # Mock AWS session and credentials
        mock_credentials = Mock()
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock ChatBedrock client
        mock_client = Mock()
        mock_chat_bedrock.return_value = mock_client
        
        manager = BedrockClientManager()
        
        # Open the circuit breaker
        model_key = BedrockModelId.CLAUDE_SONNET_4_5.value
        manager._circuit_breakers[model_key].state = "OPEN"
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            manager.invoke_with_retry(BedrockModelId.CLAUDE_SONNET_4_5, messages)
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    @patch('autoninja.core.bedrock_client.ChatBedrock')
    def test_get_available_models(self, mock_chat_bedrock, mock_session):
        """Test getting available models."""
        # Mock AWS session and credentials
        mock_credentials = Mock()
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock ChatBedrock client
        mock_client = Mock()
        mock_chat_bedrock.return_value = mock_client
        
        manager = BedrockClientManager()
        available_models = manager.get_available_models()
        
        # All models should be available initially
        assert len(available_models) == len(BedrockModelId)
        assert all(isinstance(model, BedrockModelId) for model in available_models)
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    @patch('autoninja.core.bedrock_client.ChatBedrock')
    def test_get_client_status(self, mock_chat_bedrock, mock_session):
        """Test getting client status information."""
        # Mock AWS session and credentials
        mock_credentials = Mock()
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock ChatBedrock client
        mock_client = Mock()
        mock_chat_bedrock.return_value = mock_client
        
        manager = BedrockClientManager()
        status = manager.get_client_status()
        
        # Verify status structure
        assert len(status) == len(BedrockModelId)
        
        for model_id in BedrockModelId:
            model_status = status[model_id.value]
            assert "available" in model_status
            assert "circuit_breaker_state" in model_status
            assert "failure_count" in model_status
            assert "last_failure_time" in model_status


class TestGlobalClientManager:
    """Test cases for global client manager functions."""
    
    def teardown_method(self):
        """Reset global client manager after each test."""
        reset_client_manager()
    
    @patch('autoninja.core.bedrock_client.boto3.Session')
    @patch('autoninja.core.bedrock_client.ChatBedrock')
    def test_get_bedrock_client_manager_singleton(self, mock_chat_bedrock, mock_session):
        """Test that get_bedrock_client_manager returns singleton instance."""
        # Mock AWS session and credentials
        mock_credentials = Mock()
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock ChatBedrock client
        mock_client = Mock()
        mock_chat_bedrock.return_value = mock_client
        
        manager1 = get_bedrock_client_manager()
        manager2 = get_bedrock_client_manager()
        
        assert manager1 is manager2
    
    def test_reset_client_manager(self):
        """Test that reset_client_manager clears the global instance."""
        with patch('autoninja.core.bedrock_client.boto3.Session'), \
             patch('autoninja.core.bedrock_client.ChatBedrock'):
            
            # Get initial manager
            manager1 = get_bedrock_client_manager()
            
            # Reset and get new manager
            reset_client_manager()
            manager2 = get_bedrock_client_manager()
            
            assert manager1 is not manager2