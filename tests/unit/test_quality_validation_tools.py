"""
Unit tests for Quality Validation Tools

Tests for code quality analysis, CloudFormation validation,
and security scanning tools.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from autoninja.tools.quality_validation import (
    CodeQualityAnalysisTool,
    CloudFormationValidationTool,
    SecurityScanTool,
    AWSBestPracticesValidationTool,
    PerformanceAssessmentTool,
    ComplianceValidationTool
)


class TestCodeQualityAnalysisTool:
    """Test cases for CodeQualityAnalysisTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CodeQualityAnalysisTool()
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        assert self.tool.name == "code_quality_analyzer"
        assert "pylint" in self.tool.description
        assert "black" in self.tool.description
        assert "mypy" in self.tool.description
    
    def test_unsupported_language(self):
        """Test handling of unsupported programming languages."""
        result = self.tool._run("console.log('hello');", "test.js", "javascript")
        result_data = json.loads(result)
        
        assert "error" in result_data
        assert "not supported" in result_data["error"]
        assert result_data["quality_score"] == 0
    
    @patch('subprocess.run')
    def test_pylint_analysis_success(self, mock_run):
        """Test successful pylint analysis."""
        # Mock pylint output
        mock_run.return_value = MagicMock(
            stdout='[]',
            stderr='Your code has been rated at 8.5/10',
            returncode=0
        )
        
        with patch('tempfile.NamedTemporaryFile'), patch('os.unlink'):
            result = self.tool._run("print('hello world')", "test.py", "python")
            result_data = json.loads(result)
        
        assert result_data["quality_score"] > 0
        assert result_data["pylint_analysis"]["score"] == 8.5
        assert result_data["pylint_analysis"]["status"] == "PASS"
    
    @patch('subprocess.run')
    def test_pylint_analysis_with_errors(self, mock_run):
        """Test pylint analysis with errors."""
        # Mock pylint output with errors
        mock_run.return_value = MagicMock(
            stdout='[{"type": "error", "message": "syntax error", "line": 1}]',
            stderr='Your code has been rated at 3.2/10',
            returncode=1
        )
        
        with patch('tempfile.NamedTemporaryFile'), patch('os.unlink'):
            result = self.tool._run("invalid python code", "test.py", "python")
            result_data = json.loads(result)
        
        assert result_data["pylint_analysis"]["score"] == 3.2
        assert result_data["pylint_analysis"]["errors"] == 1
        assert result_data["pylint_analysis"]["status"] == "FAIL"
    
    @patch('subprocess.run')
    def test_black_formatting_check_pass(self, mock_run):
        """Test black formatting check that passes."""
        mock_run.return_value = MagicMock(
            stdout='',
            stderr='',
            returncode=0
        )
        
        with patch('tempfile.NamedTemporaryFile'), patch('os.unlink'):
            result = self.tool._run("print('hello')", "test.py", "python")
            result_data = json.loads(result)
        
        assert result_data["black_formatting"]["is_formatted"] is True
        assert result_data["black_formatting"]["status"] == "PASS"
    
    @patch('subprocess.run')
    def test_black_formatting_check_fail(self, mock_run):
        """Test black formatting check that fails."""
        mock_run.return_value = MagicMock(
            stdout='--- test.py\n+++ test.py\n@@ -1 +1 @@\n-print( "hello" )\n+print("hello")',
            stderr='',
            returncode=1
        )
        
        with patch('tempfile.NamedTemporaryFile'), patch('os.unlink'):
            result = self.tool._run('print( "hello" )', "test.py", "python")
            result_data = json.loads(result)
        
        assert result_data["black_formatting"]["is_formatted"] is False
        assert result_data["black_formatting"]["status"] == "FAIL"
        assert "diff" in result_data["black_formatting"]
    
    @patch('subprocess.run')
    def test_mypy_type_checking_pass(self, mock_run):
        """Test mypy type checking that passes."""
        mock_run.return_value = MagicMock(
            stdout='',
            stderr='',
            returncode=0
        )
        
        with patch('tempfile.NamedTemporaryFile'), patch('os.unlink'):
            result = self.tool._run("def hello() -> str:\n    return 'hello'", "test.py", "python")
            result_data = json.loads(result)
        
        assert result_data["mypy_type_checking"]["has_type_errors"] is False
        assert result_data["mypy_type_checking"]["status"] == "PASS"
    
    @patch('subprocess.run')
    def test_mypy_type_checking_with_errors(self, mock_run):
        """Test mypy type checking with errors."""
        mock_run.return_value = MagicMock(
            stdout='test.py:1: error: Function is missing a return type annotation',
            stderr='',
            returncode=1
        )
        
        with patch('tempfile.NamedTemporaryFile'), patch('os.unlink'):
            result = self.tool._run("def hello():\n    return 'hello'", "test.py", "python")
            result_data = json.loads(result)
        
        assert result_data["mypy_type_checking"]["has_type_errors"] is True
        assert result_data["mypy_type_checking"]["error_count"] == 1
        assert result_data["mypy_type_checking"]["status"] == "FAIL"
    
    def test_quality_score_calculation(self):
        """Test quality score calculation logic."""
        # Test with perfect scores
        pylint_results = {"status": "PASS", "score": 10.0}
        black_results = {"status": "PASS"}
        mypy_results = {"status": "PASS"}
        
        score = self.tool._calculate_quality_score(pylint_results, black_results, mypy_results)
        assert score == 10.0
        
        # Test with mixed results
        pylint_results = {"status": "PASS", "score": 7.0}
        black_results = {"status": "FAIL"}
        mypy_results = {"status": "FAIL", "error_count": 3}
        
        score = self.tool._calculate_quality_score(pylint_results, black_results, mypy_results)
        assert 0 <= score <= 10
    
    def test_recommendations_generation(self):
        """Test recommendations generation."""
        pylint_results = {"status": "PASS", "score": 6.0, "errors": 2, "warnings": 8}
        black_results = {"status": "FAIL"}
        mypy_results = {"status": "FAIL", "error_count": 5}
        
        recommendations = self.tool._generate_recommendations(pylint_results, black_results, mypy_results)
        
        assert len(recommendations) > 0
        assert any("pylint score" in rec for rec in recommendations)
        assert any("black" in rec for rec in recommendations)
        assert any("type checking" in rec for rec in recommendations)


