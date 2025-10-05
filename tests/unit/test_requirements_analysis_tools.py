"""
Unit tests for Requirements Analysis Tools
"""

import json
import pytest
from unittest.mock import Mock, patch
from autoninja.tools.requirements_analysis import (
    RequirementExtractionTool,
    ComplianceFrameworkDetectionTool,
    RequirementValidationTool,
    RequirementStructuringTool
)
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient


class TestRequirementExtractionTool:
    """Test cases for RequirementExtractionTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = RequirementExtractionTool()
    
    def test_extract_functional_requirements(self):
        """Test functional requirement extraction."""
        user_request = "I need an agent that can process customer emails and generate automated responses"
        
        result = self.tool._run(user_request)
        result_data = json.loads(result)
        
        assert "functional_requirements" in result_data
        assert len(result_data["functional_requirements"]) > 0
        assert any("process" in req.lower() for req in result_data["functional_requirements"])
    
    def test_detect_agent_type_conversational(self):
        """Test detection of conversational agent type."""
        user_request = "I want a customer service chatbot that can help users"
        
        result = self.tool._run(user_request)
        result_data = json.loads(result)
        
        assert result_data["agent_type_detected"] == "conversational"
    
    def test_detect_agent_type_analytical(self):
        """Test detection of analytical agent type."""
        user_request = "I need an agent to analyze sales data and generate reports"
        
        result = self.tool._run(user_request)
        result_data = json.loads(result)
        
        assert result_data["agent_type_detected"] == "analytical"
    
    def test_extract_constraints(self):
        """Test constraint extraction."""
        user_request = "I need a budget-friendly solution within 2 weeks using Python"
        
        result = self.tool._run(user_request)
        result_data = json.loads(result)
        
        constraints = result_data["constraints"]
        assert any("budget" in constraint.lower() for constraint in constraints)
        assert any("2 weeks" in constraint for constraint in constraints)
        assert any("python" in constraint.lower() for constraint in constraints)
    
    def test_extract_non_functional_requirements(self):
        """Test non-functional requirement extraction."""
        user_request = "The agent must respond within 2 seconds and be secure with encrypted data"
        
        result = self.tool._run(user_request)
        result_data = json.loads(result)
        
        nfr = result_data["non_functional_requirements"]
        assert "performance" in nfr
        assert "security" in nfr
    
    def test_with_knowledge_base_client(self):
        """Test tool with knowledge base client."""
        # Create a mock that passes type validation
        mock_kb_instance = Mock(spec=BedrockKnowledgeBaseClient)
        mock_kb_instance.search_knowledge_base.return_value = [
            Mock(content="Similar pattern found", relevance_score=0.8)
        ]
        
        tool = RequirementExtractionTool(knowledge_base_client=mock_kb_instance)
        result = tool._run("I need a customer service agent")
        result_data = json.loads(result)
        
        assert "similar_patterns" in result_data
        assert len(result_data["similar_patterns"]) > 0


class TestComplianceFrameworkDetectionTool:
    """Test cases for ComplianceFrameworkDetectionTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = ComplianceFrameworkDetectionTool()
    
    def test_detect_hipaa_compliance(self):
        """Test HIPAA compliance detection."""
        requirements_text = "I need an agent to handle patient health information securely"
        
        result = self.tool._run(requirements_text)
        result_data = json.loads(result)
        
        frameworks = result_data["compliance_frameworks"]
        assert any(framework["name"] == "HIPAA" for framework in frameworks)
    
    def test_detect_gdpr_compliance(self):
        """Test GDPR compliance detection."""
        requirements_text = "The agent will process personal data from European customers"
        
        result = self.tool._run(requirements_text)
        result_data = json.loads(result)
        
        frameworks = result_data["compliance_frameworks"]
        assert any(framework["name"] == "GDPR" for framework in frameworks)
    
    def test_detect_financial_compliance(self):
        """Test financial compliance detection."""
        requirements_text = "Agent for processing payment transactions and financial data"
        
        result = self.tool._run(requirements_text, industry="financial")
        result_data = json.loads(result)
        
        frameworks = result_data["compliance_frameworks"]
        framework_names = [f["name"] for f in frameworks]
        assert "PCI DSS" in framework_names or "SOX" in framework_names
    
    def test_detect_security_standards(self):
        """Test security standards detection."""
        requirements_text = "Need ISO 27001 compliant security management system"
        
        result = self.tool._run(requirements_text)
        result_data = json.loads(result)
        
        standards = result_data["security_standards"]
        assert any(standard["name"] == "ISO 27001" for standard in standards)
    
    def test_generate_recommendations(self):
        """Test compliance recommendations generation."""
        requirements_text = "Agent handling sensitive customer data with GDPR requirements"
        
        result = self.tool._run(requirements_text)
        result_data = json.loads(result)
        
        recommendations = result_data["recommendations"]
        assert len(recommendations) > 0
        assert any("audit logging" in rec.lower() for rec in recommendations)


