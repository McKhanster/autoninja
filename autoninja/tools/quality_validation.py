"""
Quality Validation Tools for AutoNinja

LangChain tools for comprehensive code quality analysis, CloudFormation
template validation, and security scanning for generated agents.
"""

import json
import os
import tempfile
import subprocess
import re
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class CodeQualityAnalysisInput(BaseModel):
    """Input schema for code quality analysis tool."""
    code_content: str = Field(description="Python code content to analyze")
    file_name: str = Field(description="Name of the file being analyzed", default="generated_code.py")
    language: str = Field(description="Programming language", default="python")


class CloudFormationValidationInput(BaseModel):
    """Input schema for CloudFormation template validation tool."""
    template_content: str = Field(description="CloudFormation template content (JSON or YAML)")
    template_name: str = Field(description="Name of the template", default="template.yaml")


class SecurityScanInput(BaseModel):
    """Input schema for security scanning tool."""
    code_content: str = Field(description="Code content to scan for security issues")
    file_type: str = Field(description="Type of file (python, yaml, json)", default="python")
    scan_type: str = Field(description="Type of security scan (code, infrastructure)", default="code")


class AWSBestPracticesInput(BaseModel):
    """Input schema for AWS best practices validation tool."""
    template_content: str = Field(description="AWS CloudFormation template or code content")
    resource_type: str = Field(description="Type of AWS resource or service", default="general")
    validation_level: str = Field(description="Validation level (basic, comprehensive)", default="comprehensive")


class PerformanceAssessmentInput(BaseModel):
    """Input schema for performance assessment tool."""
    code_content: str = Field(description="Code content to assess for performance")
    language: str = Field(description="Programming language", default="python")
    assessment_type: str = Field(description="Type of assessment (code, architecture)", default="code")


class ComplianceValidationInput(BaseModel):
    """Input schema for compliance framework validation tool."""
    content: str = Field(description="Content to validate for compliance")
    framework: str = Field(description="Compliance framework (SOC2, HIPAA, PCI-DSS, GDPR)", default="SOC2")
    content_type: str = Field(description="Type of content (code, infrastructure, documentation)", default="code")


