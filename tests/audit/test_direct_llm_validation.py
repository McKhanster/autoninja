"""
Direct LLM Validation Test

This script makes direct calls to Bedrock LLM to simulate agent outputs
and then validates them using the validation system.
"""

import json
import boto3
from datetime import datetime, UTC
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from autoninja.models.state import AgentOutput
from autoninja.audit.integration import ComprehensiveAuditSystem
from autoninja.core.logging_config import get_session_logger, log_bedrock_request, log_bedrock_response

# Use the existing logging system
logger = get_session_logger("direct_llm_test")


def call_bedrock_directly(prompt: str, agent_type: str) -> Dict[str, Any]:
    """Make direct call to Bedrock Claude model"""
    try:
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-2')
        
        # Prepare the request
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8000,  # Increased from 4000 to handle comprehensive responses
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        logger.info(f"Calling Bedrock for {agent_type}...")
        
        model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        execution_id = f"test_{agent_type}_{int(datetime.now(UTC).timestamp())}"
        
        # Log the request using the existing logging system
        request_data = {
            "model_id": model_id,
            "body": body,
            "agent_type": agent_type,
            "execution_id": execution_id
        }
        log_bedrock_request(execution_id, request_data)
        
        # Make the call
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Log the response using the existing logging system
        response_data = {
            "model_id": model_id,
            "response_body": response_body,
            "content_length": len(content),
            "agent_type": agent_type,
            "execution_id": execution_id
        }
        log_bedrock_response(execution_id, response_data)
        
        logger.info(f"Bedrock call successful for {agent_type}")
        
        # Try to parse as JSON if it looks like JSON
        logger.info(f"=== PARSING RESPONSE ({agent_type}) ===")
        try:
            if content.strip().startswith('{'):
                logger.info("Content appears to be direct JSON")
                parsed_result = json.loads(content)
                logger.info(f"Successfully parsed as JSON with keys: {list(parsed_result.keys())}")
                return parsed_result
            elif '```json' in content:
                logger.info("Content contains JSON in markdown code block")
                # Extract JSON from markdown code block
                start = content.find('```json') + 7
                end = content.find('```', start)
                if end != -1:
                    json_content = content[start:end].strip()
                    logger.info(f"Extracted JSON content: {json_content[:200]}...")
                    parsed_result = json.loads(json_content)
                    logger.info(f"Successfully parsed JSON with keys: {list(parsed_result.keys())}")
                    return parsed_result
                else:
                    # Handle truncated JSON - try to parse what we have
                    logger.warning("Found ```json but no closing ```, attempting to parse truncated JSON")
                    json_start = content.find('```json') + 7
                    truncated_json = content[json_start:].strip()
                    
                    # Try to fix common truncation issues
                    if not truncated_json.endswith('}'):
                        # Find the last complete object/array and truncate there
                        brace_count = 0
                        last_valid_pos = 0
                        for i, char in enumerate(truncated_json):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    last_valid_pos = i + 1
                        
                        if last_valid_pos > 0:
                            truncated_json = truncated_json[:last_valid_pos]
                            logger.info(f"Attempting to parse truncated JSON ending at position {last_valid_pos}")
                            try:
                                parsed_result = json.loads(truncated_json)
                                logger.info(f"Successfully parsed truncated JSON with keys: {list(parsed_result.keys())}")
                                return parsed_result
                            except json.JSONDecodeError:
                                logger.warning("Could not parse truncated JSON, treating as text")
                    
                    return {"analysis_text": content, "parsing_method": "text_truncated"}
            else:
                logger.info("Content does not appear to be JSON, returning as text")
                # Return as text analysis
                return {"analysis_text": content, "parsing_method": "text"}
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse {agent_type} response as JSON: {str(e)}")
            logger.warning(f"Content that failed to parse: {content[:500]}...")
            return {"analysis_text": content, "parsing_method": "text"}
            
    except Exception as e:
        logger.error(f"=== ERROR CALLING BEDROCK ({agent_type}) ===")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        if hasattr(e, 'response'):
            logger.error(f"Error response: {e.response}")
        return {"error": str(e)}


