"""
Real LLM Validation Test

This script makes actual calls to Bedrock LLM to generate agent outputs
and then validates them using the validation system.
"""

import json
import logging
import os
from datetime import datetime, UTC
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from autoninja.models.state import AgentOutput
from autoninja.audit.integration import ComprehensiveAuditSystem
from autoninja.agents.requirements_analyst import RequirementsAnalystAgent
from autoninja.agents.solution_architect import SolutionArchitectAgent
from autoninja.agents.code_generator import CodeGeneratorAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_real_requirements_analyst():
    """Test Requirements Analyst with real Bedrock LLM call"""
    logger.info("=== Testing Requirements Analyst with Real LLM Call ===")
    
    try:
        # Create Requirements Analyst agent
        req_agent = RequirementsAnalystAgent()
        
        # Test with a simple user request
        user_request = "I want to build a chatbot that can help customers with product questions and order status"
        session_id = "real_test_001"
        
        logger.info(f"User Request: {user_request}")
        logger.info("Calling Requirements Analyst...")
        
        # Make actual LLM call
        result = req_agent.analyze_requirements(
            user_request=user_request,
            session_id=session_id
        )
        
        logger.info("Requirements Analyst completed successfully!")
        logger.info(f"Confidence Score: {result.output.confidence_score}")
        logger.info(f"Execution Time: {result.execution_metadata.duration_seconds:.2f}s")
        
        # Print the actual output structure
        logger.info("=== ACTUAL OUTPUT STRUCTURE ===")
        output_keys = list(result.output.result.keys())
        logger.info(f"Top-level keys: {output_keys}")
        
        for key, value in result.output.result.items():
            if isinstance(value, dict):
                logger.info(f"{key}: {list(value.keys())}")
            elif isinstance(value, list):
                logger.info(f"{key}: list with {len(value)} items")
            else:
                logger.info(f"{key}: {type(value).__name__}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Requirements Analyst test: {str(e)}")
        return None


def test_real_solution_architect(requirements_output: AgentOutput):
    """Test Solution Architect with real Bedrock LLM call"""
    logger.info("=== Testing Solution Architect with Real LLM Call ===")
    
    if not requirements_output:
        logger.error("No requirements output provided")
        return None
    
    try:
        # Create Solution Architect agent
        arch_agent = SolutionArchitectAgent()
        
        session_id = "real_test_001"
        
        logger.info("Calling Solution Architect...")
        
        # Make actual LLM call
        result = arch_agent.design_architecture(
            requirements_output=requirements_output,
            session_id=session_id
        )
        
        logger.info("Solution Architect completed successfully!")
        logger.info(f"Confidence Score: {result.output.confidence_score}")
        logger.info(f"Execution Time: {result.execution_metadata.duration_seconds:.2f}s")
        
        # Print the actual output structure
        logger.info("=== ACTUAL OUTPUT STRUCTURE ===")
        output_keys = list(result.output.result.keys())
        logger.info(f"Top-level keys: {output_keys}")
        
        for key, value in result.output.result.items():
            if isinstance(value, dict):
                logger.info(f"{key}: {list(value.keys())}")
            elif isinstance(value, list):
                logger.info(f"{key}: list with {len(value)} items")
            else:
                logger.info(f"{key}: {type(value).__name__}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Solution Architect test: {str(e)}")
        return None


def test_real_code_generator(architecture_output: AgentOutput):
    """Test Code Generator with real Bedrock LLM call"""
    logger.info("=== Testing Code Generator with Real LLM Call ===")
    
    if not architecture_output:
        logger.error("No architecture output provided")
        return None
    
    try:
        # Create Code Generator agent
        code_agent = CodeGeneratorAgent()
        
        session_id = "real_test_001"
        
        logger.info("Calling Code Generator...")
        
        # Make actual LLM call
        result = code_agent.generate_code(
            architecture_output=architecture_output,
            session_id=session_id
        )
        
        logger.info("Code Generator completed successfully!")
        logger.info(f"Confidence Score: {result.output.confidence_score}")
        logger.info(f"Execution Time: {result.execution_metadata.duration_seconds:.2f}s")
        
        # Print the actual output structure
        logger.info("=== ACTUAL OUTPUT STRUCTURE ===")
        output_keys = list(result.output.result.keys())
        logger.info(f"Top-level keys: {output_keys}")
        
        for key, value in result.output.result.items():
            if isinstance(value, dict):
                logger.info(f"{key}: {list(value.keys())}")
            elif isinstance(value, list):
                logger.info(f"{key}: list with {len(value)} items")
            else:
                logger.info(f"{key}: {type(value).__name__}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Code Generator test: {str(e)}")
        return None


