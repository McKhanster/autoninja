"""
Unit tests for Code Generation Tools
"""

import json
import pytest
from unittest.mock import Mock
from autoninja.tools.code_generation import (
    BedrockAgentConfigTool,
    ActionGroupGeneratorTool,
    DeploymentTemplateGeneratorTool
)
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient


class TestBedrockAgentConfigTool:
    """Test cases for BedrockAgentConfigTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = BedrockAgentConfigTool()
    
    def test_basic_agent_config_generation(self):
        """Test basic Bedrock Agent configuration generation."""
        requirements = {
            "functional_requirements": ["process user requests", "provide responses"],
            "agent_type_detected": "conversational"
        }
        
        architecture = {
            "services": {
                "Bedrock": {"enabled": True},
                "Lambda": {"enabled": True}
            }
        }
        
        result = self.tool._run(requirements, architecture)
        result_data = json.loads(result)
        
        assert "agent_configuration" in result_data
        assert "action_groups" in result_data
        assert "knowledge_base_configuration" in result_data
        assert "deployment_artifacts" in result_data
        
        # Check agent configuration
        agent_config = result_data["agent_configuration"]
        assert "agent_name" in agent_config
        assert "foundation_model" in agent_config
        assert "instruction" in agent_config
        assert "conversational" in agent_config["agent_name"].lower()
    
    def test_complexity_assessment(self):
        """Test complexity assessment and model selection."""
        # High complexity requirements
        high_complexity_reqs = {
            "functional_requirements": [
                "analyze complex data using machine learning algorithms",
                "perform advanced AI-powered intelligent processing",
                "complex analytical computations"
            ],
            "agent_type_detected": "analytical"
        }
        
        architecture = {"services": {"Bedrock": {"enabled": True}}}
        
        result = self.tool._run(high_complexity_reqs, architecture)
        result_data = json.loads(result)
        
        agent_config = result_data["agent_configuration"]
        # Should select Opus model for high complexity
        assert "opus" in agent_config["foundation_model"]
    
    def test_action_group_generation(self):
        """Test action group generation based on requirements."""
        requirements = {
            "functional_requirements": [
                "store user data",
                "retrieve information",
                "send notifications",
                "integrate with external APIs"
            ],
            "agent_type_detected": "custom"
        }
        
        architecture = {"services": {"Bedrock": {"enabled": True}}}
        
        result = self.tool._run(requirements, architecture)
        result_data = json.loads(result)
        
        action_groups = result_data["action_groups"]
        
        assert len(action_groups) > 0
        
        # Should have core actions
        action_group_names = [ag["action_group_name"] for ag in action_groups]
        assert "CoreActions" in action_group_names
        
        # Should have data actions due to "store" and "retrieve" requirements
        assert "DataActions" in action_group_names
        
        # Should have integration actions due to "integrate" requirement
        assert "IntegrationActions" in action_group_names
    
    def test_knowledge_base_configuration(self):
        """Test knowledge base configuration generation."""
        requirements = {
            "functional_requirements": ["answer questions"],
            "agent_type_detected": "conversational"
        }
        
        architecture = {"services": {"Bedrock": {"enabled": True}}}
        
        result = self.tool._run(requirements, architecture)
        result_data = json.loads(result)
        
        kb_config = result_data["knowledge_base_configuration"]
        
        assert "knowledge_base_id" in kb_config
        assert "conversational" in kb_config["knowledge_base_id"]
        assert "data_source_configuration" in kb_config
        assert "storage_configuration" in kb_config
    
    def test_deployment_artifacts_generation(self):
        """Test deployment artifacts generation."""
        requirements = {
            "functional_requirements": ["process requests"],
            "agent_type_detected": "simple"
        }
        
        architecture = {"services": {"Bedrock": {"enabled": True}}}
        
        result = self.tool._run(requirements, architecture)
        result_data = json.loads(result)
        
        artifacts = result_data["deployment_artifacts"]
        
        assert "lambda_functions" in artifacts
        assert "iam_policies" in artifacts
        assert "deployment_script" in artifacts
        assert "environment_variables" in artifacts
        
        # Check Lambda functions
        lambda_functions = artifacts["lambda_functions"]
        assert len(lambda_functions) > 0
        
        for func in lambda_functions:
            assert "function_name" in func
            assert "code" in func
            assert "runtime" in func
            assert func["runtime"] == "python3.12"
    
    def test_agent_instruction_generation(self):
        """Test agent instruction generation."""
        # Test conversational agent
        conv_requirements = {
            "functional_requirements": ["chat with users", "answer questions"],
            "agent_type_detected": "conversational"
        }
        
        instruction = self.tool._generate_agent_instruction(conv_requirements)
        
        assert "conversational" in instruction.lower()
        assert "chat with users" in instruction or "answer questions" in instruction
        
        # Test analytical agent
        analytical_requirements = {
            "functional_requirements": ["analyze data", "generate reports"],
            "agent_type_detected": "analytical"
        }
        
        instruction = self.tool._generate_agent_instruction(analytical_requirements)
        
        assert "analytical" in instruction.lower() or "analysis" in instruction.lower()
    
    def test_with_knowledge_base_client(self):
        """Test tool with knowledge base client."""
        mock_kb_client = Mock(spec=BedrockKnowledgeBaseClient)
        mock_kb_client.search_knowledge_base.return_value = [
            Mock(title="Template 1", excerpt="Description 1", relevance_score=0.9, content="Content 1")
        ]
        
        tool = BedrockAgentConfigTool(knowledge_base_client=mock_kb_client)
        
        requirements = {
            "functional_requirements": ["process requests"],
            "agent_type_detected": "conversational"
        }
        
        architecture = {"services": {"Bedrock": {"enabled": True}}}
        
        result = tool._run(requirements, architecture)
        result_data = json.loads(result)
        
        assert "code_templates" in result_data
        assert len(result_data["code_templates"]) > 0


class TestActionGroupGeneratorTool:
    """Test cases for ActionGroupGeneratorTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = ActionGroupGeneratorTool()
    
    def test_basic_action_group_generation(self):
        """Test basic action group generation."""
        functional_requirements = [
            "store user data",
            "send email notifications",
            "analyze customer behavior"
        ]
        
        result = self.tool._run(functional_requirements)
        result_data = json.loads(result)
        
        assert "action_groups" in result_data
        assert "api_specifications" in result_data
        assert "lambda_implementations" in result_data
        assert "deployment_guide" in result_data
        
        action_groups = result_data["action_groups"]
        assert len(action_groups) > 0
        
        # Should categorize requirements appropriately
        categories = [ag["category"] for ag in action_groups]
        assert "data" in categories
        assert "communication" in categories
        assert "analysis" in categories
    
    def test_requirement_categorization(self):
        """Test requirement categorization."""
        requirements = [
            "store customer information",  # data
            "send email alerts",          # communication
            "analyze sales trends",       # analysis
            "automate workflows",         # automation
            "integrate with CRM API",     # integration
            "handle user requests"        # general
        ]
        
        categories = self.tool._categorize_requirements(requirements)
        
        assert len(categories["data"]) > 0
        assert len(categories["communication"]) > 0
        assert len(categories["analysis"]) > 0
        assert len(categories["automation"]) > 0
        assert len(categories["integration"]) > 0
        assert len(categories["general"]) > 0
    
    def test_api_specification_generation(self):
        """Test OpenAPI specification generation."""
        functional_requirements = ["store data", "retrieve information"]
        
        result = self.tool._run(functional_requirements)
        result_data = json.loads(result)
        
        api_specs = result_data["api_specifications"]
        assert len(api_specs) > 0
        
        for spec in api_specs:
            assert "action_group_name" in spec
            assert "openapi_spec" in spec
            
            openapi = spec["openapi_spec"]
            assert openapi["openapi"] == "3.0.0"
            assert "info" in openapi
            assert "paths" in openapi
            
            # Check that paths are generated
            assert len(openapi["paths"]) > 0
    
    def test_lambda_implementation_generation(self):
        """Test Lambda implementation generation."""
        functional_requirements = ["process user requests", "store data"]
        
        result = self.tool._run(functional_requirements)
        result_data = json.loads(result)
        
        implementations = result_data["lambda_implementations"]
        assert len(implementations) > 0
        
        for impl in implementations:
            assert "function_name" in impl
            assert "code" in impl
            assert "runtime" in impl
            assert "handler" in impl
            
            # Check code structure
            code = impl["code"]
            assert "lambda_handler" in code
            assert "def handle_" in code  # Should have handler functions
            assert "get_parameter_value" in code
    
    def test_integration_generation(self):
        """Test integration code generation."""
        functional_requirements = ["integrate with external API"]
        
        integration_specs = {
            "external_service": {
                "type": "api",
                "configuration": {
                    "base_url": "https://api.example.com",
                    "auth_type": "bearer"
                }
            },
            "database_service": {
                "type": "database",
                "configuration": {
                    "table_name": "user_data"
                }
            }
        }
        
        result = self.tool._run(functional_requirements, integration_specs)
        result_data = json.loads(result)
        
        integrations = result_data["integrations"]
        assert len(integrations) == 2
        
        # Check API integration
        api_integration = next(i for i in integrations if i["service"] == "external_service")
        assert api_integration["type"] == "api"
        assert "class External_serviceIntegration" in api_integration["implementation"]
        
        # Check database integration
        db_integration = next(i for i in integrations if i["service"] == "database_service")
        assert db_integration["type"] == "database"
        assert "class Database_serviceIntegration" in db_integration["implementation"]
    
    def test_deployment_guide_generation(self):
        """Test deployment guide generation."""
        functional_requirements = ["process requests", "store data"]
        
        result = self.tool._run(functional_requirements)
        result_data = json.loads(result)
        
        deployment_guide = result_data["deployment_guide"]
        
        assert isinstance(deployment_guide, list)
        assert len(deployment_guide) > 0
        
        guide_text = "\n".join(deployment_guide)
        assert "Prerequisites" in guide_text
        assert "Deployment Steps" in guide_text
        assert "aws lambda create-function" in guide_text
        assert "aws bedrock-agent" in guide_text


