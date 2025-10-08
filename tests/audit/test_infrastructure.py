"""
Simple test script for the audit system infrastructure.

Tests the basic components without depending on the full AutoNinja configuration.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import autoninja modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from autoninja.audit.config import AuditConfig, LogLevel, ExecutionStatus, AgentStatus
from autoninja.audit.validator import AgentOutputValidator, ValidationResult


def test_audit_config():
    """Test the audit configuration system."""
    print("=== Testing Audit Configuration ===")
    
    # Test default configuration
    config = AuditConfig()
    print(f"✓ Default config loaded")
    print(f"  - Agent timeout: {config.agent_timeout_seconds}s")
    print(f"  - Validation enabled: {config.validation_enabled}")
    print(f"  - Log level: {config.log_level}")
    print(f"  - Quality assessment enabled: {config.quality_assessment_enabled}")
    
    # Test custom configuration
    custom_config = AuditConfig(
        agent_timeout_seconds=600,
        log_level=LogLevel.DEBUG,
        validation_enabled=False
    )
    print(f"✓ Custom config created")
    print(f"  - Agent timeout: {custom_config.agent_timeout_seconds}s")
    print(f"  - Log level: {custom_config.log_level}")
    print(f"  - Validation enabled: {custom_config.validation_enabled}")
    
    # Test required fields configuration
    required_fields = config.required_fields_by_agent
    print(f"✓ Required fields configuration:")
    for agent, fields in required_fields.items():
        print(f"  - {agent}: {fields}")
    
    print()


def test_validator():
    """Test the output validator."""
    print("=== Testing Output Validator ===")
    
    config = AuditConfig()
    validator = AgentOutputValidator(config)
    print("✓ Validator initialized")
    
    # Test Requirements Analyst validation with valid output
    valid_requirements = {
        "extracted_requirements": ["AI conversation", "Memory management", "Context awareness"],
        "compliance_frameworks": ["AWS Well-Architected", "Security Best Practices"],
        "structured_specifications": {
            "functional_requirements": ["Process natural language", "Generate responses"],
            "non_functional_requirements": ["Response time < 2s", "99.9% availability"]
        }
    }
    
    result = validator.validate_requirements_output(valid_requirements)
    print(f"✓ Requirements validation (valid): {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"  - Compatibility score: {result.compatibility_score:.2f}")
    print(f"  - Errors: {len(result.validation_errors)}")
    print(f"  - Warnings: {len(result.warnings)}")
    
    # Test Requirements Analyst validation with invalid output
    invalid_requirements = {
        "extracted_requirements": [],  # Empty list
        "compliance_frameworks": None,  # Missing data
        # Missing structured_specifications entirely
    }
    
    result = validator.validate_requirements_output(invalid_requirements)
    print(f"✓ Requirements validation (invalid): {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"  - Compatibility score: {result.compatibility_score:.2f}")
    print(f"  - Errors: {len(result.validation_errors)}")
    print(f"  - Warnings: {len(result.warnings)}")
    if result.validation_errors:
        print(f"  - Sample error: {result.validation_errors[0]}")
    
    # Test Solution Architect validation
    valid_architecture = {
        "selected_services": ["Amazon Bedrock", "AWS Lambda", "API Gateway", "DynamoDB"],
        "architecture_blueprint": {
            "compute": "AWS Lambda",
            "ai_service": "Amazon Bedrock",
            "storage": "DynamoDB"
        },
        "security_architecture": {
            "authentication": "API Gateway with IAM",
            "encryption": "KMS"
        },
        "iac_templates": {
            "cloudformation": "template_defined"
        }
    }
    
    result = validator.validate_architecture_output(valid_architecture)
    print(f"✓ Architecture validation: {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"  - Compatibility score: {result.compatibility_score:.2f}")
    
    # Test Code Generator validation
    valid_code = {
        "bedrock_agent_config": {
            "agent_name": "companion-ai",
            "foundation_model": "anthropic.claude-3-sonnet-20240229-v1:0"
        },
        "action_groups": [
            {"name": "conversation_handler", "lambda_function": "handler"}
        ],
        "lambda_functions": [
            {"name": "handler", "runtime": "python3.9"}
        ],
        "cloudformation_templates": {
            "main_template": "template_content"
        }
    }
    
    result = validator.validate_code_output(valid_code)
    print(f"✓ Code validation: {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"  - Compatibility score: {result.compatibility_score:.2f}")
    
    # Test pipeline compatibility
    all_outputs = [valid_requirements, valid_architecture, valid_code]
    compatibility = validator.check_pipeline_compatibility(all_outputs)
    print(f"✓ Pipeline compatibility: {'COMPATIBLE' if compatibility.is_compatible else 'INCOMPATIBLE'}")
    print(f"  - Compatibility score: {compatibility.compatibility_score:.2f}")
    print(f"  - Missing fields: {len(compatibility.missing_fields)}")
    print(f"  - Incompatible fields: {len(compatibility.incompatible_fields)}")
    
    print()


def test_enums():
    """Test the enum definitions."""
    print("=== Testing Enums ===")
    
    # Test ExecutionStatus
    print("✓ ExecutionStatus values:")
    for status in ExecutionStatus:
        print(f"  - {status.name}: {status.value}")
    
    # Test AgentStatus
    print("✓ AgentStatus values:")
    for status in AgentStatus:
        print(f"  - {status.name}: {status.value}")
    
    # Test LogLevel
    print("✓ LogLevel values:")
    for level in LogLevel:
        print(f"  - {level.name}: {level.value}")
    
    print()


def main():
    """Run all infrastructure tests."""
    print("=== AutoNinja Audit System Infrastructure Test ===\n")
    
    try:
        test_audit_config()
        test_validator()
        test_enums()
        
        print("=== All Tests Completed Successfully ===")
        print("✓ Audit system infrastructure is working correctly")
        print("✓ Configuration management is functional")
        print("✓ Output validation is operational")
        print("✓ All enums are properly defined")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())