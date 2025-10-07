#!/usr/bin/env python3
"""
Demo script for Solution Architect Agent using Claude 4.5 Sonnet

This script demonstrates the Solution Architect Agent's capabilities
with the upgraded Claude 4.5 model and concise response generation.
"""

import json
import logging
from datetime import datetime, UTC

from autoninja.agents.solution_architect import SolutionArchitectAgent
from autoninja.models.state import AgentOutput
from autoninja.core.bedrock_client import get_bedrock_client_manager, BedrockModelId

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_requirements_output():
    """Create a sample requirements output for testing."""
    return AgentOutput(
        agent_name="requirements_analyst",
        execution_id="demo_req_001",
        input_data={
            "user_request": "Create a document analysis AI agent that can extract key information from PDFs",
            "session_id": "demo_session"
        },
        output=AgentOutput.Output(
            result={
                "extracted_requirements": {
                    "functional_requirements": [
                        "Extract text from PDF documents",
                        "Identify key information and entities",
                        "Generate structured summaries",
                        "Support multiple document formats"
                    ],
                    "non_functional_requirements": {
                        "performance": ["Process documents under 30 seconds"],
                        "security": ["Encrypt document data", "Secure API access"],
                        "scalability": ["Handle 100 concurrent uploads"]
                    }
                },
                "compliance_frameworks": ["GDPR"],
                "complexity_assessment": {
                    "complexity_score": 65,
                    "complexity_level": "medium"
                }
            },
            confidence_score=0.85,
            reasoning="Document analysis requirements extracted successfully",
            recommendations=["Consider OCR capabilities for scanned documents"]
        ),
        execution_metadata=AgentOutput.ExecutionMetadata(
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration_seconds=25.0,
            model_invocations=1,
            tokens_used=1800
        ),
        trace_data=AgentOutput.TraceData(
            trace_id="demo_req_001",
            steps=[{"step": "requirements_analysis", "status": "completed"}]
        )
    )


def main():
    """Main demo function."""
    print("🏗️  Solution Architect Agent Demo - Claude 4.5 Sonnet")
    print("=" * 60)
    
    try:
        # Initialize the Solution Architect Agent
        print("Initializing Solution Architect Agent...")
        bedrock_manager = get_bedrock_client_manager()
        agent = SolutionArchitectAgent(bedrock_client_manager=bedrock_manager)
        
        # Verify the model being used
        agent_info = agent.get_agent_info()
        print(f"✅ Agent initialized successfully")
        print(f"📋 Agent Type: {agent_info['agent_type']}")
        print(f"🤖 Model: {agent_info['model_id']}")
        print(f"🛠️  Tools: {', '.join(agent_info['tools'])}")
        print()
        
        # Verify we're using Claude 4.5 Sonnet
        expected_model = BedrockModelId.CLAUDE_SONNET_4_5.value
        if agent_info['model_id'] == expected_model:
            print(f"✅ Confirmed using Claude 4.5 Sonnet: {expected_model}")
        else:
            print(f"⚠️  Expected {expected_model}, but using {agent_info['model_id']}")
        print()
        
        # Create sample requirements
        print("📝 Creating sample requirements output...")
        requirements_output = create_sample_requirements_output()
        print(f"✅ Requirements created with confidence: {requirements_output.output.confidence_score}")
        print()
        
        # Design architecture
        print("🏗️  Designing architecture with Claude 4.5...")
        print("⏳ This may take a moment for real Bedrock inference...")
        
        result = agent.design_architecture(
            requirements_output=requirements_output,
            session_id="demo_session_001"
        )
        
        print("✅ Architecture design completed!")
        print(f"📊 Confidence Score: {result.output.confidence_score:.2f}")
        print(f"⏱️  Processing Time: {result.execution_metadata.duration_seconds:.2f}s")
        print(f"🔄 Model Invocations: {result.execution_metadata.model_invocations}")
        print()
        
        # Display key results
        architecture_result = result.output.result
        
        print("🎯 Key Architecture Components:")
        print("-" * 40)
        
        # Selected Services
        services = architecture_result.get("selected_services", [])
        print(f"📦 Selected Services ({len(services)}):")
        for i, service in enumerate(services[:5], 1):  # Show first 5
            if isinstance(service, dict):
                print(f"  {i}. {service.get('service', 'Unknown')} - {service.get('purpose', 'N/A')}")
            else:
                print(f"  {i}. {service}")
        
        # Architecture Blueprint
        blueprint = architecture_result.get("architecture_blueprint", {})
        if blueprint:
            print(f"\n🏗️  Architecture Model: {blueprint.get('deployment_model', 'Not specified')}")
        
        # Cost Estimation
        cost_est = architecture_result.get("cost_estimation", {})
        if cost_est:
            monthly_cost = cost_est.get("monthly_estimate", cost_est.get("monthly", 0))
            print(f"💰 Estimated Monthly Cost: ${monthly_cost}")
        
        # Security Architecture
        security = architecture_result.get("security_architecture", {})
        if security:
            print(f"🔒 Security Features: {len(security)} categories configured")
        
        print()
        print("📋 Recommendations:")
        for i, rec in enumerate(result.output.recommendations[:3], 1):
            print(f"  {i}. {rec}")
        
        print()
        print("✅ Demo completed successfully!")
        print(f"🔍 Full result available in execution ID: {result.execution_id}")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        logger.exception("Demo execution failed")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())