def test_requirements_analyst_llm():
    """Test Requirements Analyst with real LLM call"""
    logger.info("=== Testing Requirements Analyst with Direct LLM Call ===")
    
    prompt = """You are a Requirements Analyst. Analyze this user request and provide a JSON response with the following structure:

{
    "extracted_requirements": {
        "functional_requirements": ["list of functional requirements"],
        "non_functional_requirements": {
            "security": ["security requirements"],
            "performance": ["performance requirements"],
            "scalability": ["scalability requirements"]
        }
    },
    "compliance_frameworks": ["list of applicable compliance frameworks"],
    "complexity_assessment": {
        "complexity_level": "low|medium|high",
        "complexity_score": 0-100,
        "estimated_effort": "time estimate"
    },
    "structured_specifications": {
        "user_stories": [{"id": "US-001", "story": "user story"}],
        "acceptance_criteria": ["criteria list"]
    },
    "clarification_needed": ["list of clarifications needed"],
    "validation_results": {
        "completeness_score": 0-100,
        "consistency_issues": ["list of issues"]
    }
}

User Request: "I want to build a customer service chatbot that can handle product inquiries, order status checks, and basic troubleshooting. It should be available 24/7 and handle multiple languages. The bot should escalate complex issues to human agents."

Provide only the JSON response:"""

    result = call_bedrock_directly(prompt, "requirements_analyst")
    
    if result and "error" not in result:
        # Create AgentOutput structure
        agent_output = AgentOutput(
            agent_name="requirements_analyst",
            execution_id="direct_llm_req_001",
            input_data={"user_request": "customer service chatbot request"},
            output=AgentOutput.Output(
                result=result,
                confidence_score=0.8,
                reasoning="Direct LLM analysis",
                recommendations=[]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=5.0,
                model_invocations=1,
                tokens_used=1000
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="direct_llm_req_001",
                steps=[{"step": "requirements_analysis", "status": "completed"}]
            )
        )
        
        # Save raw output for inspection
        output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "direct_llm_requirements.json"), "w") as f:
            json.dump(result, f, indent=2, default=str)
        
        return agent_output
    
    return None


def test_solution_architect_llm():
    """Test Solution Architect with real LLM call"""
    logger.info("=== Testing Solution Architect with Direct LLM Call ===")
    
    prompt = """You are a Solution Architect. Design an AWS architecture and provide a JSON response with this structure:

{
    "selected_services": [
        {"service": "Amazon Bedrock", "purpose": "AI inference", "priority": "high"},
        {"service": "AWS Lambda", "purpose": "Serverless compute", "priority": "high"}
    ],
    "architecture_blueprint": {
        "deployment_model": "serverless",
        "service_relationships": {"api_gateway": "lambda", "lambda": "bedrock"},
        "data_flow": "description of data flow"
    },
    "security_architecture": {
        "iam_design": {"roles": ["role1"], "policies": ["policy1"]},
        "encryption": {"at_rest": "kms", "in_transit": "tls"}
    },
    "iac_templates": {
        "cloudformation": {"template_version": "2010-09-09", "resources": ["resource1"]}
    },
    "cost_estimation": {
        "monthly_estimate": 150,
        "breakdown": {"bedrock": 100, "lambda": 50}
    },
    "integration_design": {
        "api_endpoints": ["/chat", "/status"],
        "authentication": "api_key"
    }
}

Requirements: Customer service chatbot with 24/7 availability, multi-language support, escalation to humans, product inquiries, order status, troubleshooting.

Provide only the JSON response:"""

    result = call_bedrock_directly(prompt, "solution_architect")
    
    if result and "error" not in result:
        # Create AgentOutput structure
        agent_output = AgentOutput(
            agent_name="solution_architect",
            execution_id="direct_llm_arch_001",
            input_data={"requirements": "chatbot requirements"},
            output=AgentOutput.Output(
                result=result,
                confidence_score=0.85,
                reasoning="Direct LLM architecture design",
                recommendations=[]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=8.0,
                model_invocations=1,
                tokens_used=1500
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="direct_llm_arch_001",
                steps=[{"step": "architecture_design", "status": "completed"}]
            )
        )
        
        # Save raw output for inspection
        output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "direct_llm_architecture.json"), "w") as f:
            json.dump(result, f, indent=2, default=str)
        
        return agent_output
    
    return None


