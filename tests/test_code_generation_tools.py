"""
Tests for Code Generation Tools

Comprehensive tests for all code generation tools to ensure they work correctly
and meet the requirements specified in task 5.3.
"""

import json
import pytest
from unittest.mock import Mock, patch
from autoninja.tools.code_generation import (
    BedrockAgentConfigTool,
    ActionGroupGeneratorTool,
    StepFunctionsGeneratorTool,
    DynamoDBIntegrationTool,
    APIGatewayConfigTool,
    DeploymentTemplateGeneratorTool
)


class TestBedrockAgentConfigTool:
    """Test cases for BedrockAgentConfigTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = BedrockAgentConfigTool()
        self.sample_requirements = {
            "agent_type_detected": "conversational",
            "functional_requirements": [
                "Handle customer inquiries",
                "Process data requests",
                "Integrate with external APIs"
            ]
        }
        self.sample_architecture = {
            "services": ["lambda", "dynamodb", "api-gateway"],
            "complexity": "medium"
        }
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        assert self.tool.name == "bedrock_agent_config_generator"
        assert "Bedrock Agent configurations" in self.tool.description
        assert self.tool.kb_client is None
    
    def test_generate_agent_config(self):
        """Test agent configuration generation."""
        result = self.tool._run(self.sample_requirements, self.sample_architecture)
        
        # Parse the JSON result
        config = json.loads(result)
        
        # Verify structure
        assert "agent_configuration" in config
        assert "action_groups" in config
        assert "knowledge_base_configuration" in config
        assert "deployment_artifacts" in config
        
        # Verify agent configuration details
        agent_config = config["agent_configuration"]
        assert "agent_name" in agent_config
        assert "AutoNinja-Conversational-Agent" in agent_config["agent_name"]
        assert "foundation_model" in agent_config
        assert "instruction" in agent_config
    
    def test_action_groups_generation(self):
        """Test action groups are generated correctly."""
        result = self.tool._run(self.sample_requirements, self.sample_architecture)
        config = json.loads(result)
        
        action_groups = config["action_groups"]
        assert len(action_groups) > 0
        
        # Check for core action group
        core_group = next((ag for ag in action_groups if ag["action_group_name"] == "CoreActions"), None)
        assert core_group is not None
        assert "api_schema" in core_group
        assert "action_group_executor" in core_group
    
    def test_foundation_model_selection(self):
        """Test foundation model selection based on complexity."""
        # Test high complexity
        high_complexity_reqs = [
            "Complex machine learning analysis",
            "Advanced AI processing",
            "Intelligent data analysis with multiple algorithms"
        ]
        
        complexity = self.tool._assess_complexity(high_complexity_reqs)
        model = self.tool._select_foundation_model(complexity)
        
        assert complexity == "high"
        assert "claude-3-opus" in model
    
    def test_knowledge_base_config(self):
        """Test knowledge base configuration generation."""
        kb_config = self.tool._generate_knowledge_base_config(self.sample_requirements)
        
        assert "knowledge_base_id" in kb_config
        assert "conversational" in kb_config["knowledge_base_id"]
        assert "data_source_configuration" in kb_config
        assert "storage_configuration" in kb_config


class TestActionGroupGeneratorTool:
    """Test cases for ActionGroupGeneratorTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = ActionGroupGeneratorTool()
        self.sample_requirements = [
            "Store user data securely",
            "Send email notifications",
            "Analyze customer behavior",
            "Integrate with external CRM system"
        ]
    
    def test_requirement_categorization(self):
        """Test requirement categorization."""
        categories = self.tool._categorize_requirements(self.sample_requirements)
        
        assert "data" in categories
        assert "communication" in categories
        assert "analysis" in categories
        assert "integration" in categories
        
        # Check specific categorizations
        assert any("Store user data" in req for req in categories["data"])
        assert any("email notifications" in req for req in categories["communication"])
    
    def test_action_group_generation(self):
        """Test action group generation."""
        result = self.tool._run(self.sample_requirements)
        config = json.loads(result)
        
        assert "action_groups" in config
        assert "api_specifications" in config
        assert "lambda_implementations" in config
        
        action_groups = config["action_groups"]
        assert len(action_groups) > 0
        
        # Verify action group structure
        for group in action_groups:
            assert "name" in group
            assert "description" in group
            assert "actions" in group
    
    def test_api_specification_generation(self):
        """Test OpenAPI specification generation."""
        action_groups = self.tool._analyze_and_generate_action_groups(self.sample_requirements)
        api_specs = self.tool._generate_api_specifications(action_groups)
        
        assert len(api_specs) > 0
        
        for spec in api_specs:
            assert "openapi_spec" in spec
            openapi = spec["openapi_spec"]
            assert openapi["openapi"] == "3.0.0"
            assert "paths" in openapi
            assert "info" in openapi
    
    def test_lambda_implementation_generation(self):
        """Test Lambda implementation generation."""
        action_groups = self.tool._analyze_and_generate_action_groups(self.sample_requirements)
        implementations = self.tool._generate_lambda_implementations(action_groups)
        
        assert len(implementations) > 0
        
        for impl in implementations:
            assert "function_name" in impl
            assert "code" in impl
            assert "runtime" in impl
            assert impl["runtime"] == "python3.12"
            
            # Verify code structure
            code = impl["code"]
            assert "def lambda_handler" in code
            assert "import json" in code
            assert "import boto3" in code


