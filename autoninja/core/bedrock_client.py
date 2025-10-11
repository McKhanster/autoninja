"""
Bedrock ChatBedrock client configuration and management.

This module provides configuration and management for Amazon Bedrock ChatBedrock clients,
including model selection logic and error handling with retry mechanisms.
"""

import logging
import time
from enum import Enum
from typing import Dict, Optional, Any
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from langchain_aws import ChatBedrock
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for model selection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BedrockModelId(Enum):
    """Available Bedrock model identifiers."""
    CLAUDE_SONNET_4_5 = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


@dataclass
class BedrockClientConfig:
    """Configuration for Bedrock client initialization."""
    region_name: str = "us-east-2"
    max_tokens: int = 4096
    temperature: float = 0.1
    top_p: float = 0.9
    timeout: int = 300
    max_retries: int = 3


class BedrockCircuitBreaker:
    """Circuit breaker pattern implementation for Bedrock API calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_available(self) -> bool:
        """Check if the circuit breaker allows requests."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class BedrockClientManager:
    """Manages Bedrock ChatBedrock clients with model selection and error handling."""
    
    def __init__(self, config: Optional[BedrockClientConfig] = None):
        self.config = config or BedrockClientConfig()
        self._clients: Dict[str, ChatBedrock] = {}
        self._circuit_breakers: Dict[str, BedrockCircuitBreaker] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize ChatBedrock clients for available models."""
        try:
            # Verify AWS credentials and region
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if not credentials:
                raise ValueError("AWS credentials not found. Please configure AWS credentials.")
            
            # Initialize clients for each model
            for model_id in BedrockModelId:
                client_key = model_id.value
                
                try:
                    client = ChatBedrock(
                        model_id=model_id.value,
                        region_name=self.config.region_name,
                        model_kwargs={
                            "max_tokens": self.config.max_tokens,
                            "temperature": self.config.temperature,
                            # Note: Claude models don't support both temperature and top_p
                            # Using only temperature for better compatibility
                        },
                        streaming=False,
                        verbose=False
                    )
                    
                    self._clients[client_key] = client
                    self._circuit_breakers[client_key] = BedrockCircuitBreaker()
                    
                    logger.info(f"Initialized Bedrock client for model: {model_id.value}")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize client for {model_id.value}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock clients: {str(e)}")
            raise
    
    def select_model_by_complexity(self, complexity: TaskComplexity) -> BedrockModelId:
        """
        Select the optimal model based on task complexity.
        
        Args:
            complexity: The complexity level of the task
            
        Returns:
            BedrockModelId: The selected model identifier
        """
        model_mapping = {
            TaskComplexity.LOW: BedrockModelId.CLAUDE_SONNET_4_5,
            TaskComplexity.MEDIUM: BedrockModelId.CLAUDE_SONNET_4_5,
            TaskComplexity.HIGH: BedrockModelId.CLAUDE_SONNET_4_5,
            TaskComplexity.CRITICAL: BedrockModelId.CLAUDE_SONNET_4_5
        }
        
        selected_model = model_mapping.get(complexity, BedrockModelId.CLAUDE_SONNET_4_5)
        logger.info(f"Selected model {selected_model.value} for complexity {complexity.value}")
        
        return selected_model
    
    def get_client(self, model_id: BedrockModelId) -> ChatBedrock:
        """
        Get a ChatBedrock client for the specified model.
        
        Args:
            model_id: The Bedrock model identifier
            
        Returns:
            ChatBedrock: The configured client
            
        Raises:
            ValueError: If the model client is not available
            RuntimeError: If the circuit breaker is open
        """
        client_key = model_id.value
        
        if client_key not in self._clients:
            raise ValueError(f"Client not available for model: {model_id.value}")
        
        circuit_breaker = self._circuit_breakers[client_key]
        if not circuit_breaker.is_available():
            raise RuntimeError(f"Circuit breaker is open for model: {model_id.value}")
        
        return self._clients[client_key]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def invoke_with_retry(
        self, 
        model_id: BedrockModelId, 
        messages: Any,
        **kwargs
    ) -> Any:
        """
        Invoke a Bedrock model with retry logic and circuit breaker protection.
        
        Args:
            model_id: The Bedrock model to use
            messages: The messages to send to the model
            **kwargs: Additional arguments for the model invocation
            
        Returns:
            The model response
            
        Raises:
            RuntimeError: If the circuit breaker is open or max retries exceeded
            ValueError: If the model client is not available
        """
        client_key = model_id.value
        circuit_breaker = self._circuit_breakers[client_key]
        
        try:
            if not circuit_breaker.is_available():
                raise RuntimeError(f"Circuit breaker is open for model: {model_id.value}")
            
            client = self.get_client(model_id)
            
            # Invoke the model
            response = client.invoke(messages, **kwargs)
            
            # Record success
            circuit_breaker.record_success()
            
            logger.debug(f"Successfully invoked model {model_id.value}")
            return response
            
        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            
            logger.error(f"Failed to invoke model {model_id.value}: {str(e)}")
            raise
    
    def get_available_models(self) -> list[BedrockModelId]:
        """
        Get a list of available model identifiers.
        
        Returns:
            List of available BedrockModelId values
        """
        available_models = []
        for model_id in BedrockModelId:
            if model_id.value in self._clients:
                circuit_breaker = self._circuit_breakers[model_id.value]
                if circuit_breaker.is_available():
                    available_models.append(model_id)
        
        return available_models
    
    def get_client_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all clients and their circuit breakers.
        
        Returns:
            Dictionary containing status information for each client
        """
        status = {}
        
        for model_id in BedrockModelId:
            client_key = model_id.value
            circuit_breaker = self._circuit_breakers.get(client_key)
            
            status[client_key] = {
                "available": client_key in self._clients,
                "circuit_breaker_state": circuit_breaker.state if circuit_breaker else "N/A",
                "failure_count": circuit_breaker.failure_count if circuit_breaker else 0,
                "last_failure_time": circuit_breaker.last_failure_time if circuit_breaker else None
            }
        
        return status


# Global client manager instance
_client_manager: Optional[BedrockClientManager] = None


def get_bedrock_client_manager(config: Optional[BedrockClientConfig] = None) -> BedrockClientManager:
    """
    Get the global Bedrock client manager instance.
    
    Args:
        config: Optional configuration for the client manager
        
    Returns:
        BedrockClientManager: The global client manager instance
    """
    global _client_manager
    
    if _client_manager is None:
        _client_manager = BedrockClientManager(config)
    
    return _client_manager


def reset_client_manager():
    """Reset the global client manager instance (mainly for testing)."""
    global _client_manager
    _client_manager = None