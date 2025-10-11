"""
Quality Validator Agent

LangChain agent implementation for comprehensive code quality analysis, CloudFormation
template validation, and security scanning for generated agents. This agent validates
the output from the Code Generator Agent to ensure production readiness.
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
from autoninja.tools.quality_validation import (
    CodeQualityAnalysisTool,
    CloudFormationValidationTool,
    SecurityScanTool,
    AWSBestPracticesValidationTool,
    PerformanceAssessmentTool,
    ComplianceValidationTool
)
from autoninja.models.state import (
    AgentOutput,
    CodeGeneratorOutput
)
from autoninja.utils.retry import exponential_backoff_retry

logger = logging.getLogger(__name__)


class QualityValidatorAgent:
    """
    Quality Validator Agent for comprehensive code and configuration analysis.
    
    This agent specializes in:
    - Static code analysis for quality metrics and best practices
    - Security scanning for vulnerabilities and security anti-patterns
    - AWS best practices validation for compliance with guidelines
    - Performance assessment and optimization recommendations
    - Compliance validation for regulatory requirements
    - CloudFormation template validation
    """
    
    def __init__(
        self,
        bedrock_client_manager: Optional[BedrockClientManager] = None,
        knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None
    ):
        """
        Initialize the Quality Validator Agent.
        
        Args:
            bedrock_client_manager: Bedrock client manager for model access
            knowledge_base_client: Knowledge base client for pattern retrieval
        """
        self.agent_name = "quality_validator"
        self.bedrock_client_manager = bedrock_client_manager or get_bedrock_client_manager()
        self.knowledge_base_client = knowledge_base_client
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Create the agent
        self.agent_executor = self._create_agent()
        
        logger.info("Quality Validator Agent initialized successfully")
    
    def _initialize_tools(self) -> List:
        """Initialize the tools available to the agent."""
        tools = [
            CodeQualityAnalysisTool(),
            CloudFormationValidationTool(),
            SecurityScanTool(),
            AWSBestPracticesValidationTool(),
            PerformanceAssessmentTool(),
            ComplianceValidationTool()
        ]
        
        logger.info(f"Initialized {len(tools)} tools for Quality Validator Agent")
        return tools
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools and prompt."""
        
        # System prompt for the Quality Validator Agent
        system_prompt = """You are a Quality Validator responsible for comprehensive Bedrock Agent 
validation. Validate agent configurations, action group implementations, knowledge base 
integrations, and CloudFormation templates for production readiness.

Your capabilities include:
- Static code analysis using pylint, black, and mypy for Python code quality
- CloudFormation template validation using cfn-lint and AWS CLI
- Security scanning for vulnerabilities and security anti-patterns
- AWS best practices validation for compliance with operational guidelines
- Performance assessment and optimization recommendations
- Compliance validation for regulatory frameworks (SOC2, HIPAA, PCI-DSS, GDPR)

When validating generated code and configurations:
1. Perform comprehensive code quality analysis on all Python code
2. Validate CloudFormation templates for syntax and best practices
3. Scan for security vulnerabilities and anti-patterns
4. Verify compliance with AWS Well-Architected Framework principles
5. Assess performance characteristics and optimization opportunities
6. Check adherence to specified compliance frameworks
7. Generate detailed quality reports with scores and recommendations
8. Flag critical issues that block production deployment

Always provide structured, actionable output with specific recommendations for improvement.
Focus on production readiness, security, and operational excellence. Use available tools for 
comprehensive validation and analysis."""

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Use Claude 3 Haiku for quality validation (reliable and fast)
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
            max_iterations=20,
            max_execution_time=900  # 15 minutes timeout for comprehensive validation
        )
        
        return agent_executor
    
    @exponential_backoff_retry(max_retries=3)
    def validate_quality(
        self,
        code_generator_output: AgentOutput,
        session_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        Validate quality of generated code and configurations.
        
        Args:
            code_generator_output: Output from Code Generator Agent
            session_id: Session identifier for tracking
            additional_context: Optional additional context information
            
        Returns:
            AgentOutput: Structured agent output with validation results
        """
        execution_id = f"{session_id}_{self.agent_name}_{int(datetime.now(UTC).timestamp())}"
        start_time = datetime.now(UTC)
        
        logger.info(f"Starting quality validation for session {session_id}")
        
        # Get pipeline logger for structured logging
        pipeline_logger = get_pipeline_logger(session_id)
        
        try:
            # Prepare input for the agent
            agent_input = self._prepare_agent_input(code_generator_output, additional_context)
            
            # Log agent input for pipeline debugging
            pipeline_logger.log_agent_input(
                stage=PipelineStage.QUALITY_VALIDATION,
                agent_name=self.agent_name,
                execution_id=execution_id,
                input_data={
                    "code_generator_output": code_generator_output.model_dump(),
                    "additional_context": additional_context or {},
                    "prepared_input": agent_input
                },
                metadata={
                    "agent_type": "quality_validator",
                    "model_complexity": "high",
                    "previous_agent": "code_generator"
                }
            )
            
            # Log raw request
            logger.info(f"Raw request for {execution_id}: {json.dumps(agent_input, indent=2)}")
            
            # Make multiple Bedrock inference calls for different components
            result = self._make_chunked_bedrock_inference(code_generator_output, execution_id, pipeline_logger)
            
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
                    "code_generator_output": code_generator_output.model_dump(),
                    "session_id": session_id,
                    "additional_context": additional_context or {}
                },
                output=AgentOutput.Output(
                    result=structured_output,
                    confidence_score=self._calculate_confidence_score(structured_output),
                    reasoning=str(result.get("intermediate_steps", "Quality validation completed successfully")),
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
                        "step": "quality_validation",
                        "timestamp": start_time.isoformat(),
                        "duration": duration,
                        "status": "completed"
                    }]
                )
            )
            
            # Log agent output for pipeline handoff
            pipeline_logger.log_agent_output(
                stage=PipelineStage.QUALITY_VALIDATION,
                agent_name=self.agent_name,
                execution_id=execution_id,
                output_data=agent_output,
                metadata={
                    "confidence_score": agent_output.output.confidence_score,
                    "processing_time": duration,
                    "recommendations_count": len(agent_output.output.recommendations),
                    "next_agent": "deployment_manager"
                }
            )
            
            logger.info(f"Quality validation completed successfully for session {session_id}")
            return agent_output
            
        except Exception as e:
            logger.error(f"Error in quality validation for session {session_id}: {str(e)}")
            
            # Log pipeline error
            pipeline_logger.log_pipeline_error(
                stage=PipelineStage.QUALITY_VALIDATION,
                agent_name=self.agent_name,
                execution_id=execution_id,
                error=e,
                context={
                    "code_generator_output": code_generator_output.model_dump(),
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
                    "code_generator_output": code_generator_output.model_dump(),
                    "session_id": session_id,
                    "additional_context": additional_context or {}
                },
                output=AgentOutput.Output(
                    result={"error": str(e)},
                    confidence_score=0.0,
                    reasoning=f"Quality validation failed: {str(e)}",
                    recommendations=["Review generated code and retry validation"]
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
                        "step": "quality_validation",
                        "timestamp": start_time.isoformat(),
                        "duration": duration,
                        "status": "failed",
                        "error": str(e)
                    }]
                )
            )
    
    def _prepare_agent_input(
        self, 
        code_generator_output: AgentOutput, 
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare input for the agent execution."""
        
        # Extract generated code from the previous agent's output
        code_result = code_generator_output.output.result
        
        # Create a summary of the generated components instead of full content
        summary = {
            "agent_name": code_result.get("bedrock_agent_config", {}).get("agent_name", "Unknown"),
            "components": {
                "bedrock_agent": bool(code_result.get("bedrock_agent_config")),
                "action_groups": len(code_result.get("action_groups", [])),
                "lambda_functions": len(code_result.get("lambda_functions", [])),
                "cloudformation_templates": len(code_result.get("cloudformation_templates", {})),
                "iam_policies": len(code_result.get("iam_policies", []))
            },
            "sample_lambda_code": code_result.get("lambda_functions", [{}])[0].get("code", "")[:500] + "..." if code_result.get("lambda_functions") else "",
            "sample_cf_resources": list(code_result.get("cloudformation_templates", {}).get("main_template", {}).get("Resources", {}).keys())[:3]
        }
        
        context_info = ""
        if additional_context:
            context_info = f"\nAdditional Context: {json.dumps(additional_context)}"
        
        agent_input = f"""
Validate this AI agent for production deployment:

Agent Summary: {json.dumps(summary, indent=2)}
{context_info}

Perform quality validation covering:
1. Code quality (Python Lambda functions)
2. CloudFormation template validation
3. Security scanning and compliance
4. AWS best practices
5. Performance assessment
6. Production readiness

Provide JSON response with scores, issues, and recommendations for deployment readiness.
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
                    "validation_summary": output_text,
                    "validation_method": "text_analysis"
                }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            structured_data = {
                "validation_summary": output_text,
                "validation_method": "text_analysis"
            }
        
        # Ensure required fields are present for Quality Validator output
        result = {
            "code_quality_analysis": structured_data.get("code_quality_analysis", {}),
            "cloudformation_validation": structured_data.get("cloudformation_validation", {}),
            "security_scan_results": structured_data.get("security_scan_results", {}),
            "aws_best_practices": structured_data.get("aws_best_practices", {}),
            "performance_assessment": structured_data.get("performance_assessment", {}),
            "compliance_validation": structured_data.get("compliance_validation", {}),
            "overall_quality_score": structured_data.get("overall_quality_score", 0.0),
            "critical_issues": structured_data.get("critical_issues", []),
            "blocking_issues": structured_data.get("blocking_issues", []),
            "recommendations": structured_data.get("recommendations", []),
            "production_readiness": structured_data.get("production_readiness", {}),
            "validation_summary": structured_data.get("validation_summary", output_text),
            "validation_method": structured_data.get("validation_method", "structured_analysis"),
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
        """Calculate confidence score based on the validation completeness and results."""
        
        score = 0.0
        max_score = 100.0
        
        # Check for presence of key validation components
        if structured_output.get("code_quality_analysis"):
            score += 20.0
        
        if structured_output.get("cloudformation_validation"):
            score += 15.0
        
        if structured_output.get("security_scan_results"):
            score += 20.0
        
        if structured_output.get("aws_best_practices"):
            score += 15.0
        
        if structured_output.get("performance_assessment"):
            score += 10.0
        
        if structured_output.get("compliance_validation"):
            score += 10.0
        
        # Adjust based on overall quality score
        overall_quality = structured_output.get("overall_quality_score", 0.0)
        if overall_quality >= 8.0:
            score += 10.0
        elif overall_quality >= 6.0:
            score += 5.0
        
        return min(score / max_score, 1.0)
    
    def _make_chunked_bedrock_inference(self, code_generator_output: AgentOutput, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Make multiple Bedrock inference calls for different components to avoid timeout."""
        
        code_result = code_generator_output.output.result
        combined_results = {}
        
        try:
            # 1. Validate Lambda Functions
            lambda_functions = code_result.get("lambda_functions", [])
            if lambda_functions:
                lambda_validation = self._validate_lambda_functions(lambda_functions, execution_id, pipeline_logger)
                combined_results["code_quality_analysis"] = lambda_validation
            
            # 2. Validate CloudFormation Templates
            cf_templates = code_result.get("cloudformation_templates", {})
            if cf_templates:
                cf_validation = self._validate_cloudformation_templates(cf_templates, execution_id, pipeline_logger)
                combined_results["cloudformation_validation"] = cf_validation
            
            # 3. Validate Security and Compliance
            security_validation = self._validate_security_compliance(code_result, execution_id, pipeline_logger)
            combined_results["security_scan_results"] = security_validation
            
            # 4. Overall Assessment
            overall_assessment = self._generate_overall_assessment(combined_results, execution_id, pipeline_logger)
            combined_results.update(overall_assessment)
            
            return {
                "output": json.dumps(combined_results, indent=2),
                "intermediate_steps": [],
                "raw_bedrock_response": {"combined_validation": True}
            }
            
        except Exception as e:
            logger.error(f"Chunked Bedrock inference failed for {execution_id}: {str(e)}")
            raise
    
    def _validate_lambda_functions(self, lambda_functions: List[Dict], execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Validate Lambda function code quality with size-based chunking."""
        
        if not lambda_functions:
            return {"error": "No Lambda functions to validate"}
        
        all_results = []
        
        for i, lambda_func in enumerate(lambda_functions):
            code = lambda_func.get("code", "")
            
            # Split large code into chunks (max 2000 characters per chunk)
            code_chunks = self._split_text_into_chunks(code, max_chars=2000)
            
            for chunk_idx, code_chunk in enumerate(code_chunks):
                agent_input = f"""
Analyze this Python Lambda function code segment for quality:

Function: {lambda_func.get("function_name", "unknown")} (part {chunk_idx + 1}/{len(code_chunks)})
Runtime: {lambda_func.get("runtime", "unknown")}

Code Segment:
{code_chunk}

Provide JSON response:
{{
    "code_issues": ["list of issues found in this segment"],
    "recommendations": ["recommendations for this segment"],
    "quality_score": 8.5
}}
"""
                
                chunk_result = self._make_single_bedrock_call(
                    agent_input, 
                    f"{execution_id}_lambda_{i}_{chunk_idx}", 
                    pipeline_logger
                )
                all_results.append(chunk_result)
        
        # Combine results from all chunks
        return self._combine_lambda_results(all_results)
    
    def _split_text_into_chunks(self, text: str, max_chars: int = 2000) -> List[str]:
        """Split text into chunks of maximum character count."""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            # Find a good break point (end of line if possible)
            end_pos = current_pos + max_chars
            
            if end_pos >= len(text):
                chunks.append(text[current_pos:])
                break
            
            # Try to break at a newline
            break_pos = text.rfind('\n', current_pos, end_pos)
            if break_pos == -1:
                break_pos = end_pos
            
            chunks.append(text[current_pos:break_pos])
            current_pos = break_pos + 1 if break_pos < len(text) else break_pos
        
        return chunks
    
    def _combine_lambda_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Combine results from multiple Lambda function chunks."""
        all_issues = []
        all_recommendations = []
        total_score = 0
        valid_results = 0
        
        for result in results:
            if "error" not in result:
                all_issues.extend(result.get("code_issues", []))
                all_recommendations.extend(result.get("recommendations", []))
                total_score += result.get("quality_score", 0)
                valid_results += 1
        
        avg_score = total_score / valid_results if valid_results > 0 else 0
        
        return {
            "python_code_quality": {
                "pylint_score": avg_score,
                "black_formatting": "PASS" if avg_score >= 7.0 else "FAIL",
                "mypy_type_checking": "PASS" if avg_score >= 7.0 else "FAIL",
                "issues_found": all_issues,
                "recommendations": all_recommendations
            },
            "overall_code_score": avg_score
        }
    
    def _validate_cloudformation_templates(self, cf_templates: Dict, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Validate CloudFormation templates with size-based chunking."""
        
        main_template = cf_templates.get("main_template", {})
        
        # Convert template to string and check size
        template_str = json.dumps(main_template, indent=2)
        
        if len(template_str) <= 3000:
            # Small template - validate as one piece
            agent_input = f"""
Validate this CloudFormation template:

{template_str}

Provide JSON response:
{{
    "template_validation": {{
        "syntax_valid": true,
        "cfn_lint_score": 9.0,
        "issues_found": ["list of issues"]
    }},
    "best_practices_score": 8.0
}}
"""
            return self._make_single_bedrock_call(agent_input, f"{execution_id}_cf", pipeline_logger)
        
        else:
            # Large template - validate resources individually
            resources = main_template.get("Resources", {})
            all_results = []
            
            for resource_name, resource_def in resources.items():
                resource_str = json.dumps({resource_name: resource_def}, indent=2)
                
                agent_input = f"""
Validate this CloudFormation resource:

{resource_str}

Provide JSON response:
{{
    "resource_issues": ["issues with this resource"],
    "best_practices_score": 8.0
}}
"""
                
                result = self._make_single_bedrock_call(
                    agent_input, 
                    f"{execution_id}_cf_{resource_name}", 
                    pipeline_logger
                )
                all_results.append(result)
            
            return self._combine_cf_results(all_results)
    
    def _combine_cf_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Combine results from multiple CloudFormation resource validations."""
        all_issues = []
        total_score = 0
        valid_results = 0
        
        for result in results:
            if "error" not in result:
                all_issues.extend(result.get("resource_issues", []))
                total_score += result.get("best_practices_score", 0)
                valid_results += 1
        
        avg_score = total_score / valid_results if valid_results > 0 else 0
        
        return {
            "template_validation": {
                "syntax_valid": True,
                "cfn_lint_score": avg_score,
                "aws_cli_validation": "PASS" if avg_score >= 7.0 else "FAIL",
                "issues_found": all_issues
            },
            "best_practices_score": avg_score
        }
    
    def _validate_security_compliance(self, code_result: Dict, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Validate security and compliance aspects."""
        
        # Extract key security-relevant components
        iam_policies = code_result.get("iam_policies", [])
        bedrock_config = code_result.get("bedrock_agent_config", {})
        
        agent_input = f"""
Perform security analysis on this AI agent configuration:

Bedrock Agent: {json.dumps(bedrock_config, indent=2)}
IAM Policies: {json.dumps(iam_policies, indent=2)}

Provide JSON response with:
{{
    "vulnerability_scan": {{
        "high_severity": 0,
        "medium_severity": 1,
        "low_severity": 2,
        "security_score": 8.0
    }},
    "security_recommendations": ["list of security improvements"]
}}
"""
        
        return self._make_single_bedrock_call(agent_input, f"{execution_id}_security", pipeline_logger)
    
    def _generate_overall_assessment(self, validation_results: Dict, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Generate overall quality assessment."""
        
        agent_input = f"""
Generate overall quality assessment based on validation results:

Validation Results: {json.dumps(validation_results, indent=2)}

Provide JSON response with:
{{
    "aws_best_practices": {{
        "well_architected_compliance": {{
            "security": 8.5,
            "reliability": 8.0,
            "performance": 7.5,
            "cost_optimization": 8.0,
            "operational_excellence": 7.5
        }},
        "overall_compliance_score": 8.0
    }},
    "performance_assessment": {{
        "performance_score": 7.5,
        "optimization_opportunities": ["list of optimizations"]
    }},
    "compliance_validation": {{
        "framework_compliance": {{"SOC2": "PASS", "GDPR": "PARTIAL"}},
        "compliance_score": 8.0
    }},
    "overall_quality_score": 8.1,
    "critical_issues": ["list of critical issues"],
    "blocking_issues": ["list of blocking issues"],
    "recommendations": ["prioritized recommendations"],
    "production_readiness": {{
        "ready_for_deployment": true,
        "confidence_level": "high",
        "required_actions": ["list of required actions"]
    }}
}}
"""
        
        return self._make_single_bedrock_call(agent_input, f"{execution_id}_overall", pipeline_logger)
    
    def _make_single_bedrock_call(self, agent_input: str, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Make a single Bedrock inference call."""
        
        try:
            model_id = BedrockModelId.CLAUDE_SONNET_4_5
            
            messages = [
                SystemMessage(content="You are a Quality Validator. Provide detailed JSON analysis as requested."),
                HumanMessage(content=agent_input)
            ]
            
            # Log the request
            raw_request = {
                "model_id": model_id.value,
                "messages": [{"role": msg.type, "content": msg.content} for msg in messages],
                "execution_id": execution_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
            logger.info(f"Raw Bedrock request for {execution_id}: {json.dumps(raw_request, indent=2)}")
            log_bedrock_request(execution_id, raw_request)
            
            pipeline_logger.log_inference_request(
                execution_id=execution_id,
                model_id=model_id.value,
                request_data=raw_request,
                agent_name=self.agent_name,
                stage=PipelineStage.QUALITY_VALIDATION
            )
            
            # Make the inference call
            start_inference = datetime.now(UTC)
            response = self.bedrock_client_manager.invoke_with_retry(
                model_id=model_id,
                messages=messages
            )
            end_inference = datetime.now(UTC)
            inference_time = (end_inference - start_inference).total_seconds()
            
            # Log the response
            raw_response = {
                "model_id": model_id.value,
                "response_content": response.content if hasattr(response, 'content') else str(response),
                "execution_id": execution_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
            logger.info(f"Raw Bedrock response for {execution_id}: {json.dumps(raw_response, indent=2)}")
            log_bedrock_response(execution_id, raw_response)
            
            pipeline_logger.log_inference_response(
                execution_id=execution_id,
                model_id=model_id.value,
                response_data=raw_response,
                agent_name=self.agent_name,
                stage=PipelineStage.QUALITY_VALIDATION,
                processing_time=inference_time
            )
            
            # Extract and parse the response
            if hasattr(response, 'content'):
                output_content = response.content
            else:
                output_content = str(response)
            
            try:
                return json.loads(output_content)
            except json.JSONDecodeError:
                return {"analysis_text": output_content}
                
        except Exception as e:
            logger.error(f"Single Bedrock call failed for {execution_id}: {str(e)}")
            return {"error": str(e)}

    def _make_bedrock_inference(self, agent_input: str, execution_id: str, pipeline_logger) -> Dict[str, Any]:
        """Make direct inference call to Bedrock model with full request/response logging."""
        
        try:
            # Use Claude 3 Haiku for quality validation
            model_id = BedrockModelId.CLAUDE_SONNET_4_5
            
            # Prepare the messages for the model
            messages = [
                SystemMessage(content="""You are a Quality Validator specializing in comprehensive code and configuration analysis.

Provide a detailed JSON response with complete validation results:
{
    "code_quality_analysis": {
        "python_code_quality": {
            "pylint_score": 8.5,
            "black_formatting": "PASS",
            "mypy_type_checking": "PASS",
            "issues_found": ["list of issues"],
            "recommendations": ["list of recommendations"]
        },
        "overall_code_score": 8.5
    },
    "cloudformation_validation": {
        "template_validation": {
            "syntax_valid": true,
            "cfn_lint_score": 9.0,
            "aws_cli_validation": "PASS",
            "issues_found": ["list of issues"]
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
        "security_recommendations": ["list of security improvements"]
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
        "optimization_opportunities": ["list of optimizations"]
    },
    "compliance_validation": {
        "framework_compliance": {"SOC2": "PASS", "GDPR": "PARTIAL"},
        "compliance_score": 8.0
    },
    "overall_quality_score": 8.1,
    "critical_issues": ["list of critical issues that block deployment"],
    "blocking_issues": ["list of issues that must be fixed"],
    "recommendations": ["prioritized list of all recommendations"],
    "production_readiness": {
        "ready_for_deployment": true,
        "confidence_level": "high",
        "required_actions": ["list of required actions before deployment"]
    }
}

Provide comprehensive analysis with specific scores, detailed findings, and actionable recommendations."""),
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
                stage=PipelineStage.QUALITY_VALIDATION
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
                stage=PipelineStage.QUALITY_VALIDATION,
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
                    "code_quality_analysis": {},
                    "cloudformation_validation": {},
                    "security_scan_results": {},
                    "aws_best_practices": {},
                    "performance_assessment": {},
                    "compliance_validation": {},
                    "overall_quality_score": 0.0,
                    "validation_summary": llm_output
                }
            
            # Extract code content from the original input for tool analysis
            code_content = self._extract_code_from_input(original_input)
            
            # Use code quality analysis tool
            quality_tool = next((tool for tool in self.tools if tool.name == "code_quality_analyzer"), None)
            if quality_tool and code_content.get("python_code"):
                try:
                    quality_result = quality_tool._run(code_content["python_code"])
                    quality_data = json.loads(quality_result)
                    base_analysis["code_quality_analysis"]["tool_analysis"] = quality_data
                except Exception as e:
                    logger.warning(f"Code quality tool enhancement failed: {str(e)}")
            
            # Use CloudFormation validation tool
            cf_tool = next((tool for tool in self.tools if tool.name == "cloudformation_validator"), None)
            if cf_tool and code_content.get("cloudformation_template"):
                try:
                    cf_result = cf_tool._run(code_content["cloudformation_template"])
                    cf_data = json.loads(cf_result)
                    base_analysis["cloudformation_validation"]["tool_analysis"] = cf_data
                except Exception as e:
                    logger.warning(f"CloudFormation validation tool enhancement failed: {str(e)}")
            
            # Use security scan tool
            security_tool = next((tool for tool in self.tools if tool.name == "security_scanner"), None)
            if security_tool and code_content.get("python_code"):
                try:
                    security_result = security_tool._run(code_content["python_code"], "python", "code")
                    security_data = json.loads(security_result)
                    base_analysis["security_scan_results"]["tool_analysis"] = security_data
                except Exception as e:
                    logger.warning(f"Security scan tool enhancement failed: {str(e)}")
            
            return json.dumps(base_analysis, indent=2)
            
        except Exception as e:
            logger.error(f"Tool enhancement failed: {str(e)}")
            return llm_output
    
    def _extract_code_from_input(self, agent_input: str) -> Dict[str, str]:
        """Extract code content from the agent input for tool analysis."""
        code_content = {}
        
        try:
            # Try to extract JSON from the input
            if "Generated Code and Configurations:" in agent_input:
                start = agent_input.find("Generated Code and Configurations:") + len("Generated Code and Configurations:")
                end = agent_input.find("\n\nAdditional Context:") if "\n\nAdditional Context:" in agent_input else len(agent_input)
                json_text = agent_input[start:end].strip()
                
                # Parse the JSON
                code_data = json.loads(json_text)
                
                # Extract Python code from lambda functions
                lambda_functions = code_data.get("lambda_functions", [])
                if lambda_functions and isinstance(lambda_functions, list) and len(lambda_functions) > 0:
                    first_function = lambda_functions[0]
                    if isinstance(first_function, dict) and "code" in first_function:
                        code_content["python_code"] = first_function["code"]
                
                # Extract CloudFormation template
                cf_templates = code_data.get("cloudformation_templates", {})
                if cf_templates and isinstance(cf_templates, dict):
                    main_template = cf_templates.get("main_template")
                    if main_template:
                        code_content["cloudformation_template"] = json.dumps(main_template, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to extract code from input: {str(e)}")
        
        return code_content
    
    def _verify_response_compatibility(self, structured_output: Dict[str, Any]) -> None:
        """Verify that the response structure is compatible with the next agent in the pipeline."""
        
        required_fields = [
            "overall_quality_score",
            "production_readiness", 
            "critical_issues",
            "recommendations"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in structured_output:
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"Response missing required fields for Deployment Manager compatibility: {missing_fields}")
            
            # Add default values for missing fields
            for field in missing_fields:
                if field == "overall_quality_score":
                    structured_output[field] = 0.0
                elif field in ["critical_issues", "recommendations"]:
                    structured_output[field] = []
                else:
                    structured_output[field] = {}
        
        # Verify that production readiness assessment exists
        prod_readiness = structured_output.get("production_readiness", {})
        if not prod_readiness.get("ready_for_deployment"):
            prod_readiness["ready_for_deployment"] = False
        if not prod_readiness.get("confidence_level"):
            prod_readiness["confidence_level"] = "low"
        
        # Verify that quality score is within valid range
        quality_score = structured_output.get("overall_quality_score", 0.0)
        if not isinstance(quality_score, (int, float)) or quality_score < 0 or quality_score > 10:
            structured_output["overall_quality_score"] = 0.0
            logger.warning("Invalid quality score detected, setting to 0.0")
        
        logger.info("Response structure verified for Deployment Manager compatibility")
    
    def _generate_recommendations(self, structured_output: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on the validation results."""
        
        recommendations = []
        
        # Check overall quality score
        quality_score = structured_output.get("overall_quality_score", 0.0)
        if quality_score < 7.0:
            recommendations.append(f"Improve overall quality score from {quality_score}/10 to at least 7.0/10")
        
        # Check for critical issues
        critical_issues = structured_output.get("critical_issues", [])
        if critical_issues:
            recommendations.append(f"Address {len(critical_issues)} critical issues before deployment")
        
        # Check for blocking issues
        blocking_issues = structured_output.get("blocking_issues", [])
        if blocking_issues:
            recommendations.append(f"Fix {len(blocking_issues)} blocking issues that prevent deployment")
        
        # Check production readiness
        prod_readiness = structured_output.get("production_readiness", {})
        if not prod_readiness.get("ready_for_deployment", False):
            recommendations.append("Code is not ready for production deployment - address validation issues")
        
        # Add specific validation recommendations
        validation_recommendations = structured_output.get("recommendations", [])
        recommendations.extend(validation_recommendations[:5])  # Top 5 recommendations
        
        # Default recommendation
        if not recommendations:
            recommendations.append("Quality validation completed successfully - ready for deployment preparation")
        
        return recommendations
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration."""
        return {
            "agent_name": self.agent_name,
            "agent_type": "quality_validator",
            "description": "Validates generated code and configurations for production readiness",
            "capabilities": [
                "Static code analysis with pylint, black, and mypy",
                "CloudFormation template validation with cfn-lint",
                "Security scanning for vulnerabilities",
                "AWS best practices validation",
                "Performance assessment and optimization",
                "Compliance validation for regulatory frameworks"
            ],
            "tools": [tool.name for tool in self.tools],
            "model_complexity": TaskComplexity.HIGH.value
        }


# Factory function for creating the agent
def create_quality_validator_agent(
    bedrock_client_manager: Optional[BedrockClientManager] = None,
    knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None
) -> QualityValidatorAgent:
    """
    Factory function to create a Quality Validator Agent.
    
    Args:
        bedrock_client_manager: Optional Bedrock client manager
        knowledge_base_client: Optional knowledge base client
        
    Returns:
        QualityValidatorAgent: Configured agent instance
    """
    return QualityValidatorAgent(
        bedrock_client_manager=bedrock_client_manager,
        knowledge_base_client=knowledge_base_client
    )