class TestRequirementValidationTool:
    """Test cases for RequirementValidationTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = RequirementValidationTool()
    
    def test_check_completeness_full(self):
        """Test completeness check with full requirements."""
        requirements = {
            "functional_requirements": ["Process data", "Generate reports"],
            "non_functional_requirements": {"performance": ["Fast response"]},
            "constraints": ["Budget under $1000"],
            "success_criteria": ["95% accuracy"]
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        assert result_data["completeness_score"] == 100.0
    
    def test_check_completeness_partial(self):
        """Test completeness check with partial requirements."""
        requirements = {
            "functional_requirements": ["Process data"],
            "constraints": ["Budget constraint"]
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        assert result_data["completeness_score"] == 50.0  # 2 out of 4 sections
    
    def test_identify_missing_elements(self):
        """Test identification of missing elements."""
        requirements = {
            "functional_requirements": ["Handle data processing"]
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        missing = result_data["missing_elements"]
        assert "Success criteria not defined" in missing
        assert "Security requirements not specified for data handling" in missing
    
    def test_assess_feasibility(self):
        """Test feasibility assessment."""
        requirements = {
            "functional_requirements": ["Simple task 1", "Simple task 2"],
            "non_functional_requirements": {}
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        feasibility = result_data["feasibility_assessment"]
        assert "complexity_score" in feasibility
        assert "complexity_level" in feasibility
        assert feasibility["complexity_level"] in ["low", "medium", "high"]
    
    def test_check_consistency_issues(self):
        """Test consistency issue detection."""
        requirements = {
            "functional_requirements": ["Complex AI processing"] * 15,  # Many requirements
            "constraints": ["urgent timeline", "budget constraint"]
        }
        
        result = self.tool._run(requirements)
        result_data = json.loads(result)
        
        issues = result_data["consistency_issues"]
        assert len(issues) > 0


class TestRequirementStructuringTool:
    """Test cases for RequirementStructuringTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = RequirementStructuringTool()
    
    def test_create_user_stories(self):
        """Test user story creation."""
        requirements = {
            "functional_requirements": ["process customer emails", "generate responses"],
            "agent_type_detected": "conversational"
        }
        
        result = self.tool._run(requirements, template_type="user_story")
        result_data = json.loads(result)
        
        user_stories = result_data["user_stories"]
        assert len(user_stories) == 2
        assert all("As a conversational" in story["story"] for story in user_stories)
        assert all("acceptance_criteria" in story for story in user_stories)
    
    def test_create_technical_spec(self):
        """Test technical specification creation."""
        requirements = {
            "functional_requirements": ["data processing"],
            "non_functional_requirements": {"performance": ["fast"]},
            "constraints": ["AWS only"],
            "agent_type_detected": "analytical"
        }
        
        result = self.tool._run(requirements, template_type="technical_spec")
        result_data = json.loads(result)
        
        tech_spec = result_data["technical_specification"]
        assert "system_overview" in tech_spec
        assert "functional_requirements" in tech_spec
        assert "architecture_considerations" in tech_spec
    
    def test_create_acceptance_criteria(self):
        """Test acceptance criteria creation."""
        requirements = {
            "functional_requirements": ["validate input data", "process requests"]
        }
        
        result = self.tool._run(requirements, template_type="acceptance_criteria")
        result_data = json.loads(result)
        
        criteria = result_data["acceptance_criteria"]
        assert len(criteria) == 2
        assert all("criteria" in criterion for criterion in criteria)
    
    def test_categorize_requirements(self):
        """Test requirement categorization."""
        processing_req = "process customer data"
        interaction_req = "respond to user queries"
        
        processing_category = self.tool._categorize_requirement(processing_req)
        interaction_category = self.tool._categorize_requirement(interaction_req)
        
        assert processing_category == "processing"
        assert interaction_category == "interaction"
    
    def test_assess_complexity(self):
        """Test complexity assessment."""
        simple_req = "save data"
        complex_req = "analyze customer behavior using machine learning algorithms"
        
        simple_complexity = self.tool._assess_requirement_complexity(simple_req)
        complex_complexity = self.tool._assess_requirement_complexity(complex_req)
        
        assert simple_complexity == "low"
        assert complex_complexity == "high"
    
    def test_comprehensive_structure(self):
        """Test comprehensive requirement structuring."""
        requirements = {
            "functional_requirements": ["process data", "generate reports"],
            "non_functional_requirements": {"performance": ["fast response"]},
            "constraints": ["budget friendly"],
            "success_criteria": ["high accuracy"],
            "agent_type_detected": "analytical"
        }
        
        result = self.tool._run(requirements, template_type="comprehensive")
        result_data = json.loads(result)
        
        structured = result_data["structured_requirements"]
        assert "overview" in structured
        assert "functional_requirements" in structured
        assert "user_stories" in structured
        assert "technical_specification" in structured


if __name__ == "__main__":
    pytest.main([__file__])