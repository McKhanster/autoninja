"""
AutoNinja State Models and Schemas

This module defines the core state models used throughout the AutoNinja system,
including LangGraph state management, DynamoDB persistence models, and agent
output schemas with validation.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class AgentType(str, Enum):
    """Supported agent types for generation"""
    CONVERSATIONAL = "conversational"
    ANALYTICAL = "analytical"
    AUTOMATION = "automation"
    CUSTOM = "custom"


class GenerationStage(str, Enum):
    """Current stage in the agent generation pipeline"""
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    GENERATION = "generation"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"


class SessionStatus(str, Enum):
    """Session status values"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# LangGraph State Management Models
class AutoNinjaState(TypedDict):
    """
    Main state model for LangGraph workflow orchestration.
    
    This TypedDict defines the complete state structure that flows through
    the LangGraph workflow, maintaining all necessary data for agent generation.
    """
    # Core session information
    user_request: str
    session_id: str
    
    # Agent outputs from each stage
    requirements: Dict[str, Any]
    architecture: Dict[str, Any]
    generated_code: Dict[str, Any]
    validation_results: Dict[str, Any]
    deployment_config: Dict[str, Any]
    final_artifacts: Dict[str, Any]
    
    # Workflow control
    current_step: str
    errors: List[str]
    
    # Metadata
    generation_metadata: Dict[str, Any]


# Pydantic Models for Validation and Serialization
class UserRequestSpecifications(BaseModel):
    """User request specifications with validation"""
    agent_name: str = Field(..., min_length=1, max_length=100)
    agent_type: AgentType
    description: str = Field(..., min_length=10, max_length=2000)
    
    class Requirements(BaseModel):
        functional: List[str] = Field(default_factory=list)
        non_functional: Dict[str, Any] = Field(default_factory=dict)
    
    class TargetPlatform(BaseModel):
        deployment: str = Field(default="bedrock-agent")
        language: str = Field(default="python")
        framework: Optional[str] = None
    
    class Constraints(BaseModel):
        budget: Optional[str] = None
        timeline: Optional[str] = None
    
    requirements: Requirements = Field(default_factory=Requirements)
    target_platform: TargetPlatform = Field(default_factory=TargetPlatform)
    integrations: List[str] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)


class UserRequest(BaseModel):
    """Complete user request model"""
    request_type: str = Field(default="generate_agent")
    specifications: UserRequestSpecifications


class AgentOutput(BaseModel):
    """Standard output schema for all specialist agents"""
    agent_name: str
    execution_id: str
    input_data: Dict[str, Any]
    
    class Output(BaseModel):
        result: Dict[str, Any]
        confidence_score: float = Field(ge=0.0, le=1.0)
        reasoning: str
        recommendations: List[str] = Field(default_factory=list)
    
    class ExecutionMetadata(BaseModel):
        start_time: datetime
        end_time: Optional[datetime] = None
        duration_seconds: Optional[float] = None
        model_invocations: int = Field(default=0)
        tokens_used: int = Field(default=0)
    
    class TraceData(BaseModel):
        trace_id: str
        steps: List[Dict[str, Any]] = Field(default_factory=list)
    
    output: Output
    execution_metadata: ExecutionMetadata
    trace_data: TraceData


class ValidationResults(BaseModel):
    """Quality validation results schema"""
    code_quality_score: float = Field(ge=0.0, le=100.0)
    security_score: float = Field(ge=0.0, le=100.0)
    compliance_checks: str
    performance_estimate: Dict[str, Any] = Field(default_factory=dict)
    
    class QualityMetrics(BaseModel):
        pylint_score: Optional[float] = None
        black_compliant: Optional[bool] = None
        mypy_errors: List[str] = Field(default_factory=list)
        security_warnings: List[str] = Field(default_factory=list)
    
    quality_metrics: QualityMetrics = Field(default_factory=QualityMetrics)


class ArtifactsLocation(BaseModel):
    """S3 artifact storage locations"""
    source_code: Optional[str] = None
    infrastructure: Optional[str] = None
    documentation: Optional[str] = None
    deployment_package: Optional[str] = None
    
    @validator('*', pre=True)
    def validate_s3_path(cls, v):
        if v and not v.startswith('s3://'):
            raise ValueError('Artifact paths must be valid S3 URIs')
        return v


class GenerationMetadata(BaseModel):
    """Metadata for the generation process"""
    start_time: datetime
    end_time: Optional[datetime] = None
    generation_time_seconds: Optional[float] = None
    bedrock_invocations: int = Field(default=0)
    total_cost: Optional[float] = None
    
    class CostBreakdown(BaseModel):
        bedrock_model_cost: float = Field(default=0.0)
        knowledge_base_cost: float = Field(default=0.0)
        storage_cost: float = Field(default=0.0)
        compute_cost: float = Field(default=0.0)
    
    cost_breakdown: CostBreakdown = Field(default_factory=CostBreakdown)