class CodeQualityAnalysisTool(BaseTool):
    """Tool for analyzing Python code quality using pylint, black, and mypy."""
    
    name: str = "code_quality_analyzer"
    description: str = """Analyze Python code quality using pylint for code analysis,
    black for formatting validation, and mypy for type checking."""
    
    args_schema: Type[BaseModel] = CodeQualityAnalysisInput
    
    def _run(self, code_content: str, file_name: str = "generated_code.py", language: str = "python") -> str:
        """Analyze code quality using multiple tools."""
        try:
            if language.lower() != "python":
                return json.dumps({
                    "error": f"Language '{language}' not supported. Only Python is currently supported.",
                    "quality_score": 0
                })
            
            # Create temporary file for analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code_content)
                temp_file_path = temp_file.name
            
            try:
                # Run quality analysis
                pylint_results = self._run_pylint(temp_file_path)
                black_results = self._run_black_check(temp_file_path)
                mypy_results = self._run_mypy(temp_file_path)
                
                # Calculate overall quality score
                quality_score = self._calculate_quality_score(pylint_results, black_results, mypy_results)
                
                # Generate recommendations
                recommendations = self._generate_recommendations(pylint_results, black_results, mypy_results)
                
                result = {
                    "file_name": file_name,
                    "language": language,
                    "quality_score": quality_score,
                    "pylint_analysis": pylint_results,
                    "black_formatting": black_results,
                    "mypy_type_checking": mypy_results,
                    "recommendations": recommendations,
                    "overall_status": "PASS" if quality_score >= 7.0 else "FAIL"
                }
                
                return json.dumps(result, indent=2)
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            return json.dumps({
                "error": f"Error analyzing code quality: {str(e)}",
                "quality_score": 0
            })
    
    def _run_pylint(self, file_path: str) -> Dict[str, Any]:
        """Run pylint analysis on the code."""
        try:
            # Run pylint with JSON output
            result = subprocess.run(
                ['pylint', '--output-format=json', '--score=yes', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse JSON output
            if result.stdout:
                try:
                    messages = json.loads(result.stdout)
                except json.JSONDecodeError:
                    messages = []
            else:
                messages = []
            
            # Extract score from stderr (pylint outputs score to stderr)
            score_match = re.search(r'Your code has been rated at ([\d.-]+)/10', result.stderr)
            score = float(score_match.group(1)) if score_match else 0.0
            
            # Categorize messages
            errors = [msg for msg in messages if msg.get('type') == 'error']
            warnings = [msg for msg in messages if msg.get('type') == 'warning']
            conventions = [msg for msg in messages if msg.get('type') == 'convention']
            refactors = [msg for msg in messages if msg.get('type') == 'refactor']
            
            return {
                "score": score,
                "total_messages": len(messages),
                "errors": len(errors),
                "warnings": len(warnings),
                "conventions": len(conventions),
                "refactors": len(refactors),
                "error_details": errors[:5],  # Top 5 errors
                "warning_details": warnings[:5],  # Top 5 warnings
                "status": "PASS" if score >= 7.0 else "FAIL"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "error": "Pylint analysis timed out",
                "score": 0,
                "status": "ERROR"
            }
        except FileNotFoundError:
            return {
                "error": "Pylint not installed. Install with: pip install pylint",
                "score": 0,
                "status": "ERROR"
            }
        except Exception as e:
            return {
                "error": f"Pylint analysis failed: {str(e)}",
                "score": 0,
                "status": "ERROR"
            }
    
    def _run_black_check(self, file_path: str) -> Dict[str, Any]:
        """Check code formatting with black."""
        try:
            # Run black in check mode
            result = subprocess.run(
                ['black', '--check', '--diff', file_path],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            is_formatted = result.returncode == 0
            diff_output = result.stdout if result.stdout else ""
            
            return {
                "is_formatted": is_formatted,
                "diff": diff_output,
                "status": "PASS" if is_formatted else "FAIL",
                "message": "Code is properly formatted" if is_formatted else "Code needs formatting"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "error": "Black formatting check timed out",
                "status": "ERROR"
            }
        except FileNotFoundError:
            return {
                "error": "Black not installed. Install with: pip install black",
                "status": "ERROR"
            }
        except Exception as e:
            return {
                "error": f"Black formatting check failed: {str(e)}",
                "status": "ERROR"
            }
    
    def _run_mypy(self, file_path: str) -> Dict[str, Any]:
        """Run mypy type checking."""
        try:
            # Run mypy with JSON output
            result = subprocess.run(
                ['mypy', '--show-error-codes', '--no-error-summary', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse mypy output
            errors = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and ':' in line:
                        errors.append(line.strip())
            
            has_errors = len(errors) > 0
            
            return {
                "has_type_errors": has_errors,
                "error_count": len(errors),
                "errors": errors[:10],  # Top 10 errors
                "status": "PASS" if not has_errors else "FAIL",
                "message": "No type errors found" if not has_errors else f"Found {len(errors)} type errors"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "error": "Mypy type checking timed out",
                "status": "ERROR"
            }
        except FileNotFoundError:
            return {
                "error": "Mypy not installed. Install with: pip install mypy",
                "status": "ERROR"
            }
        except Exception as e:
            return {
                "error": f"Mypy type checking failed: {str(e)}",
                "status": "ERROR"
            }
    
    def _calculate_quality_score(self, pylint_results: Dict, black_results: Dict, mypy_results: Dict) -> float:
        """Calculate overall quality score from all analysis results."""
        score = 0.0
        
        # Pylint score (60% weight)
        if pylint_results.get("status") != "ERROR":
            pylint_score = pylint_results.get("score", 0)
            score += pylint_score * 0.6
        
        # Black formatting (20% weight)
        if black_results.get("status") == "PASS":
            score += 2.0  # 2 points for proper formatting
        elif black_results.get("status") != "ERROR":
            score += 1.0  # 1 point for minor formatting issues
        
        # Mypy type checking (20% weight)
        if mypy_results.get("status") == "PASS":
            score += 2.0  # 2 points for no type errors
        elif mypy_results.get("status") != "ERROR":
            error_count = mypy_results.get("error_count", 0)
            if error_count <= 2:
                score += 1.5  # Minor type issues
            elif error_count <= 5:
                score += 1.0  # Moderate type issues
            else:
                score += 0.5  # Major type issues
        
        return min(10.0, max(0.0, score))
    
    def _generate_recommendations(self, pylint_results: Dict, black_results: Dict, mypy_results: Dict) -> List[str]:
        """Generate improvement recommendations based on analysis results."""
        recommendations = []
        
        # Pylint recommendations
        if pylint_results.get("status") != "ERROR":
            score = pylint_results.get("score", 0)
            if score < 7.0:
                recommendations.append(f"Improve pylint score from {score}/10 to at least 7.0/10")
            
            if pylint_results.get("errors", 0) > 0:
                recommendations.append(f"Fix {pylint_results['errors']} pylint errors")
            
            if pylint_results.get("warnings", 0) > 5:
                recommendations.append(f"Address {pylint_results['warnings']} pylint warnings")
        
        # Black recommendations
        if black_results.get("status") == "FAIL":
            recommendations.append("Run 'black <filename>' to fix code formatting")
        
        # Mypy recommendations
        if mypy_results.get("status") == "FAIL":
            error_count = mypy_results.get("error_count", 0)
            recommendations.append(f"Fix {error_count} type checking errors")
            recommendations.append("Add type hints to improve code maintainability")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Code quality is excellent! Consider adding more comprehensive docstrings.")
        
        return recommendations


class CloudFormationValidationTool(BaseTool):
    """Tool for validating CloudFormation templates using cfn-lint and AWS CLI."""
    
    name: str = "cloudformation_validator"
    description: str = """Validate CloudFormation templates using cfn-lint for
    comprehensive template analysis and AWS CLI for syntax validation."""
    
    args_schema: Type[BaseModel] = CloudFormationValidationInput
    
    def _run(self, template_content: str, template_name: str = "template.yaml") -> str:
        """Validate CloudFormation template."""
        try:
            # Create temporary file for validation
            file_extension = '.yaml' if template_name.endswith('.yaml') or template_name.endswith('.yml') else '.json'
            
            with tempfile.NamedTemporaryFile(mode='w', suffix=file_extension, delete=False) as temp_file:
                temp_file.write(template_content)
                temp_file_path = temp_file.name
            
            try:
                # Run validations
                cfn_lint_results = self._run_cfn_lint(temp_file_path)
                aws_cli_results = self._run_aws_validate(temp_file_path)
                syntax_check = self._check_template_syntax(template_content, file_extension)
                
                # Calculate validation score
                validation_score = self._calculate_validation_score(cfn_lint_results, aws_cli_results, syntax_check)
                
                # Generate recommendations
                recommendations = self._generate_cfn_recommendations(cfn_lint_results, aws_cli_results, syntax_check)
                
                result = {
                    "template_name": template_name,
                    "validation_score": validation_score,
                    "cfn_lint_analysis": cfn_lint_results,
                    "aws_cli_validation": aws_cli_results,
                    "syntax_check": syntax_check,
                    "recommendations": recommendations,
                    "overall_status": "PASS" if validation_score >= 8.0 else "FAIL"
                }
                
                return json.dumps(result, indent=2)
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            return json.dumps({
                "error": f"Error validating CloudFormation template: {str(e)}",
                "validation_score": 0
            })
    
    def _run_cfn_lint(self, file_path: str) -> Dict[str, Any]:
        """Run cfn-lint validation on the template."""
        try:
            # Run cfn-lint with JSON output
            result = subprocess.run(
                ['cfn-lint', '--format', 'json', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse JSON output
            if result.stdout:
                try:
                    violations = json.loads(result.stdout)
                except json.JSONDecodeError:
                    violations = []
            else:
                violations = []
            
            # Categorize violations
            errors = [v for v in violations if v.get('Level') == 'Error']
            warnings = [v for v in violations if v.get('Level') == 'Warning']
            info = [v for v in violations if v.get('Level') == 'Informational']
            
            return {
                "total_violations": len(violations),
                "errors": len(errors),
                "warnings": len(warnings),
                "informational": len(info),
                "error_details": errors[:5],  # Top 5 errors
                "warning_details": warnings[:5],  # Top 5 warnings
                "status": "PASS" if len(errors) == 0 else "FAIL"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "error": "cfn-lint validation timed out",
                "status": "ERROR"
            }
        except FileNotFoundError:
            return {
                "error": "cfn-lint not installed. Install with: pip install cfn-lint",
                "status": "ERROR"
            }
        except Exception as e:
            return {
                "error": f"cfn-lint validation failed: {str(e)}",
                "status": "ERROR"
            }
    
    def _run_aws_validate(self, file_path: str) -> Dict[str, Any]:
        """Run AWS CLI template validation."""
        try:
            # Run AWS CLI validate-template
            result = subprocess.run(
                ['aws', 'cloudformation', 'validate-template', '--template-body', f'file://{file_path}'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            is_valid = result.returncode == 0
            
            if is_valid and result.stdout:
                try:
                    template_info = json.loads(result.stdout)
                    return {
                        "is_valid": True,
                        "description": template_info.get("Description", ""),
                        "parameters": template_info.get("Parameters", []),
                        "capabilities": template_info.get("Capabilities", []),
                        "status": "PASS"
                    }
                except json.JSONDecodeError:
                    pass
            
            error_message = result.stderr if result.stderr else "Unknown validation error"
            
            return {
                "is_valid": False,
                "error": error_message,
                "status": "FAIL"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "error": "AWS CLI validation timed out",
                "status": "ERROR"
            }
        except FileNotFoundError:
            return {
                "error": "AWS CLI not installed or not configured",
                "status": "ERROR"
            }
        except Exception as e:
            return {
                "error": f"AWS CLI validation failed: {str(e)}",
                "status": "ERROR"
            }
    
    def _check_template_syntax(self, template_content: str, file_extension: str) -> Dict[str, Any]:
        """Check basic template syntax."""
        try:
            if file_extension == '.json':
                json.loads(template_content)
                return {
                    "syntax_valid": True,
                    "format": "JSON",
                    "status": "PASS"
                }
            else:
                # Basic YAML syntax check
                import yaml
                yaml.safe_load(template_content)
                return {
                    "syntax_valid": True,
                    "format": "YAML",
                    "status": "PASS"
                }
                
        except json.JSONDecodeError as e:
            return {
                "syntax_valid": False,
                "format": "JSON",
                "error": str(e),
                "status": "FAIL"
            }
        except yaml.YAMLError as e:
            return {
                "syntax_valid": False,
                "format": "YAML",
                "error": str(e),
                "status": "FAIL"
            }
        except Exception as e:
            return {
                "syntax_valid": False,
                "error": str(e),
                "status": "ERROR"
            }
    
    def _calculate_validation_score(self, cfn_lint_results: Dict, aws_cli_results: Dict, syntax_check: Dict) -> float:
        """Calculate overall validation score."""
        score = 0.0
        
        # Syntax check (30% weight)
        if syntax_check.get("status") == "PASS":
            score += 3.0
        
        # AWS CLI validation (40% weight)
        if aws_cli_results.get("status") == "PASS":
            score += 4.0
        elif aws_cli_results.get("status") != "ERROR":
            score += 2.0  # Partial credit for attempting validation
        
        # cfn-lint validation (30% weight)
        if cfn_lint_results.get("status") == "PASS":
            score += 3.0
        elif cfn_lint_results.get("status") != "ERROR":
            errors = cfn_lint_results.get("errors", 0)
            warnings = cfn_lint_results.get("warnings", 0)
            
            if errors == 0:
                score += 2.5  # No errors, only warnings
            elif errors <= 2:
                score += 1.5  # Few errors
            else:
                score += 0.5  # Many errors
        
        return min(10.0, max(0.0, score))
    
    def _generate_cfn_recommendations(self, cfn_lint_results: Dict, aws_cli_results: Dict, syntax_check: Dict) -> List[str]:
        """Generate CloudFormation improvement recommendations."""
        recommendations = []
        
        # Syntax recommendations
        if syntax_check.get("status") == "FAIL":
            recommendations.append(f"Fix template syntax errors: {syntax_check.get('error', 'Unknown syntax error')}")
        
        # AWS CLI recommendations
        if aws_cli_results.get("status") == "FAIL":
            recommendations.append(f"Fix AWS validation errors: {aws_cli_results.get('error', 'Unknown validation error')}")
        
        # cfn-lint recommendations
        if cfn_lint_results.get("status") != "ERROR":
            errors = cfn_lint_results.get("errors", 0)
            warnings = cfn_lint_results.get("warnings", 0)
            
            if errors > 0:
                recommendations.append(f"Fix {errors} cfn-lint errors")
            
            if warnings > 5:
                recommendations.append(f"Address {warnings} cfn-lint warnings for better practices")
        
        # General recommendations
        if not recommendations:
            recommendations.append("CloudFormation template is valid! Consider adding more comprehensive resource tags.")
        
        return recommendations


class SecurityScanTool(BaseTool):
    """Tool for security scanning of code and infrastructure configurations."""
    
    name: str = "security_scanner"
    description: str = """Perform security analysis on code and infrastructure
    configurations to identify vulnerabilities and security best practices violations."""
    
    args_schema: Type[BaseModel] = SecurityScanInput
    
    def _run(self, code_content: str, file_type: str = "python", scan_type: str = "code") -> str:
        """Perform security scanning on the provided content."""
        try:
            if scan_type == "code":
                if file_type == "python":
                    results = self._scan_python_security(code_content)
                else:
                    results = {"error": f"Code security scanning for {file_type} not yet implemented"}
            elif scan_type == "infrastructure":
                results = self._scan_infrastructure_security(code_content, file_type)
            else:
                results = {"error": f"Unknown scan type: {scan_type}"}
            
            return json.dumps(results, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Error performing security scan: {str(e)}",
                "security_score": 0
            })
    
    def _scan_python_security(self, code_content: str) -> Dict[str, Any]:
        """Scan Python code for security vulnerabilities."""
        security_issues = []
        security_score = 10.0
        
        # Check for common security anti-patterns
        security_patterns = [
            {
                "pattern": r"eval\s*\(",
                "severity": "HIGH",
                "message": "Use of eval() can lead to code injection vulnerabilities",
                "score_deduction": 2.0
            },
            {
                "pattern": r"exec\s*\(",
                "severity": "HIGH", 
                "message": "Use of exec() can lead to code injection vulnerabilities",
                "score_deduction": 2.0
            },
            {
                "pattern": r"subprocess\.call\s*\([^)]*shell\s*=\s*True",
                "severity": "HIGH",
                "message": "subprocess.call with shell=True can lead to command injection",
                "score_deduction": 1.5
            },
            {
                "pattern": r"os\.system\s*\(",
                "severity": "HIGH",
                "message": "os.system() can lead to command injection vulnerabilities",
                "score_deduction": 1.5
            },
            {
                "pattern": r"pickle\.loads?\s*\(",
                "severity": "MEDIUM",
                "message": "pickle.load/loads can execute arbitrary code",
                "score_deduction": 1.0
            },
            {
                "pattern": r"input\s*\(",
                "severity": "LOW",
                "message": "input() can be dangerous in Python 2, consider validation",
                "score_deduction": 0.5
            },
            {
                "pattern": r"random\.random\s*\(",
                "severity": "LOW",
                "message": "random module is not cryptographically secure, use secrets module",
                "score_deduction": 0.3
            },
            {
                "pattern": r"hashlib\.md5\s*\(",
                "severity": "MEDIUM",
                "message": "MD5 is cryptographically broken, use SHA-256 or better",
                "score_deduction": 0.8
            },
            {
                "pattern": r"hashlib\.sha1\s*\(",
                "severity": "MEDIUM",
                "message": "SHA-1 is cryptographically weak, use SHA-256 or better",
                "score_deduction": 0.6
            },
            {
                "pattern": r"ssl\.create_default_context\s*\([^)]*check_hostname\s*=\s*False",
                "severity": "HIGH",
                "message": "Disabling SSL hostname verification is insecure",
                "score_deduction": 1.5
            }
        ]
        
        # Scan for security patterns
        for pattern_info in security_patterns:
            matches = re.finditer(pattern_info["pattern"], code_content, re.IGNORECASE)
            for match in matches:
                line_num = code_content[:match.start()].count('\n') + 1
                security_issues.append({
                    "severity": pattern_info["severity"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                security_score -= pattern_info["score_deduction"]
        
        # Check for hardcoded secrets patterns
        secret_patterns = [
            {
                "pattern": r"password\s*=\s*['\"][^'\"]{8,}['\"]",
                "message": "Potential hardcoded password detected"
            },
            {
                "pattern": r"api[_-]?key\s*=\s*['\"][^'\"]{16,}['\"]",
                "message": "Potential hardcoded API key detected"
            },
            {
                "pattern": r"secret[_-]?key\s*=\s*['\"][^'\"]{16,}['\"]",
                "message": "Potential hardcoded secret key detected"
            },
            {
                "pattern": r"aws[_-]?access[_-]?key[_-]?id\s*=\s*['\"]AKIA[A-Z0-9]{16}['\"]",
                "message": "Potential hardcoded AWS access key detected"
            }
        ]
        
        for pattern_info in secret_patterns:
            matches = re.finditer(pattern_info["pattern"], code_content, re.IGNORECASE)
            for match in matches:
                line_num = code_content[:match.start()].count('\n') + 1
                security_issues.append({
                    "severity": "HIGH",
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)[:50] + "..." if len(match.group(0)) > 50 else match.group(0)
                })
                security_score -= 1.5
        
        # Ensure score doesn't go below 0
        security_score = max(0.0, security_score)
        
        # Categorize issues by severity
        high_issues = [issue for issue in security_issues if issue["severity"] == "HIGH"]
        medium_issues = [issue for issue in security_issues if issue["severity"] == "MEDIUM"]
        low_issues = [issue for issue in security_issues if issue["severity"] == "LOW"]
        
        # Generate recommendations
        recommendations = self._generate_security_recommendations(high_issues, medium_issues, low_issues)
        
        return {
            "scan_type": "python_code_security",
            "security_score": round(security_score, 1),
            "total_issues": len(security_issues),
            "high_severity": len(high_issues),
            "medium_severity": len(medium_issues),
            "low_severity": len(low_issues),
            "issues": security_issues,
            "recommendations": recommendations,
            "status": "PASS" if security_score >= 8.0 else "FAIL"
        }
    
    def _scan_infrastructure_security(self, template_content: str, file_type: str) -> Dict[str, Any]:
        """Scan infrastructure templates for security issues."""
        security_issues = []
        security_score = 10.0
        
        if file_type in ["yaml", "yml", "json"]:
            # CloudFormation/AWS security patterns
            security_patterns = [
                {
                    "pattern": r'"Effect"\s*:\s*"Allow"[^}]*"Resource"\s*:\s*"\*"',
                    "severity": "HIGH",
                    "message": "Overly permissive IAM policy with wildcard resource",
                    "score_deduction": 2.0
                },
                {
                    "pattern": r'"Action"\s*:\s*"\*"',
                    "severity": "HIGH",
                    "message": "Overly permissive IAM policy with wildcard action",
                    "score_deduction": 2.0
                },
                {
                    "pattern": r'"PublicReadAccess"\s*:\s*true',
                    "severity": "MEDIUM",
                    "message": "S3 bucket configured for public read access",
                    "score_deduction": 1.0
                },
                {
                    "pattern": r'"PublicWriteAccess"\s*:\s*true',
                    "severity": "HIGH",
                    "message": "S3 bucket configured for public write access",
                    "score_deduction": 2.0
                },
                {
                    "pattern": r'"CidrIp"\s*:\s*"0\.0\.0\.0/0"',
                    "severity": "MEDIUM",
                    "message": "Security group allows access from anywhere (0.0.0.0/0)",
                    "score_deduction": 1.0
                },
                {
                    "pattern": r'"Encrypted"\s*:\s*false',
                    "severity": "MEDIUM",
                    "message": "Resource not configured for encryption",
                    "score_deduction": 0.8
                }
            ]
            
            # Scan for security patterns
            for pattern_info in security_patterns:
                matches = re.finditer(pattern_info["pattern"], template_content, re.IGNORECASE)
                for match in matches:
                    line_num = template_content[:match.start()].count('\n') + 1
                    security_issues.append({
                        "severity": pattern_info["severity"],
                        "message": pattern_info["message"],
                        "line": line_num,
                        "code_snippet": match.group(0)
                    })
                    security_score -= pattern_info["score_deduction"]
        
        # Ensure score doesn't go below 0
        security_score = max(0.0, security_score)
        
        # Categorize issues by severity
        high_issues = [issue for issue in security_issues if issue["severity"] == "HIGH"]
        medium_issues = [issue for issue in security_issues if issue["severity"] == "MEDIUM"]
        low_issues = [issue for issue in security_issues if issue["severity"] == "LOW"]
        
        # Generate recommendations
        recommendations = self._generate_security_recommendations(high_issues, medium_issues, low_issues)
        
        return {
            "scan_type": "infrastructure_security",
            "file_type": file_type,
            "security_score": round(security_score, 1),
            "total_issues": len(security_issues),
            "high_severity": len(high_issues),
            "medium_severity": len(medium_issues),
            "low_severity": len(low_issues),
            "issues": security_issues,
            "recommendations": recommendations,
            "status": "PASS" if security_score >= 8.0 else "FAIL"
        }
    
    def _generate_security_recommendations(self, high_issues: List, medium_issues: List, low_issues: List) -> List[str]:
        """Generate security improvement recommendations."""
        recommendations = []
        
        if high_issues:
            recommendations.append(f"CRITICAL: Fix {len(high_issues)} high-severity security issues immediately")
            for issue in high_issues[:3]:  # Top 3 high-severity issues
                recommendations.append(f"  - {issue['message']} (line {issue['line']})")
        
        if medium_issues:
            recommendations.append(f"Address {len(medium_issues)} medium-severity security issues")
        
        if low_issues:
            recommendations.append(f"Consider addressing {len(low_issues)} low-severity security issues")
        
        # General security recommendations
        if not any([high_issues, medium_issues, low_issues]):
            recommendations.append("No obvious security issues detected. Consider additional security testing.")
        
        recommendations.extend([
            "Use environment variables or AWS Secrets Manager for sensitive data",
            "Implement least privilege access principles",
            "Enable encryption at rest and in transit",
            "Regularly update dependencies and scan for vulnerabilities",
            "Implement proper input validation and sanitization"
        ])
        
        return recommendations


class AWSBestPracticesValidationTool(BaseTool):
    """Tool for validating AWS best practices in CloudFormation templates and code."""
    
    name: str = "aws_best_practices_validator"
    description: str = """Validate AWS best practices in CloudFormation templates,
    code, and architecture configurations following AWS Well-Architected Framework."""
    
    args_schema: Type[BaseModel] = AWSBestPracticesInput
    
    def _run(self, template_content: str, resource_type: str = "general", validation_level: str = "comprehensive") -> str:
        """Validate AWS best practices."""
        try:
            # Run different validations based on content type
            well_architected_results = self._validate_well_architected_principles(template_content)
            security_best_practices = self._validate_security_best_practices(template_content)
            cost_optimization = self._validate_cost_optimization(template_content)
            reliability_practices = self._validate_reliability_practices(template_content)
            performance_practices = self._validate_performance_practices(template_content)
            
            # Calculate overall best practices score
            best_practices_score = self._calculate_best_practices_score(
                well_architected_results, security_best_practices, cost_optimization,
                reliability_practices, performance_practices
            )
            
            # Generate recommendations
            recommendations = self._generate_best_practices_recommendations(
                well_architected_results, security_best_practices, cost_optimization,
                reliability_practices, performance_practices
            )
            
            result = {
                "resource_type": resource_type,
                "validation_level": validation_level,
                "best_practices_score": best_practices_score,
                "well_architected_framework": well_architected_results,
                "security_best_practices": security_best_practices,
                "cost_optimization": cost_optimization,
                "reliability_practices": reliability_practices,
                "performance_practices": performance_practices,
                "recommendations": recommendations,
                "overall_status": "PASS" if best_practices_score >= 7.5 else "FAIL"
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Error validating AWS best practices: {str(e)}",
                "best_practices_score": 0
            })
    
    def _validate_well_architected_principles(self, content: str) -> Dict[str, Any]:
        """Validate against AWS Well-Architected Framework principles."""
        issues = []
        score = 10.0
        
        # Security pillar checks
        security_patterns = [
            {
                "pattern": r'"MasterUsername"\s*:\s*"[^"]*"',
                "message": "Database master username should be stored in Secrets Manager",
                "severity": "MEDIUM",
                "pillar": "Security",
                "score_deduction": 0.5
            },
            {
                "pattern": r'"MasterUserPassword"\s*:\s*"[^"]*"',
                "message": "Database password should be stored in Secrets Manager",
                "severity": "HIGH",
                "pillar": "Security",
                "score_deduction": 1.5
            },
            {
                "pattern": r'"VpcSecurityGroupIds"\s*:\s*\[\s*\]',
                "message": "Resources should be placed in security groups",
                "severity": "MEDIUM",
                "pillar": "Security",
                "score_deduction": 0.8
            }
        ]
        
        # Reliability pillar checks
        reliability_patterns = [
            {
                "pattern": r'"MultiAZ"\s*:\s*false',
                "message": "Enable Multi-AZ for high availability",
                "severity": "MEDIUM",
                "pillar": "Reliability",
                "score_deduction": 1.0
            },
            {
                "pattern": r'"BackupRetentionPeriod"\s*:\s*0',
                "message": "Enable backup retention for data durability",
                "severity": "HIGH",
                "pillar": "Reliability",
                "score_deduction": 1.5
            }
        ]
        
        # Performance pillar checks
        performance_patterns = [
            {
                "pattern": r'"InstanceType"\s*:\s*"t2\.micro"',
                "message": "Consider using newer generation instance types (t3, t4g)",
                "severity": "LOW",
                "pillar": "Performance",
                "score_deduction": 0.3
            }
        ]
        
        # Cost optimization pillar checks
        cost_patterns = [
            {
                "pattern": r'"StorageType"\s*:\s*"io1"',
                "message": "Consider gp3 storage for better cost-performance ratio",
                "severity": "LOW",
                "pillar": "Cost Optimization",
                "score_deduction": 0.3
            }
        ]
        
        all_patterns = security_patterns + reliability_patterns + performance_patterns + cost_patterns
        
        for pattern_info in all_patterns:
            matches = re.finditer(pattern_info["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "pillar": pattern_info["pillar"],
                    "severity": pattern_info["severity"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                score -= pattern_info["score_deduction"]
        
        score = max(0.0, score)
        
        return {
            "score": round(score, 1),
            "total_issues": len(issues),
            "issues_by_pillar": {
                "Security": len([i for i in issues if i["pillar"] == "Security"]),
                "Reliability": len([i for i in issues if i["pillar"] == "Reliability"]),
                "Performance": len([i for i in issues if i["pillar"] == "Performance"]),
                "Cost Optimization": len([i for i in issues if i["pillar"] == "Cost Optimization"]),
                "Operational Excellence": 0  # Could be extended
            },
            "issues": issues,
            "status": "PASS" if score >= 7.5 else "FAIL"
        }
    
    def _validate_security_best_practices(self, content: str) -> Dict[str, Any]:
        """Validate security best practices."""
        issues = []
        score = 10.0
        
        security_checks = [
            {
                "pattern": r'"Encrypted"\s*:\s*false',
                "message": "Enable encryption at rest for data protection",
                "severity": "HIGH",
                "score_deduction": 1.5
            },
            {
                "pattern": r'"SSLEnabled"\s*:\s*false',
                "message": "Enable SSL/TLS for data in transit",
                "severity": "HIGH",
                "score_deduction": 1.5
            },
            {
                "pattern": r'"PubliclyAccessible"\s*:\s*true',
                "message": "Avoid making resources publicly accessible",
                "severity": "HIGH",
                "score_deduction": 2.0
            },
            {
                "pattern": r'"LoggingEnabled"\s*:\s*false',
                "message": "Enable logging for audit and monitoring",
                "severity": "MEDIUM",
                "score_deduction": 0.8
            }
        ]
        
        for check in security_checks:
            matches = re.finditer(check["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "severity": check["severity"],
                    "message": check["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                score -= check["score_deduction"]
        
        score = max(0.0, score)
        
        return {
            "score": round(score, 1),
            "total_issues": len(issues),
            "high_severity": len([i for i in issues if i["severity"] == "HIGH"]),
            "medium_severity": len([i for i in issues if i["severity"] == "MEDIUM"]),
            "low_severity": len([i for i in issues if i["severity"] == "LOW"]),
            "issues": issues,
            "status": "PASS" if score >= 8.0 else "FAIL"
        }
    
    def _validate_cost_optimization(self, content: str) -> Dict[str, Any]:
        """Validate cost optimization practices."""
        issues = []
        score = 10.0
        
        cost_checks = [
            {
                "pattern": r'"DeletionPolicy"\s*:\s*"Retain"',
                "message": "Review retention policies to avoid unnecessary costs",
                "severity": "LOW",
                "score_deduction": 0.3
            },
            {
                "pattern": r'"AllocatedStorage"\s*:\s*[5-9]\d{3,}',
                "message": "Large storage allocation detected, consider if necessary",
                "severity": "MEDIUM",
                "score_deduction": 0.5
            }
        ]
        
        for check in cost_checks:
            matches = re.finditer(check["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "severity": check["severity"],
                    "message": check["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                score -= check["score_deduction"]
        
        score = max(0.0, score)
        
        return {
            "score": round(score, 1),
            "total_issues": len(issues),
            "issues": issues,
            "status": "PASS" if score >= 8.0 else "FAIL"
        }
    
    def _validate_reliability_practices(self, content: str) -> Dict[str, Any]:
        """Validate reliability practices."""
        issues = []
        score = 10.0
        
        reliability_checks = [
            {
                "pattern": r'"AvailabilityZone"\s*:\s*"[^"]*[ab]"',
                "message": "Consider using multiple AZs for high availability",
                "severity": "MEDIUM",
                "score_deduction": 1.0
            },
            {
                "pattern": r'"AutoScalingGroupName"',
                "message": "Good: Using Auto Scaling for reliability",
                "severity": "POSITIVE",
                "score_deduction": -0.5  # Bonus points
            }
        ]
        
        for check in reliability_checks:
            matches = re.finditer(check["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "severity": check["severity"],
                    "message": check["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                score -= check["score_deduction"]
        
        score = min(10.0, max(0.0, score))
        
        return {
            "score": round(score, 1),
            "total_issues": len([i for i in issues if i["severity"] != "POSITIVE"]),
            "positive_practices": len([i for i in issues if i["severity"] == "POSITIVE"]),
            "issues": issues,
            "status": "PASS" if score >= 8.0 else "FAIL"
        }
    
    def _validate_performance_practices(self, content: str) -> Dict[str, Any]:
        """Validate performance practices."""
        issues = []
        score = 10.0
        
        performance_checks = [
            {
                "pattern": r'"CachingEnabled"\s*:\s*false',
                "message": "Consider enabling caching for better performance",
                "severity": "MEDIUM",
                "score_deduction": 0.8
            },
            {
                "pattern": r'"ReadReplicaDBInstanceIdentifier"',
                "message": "Good: Using read replicas for performance",
                "severity": "POSITIVE",
                "score_deduction": -0.5  # Bonus points
            }
        ]
        
        for check in performance_checks:
            matches = re.finditer(check["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "severity": check["severity"],
                    "message": check["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                score -= check["score_deduction"]
        
        score = min(10.0, max(0.0, score))
        
        return {
            "score": round(score, 1),
            "total_issues": len([i for i in issues if i["severity"] != "POSITIVE"]),
            "positive_practices": len([i for i in issues if i["severity"] == "POSITIVE"]),
            "issues": issues,
            "status": "PASS" if score >= 8.0 else "FAIL"
        }
    
    def _calculate_best_practices_score(self, well_architected: Dict, security: Dict, 
                                      cost: Dict, reliability: Dict, performance: Dict) -> float:
        """Calculate overall best practices score."""
        scores = [
            well_architected.get("score", 0) * 0.3,  # 30% weight
            security.get("score", 0) * 0.25,         # 25% weight
            cost.get("score", 0) * 0.15,             # 15% weight
            reliability.get("score", 0) * 0.15,      # 15% weight
            performance.get("score", 0) * 0.15       # 15% weight
        ]
        
        return round(sum(scores), 1)
    
    def _generate_best_practices_recommendations(self, well_architected: Dict, security: Dict,
                                               cost: Dict, reliability: Dict, performance: Dict) -> List[str]:
        """Generate AWS best practices recommendations."""
        recommendations = []
        
        # Well-Architected Framework recommendations
        if well_architected.get("score", 0) < 7.5:
            recommendations.append("Review AWS Well-Architected Framework principles")
            
        # Security recommendations
        if security.get("score", 0) < 8.0:
            recommendations.append("Implement additional security best practices")
            recommendations.append("Enable encryption at rest and in transit")
            recommendations.append("Review IAM permissions and apply least privilege")
            
        # Cost optimization recommendations
        if cost.get("score", 0) < 8.0:
            recommendations.append("Review resource sizing and utilization")
            recommendations.append("Consider reserved instances for predictable workloads")
            
        # Reliability recommendations
        if reliability.get("score", 0) < 8.0:
            recommendations.append("Implement multi-AZ deployment for high availability")
            recommendations.append("Enable automated backups and disaster recovery")
            
        # Performance recommendations
        if performance.get("score", 0) < 8.0:
            recommendations.append("Consider caching strategies for better performance")
            recommendations.append("Review instance types and storage configurations")
        
        if not recommendations:
            recommendations.append("Excellent adherence to AWS best practices!")
            
        return recommendations


class PerformanceAssessmentTool(BaseTool):
    """Tool for assessing code and architecture performance characteristics."""
    
    name: str = "performance_assessor"
    description: str = """Assess performance characteristics of code and architecture
    configurations to identify optimization opportunities."""
    
    args_schema: Type[BaseModel] = PerformanceAssessmentInput
    
    def _run(self, code_content: str, language: str = "python", assessment_type: str = "code") -> str:
        """Assess performance characteristics."""
        try:
            if assessment_type == "code":
                if language == "python":
                    results = self._assess_python_performance(code_content)
                else:
                    results = {"error": f"Performance assessment for {language} not yet implemented"}
            elif assessment_type == "architecture":
                results = self._assess_architecture_performance(code_content)
            else:
                results = {"error": f"Unknown assessment type: {assessment_type}"}
            
            return json.dumps(results, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Error assessing performance: {str(e)}",
                "performance_score": 0
            })
    
    def _assess_python_performance(self, code_content: str) -> Dict[str, Any]:
        """Assess Python code performance."""
        issues = []
        performance_score = 10.0
        
        # Performance anti-patterns
        performance_patterns = [
            {
                "pattern": r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\([^)]+\)\s*\)",
                "message": "Use direct iteration instead of range(len())",
                "severity": "MEDIUM",
                "category": "Iteration",
                "score_deduction": 0.5
            },
            {
                "pattern": r"\+\s*=.*\[.*\]",
                "message": "List concatenation in loop can be inefficient, consider list comprehension",
                "severity": "MEDIUM",
                "category": "Data Structures",
                "score_deduction": 0.8
            },
            {
                "pattern": r"\.append\s*\([^)]*\)\s*\n.*\.append",
                "message": "Multiple appends can be optimized with extend() or list comprehension",
                "severity": "LOW",
                "category": "Data Structures",
                "score_deduction": 0.3
            },
            {
                "pattern": r"time\.sleep\s*\(\s*[1-9]\d*\s*\)",
                "message": "Long sleep times can impact performance",
                "severity": "MEDIUM",
                "category": "Timing",
                "score_deduction": 1.0
            },
            {
                "pattern": r"global\s+\w+",
                "message": "Global variables can impact performance and maintainability",
                "severity": "LOW",
                "category": "Variables",
                "score_deduction": 0.3
            },
            {
                "pattern": r"try:\s*\n.*\n.*except.*:\s*\n.*pass",
                "message": "Broad exception handling can hide performance issues",
                "severity": "LOW",
                "category": "Error Handling",
                "score_deduction": 0.4
            }
        ]
        
        # Positive performance patterns
        positive_patterns = [
            {
                "pattern": r"@lru_cache|@cache",
                "message": "Good: Using caching for performance optimization",
                "category": "Caching",
                "score_bonus": 0.5
            },
            {
                "pattern": r"list\s*\([^)]*for\s+[^)]*in\s+[^)]*\)",
                "message": "Good: Using list comprehension",
                "category": "Data Structures",
                "score_bonus": 0.3
            },
            {
                "pattern": r"with\s+\w+\s*\([^)]*\)\s+as\s+\w+:",
                "message": "Good: Using context managers for resource management",
                "category": "Resource Management",
                "score_bonus": 0.2
            }
        ]
        
        # Check for performance issues
        for pattern_info in performance_patterns:
            matches = re.finditer(pattern_info["pattern"], code_content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = code_content[:match.start()].count('\n') + 1
                issues.append({
                    "severity": pattern_info["severity"],
                    "category": pattern_info["category"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                performance_score -= pattern_info["score_deduction"]
        
        # Check for positive patterns
        positive_findings = []
        for pattern_info in positive_patterns:
            matches = re.finditer(pattern_info["pattern"], code_content, re.IGNORECASE)
            for match in matches:
                line_num = code_content[:match.start()].count('\n') + 1
                positive_findings.append({
                    "category": pattern_info["category"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                performance_score += pattern_info["score_bonus"]
        
        performance_score = min(10.0, max(0.0, performance_score))
        
        # Generate recommendations
        recommendations = self._generate_performance_recommendations(issues, positive_findings)
        
        return {
            "assessment_type": "python_code_performance",
            "performance_score": round(performance_score, 1),
            "total_issues": len(issues),
            "issues_by_category": self._categorize_issues(issues),
            "positive_findings": len(positive_findings),
            "issues": issues,
            "positive_practices": positive_findings,
            "recommendations": recommendations,
            "status": "PASS" if performance_score >= 7.0 else "FAIL"
        }
    
    def _assess_architecture_performance(self, template_content: str) -> Dict[str, Any]:
        """Assess architecture performance characteristics."""
        issues = []
        performance_score = 10.0
        
        # Architecture performance patterns
        arch_patterns = [
            {
                "pattern": r'"InstanceType"\s*:\s*"t2\.nano"',
                "message": "Very small instance type may cause performance bottlenecks",
                "severity": "MEDIUM",
                "category": "Compute",
                "score_deduction": 1.0
            },
            {
                "pattern": r'"ReadCapacityUnits"\s*:\s*[1-5]',
                "message": "Low DynamoDB read capacity may cause throttling",
                "severity": "MEDIUM",
                "category": "Database",
                "score_deduction": 0.8
            },
            {
                "pattern": r'"WriteCapacityUnits"\s*:\s*[1-5]',
                "message": "Low DynamoDB write capacity may cause throttling",
                "severity": "MEDIUM",
                "category": "Database",
                "score_deduction": 0.8
            },
            {
                "pattern": r'"CachingEnabled"\s*:\s*false',
                "message": "Caching disabled, may impact performance",
                "severity": "MEDIUM",
                "category": "Caching",
                "score_deduction": 1.0
            }
        ]
        
        # Positive architecture patterns
        positive_arch_patterns = [
            {
                "pattern": r'"AutoScalingGroupName"',
                "message": "Good: Using Auto Scaling for performance and availability",
                "category": "Scaling",
                "score_bonus": 0.5
            },
            {
                "pattern": r'"LoadBalancerName"',
                "message": "Good: Using load balancing for performance distribution",
                "category": "Load Balancing",
                "score_bonus": 0.5
            },
            {
                "pattern": r'"CachingEnabled"\s*:\s*true',
                "message": "Good: Caching enabled for better performance",
                "category": "Caching",
                "score_bonus": 0.5
            }
        ]
        
        # Check for performance issues
        for pattern_info in arch_patterns:
            matches = re.finditer(pattern_info["pattern"], template_content, re.IGNORECASE)
            for match in matches:
                line_num = template_content[:match.start()].count('\n') + 1
                issues.append({
                    "severity": pattern_info["severity"],
                    "category": pattern_info["category"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                performance_score -= pattern_info["score_deduction"]
        
        # Check for positive patterns
        positive_findings = []
        for pattern_info in positive_arch_patterns:
            matches = re.finditer(pattern_info["pattern"], template_content, re.IGNORECASE)
            for match in matches:
                line_num = template_content[:match.start()].count('\n') + 1
                positive_findings.append({
                    "category": pattern_info["category"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                performance_score += pattern_info["score_bonus"]
        
        performance_score = min(10.0, max(0.0, performance_score))
        
        # Generate recommendations
        recommendations = self._generate_architecture_performance_recommendations(issues, positive_findings)
        
        return {
            "assessment_type": "architecture_performance",
            "performance_score": round(performance_score, 1),
            "total_issues": len(issues),
            "issues_by_category": self._categorize_issues(issues),
            "positive_findings": len(positive_findings),
            "issues": issues,
            "positive_practices": positive_findings,
            "recommendations": recommendations,
            "status": "PASS" if performance_score >= 7.0 else "FAIL"
        }
    
    def _categorize_issues(self, issues: List[Dict]) -> Dict[str, int]:
        """Categorize issues by category."""
        categories = {}
        for issue in issues:
            category = issue.get("category", "Other")
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _generate_performance_recommendations(self, issues: List[Dict], positive_findings: List[Dict]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        # Category-specific recommendations
        categories = self._categorize_issues(issues)
        
        if categories.get("Iteration", 0) > 0:
            recommendations.append("Optimize loops and iterations using list comprehensions or built-in functions")
            
        if categories.get("Data Structures", 0) > 0:
            recommendations.append("Review data structure usage and consider more efficient alternatives")
            
        if categories.get("Timing", 0) > 0:
            recommendations.append("Review sleep/wait times and consider asynchronous alternatives")
            
        if categories.get("Caching", 0) > 0:
            recommendations.append("Implement caching strategies for frequently accessed data")
        
        # General recommendations
        if len(issues) == 0:
            recommendations.append("Code shows good performance practices!")
        else:
            recommendations.append("Consider profiling code to identify actual bottlenecks")
            recommendations.append("Use appropriate data structures for your use case")
            recommendations.append("Consider algorithmic complexity when processing large datasets")
        
        return recommendations
    
    def _generate_architecture_performance_recommendations(self, issues: List[Dict], positive_findings: List[Dict]) -> List[str]:
        """Generate architecture performance recommendations."""
        recommendations = []
        
        categories = self._categorize_issues(issues)
        
        if categories.get("Compute", 0) > 0:
            recommendations.append("Review instance types and sizes for your workload requirements")
            
        if categories.get("Database", 0) > 0:
            recommendations.append("Review database capacity settings and consider auto-scaling")
            
        if categories.get("Caching", 0) > 0:
            recommendations.append("Implement caching layers (ElastiCache, CloudFront) for better performance")
        
        # General architecture recommendations
        if len(issues) == 0:
            recommendations.append("Architecture shows good performance characteristics!")
        else:
            recommendations.append("Consider implementing auto-scaling for variable workloads")
            recommendations.append("Use content delivery networks (CDN) for global performance")
            recommendations.append("Implement monitoring and alerting for performance metrics")
        
        return recommendations


class ComplianceValidationTool(BaseTool):
    """Tool for validating compliance with various regulatory frameworks."""
    
    name: str = "compliance_validator"
    description: str = """Validate content against compliance frameworks like
    SOC2, HIPAA, PCI-DSS, and GDPR requirements."""
    
    args_schema: Type[BaseModel] = ComplianceValidationInput
    
    def _run(self, content: str, framework: str = "SOC2", content_type: str = "code") -> str:
        """Validate compliance with specified framework."""
        try:
            if framework.upper() == "SOC2":
                results = self._validate_soc2_compliance(content, content_type)
            elif framework.upper() == "HIPAA":
                results = self._validate_hipaa_compliance(content, content_type)
            elif framework.upper() == "PCI-DSS":
                results = self._validate_pci_compliance(content, content_type)
            elif framework.upper() == "GDPR":
                results = self._validate_gdpr_compliance(content, content_type)
            else:
                results = {"error": f"Compliance framework '{framework}' not supported"}
            
            return json.dumps(results, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Error validating compliance: {str(e)}",
                "compliance_score": 0
            })
    
    def _validate_soc2_compliance(self, content: str, content_type: str) -> Dict[str, Any]:
        """Validate SOC2 compliance requirements."""
        issues = []
        compliance_score = 10.0
        
        # SOC2 Trust Service Criteria checks
        soc2_patterns = [
            {
                "pattern": r'"Encrypted"\s*:\s*false',
                "message": "SOC2 Security: Data should be encrypted at rest",
                "severity": "HIGH",
                "criteria": "Security",
                "score_deduction": 2.0
            },
            {
                "pattern": r'"LoggingEnabled"\s*:\s*false',
                "message": "SOC2 Availability: Logging should be enabled for monitoring",
                "severity": "HIGH",
                "criteria": "Availability",
                "score_deduction": 1.5
            },
            {
                "pattern": r'"BackupRetentionPeriod"\s*:\s*0',
                "message": "SOC2 Availability: Backup retention required for data recovery",
                "severity": "HIGH",
                "criteria": "Availability",
                "score_deduction": 2.0
            },
            {
                "pattern": r'"PubliclyAccessible"\s*:\s*true',
                "message": "SOC2 Security: Resources should not be publicly accessible",
                "severity": "HIGH",
                "criteria": "Security",
                "score_deduction": 2.0
            },
            {
                "pattern": r'"MfaDelete"\s*:\s*false',
                "message": "SOC2 Security: MFA should be enabled for critical operations",
                "severity": "MEDIUM",
                "criteria": "Security",
                "score_deduction": 1.0
            }
        ]
        
        # Check for SOC2 compliance issues
        for pattern_info in soc2_patterns:
            matches = re.finditer(pattern_info["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "framework": "SOC2",
                    "criteria": pattern_info["criteria"],
                    "severity": pattern_info["severity"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                compliance_score -= pattern_info["score_deduction"]
        
        compliance_score = max(0.0, compliance_score)
        
        # Categorize by SOC2 criteria
        criteria_counts = {}
        for issue in issues:
            criteria = issue["criteria"]
            criteria_counts[criteria] = criteria_counts.get(criteria, 0) + 1
        
        return {
            "framework": "SOC2",
            "content_type": content_type,
            "compliance_score": round(compliance_score, 1),
            "total_issues": len(issues),
            "issues_by_criteria": criteria_counts,
            "issues": issues,
            "recommendations": self._generate_soc2_recommendations(issues),
            "status": "PASS" if compliance_score >= 8.0 else "FAIL"
        }
    
    def _validate_hipaa_compliance(self, content: str, content_type: str) -> Dict[str, Any]:
        """Validate HIPAA compliance requirements."""
        issues = []
        compliance_score = 10.0
        
        # HIPAA Security Rule checks
        hipaa_patterns = [
            {
                "pattern": r'"Encrypted"\s*:\s*false',
                "message": "HIPAA Security Rule: PHI must be encrypted at rest",
                "severity": "HIGH",
                "rule": "Security Rule",
                "score_deduction": 2.5
            },
            {
                "pattern": r'"SSLEnabled"\s*:\s*false',
                "message": "HIPAA Security Rule: PHI must be encrypted in transit",
                "severity": "HIGH",
                "rule": "Security Rule",
                "score_deduction": 2.5
            },
            {
                "pattern": r'"LoggingEnabled"\s*:\s*false',
                "message": "HIPAA Security Rule: Access logging required for audit trails",
                "severity": "HIGH",
                "rule": "Security Rule",
                "score_deduction": 2.0
            },
            {
                "pattern": r'"PubliclyAccessible"\s*:\s*true',
                "message": "HIPAA Security Rule: PHI systems should not be publicly accessible",
                "severity": "HIGH",
                "rule": "Security Rule",
                "score_deduction": 2.5
            }
        ]
        
        # Check for HIPAA compliance issues
        for pattern_info in hipaa_patterns:
            matches = re.finditer(pattern_info["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "framework": "HIPAA",
                    "rule": pattern_info["rule"],
                    "severity": pattern_info["severity"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                compliance_score -= pattern_info["score_deduction"]
        
        compliance_score = max(0.0, compliance_score)
        
        return {
            "framework": "HIPAA",
            "content_type": content_type,
            "compliance_score": round(compliance_score, 1),
            "total_issues": len(issues),
            "issues": issues,
            "recommendations": self._generate_hipaa_recommendations(issues),
            "status": "PASS" if compliance_score >= 8.5 else "FAIL"
        }
    
    def _validate_pci_compliance(self, content: str, content_type: str) -> Dict[str, Any]:
        """Validate PCI-DSS compliance requirements."""
        issues = []
        compliance_score = 10.0
        
        # PCI-DSS requirements checks
        pci_patterns = [
            {
                "pattern": r'"Encrypted"\s*:\s*false',
                "message": "PCI-DSS Req 3: Cardholder data must be encrypted",
                "severity": "HIGH",
                "requirement": "Requirement 3",
                "score_deduction": 2.5
            },
            {
                "pattern": r'"SSLEnabled"\s*:\s*false',
                "message": "PCI-DSS Req 4: Encrypt transmission of cardholder data",
                "severity": "HIGH",
                "requirement": "Requirement 4",
                "score_deduction": 2.5
            },
            {
                "pattern": r'"LoggingEnabled"\s*:\s*false',
                "message": "PCI-DSS Req 10: Track and monitor access to network resources",
                "severity": "HIGH",
                "requirement": "Requirement 10",
                "score_deduction": 2.0
            }
        ]
        
        # Check for PCI compliance issues
        for pattern_info in pci_patterns:
            matches = re.finditer(pattern_info["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "framework": "PCI-DSS",
                    "requirement": pattern_info["requirement"],
                    "severity": pattern_info["severity"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                compliance_score -= pattern_info["score_deduction"]
        
        compliance_score = max(0.0, compliance_score)
        
        return {
            "framework": "PCI-DSS",
            "content_type": content_type,
            "compliance_score": round(compliance_score, 1),
            "total_issues": len(issues),
            "issues": issues,
            "recommendations": self._generate_pci_recommendations(issues),
            "status": "PASS" if compliance_score >= 8.5 else "FAIL"
        }
    
    def _validate_gdpr_compliance(self, content: str, content_type: str) -> Dict[str, Any]:
        """Validate GDPR compliance requirements."""
        issues = []
        compliance_score = 10.0
        
        # GDPR requirements checks
        gdpr_patterns = [
            {
                "pattern": r'"Encrypted"\s*:\s*false',
                "message": "GDPR Art 32: Personal data should be encrypted",
                "severity": "HIGH",
                "article": "Article 32",
                "score_deduction": 2.0
            },
            {
                "pattern": r'"LoggingEnabled"\s*:\s*false',
                "message": "GDPR Art 30: Records of processing activities required",
                "severity": "MEDIUM",
                "article": "Article 30",
                "score_deduction": 1.5
            },
            {
                "pattern": r'"BackupRetentionPeriod"\s*:\s*[0-9]{4,}',
                "message": "GDPR Art 5: Data retention should be limited to necessary period",
                "severity": "MEDIUM",
                "article": "Article 5",
                "score_deduction": 1.0
            }
        ]
        
        # Check for GDPR compliance issues
        for pattern_info in gdpr_patterns:
            matches = re.finditer(pattern_info["pattern"], content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    "framework": "GDPR",
                    "article": pattern_info["article"],
                    "severity": pattern_info["severity"],
                    "message": pattern_info["message"],
                    "line": line_num,
                    "code_snippet": match.group(0)
                })
                compliance_score -= pattern_info["score_deduction"]
        
        compliance_score = max(0.0, compliance_score)
        
        return {
            "framework": "GDPR",
            "content_type": content_type,
            "compliance_score": round(compliance_score, 1),
            "total_issues": len(issues),
            "issues": issues,
            "recommendations": self._generate_gdpr_recommendations(issues),
            "status": "PASS" if compliance_score >= 8.0 else "FAIL"
        }
    
    def _generate_soc2_recommendations(self, issues: List[Dict]) -> List[str]:
        """Generate SOC2 compliance recommendations."""
        recommendations = []
        
        criteria_counts = {}
        for issue in issues:
            criteria = issue.get("criteria", "Other")
            criteria_counts[criteria] = criteria_counts.get(criteria, 0) + 1
        
        if criteria_counts.get("Security", 0) > 0:
            recommendations.append("Implement encryption at rest and in transit")
            recommendations.append("Enable MFA for administrative access")
            recommendations.append("Restrict public access to resources")
        
        if criteria_counts.get("Availability", 0) > 0:
            recommendations.append("Enable comprehensive logging and monitoring")
            recommendations.append("Implement backup and disaster recovery procedures")
        
        if not issues:
            recommendations.append("Good SOC2 compliance posture!")
        
        recommendations.append("Conduct regular SOC2 compliance assessments")
        recommendations.append("Document security policies and procedures")
        
        return recommendations
    
    def _generate_hipaa_recommendations(self, issues: List[Dict]) -> List[str]:
        """Generate HIPAA compliance recommendations."""
        recommendations = []
        
        if issues:
            recommendations.append("Implement end-to-end encryption for PHI")
            recommendations.append("Enable comprehensive audit logging")
            recommendations.append("Restrict access to PHI on need-to-know basis")
            recommendations.append("Implement access controls and authentication")
        else:
            recommendations.append("Good HIPAA compliance posture!")
        
        recommendations.append("Conduct regular HIPAA risk assessments")
        recommendations.append("Train staff on HIPAA requirements")
        recommendations.append("Implement Business Associate Agreements (BAAs)")
        
        return recommendations
    
    def _generate_pci_recommendations(self, issues: List[Dict]) -> List[str]:
        """Generate PCI-DSS compliance recommendations."""
        recommendations = []
        
        if issues:
            recommendations.append("Encrypt cardholder data at rest and in transit")
            recommendations.append("Implement strong access controls")
            recommendations.append("Enable comprehensive logging and monitoring")
            recommendations.append("Regularly test security systems and processes")
        else:
            recommendations.append("Good PCI-DSS compliance posture!")
        
        recommendations.append("Conduct quarterly vulnerability scans")
        recommendations.append("Maintain secure network architecture")
        recommendations.append("Implement and maintain firewall configuration")
        
        return recommendations
    
    def _generate_gdpr_recommendations(self, issues: List[Dict]) -> List[str]:
        """Generate GDPR compliance recommendations."""
        recommendations = []
        
        if issues:
            recommendations.append("Implement privacy by design principles")
            recommendations.append("Enable data encryption and pseudonymization")
            recommendations.append("Implement data retention policies")
            recommendations.append("Enable audit logging for data processing")
        else:
            recommendations.append("Good GDPR compliance posture!")
        
        recommendations.append("Conduct Data Protection Impact Assessments (DPIAs)")
        recommendations.append("Implement data subject rights procedures")
        recommendations.append("Maintain records of processing activities")
        
        return recommendations


# For testing purposes
if __name__ == "__main__":
    # Test code quality analysis
    test_code = '''
import os
import subprocess

def unsafe_function():
    password = "hardcoded_password_123"
    eval("print('hello')")
    os.system("ls -la")
    return password

def better_function(user_input):
    # This is a better implementation
    result = subprocess.run(["ls", "-la"], capture_output=True, text=True)
    return result.stdout
'''
    
    quality_tool = CodeQualityAnalysisTool()
    result = quality_tool._run(test_code)
    print("✅ CodeQualityAnalysisTool test completed")
    
    # Test CloudFormation validation
    test_template = '''
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Test template'
Resources:
  TestBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: test-bucket
'''
    
    cfn_tool = CloudFormationValidationTool()
    result = cfn_tool._run(test_template)
    print("✅ CloudFormationValidationTool test completed")
    
    # Test security scanning
    security_tool = SecurityScanTool()
    result = security_tool._run(test_code, "python", "code")
    print("✅ SecurityScanTool test completed")
    
    # Test AWS best practices validation
    aws_tool = AWSBestPracticesValidationTool()
    result = aws_tool._run(test_template)
    print("✅ AWSBestPracticesValidationTool test completed")
    
    # Test performance assessment
    performance_tool = PerformanceAssessmentTool()
    result = performance_tool._run(test_code, "python", "code")
    print("✅ PerformanceAssessmentTool test completed")
    
    # Test compliance validation
    compliance_tool = ComplianceValidationTool()
    result = compliance_tool._run(test_template, "SOC2", "infrastructure")
    print("✅ ComplianceValidationTool test completed")
    
    print("All quality validation tools implemented successfully!")