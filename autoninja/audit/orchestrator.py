"""
Three-Agent Orchestrator for the multi-agent pipeline.

Manages execution flow for the current three agents (Requirements Analyst,
Solution Architect, Code Generator) with proper error handling and validation.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .config import AuditConfig, ExecutionStatus, AgentStatus
from .logger import PipelineAuditLogger
from .validator import AgentOutputValidator


@dataclass
class AgentExecution:
    """Represents the execution of a single agent."""
    agent_name: str
    execution_id: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: AgentStatus = AgentStatus.NOT_STARTED
    error_message: Optional[str] = None
    execution_time_seconds: Optional[float] = None


@dataclass
class PipelineExecution:
    """Represents a complete pipeline execution."""
    session_id: str
    user_request: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    agent_executions: List[AgentExecution] = None
    final_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    
    def __post_init__(self):
        if self.agent_executions is None:
            self.agent_executions = []


class ThreeAgentOrchestrator:
    """
    Orchestrates execution of the three-agent pipeline.
    
    Manages the flow: Requirements Analyst → Solution Architect → Code Generator
    with comprehensive validation, logging, and error handling.
    """
    
    def __init__(self, config: AuditConfig):
        """Initialize the orchestrator with configuration."""
        self.config = config
        self.audit_logger = PipelineAuditLogger(config)
        self.validator = AgentOutputValidator(config)
        self.active_executions: Dict[str, PipelineExecution] = {}
    
    def execute_three_agent_pipeline(self, user_request: str, 
                                   session_id: Optional[str] = None) -> PipelineExecution:
        """
        Execute the complete three-agent pipeline.
        
        Args:
            user_request: The user's natural language request
            session_id: Optional session identifier (generated if not provided)
            
        Returns:
            PipelineExecution with complete execution details
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Initialize pipeline execution
        execution = PipelineExecution(
            session_id=session_id,
            user_request=user_request,
            start_time=datetime.now(),
            status=ExecutionStatus.IN_PROGRESS
        )
        
        self.active_executions[session_id] = execution
        self.audit_logger.log_pipeline_start(session_id, user_request)
        
        try:
            # Execute the three-agent pipeline
            self._execute_pipeline_stages(execution)
            
            # Mark as completed
            execution.end_time = datetime.now()
            execution.execution_time_seconds = (
                execution.end_time - execution.start_time
            ).total_seconds()
            execution.status = ExecutionStatus.COMPLETED
            
            self.audit_logger.log_pipeline_completion(
                session_id, 
                ExecutionStatus.COMPLETED,
                execution.execution_time_seconds,
                execution.final_output
            )
            
        except Exception as e:
            # Handle pipeline failure
            execution.end_time = datetime.now()
            execution.execution_time_seconds = (
                execution.end_time - execution.start_time
            ).total_seconds()
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            
            self.audit_logger.log_error(
                session_id,
                "PIPELINE_EXECUTION_ERROR",
                str(e),
                error_context={"user_request": user_request}
            )
            
            self.audit_logger.log_pipeline_completion(
                session_id,
                ExecutionStatus.FAILED,
                execution.execution_time_seconds
            )
        
        return execution
    
    def _execute_pipeline_stages(self, execution: PipelineExecution) -> None:
        """Execute the three pipeline stages in sequence."""
        
        # Stage 1: Requirements Analyst
        requirements_output = self._execute_requirements_analyst(
            execution.session_id,
            execution.user_request
        )
        
        # Stage 2: Solution Architect
        architecture_output = self._execute_solution_architect(
            execution.session_id,
            requirements_output
        )
        
        # Stage 3: Code Generator
        code_output = self._execute_code_generator(
            execution.session_id,
            architecture_output
        )
        
        # Set final output
        execution.final_output = code_output
    
    def _execute_requirements_analyst(self, session_id: str, 
                                    user_request: str) -> Dict[str, Any]:
        """Execute the Requirements Analyst agent."""
        execution_id = str(uuid.uuid4())
        agent_name = "requirements_analyst"
        
        # Create agent execution record
        agent_exec = AgentExecution(
            agent_name=agent_name,
            execution_id=execution_id,
            input_data={"user_request": user_request},
            start_time=datetime.now(),
            status=AgentStatus.RUNNING
        )
        
        self.active_executions[session_id].agent_executions.append(agent_exec)
        self.audit_logger.log_agent_execution_start(
            session_id, execution_id, agent_name, agent_exec.input_data
        )
        
        try:
            # TODO: Integrate with actual Requirements Analyst agent
            # For now, return mock output structure
            output = self._mock_requirements_analyst_output(user_request)
            
            # Validate output
            validation_result = self.validator.validate_requirements_output(output)
            self.audit_logger.log_validation_result(
                session_id,
                agent_name,
                "schema_validation",
                validation_result.is_valid,
                validation_result.validation_errors,
                validation_result.warnings
            )
            
            if not validation_result.is_valid and self.config.validation_enabled:
                raise ValueError(f"Requirements Analyst output validation failed: {validation_result.validation_errors}")
            
            # Complete execution
            agent_exec.end_time = datetime.now()
            agent_exec.execution_time_seconds = (
                agent_exec.end_time - agent_exec.start_time
            ).total_seconds()
            agent_exec.output_data = output
            agent_exec.status = AgentStatus.COMPLETED
            
            self.audit_logger.log_agent_execution_complete(
                session_id, execution_id, agent_name, 
                AgentStatus.COMPLETED, output, agent_exec.execution_time_seconds
            )
            
            return output
            
        except Exception as e:
            agent_exec.end_time = datetime.now()
            agent_exec.execution_time_seconds = (
                agent_exec.end_time - agent_exec.start_time
            ).total_seconds()
            agent_exec.status = AgentStatus.FAILED
            agent_exec.error_message = str(e)
            
            self.audit_logger.log_agent_execution_complete(
                session_id, execution_id, agent_name, AgentStatus.FAILED
            )
            
            raise
    
    def _execute_solution_architect(self, session_id: str, 
                                  requirements_output: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Solution Architect agent."""
        execution_id = str(uuid.uuid4())
        agent_name = "solution_architect"
        
        # Create agent execution record
        agent_exec = AgentExecution(
            agent_name=agent_name,
            execution_id=execution_id,
            input_data=requirements_output,
            start_time=datetime.now(),
            status=AgentStatus.RUNNING
        )
        
        self.active_executions[session_id].agent_executions.append(agent_exec)
        self.audit_logger.log_agent_execution_start(
            session_id, execution_id, agent_name, agent_exec.input_data
        )
        
        try:
            # TODO: Integrate with actual Solution Architect agent
            # For now, return mock output structure
            output = self._mock_solution_architect_output(requirements_output)
            
            # Validate output
            validation_result = self.validator.validate_architecture_output(output)
            self.audit_logger.log_validation_result(
                session_id,
                agent_name,
                "schema_validation",
                validation_result.is_valid,
                validation_result.validation_errors,
                validation_result.warnings
            )
            
            if not validation_result.is_valid and self.config.validation_enabled:
                raise ValueError(f"Solution Architect output validation failed: {validation_result.validation_errors}")
            
            # Complete execution
            agent_exec.end_time = datetime.now()
            agent_exec.execution_time_seconds = (
                agent_exec.end_time - agent_exec.start_time
            ).total_seconds()
            agent_exec.output_data = output
            agent_exec.status = AgentStatus.COMPLETED
            
            self.audit_logger.log_agent_execution_complete(
                session_id, execution_id, agent_name,
                AgentStatus.COMPLETED, output, agent_exec.execution_time_seconds
            )
            
            return output
            
        except Exception as e:
            agent_exec.end_time = datetime.now()
            agent_exec.execution_time_seconds = (
                agent_exec.end_time - agent_exec.start_time
            ).total_seconds()
            agent_exec.status = AgentStatus.FAILED
            agent_exec.error_message = str(e)
            
            self.audit_logger.log_agent_execution_complete(
                session_id, execution_id, agent_name, AgentStatus.FAILED
            )
            
            raise
    
    def _execute_code_generator(self, session_id: str,
                              architecture_output: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Code Generator agent."""
        execution_id = str(uuid.uuid4())
        agent_name = "code_generator"
        
        # Create agent execution record
        agent_exec = AgentExecution(
            agent_name=agent_name,
            execution_id=execution_id,
            input_data=architecture_output,
            start_time=datetime.now(),
            status=AgentStatus.RUNNING
        )
        
        self.active_executions[session_id].agent_executions.append(agent_exec)
        self.audit_logger.log_agent_execution_start(
            session_id, execution_id, agent_name, agent_exec.input_data
        )
        
        try:
            # TODO: Integrate with actual Code Generator agent
            # For now, return mock output structure
            output = self._mock_code_generator_output(architecture_output)
            
            # Validate output
            validation_result = self.validator.validate_code_output(output)
            self.audit_logger.log_validation_result(
                session_id,
                agent_name,
                "schema_validation",
                validation_result.is_valid,
                validation_result.validation_errors,
                validation_result.warnings
            )
            
            if not validation_result.is_valid and self.config.validation_enabled:
                raise ValueError(f"Code Generator output validation failed: {validation_result.validation_errors}")
            
            # Complete execution
            agent_exec.end_time = datetime.now()
            agent_exec.execution_time_seconds = (
                agent_exec.end_time - agent_exec.start_time
            ).total_seconds()
            agent_exec.output_data = output
            agent_exec.status = AgentStatus.COMPLETED
            
            self.audit_logger.log_agent_execution_complete(
                session_id, execution_id, agent_name,
                AgentStatus.COMPLETED, output, agent_exec.execution_time_seconds
            )
            
            return output
            
        except Exception as e:
            agent_exec.end_time = datetime.now()
            agent_exec.execution_time_seconds = (
                agent_exec.end_time - agent_exec.start_time
            ).total_seconds()
            agent_exec.status = AgentStatus.FAILED
            agent_exec.error_message = str(e)
            
            self.audit_logger.log_agent_execution_complete(
                session_id, execution_id, agent_name, AgentStatus.FAILED
            )
            
            raise
    
    def get_execution_status(self, session_id: str) -> Optional[PipelineExecution]:
        """Get the current execution status for a session."""
        return self.active_executions.get(session_id)
    
    def generate_audit_report(self, session_id: str) -> str:
        """Generate and save a comprehensive audit report."""
        return self.audit_logger.save_execution_report(session_id)
    
    # Mock methods for testing - these will be replaced with actual agent integrations
    def _mock_requirements_analyst_output(self, user_request: str) -> Dict[str, Any]:
        """Mock Requirements Analyst output for testing."""
        return {
            "extracted_requirements": [
                "Conversational AI capabilities",
                "Natural language understanding",
                "Context awareness and memory",
                "Personality and tone customization"
            ],
            "compliance_frameworks": ["AWS Well-Architected", "Security Best Practices"],
            "structured_specifications": {
                "functional_requirements": [
                    "Process natural language input",
                    "Generate contextual responses",
                    "Maintain conversation history",
                    "Support multiple conversation topics"
                ],
                "non_functional_requirements": [
                    "Response time < 2 seconds",
                    "99.9% availability",
                    "Secure data handling",
                    "Scalable architecture"
                ]
            }
        }
    
    def _mock_solution_architect_output(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Mock Solution Architect output for testing."""
        return {
            "selected_services": [
                "Amazon Bedrock",
                "AWS Lambda", 
                "Amazon API Gateway",
                "Amazon DynamoDB",
                "Amazon S3"
            ],
            "architecture_blueprint": {
                "compute": "AWS Lambda for serverless processing",
                "ai_service": "Amazon Bedrock for conversational AI",
                "storage": "DynamoDB for conversation history, S3 for artifacts",
                "api": "API Gateway for REST endpoints"
            },
            "security_architecture": {
                "authentication": "API Gateway with IAM",
                "encryption": "KMS for data encryption",
                "access_control": "IAM roles and policies"
            },
            "iac_templates": {
                "cloudformation": "template_structure_defined",
                "terraform": "alternative_option_available"
            }
        }
    
    def _mock_code_generator_output(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Mock Code Generator output for testing."""
        return {
            "bedrock_agent_config": {
                "agent_name": "companion-ai",
                "foundation_model": "anthropic.claude-3-sonnet-20240229-v1:0",
                "instruction": "You are a helpful AI companion that provides conversational support."
            },
            "action_groups": [
                {
                    "name": "conversation_handler",
                    "description": "Handles conversational interactions",
                    "lambda_function": "companion-ai-conversation-handler"
                }
            ],
            "lambda_functions": [
                {
                    "name": "companion-ai-conversation-handler",
                    "runtime": "python3.9",
                    "handler": "lambda_function.lambda_handler",
                    "code": "# Lambda function code would be generated here"
                }
            ],
            "cloudformation_templates": {
                "main_template": "# CloudFormation template would be generated here",
                "parameters": ["AgentName", "BedrockModel", "Environment"]
            }
        }