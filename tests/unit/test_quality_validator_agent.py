"""
Unit tests for Quality Validator Agent

Tests the Quality Validator Agent's comprehensive code quality analysis,
CloudFormation template validation, and security scanning capabilities.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from autoninja.agents.quality_validator import QualityValidatorAgent, create_quality_validator_agent
from autoninja.models.state import AgentOutput
from autoninja.core.bedrock_client import BedrockClientManager, BedrockModelId, TaskComplexity
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient


class TestQualityValidatorAgent:
    """Test cases for Quality Validator Agent"""
    
    @pytest.fixture
    def mock_bedrock_client_manager(self):
        """Mock Bedrock client manager"""
        manager = Mock(spec=BedrockClientManager)
        manager.select_model_by_complexity.return_value = BedrockModelId.CLAUDE_SONNET_4_5
        
        # Mock the client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = json.dumps({
            "code_quality_analysis": {
                "python_code_quality": {
                    "pylint_score": 8.5,
                    "black_formatting": "PASS",
                    "mypy_type_checking": "PASS",
                    "issues_found": [],
                    "recommendations": ["Add more docstrings"]
                },
                "overall_code_score": 8.5
            },
            "cloudformation_validation": {
                "template_validation": {
                    "syntax_valid": True,
                    "cfn_lint_score": 9.0,
                    "aws_cli_validation": "PASS",
                    "issues_found": []
                },
                "best_practices_score": 8.0
            },
            "security_scan_results": {
                "vulnerability_scan": {
                    "high_severity": 0,
                    "medium_severity": 1,
                    "low_severity": 2,
                    "security_score": 8.0
                },
                "security_recommendations": ["Use environment variables for secrets"]
            },
            "aws_best_practices": {
                "well_architected_compliance": {
                    "security": 8.5,
                    "reliability": 8.0,
                    "performance": 7.5,
                    "cost_optimization": 8.0,
                    "operational_excellence": 7.5
                },
                "overall_compliance_score": 8.0
            },
            "performance_assessment": {
                "performance_score": 7.5,
                "optimization_opportunities": ["Use caching for repeated operations"]
            },
            "compliance_validation": {
                "framework_compliance": {"SOC2": "PASS", "GDPR": "PARTIAL"},
                "compliance_score": 8.0
            },
            "overall_quality_score": 8.1,
            "critical_issues": [],
            "blocking_issues": [],
            "recommendations": ["Consider adding more comprehensive error handling"],
            "production_readiness": {
                "ready_for_deployment": True,
                "confidence_level": "high",
                "required_actions": []
            }
        })
        
        mock_client.invoke.return_value = mock_response
        manager.get_client.return_value = mock_client
        manager.invoke_with_retry.return_value = mock_response
        
        return manager
    
    @pytest.fixture
    def mock_knowledge_base_client(self):
        """Mock knowledge base client"""
        return Mock(spec=BedrockKnowledgeBaseClient)
    
    @pytest.fixture
    def sample_code_generator_output(self):
        """Sample code generator output for testing"""
        return AgentOutput(
            agent_name="code_generator",
            execution_id="test_code_123",
            input_data={"architecture_output": "test architecture"},
            output=AgentOutput.Output(
                result={
                    "bedrock_agent_config": {
                        "agent_name": "TestAgent",
                        "description": "Test AI agent",
                        "foundation_model": "anthropic.claude-3-sonnet-20240229-v1:0"
                    },
                    "action_groups": [
                        {
                            "name": "CoreActions",
                            "description": "Core functionality",
                            "api_schema": {"openapi": "3.0.0"},
                            "lambda_function": "test-handler"
                        }
                    ],
                    "lambda_functions": [
                        {
                            "function_name": "test-handler",
                            "runtime": "python3.12",
                            "handler": "index.lambda_handler",
                            "code": "def lambda_handler(event, context):\n    return {'statusCode': 200}",
                            "environment_variables": {"LOG_LEVEL": "INFO"}
                        }
                    ],
                    "cloudformation_templates": {
                        "main_template": {
                            "AWSTemplateFormatVersion": "2010-09-09",
                            "Resources": {
                                "TestFunction": {
                                    "Type": "AWS::Lambda::Function",
                                    "Properties": {
                                        "Runtime": "python3.12",
                                        "Handler": "index.lambda_handler"
                                    }
                                }
                            }
                        }
                    },
                    "iam_policies": [
                        {
                            "policy_name": "TestPolicy",
                            "policy_document": {
                                "Version": "2012-10-17",
                                "Statement": []
                            }
                        }
                    ]
                },
                confidence_score=0.9,
                reasoning="Code generation completed successfully",
                recommendations=["Review generated code for optimization"]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=45.0,
                model_invocations=1,
                tokens_used=2000
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="test_code_123",
                steps=[{"step": "code_generation", "status": "completed"}]
            )
        )
    
    def test_agent_initialization(self, mock_bedrock_client_manager, mock_knowledge_base_client):
        """Test agent initialization"""
        agent = QualityValidatorAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
        
        assert agent.agent_name == "quality_validator"
        assert agent.bedrock_client_manager == mock_bedrock_client_manager
        assert agent.knowledge_base_client == mock_knowledge_base_client
        assert len(agent.tools) == 6  # 6 validation tools
        assert agent.agent_executor is not None
    
    def test_factory_function(self):
        """Test the factory function"""
        with patch('autoninja.agents.quality_validator.get_bedrock_client_manager') as mock_get_manager:
            mock_manager = Mock(spec=BedrockClientManager)
            mock_get_manager.return_value = mock_manager
            
            agent = create_quality_validator_agent()
            
            assert isinstance(agent, QualityValidatorAgent)
            assert agent.bedrock_client_manager == mock_manager
    
    def test_get_agent_info(self, mock_bedrock_client_manager):
        """Test agent information retrieval"""
        agent = QualityValidatorAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        info = agent.get_agent_info()
        
        assert info["agent_name"] == "quality_validator"
        assert info["agent_type"] == "quality_validator"
        assert "Static code analysis with pylint, black, and mypy" in info["capabilities"]
        assert "CloudFormation template validation with cfn-lint" in info["capabilities"]
        assert "Security scanning for vulnerabilities" in info["capabilities"]
        assert len(info["tools"]) == 6
        assert info["model_complexity"] == TaskComplexity.HIGH.value
    
    @patch('autoninja.agents.quality_validator.get_pipeline_logger')
    @patch('autoninja.agents.quality_validator.log_bedrock_request')
    @patch('autoninja.agents.quality_validator.log_bedrock_response')
    def test_validate_quality_success(
        self, 
        mock_log_response,
        mock_log_request,
        mock_get_pipeline_logger,
        mock_bedrock_client_manager,
        mock_knowledge_base_client,
        sample_code_generator_output
    ):
        """Test successful quality validation"""
        # Setup mocks
        mock_pipeline_logger = Mock()
        mock_get_pipeline_logger.return_value = mock_pipeline_logger
        
        agent = QualityValidatorAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
        
        # Execute quality validation
        result = agent.validate_quality(
            code_generator_output=sample_code_generator_output,
            session_id="test_session_123"
        )
        
        # Verify result structure
        assert isinstance(result, AgentOutput)
        assert result.agent_name == "quality_validator"
        assert result.output.confidence_score > 0
        assert "code_quality_analysis" in result.output.result
        assert "cloudformation_validation" in result.output.result
        assert "security_scan_results" in result.output.result
        assert "aws_best_practices" in result.output.result
        assert "performance_assessment" in result.output.result
        assert "compliance_validation" in result.output.result
        assert "overall_quality_score" in result.output.result
        assert "production_readiness" in result.output.result
        
        # Verify logging calls
        mock_pipeline_logger.log_agent_input.assert_called_once()
        mock_pipeline_logger.log_agent_output.assert_called_once()
        mock_log_request.assert_called_once()
        mock_log_response.assert_called_once()
    
    @patch('autoninja.agents.quality_validator.get_pipeline_logger')
    def test_validate_quality_error_handling(
        self,
        mock_get_pipeline_logger,
        mock_bedrock_client_manager,
        sample_code_generator_output
    ):
        """Test error handling in quality validation"""
        # Setup mocks to raise exception
        mock_pipeline_logger = Mock()
        mock_get_pipeline_logger.return_value = mock_pipeline_logger
        
        mock_bedrock_client_manager.invoke_with_retry.side_effect = Exception("Validation error")
        
        agent = QualityValidatorAgent(
            bedrock_client_manager=mock_bedrock_client_manager
        )
        
        # Execute quality validation
        result = agent.validate_quality(
            code_generator_output=sample_code_generator_output,
            session_id="test_session_123"
        )
        
        # Verify error handling
        assert isinstance(result, AgentOutput)
        assert result.output.confidence_score == 0.0
        assert "error" in result.output.result
        assert "Validation error" in result.output.reasoning
        
        # Verify error logging
        mock_pipeline_logger.log_pipeline_error.assert_called_once()
    
    def test_prepare_agent_input(self, mock_bedrock_client_manager, sample_code_generator_output):
        """Test agent input preparation"""
        agent = QualityValidatorAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        additional_context = {"compliance_framework": "SOC2", "security_level": "high"}
        
        agent_input = agent._prepare_agent_input(sample_code_generator_output, additional_context)
        
        assert isinstance(agent_input, str)
        assert "Perform comprehensive quality validation" in agent_input
        assert "Generated Code and Configurations:" in agent_input
        assert "Analyze Python code quality" in agent_input
        assert "Validate CloudFormation templates" in agent_input
        assert "Perform security scanning" in agent_input
        assert "Verify AWS best practices" in agent_input
        assert "Assess performance characteristics" in agent_input
        assert "Check compliance" in agent_input
        assert json.dumps(additional_context, indent=2) in agent_input
    
    def test_process_agent_output_json(self, mock_bedrock_client_manager):
        """Test processing of JSON agent output"""
        agent = QualityValidatorAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        raw_output = {
            "output": json.dumps({
                "code_quality_analysis": {"score": 8.5},
                "security_scan_results": {"vulnerabilities": 0},
                "overall_quality_score": 8.2,
                "production_readiness": {"ready": True}
            }),
            "intermediate_steps": []
        }
        
        result = agent._process_agent_output(raw_output)
        
        assert "code_quality_analysis" in result
        assert "security_scan_results" in result
        assert "overall_quality_score" in result
        assert "production_readiness" in result
        assert result["overall_quality_score"] == 8.2
    
    def test_process_agent_output_text(self, mock_bedrock_client_manager):
        """Test processing of text agent output"""
        agent = QualityValidatorAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        raw_output = {
            "output": "Quality validation completed with high scores",
            "intermediate_steps": []
        }
        
        result = agent._process_agent_output(raw_output)
        
        assert "code_quality_analysis" in result
        assert "security_scan_results" in result
        assert result["validation_summary"] == "Quality validation completed with high scores"
        assert result["validation_method"] == "text_analysis"
    
    def test_calculate_confidence_score(self, mock_bedrock_client_manager):
        """Test confidence score calculation"""
        agent = QualityValidatorAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        # Complete output with high quality score
        complete_output = {
            "code_quality_analysis": {"score": 8.5},
            "cloudformation_validation": {"valid": True},
            "security_scan_results": {"vulnerabilities": 0},
            "aws_best_practices": {"compliant": True},
            "performance_assessment": {"optimized": True},
            "compliance_validation": {"compliant": True},
            "overall_quality_score": 8.5
        }
        
        score = agent._calculate_confidence_score(complete_output)
        assert score == 1.0
        
        # Partial output with lower quality score
        partial_output = {
            "code_quality_analysis": {"score": 6.0},
            "overall_quality_score": 6.0
        }
        
        score = agent._calculate_confidence_score(partial_output)
        assert 0.2 <= score <= 0.3  # 20% for code quality analysis
    
    def test_verify_response_compatibility(self, mock_bedrock_client_manager):
        """Test response compatibility verification"""
        agent = QualityValidatorAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        # Test with missing fields
        incomplete_output = {
            "code_quality_analysis": {"score": 8.0}
        }
        
        agent._verify_response_compatibility(incomplete_output)
        
        # Verify that missing fields were added
        assert "overall_quality_score" in incomplete_output
        assert "production_readiness" in incomplete_output
        assert "critical_issues" in incomplete_output
        assert "recommendations" in incomplete_output
        assert incomplete_output["production_readiness"]["ready_for_deployment"] is False
        assert incomplete_output["production_readiness"]["confidence_level"] == "low"
    
    def test_generate_recommendations(self, mock_bedrock_client_manager):
        """Test recommendation generation"""
        agent = QualityValidatorAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        # Test with low quality score and issues
        poor_output = {
            "overall_quality_score": 5.0,
            "critical_issues": ["Security vulnerability", "Syntax error"],
            "blocking_issues": ["Missing IAM policy"],
            "production_readiness": {"ready_for_deployment": False},
            "recommendations": ["Fix security issues", "Add proper error handling"]
        }
        
        recommendations = agent._generate_recommendations(poor_output)
        
        assert len(recommendations) >= 4
        assert any("quality score" in rec for rec in recommendations)
        assert any("critical issues" in rec for rec in recommendations)
        assert any("blocking issues" in rec for rec in recommendations)
        assert any("not ready for production" in rec for rec in recommendations)
        
        # Test with good output
        good_output = {
            "overall_quality_score": 9.0,
            "critical_issues": [],
            "blocking_issues": [],
            "production_readiness": {"ready_for_deployment": True},
            "recommendations": []
        }
        
        recommendations = agent._generate_recommendations(good_output)
        assert "ready for deployment preparation" in recommendations[0]
    
    def test_extract_code_from_input(self, mock_bedrock_client_manager):
        """Test code extraction from agent input"""
        agent = QualityValidatorAgent(bedrock_client_manager=mock_bedrock_client_manager)
        
        # Test input with code content
        agent_input = '''
Perform comprehensive quality validation on this generated AI agent code and configurations:

Generated Code and Configurations: {
    "lambda_functions": [
        {
            "function_name": "test-handler",
            "code": "def lambda_handler(event, context):\\n    return {'statusCode': 200}"
        }
    ],
    "cloudformation_templates": {
        "main_template": {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {}
        }
    }
}

Additional Context:
{"framework": "SOC2"}
'''
        
        code_content = agent._extract_code_from_input(agent_input)
        
        assert "python_code" in code_content
        assert "cloudformation_template" in code_content
        assert "def lambda_handler" in code_content["python_code"]
        assert "AWSTemplateFormatVersion" in code_content["cloudformation_template"]
    
    @patch('autoninja.agents.quality_validator.get_pipeline_logger')
    @patch('autoninja.agents.quality_validator.log_bedrock_request')
    @patch('autoninja.agents.quality_validator.log_bedrock_response')
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
        
        agent = QualityValidatorAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
        
        agent_input = "Validate quality of generated code"
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
        agent = QualityValidatorAgent(
            bedrock_client_manager=mock_bedrock_client_manager,
            knowledge_base_client=mock_knowledge_base_client
        )
        
        # Mock tool responses
        for tool in agent.tools:
            if hasattr(tool, '_run'):
                tool._run = Mock(return_value=json.dumps({
                    "quality_score": 8.5,
                    "validation_score": 9.0,
                    "security_score": 8.0,
                    "status": "PASS"
                }))
        
        llm_output = json.dumps({
            "code_quality_analysis": {"score": 8.0},
            "security_scan_results": {"vulnerabilities": 0}
        })
        
        enhanced_output = agent._enhance_with_tools(llm_output, "test input")
        
        assert isinstance(enhanced_output, str)
        enhanced_data = json.loads(enhanced_output)
        assert "code_quality_analysis" in enhanced_data
        assert "security_scan_results" in enhanced_data


class TestQualityValidatorAgentIntegration:
    """Integration tests for Quality Validator Agent"""
    
    @pytest.fixture
    def real_bedrock_manager(self):
        """Real Bedrock client manager for integration tests"""
        return BedrockClientManager()
    
    @pytest.mark.integration
    def test_full_quality_validation_flow(self, real_bedrock_manager):
        """Test full quality validation flow with real Bedrock client"""
        # Skip if no AWS credentials
        pytest.importorskip("boto3")
        
        agent = QualityValidatorAgent(bedrock_client_manager=real_bedrock_manager)
        
        # Create sample code generator output
        code_generator_output = AgentOutput(
            agent_name="code_generator",
            execution_id="integration_test",
            input_data={"architecture_output": "test architecture"},
            output=AgentOutput.Output(
                result={
                    "bedrock_agent_config": {"agent_name": "TestAgent"},
                    "lambda_functions": [{
                        "function_name": "test-handler",
                        "code": "def lambda_handler(event, context):\n    return {'statusCode': 200}"
                    }],
                    "cloudformation_templates": {
                        "main_template": {
                            "AWSTemplateFormatVersion": "2010-09-09",
                            "Resources": {}
                        }
                    }
                },
                confidence_score=0.8,
                reasoning="Code generated successfully",
                recommendations=[]
            ),
            execution_metadata=AgentOutput.ExecutionMetadata(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_seconds=30.0,
                model_invocations=1,
                tokens_used=1000
            ),
            trace_data=AgentOutput.TraceData(
                trace_id="integration_test",
                steps=[]
            )
        )
        
        # This would make a real call to Bedrock
        # Uncomment for actual integration testing
        # result = agent.validate_quality(code_generator_output, "integration_session")
        # assert isinstance(result, AgentOutput)
        # assert result.output.confidence_score > 0
        # assert "overall_quality_score" in result.output.result


if __name__ == "__main__":
    pytest.main([__file__])