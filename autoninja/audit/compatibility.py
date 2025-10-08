"""
Content Compatibility Checker

This module provides semantic validation to ensure data flows logically between agents
and that each agent's output contains the necessary information for the next agent.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, UTC
from dataclasses import dataclass
from enum import Enum

from autoninja.models.state import AgentOutput

logger = logging.getLogger(__name__)


class CompatibilityLevel(str, Enum):
    """Compatibility assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INCOMPATIBLE = "incompatible"


@dataclass
class FieldMapping:
    """Mapping between fields across agents"""
    source_agent: str
    source_field: str
    target_agent: str
    target_field: str
    required: bool = True
    transformation_needed: bool = False
    description: str = ""


@dataclass
class SemanticValidationResult:
    """Result of semantic validation between agents"""
    is_valid: bool
    compatibility_level: CompatibilityLevel
    missing_mappings: List[FieldMapping]
    invalid_mappings: List[FieldMapping]
    semantic_issues: List[str]
    data_flow_score: float
    recommendations: List[str]
    metadata: Dict[str, Any]


class ContentCompatibilityChecker:
    """
    Checks semantic compatibility and data flow between agent outputs.
    
    This class ensures that:
    1. Requirements Analyst output contains necessary fields for Solution Architect
    2. Solution Architect output contains necessary fields for Code Generator
    3. Data flows logically and semantically between agents
    """
    
    def __init__(self):
        self.field_mappings = self._initialize_field_mappings()
        self.semantic_rules = self._initialize_semantic_rules()
    
    def _initialize_field_mappings(self) -> Dict[str, List[FieldMapping]]:
        """Initialize field mappings between agents"""
        return {
            "requirements_to_architecture": [
                FieldMapping(
                    source_agent="requirements_analyst",
                    source_field="extracted_requirements.functional_requirements",
                    target_agent="solution_architect",
                    target_field="selected_services",
                    required=True,
                    description="Functional requirements should drive service selection"
                ),
                FieldMapping(
                    source_agent="requirements_analyst",
                    source_field="extracted_requirements.non_functional_requirements.security",
                    target_agent="solution_architect",
                    target_field="security_architecture",
                    required=True,
                    description="Security requirements should inform security architecture"
                ),
                FieldMapping(
                    source_agent="requirements_analyst",
                    source_field="extracted_requirements.non_functional_requirements.performance",
                    target_agent="solution_architect",
                    target_field="architecture_blueprint.performance_considerations",
                    required=False,
                    description="Performance requirements should influence architecture design"
                ),
                FieldMapping(
                    source_agent="requirements_analyst",
                    source_field="extracted_requirements.non_functional_requirements.scalability",
                    target_agent="solution_architect",
                    target_field="architecture_blueprint.scalability_plan",
                    required=False,
                    description="Scalability requirements should drive scalability planning"
                ),
                FieldMapping(
                    source_agent="requirements_analyst",
                    source_field="compliance_frameworks",
                    target_agent="solution_architect",
                    target_field="security_architecture.compliance_measures",
                    required=False,
                    description="Compliance frameworks should be addressed in security design"
                ),
                FieldMapping(
                    source_agent="requirements_analyst",
                    source_field="complexity_assessment.complexity_level",
                    target_agent="solution_architect",
                    target_field="architecture_blueprint.deployment_complexity",
                    required=False,
                    transformation_needed=True,
                    description="Complexity assessment should inform deployment strategy"
                )
            ],
            "architecture_to_code": [
                FieldMapping(
                    source_agent="solution_architect",
                    source_field="selected_services",
                    target_agent="code_generator",
                    target_field="bedrock_agent_config",
                    required=True,
                    description="Selected services should be implemented in code"
                ),
                FieldMapping(
                    source_agent="solution_architect",
                    source_field="architecture_blueprint.deployment_model",
                    target_agent="code_generator",
                    target_field="cloudformation_templates",
                    required=True,
                    description="Deployment model should drive infrastructure code"
                ),
                FieldMapping(
                    source_agent="solution_architect",
                    source_field="security_architecture.iam_design",
                    target_agent="code_generator",
                    target_field="iam_policies",
                    required=True,
                    description="IAM design should be implemented as policies"
                ),
                FieldMapping(
                    source_agent="solution_architect",
                    source_field="integration_design.api_endpoints",
                    target_agent="code_generator",
                    target_field="action_groups",
                    required=False,
                    description="API design should drive action group implementation"
                ),
                FieldMapping(
                    source_agent="solution_architect",
                    source_field="iac_templates",
                    target_agent="code_generator",
                    target_field="cloudformation_templates",
                    required=True,
                    description="IaC templates should be implemented as CloudFormation"
                )
            ]
        }
    
    def _initialize_semantic_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize semantic validation rules"""
        return {
            "requirements_to_architecture": [
                {
                    "rule": "ai_agent_requirements_to_bedrock",
                    "description": "AI agent requirements should result in Bedrock service selection",
                    "check": lambda req, arch: self._check_ai_agent_to_bedrock(req, arch)
                },
                {
                    "rule": "api_requirements_to_gateway",
                    "description": "API requirements should result in API Gateway selection",
                    "check": lambda req, arch: self._check_api_requirements_to_gateway(req, arch)
                },
                {
                    "rule": "data_storage_requirements_to_services",
                    "description": "Data storage requirements should result in appropriate storage services",
                    "check": lambda req, arch: self._check_data_storage_requirements(req, arch)
                }
            ],
            "architecture_to_code": [
                {
                    "rule": "bedrock_service_to_agent_config",
                    "description": "Bedrock service selection should result in agent configuration",
                    "check": lambda arch, code: self._check_bedrock_to_config(arch, code)
                },
                {
                    "rule": "lambda_service_to_functions",
                    "description": "Lambda service selection should result in function implementations",
                    "check": lambda arch, code: self._check_lambda_to_functions(arch, code)
                },
                {
                    "rule": "security_design_to_iam",
                    "description": "Security architecture should result in IAM implementations",
                    "check": lambda arch, code: self._check_security_to_iam(arch, code)
                }
            ]
        }
    
    def verify_requirements_to_architecture_compatibility(
        self, 
        requirements_output: Dict[str, Any], 
        architecture_output: Dict[str, Any]
    ) -> SemanticValidationResult:
        """
        Verify that Requirements Analyst output contains necessary fields for Solution Architect.
        
        Args:
            requirements_output: Requirements Analyst output data
            architecture_output: Solution Architect output data
            
        Returns:
            SemanticValidationResult: Detailed compatibility assessment
        """
        logger.info("Verifying Requirements Analyst to Solution Architect compatibility")
        
        mappings = self.field_mappings["requirements_to_architecture"]
        semantic_rules = self.semantic_rules["requirements_to_architecture"]
        
        return self._perform_compatibility_check(
            requirements_output, 
            architecture_output, 
            mappings, 
            semantic_rules,
            "requirements_to_architecture"
        )
    
    def verify_architecture_to_code_compatibility(
        self, 
        architecture_output: Dict[str, Any], 
        code_output: Dict[str, Any]
    ) -> SemanticValidationResult:
        """
        Verify that Solution Architect output contains necessary fields for Code Generator.
        
        Args:
            architecture_output: Solution Architect output data
            code_output: Code Generator output data
            
        Returns:
            SemanticValidationResult: Detailed compatibility assessment
        """
        logger.info("Verifying Solution Architect to Code Generator compatibility")
        
        mappings = self.field_mappings["architecture_to_code"]
        semantic_rules = self.semantic_rules["architecture_to_code"]
        
        return self._perform_compatibility_check(
            architecture_output, 
            code_output, 
            mappings, 
            semantic_rules,
            "architecture_to_code"
        )
    
    def validate_semantic_data_flow(
        self, 
        requirements_output: Dict[str, Any],
        architecture_output: Dict[str, Any], 
        code_output: Dict[str, Any]
    ) -> SemanticValidationResult:
        """
        Validate semantic data flow across all three agents.
        
        Args:
            requirements_output: Requirements Analyst output
            architecture_output: Solution Architect output
            code_output: Code Generator output
            
        Returns:
            SemanticValidationResult: Overall semantic validation result
        """
        logger.info("Validating semantic data flow across all agents")
        
        # Check requirements to architecture
        req_to_arch = self.verify_requirements_to_architecture_compatibility(
            requirements_output, architecture_output
        )
        
        # Check architecture to code
        arch_to_code = self.verify_architecture_to_code_compatibility(
            architecture_output, code_output
        )
        
        # Combine results
        all_missing_mappings = req_to_arch.missing_mappings + arch_to_code.missing_mappings
        all_invalid_mappings = req_to_arch.invalid_mappings + arch_to_code.invalid_mappings
        all_semantic_issues = req_to_arch.semantic_issues + arch_to_code.semantic_issues
        all_recommendations = req_to_arch.recommendations + arch_to_code.recommendations
        
        # Calculate overall scores
        overall_data_flow_score = (req_to_arch.data_flow_score + arch_to_code.data_flow_score) / 2
        
        # Determine overall compatibility level
        if overall_data_flow_score >= 0.9:
            compatibility_level = CompatibilityLevel.EXCELLENT
        elif overall_data_flow_score >= 0.8:
            compatibility_level = CompatibilityLevel.GOOD
        elif overall_data_flow_score >= 0.7:
            compatibility_level = CompatibilityLevel.ACCEPTABLE
        elif overall_data_flow_score >= 0.5:
            compatibility_level = CompatibilityLevel.POOR
        else:
            compatibility_level = CompatibilityLevel.INCOMPATIBLE
        
        is_valid = len(all_missing_mappings) == 0 and len(all_invalid_mappings) == 0
        
        return SemanticValidationResult(
            is_valid=is_valid,
            compatibility_level=compatibility_level,
            missing_mappings=all_missing_mappings,
            invalid_mappings=all_invalid_mappings,
            semantic_issues=all_semantic_issues,
            data_flow_score=overall_data_flow_score,
            recommendations=list(set(all_recommendations)),  # Remove duplicates
            metadata={
                "validation_time": datetime.now(UTC).isoformat(),
                "req_to_arch_score": req_to_arch.data_flow_score,
                "arch_to_code_score": arch_to_code.data_flow_score,
                "total_mappings_checked": len(self.field_mappings["requirements_to_architecture"]) + 
                                        len(self.field_mappings["architecture_to_code"])
            }
        )
    
    def _perform_compatibility_check(
        self,
        source_output: Dict[str, Any],
        target_output: Dict[str, Any],
        mappings: List[FieldMapping],
        semantic_rules: List[Dict[str, Any]],
        check_type: str
    ) -> SemanticValidationResult:
        """Perform compatibility check between two agent outputs"""
        missing_mappings = []
        invalid_mappings = []
        semantic_issues = []
        recommendations = []
        
        # Check field mappings
        for mapping in mappings:
            source_value = self._get_nested_value(source_output, mapping.source_field)
            target_value = self._get_nested_value(target_output, mapping.target_field)
            
            if mapping.required and source_value is not None and target_value is None:
                missing_mappings.append(mapping)
                recommendations.append(
                    f"Map {mapping.source_field} from {mapping.source_agent} to "
                    f"{mapping.target_field} in {mapping.target_agent}"
                )
            elif source_value is not None and target_value is not None:
                # Check if the mapping makes semantic sense
                if not self._validate_field_mapping(source_value, target_value, mapping):
                    invalid_mappings.append(mapping)
                    recommendations.append(
                        f"Review mapping between {mapping.source_field} and {mapping.target_field} "
                        f"- values may not be semantically compatible"
                    )
        
        # Check semantic rules
        for rule in semantic_rules:
            try:
                rule_result = rule["check"](source_output, target_output)
                if not rule_result:
                    semantic_issues.append(f"Semantic rule violation: {rule['description']}")
                    recommendations.append(f"Address semantic issue: {rule['description']}")
            except Exception as e:
                logger.warning(f"Error checking semantic rule {rule['rule']}: {str(e)}")
        
        # Calculate data flow score
        total_mappings = len(mappings)
        successful_mappings = total_mappings - len(missing_mappings) - len(invalid_mappings)
        mapping_score = successful_mappings / total_mappings if total_mappings > 0 else 1.0
        
        semantic_score = 1.0 - (len(semantic_issues) * 0.2)
        data_flow_score = (mapping_score + max(0.0, semantic_score)) / 2
        
        # Determine compatibility level
        if data_flow_score >= 0.9:
            compatibility_level = CompatibilityLevel.EXCELLENT
        elif data_flow_score >= 0.8:
            compatibility_level = CompatibilityLevel.GOOD
        elif data_flow_score >= 0.7:
            compatibility_level = CompatibilityLevel.ACCEPTABLE
        elif data_flow_score >= 0.5:
            compatibility_level = CompatibilityLevel.POOR
        else:
            compatibility_level = CompatibilityLevel.INCOMPATIBLE
        
        is_valid = len(missing_mappings) == 0 and len(invalid_mappings) == 0 and len(semantic_issues) == 0
        
        return SemanticValidationResult(
            is_valid=is_valid,
            compatibility_level=compatibility_level,
            missing_mappings=missing_mappings,
            invalid_mappings=invalid_mappings,
            semantic_issues=semantic_issues,
            data_flow_score=data_flow_score,
            recommendations=recommendations,
            metadata={
                "check_type": check_type,
                "validation_time": datetime.now(UTC).isoformat(),
                "total_mappings": total_mappings,
                "successful_mappings": successful_mappings
            }
        )
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        try:
            keys = field_path.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        except Exception:
            return None
    
    def _validate_field_mapping(
        self, 
        source_value: Any, 
        target_value: Any, 
        mapping: FieldMapping
    ) -> bool:
        """Validate that a field mapping makes semantic sense"""
        # Basic validation - can be extended with more sophisticated checks
        if source_value is None or target_value is None:
            return True  # Already handled in missing mappings
        
        # Check if both values are non-empty
        if isinstance(source_value, (list, dict, str)):
            if not source_value:  # Empty list, dict, or string
                return True  # Empty source is acceptable
        
        if isinstance(target_value, (list, dict, str)):
            if not target_value:  # Empty target when source has value
                return False
        
        return True
    
    # Semantic rule implementations
    def _check_ai_agent_to_bedrock(self, requirements: Dict[str, Any], architecture: Dict[str, Any]) -> bool:
        """Check if AI agent requirements result in Bedrock service selection"""
        functional_req = requirements.get("extracted_requirements", {}).get("functional_requirements", [])
        selected_services = architecture.get("selected_services", [])
        
        # Check if AI/conversational requirements exist
        ai_keywords = ["ai", "agent", "conversational", "chat", "nlp", "language model", "bedrock"]
        has_ai_requirements = any(
            any(keyword in str(req).lower() for keyword in ai_keywords)
            for req in functional_req
        )
        
        if not has_ai_requirements:
            return True  # No AI requirements, so no need for Bedrock
        
        # Check if Bedrock is selected
        service_names = []
        for service in selected_services:
            if isinstance(service, dict):
                service_names.append(service.get("service", "").lower())
            else:
                service_names.append(str(service).lower())
        
        return any("bedrock" in name for name in service_names)
    
    def _check_api_requirements_to_gateway(self, requirements: Dict[str, Any], architecture: Dict[str, Any]) -> bool:
        """Check if API requirements result in API Gateway selection"""
        functional_req = requirements.get("extracted_requirements", {}).get("functional_requirements", [])
        selected_services = architecture.get("selected_services", [])
        
        # Check if API requirements exist
        api_keywords = ["api", "endpoint", "rest", "http", "web service", "interface"]
        has_api_requirements = any(
            any(keyword in str(req).lower() for keyword in api_keywords)
            for req in functional_req
        )
        
        if not has_api_requirements:
            return True  # No API requirements
        
        # Check if API Gateway is selected
        service_names = []
        for service in selected_services:
            if isinstance(service, dict):
                service_names.append(service.get("service", "").lower())
            else:
                service_names.append(str(service).lower())
        
        return any("api gateway" in name or "apigateway" in name for name in service_names)
    
    def _check_data_storage_requirements(self, requirements: Dict[str, Any], architecture: Dict[str, Any]) -> bool:
        """Check if data storage requirements result in appropriate storage services"""
        functional_req = requirements.get("extracted_requirements", {}).get("functional_requirements", [])
        selected_services = architecture.get("selected_services", [])
        
        # Check if storage requirements exist
        storage_keywords = ["storage", "database", "data", "persist", "save", "store"]
        has_storage_requirements = any(
            any(keyword in str(req).lower() for keyword in storage_keywords)
            for req in functional_req
        )
        
        if not has_storage_requirements:
            return True  # No storage requirements
        
        # Check if storage services are selected
        service_names = []
        for service in selected_services:
            if isinstance(service, dict):
                service_names.append(service.get("service", "").lower())
            else:
                service_names.append(str(service).lower())
        
        storage_services = ["dynamodb", "s3", "rds", "aurora", "documentdb", "elasticache"]
        return any(storage_service in name for name in service_names for storage_service in storage_services)
    
    def _check_bedrock_to_config(self, architecture: Dict[str, Any], code: Dict[str, Any]) -> bool:
        """Check if Bedrock service selection results in agent configuration"""
        selected_services = architecture.get("selected_services", [])
        bedrock_config = code.get("bedrock_agent_config", {})
        
        # Check if Bedrock is selected
        service_names = []
        for service in selected_services:
            if isinstance(service, dict):
                service_names.append(service.get("service", "").lower())
            else:
                service_names.append(str(service).lower())
        
        has_bedrock = any("bedrock" in name for name in service_names)
        
        if not has_bedrock:
            return True  # No Bedrock selected, no config needed
        
        # Check if Bedrock agent config exists and has essential fields
        return bool(bedrock_config.get("agent_name") and bedrock_config.get("foundation_model"))
    
    def _check_lambda_to_functions(self, architecture: Dict[str, Any], code: Dict[str, Any]) -> bool:
        """Check if Lambda service selection results in function implementations"""
        selected_services = architecture.get("selected_services", [])
        lambda_functions = code.get("lambda_functions", [])
        
        # Check if Lambda is selected
        service_names = []
        for service in selected_services:
            if isinstance(service, dict):
                service_names.append(service.get("service", "").lower())
            else:
                service_names.append(str(service).lower())
        
        has_lambda = any("lambda" in name for name in service_names)
        
        if not has_lambda:
            return True  # No Lambda selected, no functions needed
        
        # Check if Lambda functions are implemented
        return len(lambda_functions) > 0
    
    def _check_security_to_iam(self, architecture: Dict[str, Any], code: Dict[str, Any]) -> bool:
        """Check if security architecture results in IAM implementations"""
        security_arch = architecture.get("security_architecture", {})
        iam_policies = code.get("iam_policies", [])
        
        # Check if IAM design exists in security architecture
        iam_design = security_arch.get("iam_design", {})
        
        if not iam_design:
            return True  # No IAM design, no policies needed
        
        # Check if IAM policies are implemented
        return len(iam_policies) > 0