class TestCloudFormationValidationTool:
    """Test cases for CloudFormationValidationTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CloudFormationValidationTool()
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        assert self.tool.name == "cloudformation_validator"
        assert "cfn-lint" in self.tool.description
        assert "AWS CLI" in self.tool.description
    
    def test_valid_yaml_syntax(self):
        """Test valid YAML syntax checking."""
        template = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Test template'
Resources:
  TestBucket:
    Type: AWS::S3::Bucket
"""
        syntax_check = self.tool._check_template_syntax(template, '.yaml')
        
        assert syntax_check["syntax_valid"] is True
        assert syntax_check["format"] == "YAML"
        assert syntax_check["status"] == "PASS"
    
    def test_valid_json_syntax(self):
        """Test valid JSON syntax checking."""
        template = '''
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Test template",
    "Resources": {
        "TestBucket": {
            "Type": "AWS::S3::Bucket"
        }
    }
}
'''
        syntax_check = self.tool._check_template_syntax(template, '.json')
        
        assert syntax_check["syntax_valid"] is True
        assert syntax_check["format"] == "JSON"
        assert syntax_check["status"] == "PASS"
    
    def test_invalid_yaml_syntax(self):
        """Test invalid YAML syntax checking."""
        template = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Test template'
Resources:
  TestBucket:
    Type: AWS::S3::Bucket
      InvalidIndentation: true