# DynamoDB Session State Model
class SessionState(BaseModel):
    """
    Complete session state model for DynamoDB persistence.
    
    This model represents the full state of an agent generation session
    that is persisted in DynamoDB for recovery and tracking purposes.
    """
    # Primary key
    session_id: str = Field(..., description="Unique session identifier")
    
    # User request data
    user_request: UserRequest
    
    # Current workflow state
    current_stage: GenerationStage
    status: SessionStatus
    
    # Agent outputs
    agent_outputs: Dict[str, AgentOutput] = Field(default_factory=dict)
    
    # Validation and artifacts
    validation_results: Optional[ValidationResults] = None
    artifacts_location: ArtifactsLocation = Field(default_factory=ArtifactsLocation)
    
    # Metadata and tracking
    generation_metadata: GenerationMetadata
    
    # Error handling
    error_details: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow()
    
    def add_agent_output(self, agent_name: str, output: AgentOutput):
        """Add output from a specialist agent"""
        self.agent_outputs[agent_name] = output
        self.update_timestamp()
    
    def set_stage(self, stage: GenerationStage):
        """Update the current generation stage"""
        self.current_stage = stage
        self.update_timestamp()
    
    def set_status(self, status: SessionStatus):
        """Update the session status"""
        self.status = status
        self.update_timestamp()
    
    def add_error(self, error_type: str, error_message: str, error_details: Dict[str, Any] = None):
        """Add error information to the session"""
        self.error_details[error_type] = {
            "message": error_message,
            "details": error_details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.retry_count += 1
        self.update_timestamp()


# Specialized Agent State Models
class RequirementsAnalystOutput(BaseModel):
    """Output schema for Requirements Analyst Agent"""
    extracted_requirements: Dict[str, Any]
    compliance_frameworks: List[str]
    complexity_assessment: Dict[str, Any]
    structured_specifications: Dict[str, Any]
    clarification_needed: List[str] = Field(default_factory=list)


class SolutionArchitectOutput(BaseModel):
    """Output schema for Solution Architect Agent"""
    selected_services: List[str]
    architecture_blueprint: Dict[str, Any]
    security_architecture: Dict[str, Any]
    cost_estimation: Dict[str, Any]
    iac_templates: Dict[str, str]
    integration_design: Dict[str, Any]


class CodeGeneratorOutput(BaseModel):
    """Output schema for Code Generator Agent"""
    generated_code: Dict[str, str]  # filename -> code content
    configuration_files: Dict[str, str]
    api_specifications: Dict[str, Any]
    integration_code: Dict[str, str]
    documentation: Dict[str, str]


class QualityValidatorOutput(BaseModel):
    """Output schema for Quality Validator Agent"""
    validation_results: ValidationResults
    quality_report: Dict[str, Any]
    security_assessment: Dict[str, Any]
    performance_analysis: Dict[str, Any]
    compliance_validation: Dict[str, Any]
    remediation_suggestions: List[str]


class DeploymentManagerOutput(BaseModel):
    """Output schema for Deployment Manager Agent"""
    deployment_package: Dict[str, Any]
    cicd_configuration: Dict[str, Any]
    monitoring_setup: Dict[str, Any]
    operational_documentation: Dict[str, str]
    cost_projections: Dict[str, Any]
    deployment_instructions: List[str]


# State Conversion Utilities
class StateConverter:
    """Utilities for converting between different state representations"""
    
    @staticmethod
    def session_to_langgraph_state(session: SessionState) -> AutoNinjaState:
        """Convert SessionState to AutoNinjaState for LangGraph"""
        return AutoNinjaState(
            user_request=session.user_request.specifications.description,
            session_id=session.session_id,
            requirements=session.agent_outputs.get("requirements_analyst", {}).dict() if "requirements_analyst" in session.agent_outputs else {},
            architecture=session.agent_outputs.get("solution_architect", {}).dict() if "solution_architect" in session.agent_outputs else {},
            generated_code=session.agent_outputs.get("code_generator", {}).dict() if "code_generator" in session.agent_outputs else {},
            validation_results=session.validation_results.dict() if session.validation_results else {},
            deployment_config=session.agent_outputs.get("deployment_manager", {}).dict() if "deployment_manager" in session.agent_outputs else {},
            final_artifacts=session.artifacts_location.dict(),
            current_step=session.current_stage.value,
            errors=[error["message"] for error in session.error_details.values()],
            generation_metadata=session.generation_metadata.dict()
        )
    
    @staticmethod
    def langgraph_to_session_state(state: AutoNinjaState, session_id: str) -> SessionState:
        """Convert AutoNinjaState back to SessionState for persistence"""
        # This is a simplified conversion - in practice, you'd need more sophisticated mapping
        user_request = UserRequest(
            specifications=UserRequestSpecifications(
                agent_name="Generated Agent",
                agent_type=AgentType.CUSTOM,
                description=state["user_request"]
            )
        )
        
        return SessionState(
            session_id=session_id,
            user_request=user_request,
            current_stage=GenerationStage(state["current_step"]),
            status=SessionStatus.IN_PROGRESS,
            generation_metadata=GenerationMetadata(**state["generation_metadata"]),
            artifacts_location=ArtifactsLocation(**state["final_artifacts"])
        )


# Validation Functions
def validate_agent_output(agent_name: str, output_data: Dict[str, Any]) -> AgentOutput:
    """Validate and create AgentOutput instance"""
    try:
        return AgentOutput(**output_data)
    except Exception as e:
        raise ValueError(f"Invalid output format for agent {agent_name}: {str(e)}")


def validate_session_state(state_data: Dict[str, Any]) -> SessionState:
    """Validate and create SessionState instance"""
    try:
        return SessionState(**state_data)
    except Exception as e:
        raise ValueError(f"Invalid session state format: {str(e)}")