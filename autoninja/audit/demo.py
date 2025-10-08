"""
Demo script for testing the audit system infrastructure.

This script demonstrates the basic functionality of the audit system
including configuration, logging, validation, and orchestration.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import autoninja modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from autoninja.audit import (
    AuditConfig, 
    ThreeAgentOrchestrator, 
    PipelineAuditLogger,
    AgentOutputValidator
)


def demo_audit_system():
    """Demonstrate the audit system functionality."""
    print("=== AutoNinja Audit System Demo ===\n")
    
    # 1. Load configuration
    print("1. Loading audit configuration...")
    config = AuditConfig()
    print(f"   - Agent timeout: {config.agent_timeout_seconds}s")
    print(f"   - Validation enabled: {config.validation_enabled}")
    print(f"   - Log level: {config.log_level}")
    print(f"   - Required fields for requirements_analyst: {config.required_fields_by_agent['requirements_analyst']}")
    print()
    
    # 2. Initialize audit logger
    print("2. Initializing audit logger...")
    audit_logger = PipelineAuditLogger(config)
    print("   - Audit logger initialized")
    print("   - Log files will be created in ./logs/ directory")
    print()
    
    # 3. Initialize validator
    print("3. Initializing output validator...")
    validator = AgentOutputValidator(config)
    print("   - Output validator initialized")
    print()
    
    # 4. Test validation with mock data
    print("4. Testing validation with mock data...")
    
    # Test Requirements Analyst output validation
    mock_requirements_output = {
        "extracted_requirements": ["AI conversation", "Memory management"],
        "compliance_frameworks": ["AWS Well-Architected"],
        "structured_specifications": {
            "functional_requirements": ["Process natural language"],
            "non_functional_requirements": ["Response time < 2s"]
        }
    }
    
    validation_result = validator.validate_requirements_output(mock_requirements_output)
    print(f"   - Requirements validation: {'PASSED' if validation_result.is_valid else 'FAILED'}")
    print(f"   - Compatibility score: {validation_result.compatibility_score:.2f}")
    if validation_result.warnings:
        print(f"   - Warnings: {validation_result.warnings}")
    print()
    
    # 5. Initialize orchestrator
    print("5. Initializing three-agent orchestrator...")
    orchestrator = ThreeAgentOrchestrator(config)
    print("   - Orchestrator initialized")
    print("   - Ready to execute three-agent pipeline")
    print()
    
    # 6. Test pipeline execution (with mock agents)
    print("6. Testing pipeline execution...")
    user_request = "I would like a companion AI"
    print(f"   - User request: '{user_request}'")
    
    try:
        execution = orchestrator.execute_three_agent_pipeline(user_request)
        print(f"   - Pipeline execution status: {execution.status.value}")
        print(f"   - Session ID: {execution.session_id}")
        print(f"   - Execution time: {execution.execution_time_seconds:.2f}s")
        print(f"   - Number of agent executions: {len(execution.agent_executions)}")
        
        # Show agent execution details
        for agent_exec in execution.agent_executions:
            print(f"     - {agent_exec.agent_name}: {agent_exec.status.value} ({agent_exec.execution_time_seconds:.2f}s)")
        
        # Generate audit report
        print("\n7. Generating audit report...")
        report_path = orchestrator.generate_audit_report(execution.session_id)
        print(f"   - Audit report saved to: {report_path}")
        
    except Exception as e:
        print(f"   - Pipeline execution failed: {str(e)}")
    
    print("\n=== Demo completed ===")
    print("Check the ./logs/ directory for detailed audit logs.")


if __name__ == "__main__":
    demo_audit_system()