#!/usr/bin/env python3
"""
Basic functionality test for Bedrock client implementation.

This script tests the core functionality without external dependencies.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all modules can be imported correctly."""
    print("Testing imports...")
    
    try:
        from autoninja.core.bedrock_client import (
            BedrockClientManager,
            BedrockClientConfig,
            BedrockCircuitBreaker,
            TaskComplexity,
            BedrockModelId
        )
        print("✅ Bedrock client imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        return False


def test_enums():
    """Test enum definitions."""
    print("Testing enums...")
    
    try:
        from autoninja.core.bedrock_client import TaskComplexity, BedrockModelId
        
        # Test TaskComplexity enum
        complexities = [TaskComplexity.LOW, TaskComplexity.MEDIUM, TaskComplexity.HIGH, TaskComplexity.CRITICAL]
        assert len(complexities) == 4
        print(f"✅ TaskComplexity enum: {[c.value for c in complexities]}")
        
        # Test BedrockModelId enum
        models = list(BedrockModelId)
        assert len(models) >= 3  # Should have at least 3 models
        print(f"✅ BedrockModelId enum: {[m.value for m in models]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enum test error: {str(e)}")
        return False


def test_config():
    """Test configuration classes."""
    print("Testing configuration...")
    
    try:
        from autoninja.core.bedrock_client import BedrockClientConfig
        
        # Test default config
        config = BedrockClientConfig()
        assert config.region_name == "us-east-2"
        assert config.max_tokens == 4096
        assert config.temperature == 0.1
        print("✅ Default configuration created successfully")
        
        # Test custom config
        custom_config = BedrockClientConfig(
            region_name="us-west-2",
            max_tokens=2048,
            temperature=0.5
        )
        assert custom_config.region_name == "us-west-2"
        assert custom_config.max_tokens == 2048
        assert custom_config.temperature == 0.5
        print("✅ Custom configuration created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test error: {str(e)}")
        return False


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("Testing circuit breaker...")
    
    try:
        from autoninja.core.bedrock_client import BedrockCircuitBreaker
        
        # Test initial state
        cb = BedrockCircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.is_available() is True
        assert cb.failure_count == 0
        print("✅ Circuit breaker initial state correct")
        
        # Test failure recording
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.last_failure_time is not None
        print("✅ Circuit breaker failure recording works")
        
        # Test success recording
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"
        print("✅ Circuit breaker success recording works")
        
        # Test threshold behavior
        cb_threshold = BedrockCircuitBreaker(failure_threshold=2)
        cb_threshold.record_failure()
        cb_threshold.record_failure()
        assert cb_threshold.state == "OPEN"
        assert cb_threshold.is_available() is False
        print("✅ Circuit breaker threshold behavior works")
        
        return True
        
    except Exception as e:
        print(f"❌ Circuit breaker test error: {str(e)}")
        return False


def test_model_selection_logic():
    """Test model selection logic without AWS dependencies."""
    print("Testing model selection logic...")
    
    try:
        from autoninja.core.bedrock_client import BedrockClientManager, TaskComplexity, BedrockModelId
        
        # Create a manager instance without initializing AWS clients
        # We'll patch the initialization to avoid AWS calls
        class TestManager(BedrockClientManager):
            def _initialize_clients(self):
                # Skip AWS initialization for testing
                pass
        
        manager = TestManager()
        
        # Test model selection
        low_model = manager.select_model_by_complexity(TaskComplexity.LOW)
        medium_model = manager.select_model_by_complexity(TaskComplexity.MEDIUM)
        high_model = manager.select_model_by_complexity(TaskComplexity.HIGH)
        critical_model = manager.select_model_by_complexity(TaskComplexity.CRITICAL)
        
        assert low_model == BedrockModelId.CLAUDE_HAIKU_3
        assert medium_model == BedrockModelId.CLAUDE_SONNET_4_5
        assert high_model == BedrockModelId.CLAUDE_OPUS_4_1
        assert critical_model == BedrockModelId.CLAUDE_OPUS_4_1
        
        print("✅ Model selection logic works correctly")
        print(f"   LOW -> {low_model.value}")
        print(f"   MEDIUM -> {medium_model.value}")
        print(f"   HIGH -> {high_model.value}")
        print(f"   CRITICAL -> {critical_model.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model selection test error: {str(e)}")
        return False


def test_configuration_module():
    """Test configuration module."""
    print("Testing configuration module...")
    
    try:
        from autoninja.core.config import BedrockSettings, AutoNinjaSettings
        
        # Test BedrockSettings
        bedrock_settings = BedrockSettings()
        assert bedrock_settings.region_name == "us-east-2"
        assert bedrock_settings.default_max_tokens == 4096
        print("✅ BedrockSettings created successfully")
        
        # Test AutoNinjaSettings
        app_settings = AutoNinjaSettings()
        assert app_settings.app_name == "AutoNinja AWS Bedrock"
        assert app_settings.environment == "development"
        print("✅ AutoNinjaSettings created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration module test error: {str(e)}")
        return False


def main():
    """Run all basic functionality tests."""
    print("Running basic functionality tests for Bedrock client implementation...")
    print("=" * 70)
    
    tests = [
        ("Imports", test_imports),
        ("Enums", test_enums),
        ("Configuration", test_config),
        ("Circuit Breaker", test_circuit_breaker),
        ("Model Selection Logic", test_model_selection_logic),
        ("Configuration Module", test_configuration_module),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'-' * 50}")
        print(f"Running: {test_name}")
        print(f"{'-' * 50}")
        
        try:
            result = test_func()
            results[test_name] = result
            
        except Exception as e:
            print(f"❌ {test_name} ERROR: {str(e)}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'=' * 70}")
    print("TEST SUMMARY")
    print(f"{'=' * 70}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic functionality tests passed!")
        print("\nThe Bedrock client implementation is ready for use.")
        print("Next steps:")
        print("1. Configure AWS credentials")
        print("2. Run examples/demo_bedrock_client.py to test with real AWS services")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. Check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)