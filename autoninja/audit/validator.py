"""
Agent Output Validation System

This module provides comprehensive validation for agent outputs, ensuring compatibility
between agents in the pipeline and validating output structure and content quality.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, UTC
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_core import ValidationError as PydanticValidationError

from autoninja.models.state import AgentOutput

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Validation error severity levels"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationErrorType(str, Enum):
    """Types of validation errors"""
    MISSING_FIELD = "missing_field"
    INVALID_TYPE = "invalid_type"
    INVALID_VALUE = "invalid_value"
    SCHEMA_VIOLATION = "schema_violation"
    COMPATIBILITY_ISSUE = "compatibility_issue"
    CONTENT_QUALITY = "content_quality"


@dataclass
class ValidationError:
    """Detailed validation error information"""
    field_name: str
    error_type: ValidationErrorType
    error_message: str
    severity: ValidationSeverity
    remediation_suggestion: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of validation operation"""
    is_valid: bool
    validation_errors: List[ValidationError]
    warnings: List[str]
    recommendations: List[str]
    compatibility_score: float
    quality_score: float
    metadata: Dict[str, Any]


@dataclass
class CompatibilityResult:
    """Result of compatibility checking between agents"""
    is_compatible: bool
    compatibility_score: float
    missing_fields: List[str]
    incompatible_fields: List[str]
    semantic_issues: List[str]
    recommendations: List[str]


class RequirementsAnalystSchema(BaseModel):
    """Expected schema for Requirements Analyst output"""
    extracted_requirements: Dict[str, Any] = Field(
        ..., 
        description="Extracted functional and non-functional requirements"
    )
    compliance_frameworks: List[str] = Field(
        default_factory=list,
        description="Applicable compliance frameworks"
    )
    complexity_assessment: Dict[str, Any] = Field(
        default_factory=dict,
        description="Technical complexity assessment"
    )
    structured_specifications: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured user stories and acceptance criteria"
    )
    clarification_needed: List[str] = Field(
        default_factory=list,
        description="Areas requiring clarification"
    )
    validation_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Internal validation results"
    )


class SolutionArchitectSchema(BaseModel):
    """Expected schema for Solution Architect output"""
    selected_services: List[Union[str, Dict[str, Any]]] = Field(
        ...,
        description="Selected AWS services with configuration"
    )
    architecture_blueprint: Dict[str, Any] = Field(
        ...,
        description="Complete architecture design"
    )
    security_architecture: Dict[str, Any] = Field(
        ...,
        description="Security design and IAM configuration"
    )
    iac_templates: Dict[str, Any] = Field(
        ...,
        description="Infrastructure as Code templates"
    )
    cost_estimation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cost estimation and breakdown"
    )
    integration_design: Dict[str, Any] = Field(
        default_factory=dict,
        description="API and integration design"
    )


class CodeGeneratorSchema(BaseModel):
    """Expected schema for Code Generator output"""
    bedrock_agent_config: Dict[str, Any] = Field(
        ...,
        description="Complete Bedrock Agent configuration"
    )
    action_groups: List[Dict[str, Any]] = Field(
        ...,
        description="Action group definitions with OpenAPI schemas"
    )
    lambda_functions: List[Dict[str, Any]] = Field(
        ...,
        description="Lambda function implementations"
    )
    cloudformation_templates: Dict[str, Any] = Field(
        ...,
        description="CloudFormation templates for deployment"
    )
    iam_policies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="IAM policies and roles"
    )
    deployment_scripts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Deployment automation scripts"
    )


