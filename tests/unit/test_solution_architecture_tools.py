"""
Unit tests for Solution Architecture Tools
"""

import json
import pytest
from unittest.mock import Mock
from autoninja.tools.solution_architecture import (
    ServiceSelectionTool,
    CloudFormationGeneratorTool,
    CostEstimationTool
)
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient


class TestServiceSelectionTool:
    """Test cases for ServiceSelectionTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = ServiceSelectionTool()
    
    def test_basic_service_selection(self):
        """Test basic AWS service selection."""
        requirements = {
            "functional_requirements": ["process user requests", "store data"],
            "non_functional_requirements": {"performance": ["fast response"]},
            "agent_type_detected": "conversational"
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        assert "recommended_services" in result_data
        assert "service_configuration" in result_data
        assert "cost_estimate" in result_data
        
        services = result_data["recommended_services"]
        service_names = [s["service"] for s in services]
        
        # Check for core services
        assert "Amazon Bedrock" in service_names
        assert "AWS Lambda" in service_names
        assert "Amazon DynamoDB" in service_names
    
    def test_service_selection_with_constraints(self):
        """Test service selection with budget constraints."""
        requirements = {
            "functional_requirements": ["basic processing"],
            "agent_type_detected": "simple"
        }
        
        constraints = {
            "budget": "minimal",
            "technology": ["serverless_only"]
        }
        
        result = self.tool._run(requirements, constraints)
        result_data = json.loads(result)
        
        services = result_data["recommended_services"]
        
        # Should not include expensive services for minimal budget
        service_names = [s["service"] for s in services]
        assert "Amazon ElastiCache" not in service_names  # Expensive service
    
    def test_api_service_detection(self):
        """Test detection of API-related services."""
        requirements = {
            "functional_requirements": ["provide REST API endpoints", "handle HTTP requests"],
            "agent_type_detected": "api"
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        services = result_data["recommended_services"]
        service_names = [s["service"] for s in services]
        
        assert "Amazon API Gateway" in service_names
    
    def test_performance_requirements(self):
        """Test service selection for performance requirements."""
        requirements = {
            "functional_requirements": ["fast data processing"],
            "non_functional_requirements": {
                "performance": ["real-time response", "low latency"]
            },
            "agent_type_detected": "analytical"
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        services = result_data["recommended_services"]
        service_names = [s["service"] for s in services]
        
        # Should include caching for performance
        assert "Amazon ElastiCache" in service_names
    
    def test_cost_estimation(self):
        """Test cost estimation functionality."""
        requirements = {
            "functional_requirements": ["basic processing"],
            "agent_type_detected": "simple"
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        cost_estimate = result_data["cost_estimate"]
        
        assert "monthly_estimate" in cost_estimate
        assert "service_breakdown" in cost_estimate
        assert "cost_factors" in cost_estimate
        assert isinstance(cost_estimate["monthly_estimate"], (int, float))
    
    def test_deployment_complexity_assessment(self):
        """Test deployment complexity assessment."""
        requirements = {
            "functional_requirements": ["complex processing", "multiple integrations"],
            "non_functional_requirements": {
                "performance": ["high performance"],
                "availability": ["high availability"]
            },
            "agent_type_detected": "complex"
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        complexity = result_data["deployment_complexity"]
        
        assert "complexity_level" in complexity
        assert "complexity_score" in complexity
        assert "estimated_deployment_time" in complexity
        assert complexity["complexity_level"] in ["low", "medium", "high"]
    
    def test_with_knowledge_base_client(self):
        """Test tool with knowledge base client."""
        mock_kb_client = Mock(spec=BedrockKnowledgeBaseClient)
        mock_kb_client.search_knowledge_base.return_value = [
            Mock(title="Pattern 1", excerpt="Description 1", relevance_score=0.9, content="Content 1")
        ]
        
        tool = ServiceSelectionTool(knowledge_base_client=mock_kb_client)
        
        requirements = {
            "functional_requirements": ["process requests"],
            "agent_type_detected": "conversational"
        }
        
        result = tool._run(requirements)
        result_data = json.loads(result)
        
        assert "architecture_patterns" in result_data
        assert len(result_data["architecture_patterns"]) > 0


class TestCloudFormationGeneratorTool:
    """Test cases for CloudFormationGeneratorTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CloudFormationGeneratorTool()
    
    def test_basic_template_generation(self):
        """Test basic CloudFormation template generation."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True},
                "APIGateway": {"enabled": True},
                "DynamoDB": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        assert "cloudformation_template" in result_data
        assert "deployment_instructions" in result_data
        assert "validation_commands" in result_data
        
        template = result_data["cloudformation_template"]
        
        # Check template structure
        assert "AWSTemplateFormatVersion" in template
        assert "Description" in template
        assert "Parameters" in template
        assert "Resources" in template
        assert "Outputs" in template
    
    def test_lambda_resources(self):
        """Test Lambda resource generation."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        resources = template["Resources"]
        
        assert "LambdaExecutionRole" in resources
        assert "AgentLambdaFunction" in resources
        
        # Check Lambda function properties
        lambda_func = resources["AgentLambdaFunction"]
        assert lambda_func["Type"] == "AWS::Lambda::Function"
        assert lambda_func["Properties"]["Runtime"] == "python3.12"
    
    def test_api_gateway_resources(self):
        """Test API Gateway resource generation."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True},
                "APIGateway": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        resources = template["Resources"]
        
        assert "AgentRestApi" in resources
        assert "AgentApiResource" in resources
        assert "AgentApiMethod" in resources
        assert "AgentApiDeployment" in resources
        assert "LambdaApiPermission" in resources
    
    def test_dynamodb_resources(self):
        """Test DynamoDB resource generation."""
        architecture = {
            "services": {
                "DynamoDB": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        resources = template["Resources"]
        
        assert "AgentStateTable" in resources
        
        table = resources["AgentStateTable"]
        assert table["Type"] == "AWS::DynamoDB::Table"
        assert table["Properties"]["BillingMode"] == {"Ref": "DynamoDBBillingMode"}
    
    def test_s3_resources(self):
        """Test S3 resource generation."""
        architecture = {
            "services": {
                "S3": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        resources = template["Resources"]
        
        assert "AgentArtifactsBucket" in resources
        
        bucket = resources["AgentArtifactsBucket"]
        assert bucket["Type"] == "AWS::S3::Bucket"
        assert bucket["Properties"]["VersioningConfiguration"]["Status"] == "Enabled"
    
    def test_parameters_generation(self):
        """Test CloudFormation parameters generation."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True},
                "DynamoDB": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        parameters = template["Parameters"]
        
        # Check basic parameters
        assert "AgentName" in parameters
        assert "Environment" in parameters
        assert "KMSKeyId" in parameters
        
        # Check service-specific parameters
        assert "LambdaMemorySize" in parameters
        assert "DynamoDBBillingMode" in parameters
    
    def test_outputs_generation(self):
        """Test CloudFormation outputs generation."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True},
                "APIGateway": {"enabled": True},
                "DynamoDB": {"enabled": True},
                "S3": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        outputs = template["Outputs"]
        
        assert "ApiEndpoint" in outputs
        assert "LambdaFunctionArn" in outputs
        assert "DynamoDBTableName" in outputs
        assert "S3BucketName" in outputs
    
    def test_deployment_instructions(self):
        """Test deployment instructions generation."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        instructions = result_data["deployment_instructions"]
        
        assert isinstance(instructions, list)
        assert len(instructions) > 0
        assert any("validate-template" in instruction for instruction in instructions)
        assert any("create-stack" in instruction for instruction in instructions)
    
    def test_validation_commands(self):
        """Test validation commands generation."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        commands = result_data["validation_commands"]
        
        assert isinstance(commands, list)
        assert len(commands) > 0
        assert any("validate-template" in command for command in commands)
        assert any("cfn-lint" in command for command in commands)


class TestCostEstimationTool:
    """Test cases for CostEstimationTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CostEstimationTool()
    
    def test_basic_cost_estimation(self):
        """Test basic cost estimation."""
        architecture = {
            "services": {
                "Bedrock": {"enabled": True},
                "Lambda": {"enabled": True},
                "APIGateway": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        assert "cost_breakdown" in result_data
        assert "total_monthly_cost" in result_data
        assert "cost_optimizations" in result_data
        assert "usage_assumptions" in result_data
        
        # Check cost breakdown
        cost_breakdown = result_data["cost_breakdown"]
        assert "Bedrock" in cost_breakdown
        assert "Lambda" in cost_breakdown
        assert "APIGateway" in cost_breakdown
        
        # Check total costs
        total_costs = result_data["total_monthly_cost"]
        assert "monthly" in total_costs
        assert "annual" in total_costs
        assert "daily" in total_costs
    
    def test_bedrock_cost_calculation(self):
        """Test Bedrock cost calculation."""
        architecture = {
            "services": {
                "Bedrock": {"enabled": True}
            }
        }
        
        usage_patterns = {
            "monthly_requests": 50000,
            "average_request_duration": 2.0,
            "lambda_memory": 1024,
            "storage_gb": 5,
            "data_transfer_gb": 25,
            "concurrent_users": 50,
            "peak_usage_factor": 1.5
        }
        
        result = self.tool._run(architecture, usage_patterns)
        result_data = json.loads(result)
        
        bedrock_costs = result_data["cost_breakdown"]["Bedrock"]
        
        assert "input_token_cost" in bedrock_costs
        assert "output_token_cost" in bedrock_costs
        assert "monthly_total" in bedrock_costs
        assert "usage_details" in bedrock_costs
        
        assert bedrock_costs["monthly_total"] > 0
    
    def test_lambda_cost_calculation(self):
        """Test Lambda cost calculation."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        lambda_costs = result_data["cost_breakdown"]["Lambda"]
        
        assert "request_cost" in lambda_costs
        assert "compute_cost" in lambda_costs
        assert "monthly_total" in lambda_costs
        assert "usage_details" in lambda_costs
        
        assert lambda_costs["monthly_total"] > 0
    
    def test_dynamodb_cost_calculation(self):
        """Test DynamoDB cost calculation."""
        architecture = {
            "services": {
                "DynamoDB": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        dynamodb_costs = result_data["cost_breakdown"]["DynamoDB"]
        
        assert "read_cost" in dynamodb_costs
        assert "write_cost" in dynamodb_costs
        assert "storage_cost" in dynamodb_costs
        assert "monthly_total" in dynamodb_costs
        
        assert dynamodb_costs["monthly_total"] > 0
    
    def test_cost_optimizations(self):
        """Test cost optimization recommendations."""
        architecture = {
            "services": {
                "Bedrock": {"enabled": True},
                "Lambda": {"enabled": True},
                "DynamoDB": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        optimizations = result_data["cost_optimizations"]
        
        assert isinstance(optimizations, list)
        assert len(optimizations) > 0
        
        # Check optimization structure
        for opt in optimizations:
            assert "service" in opt
            assert "recommendation" in opt
            assert "potential_savings" in opt
            assert "implementation" in opt
    
    def test_custom_usage_patterns(self):
        """Test cost estimation with custom usage patterns."""
        architecture = {
            "services": {
                "Lambda": {"enabled": True}
            }
        }
        
        custom_usage = {
            "monthly_requests": 1000000,  # High volume
            "average_request_duration": 5.0,  # Longer duration
            "lambda_memory": 2048,  # More memory
            "storage_gb": 100,
            "data_transfer_gb": 500,
            "concurrent_users": 1000,
            "peak_usage_factor": 3.0
        }
        
        result = self.tool._run(architecture, custom_usage)
        result_data = json.loads(result)
        
        # Should have higher costs due to increased usage
        lambda_costs = result_data["cost_breakdown"]["Lambda"]
        assert lambda_costs["monthly_total"] > 10  # Should be significant cost
        
        # Check that custom usage is reflected
        usage_assumptions = result_data["usage_assumptions"]
        assert usage_assumptions["monthly_requests"] == 1000000
        assert usage_assumptions["lambda_memory"] == 2048
    
    def test_cost_factors_identification(self):
        """Test identification of cost factors."""
        architecture = {
            "services": {
                "Bedrock": {"enabled": True},
                "DynamoDB": {"enabled": True},
                "S3": {"enabled": True}
            }
        }
        
        result = self.tool._run(architecture)
        result_data = json.loads(result)
        
        cost_factors = result_data["cost_factors"]
        
        assert isinstance(cost_factors, list)
        assert len(cost_factors) > 0
        
        # Should include service-specific factors
        factors_text = " ".join(cost_factors)
        assert "Bedrock" in factors_text
        assert "DynamoDB" in factors_text
        assert "S3" in factors_text


if __name__ == "__main__":
    pytest.main([__file__])