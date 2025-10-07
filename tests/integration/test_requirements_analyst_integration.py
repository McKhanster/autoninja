"""
Integration tests for Requirements Analyst Agent with real Bedrock inference

These tests make actual calls to Amazon Bedrock models to verify the agent
works end-to-end with real model inference and logging.
"""

import json
import pytest
import logging
from unittest.mock import patch
import os

from autoninja.agents.requirements_analyst import RequirementsAnalystAgent, create_requirements_analyst_agent
from autoninja.core.bedrock_client import BedrockClientManager, BedrockModelId
from autoninja.models.state import AgentOutput

# Configure logging to capture the raw requests/responses
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRequirementsAnalystIntegration:
    """Integration tests with real Bedrock model inference"""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"),
        reason="AWS credentials not available"
    )
    def test_real_bedrock_inference_simple_request(self):
        """Test real Bedrock inference with a simple customer service request"""
        
        # Create agent with real Bedrock client
        agent = create_requirements_analyst_agent()
        
        # Simple user request
        user_request = """
        I need a customer service chatbot for my small business. 
        It should answer basic questions about our products and hours.
        The bot should be simple and cost-effective.
        """
        
        session_id = "integration-test-simple"
        
        # Make real inference call
        result = agent.analyze_requirements(user_request, session_id)
        
        # Verify the result structure
        assert isinstance(result, AgentOutput)
        assert result.agent_name == "requirements_analyst"
        assert result.input_data["user_request"] == user_request
        assert result.input_data["session_id"] == session_id
        
        # Verify we got meaningful analysis
        assert result.output.confidence_score > 0.0
        assert "extracted_requirements" in result.output.result
        assert len(result.output.recommendations) > 0
        
        # Log the results for inspection
        logger.info(f"=== INTEGRATION TEST RESULTS ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Confidence Score: {result.output.confidence_score}")
        logger.info(f"Analysis Result: {json.dumps(result.output.result, indent=2)}")
        logger.info(f"Recommendations: {result.output.recommendations}")
        logger.info(f"Execution Time: {result.execution_metadata.duration_seconds}s")
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"),
        reason="AWS credentials not available"
    )
    def test_real_bedrock_inference_complex_request(self):
        """Test real Bedrock inference with a complex enterprise request"""
        
        # Create agent with real Bedrock client
        agent = create_requirements_analyst_agent()
        
        # Complex enterprise request
        user_request = """
        I need an AI agent for our healthcare organization that can:
        1. Process patient inquiries about appointments and billing
        2. Integrate with our existing EHR system (Epic)
        3. Ensure HIPAA compliance for all patient data
        4. Handle multiple languages (English, Spanish, French)
        5. Escalate complex medical questions to human staff
        6. Generate reports on common inquiry types
        7. Work 24/7 with high availability requirements
        8. Scale to handle 10,000+ daily interactions
        
        The system must be secure, auditable, and meet healthcare regulations.
        We have a budget of $50,000 for initial implementation.
        """
        
        session_id = "integration-test-complex"
        additional_context = {
            "industry": "healthcare",
            "compliance_requirements": ["HIPAA", "HITECH"],
            "integration_systems": ["Epic EHR"],
            "languages": ["English", "Spanish", "French"]
        }
        
        # Make real inference call
        result = agent.analyze_requirements(user_request, session_id, additional_context)
        
        # Verify the result structure
        assert isinstance(result, AgentOutput)
        assert result.agent_name == "requirements_analyst"
        assert result.input_data["additional_context"] == additional_context
        
        # Verify we got comprehensive analysis
        assert result.output.confidence_score > 0.5  # Should be reasonably confident
        
        output_data = result.output.result
        assert "extracted_requirements" in output_data
        assert "compliance_frameworks" in output_data
        assert "complexity_assessment" in output_data
        
        # Should detect healthcare compliance requirements
        compliance_frameworks = output_data.get("compliance_frameworks", [])
        assert len(compliance_frameworks) > 0
        
        # Should have multiple recommendations for complex system
        assert len(result.output.recommendations) >= 3
        
        # Log the comprehensive results
        logger.info(f"=== COMPLEX INTEGRATION TEST RESULTS ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Confidence Score: {result.output.confidence_score}")
        logger.info(f"Detected Compliance Frameworks: {compliance_frameworks}")
        logger.info(f"Number of Recommendations: {len(result.output.recommendations)}")
        logger.info(f"Execution Time: {result.execution_metadata.duration_seconds}s")
        logger.info(f"Full Analysis: {json.dumps(output_data, indent=2)}")
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"),
        reason="AWS credentials not available"
    )
    def test_real_bedrock_inference_with_logging_verification(self):
        """Test that raw requests and responses are properly logged"""
        
        # Create agent with real Bedrock client
        agent = create_requirements_analyst_agent()
        
        # Capture logs
        with patch('autoninja.agents.requirements_analyst.logger') as mock_logger:
            user_request = "Create a simple task automation agent for my team"
            session_id = "integration-test-logging"
            
            # Make real inference call
            result = agent.analyze_requirements(user_request, session_id)
            
            # Verify the call was successful
            assert isinstance(result, AgentOutput)
            assert result.output.confidence_score > 0.0
            
            # Verify that logging occurred
            mock_logger.info.assert_called()
            
            # Check that raw request and response logging happened
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            
            # Should have logged raw request
            raw_request_logged = any("Raw request for" in log_msg for log_msg in log_calls)
            assert raw_request_logged, "Raw request should be logged"
            
            # Should have logged raw response  
            raw_response_logged = any("Raw response for" in log_msg for log_msg in log_calls)
            assert raw_response_logged, "Raw response should be logged"
            
            # Should have logged completion
            completion_logged = any("Requirements analysis completed successfully" in log_msg for log_msg in log_calls)
            assert completion_logged, "Completion should be logged"
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"),
        reason="AWS credentials not available"
    )
    def test_model_selection_and_inference(self):
        """Test that the agent selects appropriate models and makes inference calls"""
        
        # Create agent with real Bedrock client
        bedrock_manager = BedrockClientManager()
        agent = RequirementsAnalystAgent(bedrock_client_manager=bedrock_manager)
        
        # Verify model selection
        available_models = bedrock_manager.get_available_models()
        assert len(available_models) > 0, "Should have available Bedrock models"
        
        # Verify the agent uses medium complexity model (Claude Sonnet)
        expected_model = bedrock_manager.select_model_by_complexity(
            agent.bedrock_client_manager.select_model_by_complexity.__defaults__[0]  # TaskComplexity.MEDIUM
        )
        assert expected_model == BedrockModelId.CLAUDE_SONNET_4_5
        
        # Test inference with different request types
        test_cases = [
            {
                "request": "Simple chatbot for customer support",
                "expected_type": "conversational"
            },
            {
                "request": "Data analysis agent for business intelligence reports",
                "expected_type": "analytical"  
            },
            {
                "request": "Workflow automation for document processing",
                "expected_type": "automation"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            session_id = f"model-test-{i}"
            
            result = agent.analyze_requirements(test_case["request"], session_id)
            
            # Verify successful inference
            assert isinstance(result, AgentOutput)
            assert result.output.confidence_score > 0.0
            
            # Log the model inference results
            logger.info(f"=== MODEL INFERENCE TEST {i+1} ===")
            logger.info(f"Request: {test_case['request']}")
            logger.info(f"Expected Type: {test_case['expected_type']}")
            logger.info(f"Confidence: {result.output.confidence_score}")
            logger.info(f"Analysis Time: {result.execution_metadata.duration_seconds}s")


class TestRequirementsAnalystRealWorldScenarios:
    """Test real-world scenarios with actual Bedrock inference"""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"),
        reason="AWS credentials not available"
    )
    def test_ecommerce_chatbot_scenario(self):
        """Test e-commerce chatbot requirements analysis"""
        
        agent = create_requirements_analyst_agent()
        
        user_request = """
        We run an online clothing store and need a chatbot that can:
        - Help customers find products based on size, color, style preferences
        - Answer questions about shipping, returns, and exchange policies  
        - Process simple order status inquiries
        - Recommend products based on browsing history
        - Handle multiple languages for international customers
        - Integrate with our Shopify store and customer service platform
        
        The bot should be friendly, fashion-aware, and able to handle peak shopping seasons.
        We need it to reduce our customer service workload by at least 40%.
        """
        
        result = agent.analyze_requirements(user_request, "ecommerce-scenario")
        
        # Verify comprehensive analysis
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score > 0.6
        
        output_data = result.output.result
        functional_reqs = output_data.get("extracted_requirements", {}).get("functional_requirements", [])
        
        # Should extract key e-commerce functionalities
        assert len(functional_reqs) >= 4
        
        # Log results
        logger.info(f"=== E-COMMERCE SCENARIO RESULTS ===")
        logger.info(f"Functional Requirements: {len(functional_reqs)}")
        logger.info(f"Recommendations: {result.output.recommendations}")
    
    @pytest.mark.integration  
    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"),
        reason="AWS credentials not available"
    )
    def test_financial_compliance_scenario(self):
        """Test financial services compliance requirements analysis"""
        
        agent = create_requirements_analyst_agent()
        
        user_request = """
        Our credit union needs an AI assistant for member services that can:
        - Answer questions about account balances, transactions, and loan status
        - Help members with basic banking tasks like transfers and bill pay
        - Provide information about loan products and interest rates
        - Assist with fraud alerts and security questions
        - Comply with all banking regulations including PCI DSS, SOX, and GLBA
        - Maintain detailed audit logs of all interactions
        - Integrate with our core banking system (Jack Henry)
        
        Security and compliance are our top priorities. The system must be bulletproof.
        """
        
        additional_context = {
            "industry": "financial_services",
            "compliance_requirements": ["PCI DSS", "SOX", "GLBA", "FFIEC"],
            "integration_systems": ["Jack Henry Core Banking"]
        }
        
        result = agent.analyze_requirements(user_request, "financial-scenario", additional_context)
        
        # Verify compliance detection
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score > 0.5
        
        output_data = result.output.result
        compliance_frameworks = output_data.get("compliance_frameworks", [])
        
        # Should detect financial compliance requirements
        assert len(compliance_frameworks) > 0
        
        # Should have security-focused recommendations
        recommendations = result.output.recommendations
        security_recommendations = [r for r in recommendations if any(
            keyword in r.lower() for keyword in ["security", "compliance", "audit", "encryption"]
        )]
        assert len(security_recommendations) > 0
        
        # Log results
        logger.info(f"=== FINANCIAL COMPLIANCE SCENARIO RESULTS ===")
        logger.info(f"Detected Compliance Frameworks: {compliance_frameworks}")
        logger.info(f"Security Recommendations: {security_recommendations}")