class SchemaValidator:
    """Validates agent outputs against expected schemas"""
    
    def __init__(self):
        self.schemas = {
            "requirements_analyst": RequirementsAnalystSchema,
            "solution_architect": SolutionArchitectSchema,
            "code_generator": CodeGeneratorSchema
        }
    
    def validate_schema(self, agent_name: str, output_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate agent output against expected schema.
        
        Args:
            agent_name: Name of the agent
            output_data: Agent output data to validate
            
        Returns:
            ValidationResult: Detailed validation results
        """
        logger.info(f"Validating schema for {agent_name}")
        
        errors = []
        warnings = []
        recommendations = []
        
        # Get the appropriate schema
        schema_class = self.schemas.get(agent_name)
        if not schema_class:
            errors.append(ValidationError(
                field_name="agent_name",
                error_type=ValidationErrorType.INVALID_VALUE,
                error_message=f"Unknown agent type: {agent_name}",
                severity=ValidationSeverity.CRITICAL,
                remediation_suggestion=f"Use one of: {list(self.schemas.keys())}"
            ))
            return ValidationResult(
                is_valid=False,
                validation_errors=errors,
                warnings=warnings,
                recommendations=recommendations,
                compatibility_score=0.0,
                quality_score=0.0,
                metadata={"agent_name": agent_name, "validation_time": datetime.now(UTC).isoformat()}
            )
        
        # Validate against schema
        try:
            schema_instance = schema_class(**output_data)
            logger.info(f"Schema validation passed for {agent_name}")
        except PydanticValidationError as e:
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                errors.append(ValidationError(
                    field_name=field_path,
                    error_type=ValidationErrorType.SCHEMA_VIOLATION,
                    error_message=error["msg"],
                    severity=ValidationSeverity.ERROR,
                    remediation_suggestion=self._get_remediation_suggestion(agent_name, field_path, error),
                    context={"error_type": error["type"], "input": error.get("input")}
                ))
        
        # Perform additional validation checks
        additional_errors, additional_warnings, additional_recommendations = self._perform_additional_validation(
            agent_name, output_data
        )
        errors.extend(additional_errors)
        warnings.extend(additional_warnings)
        recommendations.extend(additional_recommendations)
        
        # Calculate scores
        compatibility_score = self._calculate_compatibility_score(agent_name, output_data, errors)
        quality_score = self._calculate_quality_score(agent_name, output_data, errors, warnings)
        
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            validation_errors=errors,
            warnings=warnings,
            recommendations=recommendations,
            compatibility_score=compatibility_score,
            quality_score=quality_score,
            metadata={
                "agent_name": agent_name,
                "validation_time": datetime.now(UTC).isoformat(),
                "schema_version": "1.0"
            }
        )
    
    def _perform_additional_validation(
        self, 
        agent_name: str, 
        output_data: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[str], List[str]]:
        """Perform additional validation beyond schema checking"""
        errors = []
        warnings = []
        recommendations = []
        
        if agent_name == "requirements_analyst":
            errors_ra, warnings_ra, recommendations_ra = self._validate_requirements_analyst_content(output_data)
            errors.extend(errors_ra)
            warnings.extend(warnings_ra)
            recommendations.extend(recommendations_ra)
        elif agent_name == "solution_architect":
            errors_sa, warnings_sa, recommendations_sa = self._validate_solution_architect_content(output_data)
            errors.extend(errors_sa)
            warnings.extend(warnings_sa)
            recommendations.extend(recommendations_sa)
        elif agent_name == "code_generator":
            errors_cg, warnings_cg, recommendations_cg = self._validate_code_generator_content(output_data)
            errors.extend(errors_cg)
            warnings.extend(warnings_cg)
            recommendations.extend(recommendations_cg)
        
        return errors, warnings, recommendations
    
    def _validate_requirements_analyst_content(
        self, 
        output_data: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[str], List[str]]:
        """Validate Requirements Analyst specific content"""
        errors = []
        warnings = []
        recommendations = []
        
        # Check extracted requirements structure
        extracted_req = output_data.get("extracted_requirements", {})
        if not extracted_req.get("functional_requirements"):
            errors.append(ValidationError(
                field_name="extracted_requirements.functional_requirements",
                error_type=ValidationErrorType.MISSING_FIELD,
                error_message="No functional requirements extracted",
                severity=ValidationSeverity.ERROR,
                remediation_suggestion="Ensure functional requirements are properly extracted from user input"
            ))
        
        # Check for non-functional requirements
        non_functional = extracted_req.get("non_functional_requirements", {})
        if not non_functional:
            warnings.append("No non-functional requirements identified - consider security, performance, scalability")
            recommendations.append("Review user request for implicit non-functional requirements")
        
        # Check complexity assessment
        complexity = output_data.get("complexity_assessment", {})
        if not complexity.get("complexity_level"):
            warnings.append("Complexity level not assessed")
            recommendations.append("Add complexity assessment to help downstream agents")
        
        return errors, warnings, recommendations
    
    def _validate_solution_architect_content(
        self, 
        output_data: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[str], List[str]]:
        """Validate Solution Architect specific content"""
        errors = []
        warnings = []
        recommendations = []
        
        # Check selected services
        services = output_data.get("selected_services", [])
        if not services:
            errors.append(ValidationError(
                field_name="selected_services",
                error_type=ValidationErrorType.MISSING_FIELD,
                error_message="No AWS services selected",
                severity=ValidationSeverity.CRITICAL,
                remediation_suggestion="Select appropriate AWS services based on requirements"
            ))
        else:
            # Check for essential services
            service_names = []
            for service in services:
                if isinstance(service, dict):
                    service_names.append(service.get("service", ""))
                else:
                    service_names.append(str(service))
            
            essential_services = ["Amazon Bedrock", "AWS Lambda"]
            for essential in essential_services:
                if not any(essential in name for name in service_names):
                    warnings.append(f"Essential service {essential} not found in selected services")
        
        # Check architecture blueprint
        blueprint = output_data.get("architecture_blueprint", {})
        if not blueprint.get("deployment_model"):
            warnings.append("Deployment model not specified in architecture blueprint")
            recommendations.append("Specify deployment model (serverless, containerized, etc.)")
        
        # Check security architecture
        security = output_data.get("security_architecture", {})
        if not security.get("iam_design"):
            warnings.append("IAM design not specified in security architecture")
            recommendations.append("Include IAM roles and policies in security design")
        
        return errors, warnings, recommendations
    
    def _validate_code_generator_content(
        self, 
        output_data: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[str], List[str]]:
        """Validate Code Generator specific content"""
        errors = []
        warnings = []
        recommendations = []
        
        # Check Bedrock agent config
        agent_config = output_data.get("bedrock_agent_config", {})
        if not agent_config.get("agent_name"):
            errors.append(ValidationError(
                field_name="bedrock_agent_config.agent_name",
                error_type=ValidationErrorType.MISSING_FIELD,
                error_message="Bedrock agent name not specified",
                severity=ValidationSeverity.ERROR,
                remediation_suggestion="Provide a valid agent name for Bedrock Agent configuration"
            ))
        
        if not agent_config.get("foundation_model"):
            errors.append(ValidationError(
                field_name="bedrock_agent_config.foundation_model",
                error_type=ValidationErrorType.MISSING_FIELD,
                error_message="Foundation model not specified",
                severity=ValidationSeverity.ERROR,
                remediation_suggestion="Specify a valid Bedrock foundation model ID"
            ))
        
        # Check action groups
        action_groups = output_data.get("action_groups", [])
        if not action_groups:
            warnings.append("No action groups defined - agent may have limited functionality")
            recommendations.append("Define action groups to provide specific capabilities to the agent")
        
        # Check Lambda functions
        lambda_functions = output_data.get("lambda_functions", [])
        if not lambda_functions:
            warnings.append("No Lambda functions defined")
            recommendations.append("Implement Lambda functions for action group handlers")
        
        # Check CloudFormation templates
        cf_templates = output_data.get("cloudformation_templates", {})
        if not cf_templates:
            warnings.append("No CloudFormation templates provided")
            recommendations.append("Include CloudFormation templates for infrastructure deployment")
        
        return errors, warnings, recommendations
    
    def _get_remediation_suggestion(
        self, 
        agent_name: str, 
        field_path: str, 
        error: Dict[str, Any]
    ) -> str:
        """Generate remediation suggestions for validation errors"""
        error_type = error.get("type", "")
        
        if error_type == "missing":
            return f"Add the required field '{field_path}' to the {agent_name} output"
        elif error_type == "type_error":
            expected_type = error.get("expected", "")
            return f"Ensure '{field_path}' is of type {expected_type}"
        elif error_type == "value_error":
            return f"Provide a valid value for '{field_path}'"
        else:
            return f"Fix the validation error for '{field_path}' in {agent_name} output"
    
    def _calculate_compatibility_score(
        self, 
        agent_name: str, 
        output_data: Dict[str, Any], 
        errors: List[ValidationError]
    ) -> float:
        """Calculate compatibility score based on validation results"""
        critical_errors = len([e for e in errors if e.severity == ValidationSeverity.CRITICAL])
        regular_errors = len([e for e in errors if e.severity == ValidationSeverity.ERROR])
        warnings = len([e for e in errors if e.severity == ValidationSeverity.WARNING])
        
        # Start with perfect score
        score = 1.0
        
        # Deduct for errors
        score -= critical_errors * 0.3
        score -= regular_errors * 0.2
        score -= warnings * 0.1
        
        return max(0.0, score)
    
    def _calculate_quality_score(
        self, 
        agent_name: str, 
        output_data: Dict[str, Any], 
        errors: List[ValidationError],
        warnings: List[str]
    ) -> float:
        """Calculate quality score based on content completeness and accuracy"""
        score = 0.0
        
        if agent_name == "requirements_analyst":
            # Check completeness of requirements extraction
            extracted_req = output_data.get("extracted_requirements", {})
            if extracted_req.get("functional_requirements"):
                score += 0.3
            if extracted_req.get("non_functional_requirements"):
                score += 0.2
            if output_data.get("complexity_assessment"):
                score += 0.2
            if output_data.get("structured_specifications"):
                score += 0.2
            if output_data.get("validation_results"):
                score += 0.1
        
        elif agent_name == "solution_architect":
            # Check completeness of architecture design
            if output_data.get("selected_services"):
                score += 0.25
            if output_data.get("architecture_blueprint"):
                score += 0.25
            if output_data.get("security_architecture"):
                score += 0.2
            if output_data.get("iac_templates"):
                score += 0.2
            if output_data.get("cost_estimation"):
                score += 0.1
        
        elif agent_name == "code_generator":
            # Check completeness of code generation
            if output_data.get("bedrock_agent_config"):
                score += 0.3
            if output_data.get("action_groups"):
                score += 0.2
            if output_data.get("lambda_functions"):
                score += 0.2
            if output_data.get("cloudformation_templates"):
                score += 0.2
            if output_data.get("iam_policies"):
                score += 0.1
        
        # Deduct for errors and warnings
        critical_errors = len([e for e in errors if e.severity == ValidationSeverity.CRITICAL])
        regular_errors = len([e for e in errors if e.severity == ValidationSeverity.ERROR])
        
        score -= critical_errors * 0.2
        score -= regular_errors * 0.1
        score -= len(warnings) * 0.05
        
        return max(0.0, min(1.0, score))


class AgentOutputValidator:
    """Main validator for agent outputs with comprehensive validation capabilities"""
    
    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.compatibility_checker = CompatibilityChecker()
    
    def validate_requirements_output(self, output: AgentOutput) -> ValidationResult:
        """Validate Requirements Analyst output"""
        return self.schema_validator.validate_schema("requirements_analyst", output.output.result)
    
    def validate_architecture_output(self, output: AgentOutput) -> ValidationResult:
        """Validate Solution Architect output"""
        return self.schema_validator.validate_schema("solution_architect", output.output.result)
    
    def validate_code_output(self, output: AgentOutput) -> ValidationResult:
        """Validate Code Generator output"""
        return self.schema_validator.validate_schema("code_generator", output.output.result)
    
    def check_pipeline_compatibility(self, outputs: List[AgentOutput]) -> CompatibilityResult:
        """Check compatibility between multiple agent outputs"""
        return self.compatibility_checker.check_compatibility(outputs)


class CompatibilityChecker:
    """Checks compatibility between agent outputs in the pipeline"""
    
    def check_compatibility(self, outputs: List[AgentOutput]) -> CompatibilityResult:
        """
        Check compatibility between agent outputs.
        
        Args:
            outputs: List of agent outputs to check compatibility
            
        Returns:
            CompatibilityResult: Compatibility assessment
        """
        logger.info(f"Checking compatibility between {len(outputs)} agent outputs")
        
        if len(outputs) < 2:
            return CompatibilityResult(
                is_compatible=True,
                compatibility_score=1.0,
                missing_fields=[],
                incompatible_fields=[],
                semantic_issues=[],
                recommendations=[]
            )
        
        missing_fields = []
        incompatible_fields = []
        semantic_issues = []
        recommendations = []
        
        # Check Requirements Analyst -> Solution Architect compatibility
        req_output = next((o for o in outputs if o.agent_name == "requirements_analyst"), None)
        arch_output = next((o for o in outputs if o.agent_name == "solution_architect"), None)
        
        if req_output and arch_output:
            missing, incompatible, semantic, recs = self._check_requirements_to_architecture(
                req_output.output.result, arch_output.output.result
            )
            missing_fields.extend(missing)
            incompatible_fields.extend(incompatible)
            semantic_issues.extend(semantic)
            recommendations.extend(recs)
        
        # Check Solution Architect -> Code Generator compatibility
        code_output = next((o for o in outputs if o.agent_name == "code_generator"), None)
        
        if arch_output and code_output:
            missing, incompatible, semantic, recs = self._check_architecture_to_code(
                arch_output.output.result, code_output.output.result
            )
            missing_fields.extend(missing)
            incompatible_fields.extend(incompatible)
            semantic_issues.extend(semantic)
            recommendations.extend(recs)
        
        # Calculate compatibility score
        total_issues = len(missing_fields) + len(incompatible_fields) + len(semantic_issues)
        compatibility_score = max(0.0, 1.0 - (total_issues * 0.1))
        
        is_compatible = total_issues == 0
        
        return CompatibilityResult(
            is_compatible=is_compatible,
            compatibility_score=compatibility_score,
            missing_fields=missing_fields,
            incompatible_fields=incompatible_fields,
            semantic_issues=semantic_issues,
            recommendations=recommendations
        )
    
    def _check_requirements_to_architecture(
        self, 
        req_data: Dict[str, Any], 
        arch_data: Dict[str, Any]
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Check compatibility from Requirements Analyst to Solution Architect"""
        missing_fields = []
        incompatible_fields = []
        semantic_issues = []
        recommendations = []
        
        # Check if requirements are addressed in architecture
        extracted_req = req_data.get("extracted_requirements", {})
        functional_req = extracted_req.get("functional_requirements", [])
        selected_services = arch_data.get("selected_services", [])
        
        if functional_req and not selected_services:
            missing_fields.append("selected_services")
            recommendations.append("Select AWS services that address the functional requirements")
        
        # Check if compliance frameworks are addressed in security architecture
        compliance_frameworks = req_data.get("compliance_frameworks", [])
        security_arch = arch_data.get("security_architecture", {})
        
        if compliance_frameworks and not security_arch:
            missing_fields.append("security_architecture")
            recommendations.append("Design security architecture to address compliance requirements")
        
        # Check complexity assessment alignment
        complexity = req_data.get("complexity_assessment", {})
        architecture_blueprint = arch_data.get("architecture_blueprint", {})
        
        if complexity.get("complexity_level") == "high" and not architecture_blueprint.get("scalability_plan"):
            semantic_issues.append("High complexity requirements not addressed with scalability planning")
            recommendations.append("Include scalability planning for high complexity requirements")
        
        return missing_fields, incompatible_fields, semantic_issues, recommendations
    
    def _check_architecture_to_code(
        self, 
        arch_data: Dict[str, Any], 
        code_data: Dict[str, Any]
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Check compatibility from Solution Architect to Code Generator"""
        missing_fields = []
        incompatible_fields = []
        semantic_issues = []
        recommendations = []
        
        # Check if selected services are implemented in code
        selected_services = arch_data.get("selected_services", [])
        bedrock_config = code_data.get("bedrock_agent_config", {})
        lambda_functions = code_data.get("lambda_functions", [])
        
        service_names = []
        for service in selected_services:
            if isinstance(service, dict):
                service_names.append(service.get("service", ""))
            else:
                service_names.append(str(service))
        
        # Check if Bedrock is configured when selected
        if any("Bedrock" in name for name in service_names) and not bedrock_config:
            missing_fields.append("bedrock_agent_config")
            recommendations.append("Implement Bedrock Agent configuration as specified in architecture")
        
        # Check if Lambda is implemented when selected
        if any("Lambda" in name for name in service_names) and not lambda_functions:
            missing_fields.append("lambda_functions")
            recommendations.append("Implement Lambda functions as specified in architecture")
        
        # Check if IAC templates match architecture
        iac_templates = arch_data.get("iac_templates", {})
        cf_templates = code_data.get("cloudformation_templates", {})
        
        if iac_templates and not cf_templates:
            missing_fields.append("cloudformation_templates")
            recommendations.append("Generate CloudFormation templates based on architecture design")
        
        # Check security architecture implementation
        security_arch = arch_data.get("security_architecture", {})
        iam_policies = code_data.get("iam_policies", [])
        
        if security_arch.get("iam_design") and not iam_policies:
            missing_fields.append("iam_policies")
            recommendations.append("Implement IAM policies based on security architecture design")
        
        return missing_fields, incompatible_fields, semantic_issues, recommendations