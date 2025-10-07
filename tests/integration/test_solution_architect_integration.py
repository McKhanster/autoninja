"""
Integration tests for Solution Architect Agent

Tests the Solution Architect Agent's integration with AWS Bedrock services,
knowledge bases, and the overall pipeline flow.
"""

import pytest
import json
import os
from datetime import datetime, UTC

from autoninja.agents.solution_architect import SolutionArchitectAgent, create_solution_architect_agent
from autoninja.agents.requirements_analyst import RequirementsAnalystAgent
from autoninja.models.state import AgentOutput
from autoninja.core.bedrock_client import get_bedrock_client_manager
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient, KnowledgeBaseType


@pytest.mark.integration
class TestSolutionArchitectIntegration:
    """Integration tests for Solution Architect Agent"""
    
    @pytest.fixture(scope="class")
    def bedrock_client_manager(self):
        """Real Bedrock client manager for integration tests"""
        # Skip if no AWS credentials configured
        if not os.getenv("AWS_REGION") and not os.path.exists(os.path.expanduser("~/.aws/credentials")):
            pytest.skip("AWS credentials not configured")
        
        return get_bedrock_client_manager()
    
    @pytest.fixture(scope="class")
    def knowledge_base_client(self):
        """Knowledge base client for integration tests"""
        # This would be configured with real knowledge base IDs in production
        return None  # BedrockKnowledgeBaseClient()
    
    @pytest.fixture
    def sample_requirements_output(self):
        """Sample requirements output for testing"""
        return AgentOutput(
            agent_name="requirements_analyst",
            execution_id="integration_test_req",
            input_data={
                "user_request": "Create a customer support chatbot that can handle billing inquiries and technical support",
                "session_id": "integration_session"
            },
            output=AgentOutput.Output(
                result={
                    "extracted_requirements": {
                        "functional_requirements": [
                            "Handle customer billing inquiries",
                            "Provide technical support guidance",
                            "Escalate complex issues to human agents",
                            "Maintain conversation context",
                            "Support multiple languages"
                        ],
                        "non_functional_requirements": {
                            "performance": [
                                "Response time under 2 seconds",
                                "Handle 1000 concurrent conversations",
                                "99.9% uptime availability"
                            ],
                            "security": [
                                "Encrypt customer data",
                                "Implement access controls",
                                "Audit all interactions"
                            ],
                            "scalability": [
                                "Auto-scale based on demand",
                                "Support peak loads during business hours"
                            ]
                        }
                    },
                    "compliance_frameworks": ["GDPR", "SOC2", "PCI-DSS"],
                    "complexity_assessment": {
                        "complexity_score": 75,
                        "complexity_level": "medium",
                        "estimated_effort": "4-6 weeks"
                    },
                    "structured_specifications": {
                        "user_stories": [
                            {
                                "id": "US-001",
                                "story": "As a customer, I want to get quick answers to billing questions"
                            },
                            {
                                "id": "US-002", 
                                "story": "As a customer, I want technical support for product issues"
                            }
                        ],
                        "acceptance_criteria": [
                            "Chatbot responds within 2 seconds",
                            "Handles billing and technical queries",
                            "Escalates when needed"
                        ]
                    },
                    "clarification_needed": [],
                    "validation_results": {
                        "completeness_score": 85,
                        "consistency_issues": []
                    }
                },
                confidence_score=0.85,
                reasoning="Comprehensive requirements analysis completed with good coverage of functional and non-functional requirements",
                recommendations=[
                    "Consider adding authentication requirements",
                    "Define specific SLA metrics",
                    "Specify data retention policies"
                ]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=45.0,
                model_invocations=1,
                tokens_used=2500
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="integration_test_req",
                steps=[{
                    "step": "requirements_analysis",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration": 45.0,
                    "status": "completed"
                }]
            )
        )
    
    def test_agent_initialization_with_real_clients(self, bedrock_client_manager, knowledge_base_client):
        """Test agent initialization with real AWS clients"""
        agent = SolutionArchitectAgent(
            bedrock_client_manager=bedrock_client_manager,
            knowledge_base_client=knowledge_base_client
        )
        
        assert agent.agent_name == "solution_architect"
        assert agent.bedrock_client_manager is not None
        assert len(agent.tools) == 3
        assert agent.agent_executor is not None
        
        # Test agent info
        info = agent.get_agent_info()
        assert info["agent_type"] == "solution_architect"
        assert "AWS service selection" in info["capabilities"]
    
    def test_architecture_design_with_bedrock(self, bedrock_client_manager, sample_requirements_output):
        """Test architecture design with real Bedrock inference"""
        agent = SolutionArchitectAgent(bedrock_client_manager=bedrock_client_manager)
        
        # Execute architecture design
        result = agent.design_architecture(
            requirements_output=sample_requirements_output,
            session_id="integration_test_session"
        )
        
        # Verify result structure
        assert isinstance(result, AgentOutput)
        assert result.agent_name == "solution_architect"
        assert result.execution_id.startswith("integration_test_session_solution_architect")
        
        # Verify output structure
        output_result = result.output.result
        assert "selected_services" in output_result
        assert "architecture_blueprint" in output_result
        assert "security_architecture" in output_result
        assert "iac_templates" in output_result
        
        # Verify confidence score
        assert 0.0 <= result.output.confidence_score <= 1.0
        
        # Verify execution metadata
        assert result.execution_metadata.duration_seconds > 0
        assert result.execution_metadata.model_invocations >= 1
        
        # Verify trace data
        assert result.trace_data.trace_id == result.execution_id
        assert len(result.trace_data.steps) > 0
        
        # Log the result for manual inspection
        print(f"\nArchitecture Design Result:")
        print(f"Confidence Score: {result.output.confidence_score}")
        print(f"Selected Services: {len(output_result.get('selected_services', []))}")
        print(f"Recommendations: {len(result.output.recommendations)}")
        print(f"Processing Time: {result.execution_metadata.duration_seconds:.2f}s")
    
    def test_pipeline_compatibility(self, bedrock_client_manager, sample_requirements_output):
        """Test that the output is compatible with the next agent in the pipeline"""
        agent = SolutionArchitectAgent(bedrock_client_manager=bedrock_client_manager)
        
        # Execute architecture design
        result = agent.design_architecture(
            requirements_output=sample_requirements_output,
            session_id="pipeline_test_session"
        )
        
        # Verify required fields for Code Generator compatibility
        output_result = result.output.result
        
        required_fields = [
            "selected_services",
            "architecture_blueprint",
            "security_architecture", 
            "iac_templates"
        ]
        
        for field in required_fields:
            assert field in output_result, f"Missing required field: {field}"
        
        # Verify architecture blueprint has essential components
        blueprint = output_result["architecture_blueprint"]
        assert isinstance(blueprint, dict)
        
        # Verify selected services include essential AWS services
        services = output_result["selected_services"]
        assert isinstance(services, list)
        
        # Check for essential services (should include Bedrock and Lambda for AI agents)
        service_names = []
        for service in services:
            if isinstance(service, dict):
                service_names.append(service.get("service", ""))
            else:
                service_names.append(str(service))
        
        # At minimum, should have some AWS services selected
        assert len(service_names) > 0, "No services selected"
        
        print(f"\nPipeline Compatibility Check:")
        print(f"Selected Services: {service_names}")
        print(f"Architecture Blueprint Keys: {list(blueprint.keys())}")
        print(f"Security Architecture Keys: {list(output_result['security_architecture'].keys())}")
    
    def test_error_handling_with_invalid_input(self, bedrock_client_manager):
        """Test error handling with invalid requirements input"""
        agent = SolutionArchitectAgent(bedrock_client_manager=bedrock_client_manager)
        
        # Create invalid requirements output
        invalid_requirements = AgentOutput(
            agent_name="requirements_analyst",
            execution_id="invalid_test",
            input_data={"user_request": ""},
            output=AgentOutput.Output(
                result={"error": "Invalid requirements"},
                confidence_score=0.0,
                reasoning="Failed to extract requirements",
                recommendations=[]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=1.0,
                model_invocations=0,
                tokens_used=0
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="invalid_test",
                steps=[]
            )
        )
        
        # Execute architecture design with invalid input
        result = agent.design_architecture(
            requirements_output=invalid_requirements,
            session_id="error_test_session"
        )
        
        # Should still return a valid AgentOutput structure
        assert isinstance(result, AgentOutput)
        assert result.agent_name == "solution_architect"
        
        # May have low confidence but should not crash
        assert 0.0 <= result.output.confidence_score <= 1.0
    
    def test_factory_function_integration(self):
        """Test the factory function with real dependencies"""
        agent = create_solution_architect_agent()
        
        assert isinstance(agent, SolutionArchitectAgent)
        assert agent.bedrock_client_manager is not None
        assert len(agent.tools) == 3
    
    def test_end_to_end_requirements_to_architecture(self, bedrock_client_manager):
        """Test end-to-end flow from requirements analysis to architecture design"""
        # First, create and run requirements analyst
        req_agent = RequirementsAnalystAgent(bedrock_client_manager=bedrock_client_manager)
        
        user_request = "Create a document analysis AI agent that can extract key information from PDFs and generate summaries"
        
        # Get requirements analysis
        req_result = req_agent.analyze_requirements(
            user_request=user_request,
            session_id="e2e_test_session"
        )
        
        assert isinstance(req_result, AgentOutput)
        assert req_result.output.confidence_score > 0
        
        # Now use those requirements for architecture design
        arch_agent = SolutionArchitectAgent(bedrock_client_manager=bedrock_client_manager)
        
        arch_result = arch_agent.design_architecture(
            requirements_output=req_result,
            session_id="e2e_test_session"
        )
        
        assert isinstance(arch_result, AgentOutput)
        assert arch_result.output.confidence_score > 0
        
        # Verify the architecture includes appropriate services for document analysis
        output_result = arch_result.output.result
        services = output_result.get("selected_services", [])
        
        # Should have selected relevant AWS services
        assert len(services) > 0
        
        print(f"\nEnd-to-End Test Results:")
        print(f"Requirements Confidence: {req_result.output.confidence_score:.2f}")
        print(f"Architecture Confidence: {arch_result.output.confidence_score:.2f}")
        print(f"Total Processing Time: {req_result.execution_metadata.duration_seconds + arch_result.execution_metadata.duration_seconds:.2f}s")
        print(f"Services Selected: {len(services)}")
    
    @pytest.mark.slow
    def test_complex_architecture_design(self, bedrock_client_manager):
        """Test architecture design for a complex multi-service application"""
        # Create complex requirements
        complex_requirements = AgentOutput(
            agent_name="requirements_analyst",
            execution_id="complex_test_req",
            input_data={
                "user_request": "Create an enterprise AI platform with multiple agents, real-time analytics, document processing, and multi-tenant support"
            },
            output=AgentOutput.Output(
                result={
                    "extracted_requirements": {
                        "functional_requirements": [
                            "Multi-tenant architecture support",
                            "Real-time data processing and analytics",
                            "Document processing with OCR capabilities",
                            "Multiple AI agent orchestration",
                            "API management and rate limiting",
                            "User authentication and authorization",
                            "Audit logging and compliance reporting"
                        ],
                        "non_functional_requirements": {
                            "performance": [
                                "Handle 10,000 concurrent users",
                                "Process 1M documents per day",
                                "Sub-second response times"
                            ],
                            "security": [
                                "End-to-end encryption",
                                "Multi-factor authentication",
                                "Role-based access control",
                                "Data isolation between tenants"
                            ],
                            "scalability": [
                                "Auto-scaling based on demand",
                                "Global deployment capability",
                                "Elastic storage scaling"
                            ]
                        }
                    },
                    "compliance_frameworks": ["SOC2", "HIPAA", "GDPR", "FedRAMP"],
                    "complexity_assessment": {
                        "complexity_score": 95,
                        "complexity_level": "high",
                        "estimated_effort": "12-16 weeks"
                    }
                },
                confidence_score=0.9,
                reasoning="Complex enterprise requirements with high compliance needs",
                recommendations=["Consider phased implementation approach"]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=60.0,
                model_invocations=1,
                tokens_used=3500
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="complex_test_req",
                steps=[]
            )
        )
        
        agent = SolutionArchitectAgent(bedrock_client_manager=bedrock_client_manager)
        
        # Execute complex architecture design
        result = agent.design_architecture(
            requirements_output=complex_requirements,
            session_id="complex_test_session"
        )
        
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score > 0
        
        # Verify complex architecture includes multiple services
        output_result = result.output.result
        services = output_result.get("selected_services", [])
        
        # Should have selected many services for complex requirements
        assert len(services) >= 5, f"Expected at least 5 services for complex architecture, got {len(services)}"
        
        # Should have cost estimation for complex architecture
        cost_est = output_result.get("cost_estimation", {})
        assert "monthly_estimate" in cost_est or "cost_breakdown" in cost_est
        
        print(f"\nComplex Architecture Test Results:")
        print(f"Confidence Score: {result.output.confidence_score:.2f}")
        print(f"Services Selected: {len(services)}")
        print(f"Processing Time: {result.execution_metadata.duration_seconds:.2f}s")
        print(f"Architecture Complexity: {output_result.get('deployment_complexity', {}).get('complexity_level', 'unknown')}")