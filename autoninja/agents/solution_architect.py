"""
Solution Architect Agent

LangChain agent implementation for AWS service selection, architecture design,
security planning, and Infrastructure as Code (IaC) generation. This agent transforms
structured requirements into optimal AWS-native architectures.
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
from autoninja.tools.solution_architecture import (
    ServiceSelectionTool,
    CloudFormationGeneratorTool,
    CostEstimationTool
)
from autoninja.models.state import (
    AgentOutput,
    SolutionArchitectOutput,
    RequirementsAnalystOutput
)
from autoninja.utils.retry import exponential_backoff_retry

logger = logging.getLogger(__name__)


class SolutionArchitectAgent:
    """
    Solution Architect Agent for AWS service selection and architecture design.
    
    This agent specializes in:
    - AWS service selection based on requirements
    - Architecture design following AWS Well-Architected Framework
    - Security architecture planning and implementation
    - Infrastructure as Code (IaC) template generation
    - Cost optimization and estimation
    """
    
    def __init__(
        self,
        bedrock_client_manager: Optional[BedrockClientManager] = None,
        knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None
    ):
        """
        Initialize the Solution Architect Agent.
        
        Args:
            bedrock_client_manager: Bedrock client manager for model access
            knowledge_base_client: Knowledge base client for pattern retrieval
        """
        self.agent_name = "solution_architect"
        self.bedrock_client_manager = bedrock_client_manager or get_bedrock_client_manager()
        self.knowledge_base_client = knowledge_base_client
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Create the agent
        self.agent_executor = self._create_agent()
        
        logger.info("Solution Architect Agent initialized successfully")
    
    def _initialize_tools(self) -> List:
        """Initialize the tools available to the agent."""
        tools = [
            ServiceSelectionTool(knowledge_base_client=self.knowledge_base_client),
            CloudFormationGeneratorTool(knowledge_base_client=self.knowledge_base_client),
            CostEstimationTool()
        ]
        
        logger.info(f"Initialized {len(tools)} tools for Solution Architect Agent")
        return tools
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools and prompt."""
        
        # System prompt for the Solution Architect Agent
        system_prompt = """You are an AWS Solution Architect for AI agents. Transform requirements into optimal, 
cost-effective AWS architectures using serverless-first approach.

Key responsibilities:
- Select essential AWS services (Bedrock, Lambda, API Gateway, DynamoDB, S3)
- Design serverless architectures with proper security (IAM, encryption)
- Generate CloudFormation templates
- Estimate costs and optimize for efficiency
- Ensure production-ready, scalable solutions

Provide concise, actionable outputs focusing on core services and essential configurations.
Use available tools for service selection, cost estimation, and template generation."""

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Use Claude 3.5 Sonnet for architecture design
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
            max_execution_time=600  # 10 minutes timeout for complex architecture design
        )
        
        return agent_executor
    
    @exponential_backoff_retry(max_retries=3)
    def design_architecture(
        self,
        requirements_output: AgentOutput,
        session_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        Design AWS architecture based on requirements analysis.
        
        Args:
            requirements_output: Output from Requirements Analyst Agent
            session_id: Session identifier for tracking
            additional_context: Optional additional context information
            
        Returns:
            AgentOutput: Structured agent output with architecture design
        """
        execution_id = f"{session_id}_{self.agent_name}_{int(datetime.now(UTC).timestamp())}"
        start_time = datetime.now(UTC)
        
        logger.info(f"Starting architecture design for session {session_id}")
        
        # Get pipeline logger for structured logging
        pipeline_logger = get_pipeline_logger(session_id)
        
        try:
            # Prepare input for the agent
            agent_input = self._prepare_agent_input(requirements_output, additional_context)
            
            # Log agent input for pipeline debugging
            pipeline_logger.log_agent_input(
                stage=PipelineStage.SOLUTION_ARCHITECTURE,
                agent_name=self.agent_name,
                execution_id=execution_id,
                input_data={
                    "requirements_output": requirements_output.model_dump(),
                    "additional_context": additional_context or {},
                    "prepared_input": agent_input
                },
                metadata={
                    "agent_type": "solution_architect",
                    "model_complexity": "high",
                    "previous_agent": "requirements_analyst"
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
                    "requirements_output": requirements_output.model_dump(),
                    "session_id": session_id,
                    "additional_context": additional_context or {}
                },
                output=AgentOutput.Output(
                    result=structured_output,
                    confidence_score=self._calculate_confidence_score(structured_output),
                    reasoning=str(result.get("intermediate_steps", "Architecture design completed successfully")),
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
                        "step": "architecture_design",
                        "timestamp": start_time.isoformat(),
                        "duration": duration,
                        "status": "completed"
                    }]
                )
            )
            
            # Log agent output for pipeline handoff
            pipeline_logger.log_agent_output(
                stage=PipelineStage.SOLUTION_ARCHITECTURE,
                agent_name=self.agent_name,
                execution_id=execution_id,
                output_data=agent_output,
                metadata={
                    "confidence_score": agent_output.output.confidence_score,
                    "processing_time": duration,
                    "recommendations_count": len(agent_output.output.recommendations),
                    "next_agent": "code_generator"
                }
            )
            
            logger.info(f"Architecture design completed successfully for session {session_id}")
            return agent_output
            
        except Exception as e:
            logger.error(f"Error in architecture design for session {session_id}: {str(e)}")
            
            # Log pipeline error
            pipeline_logger.log_pipeline_error(
                stage=PipelineStage.SOLUTION_ARCHITECTURE,
                agent_name=self.agent_name,
                execution_id=execution_id,
                error=e,
                context={
                    "requirements_output": requirements_output.model_dump(),
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
                    "requirements_output": requirements_output.model_dump(),
                    "session_id": session_id,
                    "additional_context": additional_context or {}
                },
                output=AgentOutput.Output(
                    result={"error": str(e)},
                    confidence_score=0.0,
                    reasoning=f"Architecture design failed: {str(e)}",
                    recommendations=["Review requirements and retry architecture design"]
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
                        "step": "architecture_design",
                        "timestamp": start_time.isoformat(),
                        "duration": duration,
                        "status": "failed",
                        "error": str(e)
                    }]
                )
            )
    
    def _prepare_agent_input(
        self, 
        requirements_output: AgentOutput, 
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare input for the agent execution."""
        
        # Extract requirements from the previous agent's output
        requirements_result = requirements_output.output.result
        
        context_info = ""
        if additional_context:
            context_info = f"\n\nAdditional Context:\n{json.dumps(additional_context, indent=2)}"
        
        agent_input = f"""
Design an AWS architecture for this AI agent based on requirements:

Requirements: {json.dumps(requirements_result, indent=2)}
{context_info}

Tasks:
1. Select essential AWS services (focus on Bedrock, Lambda, API Gateway, DynamoDB, S3)
2. Design serverless architecture with service relationships
3. Plan security (IAM roles, encryption)
4. Generate CloudFormation template structure
5. Estimate costs and optimization opportunities
6. Design API integrations

Provide concise, production-ready architecture. Output must be compatible with Code Generator Agent.
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
                    "architecture_summary": output_text,
                    "design_method": "text_analysis"
                }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            structured_data = {
                "architecture_summary": output_text,
                "design_method": "text_analysis"
            }
        
        # Ensure required fields are present for Solution Architect output
        result = {
            "selected_services": structured_data.get("selected_services", []),
            "architecture_blueprint": structured_data.get("architecture_blueprint", {}),
            "security_architecture": structured_data.get("security_architecture", {}),
            "cost_estimation": structured_data.get("cost_estimation", {}),
            "iac_templates": structured_data.get("iac_templates", {}),
            "integration_design": structured_data.get("integration_design", {}),
            "architecture_summary": structured_data.get("architecture_summary", output_text),
            "design_method": structured_data.get("design_method", "structured_analysis"),
            "tool_outputs": self._extract_tool_outputs(raw_output),
            "deployment_complexity": structured_data.get("deployment_complexity", {}),
            "scalability_plan": structured_data.get("scalability_plan", {}),
            "monitoring_strategy": structured_data.get("monitoring_strategy", {})
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
        """Calculate confidence score based on the architecture design completeness."""
        
        score = 0.0
        max_score = 100.0
        
        # Check for presence of key components
        if structured_output.get("selected_services"):
            score += 20.0
        
        if structured_output.get("architecture_blueprint"):
            score += 25.0
        
        if structured_output.get("security_architecture"):
            score += 20.0
        
        if structured_output.get("iac_templates"):
            score += 20.0
        
        if structured_output.get("cost_estimation"):
            score += 10.0
        
        if structured_output.get("integration_design"):
            score += 5.0
        
        return min(score / max_score, 1.0)
    
    def _make_bedrock_inference(self, agent_input: str, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Make direct inference call to Bedrock model with full request/response logging."""
        
        try:
            # Use Claude 3.5 Sonnet for architecture design
            model_id = BedrockModelId.CLAUDE_SONNET_4_5
            
            # Prepare the messages for the model
            messages = [
                SystemMessage(content="""You are an AWS Solution Architect. Transform requirements into optimal AWS architectures.

Provide a concise JSON response:
{
    "selected_services": [
        {"service": "Amazon Bedrock", "purpose": "AI inference", "priority": "high"},
        {"service": "AWS Lambda", "purpose": "Serverless compute", "priority": "high"}
    ],
    "architecture_blueprint": {
        "deployment_model": "serverless",
        "service_relationships": {"api_gateway": "lambda", "lambda": "bedrock"},
        "data_flow": "api -> lambda -> bedrock -> response"
    },
    "security_architecture": {
        "iam_design": {"roles": ["lambda_execution"], "policies": ["bedrock_invoke"]},
        "encryption": {"at_rest": "kms", "in_transit": "tls"}
    },
    "iac_templates": {
        "cloudformation_template": {"Resources": {"LambdaFunction": {}, "ApiGateway": {}}}
    },
    "cost_estimation": {
        "monthly_estimate": 150,
        "breakdown": {"bedrock": 100, "lambda": 30, "api_gateway": 20}
    },
    "integration_design": {
        "api_endpoints": ["/chat", "/analyze"],
        "authentication": "api_key"
    },
    "deployment_complexity": {
        "level": "medium",
        "time": "2-3 weeks"
    }
}

Focus on essential services only. Be specific and concise."""),
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
                stage=PipelineStage.SOLUTION_ARCHITECTURE
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
                stage=PipelineStage.SOLUTION_ARCHITECTURE,
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
                    "selected_services": [],
                    "architecture_blueprint": {},
                    "security_architecture": {},
                    "iac_templates": {},
                    "cost_estimation": {},
                    "integration_design": {},
                    "architecture_summary": llm_output
                }
            
            # Use service selection tool to enhance the analysis
            service_tool = next((tool for tool in self.tools if tool.name == "aws_service_selection"), None)
            if service_tool and base_analysis.get("selected_services"):
                try:
                    # Extract requirements for service selection
                    requirements = {
                        "functional_requirements": ["AI agent deployment", "API access"],
                        "non_functional_requirements": {"performance": [], "security": [], "scalability": []},
                        "agent_type_detected": "custom"
                    }
                    
                    service_result = service_tool._run(requirements)
                    service_data = json.loads(service_result)
                    
                    # Merge with base analysis
                    if "recommended_services" in service_data:
                        base_analysis["selected_services"] = service_data["recommended_services"]
                    if "cost_estimate" in service_data:
                        base_analysis["cost_estimation"] = service_data["cost_estimate"]
                        
                except Exception as e:
                    logger.warning(f"Service selection tool enhancement failed: {str(e)}")
            
            # Use CloudFormation generator tool
            cf_tool = next((tool for tool in self.tools if tool.name == "cloudformation_generator"), None)
            if cf_tool and base_analysis.get("architecture_blueprint"):
                try:
                    cf_result = cf_tool._run(base_analysis["architecture_blueprint"])
                    cf_data = json.loads(cf_result)
                    
                    if "cloudformation_template" in cf_data:
                        base_analysis["iac_templates"]["cloudformation"] = cf_data["cloudformation_template"]
                    if "deployment_instructions" in cf_data:
                        base_analysis["deployment_instructions"] = cf_data["deployment_instructions"]
                        
                except Exception as e:
                    logger.warning(f"CloudFormation tool enhancement failed: {str(e)}")
            
            # Use cost estimation tool
            cost_tool = next((tool for tool in self.tools if tool.name == "aws_cost_estimation"), None)
            if cost_tool and base_analysis.get("architecture_blueprint"):
                try:
                    cost_result = cost_tool._run(base_analysis["architecture_blueprint"])
                    cost_data = json.loads(cost_result)
                    base_analysis["cost_estimation"] = cost_data
                except Exception as e:
                    logger.warning(f"Cost estimation tool enhancement failed: {str(e)}")
            
            return json.dumps(base_analysis, indent=2)
            
        except Exception as e:
            logger.error(f"Tool enhancement failed: {str(e)}")
            return llm_output
    
    def _verify_response_compatibility(self, structured_output: Dict[str, Any]) -> None:
        """Verify that the response structure is compatible with the next agent in the pipeline."""
        
        required_fields = [
            "selected_services",
            "architecture_blueprint", 
            "security_architecture",
            "iac_templates"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not structured_output.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"Response missing required fields for Code Generator compatibility: {missing_fields}")
            
            # Add default values for missing fields
            for field in missing_fields:
                if field == "selected_services":
                    structured_output[field] = []
                else:
                    structured_output[field] = {}
        
        # Verify that architecture blueprint has essential components
        blueprint = structured_output.get("architecture_blueprint", {})
        if not blueprint.get("deployment_model"):
            blueprint["deployment_model"] = "serverless"
        
        # Verify that selected services include essential AWS services
        services = structured_output.get("selected_services", [])
        service_names = [s.get("service", "") if isinstance(s, dict) else str(s) for s in services]
        
        essential_services = ["Amazon Bedrock", "AWS Lambda"]
        for essential in essential_services:
            if not any(essential in service for service in service_names):
                logger.warning(f"Essential service {essential} not found in selected services")
        
        logger.info("Response structure verified for Code Generator compatibility")
    
    def _generate_recommendations(self, structured_output: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on the architecture design results."""
        
        recommendations = []
        
        # Check architecture completeness
        if not structured_output.get("selected_services"):
            recommendations.append("Consider adding more AWS services to support the requirements")
        
        if not structured_output.get("security_architecture"):
            recommendations.append("Develop comprehensive security architecture with IAM and encryption")
        
        # Check cost optimization
        cost_est = structured_output.get("cost_estimation", {})
        if cost_est.get("monthly_estimate", 0) > 500:
            recommendations.append("Review cost optimization opportunities to reduce monthly expenses")
        
        # Check deployment complexity
        complexity = structured_output.get("deployment_complexity", {})
        if complexity.get("complexity_level") == "high":
            recommendations.append("Consider simplifying architecture to reduce deployment complexity")
        
        # Default recommendation
        if not recommendations:
            recommendations.append("Architecture design completed successfully - ready for code generation")
        
        return recommendations
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration."""
        return {
            "agent_name": self.agent_name,
            "agent_type": "solution_architect",
            "description": "Designs AWS-native architectures based on requirements",
            "capabilities": [
                "AWS service selection and optimization",
                "Architecture design and blueprints",
                "Security architecture planning",
                "Infrastructure as Code generation",
                "Cost estimation and optimization",
                "Integration design"
            ],
            "tools": [tool.name for tool in self.tools],
            "model_id": BedrockModelId.CLAUDE_SONNET_4_5.value
        }


# Factory function for creating the agent
def create_solution_architect_agent(
    bedrock_client_manager: Optional[BedrockClientManager] = None,
    knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None
) -> SolutionArchitectAgent:
    """
    Factory function to create a Solution Architect Agent.
    
    Args:
        bedrock_client_manager: Optional Bedrock client manager
        knowledge_base_client: Optional knowledge base client
        
    Returns:
        SolutionArchitectAgent: Configured agent instance
    """
    return SolutionArchitectAgent(
        bedrock_client_manager=bedrock_client_manager,
        knowledge_base_client=knowledge_base_client
    )