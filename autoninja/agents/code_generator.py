"""
Code Generator Agent

LangChain agent implementation for production-ready code generation with AWS SDK integration.
This agent transforms architecture designs into complete, functional implementations including
Bedrock Agent configurations, action group implementations, and CloudFormation templates.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from autoninja.core.logging_config import get_session_logger, log_bedrock_request, log_bedrock_response
from autoninja.core.pipeline_logging import get_pipeline_logger, PipelineStage

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from autoninja.core.bedrock_client import (
    BedrockClientManager, 
    BedrockModelId, 
    TaskComplexity,
    get_bedrock_client_manager
)
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient, KnowledgeBaseType
from autoninja.tools.code_generation import (
    BedrockAgentConfigTool
)
from autoninja.models.state import (
    AgentOutput,
    SolutionArchitectOutput
)
from autoninja.utils.retry import exponential_backoff_retry

logger = logging.getLogger(__name__)


class CodeGeneratorAgent:
    """
    Code Generator Agent for production-ready code generation.
    
    This agent specializes in:
    - Bedrock Agent configuration and action group generation
    - Multi-language code creation with AWS SDK integration
    - CloudFormation template creation and validation
    - Production-ready code with proper error handling
    - Complete source code packages with documentation
    """
    
    def __init__(
        self,
        bedrock_client_manager: Optional[BedrockClientManager] = None,
        knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None
    ):
        """
        Initialize the Code Generator Agent.
        
        Args:
            bedrock_client_manager: Bedrock client manager for model access
            knowledge_base_client: Knowledge base client for pattern retrieval
        """
        self.agent_name = "code_generator"
        self.bedrock_client_manager = bedrock_client_manager or get_bedrock_client_manager()
        self.knowledge_base_client = knowledge_base_client
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Create the agent
        self.agent_executor = self._create_agent()
        
        logger.info("Code Generator Agent initialized successfully")
    
    def _initialize_tools(self) -> List:
        """Initialize the tools available to the agent."""
        tools = [
            BedrockAgentConfigTool(knowledge_base_client=self.knowledge_base_client)
        ]
        
        logger.info(f"Initialized {len(tools)} tools for Code Generator Agent")
        return tools
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools and prompt."""
        
        # System prompt for the Code Generator Agent
        system_prompt = """You are a Code Generator specializing in Bedrock Agent implementations. 
Transform architecture designs into production-ready agent configurations, action group implementations, 
knowledge base integrations, and CloudFormation templates for real AI agent deployment.

Your capabilities include:
- Bedrock Agent configuration generation with proper settings
- Action group implementation with OpenAPI schemas
- Lambda function code generation for action group handlers
- CloudFormation template creation for infrastructure deployment
- AWS SDK integration code with error handling
- Production-ready code with comprehensive documentation
- Environment configuration and deployment scripts

When generating code:
1. Create complete Bedrock Agent configurations with appropriate foundation models
2. Generate action groups with proper OpenAPI schemas and Lambda handlers
3. Implement robust error handling and logging
4. Include comprehensive documentation and deployment instructions
5. Ensure security best practices and IAM configurations
6. Generate CloudFormation templates for infrastructure deployment
7. Provide complete source code packages ready for deployment

Always provide structured, production-ready output that can be immediately deployed.
Focus on code quality, security, and operational excellence. Use available tools for 
configuration generation and template creation."""

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Use Claude 3.5 Sonnet for code generation (high complexity task)
        model_id = BedrockModelId.CLAUDE_SONNET_4_5
        llm = self.bedrock_client_manager.get_client(model_id)
        
        # Create the tool-calling agent
        agent = create_tool_calling_agent(llm, self.tools, prompt)
        
        # Create the agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15,
            max_execution_time=900  # 15 minutes timeout for complex code generation
        )
        
        return agent_executor
    
    @exponential_backoff_retry(max_retries=3)
    def generate_code(
        self,
        architecture_output: AgentOutput,
        session_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        Generate production-ready code based on architecture design.
        
        Args:
            architecture_output: Output from Solution Architect Agent
            session_id: Session identifier for tracking
            additional_context: Optional additional context information
            
        Returns:
            AgentOutput: Structured agent output with generated code
        """
        execution_id = f"{session_id}_{self.agent_name}_{int(datetime.now(UTC).timestamp())}"
        start_time = datetime.now(UTC)
        
        logger.info(f"Starting code generation for session {session_id}")
        
        # Get pipeline logger for structured logging
        pipeline_logger = get_pipeline_logger(session_id)
        
        try:
            # Prepare input for the agent
            agent_input = self._prepare_agent_input(architecture_output, additional_context)
            
            # Log agent input for pipeline debugging
            pipeline_logger.log_agent_input(
                stage=PipelineStage.CODE_GENERATION,
                agent_name=self.agent_name,
                execution_id=execution_id,
                input_data={
                    "architecture_output": architecture_output.model_dump(),
                    "additional_context": additional_context or {},
                    "prepared_input": agent_input
                },
                metadata={
                    "agent_type": "code_generator",
                    "model_complexity": "high",
                    "previous_agent": "solution_architect"
                }
            )
            
            # Log raw request
            logger.info(f"Raw request for {execution_id}: {json.dumps(agent_input, indent=2)}")
            
            # Make direct Bedrock inference call
            result = self._make_bedrock_inference(agent_input, execution_id, pipeline_logger)
            
            # Log raw response
            logger.info(f"Raw response for {execution_id}: {json.dumps(result, indent=2, default=str)}")
            
            # Process and structure the output
            structured_output = self._process_agent_output(result)
            
            # Verify response structure compatibility with next agent
            self._verify_response_compatibility(structured_output)
            
            # Calculate execution metadata
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()
            
            # Create the agent output
            agent_output = AgentOutput(
                agent_name=self.agent_name,
                execution_id=execution_id,
                input_data={
                    "architecture_output": architecture_output.model_dump(),
                    "session_id": session_id,
                    "additional_context": additional_context or {}
                },
                output=AgentOutput.Output(
                    result=structured_output,
                    confidence_score=self._calculate_confidence_score(structured_output),
                    reasoning=str(result.get("intermediate_steps", "Code generation completed successfully")),
                    recommendations=self._generate_recommendations(structured_output)
                ),
                execution_metadata=AgentOutput.ExecutionMetadata(
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration,
                    model_invocations=1,
                    tokens_used=0  # Would need to be tracked from Bedrock response
                ),
                trace_data=AgentOutput.TraceData(
                    trace_id=execution_id,
                    steps=[{
                        "step": "code_generation",
                        "timestamp": start_time.isoformat(),
                        "duration": duration,
                        "status": "completed"
                    }]
                )
            )
            
            # Log agent output for pipeline handoff
            pipeline_logger.log_agent_output(
                stage=PipelineStage.CODE_GENERATION,
                agent_name=self.agent_name,
                execution_id=execution_id,
                output_data=agent_output,
                metadata={
                    "confidence_score": agent_output.output.confidence_score,
                    "processing_time": duration,
                    "recommendations_count": len(agent_output.output.recommendations),
                    "next_agent": "quality_validator"
                }
            )
            
            logger.info(f"Code generation completed successfully for session {session_id}")
            return agent_output
            
        except Exception as e:
            logger.error(f"Error in code generation for session {session_id}: {str(e)}")
            
            # Log pipeline error
            pipeline_logger.log_pipeline_error(
                stage=PipelineStage.CODE_GENERATION,
                agent_name=self.agent_name,
                execution_id=execution_id,
                error=e,
                context={
                    "architecture_output": architecture_output.model_dump(),
                    "additional_context": additional_context
                }
            )
            
            # Create error output
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()
            
            return AgentOutput(
                agent_name=self.agent_name,
                execution_id=execution_id,
                input_data={
                    "architecture_output": architecture_output.model_dump(),
                    "session_id": session_id,
                    "additional_context": additional_context or {}
                },
                output=AgentOutput.Output(
                    result={"error": str(e)},
                    confidence_score=0.0,
                    reasoning=f"Code generation failed: {str(e)}",
                    recommendations=["Review architecture design and retry code generation"]
                ),
                execution_metadata=AgentOutput.ExecutionMetadata(
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration,
                    model_invocations=0,
                    tokens_used=0
                ),
                trace_data=AgentOutput.TraceData(
                    trace_id=execution_id,
                    steps=[{
                        "step": "code_generation",
                        "timestamp": start_time.isoformat(),
                        "duration": duration,
                        "status": "failed",
                        "error": str(e)
                    }]
                )
            )
    
    def _prepare_agent_input(
        self, 
        architecture_output: AgentOutput, 
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare input for the agent execution."""
        
        # Extract architecture from the previous agent's output
        architecture_result = architecture_output.output.result
        
        context_info = ""
        if additional_context:
            context_info = f"\n\nAdditional Context:\n{json.dumps(additional_context, indent=2)}"
        
        agent_input = f"""
Generate production-ready code for this AI agent based on the architecture design:

Architecture Design: {json.dumps(architecture_result, indent=2)}
{context_info}

Tasks:
1. Create complete Bedrock Agent configuration with appropriate foundation model
2. Generate action groups with OpenAPI schemas and Lambda function handlers
3. Implement CloudFormation templates for infrastructure deployment
4. Generate Lambda function code with proper error handling and logging
5. Create IAM policies and roles for secure operation
6. Generate deployment scripts and documentation
7. Ensure all code follows AWS best practices and security guidelines

Requirements:
- Production-ready code with comprehensive error handling
- Complete documentation and deployment instructions
- Security best practices and proper IAM configurations
- CloudFormation templates for infrastructure as code
- Lambda functions with proper logging and monitoring
- OpenAPI schemas for action group definitions

Output must be compatible with Quality Validator Agent for comprehensive validation.
Provide complete, deployable code packages ready for production use.
"""
        
        return agent_input
    
    def _process_agent_output(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Process and structure the raw agent output."""
        
        # Extract the main output from the agent execution
        output_text = raw_output.get("output", "")
        
        # Try to parse structured output if it's JSON
        structured_data = {}
        try:
            # Extract JSON from markdown code blocks if present
            json_text = output_text
            if "```json" in output_text:
                # Extract JSON from markdown code block
                start = output_text.find("```json") + 7
                end = output_text.find("```", start)
                if end != -1:
                    json_text = output_text[start:end].strip()
            elif output_text.strip().startswith("{"):
                json_text = output_text.strip()
            
            if json_text.strip().startswith("{"):
                structured_data = json.loads(json_text)
            else:
                # If not JSON, create a structured format
                structured_data = {
                    "code_summary": output_text,
                    "generation_method": "text_analysis"
                }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            structured_data = {
                "code_summary": output_text,
                "generation_method": "text_analysis"
            }
        
        # Ensure required fields are present for Code Generator output
        result = {
            "bedrock_agent_config": structured_data.get("bedrock_agent_config", {}),
            "action_groups": structured_data.get("action_groups", []),
            "lambda_functions": structured_data.get("lambda_functions", []),
            "cloudformation_templates": structured_data.get("cloudformation_templates", {}),
            "iam_policies": structured_data.get("iam_policies", []),
            "deployment_scripts": structured_data.get("deployment_scripts", {}),
            "source_code_packages": structured_data.get("source_code_packages", {}),
            "documentation": structured_data.get("documentation", {}),
            "code_summary": structured_data.get("code_summary", output_text),
            "generation_method": structured_data.get("generation_method", "structured_analysis"),
            "tool_outputs": self._extract_tool_outputs(raw_output),
            "environment_config": structured_data.get("environment_config", {}),
            "testing_framework": structured_data.get("testing_framework", {}),
            "monitoring_setup": structured_data.get("monitoring_setup", {})
        }
        
        return result
    
    def _extract_tool_outputs(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Extract outputs from individual tools used during execution."""
        tool_outputs = {}
        
        # Extract intermediate steps if available
        intermediate_steps = raw_output.get("intermediate_steps", [])
        
        for step in intermediate_steps:
            if isinstance(step, tuple) and len(step) >= 2:
                action, observation = step[0], step[1]
                if hasattr(action, 'tool') and hasattr(action, 'tool_input'):
                    tool_name = action.tool
                    tool_outputs[tool_name] = {
                        "input": action.tool_input,
                        "output": observation
                    }
        
        return tool_outputs
    
    def _calculate_confidence_score(self, structured_output: Dict[str, Any]) -> float:
        """Calculate confidence score based on the code generation completeness."""
        
        score = 0.0
        max_score = 100.0
        
        # Check for presence of key components
        if structured_output.get("bedrock_agent_config"):
            score += 25.0
        
        if structured_output.get("action_groups"):
            score += 20.0
        
        if structured_output.get("lambda_functions"):
            score += 20.0
        
        if structured_output.get("cloudformation_templates"):
            score += 15.0
        
        if structured_output.get("iam_policies"):
            score += 10.0
        
        if structured_output.get("deployment_scripts"):
            score += 10.0
        
        return min(score / max_score, 1.0)
    
    def _make_bedrock_inference(self, agent_input: str, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Make direct inference call to Bedrock model with full request/response logging."""
        
        try:
            # Use Claude 3.5 Sonnet for code generation
            model_id = BedrockModelId.CLAUDE_SONNET_4_5
            
            # Prepare the messages for the model
            messages = [
                SystemMessage(content="""You are a Code Generator specializing in Bedrock Agent implementations.

Provide a comprehensive JSON response with complete code generation:
{
    "bedrock_agent_config": {
        "agent_name": "AutoNinja-Generated-Agent",
        "description": "AI agent generated by AutoNinja",
        "foundation_model": "anthropic.claude-3-sonnet-20240229-v1:0",
        "instruction": "detailed agent instruction",
        "action_groups": ["list of action group names"],
        "knowledge_bases": ["list of knowledge base IDs"]
    },
    "action_groups": [
        {
            "name": "CoreActions",
            "description": "Core functionality",
            "api_schema": {"openapi": "3.0.0", "paths": {}},
            "lambda_function": "function_name"
        }
    ],
    "lambda_functions": [
        {
            "function_name": "agent-core-handler",
            "runtime": "python3.12",
            "handler": "index.lambda_handler",
            "code": "complete Python code",
            "environment_variables": {"LOG_LEVEL": "INFO"}
        }
    ],
    "cloudformation_templates": {
        "main_template": {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {"BedrockAgent": {}, "LambdaFunction": {}}
        }
    },
    "iam_policies": [
        {
            "policy_name": "BedrockAgentExecutionPolicy",
            "policy_document": {"Version": "2012-10-17", "Statement": []}
        }
    ],
    "deployment_scripts": {
        "deploy.sh": "#!/bin/bash deployment script",
        "setup.py": "Python setup script"
    },
    "documentation": {
        "README.md": "Complete documentation",
        "API.md": "API documentation"
    }
}

Generate complete, production-ready code with proper error handling, logging, and security."""),
                HumanMessage(content=agent_input)
            ]
            
            # Log the raw request being sent to Bedrock
            raw_request = {
                "model_id": model_id.value,
                "messages": [{"role": msg.type, "content": msg.content} for msg in messages],
                "execution_id": execution_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
            logger.info(f"Raw Bedrock request for {execution_id}: {json.dumps(raw_request, indent=2)}")
            log_bedrock_request(execution_id, raw_request)
            
            # Log inference request for pipeline debugging
            pipeline_logger.log_inference_request(
                execution_id=execution_id,
                model_id=model_id.value,
                request_data=raw_request,
                agent_name=self.agent_name,
                stage=PipelineStage.CODE_GENERATION
            )
            
            # Make the inference call using the Bedrock client manager
            start_inference = datetime.now(UTC)
            response = self.bedrock_client_manager.invoke_with_retry(
                model_id=model_id,
                messages=messages
            )
            end_inference = datetime.now(UTC)
            inference_time = (end_inference - start_inference).total_seconds()
            
            # Log the raw response from Bedrock
            raw_response = {
                "model_id": model_id.value,
                "response_content": response.content if hasattr(response, 'content') else str(response),
                "execution_id": execution_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
            logger.info(f"Raw Bedrock response for {execution_id}: {json.dumps(raw_response, indent=2)}")
            log_bedrock_response(execution_id, raw_response)
            
            # Log inference response for pipeline debugging
            pipeline_logger.log_inference_response(
                execution_id=execution_id,
                model_id=model_id.value,
                response_data=raw_response,
                agent_name=self.agent_name,
                stage=PipelineStage.CODE_GENERATION,
                processing_time=inference_time
            )
            
            # Extract the content from the response
            if hasattr(response, 'content'):
                output_content = response.content
            else:
                output_content = str(response)
            
            # Use tools to enhance the analysis
            enhanced_output = self._enhance_with_tools(output_content, agent_input)
            
            return {
                "output": enhanced_output,
                "intermediate_steps": [],
                "raw_bedrock_response": raw_response
            }
            
        except Exception as e:
            logger.error(f"Bedrock inference failed for {execution_id}: {str(e)}")
            raise
    
    def _enhance_with_tools(self, llm_output: str, original_input: str) -> str:
        """Enhance LLM output using the available tools."""
        
        try:
            # Try to parse the LLM output as JSON
            try:
                parsed_output = json.loads(llm_output)
                base_analysis = parsed_output
            except json.JSONDecodeError:
                # If not JSON, create a base structure
                base_analysis = {
                    "bedrock_agent_config": {},
                    "action_groups": [],
                    "lambda_functions": [],
                    "cloudformation_templates": {},
                    "iam_policies": [],
                    "deployment_scripts": {},
                    "code_summary": llm_output
                }
            
            # Use Bedrock Agent Config tool to enhance the analysis
            config_tool = next((tool for tool in self.tools if tool.name == "bedrock_agent_config_generator"), None)
            if config_tool:
                try:
                    # Extract requirements and architecture from the original input
                    requirements = {
                        "agent_type_detected": "custom",
                        "functional_requirements": ["AI agent deployment", "API access"]
                    }
                    architecture = {
                        "selected_services": ["Amazon Bedrock", "AWS Lambda"],
                        "deployment_model": "serverless"
                    }
                    
                    config_result = config_tool._run(requirements, architecture)
                    config_data = json.loads(config_result)
                    
                    # Merge with base analysis
                    if "agent_configuration" in config_data:
                        base_analysis["bedrock_agent_config"] = config_data["agent_configuration"]
                    if "action_groups" in config_data:
                        base_analysis["action_groups"] = config_data["action_groups"]
                    if "deployment_artifacts" in config_data:
                        artifacts = config_data["deployment_artifacts"]
                        if "lambda_functions" in artifacts:
                            base_analysis["lambda_functions"] = artifacts["lambda_functions"]
                        if "iam_policies" in artifacts:
                            base_analysis["iam_policies"] = artifacts["iam_policies"]
                        if "deployment_script" in artifacts:
                            base_analysis["deployment_scripts"]["deploy.sh"] = artifacts["deployment_script"]
                        
                except Exception as e:
                    logger.warning(f"Bedrock Agent Config tool enhancement failed: {str(e)}")
            
            return json.dumps(base_analysis, indent=2)
            
        except Exception as e:
            logger.error(f"Tool enhancement failed: {str(e)}")
            return llm_output
    
    def _verify_response_compatibility(self, structured_output: Dict[str, Any]) -> None:
        """Verify that the response structure is compatible with the next agent in the pipeline."""
        
        required_fields = [
            "bedrock_agent_config",
            "action_groups", 
            "lambda_functions",
            "cloudformation_templates"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not structured_output.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"Response missing required fields for Quality Validator compatibility: {missing_fields}")
            
            # Add default values for missing fields
            for field in missing_fields:
                if field in ["action_groups", "lambda_functions", "iam_policies"]:
                    structured_output[field] = []
                else:
                    structured_output[field] = {}
        
        # Verify that Bedrock agent config has essential components
        agent_config = structured_output.get("bedrock_agent_config", {})
        if not agent_config.get("agent_name"):
            agent_config["agent_name"] = "AutoNinja-Generated-Agent"
        if not agent_config.get("foundation_model"):
            agent_config["foundation_model"] = "anthropic.claude-3-sonnet-20240229-v1:0"
        
        # Verify that action groups exist
        action_groups = structured_output.get("action_groups", [])
        if not action_groups:
            logger.warning("No action groups found in generated code")
        
        # Verify that Lambda functions exist
        lambda_functions = structured_output.get("lambda_functions", [])
        if not lambda_functions:
            logger.warning("No Lambda functions found in generated code")
        
        logger.info("Response structure verified for Quality Validator compatibility")
    
    def _generate_recommendations(self, structured_output: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on the code generation results."""
        
        recommendations = []
        
        # Check code completeness
        if not structured_output.get("bedrock_agent_config"):
            recommendations.append("Consider adding comprehensive Bedrock Agent configuration")
        
        if not structured_output.get("action_groups"):
            recommendations.append("Add action groups to provide functionality to the agent")
        
        if not structured_output.get("lambda_functions"):
            recommendations.append("Implement Lambda functions for action group handlers")
        
        # Check deployment readiness
        if not structured_output.get("cloudformation_templates"):
            recommendations.append("Add CloudFormation templates for infrastructure deployment")
        
        if not structured_output.get("iam_policies"):
            recommendations.append("Define IAM policies for secure operation")
        
        # Check documentation
        if not structured_output.get("documentation"):
            recommendations.append("Add comprehensive documentation for deployment and operation")
        
        # Default recommendation
        if not recommendations:
            recommendations.append("Code generation completed successfully - ready for quality validation")
        
        return recommendations
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration."""
        return {
            "agent_name": self.agent_name,
            "agent_type": "code_generator",
            "description": "Generates production-ready code based on architecture designs",
            "capabilities": [
                "Bedrock Agent configuration generation",
                "Action group implementation with OpenAPI schemas",
                "Lambda function code generation",
                "CloudFormation template creation",
                "IAM policy and role generation",
                "Deployment script creation",
                "Production-ready code with error handling",
                "Comprehensive documentation generation"
            ],
            "tools": [tool.name for tool in self.tools],
            "model_complexity": TaskComplexity.HIGH.value
        }


# Factory function for creating the agent
def create_code_generator_agent(
    bedrock_client_manager: Optional[BedrockClientManager] = None,
    knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None
) -> CodeGeneratorAgent:
    """
    Factory function to create a Code Generator Agent.
    
    Args:
        bedrock_client_manager: Optional Bedrock client manager
        knowledge_base_client: Optional knowledge base client
        
    Returns:
        CodeGeneratorAgent: Configured agent instance
    """
    return CodeGeneratorAgent(
        bedrock_client_manager=bedrock_client_manager,
        knowledge_base_client=knowledge_base_client
    )