class TestStepFunctionsGeneratorTool:
    """Test cases for StepFunctionsGeneratorTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = StepFunctionsGeneratorTool()
        self.sample_requirements = [
            "Process requests sequentially",
            "Handle parallel data processing",
            "Implement retry logic for failures"
        ]
        self.sample_agent_config = {
            "agent_name": "TestAgent",
            "foundation_model": "claude-3-sonnet"
        }
    
    def test_workflow_type_determination(self):
        """Test workflow type determination."""
        parallel_reqs = ["Process data in parallel", "Run concurrent tasks"]
        choice_reqs = ["Make decisions based on conditions", "Branch logic"]
        retry_reqs = ["Handle failures with retry", "Error recovery"]
        
        assert self.tool._determine_workflow_type(parallel_reqs) == "parallel"
        assert self.tool._determine_workflow_type(choice_reqs) == "choice"
        assert self.tool._determine_workflow_type(retry_reqs) == "retry"
    
    def test_sequential_workflow_generation(self):
        """Test sequential workflow generation."""
        workflow = self.tool._generate_sequential_workflow(self.sample_requirements)
        
        assert "Comment" in workflow
        assert "StartAt" in workflow
        assert "States" in workflow
        
        # Verify sequential structure
        states = workflow["States"]
        assert "ProcessRequirements" in states
        assert "GenerateCode" in states
        assert "ValidateQuality" in states
    
    def test_parallel_workflow_generation(self):
        """Test parallel workflow generation."""
        workflow = self.tool._generate_parallel_workflow(self.sample_requirements)
        
        states = workflow["States"]
        assert "ParallelProcessing" in states
        
        parallel_state = states["ParallelProcessing"]
        assert parallel_state["Type"] == "Parallel"
        assert "Branches" in parallel_state
        assert len(parallel_state["Branches"]) >= 2
    
    def test_integration_code_generation(self):
        """Test Step Functions integration code generation."""
        state_machine = self.tool._generate_sequential_workflow(self.sample_requirements)
        integration_code = self.tool._generate_integration_code(state_machine, self.sample_agent_config)
        
        assert "class StepFunctionsIntegration" in integration_code
        assert "def start_execution" in integration_code
        assert "def get_execution_status" in integration_code
        assert "boto3.client(\"stepfunctions\"" in integration_code


class TestDynamoDBIntegrationTool:
    """Test cases for DynamoDBIntegrationTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = DynamoDBIntegrationTool()
        self.sample_requirements = [
            "Store session state data",
            "Manage user profiles",
            "Store generated data artifacts"
        ]
        self.sample_agent_config = {
            "agent_name": "TestAgent"
        }
    
    def test_table_schema_generation(self):
        """Test DynamoDB table schema generation."""
        schemas = self.tool._generate_table_schemas(self.sample_requirements)
        
        assert len(schemas) > 0
        
        # Check for session table
        session_table = next((s for s in schemas if "session" in s["table_name"]), None)
        assert session_table is not None
        assert "partition_key" in session_table
        assert "attributes" in session_table
    
    def test_operations_code_generation(self):
        """Test DynamoDB operations code generation."""
        schemas = self.tool._generate_table_schemas(self.sample_requirements)
        operations_code = self.tool._generate_operations_code(schemas)
        
        assert "class DynamoDBOperations" in operations_code
        assert "def create_" in operations_code
        assert "def get_" in operations_code
        assert "def update_" in operations_code
        assert "def delete_" in operations_code
        assert "import boto3" in operations_code
    
    def test_cloudformation_template_generation(self):
        """Test CloudFormation template generation."""
        schemas = self.tool._generate_table_schemas(self.sample_requirements)
        template = self.tool._generate_cloudformation_template(schemas)
        
        assert "AWSTemplateFormatVersion" in template
        assert "Resources" in template
        assert "Outputs" in template
        
        # Check for DynamoDB table resources
        resources = template["Resources"]
        table_resources = [r for r in resources.values() if r["Type"] == "AWS::DynamoDB::Table"]
        assert len(table_resources) > 0