class TestDeploymentTemplateGeneratorTool:
    """Test cases for DeploymentTemplateGeneratorTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = DeploymentTemplateGeneratorTool()
    
    def test_basic_template_generation(self):
        """Test basic CloudFormation template generation."""
        agent_config = {
            "agent_name": "TestAgent",
            "foundation_model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "action_groups": [
                {"action_group_name": "CoreActions"},
                {"action_group_name": "DataActions"}
            ]
        }
        
        result = self.tool._run(agent_config)
        result_data = json.loads(result)
        
        assert "cloudformation_template" in result_data
        assert "parameter_files" in result_data
        assert "deployment_scripts" in result_data
        assert "deployment_instructions" in result_data
        
        # Check CloudFormation template structure
        template = result_data["cloudformation_template"]
        assert template["AWSTemplateFormatVersion"] == "2010-09-09"
        assert "Parameters" in template
        assert "Resources" in template
        assert "Outputs" in template
    
    def test_template_parameters(self):
        """Test CloudFormation template parameters."""
        agent_config = {
            "agent_name": "TestAgent",
            "foundation_model": "anthropic.claude-3-haiku-20240307-v1:0"
        }
        
        result = self.tool._run(agent_config)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        parameters = template["Parameters"]
        
        assert "AgentName" in parameters
        assert "FoundationModel" in parameters
        assert "Environment" in parameters
        
        # Check default values
        assert parameters["AgentName"]["Default"] == "TestAgent"
        assert parameters["FoundationModel"]["Default"] == "anthropic.claude-3-haiku-20240307-v1:0"
    
    def test_template_resources(self):
        """Test CloudFormation template resources."""
        agent_config = {
            "agent_name": "TestAgent",
            "action_groups": [
                {"action_group_name": "CoreActions"},
                {"action_group_name": "DataActions"}
            ]
        }
        
        result = self.tool._run(agent_config)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        resources = template["Resources"]
        
        # Check IAM roles
        assert "BedrockAgentRole" in resources
        assert "LambdaExecutionRole" in resources
        
        # Check Lambda functions for action groups
        assert "CoreActionsFunction" in resources
        assert "DataActionsFunction" in resources
        
        # Verify resource types
        assert resources["BedrockAgentRole"]["Type"] == "AWS::IAM::Role"
        assert resources["LambdaExecutionRole"]["Type"] == "AWS::IAM::Role"
        assert resources["CoreActionsFunction"]["Type"] == "AWS::Lambda::Function"
    
    def test_template_outputs(self):
        """Test CloudFormation template outputs."""
        agent_config = {"agent_name": "TestAgent"}
        
        result = self.tool._run(agent_config)
        result_data = json.loads(result)
        
        template = result_data["cloudformation_template"]
        outputs = template["Outputs"]
        
        assert "BedrockAgentRoleArn" in outputs
        assert "LambdaExecutionRoleArn" in outputs
        
        # Check output structure
        for output_name, output_config in outputs.items():
            assert "Description" in output_config
            assert "Value" in output_config
            assert "Export" in output_config
    
    def test_parameter_files_generation(self):
        """Test parameter files generation."""
        agent_config = {"agent_name": "TestAgent"}
        
        result = self.tool._run(agent_config)
        result_data = json.loads(result)
        
        parameter_files = result_data["parameter_files"]
        
        assert "dev-parameters.json" in parameter_files
        assert "prod-parameters.json" in parameter_files
        
        # Check dev parameters
        dev_params = parameter_files["dev-parameters.json"]
        assert any(p["ParameterKey"] == "AgentName" and "dev" in p["ParameterValue"] for p in dev_params)
        assert any(p["ParameterKey"] == "Environment" and p["ParameterValue"] == "dev" for p in dev_params)
        
        # Check prod parameters
        prod_params = parameter_files["prod-parameters.json"]
        assert any(p["ParameterKey"] == "AgentName" and p["ParameterValue"] == "TestAgent" for p in prod_params)
        assert any(p["ParameterKey"] == "Environment" and p["ParameterValue"] == "prod" for p in prod_params)
    
    def test_deployment_scripts_generation(self):
        """Test deployment scripts generation."""
        agent_config = {"agent_name": "TestAgent"}
        
        result = self.tool._run(agent_config)
        result_data = json.loads(result)
        
        deployment_scripts = result_data["deployment_scripts"]
        
        assert "deploy.sh" in deployment_scripts
        assert "cleanup.sh" in deployment_scripts
        
        # Check deploy script
        deploy_script = deployment_scripts["deploy.sh"]
        assert "#!/bin/bash" in deploy_script
        assert "aws cloudformation deploy" in deploy_script
        assert "TestAgent" in deploy_script
        
        # Check cleanup script
        cleanup_script = deployment_scripts["cleanup.sh"]
        assert "#!/bin/bash" in cleanup_script
        assert "aws cloudformation delete-stack" in cleanup_script
    
    def test_deployment_instructions(self):
        """Test deployment instructions generation."""
        agent_config = {"agent_name": "TestAgent"}
        
        result = self.tool._run(agent_config)
        result_data = json.loads(result)
        
        instructions = result_data["deployment_instructions"]
        
        assert isinstance(instructions, list)
        assert len(instructions) > 0
        
        instructions_text = "\n".join(instructions)
        assert "Prerequisites" in instructions_text
        assert "Deployment Steps" in instructions_text
        assert "Post-Deployment" in instructions_text
        assert "template.yaml" in instructions_text


if __name__ == "__main__":
    pytest.main([__file__])