"""
        syntax_check = self.tool._check_template_syntax(template, '.yaml')
        
        assert syntax_check["syntax_valid"] is False
        assert syntax_check["status"] == "FAIL"
        assert "error" in syntax_check
    
    def test_invalid_json_syntax(self):
        """Test invalid JSON syntax checking."""
        template = '''
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Test template",
    "Resources": {
        "TestBucket": {
            "Type": "AWS::S3::Bucket",
        }
    }
}
'''
        syntax_check = self.tool._check_template_syntax(template, '.json')
        
        assert syntax_check["syntax_valid"] is False
        assert syntax_check["status"] == "FAIL"
        assert "error" in syntax_check
    
    @patch('subprocess.run')
    def test_cfn_lint_success(self, mock_run):
        """Test successful cfn-lint validation."""
        mock_run.return_value = MagicMock(
            stdout='[]',
            stderr='',
            returncode=0
        )
        
        result = self.tool._run_cfn_lint('/tmp/test.yaml')
        
        assert result["total_violations"] == 0
        assert result["errors"] == 0
        assert result["status"] == "PASS"
    
    @patch('subprocess.run')
    def test_cfn_lint_with_violations(self, mock_run):
        """Test cfn-lint validation with violations."""
        violations = [
            {"Level": "Error", "Message": "Invalid resource type", "Rule": "E3001"},
            {"Level": "Warning", "Message": "Missing description", "Rule": "W2001"}
        ]
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps(violations),
            stderr='',
            returncode=1
        )
        
        result = self.tool._run_cfn_lint('/tmp/test.yaml')
        
        assert result["total_violations"] == 2
        assert result["errors"] == 1
        assert result["warnings"] == 1
        assert result["status"] == "FAIL"
    
    @patch('subprocess.run')
    def test_aws_cli_validation_success(self, mock_run):
        """Test successful AWS CLI validation."""
        template_info = {
            "Description": "Test template",
            "Parameters": [],
            "Capabilities": []
        }
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps(template_info),
            stderr='',
            returncode=0
        )
        
        result = self.tool._run_aws_validate('/tmp/test.yaml')
        
        assert result["is_valid"] is True
        assert result["status"] == "PASS"
        assert result["description"] == "Test template"
    
    @patch('subprocess.run')
    def test_aws_cli_validation_failure(self, mock_run):
        """Test AWS CLI validation failure."""
        mock_run.return_value = MagicMock(
            stdout='',
            stderr='ValidationError: Template format error',
            returncode=1
        )
        
        result = self.tool._run_aws_validate('/tmp/test.yaml')
        
        assert result["is_valid"] is False
        assert result["status"] == "FAIL"
        assert "ValidationError" in result["error"]
    
    def test_validation_score_calculation(self):
        """Test validation score calculation."""
        # Perfect scores
        cfn_lint_results = {"status": "PASS"}
        aws_cli_results = {"status": "PASS"}
        syntax_check = {"status": "PASS"}
        
        score = self.tool._calculate_validation_score(cfn_lint_results, aws_cli_results, syntax_check)
        assert score == 10.0
        
        # Mixed results
        cfn_lint_results = {"status": "FAIL", "errors": 1, "warnings": 2}
        aws_cli_results = {"status": "FAIL"}
        syntax_check = {"status": "PASS"}
        
        score = self.tool._calculate_validation_score(cfn_lint_results, aws_cli_results, syntax_check)
        assert 0 <= score <= 10


class TestSecurityScanTool:
    """Test cases for SecurityScanTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = SecurityScanTool()
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        assert self.tool.name == "security_scanner"
        assert "security analysis" in self.tool.description
    
    def test_python_security_scan_clean_code(self):
        """Test security scan on clean Python code."""
        clean_code = """
import hashlib
import secrets

def secure_function(data):
    # Use secure random
    salt = secrets.token_bytes(32)
    
    # Use secure hash
    hash_obj = hashlib.sha256()
    hash_obj.update(data.encode() + salt)
    
    return hash_obj.hexdigest()
"""
        
        result = self.tool._scan_python_security(clean_code)
        
        assert result["security_score"] >= 8.0
        assert result["total_issues"] == 0
        assert result["status"] == "PASS"
    
    def test_python_security_scan_vulnerable_code(self):
        """Test security scan on vulnerable Python code."""
        vulnerable_code = """
import os
import pickle

def vulnerable_function():
    password = "hardcoded_password_123"
    api_key = "sk-1234567890abcdef"
    
    # Dangerous functions
    eval("print('hello')")
    os.system("rm -rf /")
    pickle.loads(data)
    
    return password
"""
        
        result = self.tool._scan_python_security(vulnerable_code)
        
        assert result["security_score"] < 8.0
        assert result["total_issues"] > 0
        assert result["high_severity"] > 0
        assert result["status"] == "FAIL"
    
    def test_infrastructure_security_scan_secure_template(self):
        """Test security scan on secure infrastructure template."""
        secure_template = '''
{
    "Resources": {
        "SecureBucket": {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "PublicReadAccess": false,
                "PublicWriteAccess": false,
                "Encrypted": true
            }
        }
    }
}
'''
        
        result = self.tool._scan_infrastructure_security(secure_template, "json")
        
        assert result["security_score"] >= 8.0
        assert result["total_issues"] == 0
        assert result["status"] == "PASS"
    
    def test_infrastructure_security_scan_insecure_template(self):
        """Test security scan on insecure infrastructure template."""
        insecure_template = '''
{
    "Resources": {
        "InsecureBucket": {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "PublicReadAccess": true,
                "PublicWriteAccess": true,
                "Encrypted": false
            }
        },
        "InsecureSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "SecurityGroupIngress": [{
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "CidrIp": "0.0.0.0/0"
                }]
            }
        }
    }
}
'''
        
        result = self.tool._scan_infrastructure_security(insecure_template, "json")
        
        assert result["security_score"] < 8.0
        assert result["total_issues"] > 0
        assert result["high_severity"] > 0
        assert result["status"] == "FAIL"
    
    def test_security_recommendations_generation(self):
        """Test security recommendations generation."""
        high_issues = [
            {"message": "Critical vulnerability", "line": 1},
            {"message": "Another critical issue", "line": 5}
        ]
        medium_issues = [
            {"message": "Medium severity issue", "line": 10}
        ]
        low_issues = [
            {"message": "Low severity issue", "line": 15}
        ]
        
        recommendations = self.tool._generate_security_recommendations(high_issues, medium_issues, low_issues)
        
        assert len(recommendations) > 0
        assert any("CRITICAL" in rec for rec in recommendations)
        assert any("environment variables" in rec for rec in recommendations)
        assert any("least privilege" in rec for rec in recommendations)
    
    def test_unknown_scan_type(self):
        """Test handling of unknown scan type."""
        result = self.tool._run("test code", "python", "unknown_scan_type")
        result_data = json.loads(result)
        
        assert "error" in result_data
        assert "Unknown scan type" in result_data["error"]
    
    def test_unsupported_code_type(self):
        """Test handling of unsupported code type for security scanning."""
        result = self.tool._run("console.log('test');", "javascript", "code")
        result_data = json.loads(result)
        
        assert "error" in result_data
        assert "not yet implemented" in result_data["error"]


