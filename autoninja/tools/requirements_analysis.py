"""
Requirements Analysis Tools for AutoNinja

LangChain tools for natural language processing, requirement extraction,
compliance framework detection, and requirement validation.
"""

import json
import re
from typing import Dict, List, Any, Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient


class RequirementExtractionInput(BaseModel):
    """Input schema for requirement extraction tool."""
    user_request: str = Field(description="Natural language user request to analyze")
    agent_type: Optional[str] = Field(default=None, description="Type of agent being requested")


class RequirementExtractionTool(BaseTool):
    """Tool for extracting structured requirements from natural language input."""
    
    name: str = "requirement_extraction"
    description: str = """Extract functional and non-functional requirements from natural language descriptions.
    Analyzes user requests to identify specific capabilities, constraints, and success criteria."""
    
    args_schema: Type[BaseModel] = RequirementExtractionInput
    kb_client: Optional[BedrockKnowledgeBaseClient] = Field(default=None, exclude=True)
    
    def __init__(self, knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None, **kwargs):
        super().__init__(kb_client=knowledge_base_client, **kwargs)
        
    def _run(self, user_request: str, agent_type: Optional[str] = None) -> str:
        """Extract requirements from user request."""
        try:
            # Analyze the request for key components
            functional_requirements = self._extract_functional_requirements(user_request)
            non_functional_requirements = self._extract_non_functional_requirements(user_request)
            constraints = self._extract_constraints(user_request)
            success_criteria = self._extract_success_criteria(user_request)
            
            # Query knowledge base for similar patterns if available
            similar_patterns = []
            if self.kb_client:
                similar_patterns = self._query_similar_patterns(user_request, agent_type)
            
            result = {
                "functional_requirements": functional_requirements,
                "non_functional_requirements": non_functional_requirements,
                "constraints": constraints,
                "success_criteria": success_criteria,
                "similar_patterns": similar_patterns,
                "agent_type_detected": self._detect_agent_type(user_request) if not agent_type else agent_type
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Error extracting requirements: {str(e)}"
    
    def _extract_functional_requirements(self, text: str) -> List[str]:
        """Extract functional requirements from text."""
        requirements = []
        
        # Look for action verbs and capabilities
        action_patterns = [
            r"(?:should|must|shall|will|can|need to|want to|able to)\s+([^.!?]+)",
            r"(?:I want|I need|I require)\s+([^.!?]+)",
            r"(?:The agent|The system|It)\s+(?:should|must|shall|will)\s+([^.!?]+)"
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip().lower()
                if len(cleaned) > 10:  # Filter out very short matches
                    requirements.append(cleaned)
        
        # Look for specific capabilities mentioned
        capability_keywords = [
            "process", "analyze", "generate", "create", "manage", "handle",
            "respond", "integrate", "monitor", "validate", "transform"
        ]
        
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            for keyword in capability_keywords:
                if keyword in sentence.lower():
                    cleaned = sentence.strip()
                    if len(cleaned) > 20:
                        requirements.append(cleaned)
        
        return list(set(requirements))  # Remove duplicates
    
    def _extract_non_functional_requirements(self, text: str) -> Dict[str, List[str]]:
        """Extract non-functional requirements categorized by type."""
        nfr = {
            "performance": [],
            "security": [],
            "scalability": [],
            "availability": [],
            "usability": []
        }
        
        # Performance indicators
        perf_patterns = [
            r"(?:within|under|less than)\s+(\d+\s*(?:seconds?|minutes?|ms|milliseconds?))",
            r"(?:response time|latency|speed)\s+(?:of|under|within)?\s*(\d+\s*(?:seconds?|minutes?|ms))",
            r"(?:fast|quick|real-time|instant)"
        ]
        
        for pattern in perf_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                nfr["performance"].append(match if isinstance(match, str) else "fast response required")
        
        # Security indicators
        security_keywords = ["secure", "encrypted", "authentication", "authorization", "privacy", "confidential"]
        for keyword in security_keywords:
            if keyword in text.lower():
                nfr["security"].append(f"{keyword} required")
        
        # Scalability indicators
        scale_keywords = ["scale", "concurrent", "multiple users", "high volume", "load"]
        for keyword in scale_keywords:
            if keyword in text.lower():
                nfr["scalability"].append(f"{keyword} support needed")
        
        return {k: v for k, v in nfr.items() if v}  # Only return non-empty categories
    
    def _extract_constraints(self, text: str) -> List[str]:
        """Extract constraints and limitations."""
        constraints = []
        
        # Budget constraints
        budget_patterns = [
            r"budget\s+(?:of|under|within)?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"cost\s+(?:under|within|less than)\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"(?:cheap|low cost|minimal cost|budget-friendly)"
        ]
        
        for pattern in budget_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                constraints.append(f"Budget constraint: {matches[0] if matches[0] else 'cost-conscious'}")
        
        # Time constraints
        time_patterns = [
            r"(?:by|within|in)\s+(\d+\s*(?:days?|weeks?|months?))",
            r"(?:urgent|asap|quickly|soon)"
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                constraints.append(f"Time constraint: {matches[0] if matches[0] else 'urgent timeline'}")
        
        # Technology constraints
        tech_keywords = ["python", "javascript", "java", "aws", "serverless", "lambda"]
        for keyword in tech_keywords:
            if keyword in text.lower():
                constraints.append(f"Technology preference: {keyword}")
        
        return constraints
    
    def _extract_success_criteria(self, text: str) -> List[str]:
        """Extract success criteria and acceptance conditions."""
        criteria = []
        
        # Look for success indicators
        success_patterns = [
            r"success(?:ful)?\s+(?:when|if)\s+([^.!?]+)",
            r"(?:measure|metric|kpi)\s+([^.!?]+)",
            r"(?:goal|objective|target)\s+(?:is|of)\s+([^.!?]+)"
        ]
        
        for pattern in success_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                criteria.append(match.strip())
        
        return criteria
    
    def _detect_agent_type(self, text: str) -> str:
        """Detect the type of agent being requested."""
        text_lower = text.lower()
        
        # Conversational agent indicators
        if any(word in text_lower for word in ["chat", "conversation", "talk", "customer service", "support", "help desk"]):
            return "conversational"
        
        # Analytical agent indicators
        if any(word in text_lower for word in ["analyze", "data", "report", "insights", "analytics", "dashboard"]):
            return "analytical"
        
        # Automation agent indicators
        if any(word in text_lower for word in ["automate", "workflow", "process", "task", "schedule", "trigger"]):
            return "automation"
        
        return "custom"
    
    def _query_similar_patterns(self, user_request: str, agent_type: Optional[str]) -> List[Dict]:
        """Query knowledge base for similar requirement patterns."""
        if not self.kb_client:
            return []
        
        try:
            from autoninja.core.knowledge_base import KnowledgeBaseType
            
            # Query for similar requirements
            query_text = f"requirements for {agent_type or 'agent'}: {user_request[:200]}"
            results = self.kb_client.search_knowledge_base(
                kb_type=KnowledgeBaseType.REQUIREMENTS_PATTERNS,
                query=query_text,
                max_results=3
            )
            
            return [{"content": result.content, "confidence": result.relevance_score} 
                   for result in results]
        except Exception:
            return []


class ComplianceFrameworkDetectionInput(BaseModel):
    """Input schema for compliance framework detection tool."""
    requirements_text: str = Field(description="Requirements text to analyze for compliance needs")
    industry: Optional[str] = Field(default=None, description="Industry context if known")


class ComplianceFrameworkDetectionTool(BaseTool):
    """Tool for detecting applicable compliance frameworks and regulations."""
    
    name: str = "compliance_framework_detection"
    description: str = """Identify applicable compliance frameworks and regulatory requirements
    based on the agent requirements and industry context."""
    
    args_schema: Type[BaseModel] = ComplianceFrameworkDetectionInput
    
    def _run(self, requirements_text: str, industry: Optional[str] = None) -> str:
        """Detect compliance frameworks from requirements."""
        try:
            frameworks = self._detect_frameworks(requirements_text, industry)
            regulations = self._detect_regulations(requirements_text, industry)
            security_standards = self._detect_security_standards(requirements_text)
            
            result = {
                "compliance_frameworks": frameworks,
                "regulations": regulations,
                "security_standards": security_standards,
                "recommendations": self._generate_compliance_recommendations(frameworks, regulations, security_standards)
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Error detecting compliance frameworks: {str(e)}"
    
    def _detect_frameworks(self, text: str, industry: Optional[str]) -> List[Dict[str, Any]]:
        """Detect compliance frameworks."""
        frameworks = []
        text_lower = text.lower()
        
        # Healthcare
        if any(word in text_lower for word in ["health", "medical", "patient", "hipaa", "phi"]) or industry == "healthcare":
            frameworks.append({
                "name": "HIPAA",
                "description": "Health Insurance Portability and Accountability Act",
                "requirements": ["data encryption", "access controls", "audit logging", "data minimization"]
            })
        
        # Financial services
        if any(word in text_lower for word in ["financial", "banking", "payment", "pci", "sox"]) or industry == "financial":
            frameworks.append({
                "name": "PCI DSS",
                "description": "Payment Card Industry Data Security Standard",
                "requirements": ["secure network", "cardholder data protection", "vulnerability management"]
            })
            frameworks.append({
                "name": "SOX",
                "description": "Sarbanes-Oxley Act",
                "requirements": ["financial reporting controls", "audit trails", "data integrity"]
            })
        
        # General data protection
        if any(word in text_lower for word in ["personal data", "privacy", "gdpr", "data protection"]):
            frameworks.append({
                "name": "GDPR",
                "description": "General Data Protection Regulation",
                "requirements": ["consent management", "data portability", "right to erasure", "privacy by design"]
            })
        
        return frameworks
    
    def _detect_regulations(self, text: str, industry: Optional[str]) -> List[Dict[str, Any]]:
        """Detect applicable regulations."""
        regulations = []
        text_lower = text.lower()
        
        # US regulations
        if any(word in text_lower for word in ["federal", "government", "fedramp"]):
            regulations.append({
                "name": "FedRAMP",
                "description": "Federal Risk and Authorization Management Program",
                "scope": "US Federal Government"
            })
        
        # EU regulations
        if any(word in text_lower for word in ["european", "eu", "gdpr"]):
            regulations.append({
                "name": "GDPR",
                "description": "General Data Protection Regulation",
                "scope": "European Union"
            })
        
        return regulations
    
    def _detect_security_standards(self, text: str) -> List[Dict[str, Any]]:
        """Detect security standards requirements."""
        standards = []
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["iso", "27001", "security management"]):
            standards.append({
                "name": "ISO 27001",
                "description": "Information Security Management System",
                "controls": ["access control", "cryptography", "incident management"]
            })
        
        if any(word in text_lower for word in ["nist", "cybersecurity", "framework"]):
            standards.append({
                "name": "NIST Cybersecurity Framework",
                "description": "Framework for improving critical infrastructure cybersecurity",
                "functions": ["identify", "protect", "detect", "respond", "recover"]
            })
        
        return standards
    
    def _generate_compliance_recommendations(self, frameworks: List, regulations: List, standards: List) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []
        
        if frameworks or regulations or standards:
            recommendations.append("Implement comprehensive audit logging and monitoring")
            recommendations.append("Ensure data encryption at rest and in transit")
            recommendations.append("Implement strong access controls and authentication")
            recommendations.append("Regular security assessments and penetration testing")
            recommendations.append("Incident response and business continuity planning")
        
        if any("GDPR" in str(item) for item in frameworks + regulations):
            recommendations.append("Implement data subject rights management")
            recommendations.append("Conduct Data Protection Impact Assessments (DPIA)")
        
        if any("HIPAA" in str(item) for item in frameworks):
            recommendations.append("Implement Business Associate Agreements (BAA)")
            recommendations.append("Regular HIPAA compliance training")
        
        return recommendations


class RequirementValidationInput(BaseModel):
    """Input schema for requirement validation tool."""
    requirements: Dict[str, Any] = Field(description="Requirements structure to validate")


class RequirementValidationTool(BaseTool):
    """Tool for validating requirement completeness and consistency."""
    
    name: str = "requirement_validation"
    description: str = """Validate requirements for completeness, consistency, and feasibility.
    Checks for missing elements, conflicts, and implementation challenges."""
    
    args_schema: Type[BaseModel] = RequirementValidationInput
    
    def _run(self, requirements: Dict[str, Any]) -> str:
        """Validate requirements structure."""
        try:
            validation_results = {
                "completeness_score": self._check_completeness(requirements),
                "consistency_issues": self._check_consistency(requirements),
                "feasibility_assessment": self._assess_feasibility(requirements),
                "missing_elements": self._identify_missing_elements(requirements),
                "recommendations": self._generate_validation_recommendations(requirements)
            }
            
            return json.dumps(validation_results, indent=2)
            
        except Exception as e:
            return f"Error validating requirements: {str(e)}"
    
    def _check_completeness(self, requirements: Dict[str, Any]) -> float:
        """Check completeness of requirements."""
        required_sections = [
            "functional_requirements",
            "non_functional_requirements", 
            "constraints",
            "success_criteria"
        ]
        
        present_sections = sum(1 for section in required_sections if section in requirements and requirements[section])
        return (present_sections / len(required_sections)) * 100
    
    def _check_consistency(self, requirements: Dict[str, Any]) -> List[str]:
        """Check for consistency issues."""
        issues = []
        
        # Check for conflicting constraints
        constraints = requirements.get("constraints", [])
        if any("budget" in str(c).lower() for c in constraints) and any("high performance" in str(c).lower() for c in constraints):
            issues.append("Potential conflict between budget constraints and high performance requirements")
        
        # Check for unrealistic timelines
        if any("urgent" in str(c).lower() for c in constraints) and len(requirements.get("functional_requirements", [])) > 10:
            issues.append("Urgent timeline may conflict with extensive functional requirements")
        
        return issues
    
    def _assess_feasibility(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Assess technical feasibility."""
        functional_reqs = requirements.get("functional_requirements", [])
        nfr = requirements.get("non_functional_requirements", {})
        
        complexity_score = min(len(functional_reqs) * 10, 100)  # Cap at 100
        
        feasibility = {
            "complexity_score": complexity_score,
            "complexity_level": "low" if complexity_score < 30 else "medium" if complexity_score < 70 else "high",
            "estimated_effort": "1-2 weeks" if complexity_score < 30 else "2-4 weeks" if complexity_score < 70 else "4+ weeks",
            "technical_risks": []
        }
        
        # Identify technical risks
        if nfr.get("performance") and any("real-time" in str(p).lower() for p in nfr["performance"]):
            feasibility["technical_risks"].append("Real-time performance requirements may require specialized architecture")
        
        if nfr.get("scalability") and any("high volume" in str(s).lower() for s in nfr["scalability"]):
            feasibility["technical_risks"].append("High scalability requirements need careful architecture planning")
        
        return feasibility
    
    def _identify_missing_elements(self, requirements: Dict[str, Any]) -> List[str]:
        """Identify missing requirement elements."""
        missing = []
        
        if not requirements.get("functional_requirements"):
            missing.append("Functional requirements not specified")
        
        if not requirements.get("success_criteria"):
            missing.append("Success criteria not defined")
        
        nfr = requirements.get("non_functional_requirements", {})
        if not nfr.get("security") and any("data" in str(req).lower() for req in requirements.get("functional_requirements", [])):
            missing.append("Security requirements not specified for data handling")
        
        if not requirements.get("constraints"):
            missing.append("Project constraints not specified")
        
        return missing
    
    def _generate_validation_recommendations(self, requirements: Dict[str, Any]) -> List[str]:
        """Generate recommendations for requirement improvement."""
        recommendations = []
        
        completeness = self._check_completeness(requirements)
        if completeness < 75:
            recommendations.append("Requirements are incomplete - consider adding missing sections")
        
        if not requirements.get("success_criteria"):
            recommendations.append("Define clear success criteria and acceptance conditions")
        
        if not requirements.get("non_functional_requirements", {}).get("performance"):
            recommendations.append("Specify performance requirements (response time, throughput)")
        
        if len(recommendations) == 0:
            recommendations.append("Requirements appear well-structured and complete")
        
        return recommendations


class RequirementStructuringInput(BaseModel):
    """Input schema for requirement structuring tool."""
    raw_requirements: Dict[str, Any] = Field(description="Raw requirements to structure")
    template_type: Optional[str] = Field(default="user_story", description="Template type to use")


class RequirementStructuringTool(BaseTool):
    """Tool for structuring requirements into standardized formats."""
    
    name: str = "requirement_structuring"
    description: str = """Structure requirements into standardized formats like user stories,
    acceptance criteria, and technical specifications."""
    
    args_schema: Type[BaseModel] = RequirementStructuringInput
    
    def _run(self, raw_requirements: Dict[str, Any], template_type: str = "user_story") -> str:
        """Structure requirements into specified format."""
        try:
            if template_type == "user_story":
                structured = self._create_user_stories(raw_requirements)
            elif template_type == "technical_spec":
                structured = self._create_technical_spec(raw_requirements)
            elif template_type == "acceptance_criteria":
                structured = self._create_acceptance_criteria(raw_requirements)
            else:
                structured = self._create_comprehensive_structure(raw_requirements)
            
            return json.dumps(structured, indent=2)
            
        except Exception as e:
            return f"Error structuring requirements: {str(e)}"
    
    def _create_user_stories(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create user stories from requirements."""
        functional_reqs = requirements.get("functional_requirements", [])
        agent_type = requirements.get("agent_type_detected", "user")
        
        user_stories = []
        for i, req in enumerate(functional_reqs, 1):
            story = {
                "id": f"US-{i:03d}",
                "title": f"Agent {req[:50]}..." if len(req) > 50 else f"Agent {req}",
                "story": f"As a {agent_type}, I want the agent to {req}, so that I can achieve my goals efficiently",
                "acceptance_criteria": [
                    f"GIVEN the agent is active WHEN {req} THEN the system SHALL respond appropriately",
                    "GIVEN valid input WHEN processing request THEN the system SHALL provide accurate results",
                    "GIVEN error conditions WHEN they occur THEN the system SHALL handle them gracefully"
                ],
                "priority": "high" if i <= 3 else "medium"
            }
            user_stories.append(story)
        
        return {
            "user_stories": user_stories,
            "total_stories": len(user_stories),
            "epic": f"{agent_type.title()} Agent Implementation"
        }
    
    def _create_technical_spec(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create technical specification from requirements."""
        return {
            "technical_specification": {
                "system_overview": f"Implementation of {requirements.get('agent_type_detected', 'custom')} agent",
                "functional_requirements": requirements.get("functional_requirements", []),
                "non_functional_requirements": requirements.get("non_functional_requirements", {}),
                "technical_constraints": requirements.get("constraints", []),
                "architecture_considerations": self._derive_architecture_needs(requirements),
                "integration_requirements": self._derive_integration_needs(requirements),
                "security_requirements": self._derive_security_needs(requirements)
            }
        }
    
    def _create_acceptance_criteria(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create acceptance criteria from requirements."""
        criteria = []
        
        for req in requirements.get("functional_requirements", []):
            criteria.append({
                "requirement": req,
                "criteria": [
                    f"WHEN user requests {req} THEN system SHALL process request successfully",
                    f"WHEN {req} is completed THEN system SHALL provide confirmation",
                    f"WHEN errors occur during {req} THEN system SHALL provide meaningful error messages"
                ]
            })
        
        return {"acceptance_criteria": criteria}
    
    def _create_comprehensive_structure(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive structured requirements."""
        return {
            "structured_requirements": {
                "overview": {
                    "agent_type": requirements.get("agent_type_detected", "custom"),
                    "complexity": "medium",  # Could be derived from analysis
                    "estimated_effort": "2-4 weeks"
                },
                "functional_requirements": self._structure_functional_requirements(requirements),
                "non_functional_requirements": requirements.get("non_functional_requirements", {}),
                "constraints": requirements.get("constraints", []),
                "success_criteria": requirements.get("success_criteria", []),
                "user_stories": self._create_user_stories(requirements)["user_stories"],
                "technical_specification": self._create_technical_spec(requirements)["technical_specification"]
            }
        }
    
    def _structure_functional_requirements(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Structure functional requirements with metadata."""
        structured = []
        
        for i, req in enumerate(requirements.get("functional_requirements", []), 1):
            structured.append({
                "id": f"FR-{i:03d}",
                "description": req,
                "priority": "high" if i <= 3 else "medium",
                "category": self._categorize_requirement(req),
                "complexity": self._assess_requirement_complexity(req)
            })
        
        return structured
    
    def _categorize_requirement(self, requirement: str) -> str:
        """Categorize a functional requirement."""
        req_lower = requirement.lower()
        
        if any(word in req_lower for word in ["process", "analyze", "compute"]):
            return "processing"
        elif any(word in req_lower for word in ["respond", "answer", "reply"]):
            return "interaction"
        elif any(word in req_lower for word in ["store", "save", "retrieve"]):
            return "data_management"
        elif any(word in req_lower for word in ["integrate", "connect", "api"]):
            return "integration"
        else:
            return "general"
    
    def _assess_requirement_complexity(self, requirement: str) -> str:
        """Assess complexity of a requirement."""
        req_lower = requirement.lower()
        
        complex_indicators = ["analyze", "machine learning", "ai", "complex", "advanced", "intelligent"]
        if any(indicator in req_lower for indicator in complex_indicators):
            return "high"
        elif len(requirement.split()) > 10:
            return "medium"
        else:
            return "low"
    
    def _derive_architecture_needs(self, requirements: Dict[str, Any]) -> List[str]:
        """Derive architecture needs from requirements."""
        needs = ["AWS Bedrock Agent", "Lambda functions", "API Gateway"]
        
        if any("data" in str(req).lower() for req in requirements.get("functional_requirements", [])):
            needs.append("DynamoDB for data storage")
        
        if requirements.get("non_functional_requirements", {}).get("scalability"):
            needs.append("Auto-scaling configuration")
        
        return needs
    
    def _derive_integration_needs(self, requirements: Dict[str, Any]) -> List[str]:
        """Derive integration needs from requirements."""
        integrations = []
        
        functional_reqs = " ".join(requirements.get("functional_requirements", []))
        
        if "email" in functional_reqs.lower():
            integrations.append("Amazon SES for email")
        if "notification" in functional_reqs.lower():
            integrations.append("Amazon SNS for notifications")
        if "file" in functional_reqs.lower():
            integrations.append("Amazon S3 for file storage")
        
        return integrations
    
    def _derive_security_needs(self, requirements: Dict[str, Any]) -> List[str]:
        """Derive security needs from requirements."""
        security_needs = ["IAM roles and policies", "Encryption at rest and in transit"]
        
        if any("personal" in str(req).lower() for req in requirements.get("functional_requirements", [])):
            security_needs.append("Data privacy controls")
        
        if requirements.get("compliance_frameworks"):
            security_needs.append("Compliance monitoring and reporting")
        
        return security_needs