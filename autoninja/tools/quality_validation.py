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
    
    print("All quality validation tools implemented successfully!")