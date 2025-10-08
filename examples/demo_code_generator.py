#!/usr/bin/env python3
"""
Demo script for Code Generator Agent

This script demonstrates the Code Generator Agent functionality by:
1. Creating a mock architecture output from Solution Architect Agent
2. Running the Code Generator Agent to generate production-ready code
3. Displaying the generated code structure and components
"""

import json
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from autoninja.agents.code_generator import create_code_generator_agent
from autoninja.models.state import AgentOutput
from autoninja.core.logging_config import setup_logging


def create_mock_architecture_output() -> AgentOutput:
    """Create a mock architecture output from Solution Architect Agent."""
    
    mock_architecture_result = {
        "selected_services": [
            {"service": "Amazon Bedrock", "purpose": "AI inference", "priority": "high"},
            {"service": "AWS Lambda", "purpose": "Serverless compute", "priority": "high"},
            {"service": "API Gateway", "purpose": "API management", "priority": "medium"},
            {"service": "DynamoDB", "purpose": "Data storage", "priority": "medium"}
        ],
        "architecture_blueprint": {
            "deployment_model": "serverless",
            "service_relationships": {
                "api_gateway": "lambda",
                "lambda": "bedrock",
                "lambda_data": "dynamodb"
            },
            "data_flow": "api -> lambda -> bedrock -> response"
        },
        "security_architecture": {
            "iam_design": {
                "roles": ["lambda_execution", "bedrock_invoke"],
                "policies": ["bedrock_invoke_policy", "dynamodb_access_policy"]
            },
            "encryption": {
                "at_rest": "kms",
                "in_transit": "tls"
            }
        },
        "iac_templates": {
            "cloudformation_template": {
                "Resources": {
                    "LambdaFunction": {"Type": "AWS::Lambda::Function"},
                    "ApiGateway": {"Type": "AWS::ApiGateway::RestApi"},
                    "DynamoDBTable": {"Type": "AWS::DynamoDB::Table"}
                }
            }
        },
        "cost_estimation": {
            "monthly_estimate": 150,
            "breakdown": {
                "bedrock": 100,
                "lambda": 30,
                "api_gateway": 20
            }
        },
        "integration_design": {
            "api_endpoints": ["/chat", "/analyze"],
            "authentication": "api_key"
        }
    }
    
    return AgentOutput(
        agent_name="solution_architect",
        execution_id="demo_arch_001",
        input_data={"mock": "architecture input"},
        output=AgentOutput.Output(
            result=mock_architecture_result,
            confidence_score=0.95,
            reasoning="Mock architecture design for demo purposes",
            recommendations=["Architecture ready for code generation"]
        ),
        execution_metadata=AgentOutput.ExecutionMetadata(
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration_seconds=5.0,
            model_invocations=1,
            tokens_used=1500
        ),
        trace_data=AgentOutput.TraceData(
            trace_id="demo_arch_001",
            steps=[{"step": "architecture_design", "status": "completed"}]
        )
    )


def main():
    """Main demo function."""
    print("🚀 AutoNinja Code Generator Agent Demo")
    print("=" * 50)
    
    # Setup logging
    setup_logging(log_level="INFO")
    
    try:
        # Create the Code Generator Agent
        print("\n1. Creating Code Generator Agent...")
        code_generator = create_code_generator_agent()
        
        # Display agent info
        agent_info = code_generator.get_agent_info()
        print(f"   Agent: {agent_info['agent_name']}")
        print(f"   Type: {agent_info['agent_type']}")
        print(f"   Description: {agent_info['description']}")
        print(f"   Tools: {', '.join(agent_info['tools'])}")
        
        # Create mock architecture output
        print("\n2. Creating mock architecture output...")
        architecture_output = create_mock_architecture_output()
        print(f"   Architecture confidence: {architecture_output.output.confidence_score}")
        print(f"   Selected services: {len(architecture_output.output.result['selected_services'])}")
        
        # Generate code
        print("\n3. Generating production-ready code...")
        session_id = "demo_code_gen_001"
        
        code_output = code_generator.generate_code(
            architecture_output=architecture_output,
            session_id=session_id,
            additional_context={
                "demo_mode": True,
                "target_environment": "development"
            }
        )
        
        # Display results
        print(f"\n4. Code Generation Results:")
        print(f"   Execution ID: {code_output.execution_id}")
        print(f"   Confidence Score: {code_output.output.confidence_score:.2f}")
        print(f"   Processing Time: {code_output.execution_metadata.duration_seconds:.2f}s")
        print(f"   Recommendations: {len(code_output.output.recommendations)}")
        
        # Display generated components
        result = code_output.output.result
        print(f"\n5. Generated Components:")
        
        if result.get("bedrock_agent_config"):
            agent_config = result["bedrock_agent_config"]
            print(f"   ✅ Bedrock Agent Config: {agent_config.get('agent_name', 'Generated')}")
        
        if result.get("action_groups"):
            print(f"   ✅ Action Groups: {len(result['action_groups'])} groups")
        
        if result.get("lambda_functions"):
            print(f"   ✅ Lambda Functions: {len(result['lambda_functions'])} functions")
        
        if result.get("cloudformation_templates"):
            print(f"   ✅ CloudFormation Templates: {len(result['cloudformation_templates'])} templates")
        
        if result.get("iam_policies"):
            print(f"   ✅ IAM Policies: {len(result['iam_policies'])} policies")
        
        if result.get("deployment_scripts"):
            print(f"   ✅ Deployment Scripts: {len(result['deployment_scripts'])} scripts")
        
        # Display recommendations
        print(f"\n6. Recommendations:")
        for i, rec in enumerate(code_output.output.recommendations, 1):
            print(f"   {i}. {rec}")
        
        # Display tool outputs if available
        tool_outputs = result.get("tool_outputs", {})
        if tool_outputs:
            print(f"\n7. Tool Outputs:")
            for tool_name, output in tool_outputs.items():
                print(f"   - {tool_name}: Available")
        
        print(f"\n✅ Code Generator Agent demo completed successfully!")
        print(f"📁 Check logs/code_generator.log for detailed execution logs")
        
        # Save detailed output to file for inspection
        output_file = Path("demo_code_generator_output.json")
        with open(output_file, 'w') as f:
            json.dump(code_output.model_dump(), f, indent=2, default=str)
        print(f"📄 Detailed output saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)