class TestAWSBestPracticesValidationTool:
    """Test cases for AWSBestPracticesValidationTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = AWSBestPracticesValidationTool()
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        assert self.tool.name == "aws_best_practices_validator"
        assert "AWS best practices" in self.tool.description
        assert "Well-Architected Framework" in self.tool.description
    
    def test_well_architected_validation_secure_template(self):
        """Test Well-Architected validation on secure template."""
        secure_template = '''
{
    "Resources": {
        "SecureDatabase": {
            "Type": "AWS::RDS::DBInstance",
            "Properties": {
                "MultiAZ": true,
                "BackupRetentionPeriod": 7,
                "StorageEncrypted": true,
                "VpcSecurityGroupIds": ["sg-12345"]
            }
        }
    }
}
'''
        
        result = self.tool._validate_well_architected_principles(secure_template)
        
        assert result["score"] >= 7.5
        assert result["status"] == "PASS"
        assert result["total_issues"] == 0
    
    def test_well_architected_validation_insecure_template(self):
        """Test Well-Architected validation on insecure template."""
        insecure_template = '''
{
    "Resources": {
        "InsecureDatabase": {
            "Type": "AWS::RDS::DBInstance",
            "Properties": {
                "MasterUsername": "admin",
                "MasterUserPassword": "password123",
                "MultiAZ": false,
                "BackupRetentionPeriod": 0,
                "VpcSecurityGroupIds": []
            }
        }
    }
}
'''
        
        result = self.tool._validate_well_architected_principles(insecure_template)
        
        assert result["score"] < 7.5
        assert result["status"] == "FAIL"
        assert result["total_issues"] > 0
        assert result["issues_by_pillar"]["Security"] > 0
        assert result["issues_by_pillar"]["Reliability"] > 0
    
    def test_security_best_practices_validation(self):
        """Test security best practices validation."""
        insecure_template = '''
{
    "Resources": {
        "InsecureResource": {
            "Properties": {
                "Encrypted": false,
                "SSLEnabled": false,
                "PubliclyAccessible": true,
                "LoggingEnabled": false
            }
        }
    }
}
'''
        
        result = self.tool._validate_security_best_practices(insecure_template)
        
        assert result["score"] < 8.0
        assert result["status"] == "FAIL"
        assert result["high_severity"] > 0
        assert result["total_issues"] > 0
    
    def test_best_practices_score_calculation(self):
        """Test best practices score calculation."""
        well_architected = {"score": 8.0}
        security = {"score": 9.0}
        cost = {"score": 7.0}
        reliability = {"score": 8.5}
        performance = {"score": 7.5}
        
        score = self.tool._calculate_best_practices_score(
            well_architected, security, cost, reliability, performance
        )
        
        # Expected: 8.0*0.3 + 9.0*0.25 + 7.0*0.15 + 8.5*0.15 + 7.5*0.15 = 8.075
        assert 8.0 <= score <= 8.2
    
    def test_best_practices_recommendations_generation(self):
        """Test best practices recommendations generation."""
        well_architected = {"score": 6.0}
        security = {"score": 7.0}
        cost = {"score": 7.5}
        reliability = {"score": 7.0}
        performance = {"score": 7.0}
        
        recommendations = self.tool._generate_best_practices_recommendations(
            well_architected, security, cost, reliability, performance
        )
        
        assert len(recommendations) > 0
        assert any("Well-Architected" in rec for rec in recommendations)
        assert any("security" in rec for rec in recommendations)


class TestPerformanceAssessmentTool:
    """Test cases for PerformanceAssessmentTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = PerformanceAssessmentTool()
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        assert self.tool.name == "performance_assessor"
        assert "performance characteristics" in self.tool.description
    
    def test_python_performance_assessment_good_code(self):
        """Test performance assessment on well-optimized Python code."""
        good_code = '''
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def process_data(items):
    # Good: Using list comprehension
    results = [item.upper() for item in items if item]
    
    # Good: Using context manager
    with open('file.txt', 'r') as f:
        data = f.read()
    
    return results
'''
        
        result = self.tool._assess_python_performance(good_code)
        
        assert result["performance_score"] >= 7.0
        assert result["status"] == "PASS"
        assert result["positive_findings"] > 0
    
    def test_python_performance_assessment_poor_code(self):
        """Test performance assessment on poorly optimized Python code."""
        poor_code = '''
import time

global_var = []

def slow_function(items):
    # Bad: Using range(len())
    for i in range(len(items)):
        item = items[i]
        
        # Bad: List concatenation in loop
        global_var += [item.upper()]
        
        # Bad: Multiple appends
        result = []
        result.append(item)
        result.append(item.lower())
        
        # Bad: Long sleep
        time.sleep(5)
    
    try:
        risky_operation()
    except:
        pass
    
    return global_var
'''
        
        result = self.tool._assess_python_performance(poor_code)
        
        assert result["performance_score"] <= 7.0
        assert result["status"] == "FAIL"
        assert result["total_issues"] > 0
        assert "Iteration" in result["issues_by_category"]
        assert "Timing" in result["issues_by_category"]
    
    def test_architecture_performance_assessment(self):
        """Test architecture performance assessment."""
        poor_arch_template = '''
{
    "Resources": {
        "SlowInstance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "InstanceType": "t2.nano"
            }
        },
        "SlowDatabase": {
            "Type": "AWS::DynamoDB::Table",
            "Properties": {
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1
                }
            }
        },
        "NoCaching": {
            "Properties": {
                "CachingEnabled": false
            }
        }
    }
}
'''
        
        result = self.tool._assess_architecture_performance(poor_arch_template)
        
        assert result["performance_score"] < 7.0
        assert result["status"] == "FAIL"
        assert result["total_issues"] > 0
        assert "Compute" in result["issues_by_category"]
        assert "Database" in result["issues_by_category"]
    
    def test_performance_recommendations_generation(self):
        """Test performance recommendations generation."""
        issues = [
            {"category": "Iteration", "message": "Slow iteration"},
            {"category": "Data Structures", "message": "Inefficient data structure"},
            {"category": "Timing", "message": "Long wait time"}
        ]
        positive_findings = []
        
        recommendations = self.tool._generate_performance_recommendations(issues, positive_findings)
        
        assert len(recommendations) > 0
        assert any("loops" in rec for rec in recommendations)
        assert any("data structure" in rec for rec in recommendations)
        assert any("asynchronous" in rec for rec in recommendations)


