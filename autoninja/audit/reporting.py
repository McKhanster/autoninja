"""
Validation Reporting System

This module provides detailed validation error reporting, compatibility scoring,
and remediation recommendations for agent output validation failures.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from autoninja.audit.validator import ValidationResult, ValidationError, ValidationSeverity
from autoninja.audit.compatibility import SemanticValidationResult, CompatibilityLevel
from autoninja.models.state import AgentOutput

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Available report formats"""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"


@dataclass
class ValidationSummary:
    """Summary of validation results across all agents"""
    total_agents_validated: int
    agents_passed: int
    agents_failed: int
    total_errors: int
    total_warnings: int
    overall_compatibility_score: float
    overall_quality_score: float
    validation_timestamp: str
    recommendations_count: int


@dataclass
class CompatibilityScoring:
    """Detailed compatibility scoring between agent pairs"""
    requirements_to_architecture_score: float
    architecture_to_code_score: float
    overall_pipeline_score: float
    compatibility_level: CompatibilityLevel
    critical_issues: List[str]
    improvement_areas: List[str]


@dataclass
class RemediationPlan:
    """Comprehensive remediation plan for validation failures"""
    priority_fixes: List[Dict[str, Any]]
    optional_improvements: List[Dict[str, Any]]
    estimated_effort: str
    implementation_order: List[str]
    success_criteria: List[str]


