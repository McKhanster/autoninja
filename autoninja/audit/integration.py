"""
Audit System Integration

This module provides a unified interface for the complete audit system,
integrating schema validation, compatibility checking, and reporting.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC

from autoninja.models.state import AgentOutput
from autoninja.audit.validator import AgentOutputValidator, ValidationResult
from autoninja.audit.compatibility import ContentCompatibilityChecker, SemanticValidationResult
from autoninja.audit.reporting import ValidationReporter, ReportFormat

logger = logging.getLogger(__name__)


class ComprehensiveAuditSystem:
    """
    Unified audit system that integrates all validation components.
    
    This class provides a single interface for:
    - Schema validation of agent outputs
    - Compatibility checking between agents
    - Comprehensive reporting and remediation recommendations
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the comprehensive audit system.
        
        Args:
            output_dir: Directory for saving audit reports
        """
        self.validator = AgentOutputValidator()
        self.compatibility_checker = ContentCompatibilityChecker()
        self.reporter = ValidationReporter(output_dir)
        
        logger.info("Comprehensive Audit System initialized")
    
    def audit_agent_outputs(
        self,
        agent_outputs: Dict[str, AgentOutput],
        session_id: str,
        generate_report: bool = True,
        report_format: ReportFormat = ReportFormat.JSON
    ) -> Dict[str, Any]:
        """
        Perform comprehensive audit of agent outputs.
        
        Args:
            agent_outputs: Dictionary of agent outputs to audit
            session_id: Session identifier for tracking
            generate_report: Whether to generate a detailed report
            report_format: Format for the generated report
            
        Returns:
            Dict containing complete audit results
        """
        logger.info(f"Starting comprehensive audit for session {session_id}")
        
        audit_start_time = datetime.now(UTC)
        
        # Step 1: Validate individual agent outputs
        validation_results = self._validate_individual_agents(agent_outputs)
        
        # Step 2: Check compatibility between agents
        compatibility_results = self._check_agent_compatibility(agent_outputs)
        
        # Step 3: Generate comprehensive report if requested
        report = None
        if generate_report:
            report = self.reporter.generate_comprehensive_report(
                validation_results=validation_results,
                compatibility_results=compatibility_results,
                agent_outputs=agent_outputs,
                session_id=session_id,
                report_format=report_format
            )
        
        audit_end_time = datetime.now(UTC)
        audit_duration = (audit_end_time - audit_start_time).total_seconds()
        
        # Compile audit results
        audit_results = {
            "session_id": session_id,
            "audit_metadata": {
                "audit_start_time": audit_start_time.isoformat(),
                "audit_end_time": audit_end_time.isoformat(),
                "audit_duration_seconds": audit_duration,
                "agents_audited": list(agent_outputs.keys()),
                "audit_version": "1.0"
            },
            "validation_results": {
                agent_name: self._serialize_validation_result(result)
                for agent_name, result in validation_results.items()
            },
            "compatibility_results": {
                pair_name: self._serialize_compatibility_result(result)
                for pair_name, result in compatibility_results.items()
            },
            "audit_summary": self._generate_audit_summary(validation_results, compatibility_results),
            "report": report
        }
        
        logger.info(f"Comprehensive audit completed for session {session_id} in {audit_duration:.2f} seconds")
        
        return audit_results
    
    def validate_pipeline_flow(
        self,
        requirements_output: AgentOutput,
        architecture_output: AgentOutput,
        code_output: AgentOutput,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Validate the complete pipeline flow from requirements to code.
        
        Args:
            requirements_output: Requirements Analyst output
            architecture_output: Solution Architect output
            code_output: Code Generator output
            session_id: Session identifier
            
        Returns:
            Dict containing pipeline validation results
        """
        logger.info(f"Validating complete pipeline flow for session {session_id}")
        
        agent_outputs = {
            "requirements_analyst": requirements_output,
            "solution_architect": architecture_output,
            "code_generator": code_output
        }
        
        return self.audit_agent_outputs(agent_outputs, session_id)
    
    def quick_validation_check(
        self,
        agent_outputs: Dict[str, AgentOutput]
    ) -> Tuple[bool, List[str]]:
        """
        Perform quick validation check without detailed reporting.
        
        Args:
            agent_outputs: Dictionary of agent outputs to check
            
        Returns:
            Tuple of (is_valid, list_of_critical_issues)
        """
        logger.info("Performing quick validation check")
        
        critical_issues = []
        
        # Quick schema validation
        for agent_name, output in agent_outputs.items():
            if agent_name == "requirements_analyst":
                result = self.validator.validate_requirements_output(output)
            elif agent_name == "solution_architect":
                result = self.validator.validate_architecture_output(output)
            elif agent_name == "code_generator":
                result = self.validator.validate_code_output(output)
            else:
                continue
            
            if not result.is_valid:
                critical_errors = [
                    error.error_message for error in result.validation_errors
                    if error.severity.value in ["critical", "error"]
                ]
                critical_issues.extend(critical_errors)
        
        # Quick compatibility check
        if len(agent_outputs) >= 2:
            outputs_list = list(agent_outputs.values())
            compatibility_result = self.validator.check_pipeline_compatibility(outputs_list)
            
            if not compatibility_result.is_compatible:
                critical_issues.extend(compatibility_result.semantic_issues)
        
        is_valid = len(critical_issues) == 0
        
        return is_valid, critical_issues
    
    def _validate_individual_agents(
        self,
        agent_outputs: Dict[str, AgentOutput]
    ) -> Dict[str, ValidationResult]:
        """Validate individual agent outputs"""
        logger.info("Validating individual agent outputs")
        
        validation_results = {}
        
        for agent_name, output in agent_outputs.items():
            try:
                if agent_name == "requirements_analyst":
                    result = self.validator.validate_requirements_output(output)
                elif agent_name == "solution_architect":
                    result = self.validator.validate_architecture_output(output)
                elif agent_name == "code_generator":
                    result = self.validator.validate_code_output(output)
                else:
                    logger.warning(f"Unknown agent type for validation: {agent_name}")
                    continue
                
                validation_results[agent_name] = result
                logger.info(f"Validation completed for {agent_name}: {'PASSED' if result.is_valid else 'FAILED'}")
                
            except Exception as e:
                logger.error(f"Error validating {agent_name}: {str(e)}")
                # Create a failed validation result
                from autoninja.audit.validator import ValidationError, ValidationSeverity, ValidationErrorType
                error = ValidationError(
                    field_name="validation_system",
                    error_type=ValidationErrorType.SCHEMA_VIOLATION,
                    error_message=f"Validation system error: {str(e)}",
                    severity=ValidationSeverity.CRITICAL,
                    remediation_suggestion="Check agent output format and validation system"
                )
                validation_results[agent_name] = ValidationResult(
                    is_valid=False,
                    validation_errors=[error],
                    warnings=[],
                    recommendations=["Fix validation system error"],
                    compatibility_score=0.0,
                    quality_score=0.0,
                    metadata={"error": str(e)}
                )
        
        return validation_results
    
    def _check_agent_compatibility(
        self,
        agent_outputs: Dict[str, AgentOutput]
    ) -> Dict[str, SemanticValidationResult]:
        """Check compatibility between agent outputs"""
        logger.info("Checking agent compatibility")
        
        compatibility_results = {}
        
        # Check requirements to architecture compatibility
        req_output = agent_outputs.get("requirements_analyst")
        arch_output = agent_outputs.get("solution_architect")
        
        if req_output and arch_output:
            try:
                result = self.compatibility_checker.verify_requirements_to_architecture_compatibility(
                    req_output.output.result,
                    arch_output.output.result
                )
                compatibility_results["requirements_to_architecture"] = result
                logger.info(f"Requirements to Architecture compatibility: {'PASSED' if result.is_valid else 'FAILED'}")
            except Exception as e:
                logger.error(f"Error checking requirements to architecture compatibility: {str(e)}")
        
        # Check architecture to code compatibility
        code_output = agent_outputs.get("code_generator")
        
        if arch_output and code_output:
            try:
                result = self.compatibility_checker.verify_architecture_to_code_compatibility(
                    arch_output.output.result,
                    code_output.output.result
                )
                compatibility_results["architecture_to_code"] = result
                logger.info(f"Architecture to Code compatibility: {'PASSED' if result.is_valid else 'FAILED'}")
            except Exception as e:
                logger.error(f"Error checking architecture to code compatibility: {str(e)}")
        
        # Check overall semantic flow if all three agents are present
        if req_output and arch_output and code_output:
            try:
                result = self.compatibility_checker.validate_semantic_data_flow(
                    req_output.output.result,
                    arch_output.output.result,
                    code_output.output.result
                )
                compatibility_results["overall_semantic_flow"] = result
                logger.info(f"Overall semantic flow: {'PASSED' if result.is_valid else 'FAILED'}")
            except Exception as e:
                logger.error(f"Error checking overall semantic flow: {str(e)}")
        
        return compatibility_results
    
    def _generate_audit_summary(
        self,
        validation_results: Dict[str, ValidationResult],
        compatibility_results: Dict[str, SemanticValidationResult]
    ) -> Dict[str, Any]:
        """Generate audit summary"""
        total_agents = len(validation_results)
        passed_agents = sum(1 for result in validation_results.values() if result.is_valid)
        failed_agents = total_agents - passed_agents
        
        total_errors = sum(len(result.validation_errors) for result in validation_results.values())
        total_warnings = sum(len(result.warnings) for result in validation_results.values())
        
        # Calculate average scores
        quality_scores = [result.quality_score for result in validation_results.values()]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        compatibility_scores = [result.data_flow_score for result in compatibility_results.values()]
        avg_compatibility_score = sum(compatibility_scores) / len(compatibility_scores) if compatibility_scores else 0.0
        
        # Determine overall status
        overall_status = "PASSED" if failed_agents == 0 and total_errors == 0 else "FAILED"
        
        return {
            "overall_status": overall_status,
            "agents_summary": {
                "total": total_agents,
                "passed": passed_agents,
                "failed": failed_agents
            },
            "issues_summary": {
                "total_errors": total_errors,
                "total_warnings": total_warnings
            },
            "scores": {
                "average_quality_score": avg_quality_score,
                "average_compatibility_score": avg_compatibility_score
            },
            "compatibility_checks": len(compatibility_results),
            "recommendations_available": any(
                result.recommendations for result in validation_results.values()
            ) or any(
                result.recommendations for result in compatibility_results.values()
            )
        }
    
    def _serialize_validation_result(self, result: ValidationResult) -> Dict[str, Any]:
        """Serialize ValidationResult for JSON output"""
        return {
            "is_valid": result.is_valid,
            "validation_errors": [
                {
                    "field_name": error.field_name,
                    "error_type": error.error_type.value,
                    "error_message": error.error_message,
                    "severity": error.severity.value,
                    "remediation_suggestion": error.remediation_suggestion,
                    "context": error.context
                }
                for error in result.validation_errors
            ],
            "warnings": result.warnings,
            "recommendations": result.recommendations,
            "compatibility_score": result.compatibility_score,
            "quality_score": result.quality_score,
            "metadata": result.metadata
        }
    
    def _serialize_compatibility_result(self, result: SemanticValidationResult) -> Dict[str, Any]:
        """Serialize SemanticValidationResult for JSON output"""
        return {
            "is_valid": result.is_valid,
            "compatibility_level": result.compatibility_level.value,
            "missing_mappings": [
                {
                    "source_agent": mapping.source_agent,
                    "source_field": mapping.source_field,
                    "target_agent": mapping.target_agent,
                    "target_field": mapping.target_field,
                    "required": mapping.required,
                    "description": mapping.description
                }
                for mapping in result.missing_mappings
            ],
            "invalid_mappings": [
                {
                    "source_agent": mapping.source_agent,
                    "source_field": mapping.source_field,
                    "target_agent": mapping.target_agent,
                    "target_field": mapping.target_field,
                    "required": mapping.required,
                    "description": mapping.description
                }
                for mapping in result.invalid_mappings
            ],
            "semantic_issues": result.semantic_issues,
            "data_flow_score": result.data_flow_score,
            "recommendations": result.recommendations,
            "metadata": result.metadata
        }


# Convenience function for quick auditing
def audit_agent_pipeline(
    agent_outputs: Dict[str, AgentOutput],
    session_id: str,
    output_dir: Optional[str] = None,
    generate_report: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for auditing agent pipeline.
    
    Args:
        agent_outputs: Dictionary of agent outputs to audit
        session_id: Session identifier
        output_dir: Directory for saving reports
        generate_report: Whether to generate detailed report
        
    Returns:
        Dict containing audit results
    """
    audit_system = ComprehensiveAuditSystem(output_dir)
    return audit_system.audit_agent_outputs(
        agent_outputs=agent_outputs,
        session_id=session_id,
        generate_report=generate_report
    )