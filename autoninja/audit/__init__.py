"""
AutoNinja Audit System

This package provides comprehensive auditing capabilities for the multi-agent pipeline,
including output validation, compatibility checking, and detailed reporting.
"""

from .validator import (
    AgentOutputValidator,
    SchemaValidator,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    ValidationErrorType
)

from .compatibility import (
    ContentCompatibilityChecker,
    SemanticValidationResult,
    CompatibilityLevel,
    FieldMapping
)

from .reporting import (
    ValidationReporter,
    ValidationSummary,
    CompatibilityScoring,
    RemediationPlan,
    ReportFormat
)

__all__ = [
    # Validator classes
    "AgentOutputValidator",
    "SchemaValidator",
    "ContentCompatibilityChecker",
    
    # Result classes
    "ValidationResult",
    "SemanticValidationResult",
    "ValidationSummary",
    "CompatibilityScoring",
    "RemediationPlan",
    
    # Error and data classes
    "ValidationError",
    "FieldMapping",
    
    # Enums
    "ValidationSeverity",
    "ValidationErrorType",
    "CompatibilityLevel",
    "ReportFormat",
    
    # Reporter
    "ValidationReporter"
]