"""
Requirements Analyst Agent

LangChain agent implementation for natural language processing, requirement extraction,
compliance checking, and validation capabilities. This agent transforms user requests
into structured, comprehensive specifications.
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
from autoninja.tools.requirements_analysis import (
    RequirementExtractionTool,
    ComplianceFrameworkDetectionTool,
    RequirementValidationTool,
    RequirementStructuringTool
)
from autoninja.models.state import (
    AgentOutput,
    RequirementsAnalystOutput,
    UserRequest
)
from autoninja.utils.retry import exponential_backoff_retry

logger = logging.getLogger(__name__)


class RequirementsAnalystAgent:
    """
    Requirements Analyst Agent for natural language processing and requirement extraction.
    
    This agent specializes in:
    - Natural language processing and requirement extraction
    - Compliance framework detection and validation
    - Requirement structuring and validation
    - Integration with Bedrock Knowledge Bases for pattern matching
    """
    
    def __init__(
        self,
        bedrock_client_manager: Optional[BedrockClientManager] = None,
        knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None
    ):
        """
        Initialize the Requirements Analyst Agent.
        
        Args:
            bedrock_client_manager: Bedrock client manager for model access
            knowledge_base_client: Knowledge base client for pattern retrieval
        """
        self.agent_name = "requirements_analyst"
        self.bedrock_client_manager = bedrock_client_manager or get_bedrock_client_manager()
        self.knowledge_base_client = knowledge_base_client
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Create the agent
        self.agent_executor = self._create_agent()
        
        logger.info("Requirements Analyst Agent initialized successfully")
    
    def _initialize_tools(self) -> List:
        """Initialize the tools available to the agent."""
        tools = [
            RequirementExtractionTool(knowledge_base_client=self.knowledge_base_client),
            ComplianceFrameworkDetectionTool(),
            RequirementValidationTool(),
            RequirementStructuringTool()
        ]
        
        logger.info(f"Initialized {len(tools)} tools for Requirements Analyst Agent")
        return tools
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools and prompt."""
        
        # System prompt for the Requirements Analyst Agent
        system_prompt = """You are a Requirements Analyst specializing in extracting and structuring 
requirements from natural language descriptions for any type of user - business, personal, 
or individual. Your role is to analyze user requests, identify functional and non-functional 
requirements, assess compliance needs, and generate structured specifications for real AI agents.

Your capabilities include:
- Natural language processing and requirement extraction
- Compliance framework identification and validation
- Requirement structuring into user stories and acceptance criteria
- Technical feasibility assessment
- Integration with knowledge bases for pattern matching

When analyzing user requests:
1. Extract clear functional requirements (what the agent should do)
2. Identify non-functional requirements (performance, security, scalability)
3. Detect applicable compliance frameworks and regulations
4. Assess technical complexity and feasibility
5. Structure requirements into standardized formats
6. Validate completeness and consistency
7. Provide recommendations for improvement

Always provide structured, actionable output that can be used by downstream agents
in the AutoNinja pipeline. Focus on clarity, completeness, and technical accuracy.

Use the available tools to perform thorough analysis and validation of requirements."""

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Get the appropriate Bedrock model
        model_id = self.bedrock_client_manager.select_model_by_complexity(TaskComplexity.MEDIUM)
        llm = self.bedrock_client_manager.get_client(model_id)
        
        # Create the tool-calling agent
        agent = create_tool_calling_agent(llm, self.tools, prompt)
        
        # Create the agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
            max_execution_time=300  # 5 minutes timeout
        )
        
        return agent_executor
    
    @exponential_backoff_retry(max_retries=3)
    def analyze_requirements(
        self,
        user_request: str,
        session_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        Analyze user requirements and extract structured specifications.
        
        Args:
            user_request: Natural language user request
            session_id: Session identifier for tracking
            additional_context: Optional additional context information
            
        Returns:
            AgentOutput: Structured agent output with requirements analysis
        """
        execution_id = f"{session_id}_{self.agent_name}_{int(datetime.now(UTC).timestamp())}"
        start_time = datetime.now(UTC)
        
        logger.info(f"Starting requirements analysis for session {session_id}")
        
        # Get pipeline logger for structured logging
        pipeline_logger = get_pipeline_logger(session_id)
        
        try:
            # Prepare input for the agent
            agent_input = self._prepare_agent_input(user_request, additional_context)
            
            # Log agent input for pipeline debugging
            pipeline_logger.log_agent_input(
                stage=PipelineStage.REQUIREMENTS_ANALYSIS,
                agent_name=self.agent_name,
                execution_id=execution_id,
                input_data={
                    "user_request": user_request,
                    "additional_context": additional_context or {},
                    "prepared_input": agent_input
                },
                metadata={
                    "agent_type": "requirements_analyst",
                    "model_complexity": "medium"
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
            
            # Calculate execution metadata
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()
            
            # Create the agent output
            agent_output = AgentOutput(
                agent_name=self.agent_name,
                execution_id=execution_id,
                input_data={
                    "user_request": user_request,
                    "session_id": session_id,
                    "additional_context": additional_context or {}
                },
                output=AgentOutput.Output(
                    result=structured_output,
                    confidence_score=self._calculate_confidence_score(structured_output),
                    reasoning=str(result.get("intermediate_steps", "Analysis completed successfully")),
                    recommendations=self._generate_recommendations(structured_output)
                ),
                execution_metadata=AgentOutput.ExecutionMetadata(
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration,
                    model_invocations=1,  # Could be tracked more precisely
                    tokens_used=0  # Would need to be tracked from Bedrock response
                ),
                trace_data=AgentOutput.TraceData(
                    trace_id=execution_id,
                    steps=[{
                        "step": "requirements_analysis",
                        "timestamp": start_time.isoformat(),
                        "duration": duration,
                        "status": "completed"
                    }]
                )
            )
            
            # Log agent output for pipeline handoff
            pipeline_logger.log_agent_output(
                stage=PipelineStage.REQUIREMENTS_ANALYSIS,
                agent_name=self.agent_name,
                execution_id=execution_id,
                output_data=agent_output,
                metadata={
                    "confidence_score": agent_output.output.confidence_score,
                    "processing_time": duration,
                    "recommendations_count": len(agent_output.output.recommendations)
                }
            )
            
            logger.info(f"Requirements analysis completed successfully for session {session_id}")
            return agent_output
            
        except Exception as e:
            logger.error(f"Error in requirements analysis for session {session_id}: {str(e)}")
            
            # Log pipeline error
            pipeline_logger.log_pipeline_error(
                stage=PipelineStage.REQUIREMENTS_ANALYSIS,
                agent_name=self.agent_name,
                execution_id=execution_id,
                error=e,
                context={
                    "user_request": user_request,
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
                    "user_request": user_request,
                    "session_id": session_id,
                    "additional_context": additional_context or {}
                },
                output=AgentOutput.Output(
                    result={"error": str(e)},
                    confidence_score=0.0,
                    reasoning=f"Analysis failed: {str(e)}",
                    recommendations=["Review input and retry analysis"]
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
                        "step": "requirements_analysis",
                        "timestamp": start_time.isoformat(),
                        "duration": duration,
                        "status": "failed",
                        "error": str(e)
                    }]
                )
            )
    
    def _prepare_agent_input(
        self, 
        user_request: str, 
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare input for the agent execution."""
        
        context_info = ""
        if additional_context:
            context_info = f"\n\nAdditional Context:\n{json.dumps(additional_context, indent=2)}"
        
        agent_input = f"""
Please analyze the following user request for AI agent generation and extract comprehensive requirements:

User Request:
{user_request}
{context_info}

Please perform the following analysis:

1. Extract functional requirements (what the agent should do)
2. Identify non-functional requirements (performance, security, scalability, etc.)
3. Detect applicable compliance frameworks and regulations
4. Assess technical complexity and feasibility
5. Structure requirements into user stories and acceptance criteria
6. Validate completeness and consistency
7. Provide recommendations for improvement

Use the available tools to perform thorough analysis. Provide a comprehensive, structured response
that includes all extracted requirements, compliance considerations, and validation results.
"""
        
        return agent_input
    
    def _process_agent_output(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Process and structure the raw agent output."""
        
        # Extract the main output from the agent execution
        output_text = raw_output.get("output", "")
        
        # Try to parse structured output if it's JSON
        structured_data = {}
        try:
            if output_text.strip().startswith("{"):
                structured_data = json.loads(output_text)
            else:
                # If not JSON, create a structured format
                structured_data = {
                    "analysis_summary": output_text,
                    "extraction_method": "text_analysis"
                }
        except json.JSONDecodeError:
            structured_data = {
                "analysis_summary": output_text,
                "extraction_method": "text_analysis"
            }
        
        # Ensure required fields are present
        result = {
            "extracted_requirements": structured_data.get("extracted_requirements", {}),
            "compliance_frameworks": structured_data.get("compliance_frameworks", []),
            "complexity_assessment": structured_data.get("complexity_assessment", {}),
            "structured_specifications": structured_data.get("structured_specifications", {}),
            "clarification_needed": structured_data.get("clarification_needed", []),
            "validation_results": structured_data.get("validation_results", {}),
            "analysis_summary": structured_data.get("analysis_summary", output_text),
            "extraction_method": structured_data.get("extraction_method", "structured_analysis"),
            "tool_outputs": self._extract_tool_outputs(raw_output)
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
        """Calculate confidence score based on the analysis completeness."""
        
        score = 0.0
        max_score = 100.0
        
        # Check for presence of key components
        if structured_output.get("extracted_requirements"):
            score += 30.0
        
        if structured_output.get("compliance_frameworks"):
            score += 20.0
        
        if structured_output.get("complexity_assessment"):
            score += 20.0
        
        if structured_output.get("structured_specifications"):
            score += 20.0
        
        if structured_output.get("validation_results"):
            score += 10.0
        
        return min(score / max_score, 1.0)
    
    def _make_bedrock_inference(self, agent_input: str, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Make direct inference call to Bedrock model with full request/response logging."""
        
        try:
            # Get the appropriate Bedrock model
            model_id = self.bedrock_client_manager.select_model_by_complexity(TaskComplexity.MEDIUM)
            
            # Prepare the messages for the model
            messages = [
                SystemMessage(content="""You are a Requirements Analyst specializing in extracting and structuring 
requirements from natural language descriptions. Your role is to analyze user requests, identify functional 
and non-functional requirements, assess compliance needs, and generate structured specifications.

Analyze the user request and provide a comprehensive JSON response with the following structure:
{
    "extracted_requirements": {
        "functional_requirements": ["list of functional requirements"],
        "non_functional_requirements": {
            "performance": ["performance requirements"],
            "security": ["security requirements"],
            "scalability": ["scalability requirements"]
        }
    },
    "compliance_frameworks": ["list of applicable compliance frameworks"],
    "complexity_assessment": {
        "complexity_score": 0-100,
        "complexity_level": "low|medium|high",
        "estimated_effort": "time estimate"
    },
    "structured_specifications": {
        "user_stories": [{"id": "US-001", "story": "user story"}],
        "acceptance_criteria": ["criteria list"]
    },
    "clarification_needed": ["list of clarifications needed"],
    "validation_results": {
        "completeness_score": 0-100,
        "consistency_issues": ["list of issues"]
    }
}"""),
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
                stage=PipelineStage.REQUIREMENTS_ANALYSIS
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
                stage=PipelineStage.REQUIREMENTS_ANALYSIS,
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
                    "extracted_requirements": {"functional_requirements": [], "non_functional_requirements": {}},
                    "compliance_frameworks": [],
                    "complexity_assessment": {},
                    "structured_specifications": {},
                    "analysis_summary": llm_output
                }
            
            # Use requirement extraction tool to enhance the analysis
            extraction_tool = next((tool for tool in self.tools if tool.name == "requirement_extraction"), None)
            if extraction_tool:
                try:
                    extraction_result = extraction_tool._run(original_input)
                    extraction_data = json.loads(extraction_result)
                    
                    # Merge with base analysis
                    if "functional_requirements" in extraction_data:
                        base_analysis["extracted_requirements"]["functional_requirements"].extend(
                            extraction_data["functional_requirements"]
                        )
                    if "non_functional_requirements" in extraction_data:
                        base_analysis["extracted_requirements"]["non_functional_requirements"].update(
                            extraction_data["non_functional_requirements"]
                        )
                except Exception as e:
                    logger.warning(f"Tool enhancement failed: {str(e)}")
            
            # Use compliance detection tool
            compliance_tool = next((tool for tool in self.tools if tool.name == "compliance_framework_detection"), None)
            if compliance_tool:
                try:
                    compliance_result = compliance_tool._run(original_input)
                    compliance_data = json.loads(compliance_result)
                    
                    if "compliance_frameworks" in compliance_data:
                        base_analysis["compliance_frameworks"].extend(
                            [fw["name"] for fw in compliance_data["compliance_frameworks"]]
                        )
                except Exception as e:
                    logger.warning(f"Compliance tool enhancement failed: {str(e)}")
            
            # Use validation tool
            validation_tool = next((tool for tool in self.tools if tool.name == "requirement_validation"), None)
            if validation_tool:
                try:
                    validation_result = validation_tool._run(base_analysis)
                    validation_data = json.loads(validation_result)
                    base_analysis["validation_results"] = validation_data
                except Exception as e:
                    logger.warning(f"Validation tool enhancement failed: {str(e)}")
            
            return json.dumps(base_analysis, indent=2)
            
        except Exception as e:
            logger.error(f"Tool enhancement failed: {str(e)}")
            return llm_output
    
    def _generate_recommendations(self, structured_output: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on the analysis results."""
        
        recommendations = []
        
        # Check completeness
        if not structured_output.get("extracted_requirements"):
            recommendations.append("Consider providing more detailed functional requirements")
        
        if not structured_output.get("compliance_frameworks"):
            recommendations.append("Review if any compliance frameworks apply to your use case")
        
        # Check for clarification needs
        clarifications = structured_output.get("clarification_needed", [])
        if clarifications:
            recommendations.extend([f"Clarification needed: {item}" for item in clarifications])
        
        # Default recommendation
        if not recommendations:
            recommendations.append("Requirements analysis completed successfully - ready for architecture design")
        
        return recommendations
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration."""
        return {
            "agent_name": self.agent_name,
            "agent_type": "requirements_analyst",
            "description": "Analyzes user requests and extracts structured requirements",
            "capabilities": [
                "Natural language processing",
                "Requirement extraction",
                "Compliance framework detection",
                "Requirement validation",
                "Requirement structuring"
            ],
            "tools": [tool.name for tool in self.tools],
            "model_complexity": TaskComplexity.MEDIUM.value
        }


# Factory function for creating the agent
def create_requirements_analyst_agent(
    bedrock_client_manager: Optional[BedrockClientManager] = None,
    knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None
) -> RequirementsAnalystAgent:
    """
    Factory function to create a Requirements Analyst Agent.
    
    Args:
        bedrock_client_manager: Optional Bedrock client manager
        knowledge_base_client: Optional knowledge base client
        
    Returns:
        RequirementsAnalystAgent: Configured agent instance
    """
    return RequirementsAnalystAgent(
        bedrock_client_manager=bedrock_client_manager,
        knowledge_base_client=knowledge_base_client
    )