class TestAPIGatewayConfigTool:
    """Test cases for APIGatewayConfigTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = APIGatewayConfigTool()
        self.sample_requirements = [
            "Provide REST API access",
            "Handle authentication",
            "Support session management"
        ]
        self.sample_agent_config = {
            "agent_name": "TestAgent"
        }
    
    def test_api_specification_generation(self):
        """Test OpenAPI specification generation."""
        api_spec = self.tool._generate_api_specification(self.sample_requirements, self.sample_agent_config)
        
        assert api_spec["openapi"] == "3.0.0"
        assert "info" in api_spec
        assert "paths" in api_spec
        assert "components" in api_spec
        
        # Check for required paths
        paths = api_spec["paths"]
        assert "/chat" in paths
        assert "/sessions" in paths
        assert "/health" in paths
    
    def test_cloudformation_template_generation(self):
        """Test API Gateway CloudFormation template generation."""
        api_spec = self.tool._generate_api_specification(self.sample_requirements, self.sample_agent_config)
        template = self.tool._generate_api_cloudformation_template(api_spec)
        
        assert "Resources" in template
        resources = template["Resources"]
        
        assert "ApiGatewayRestApi" in resources
        assert "ApiGatewayDeployment" in resources
        assert "ApiGatewayUsagePlan" in resources
        assert "ApiGatewayApiKey" in resources
    
    def test_integration_code_generation(self):
        """Test API Gateway integration code generation."""
        api_spec = self.tool._generate_api_specification(self.sample_requirements, self.sample_agent_config)
        integration_code = self.tool._generate_api_integration_code(api_spec)
        
        assert "class APIGatewayIntegration" in integration_code
        assert "def lambda_handler" in integration_code
        assert "def handle_chat_request" in integration_code
        assert "bedrock-agent-runtime" in integration_code


class TestDeploymentTemplateGeneratorTool:
    """Test cases for DeploymentTemplateGeneratorTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = DeploymentTemplateGeneratorTool()
        self.sample_agent_config = {
            "agent_name": "TestAgent",
            "foundation_model": "claude-3-sonnet",
            "action_groups": [
                {"action_group_name": "CoreActions"},
                {"action_group_name": "DataActions"}
            ]
        }
    
    def test_complete_template_generation(self):
        """Test complete CloudFormation template generation."""
        template = self.tool._generate_complete_template(self.sample_agent_config, None)
        
        assert "AWSTemplateFormatVersion" in template
        assert "Resources" in template
        assert "Parameters" in template
        assert "Outputs" in template
        
        # Check for required resources
        resources = template["Resources"]
        assert "BedrockAgentRole" in resources
        assert "LambdaExecutionRole" in resources
    
    def test_parameter_files_generation(self):
        """Test parameter files generation."""
        parameter_files = self.tool._generate_parameter_files(self.sample_agent_config)
        
        assert "dev-parameters.json" in parameter_files
        assert "prod-parameters.json" in parameter_files
        
        dev_params = parameter_files["dev-parameters.json"]
        assert any(p["ParameterKey"] == "AgentName" for p in dev_params)
        assert any(p["ParameterKey"] == "Environment" for p in dev_params)
    
    def test_deployment_scripts_generation(self):
        """Test deployment scripts generation."""
        scripts = self.tool._generate_deployment_scripts(self.sample_agent_config)
        
        assert "deploy.sh" in scripts
        assert "cleanup.sh" in scripts
        
        deploy_script = scripts["deploy.sh"]
        assert "aws cloudformation deploy" in deploy_script
        assert "#!/bin/bash" in deploy_script


