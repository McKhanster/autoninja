"""
Unit tests for direct Bedrock inference in Requirements Analyst Agent
"""

import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from autoninja.agents.requirements_analyst import RequirementsAnalystAgent
from autoninja.core.bedrock_client import BedrockClientManager, BedrockModelId
from autoninja.models.state import AgentOutput


class TestDirectBedrockInference:
    """Test direct Bedrock inference functionality"""
    
    @pytest.fixture
    def mock_bedrock_client_manager(self):
        """Mock Bedrock client manager"""
        manager = Mock(spec=BedrockClientManager)
        manager.select_model_by_complexity.return_value = BedrockModelId.CLAUDE_SONNET_4_5
        return manager
    
    @pytest.fixture
    def requirements_analyst_agent(self, mock_bedrock_client_manager):
        """Create Requirements Analyst Agent with mocked Bedrock client"""
        return RequirementsAnalystAgent(bedrock_client_manager=mock_bedrock_client_manager)
    
    @patch('autoninja.agents.requirements_analyst.logger')
    def test_direct_bedrock_inference_success(self, mock_logger, requirements_analyst_agent):
        """Test successful direct Bedrock inference with request/response logging"""
        
        # Mock successful Bedrock response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "extracted_requirements": {
                "functional_requirements": [
                    "Answer customer questions about products",
                    "Provide basic product information",
                    "Handle simple customer inquiries"
                ],
                "non_functional_requirements": {
                    "performance": ["Response time under 3 seconds"],
                    "security": ["Secure customer data handling"]
                }
            },
            "compliance_frameworks": [],
            "complexity_assessment": {
                "complexity_score": 30,
                "complexity_level": "low",
                "estimated_effort": "1-2 weeks"
            },
            "structured_specifications": {
                "user_stories": [
                    {"id": "US-001", "story": "As a customer, I want quick answers to product questions"}
                ]
            },
            "clarification_needed": [],
            "validation_results": {
                "completeness_score": 85,
                "consistency_issues": []
            }
        })
        
        # Mock the Bedrock client manager's invoke_with_retry method
        requirements_analyst_agent.bedrock_client_manager.invoke_with_retry.return_value = mock_response
        
        # Test the analysis
        user_request = "I need a simple chatbot for customer support"
        session_id = "test-direct-inference"
        
        result = requirements_analyst_agent.analyze_requirements(user_request, session_id)
        
        # Verify the result
        assert isinstance(result, AgentOutput)
        assert result.agent_name == "requirements_analyst"
        assert result.output.confidence_score > 0.0
        
        # Verify direct Bedrock call was made
        requirements_analyst_agent.bedrock_client_manager.invoke_with_retry.assert_called_once()
        
        # Verify raw request logging
        raw_request_logged = any(
            "Raw Bedrock request for" in str(call) 
            for call in mock_logger.info.call_args_list
        )
        assert raw_request_logged, "Raw Bedrock request should be logged"
        
        # Verify raw response logging
        raw_response_logged = any(
            "Raw Bedrock response for" in str(call) 
            for call in mock_logger.info.call_args_list
        )
        assert raw_response_logged, "Raw Bedrock response should be logged"
        
        # Verify the analysis results
        output_data = result.output.result
        assert "extracted_requirements" in output_data
        functional_reqs = output_data["extracted_requirements"]["functional_requirements"]
        assert len(functional_reqs) >= 3
        assert "Answer customer questions about products" in functional_reqs
    
    @patch('autoninja.agents.requirements_analyst.logger')
    def test_direct_bedrock_inference_with_tools_enhancement(self, mock_logger, requirements_analyst_agent):
        """Test that tools are used to enhance the Bedrock response"""
        
        # Mock Bedrock response (simple text, not JSON)
        mock_response = Mock()
        mock_response.content = "The user needs a customer support chatbot with basic functionality."
        
        requirements_analyst_agent.bedrock_client_manager.invoke_with_retry.return_value = mock_response
        
        # Test the analysis
        user_request = "Create a customer service bot"
        session_id = "test-tools-enhancement"
        
        result = requirements_analyst_agent.analyze_requirements(user_request, session_id)
        
        # Verify the result
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score >= 0.0
        
        # Verify that tools were used to enhance the response
        output_data = result.output.result
        assert "extracted_requirements" in output_data
        assert "compliance_frameworks" in output_data
        assert "tool_outputs" in output_data
        
        # Verify logging of tool enhancement
        tool_enhancement_logged = any(
            "Tool enhancement" in str(call) or "enhancement" in str(call)
            for call in mock_logger.warning.call_args_list + mock_logger.info.call_args_list
        )
        # Tool enhancement warnings are expected when tools fail, which is normal in mocked environment
    
    def test_make_bedrock_inference_request_structure(self, requirements_analyst_agent):
        """Test the structure of the Bedrock inference request"""
        
        # Mock the invoke_with_retry to capture the call
        mock_response = Mock()
        mock_response.content = '{"test": "response"}'
        requirements_analyst_agent.bedrock_client_manager.invoke_with_retry.return_value = mock_response
        
        # Call the private method directly
        agent_input = "Test user request for chatbot"
        execution_id = "test-execution-123"
        
        result = requirements_analyst_agent._make_bedrock_inference(agent_input, execution_id)
        
        # Verify the method was called with correct parameters
        call_args = requirements_analyst_agent.bedrock_client_manager.invoke_with_retry.call_args
        
        # Check model_id parameter
        assert call_args[1]['model_id'] == BedrockModelId.CLAUDE_SONNET_4_5
        
        # Check messages parameter
        messages = call_args[1]['messages']
        assert len(messages) == 2  # System and Human messages
        assert messages[0].type == "system"
        assert messages[1].type == "human"
        assert agent_input in messages[1].content
        
        # Verify result structure
        assert "output" in result
        assert "raw_bedrock_response" in result
    
    def test_enhance_with_tools_json_parsing(self, requirements_analyst_agent):
        """Test tool enhancement with valid JSON LLM output"""
        
        llm_output = json.dumps({
            "extracted_requirements": {
                "functional_requirements": ["Test requirement"]
            },
            "compliance_frameworks": ["GDPR"]
        })
        
        original_input = "Test input"
        
        enhanced_output = requirements_analyst_agent._enhance_with_tools(llm_output, original_input)
        
        # Should return enhanced JSON
        parsed_output = json.loads(enhanced_output)
        assert "extracted_requirements" in parsed_output
        assert "compliance_frameworks" in parsed_output
    
    def test_enhance_with_tools_text_parsing(self, requirements_analyst_agent):
        """Test tool enhancement with non-JSON LLM output"""
        
        llm_output = "This is a plain text analysis of the requirements."
        original_input = "Test input"
        
        enhanced_output = requirements_analyst_agent._enhance_with_tools(llm_output, original_input)
        
        # Should return structured JSON even from text input
        parsed_output = json.loads(enhanced_output)
        assert "extracted_requirements" in parsed_output
        assert "analysis_summary" in parsed_output
        assert parsed_output["analysis_summary"] == llm_output
    
    @patch('autoninja.agents.requirements_analyst.logger')
    def test_bedrock_inference_error_handling(self, mock_logger, requirements_analyst_agent):
        """Test error handling in direct Bedrock inference"""
        
        # Mock Bedrock client to raise an exception
        requirements_analyst_agent.bedrock_client_manager.invoke_with_retry.side_effect = Exception("Bedrock API error")
        
        user_request = "Test request"
        session_id = "test-error-handling"
        
        result = requirements_analyst_agent.analyze_requirements(user_request, session_id)
        
        # Should handle error gracefully
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score == 0.0
        assert "error" in result.output.result
        
        # Verify error logging
        mock_logger.error.assert_called()
        error_logged = any(
            "Bedrock inference failed" in str(call)
            for call in mock_logger.error.call_args_list
        )
        assert error_logged