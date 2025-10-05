#!/usr/bin/env python3
"""
Demo script for testing Bedrock client functionality.

This script demonstrates the Bedrock client configuration and usage
without mocking, using real AWS Bedrock services.
"""

import logging
import sys
import os
import boto3

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoninja.core.bedrock_client import (
    BedrockClientManager,
    BedrockClientConfig,
    TaskComplexity,
    BedrockModelId,
    get_bedrock_client_manager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_client_initialization():
    """Test Bedrock client initialization."""
    logger.info("Testing Bedrock client initialization...")
    
    try:
        # Create configuration
        config = BedrockClientConfig(
            region_name="us-east-2",
            max_tokens=1000,
            temperature=0.1
        )
        
        # Initialize client manager
        manager = BedrockClientManager(config)
        
        logger.info(f"Successfully initialized {len(manager._clients)} Bedrock clients")
        
        # Get client status
        status = manager.get_client_status()
        for model_id, model_status in status.items():
            logger.info(f"Model {model_id}: Available={model_status['available']}, "
                       f"Circuit Breaker={model_status['circuit_breaker_state']}")
        
        return manager
        
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock clients: {str(e)}")
        return None


def test_model_selection():
    """Test model selection based on task complexity."""
    logger.info("Testing model selection logic...")
    
    try:
        manager = get_bedrock_client_manager()
        
        # Test different complexity levels
        complexities = [
            TaskComplexity.LOW,
            TaskComplexity.MEDIUM,
            TaskComplexity.HIGH,
            TaskComplexity.CRITICAL
        ]
        
        for complexity in complexities:
            selected_model = manager.select_model_by_complexity(complexity)
            logger.info(f"Complexity {complexity.value} -> Model {selected_model.value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Model selection test failed: {str(e)}")
        return False


def test_available_models():
    """Test getting available models."""
    logger.info("Testing available models...")
    
    try:
        manager = get_bedrock_client_manager()
        available_models = manager.get_available_models()
        
        logger.info(f"Available models: {[m.value for m in available_models]}")
        
        if len(available_models) == 0:
            logger.warning("No models are currently available")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Available models test failed: {str(e)}")
        return False


def test_simple_invocation():
    """Test a simple model invocation."""
    logger.info("Testing simple model invocation...")
    
    try:
        manager = get_bedrock_client_manager()
        
        # Get available models
        available_models = manager.get_available_models()
        if not available_models:
            logger.warning("No models available for testing")
            return False
        
        # Use the first available model (likely Haiku for speed)
        model_id = available_models[0]
        logger.info(f"Using model: {model_id.value}")
        
        # Simple test message
        messages = [{"role": "user", "content": "Say 'Hello from AutoNinja!' and nothing else."}]
        
        # Invoke with retry logic
        response = manager.invoke_with_retry(model_id, messages)
        
        logger.info(f"Model response: {response}")
        
        return True
        
    except Exception as e:
        logger.error(f"Simple invocation test failed: {str(e)}")
        return False


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    logger.info("Testing circuit breaker functionality...")
    
    try:
        manager = get_bedrock_client_manager()
        
        # Get a circuit breaker for testing
        available_models = manager.get_available_models()
        if not available_models:
            logger.warning("No models available for circuit breaker testing")
            return False
        
        model_id = available_models[0]
        circuit_breaker = manager._circuit_breakers[model_id.value]
        
        # Check initial state
        logger.info(f"Initial circuit breaker state: {circuit_breaker.state}")
        logger.info(f"Initial availability: {circuit_breaker.is_available()}")
        
        # Simulate some failures (but don't open the circuit)
        original_threshold = circuit_breaker.failure_threshold
        circuit_breaker.failure_threshold = 10  # Increase threshold for testing
        
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        logger.info(f"After 2 failures - State: {circuit_breaker.state}, "
                   f"Failure count: {circuit_breaker.failure_count}")
        
        # Record success to reset
        circuit_breaker.record_success()
        
        logger.info(f"After success - State: {circuit_breaker.state}, "
                   f"Failure count: {circuit_breaker.failure_count}")
        
        # Restore original threshold
        circuit_breaker.failure_threshold = original_threshold
        
        return True
        
    except Exception as e:
        logger.error(f"Circuit breaker test failed: {str(e)}")
        return False


def main():
    """Run all demo tests."""
    logger.info("Starting Bedrock client demo...")
    
    # Check AWS credentials
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            return False
        
        logger.info(f"Using AWS region: {session.region_name or 'default'}")
        
    except Exception as e:
        logger.error(f"AWS configuration error: {str(e)}")
        return False
    
    # Run tests
    tests = [
        ("Client Initialization", test_client_initialization),
        ("Model Selection", test_model_selection),
        ("Available Models", test_available_models),
        ("Circuit Breaker", test_circuit_breaker),
        ("Simple Invocation", test_simple_invocation),  # This one last as it makes API calls
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.warning(f"⚠️  {test_name} FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} ERROR: {str(e)}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("DEMO SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Bedrock client is working correctly.")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} tests failed. Check configuration and AWS access.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)