class TestComplianceValidationTool:
    """Test cases for ComplianceValidationTool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = ComplianceValidationTool()
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        assert self.tool.name == "compliance_validator"
        assert "compliance frameworks" in self.tool.description
        assert "SOC2" in self.tool.description
    
    def test_soc2_compliance_validation_compliant(self):
        """Test SOC2 compliance validation on compliant template."""
        compliant_template = '''
{
    "Resources": {
        "CompliantResource": {
            "Properties": {
                "Encrypted": true,
                "LoggingEnabled": true,
                "BackupRetentionPeriod": 30,
                "PubliclyAccessible": false,
                "MfaDelete": true
            }
        }
    }
}
'''
        
        result = self.tool._validate_soc2_compliance(compliant_template, "infrastructure")
        
        assert result["compliance_score"] >= 8.0
        assert result["status"] == "PASS"
        assert result["total_issues"] == 0
    
    def test_soc2_compliance_validation_non_compliant(self):
        """Test SOC2 compliance validation on non-compliant template."""
        non_compliant_template = '''
{
    "Resources": {
        "NonCompliantResource": {
            "Properties": {
                "Encrypted": false,
                "LoggingEnabled": false,
                "BackupRetentionPeriod": 0,
                "PubliclyAccessible": true,
                "MfaDelete": false
            }
        }
    }
}
'''
        
        result = self.tool._validate_soc2_compliance(non_compliant_template, "infrastructure")
        
        assert result["compliance_score"] < 8.0
        assert result["status"] == "FAIL"
        assert result["total_issues"] > 0
        assert "Security" in result["issues_by_criteria"]
        assert "Availability" in result["issues_by_criteria"]
    
    def test_hipaa_compliance_validation(self):
        """Test HIPAA compliance validation."""
        non_compliant_template = '''
{
    "Resources": {
        "PHIResource": {
            "Properties": {
                "Encrypted": false,
                "SSLEnabled": false,
                "LoggingEnabled": false,
                "PubliclyAccessible": true
            }
        }
    }
}
'''
        
        result = self.tool._validate_hipaa_compliance(non_compliant_template, "infrastructure")
        
        assert result["compliance_score"] < 8.5
        assert result["status"] == "FAIL"
        assert result["total_issues"] > 0
    
    def test_pci_compliance_validation(self):
        """Test PCI-DSS compliance validation."""
        non_compliant_template = '''
{
    "Resources": {
        "CardDataResource": {
            "Properties": {
                "Encrypted": false,
                "SSLEnabled": false,
                "LoggingEnabled": false
            }
        }
    }
}
'''
        
        result = self.tool._validate_pci_compliance(non_compliant_template, "infrastructure")
        
        assert result["compliance_score"] < 8.5
        assert result["status"] == "FAIL"
        assert result["total_issues"] > 0
    
    def test_gdpr_compliance_validation(self):
        """Test GDPR compliance validation."""
        non_compliant_template = '''
{
    "Resources": {
        "PersonalDataResource": {
            "Properties": {
                "Encrypted": false,
                "LoggingEnabled": false,
                "BackupRetentionPeriod": 9999
            }
        }
    }
}
'''
        
        result = self.tool._validate_gdpr_compliance(non_compliant_template, "infrastructure")
        
        assert result["compliance_score"] < 8.0
        assert result["status"] == "FAIL"
        assert result["total_issues"] > 0
    
    def test_unsupported_framework(self):
        """Test handling of unsupported compliance framework."""
        result = self.tool._run("test content", "UNKNOWN_FRAMEWORK", "code")
        result_data = json.loads(result)
        
        assert "error" in result_data
        assert "not supported" in result_data["error"]
    
    def test_compliance_recommendations_generation(self):
        """Test compliance recommendations generation."""
        issues = [
            {"criteria": "Security", "severity": "HIGH"},
            {"criteria": "Availability", "severity": "MEDIUM"}
        ]
        
        recommendations = self.tool._generate_soc2_recommendations(issues)
        
        assert len(recommendations) > 0
        assert any("encryption" in rec for rec in recommendations)
        assert any("logging" in rec for rec in recommendations)


if __name__ == "__main__":
    pytest.main([__file__])