def validate_real_outputs(agent_outputs: Dict[str, AgentOutput]):
    """Validate the real LLM outputs"""
    logger.info("=== Validating Real LLM Outputs ===")
    
    # Initialize audit system
    audit_system = ComprehensiveAuditSystem()
    
    # Perform comprehensive audit
    audit_results = audit_system.audit_agent_outputs(
        agent_outputs=agent_outputs,
        session_id="real_validation_test",
        generate_report=True
    )
    
    # Print detailed results
    logger.info("=== VALIDATION RESULTS ===")
    logger.info(f"Overall Status: {audit_results['audit_summary']['overall_status']}")
    logger.info(f"Agents Passed: {audit_results['audit_summary']['agents_summary']['passed']}")
    logger.info(f"Agents Failed: {audit_results['audit_summary']['agents_summary']['failed']}")
    logger.info(f"Total Errors: {audit_results['audit_summary']['issues_summary']['total_errors']}")
    logger.info(f"Total Warnings: {audit_results['audit_summary']['issues_summary']['total_warnings']}")
    logger.info(f"Average Quality Score: {audit_results['audit_summary']['scores']['average_quality_score']:.2f}")
    logger.info(f"Average Compatibility Score: {audit_results['audit_summary']['scores']['average_compatibility_score']:.2f}")
    
    # Show detailed validation results for each agent
    for agent_name, validation_result in audit_results['validation_results'].items():
        logger.info(f"\n--- {agent_name.upper()} VALIDATION ---")
        logger.info(f"Valid: {validation_result['is_valid']}")
        logger.info(f"Quality Score: {validation_result['quality_score']:.2f}")
        logger.info(f"Compatibility Score: {validation_result['compatibility_score']:.2f}")
        logger.info(f"Errors: {len(validation_result['validation_errors'])}")
        logger.info(f"Warnings: {len(validation_result['warnings'])}")
        
        if validation_result['validation_errors']:
            logger.info("Validation Errors:")
            for error in validation_result['validation_errors']:
                logger.info(f"  - {error['field_name']}: {error['error_message']}")
                logger.info(f"    Severity: {error['severity']}")
                logger.info(f"    Remediation: {error['remediation_suggestion']}")
        
        if validation_result['warnings']:
            logger.info("Warnings:")
            for warning in validation_result['warnings']:
                logger.info(f"  - {warning}")
        
        if validation_result['recommendations']:
            logger.info("Recommendations:")
            for rec in validation_result['recommendations']:
                logger.info(f"  - {rec}")
    
    # Show compatibility results
    logger.info("\n=== COMPATIBILITY RESULTS ===")
    for pair_name, compat_result in audit_results['compatibility_results'].items():
        logger.info(f"\n--- {pair_name.upper()} ---")
        logger.info(f"Compatible: {compat_result['is_valid']}")
        logger.info(f"Compatibility Level: {compat_result['compatibility_level']}")
        logger.info(f"Data Flow Score: {compat_result['data_flow_score']:.2f}")
        logger.info(f"Missing Mappings: {len(compat_result['missing_mappings'])}")
        logger.info(f"Invalid Mappings: {len(compat_result['invalid_mappings'])}")
        logger.info(f"Semantic Issues: {len(compat_result['semantic_issues'])}")
        
        if compat_result['missing_mappings']:
            logger.info("Missing Mappings:")
            for mapping in compat_result['missing_mappings']:
                logger.info(f"  - {mapping['source_field']} → {mapping['target_field']}")
        
        if compat_result['semantic_issues']:
            logger.info("Semantic Issues:")
            for issue in compat_result['semantic_issues']:
                logger.info(f"  - {issue}")
        
        if compat_result['recommendations']:
            logger.info("Recommendations:")
            for rec in compat_result['recommendations']:
                logger.info(f"  - {rec}")
    
    return audit_results


def main():
    """Main test function"""
    logger.info("Starting Real LLM Validation Test")
    
    # Check if AWS credentials are available
    if not os.getenv('AWS_ACCESS_KEY_ID') and not os.path.exists(os.path.expanduser('~/.aws/credentials')):
        logger.warning("AWS credentials not found. This test requires AWS Bedrock access.")
        logger.info("Please configure AWS credentials to run this test.")
        return
    
    agent_outputs = {}
    
    # Step 1: Test Requirements Analyst
    req_output = test_real_requirements_analyst()
    if req_output:
        agent_outputs["requirements_analyst"] = req_output
        
        # Save the raw output for inspection
        with open("real_requirements_output.json", "w") as f:
            json.dump(req_output.output.result, f, indent=2, default=str)
        logger.info("Requirements output saved to real_requirements_output.json")
    
    # Step 2: Test Solution Architect (if requirements succeeded)
    if req_output:
        arch_output = test_real_solution_architect(req_output)
        if arch_output:
            agent_outputs["solution_architect"] = arch_output
            
            # Save the raw output for inspection
            with open("real_architecture_output.json", "w") as f:
                json.dump(arch_output.output.result, f, indent=2, default=str)
            logger.info("Architecture output saved to real_architecture_output.json")
    
    # Step 3: Test Code Generator (if architecture succeeded)
    if "solution_architect" in agent_outputs:
        code_output = test_real_code_generator(agent_outputs["solution_architect"])
        if code_output:
            agent_outputs["code_generator"] = code_output
            
            # Save the raw output for inspection
            with open("real_code_output.json", "w") as f:
                json.dump(code_output.output.result, f, indent=2, default=str)
            logger.info("Code output saved to real_code_output.json")
    
    # Step 4: Validate all outputs
    if agent_outputs:
        logger.info(f"\nValidating {len(agent_outputs)} real agent outputs...")
        audit_results = validate_real_outputs(agent_outputs)
        
        # Save complete audit results
        with open("real_audit_results.json", "w") as f:
            json.dump(audit_results, f, indent=2, default=str)
        logger.info("Complete audit results saved to real_audit_results.json")
        
        logger.info("\n=== SUMMARY ===")
        logger.info(f"Successfully tested {len(agent_outputs)} agents with real LLM calls")
        logger.info(f"Validation Status: {audit_results['audit_summary']['overall_status']}")
        logger.info("Check the generated JSON files for detailed outputs and results")
    else:
        logger.error("No agent outputs were generated successfully")
    
    logger.info("Real LLM Validation Test Completed!")


if __name__ == "__main__":
    main()