def test_code_generator_llm():
    """Test Code Generator with real LLM call"""
    logger.info("=== Testing Code Generator with Direct LLM Call ===")
    
    prompt = """You are a Code Generator. Generate code and provide a JSON response with this structure:

{
    "bedrock_agent_config": {
        "agent_name": "CustomerServiceBot",
        "description": "Customer service chatbot",
        "foundation_model": "anthropic.claude-3-sonnet-20240229-v1:0",
        "instruction": "You are a helpful customer service agent",
        "action_groups": ["customer_actions"],
        "knowledge_bases": []
    },
    "action_groups": [
        {
            "name": "customer_actions",
            "description": "Customer service actions",
            "api_schema": {"openapi": "3.0.0", "paths": {"/inquire": {"post": {}}}},
            "lambda_function": "customer-service-handler"
        }
    ],
    "lambda_functions": [
        {
            "function_name": "customer-service-handler",
            "runtime": "python3.12",
            "handler": "index.lambda_handler",
            "code": "import json\\ndef lambda_handler(event, context):\\n    return {'statusCode': 200}",
            "environment_variables": {"LOG_LEVEL": "INFO"}
        }
    ],
    "cloudformation_templates": {
        "main_template": {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {"BedrockAgent": {"Type": "AWS::Bedrock::Agent"}}
        }
    },
    "iam_policies": [
        {
            "policy_name": "BedrockAgentPolicy",
            "policy_document": {"Version": "2012-10-17", "Statement": []}
        }
    ],
    "deployment_scripts": {
        "deploy.sh": "#!/bin/bash\\necho 'Deploying...'",
        "setup.py": "print('Setup complete')"
    }
}

Architecture: Serverless chatbot using Bedrock, Lambda, API Gateway for customer service with escalation capabilities.

IMPORTANT: Keep code examples concise. Focus on structure over detailed implementation. Provide only the JSON response:"""

    result = call_bedrock_directly(prompt, "code_generator")
    
    if result and "error" not in result:
        # Create AgentOutput structure
        agent_output = AgentOutput(
            agent_name="code_generator",
            execution_id="direct_llm_code_001",
            input_data={"architecture": "serverless chatbot architecture"},
            output=AgentOutput.Output(
                result=result,
                confidence_score=0.75,
                reasoning="Direct LLM code generation",
                recommendations=[]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=12.0,
                model_invocations=1,
                tokens_used=2000
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="direct_llm_code_001",
                steps=[{"step": "code_generation", "status": "completed"}]
            )
        )
        
        # Save raw output for inspection
        output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "direct_llm_code.json"), "w") as f:
            json.dump(result, f, indent=2, default=str)
        
        return agent_output
    
    return None