class TestIntegrationScenarios:
    """Integration tests for complete workflows."""
    
    def test_complete_agent_generation_workflow(self):
        """Test complete agent generation workflow."""
        # Initialize tools
        bedrock_tool = BedrockAgentConfigTool()
        action_tool = ActionGroupGeneratorTool()
        api_tool = APIGatewayConfigTool()
        deployment_tool = DeploymentTemplateGeneratorTool()
        
        # Sample inputs
        requirements = {
            "agent_type_detected": "conversational",
            "functional_requirements": [
                "Handle customer inquiries",
                "Store conversation history",
                "Send notifications"
            ]
        }
        architecture = {
            "services": ["lambda", "dynamodb", "api-gateway"],
            "complexity": "medium"
        }
        
        # Generate configurations
        bedrock_result = bedrock_tool._run(requirements, architecture)
        bedrock_config = json.loads(bedrock_result)
        
        action_result = action_tool._run(requirements["functional_requirements"])
        action_config = json.loads(action_result)
        
        api_result = api_tool._run(["REST API access"], bedrock_config["agent_configuration"])
        api_config = json.loads(api_result)
        
        deployment_result = deployment_tool._run(bedrock_config["agent_configuration"])
        deployment_config = json.loads(deployment_result)
        
        # Verify all components are generated
        assert "agent_configuration" in bedrock_config
        assert "action_groups" in action_config
        assert "api_specification" in api_config
        assert "cloudformation_template" in deployment_config
        
        print("✅ Complete agent generation workflow test passed!")


def run_tests():
    """Run all tests and report results."""
    test_classes = [
        TestBedrockAgentConfigTool,
        TestActionGroupGeneratorTool,
        TestStepFunctionsGeneratorTool,
        TestDynamoDBIntegrationTool,
        TestAPIGatewayConfigTool,
        TestDeploymentTemplateGeneratorTool,
        TestIntegrationScenarios
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n🧪 Running {test_class.__name__}...")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                # Create instance and run setup
                instance = test_class()
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                
                # Run the test
                getattr(instance, test_method)()
                passed_tests += 1
                print(f"  ✅ {test_method}")
                
            except Exception as e:
                failed_tests.append(f"{test_class.__name__}.{test_method}: {str(e)}")
                print(f"  ❌ {test_method}: {str(e)}")
    
    # Print summary
    print(f"\n📊 Test Summary:")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for failure in failed_tests:
            print(f"  - {failure}")
    else:
        print(f"\n🎉 All tests passed!")
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)