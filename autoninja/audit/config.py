"""
Configuration management for the audit system.

Provides centralized configuration for audit operations, validation rules,
logging settings, and performance monitoring parameters.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class LogLevel(str, Enum):
    """Supported logging levels for audit operations."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ExecutionStatus(str, Enum):
    """Pipeline execution status values."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Individual agent execution status values."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AuditConfig(BaseModel):
    """Main configuration for the audit system."""
    
    # Pipeline execution settings
    agent_timeout_seconds: int = Field(default=300, description="Timeout for individual agent execution")
    max_retries: int = Field(default=3, description="Maximum retry attempts for failed operations")
    pipeline_timeout_seconds: int = Field(default=1800, description="Total pipeline timeout")
    
    # Validation settings
    validation_enabled: bool = Field(default=True, description="Enable output validation")
    strict_schema_validation: bool = Field(default=True, description="Enforce strict schema validation")
    content_validation_enabled: bool = Field(default=True, description="Enable semantic content validation")
    compatibility_threshold: float = Field(default=0.8, description="Minimum compatibility score threshold")
    
    # Quality assessment settings
    quality_assessment_enabled: bool = Field(default=True, description="Enable quality assessment")
    minimum_quality_threshold: float = Field(default=0.7, description="Minimum quality score threshold")
    completeness_weight: float = Field(default=0.3, description="Weight for completeness in quality scoring")
    accuracy_weight: float = Field(default=0.4, description="Weight for accuracy in quality scoring")
    appropriateness_weight: float = Field(default=0.3, description="Weight for appropriateness in quality scoring")
    
    # Performance monitoring settings
    performance_monitoring_enabled: bool = Field(default=True, description="Enable performance monitoring")
    performance_alert_threshold_seconds: float = Field(default=120.0, description="Alert threshold for slow operations")
    memory_alert_threshold_mb: float = Field(default=512.0, description="Alert threshold for high memory usage")
    
    # Logging configuration
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level for audit operations")
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_to_console: bool = Field(default=True, description="Enable console logging")
    audit_log_file: str = Field(default="logs/audit.log", description="Audit log file path")
    execution_log_file: str = Field(default="logs/execution.log", description="Execution log file path")
    
    # Required fields by agent for validation
    required_fields_by_agent: Dict[str, List[str]] = Field(
        default={
            "requirements_analyst": [
                "extracted_requirements",
                "compliance_frameworks", 
                "structured_specifications"
            ],
            "solution_architect": [
                "selected_services",
                "architecture_blueprint",
                "security_architecture",
                "iac_templates"
            ],
            "code_generator": [
                "bedrock_agent_config",
                "action_groups",
                "lambda_functions",
                "cloudformation_templates"
            ]
        },
        description="Required output fields for each agent type"
    )
    
    # Demo and testing configuration
    demo_scenarios_enabled: bool = Field(default=True, description="Enable demo scenario testing")
    companion_ai_demo_enabled: bool = Field(default=True, description="Enable companion AI demo scenario")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True


class ValidationConfig(BaseModel):
    """Specific configuration for output validation."""
    
    # Schema validation settings
    enforce_required_fields: bool = Field(default=True, description="Enforce presence of required fields")
    allow_additional_fields: bool = Field(default=True, description="Allow additional fields beyond schema")
    validate_field_types: bool = Field(default=True, description="Validate field data types")
    
    # Content validation settings
    check_semantic_consistency: bool = Field(default=True, description="Check semantic consistency between agents")
    validate_data_flow: bool = Field(default=True, description="Validate logical data flow between agents")
    check_completeness: bool = Field(default=True, description="Check output completeness")
    
    # Compatibility settings
    compatibility_check_enabled: bool = Field(default=True, description="Enable compatibility checking")
    compatibility_score_threshold: float = Field(default=0.8, description="Minimum compatibility score")
    
    # Error handling
    fail_on_validation_error: bool = Field(default=False, description="Fail pipeline on validation errors")
    log_validation_warnings: bool = Field(default=True, description="Log validation warnings")


class PerformanceConfig(BaseModel):
    """Configuration for performance monitoring."""
    
    # Monitoring settings
    collect_execution_metrics: bool = Field(default=True, description="Collect execution time metrics")
    collect_memory_metrics: bool = Field(default=True, description="Collect memory usage metrics")
    collect_bedrock_metrics: bool = Field(default=True, description="Collect Bedrock API metrics")
    
    # Alert thresholds
    slow_execution_threshold_seconds: float = Field(default=60.0, description="Threshold for slow execution alerts")
    high_memory_threshold_mb: float = Field(default=256.0, description="Threshold for high memory alerts")
    high_token_usage_threshold: int = Field(default=10000, description="Threshold for high token usage alerts")
    
    # Trend analysis
    enable_trend_analysis: bool = Field(default=True, description="Enable performance trend analysis")
    trend_analysis_window_hours: int = Field(default=24, description="Time window for trend analysis")


def load_audit_config() -> AuditConfig:
    """Load audit configuration from environment variables and defaults."""
    import os
    
    config_data = {}
    
    # Load from environment variables with AUDIT_ prefix
    for key, value in os.environ.items():
        if key.startswith("AUDIT_"):
            config_key = key[6:].lower()  # Remove AUDIT_ prefix and lowercase
            config_data[config_key] = value
    
    return AuditConfig(**config_data)