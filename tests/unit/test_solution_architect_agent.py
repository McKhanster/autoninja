"""
Unit tests for Solution Architect Agent

Tests the Solution Architect Agent's architecture design capabilities,
AWS service selection, security planning, and IaC generation.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from autoninja.agents.solution_architect import SolutionArchitectAgent, create_solution_architect_agent
from autoninja.models.state import AgentOutput, RequirementsAnalystOutput
from autoninja.core.bedrock_client import BedrockClientManager, BedrockModelId, TaskComplexity
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient


class TestSolutionArchitectAgent:
    """Test cases for Solution Architect Agent"""
    
    @pytest.fixture
    def mock_bedrock_client_manager(self):
        """Mock Bedrock client manager"""
        manager = Mock(spec=BedrockClientManager)
        manager.select_model_by_complexity.return_value = BedrockModelId.CLAUDE_SONNET_4_5
        
        # Mock the client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = json.dumps({
            "selected_services": [
                {
                    "service": "Amazon Bedrock",
                    "purpose": "AI model access",
                    "configuration": {"models": ["claude-3-sonnet"]},
                    "priority": "high"
                }
            ],
            "architecture_blueprint": {
                "deployment_model": "serverless",
                "service_relationships": {"bedrock": "lambda"},
                "data_flow": {"input": "api_gateway", "output": "bedrock"}
            },
            "security_architecture": {
                "iam_design": {"roles": ["lambda_execution_role"]},
                "encryption_strategy": {"at_rest": "kms", "in_transit": "tls"}
            },
            "iac_templates": {
                "cloudformation_template": {"Resources": {}}
            },
            "cost_estimation": {
                "monthly_estimate": 150,
                "service_breakdown": {"bedrock": 100, "lambda": 50}
            },
            "integration_design": {
                "api_design": {"rest_api": True},
                "service_communication": {"async": False}
            }
        })
        
        mock_client.invoke.return_value = mock_response
        manager.get_client.return_value = mock_client
        manager.invoke_with_retry.return_value = mock_response
        
        return manager
    
    @pytest.fixture
    def mock_knowledge_base_client(self):
        """Mock knowledge base client"""
        client = Mock(spec=BedrockKnowledgeBaseClient)
        
        # Mock search results
        mock_result = Mock()
        mock_result.title = "Serverless AI Agent Pattern"
        mock_result.excerpt = "Architecture pattern for serverless AI agents"
        mock_result.content = "Detailed architecture pattern content"
        mock_result.relevance_score = 0.95
        
        client.search_knowledge_base.return_value = [mock_result]
        return client
    
    @pytest.fixture
    def sample_requirements_output(self):
        """Sample requirements output from Requirements Analyst Agent"""
        return AgentOutput(
            agent_name="requirements_analyst",
            execution_id="test_req_123",
            input_data={"user_request": "Create a customer support chatbot"},
            output=AgentOutput.Output(
                result={
                    "extracted_requirements": {
                        "functional_requirements": [
                            "Handle customer inquiries",
                            "Provide automated responses",
                            "Escalate complex issues"
                        ],
                        "non_functional_requirements": {
                            "performance": ["Response time < 2 seconds"],
                            "security": ["Data encryption", "Access control"],
                            "scalability": ["Handle 1000 concurrent users"]
                        }
                    },
                    "compliance_frameworks": ["GDPR", "SOC2"],
                    "complexity_assessment": {
                        "complexity_score": 75,
                        "complexity_level": "medium"
                    }
                },
                confidence_score=0.9,
                reasoning="Requirements extracted successfully",
                recommendations=["Consider adding authentication"]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=30.0,
                model_invocations=1,
                tokens_used=1500
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="test_req_123",
                steps=[{"step": "requirements_analysis", "status": "completed"}]
            )
        )
    
    def test_agent_initialization(self, mock_bedrock_client_manager, mock_knowledge_base_client):
        """Test agent initialization"""
        agent = SolutionArchitectAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
        
        assert agent.agent_name == "solution_architect"
        assert agent.bedrock_client_manager == mock_bedrock_client_manager
        assert agent.knowledge_base_client == mock_knowledge_base_client
        assert len(agent.tools) == 3  # ServiceSelection, CloudFormation, CostEstimation
        assert agent.agent_executor is not None
    
    def test_factory_function(self):
        """Test the factory function"""
        with patch('autoninja.agents.solution_architect.get_bedrock_client_manager') as mock_get_manager:
            mock_manager = Mock(spec=BedrockClientManager)
            mock_get_manager.return_value = mock_manager
            
            agent = create_solution_architect_agent()
            
            assert isinstance(agent, SolutionArchitectAgent)
            assert agent.bedrock_client_manager == mock_manager
    
    @patch('autoninja.agents.solution_architect.get_pipeline_logger')
    @patch('autoninja.agents.solution_architect.log_bedrock_request')
    @patch('autoninja.agents.solution_architect.log_bedrock_response')
    def test_design_architecture_success(
        self, 
        mock_log_response,
        mock_log_request,
        mock_get_pipeline_logger,
        mock_bedrock_client_manager,
        mock_knowledge_base_client,
        sample_requirements_output
    ):
        """Test successful architecture design"""
        # Setup mocks
        mock_pipeline_logger = Mock()
        mock_get_pipeline_logger.return_value = mock_pipeline_logger
        
        agent = SolutionArchitectAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
        
        # Execute architecture design
        result = agent.design_architecture(
            requirements_output=sample_requirements_output,
            session_id="test_session_123"
        )
        
        # Verify result structure
        assert isinstance(result, AgentOutput)
        assert result.agent_name == "solution_architect"
        assert result.output.confidence_score > 0
        assert "selected_services" in result.output.result
        assert "architecture_blueprint" in result.output.result
        assert "security_architecture" in result.output.result
        assert "iac_templates" in result.output.result
        
        # Verify logging calls
        mock_pipeline_logger.log_agent_input.assert_called_once()
        mock_pipeline_logger.log_agent_output.assert_called_once()
        mock_log_request.assert_called_once()
        mock_log_response.assert_called_once()
    
    @patch('autoninja.agents.solution_architect.get_pipeline_logger')
    def test_design_architecture_error_handling(
        self,
        mock_get_pipeline_logger,
        mock_bedrock_client_manager,
        sample_requirements_output
    ):
        """Test error handling in architecture design"""
        # Setup mocks to raise exception
        mock_pipeline_logger = Mock()
        mock_get_pipeline_logger.return_value = mock_pipeline_logger
        
        mock_bedrock_client_manager.invoke_with_retry.side_effect = Exception("Bedrock error")
        
        agent = SolutionArchitectAgent(
            bedrock_client_manager=mock_bedrock_client_manager
        )
        
        # Execute architecture design
        result = agent.design_architecture(
            requirements_output=sample_requirements_output,
            session_id="test_session_123"
        )
        
        # Verify error handling
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score == 0.0
        assert "error" in result.output.result
        assert "Bedrock error" in result.output.reasoning
        
        # Verify error logging
        mock_pipeline_logger.log_pipeline_error.assert_called_once()
    
    def test_prepare_agent_input(self, mock_bedrock_client_manager, sample_requirements_output):
        """Test agent input preparation"""
        agent = SolutionArchitectAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        additional_context = {"budget": "minimal", "timeline": "2 weeks"}
        
        agent_input = agent._prepare_agent_input(sample_requirements_output, additional_context)
        
        assert isinstance(agent_input, str)
        assert "Design an AWS architecture" in agent_input
        assert "Requirements:" in agent_input
        assert "Select essential AWS services" in agent_input
        assert "Design serverless architecture" in agent_input
        assert "Plan security" in agent_input
        assert "Generate CloudFormation" in agent_input
        assert "Estimate costs" in agent_input
        assert json.dumps(additional_context, indent=2) in agent_input
    
    def test_process_agent_output_json(self, mock_bedrock_client_manager):
        """Test processing of JSON agent output"""
        agent = SolutionArchitectAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        raw_output = {
            "output": json.dumps({
                "selected_services": ["Bedrock", "Lambda"],
                "architecture_blueprint": {"deployment": "serverless"},
                "security_architecture": {"encryption": "kms"}
            }),
            "intermediate_steps": []
        }
        
        result = agent._process_agent_output(raw_output)
        
        assert "selected_services" in result
        assert "architecture_blueprint" in result
        assert "security_architecture" in result
        assert "iac_templates" in result
        assert "cost_estimation" in result
        assert result["selected_services"] == ["Bedrock", "Lambda"]
    
    def test_process_agent_output_text(self, mock_bedrock_client_manager):
        """Test processing of text agent output"""
        agent = SolutionArchitectAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        raw_output = {
            "output": "Architecture design completed with serverless approach",
            "intermediate_steps": []
        }
        
        result = agent._process_agent_output(raw_output)
        
        assert "selected_services" in result
        assert "architecture_blueprint" in result
        assert result["architecture_summary"] == "Architecture design completed with serverless approach"
        assert result["design_method"] == "text_analysis"
    
    def test_calculate_confidence_score(self, mock_bedrock_client_manager):
        """Test confidence score calculation"""
        agent = SolutionArchitectAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        # Complete output
        complete_output = {
            "selected_services": ["service1"],
            "architecture_blueprint": {"key": "value"},
            "security_architecture": {"key": "value"},
            "iac_templates": {"key": "value"},
            "cost_estimation": {"key": "value"},
            "integration_design": {"key": "value"}
        }
        
        score = agent._calculate_confidence_score(complete_output)
        assert score == 1.0
        
        # Partial output
        partial_output = {
            "selected_services": ["service1"],
            "architecture_blueprint": {"key": "value"}
        }
        
        score = agent._calculate_confidence_score(partial_output)
        assert 0.4 <= score <= 0.5  # 20% + 25% = 45%
    
    def test_verify_response_compatibility(self, mock_bedrock_client_manager):
        """Test response compatibility verification"""
        agent = SolutionArchitectAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        # Test with missing fields
        incomplete_output = {
            "selected_services": ["Bedrock"]
        }
        
        agent._verify_response_compatibility(incomplete_output)
        
        # Verify that missing fields were added
        assert "architecture_blueprint" in incomplete_output
        assert "security_architecture" in incomplete_output
        assert "iac_templates" in incomplete_output
        assert incomplete_output["architecture_blueprint"]["deployment_model"] == "serverless"
    
    def test_generate_recommendations(self, mock_bedrock_client_manager):
        """Test recommendation generation"""
        agent = SolutionArchitectAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        # Test with incomplete output
        incomplete_output = {
            "selected_services": [],
            "cost_estimation": {"monthly_estimate": 600}
        }
        
        recommendations = agent._generate_recommendations(incomplete_output)
        
        assert len(recommendations) >= 2
        assert any("AWS services" in rec for rec in recommendations)
        assert any("cost optimization" in rec for rec in recommendations)
        
        # Test with complete output
        complete_output = {
            "selected_services": ["Bedrock", "Lambda"],
            "security_architecture": {"encryption": "kms"},
            "cost_estimation": {"monthly_estimate": 100},
            "deployment_complexity": {"complexity_level": "low"}
        }
        
        recommendations = agent._generate_recommendations(complete_output)
        assert "ready for code generation" in recommendations[0]
    
    def test_get_agent_info(self, mock_bedrock_client_manager):
        """Test agent information retrieval"""
        agent = SolutionArchitectAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        info = agent.get_agent_info()
        
        assert info["agent_name"] == "solution_architect"
        assert info["agent_type"] == "solution_architect"
        assert "AWS service selection and optimization" in info["capabilities"]
        assert "Architecture design and blueprints" in info["capabilities"]
        assert len(info["tools"]) == 3
        assert info["model_id"] == BedrockModelId.CLAUDE_SONNET_4_5.value
    
    @patch('autoninja.agents.solution_architect.get_pipeline_logger')
    @patch('autoninja.agents.solution_architect.log_bedrock_request')
    @patch('autoninja.agents.solution_architect.log_bedrock_response')
    def test_make_bedrock_inference(
        self,
        mock_log_response,
        mock_log_request,
        mock_get_pipeline_logger,
        mock_bedrock_client_manager,
        mock_knowledge_base_client
    ):
        """Test direct Bedrock inference call with logging verification"""
        mock_pipeline_logger = Mock()
        mock_get_pipeline_logger.return_value = mock_pipeline_logger
        
        agent = SolutionArchitectAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
        
        agent_input = "Design architecture for AI agent"
        execution_id = "test_exec_123"
        
        result = agent._make_bedrock_inference(agent_input, execution_id, mock_pipeline_logger)
        
        assert "output" in result
        assert "raw_bedrock_response" in result
        
        # Verify logging calls
        mock_pipeline_logger.log_inference_request.assert_called_once()
        mock_pipeline_logger.log_inference_response.assert_called_once()
        
        # Verify raw request/response logging
        mock_log_request.assert_called_once()
        mock_log_response.assert_called_once()
        
        # Verify the logged request structure
        request_call_args = mock_log_request.call_args
        assert request_call_args[0][0] == execution_id  # execution_id
        request_data = request_call_args[0][1]  # request data
        assert "model_id" in request_data
        assert "messages" in request_data
        assert "execution_id" in request_data
        assert "timestamp" in request_data
        
        # Verify the logged response structure
        response_call_args = mock_log_response.call_args
        assert response_call_args[0][0] == execution_id  # execution_id
        response_data = response_call_args[0][1]  # response data
        assert "model_id" in response_data
        assert "response_content" in response_data
        assert "execution_id" in response_data
        assert "timestamp" in response_data
    
    def test_enhance_with_tools(self, mock_bedrock_client_manager, mock_knowledge_base_client):
        """Test tool enhancement of LLM output"""
        agent = SolutionArchitectAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
        
        # Mock tool responses
        for tool in agent.tools:
            if hasattr(tool, '_run'):
                tool._run = Mock(return_value=json.dumps({
                    "recommended_services": ["Bedrock", "Lambda"],
                    "cost_estimate": {"monthly_total": 100}
                }))
        
        llm_output = json.dumps({
            "selected_services": ["Bedrock"],
            "architecture_blueprint": {"deployment": "serverless"}
        })
        
        enhanced_output = agent._enhance_with_tools(llm_output, "test input")
        
        assert isinstance(enhanced_output, str)
        enhanced_data = json.loads(enhanced_output)
        assert "selected_services" in enhanced_data
        assert "architecture_blueprint" in enhanced_data


class TestSolutionArchitectAgentIntegration:
    """Integration tests for Solution Architect Agent"""
    
    @pytest.fixture
    def real_bedrock_manager(self):
        """Real Bedrock client manager for integration tests"""
        return BedrockClientManager()
    
    @pytest.mark.integration
    def test_full_architecture_design_flow(self, real_bedrock_manager):
        """Test full architecture design flow with real Bedrock client"""
        # Skip if no AWS credentials
        pytest.importorskip("boto3")
        
        agent = SolutionArchitectAgent(bedrock_client_manager=real_bedrock_manager)
        
        # Create sample requirements output
        requirements_output = AgentOutput(
            agent_name="requirements_analyst",
            execution_id="integration_test",
            input_data={"user_request": "Create a simple chatbot"},
            output=AgentOutput.Output(
                result={
                    "extracted_requirements": {
                        "functional_requirements": ["Handle basic conversations"],
                        "non_functional_requirements": {"performance": ["Fast response"]}
                    },
                    "complexity_assessment": {"complexity_level": "low"}
                },
                confidence_score=0.8,
                reasoning="Simple requirements",
                recommendations=[]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=10.0,
                model_invocations=1,
                tokens_used=500
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="integration_test",
                steps=[]
            )
        )
        
        # This would make a real call to Bedrock
        # Uncomment for actual integration testing
        # result = agent.design_architecture(requirements_output, "integration_session")
        # assert isinstance(result, AgentOutput)
        # assert result.output.confidence_score > 0