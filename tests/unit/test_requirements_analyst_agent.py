"""
Unit tests for Requirements Analyst Agent

Tests the LangChain agent implementation for natural language processing,
requirement extraction, compliance checking, and validation capabilities.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from autoninja.agents.requirements_analyst import RequirementsAnalystAgent, create_requirements_analyst_agent
from autoninja.core.bedrock_client import BedrockClientManager, BedrockModelId, TaskComplexity
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient
from autoninja.models.state import AgentOutput


class TestRequirementsAnalystAgent:
    """Test suite for Requirements Analyst Agent"""
    
    @pytest.fixture
    def mock_bedrock_client_manager(self):
        """Mock Bedrock client manager"""
        manager = Mock(spec=BedrockClientManager)
        manager.select_model_by_complexity.return_value = BedrockModelId.CLAUDE_SONNET_4_5
        
        # Mock the ChatBedrock client
        mock_client = Mock()
        manager.get_client.return_value = mock_client
        
        return manager
    
    @pytest.fixture
    def mock_knowledge_base_client(self):
        """Mock knowledge base client"""
        return Mock(spec=BedrockKnowledgeBaseClient)
    
    @pytest.fixture
    def requirements_analyst_agent(self, mock_bedrock_client_manager, mock_knowledge_base_client):
        """Create Requirements Analyst Agent with mocked dependencies"""
        return RequirementsAnalystAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
    
    def test_agent_initialization(self, requirements_analyst_agent):
        """Test agent initialization"""
        assert requirements_analyst_agent.agent_name == "requirements_analyst"
        assert requirements_analyst_agent.tools is not None
        assert len(requirements_analyst_agent.tools) == 4  # 4 tools initialized
        assert requirements_analyst_agent.agent_executor is not None
    
    def test_get_agent_info(self, requirements_analyst_agent):
        """Test agent info retrieval"""
        info = requirements_analyst_agent.get_agent_info()
        
        assert info["agent_name"] == "requirements_analyst"
        assert info["agent_type"] == "requirements_analyst"
        assert "Natural language processing" in info["capabilities"]
        assert len(info["tools"]) == 4
        assert info["model_complexity"] == TaskComplexity.MEDIUM.value
    
    @patch('autoninja.agents.requirements_analyst.logger')
    def test_analyze_requirements_success(self, mock_logger, requirements_analyst_agent):
        """Test successful requirements analysis"""
        
        # Mock the agent executor response
        mock_response = {
            "output": json.dumps({
                "extracted_requirements": {
                    "functional_requirements": ["Process customer inquiries", "Provide automated responses"],
                    "non_functional_requirements": {
                        "performance": ["Response time under 2 seconds"],
                        "security": ["Secure data handling"]
                    }
                },
                "compliance_frameworks": ["GDPR"],
                "complexity_assessment": {
                    "complexity_score": 60,
                    "complexity_level": "medium"
                },
                "structured_specifications": {
                    "user_stories": [
                        {
                            "id": "US-001",
                            "story": "As a customer, I want automated responses to my inquiries"
                        }
                    ]
                }
            }),
            "intermediate_steps": []
        }
        
        # Mock the agent executor
        mock_executor = Mock()
        mock_executor.invoke.return_value = mock_response
        requirements_analyst_agent.agent_executor = mock_executor
        
        # Test the analysis
        user_request = "I need a customer service chatbot that can handle basic inquiries"
        session_id = "test-session-123"
        
        result = requirements_analyst_agent.analyze_requirements(user_request, session_id)
        
        # Verify the result
        assert isinstance(result, AgentOutput)
        assert result.agent_name == "requirements_analyst"
        assert result.input_data["user_request"] == user_request
        assert result.input_data["session_id"] == session_id
        
        # Check output structure
        assert "extracted_requirements" in result.output.result
        assert "compliance_frameworks" in result.output.result
        assert result.output.confidence_score > 0.0
        
        # Verify logging
        mock_logger.info.assert_called()
    
    @patch('autoninja.agents.requirements_analyst.logger')
    def test_analyze_requirements_with_additional_context(self, mock_logger, requirements_analyst_agent):
        """Test requirements analysis with additional context"""
        
        # Mock the agent executor response
        mock_response = {
            "output": "Analysis completed with additional context",
            "intermediate_steps": []
        }
        
        # Mock the agent executor
        mock_executor = Mock()
        mock_executor.invoke.return_value = mock_response
        requirements_analyst_agent.agent_executor = mock_executor
        
        # Test with additional context
        user_request = "Create an analytics agent"
        session_id = "test-session-456"
        additional_context = {
            "industry": "healthcare",
            "compliance_requirements": ["HIPAA"]
        }
        
        result = requirements_analyst_agent.analyze_requirements(
            user_request, 
            session_id, 
            additional_context
        )
        
        # Verify additional context was included
        assert result.input_data["additional_context"] == additional_context
    
    @patch('autoninja.agents.requirements_analyst.logger')
    def test_analyze_requirements_error_handling(self, mock_logger, requirements_analyst_agent):
        """Test error handling in requirements analysis"""
        
        # Mock the agent executor to raise an exception
        mock_executor = Mock()
        mock_executor.invoke.side_effect = Exception("Bedrock API error")
        requirements_analyst_agent.agent_executor = mock_executor
        
        user_request = "Create a test agent"
        session_id = "test-session-error"
        
        result = requirements_analyst_agent.analyze_requirements(user_request, session_id)
        
        # Verify error handling
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score == 0.0
        assert "error" in result.output.result
        assert "Bedrock API error" in result.output.result["error"]
        assert "Analysis failed" in result.output.reasoning
        
        # Verify error logging
        mock_logger.error.assert_called()
    
    def test_prepare_agent_input(self, requirements_analyst_agent):
        """Test agent input preparation"""
        
        user_request = "Create a chatbot"
        additional_context = {"industry": "finance"}
        
        input_text = requirements_analyst_agent._prepare_agent_input(user_request, additional_context)
        
        assert user_request in input_text
        assert "Additional Context:" in input_text
        assert "finance" in input_text
        assert "Extract functional requirements" in input_text
    
    def test_process_agent_output_json(self, requirements_analyst_agent):
        """Test processing of JSON agent output"""
        
        raw_output = {
            "output": json.dumps({
                "extracted_requirements": {"functional": ["test"]},
                "compliance_frameworks": ["GDPR"]
            }),
            "intermediate_steps": []
        }
        
        result = requirements_analyst_agent._process_agent_output(raw_output)
        
        assert "extracted_requirements" in result
        assert "compliance_frameworks" in result
        assert result["compliance_frameworks"] == ["GDPR"]
    
    def test_process_agent_output_text(self, requirements_analyst_agent):
        """Test processing of text agent output"""
        
        raw_output = {
            "output": "This is a text analysis result",
            "intermediate_steps": []
        }
        
        result = requirements_analyst_agent._process_agent_output(raw_output)
        
        assert result["analysis_summary"] == "This is a text analysis result"
        assert result["extraction_method"] == "text_analysis"
        assert "extracted_requirements" in result
    
    def test_calculate_confidence_score(self, requirements_analyst_agent):
        """Test confidence score calculation"""
        
        # Complete output
        complete_output = {
            "extracted_requirements": {"functional": ["test"]},
            "compliance_frameworks": ["GDPR"],
            "complexity_assessment": {"score": 60},
            "structured_specifications": {"stories": []},
            "validation_results": {"valid": True}
        }
        
        score = requirements_analyst_agent._calculate_confidence_score(complete_output)
        assert score == 1.0
        
        # Partial output
        partial_output = {
            "extracted_requirements": {"functional": ["test"]}
        }
        
        score = requirements_analyst_agent._calculate_confidence_score(partial_output)
        assert score == 0.3  # 30/100
    
    def test_generate_recommendations(self, requirements_analyst_agent):
        """Test recommendation generation"""
        
        # Output with missing requirements
        incomplete_output = {
            "compliance_frameworks": ["GDPR"]
        }
        
        recommendations = requirements_analyst_agent._generate_recommendations(incomplete_output)
        
        assert len(recommendations) > 0
        assert any("functional requirements" in rec for rec in recommendations)
        
        # Complete output
        complete_output = {
            "extracted_requirements": {"functional": ["test"]},
            "compliance_frameworks": ["GDPR"],
            "complexity_assessment": {"score": 60},
            "structured_specifications": {"stories": []},
            "validation_results": {"valid": True}
        }
        
        recommendations = requirements_analyst_agent._generate_recommendations(complete_output)
        assert "ready for architecture design" in recommendations[0]
    
    def test_extract_tool_outputs(self, requirements_analyst_agent):
        """Test extraction of tool outputs from intermediate steps"""
        
        # Mock action and observation
        mock_action = Mock()
        mock_action.tool = "requirement_extraction"
        mock_action.tool_input = {"user_request": "test"}
        
        raw_output = {
            "output": "test",
            "intermediate_steps": [
                (mock_action, "tool output result")
            ]
        }
        
        tool_outputs = requirements_analyst_agent._extract_tool_outputs(raw_output)
        
        assert "requirement_extraction" in tool_outputs
        assert tool_outputs["requirement_extraction"]["input"] == {"user_request": "test"}
        assert tool_outputs["requirement_extraction"]["output"] == "tool output result"


class TestRequirementsAnalystAgentFactory:
    """Test the factory function for creating Requirements Analyst Agent"""
    
    @patch('autoninja.agents.requirements_analyst.get_bedrock_client_manager')
    def test_create_requirements_analyst_agent_default(self, mock_get_manager):
        """Test creating agent with default parameters"""
        
        mock_manager = Mock(spec=BedrockClientManager)
        mock_get_manager.return_value = mock_manager
        
        agent = create_requirements_analyst_agent()
        
        assert isinstance(agent, RequirementsAnalystAgent)
        assert agent.bedrock_client_manager == mock_manager
        mock_get_manager.assert_called_once()
    
    def test_create_requirements_analyst_agent_with_params(self):
        """Test creating agent with custom parameters"""
        
        mock_manager = Mock(spec=BedrockClientManager)
        mock_kb_client = Mock(spec=BedrockKnowledgeBaseClient)
        
        agent = create_requirements_analyst_agent(
            bedrock_client_manager=mock_manager,
            knowledge_base_client=mock_kb_client
        )
        
        assert isinstance(agent, RequirementsAnalystAgent)
        assert agent.bedrock_client_manager == mock_manager
        assert agent.knowledge_base_client == mock_kb_client


class TestRequirementsAnalystAgentIntegration:
    """Integration tests for Requirements Analyst Agent"""
    
    @pytest.mark.integration
    @patch('autoninja.agents.requirements_analyst.get_bedrock_client_manager')
    def test_full_analysis_workflow(self, mock_get_manager):
        """Test the complete analysis workflow"""
        
        # Setup mocks
        mock_manager = Mock(spec=BedrockClientManager)
        mock_manager.select_model_by_complexity.return_value = BedrockModelId.CLAUDE_SONNET_4_5
        mock_client = Mock()
        mock_manager.get_client.return_value = mock_client
        mock_get_manager.return_value = mock_manager
        
        # Create agent
        agent = create_requirements_analyst_agent()
        
        # Mock successful execution
        mock_response = {
            "output": json.dumps({
                "extracted_requirements": {
                    "functional_requirements": [
                        "Handle customer service inquiries",
                        "Provide automated responses",
                        "Escalate complex issues to human agents"
                    ],
                    "non_functional_requirements": {
                        "performance": ["Response time under 2 seconds"],
                        "security": ["Secure customer data handling"],
                        "availability": ["99.9% uptime"]
                    }
                },
                "compliance_frameworks": ["GDPR", "CCPA"],
                "complexity_assessment": {
                    "complexity_score": 70,
                    "complexity_level": "medium",
                    "estimated_effort": "2-4 weeks"
                },
                "structured_specifications": {
                    "user_stories": [
                        {
                            "id": "US-001",
                            "story": "As a customer, I want quick responses to my inquiries"
                        }
                    ]
                },
                "validation_results": {
                    "completeness_score": 85.0,
                    "consistency_issues": [],
                    "missing_elements": []
                }
            }),
            "intermediate_steps": []
        }
        
        # Mock the agent executor
        mock_executor = Mock()
        mock_executor.invoke.return_value = mock_response
        agent.agent_executor = mock_executor
        
        # Execute analysis
        user_request = """
        I need a customer service chatbot for my e-commerce website. 
        It should handle basic inquiries about orders, returns, and product information.
        The bot needs to be fast, secure, and comply with data protection regulations.
        It should escalate complex issues to human agents.
        """
        
        result = agent.analyze_requirements(user_request, "integration-test-session")
        
        # Verify comprehensive analysis
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score > 0.8
        
        output_data = result.output.result
        assert len(output_data["extracted_requirements"]["functional_requirements"]) >= 3
        assert "performance" in output_data["extracted_requirements"]["non_functional_requirements"]
        assert len(output_data["compliance_frameworks"]) >= 1
        assert output_data["complexity_assessment"]["complexity_level"] == "medium"
        
        # Verify recommendations
        assert len(result.output.recommendations) > 0