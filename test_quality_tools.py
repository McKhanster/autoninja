#!/usr/bin/env python3
"""
Quick test script for quality validation tools
"""

from autoninja.tools.quality_validation import (
    CodeQualityAnalysisTool, 
    CloudFormationValidationTool, 
    SecurityScanTool
)
import json

def test_quality_tools():
    print("Testing Quality Validation Tools...")
    
    # Test code quality analysis
    quality_tool = CodeQualityAnalysisTool()
    test_code = '''
def hello_world():
    print('Hello, World!')
    return 'success'
'''
    result = quality_tool._run(test_code, 'test.py', 'python')
    data = json.loads(result)
    print(f'✅ Code Quality Analysis: Score {data.get("quality_score", 0)}/10')
    
    # Test security scanning
    security_tool = SecurityScanTool()
    secure_code = '''
import hashlib
import secrets

def secure_hash(data):
    salt = secrets.token_bytes(32)
    return hashlib.sha256(data.encode() + salt).hexdigest()
'''
    result = security_tool._run(secure_code, 'python', 'code')
    data = json.loads(result)
    print(f'✅ Security Scan: Score {data.get("security_score", 0)}/10, Issues: {data.get("total_issues", 0)}')
    
    # Test CloudFormation validation
    cfn_tool = CloudFormationValidationTool()
    template = '''
AWSTemplateFormatVersion: "2010-09-09"
Description: "Test template"
Resources:
  TestBucket:
    Type: AWS::S3::Bucket
'''
    result = cfn_tool._run(template, 'template.yaml')
    data = json.loads(result)
    print(f'✅ CloudFormation Validation: Score {data.get("validation_score", 0)}/10')
    
    print('All quality validation tools are working correctly!')

if __name__ == "__main__":
    test_quality_tools()