def main():
    """Main test function"""
    logger.info("Starting Direct LLM Validation Test")
    
    agent_outputs = {}
    
    # Test each agent with direct LLM calls
    req_output = test_requirements_analyst_llm()
    if req_output:
        agent_outputs["requirements_analyst"] = req_output
        logger.info("✓ Requirements Analyst LLM call successful")
    else:
        logger.error("✗ Requirements Analyst LLM call failed")
    
    arch_output = test_solution_architect_llm()
    if arch_output:
        agent_outputs["solution_architect"] = arch_output
        logger.info("✓ Solution Architect LLM call successful")
    else:
        logger.error("✗ Solution Architect LLM call failed")
    
    code_output = test_code_generator_llm()
    if code_output:
        agent_outputs["code_generator"] = code_output
        logger.info("✓ Code Generator LLM call successful")
    else:
        logger.error("✗ Code Generator LLM call failed")
    
    # Validate the real LLM outputs
    if agent_outputs:
        logger.info(f"\n=== Validating {len(agent_outputs)} Real LLM Outputs ===")
        
        # Initialize audit system
        audit_system = ComprehensiveAuditSystem()
        
        # Perform comprehensive audit
        audit_results = audit_system.audit_agent_outputs(
            agent_outputs=agent_outputs,
            session_id="direct_llm_validation",
            generate_report=True
        )
        
        # Print results
        logger.info("=== VALIDATION RESULTS ===")
        logger.info(f"Overall Status: {audit_results['audit_summary']['overall_status']}")
        logger.info(f"Agents Passed: {audit_results['audit_summary']['agents_summary']['passed']}")
        logger.info(f"Agents Failed: {audit_results['audit_summary']['agents_summary']['failed']}")
        logger.info(f"Total Errors: {audit_results['audit_summary']['issues_summary']['total_errors']}")
        logger.info(f"Total Warnings: {audit_results['audit_summary']['issues_summary']['total_warnings']}")
        logger.info(f"Average Quality Score: {audit_results['audit_summary']['scores']['average_quality_score']:.2f}")
        logger.info(f"Average Compatibility Score: {audit_results['audit_summary']['scores']['average_compatibility_score']:.2f}")
        
        # Show validation details for each agent
        for agent_name, validation_result in audit_results['validation_results'].items():
            logger.info(f"\n--- {agent_name.upper()} VALIDATION ---")
            logger.info(f"Valid: {validation_result['is_valid']}")
            logger.info(f"Quality Score: {validation_result['quality_score']:.2f}")
            logger.info(f"Errors: {len(validation_result['validation_errors'])}")
            
            if validation_result['validation_errors']:
                logger.info("Validation Errors:")
                for error in validation_result['validation_errors'][:3]:  # Show first 3
                    logger.info(f"  - {error['field_name']}: {error['error_message']}")
            
            if validation_result['warnings']:
                logger.info(f"Warnings: {len(validation_result['warnings'])}")
        
        # Show compatibility results
        logger.info("\n=== COMPATIBILITY RESULTS ===")
        for pair_name, compat_result in audit_results['compatibility_results'].items():
            logger.info(f"{pair_name}: {'✓' if compat_result['is_valid'] else '✗'} "
                       f"(Score: {compat_result['data_flow_score']:.2f})")
            
            if compat_result['semantic_issues']:
                logger.info(f"  Semantic Issues: {len(compat_result['semantic_issues'])}")
                for issue in compat_result['semantic_issues'][:2]:  # Show first 2
                    logger.info(f"    - {issue}")
        
        # Save complete results
        output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "direct_llm_audit_results.json"), "w") as f:
            json.dump(audit_results, f, indent=2, default=str)
        
        logger.info("\n=== SUMMARY ===")
        logger.info(f"Successfully tested {len(agent_outputs)} agents with real Bedrock LLM calls")
        logger.info("Raw LLM outputs saved to tests/outputs/direct_llm_*.json files")
        logger.info("Complete audit results saved to tests/outputs/direct_llm_audit_results.json")
        
        # Print key findings
        total_errors = audit_results['audit_summary']['issues_summary']['total_errors']
        if total_errors > 0:
            logger.info(f"⚠️  Found {total_errors} validation errors in real LLM outputs")
            logger.info("This demonstrates the validation system catching real issues!")
        else:
            logger.info("✅ All real LLM outputs passed validation")
    else:
        logger.error("No successful LLM calls - cannot perform validation test")
    
    logger.info("Direct LLM Validation Test Completed!")


if __name__ == "__main__":
    main()