class ValidationReporter:
    """
    Generates comprehensive validation reports with detailed error analysis,
    compatibility scoring, and remediation recommendations.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default to tests/outputs for test reports, or audit_reports for production
            if "test" in str(Path.cwd()).lower():
                self.output_dir = Path("tests/outputs/audit_reports")
            else:
                self.output_dir = Path("audit_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comprehensive_report(
        self,
        validation_results: Dict[str, ValidationResult],
        compatibility_results: Dict[str, SemanticValidationResult],
        agent_outputs: Dict[str, AgentOutput],
        session_id: str,
        report_format: ReportFormat = ReportFormat.JSON
    ) -> Dict[str, Any]:
        """
        Generate comprehensive validation report.
        
        Args:
            validation_results: Validation results for each agent
            compatibility_results: Compatibility results between agents
            agent_outputs: Original agent outputs
            session_id: Session identifier
            report_format: Desired report format
            
        Returns:
            Dict containing the complete report
        """
        logger.info(f"Generating comprehensive validation report for session {session_id}")
        
        # Generate report components
        summary = self._generate_validation_summary(validation_results, compatibility_results)
        detailed_errors = self._generate_detailed_error_report(validation_results)
        compatibility_scoring = self._generate_compatibility_scoring(compatibility_results)
        remediation_plan = self._generate_remediation_plan(validation_results, compatibility_results)
        agent_analysis = self._generate_agent_analysis(validation_results, agent_outputs)
        
        # Compile complete report
        report = {
            "report_metadata": {
                "session_id": session_id,
                "report_timestamp": datetime.now(UTC).isoformat(),
                "report_version": "1.0",
                "report_format": report_format.value
            },
            "validation_summary": asdict(summary),
            "detailed_errors": detailed_errors,
            "compatibility_scoring": asdict(compatibility_scoring),
            "remediation_plan": asdict(remediation_plan),
            "agent_analysis": agent_analysis,
            "recommendations": self._generate_overall_recommendations(
                validation_results, compatibility_results
            )
        }
        
        # Save report to file
        self._save_report(report, session_id, report_format)
        
        return report
    
    def generate_field_level_error_report(
        self,
        validation_results: Dict[str, ValidationResult]
    ) -> Dict[str, Any]:
        """
        Generate detailed field-level error report.
        
        Args:
            validation_results: Validation results for each agent
            
        Returns:
            Dict containing field-level error analysis
        """
        logger.info("Generating field-level error report")
        
        field_errors = {}
        error_patterns = {}
        severity_breakdown = {
            "critical": 0,
            "error": 0,
            "warning": 0,
            "info": 0
        }
        
        for agent_name, result in validation_results.items():
            agent_field_errors = []
            
            for error in result.validation_errors:
                error_info = {
                    "field_name": error.field_name,
                    "error_type": error.error_type.value,
                    "error_message": error.error_message,
                    "severity": error.severity.value,
                    "remediation_suggestion": error.remediation_suggestion,
                    "context": error.context or {}
                }
                agent_field_errors.append(error_info)
                
                # Track error patterns
                error_key = f"{error.error_type.value}_{error.field_name}"
                if error_key not in error_patterns:
                    error_patterns[error_key] = {
                        "count": 0,
                        "agents": [],
                        "common_remediation": error.remediation_suggestion
                    }
                error_patterns[error_key]["count"] += 1
                error_patterns[error_key]["agents"].append(agent_name)
                
                # Track severity breakdown
                severity_breakdown[error.severity.value] += 1
            
            field_errors[agent_name] = agent_field_errors
        
        return {
            "field_errors_by_agent": field_errors,
            "error_patterns": error_patterns,
            "severity_breakdown": severity_breakdown,
            "total_field_errors": sum(severity_breakdown.values()),
            "most_common_errors": sorted(
                error_patterns.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:10]
        }
    
    def create_compatibility_scoring_system(
        self,
        compatibility_results: Dict[str, SemanticValidationResult]
    ) -> Dict[str, Any]:
        """
        Create detailed compatibility scoring system.
        
        Args:
            compatibility_results: Compatibility results between agents
            
        Returns:
            Dict containing compatibility scoring analysis
        """
        logger.info("Creating compatibility scoring system")
        
        scores = {}
        overall_scores = []
        compatibility_levels = []
        
        for pair_name, result in compatibility_results.items():
            score_details = {
                "data_flow_score": result.data_flow_score,
                "compatibility_level": result.compatibility_level.value,
                "missing_mappings_count": len(result.missing_mappings),
                "invalid_mappings_count": len(result.invalid_mappings),
                "semantic_issues_count": len(result.semantic_issues),
                "is_valid": result.is_valid,
                "improvement_potential": 1.0 - result.data_flow_score
            }
            scores[pair_name] = score_details
            overall_scores.append(result.data_flow_score)
            compatibility_levels.append(result.compatibility_level.value)
        
        # Calculate aggregate metrics
        average_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
        min_score = min(overall_scores) if overall_scores else 0.0
        max_score = max(overall_scores) if overall_scores else 0.0
        
        # Determine overall compatibility level
        if average_score >= 0.9:
            overall_level = CompatibilityLevel.EXCELLENT
        elif average_score >= 0.8:
            overall_level = CompatibilityLevel.GOOD
        elif average_score >= 0.7:
            overall_level = CompatibilityLevel.ACCEPTABLE
        elif average_score >= 0.5:
            overall_level = CompatibilityLevel.POOR
        else:
            overall_level = CompatibilityLevel.INCOMPATIBLE
        
        return {
            "individual_scores": scores,
            "aggregate_metrics": {
                "average_score": average_score,
                "minimum_score": min_score,
                "maximum_score": max_score,
                "overall_compatibility_level": overall_level.value,
                "score_variance": max_score - min_score if overall_scores else 0.0
            },
            "compatibility_distribution": {
                level: compatibility_levels.count(level) 
                for level in set(compatibility_levels)
            },
            "improvement_recommendations": self._generate_compatibility_improvements(scores)
        }
    
    def generate_remediation_recommendations(
        self,
        validation_results: Dict[str, ValidationResult],
        compatibility_results: Dict[str, SemanticValidationResult]
    ) -> List[Dict[str, Any]]:
        """
        Generate specific remediation recommendations for validation failures.
        
        Args:
            validation_results: Validation results for each agent
            compatibility_results: Compatibility results between agents
            
        Returns:
            List of prioritized remediation recommendations
        """
        logger.info("Generating remediation recommendations")
        
        recommendations = []
        
        # Process validation errors
        for agent_name, result in validation_results.items():
            for error in result.validation_errors:
                if error.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
                    recommendations.append({
                        "type": "validation_fix",
                        "priority": "high" if error.severity == ValidationSeverity.CRITICAL else "medium",
                        "agent": agent_name,
                        "field": error.field_name,
                        "issue": error.error_message,
                        "remediation": error.remediation_suggestion,
                        "estimated_effort": self._estimate_fix_effort(error),
                        "impact": "Pipeline will fail" if error.severity == ValidationSeverity.CRITICAL else "Reduced quality"
                    })
        
        # Process compatibility issues
        for pair_name, result in compatibility_results.items():
            for missing_mapping in result.missing_mappings:
                recommendations.append({
                    "type": "compatibility_fix",
                    "priority": "high" if missing_mapping.required else "medium",
                    "agent_pair": pair_name,
                    "issue": f"Missing mapping: {missing_mapping.source_field} -> {missing_mapping.target_field}",
                    "remediation": f"Implement mapping from {missing_mapping.source_agent} to {missing_mapping.target_agent}",
                    "estimated_effort": "medium",
                    "impact": "Data flow interruption"
                })
            
            for semantic_issue in result.semantic_issues:
                recommendations.append({
                    "type": "semantic_fix",
                    "priority": "medium",
                    "agent_pair": pair_name,
                    "issue": semantic_issue,
                    "remediation": "Review and align semantic meaning between agents",
                    "estimated_effort": "high",
                    "impact": "Logical inconsistency"
                })
        
        # Sort by priority and impact
        priority_order = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)
        
        return recommendations
    
    def _generate_validation_summary(
        self,
        validation_results: Dict[str, ValidationResult],
        compatibility_results: Dict[str, SemanticValidationResult]
    ) -> ValidationSummary:
        """Generate validation summary"""
        total_agents = len(validation_results)
        agents_passed = sum(1 for result in validation_results.values() if result.is_valid)
        agents_failed = total_agents - agents_passed
        
        total_errors = sum(len(result.validation_errors) for result in validation_results.values())
        total_warnings = sum(len(result.warnings) for result in validation_results.values())
        
        # Calculate overall scores
        quality_scores = [result.quality_score for result in validation_results.values()]
        overall_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        compatibility_scores = [result.data_flow_score for result in compatibility_results.values()]
        overall_compatibility_score = sum(compatibility_scores) / len(compatibility_scores) if compatibility_scores else 0.0
        
        total_recommendations = sum(
            len(result.recommendations) for result in validation_results.values()
        ) + sum(
            len(result.recommendations) for result in compatibility_results.values()
        )
        
        return ValidationSummary(
            total_agents_validated=total_agents,
            agents_passed=agents_passed,
            agents_failed=agents_failed,
            total_errors=total_errors,
            total_warnings=total_warnings,
            overall_compatibility_score=overall_compatibility_score,
            overall_quality_score=overall_quality_score,
            validation_timestamp=datetime.now(UTC).isoformat(),
            recommendations_count=total_recommendations
        )
    
    def _generate_detailed_error_report(
        self,
        validation_results: Dict[str, ValidationResult]
    ) -> Dict[str, Any]:
        """Generate detailed error report"""
        return self.generate_field_level_error_report(validation_results)
    
    def _generate_compatibility_scoring(
        self,
        compatibility_results: Dict[str, SemanticValidationResult]
    ) -> CompatibilityScoring:
        """Generate compatibility scoring"""
        req_to_arch_score = compatibility_results.get("requirements_to_architecture", SemanticValidationResult(
            is_valid=True, compatibility_level=CompatibilityLevel.EXCELLENT, missing_mappings=[],
            invalid_mappings=[], semantic_issues=[], data_flow_score=1.0, recommendations=[], metadata={}
        )).data_flow_score
        
        arch_to_code_score = compatibility_results.get("architecture_to_code", SemanticValidationResult(
            is_valid=True, compatibility_level=CompatibilityLevel.EXCELLENT, missing_mappings=[],
            invalid_mappings=[], semantic_issues=[], data_flow_score=1.0, recommendations=[], metadata={}
        )).data_flow_score
        
        overall_score = (req_to_arch_score + arch_to_code_score) / 2
        
        # Determine overall compatibility level
        if overall_score >= 0.9:
            compatibility_level = CompatibilityLevel.EXCELLENT
        elif overall_score >= 0.8:
            compatibility_level = CompatibilityLevel.GOOD
        elif overall_score >= 0.7:
            compatibility_level = CompatibilityLevel.ACCEPTABLE
        elif overall_score >= 0.5:
            compatibility_level = CompatibilityLevel.POOR
        else:
            compatibility_level = CompatibilityLevel.INCOMPATIBLE
        
        # Collect critical issues
        critical_issues = []
        improvement_areas = []
        
        for result in compatibility_results.values():
            critical_issues.extend(result.semantic_issues)
            if result.data_flow_score < 0.8:
                improvement_areas.append(f"Improve data flow (current score: {result.data_flow_score:.2f})")
        
        return CompatibilityScoring(
            requirements_to_architecture_score=req_to_arch_score,
            architecture_to_code_score=arch_to_code_score,
            overall_pipeline_score=overall_score,
            compatibility_level=compatibility_level,
            critical_issues=critical_issues,
            improvement_areas=improvement_areas
        )
    
    def _generate_remediation_plan(
        self,
        validation_results: Dict[str, ValidationResult],
        compatibility_results: Dict[str, SemanticValidationResult]
    ) -> RemediationPlan:
        """Generate comprehensive remediation plan"""
        recommendations = self.generate_remediation_recommendations(validation_results, compatibility_results)
        
        priority_fixes = [rec for rec in recommendations if rec["priority"] == "high"]
        optional_improvements = [rec for rec in recommendations if rec["priority"] in ["medium", "low"]]
        
        # Estimate overall effort
        high_priority_count = len(priority_fixes)
        if high_priority_count == 0:
            estimated_effort = "Low (1-2 days)"
        elif high_priority_count <= 3:
            estimated_effort = "Medium (3-5 days)"
        else:
            estimated_effort = "High (1-2 weeks)"
        
        # Define implementation order
        implementation_order = [
            "Fix critical validation errors",
            "Resolve compatibility issues",
            "Address semantic inconsistencies",
            "Implement optional improvements"
        ]
        
        # Define success criteria
        success_criteria = [
            "All agents pass schema validation",
            "Compatibility score > 0.8",
            "No critical or error-level validation issues",
            "Semantic data flow is logically consistent"
        ]
        
        return RemediationPlan(
            priority_fixes=priority_fixes,
            optional_improvements=optional_improvements,
            estimated_effort=estimated_effort,
            implementation_order=implementation_order,
            success_criteria=success_criteria
        )
    
    def _generate_agent_analysis(
        self,
        validation_results: Dict[str, ValidationResult],
        agent_outputs: Dict[str, AgentOutput]
    ) -> Dict[str, Any]:
        """Generate per-agent analysis"""
        agent_analysis = {}
        
        for agent_name, result in validation_results.items():
            agent_output = agent_outputs.get(agent_name)
            
            analysis = {
                "validation_status": "passed" if result.is_valid else "failed",
                "quality_score": result.quality_score,
                "compatibility_score": result.compatibility_score,
                "error_count": len(result.validation_errors),
                "warning_count": len(result.warnings),
                "recommendation_count": len(result.recommendations),
                "execution_metadata": agent_output.execution_metadata.model_dump() if agent_output else {},
                "key_issues": [
                    error.error_message for error in result.validation_errors
                    if error.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
                ],
                "improvement_suggestions": result.recommendations
            }
            
            agent_analysis[agent_name] = analysis
        
        return agent_analysis
    
    def _generate_overall_recommendations(
        self,
        validation_results: Dict[str, ValidationResult],
        compatibility_results: Dict[str, SemanticValidationResult]
    ) -> List[str]:
        """Generate overall recommendations for the pipeline"""
        recommendations = []
        
        # Check overall validation status
        failed_agents = [name for name, result in validation_results.items() if not result.is_valid]
        if failed_agents:
            recommendations.append(f"Priority: Fix validation failures in {', '.join(failed_agents)}")
        
        # Check compatibility scores
        low_compatibility = [
            name for name, result in compatibility_results.items()
            if result.data_flow_score < 0.7
        ]
        if low_compatibility:
            recommendations.append(f"Improve compatibility between {', '.join(low_compatibility)}")
        
        # Check overall quality
        quality_scores = [result.quality_score for result in validation_results.values()]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        if avg_quality < 0.8:
            recommendations.append("Focus on improving overall output quality across all agents")
        
        # Add general recommendations
        recommendations.extend([
            "Implement comprehensive error handling in all agents",
            "Add validation checkpoints between agent executions",
            "Consider implementing retry logic for failed validations",
            "Monitor validation metrics over time to identify trends"
        ])
        
        return recommendations
    
    def _generate_compatibility_improvements(self, scores: Dict[str, Any]) -> List[str]:
        """Generate compatibility improvement recommendations"""
        improvements = []
        
        for pair_name, score_details in scores.items():
            if score_details["data_flow_score"] < 0.8:
                improvements.append(f"Improve data flow between {pair_name}")
            if score_details["missing_mappings_count"] > 0:
                improvements.append(f"Implement missing field mappings for {pair_name}")
            if score_details["semantic_issues_count"] > 0:
                improvements.append(f"Resolve semantic inconsistencies in {pair_name}")
        
        return improvements
    
    def _estimate_fix_effort(self, error: ValidationError) -> str:
        """Estimate effort required to fix a validation error"""
        if error.severity == ValidationSeverity.CRITICAL:
            return "high"
        elif error.error_type.value in ["missing_field", "invalid_type"]:
            return "medium"
        else:
            return "low"
    
    def _save_report(
        self,
        report: Dict[str, Any],
        session_id: str,
        report_format: ReportFormat
    ) -> None:
        """Save report to file"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"validation_report_{session_id}_{timestamp}.{report_format.value}"
        filepath = self.output_dir / filename
        
        try:
            if report_format == ReportFormat.JSON:
                with open(filepath, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
            elif report_format == ReportFormat.MARKDOWN:
                markdown_content = self._convert_to_markdown(report)
                with open(filepath, 'w') as f:
                    f.write(markdown_content)
            else:
                # Default to JSON for unsupported formats
                with open(filepath, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Validation report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save validation report: {str(e)}")
    
    def _convert_to_markdown(self, report: Dict[str, Any]) -> str:
        """Convert report to Markdown format"""
        md_lines = [
            f"# Validation Report - {report['report_metadata']['session_id']}",
            f"Generated: {report['report_metadata']['report_timestamp']}",
            "",
            "## Summary",
            f"- Total Agents: {report['validation_summary']['total_agents_validated']}",
            f"- Passed: {report['validation_summary']['agents_passed']}",
            f"- Failed: {report['validation_summary']['agents_failed']}",
            f"- Overall Quality Score: {report['validation_summary']['overall_quality_score']:.2f}",
            f"- Overall Compatibility Score: {report['validation_summary']['overall_compatibility_score']:.2f}",
            "",
            "## Recommendations",
        ]
        
        for rec in report['recommendations']:
            md_lines.append(f"- {rec}")
        
        return "\n".join(md_lines)