#!/usr/bin/env python3
"""
Demo script for Deployment Manager Agent - ACTUAL AWS DEPLOYMENT EXECUTION

This script demonstrates the Deployment Manager Agent ACTUALLY DEPLOYING to AWS by:
1. Creating a mock Quality Validator output with real generated code
2. Running the Deployment Manager Agent to EXECUTE real deployments
3. Displaying the ACTUAL deployment results (real AWS resource ARNs/IDs)
4. Showing the deployment execution logs with real AWS resources
"""

import json
import logging
from datetime import datetime, UTC
from pathlib import Path

from autoninja.agents.deployment_manager import create_deployment_manager_agent
from autoninja.models.state import AgentOutput
from autoninja.core.logging_config import setup_logging


def create_mock_quality_validator_output() -> AgentOutput:
    """Create a mock Quality Validator output with real generated code for deployment testing."""
    
    # Include the actual generated code that would come from the Code Generator
    generated_code = {
        "bedrock_agent_config": {
            "agent_name": "CustomerServiceBot",
            "description": "AI agent for customer service inquiries",
            "foundation_model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "instruction": "You are a helpful customer service agent that assists with order inquiries, returns, and general product questions.",
            "action_groups": ["customer_support_actions"],
            "knowledge_bases": []
        },
        "action_groups": [
            {
                "name": "customer_support_actions",
                "description": "Core customer support functionality",
                "api_schema": {
                    "openapi": "3.0.0",
                    "info": {"title": "Customer Support API", "version": "1.0.0"},
                    "paths": {
                        "/order-status": {
                            "post": {
                                "summary": "Get order status",
                                "parameters": [{"name": "order_id", "in": "body", "required": True}]
                            }
                        }
                    }
                },
                "lambda_function": "customer-support-handler"
            }
        ],
        "lambda_functions": [
            {
                "function_name": "customer-support-handler",
                "runtime": "python3.11",
                "handler": "index.lambda_handler",
                "code": '''import json
def lambda_handler(event, context):
    """Handle customer support requests."""
    try:
        request_body = json.loads(event.get('body', '{}'))
        action = request_body.get('action')
        
        if action == 'get_order_status':
            order_id = request_body.get('order_id')
            if not order_id:
                return {'statusCode': 400, 'body': json.dumps({'error': 'order_id required'})}
            return {'statusCode': 200, 'body': json.dumps({'order_id': order_id, 'status': 'shipped'})}
        
        return {'statusCode': 400, 'body': json.dumps({'error': 'Unknown action'})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
''',
                "environment_variables": {"LOG_LEVEL": "INFO", "REGION": "us-east-1"}
            }
        ],
        "cloudformation_templates": {
            "main_template": {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Description": "Customer Service Bot Infrastructure",
                "Resources": {
                    "CustomerSupportFunction": {
                        "Type": "AWS::Lambda::Function",
                        "Properties": {
                            "Runtime": "python3.11",
                            "Handler": "index.lambda_handler",
                            "Code": {"ZipFile": "# Lambda code"},
                            "Role": {"Ref": "LambdaRole"}
                        }
                    },
                    "LambdaRole": {
                        "Type": "AWS::IAM::Role",
                        "Properties": {
                            "AssumeRolePolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [{
                                    "Effect": "Allow",
                                    "Principal": {"Service": "lambda.amazonaws.com"},
                                    "Action": "sts:AssumeRole"
                                }]
                            }
                        }
                    }
                }
            }
        },
        "iam_policies": [
            {
                "policy_name": "CustomerSupportPolicy",
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {"Effect": "Allow", "Action": ["logs:*"], "Resource": "*"},
                        {"Effect": "Allow", "Action": ["bedrock:InvokeModel"], "Resource": "*"}
                    ]
                }
            }
        ]
    }
    
    mock_validation_result = {
        "generated_code": generated_code,  # Include the actual generated code
        "code_quality_analysis": {
            "python_code_quality": {
                "pylint_score": 8.5,
                "black_formatting": "PASS",
                "mypy_type_checking": "PASS",
                "issues_found": ["Minor: Consider adding more docstrings"],
                "recommendations": ["Add comprehensive docstrings to all functions"]
            },
            "overall_code_score": 8.5
        },
        "cloudformation_validation": {
            "template_validation": {
                "syntax_valid": True,
                "cfn_lint_score": 9.0,
                "aws_cli_validation": "PASS",
                "issues_found": []
            },
            "best_practices_score": 9.0
        },
        "security_scan_results": {
            "vulnerability_scan": {
                "high_severity": 0,
                "medium_severity": 1,
                "low_severity": 2,
                "security_score": 8.0
            },
            "security_recommendations": ["Enable encryption at rest for DynamoDB"]
        },
        "aws_best_practices": {
            "well_architected_compliance": {
                "security": 8.5,
                "reliability": 8.0,
                "performance": 7.5,
                "cost_optimization": 8.0,
                "operational_excellence": 7.5
            },
            "overall_compliance_score": 8.0
        },
        "performance_assessment": {
            "performance_score": 7.5,
            "optimization_opportunities": ["Consider using provisioned concurrency for Lambda"]
        },
        "compliance_validation": {
            "framework_compliance": {"SOC2": "PASS", "GDPR": "PARTIAL"},
            "compliance_score": 8.0
        },
        "overall_quality_score": 8.2,
        "critical_issues": [],
        "blocking_issues": [],
        "recommendations": [
            "Add comprehensive docstrings to all functions",
            "Enable encryption at rest for DynamoDB",
            "Consider using provisioned concurrency for Lambda"
        ],
        "production_readiness": {
            "ready_for_deployment": True,
            "confidence_level": "high",
            "deployment_risk": "low"
        },
        "validation_summary": "Quality validation completed successfully with high confidence",
        "validation_method": "comprehensive_analysis"
    }
    
    return AgentOutput(
        agent_name="quality_validator",
        execution_id="test_quality_validator_001",
        input_data={
            "code_generator_output": {"mock": "data"},
            "session_id": "demo_session_001",
            "additional_context": {}
        },
        output=AgentOutput.Output(
            result=mock_validation_result,
            confidence_score=0.85,
            reasoning="Comprehensive quality validation completed with high scores across all categories",
            recommendations=[
                "Add comprehensive docstrings to all functions",
                "Enable encryption at rest for DynamoDB",
                "Consider using provisioned concurrency for Lambda"
            ]
        ),
        execution_metadata=AgentOutput.ExecutionMetadata(
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration_seconds=45.2,
            model_invocations=3,
            tokens_used=2500
        ),
        trace_data=AgentOutput.TraceData(
            trace_id="test_quality_validator_001",
            steps=[{
                "step": "quality_validation",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration": 45.2,
                "status": "completed"
            }]
        )
    )


def main():
    """Main demo function."""
    
    print("🚀 AutoNinja Deployment Manager Agent Demo - ACTUAL AWS DEPLOYMENT")
    print("=" * 70)
    
    # Setup logging
    setup_logging(log_level="INFO", enable_console_logging=True)
    
    # Create the Deployment Manager Agent
    print("\n1. Creating Deployment Manager Agent...")
    deployment_agent = create_deployment_manager_agent()
    
    # Display agent information
    agent_info = deployment_agent.get_agent_info()
    print(f"   Agent: {agent_info['agent_name']}")
    print(f"   Type: {agent_info['agent_type']}")
    print(f"   Description: {agent_info['description']}")
    print(f"   Tools: {', '.join(agent_info['tools'])}")
    
    # Create mock Quality Validator output
    print("\n2. Creating mock Quality Validator output...")
    quality_validator_output = create_mock_quality_validator_output()
    print(f"   Quality Score: {quality_validator_output.output.confidence_score}")
    print(f"   Production Ready: {quality_validator_output.output.result['production_readiness']['ready_for_deployment']}")
    
    # Execute Actual Deployment to AWS
    print("\n3. Executing Actual Deployment to AWS...")
    session_id = "demo_deployment_session_001"
    
    try:
        deployment_result = deployment_agent.execute_deployment(
            quality_validator_output=quality_validator_output,
            session_id=session_id,
            additional_context={
                "environment": "demo",
                "deployment_target": "aws",
                "monitoring_required": True
            }
        )
        
        print("   ✅ Actual deployment execution completed!")
        
        # Display results
        print(f"\n4. Actual Deployment Results:")
        print(f"   Execution ID: {deployment_result.execution_id}")
        print(f"   Confidence Score: {deployment_result.output.confidence_score:.2f}")
        print(f"   Processing Time: {deployment_result.execution_metadata.duration_seconds:.2f}s")
        
        # Display actual deployment results
        result = deployment_result.output.result
        print(f"\n   Actual AWS Resources Deployed:")
        
        # Show deployment executions
        deployment_executions = result.get('deployment_executions', {})
        if deployment_executions:
            print(f"   - CloudFormation Deployments: {len(deployment_executions)}")
            for exec_name, exec_result in deployment_executions.items():
                if isinstance(exec_result, dict) and exec_result.get('success'):
                    print(f"     ✅ {exec_name}: SUCCESS")
                    if 'stack_id' in exec_result:
                        print(f"        Stack ID: {exec_result['stack_id']}")
                    if 'agent_id' in exec_result:
                        print(f"        Agent ID: {exec_result['agent_id']}")
                else:
                    print(f"     ❌ {exec_name}: FAILED")
        
        # Show deployment artifacts
        deployment_artifacts = result.get('deployment_artifacts', {})
        if deployment_artifacts:
            print(f"\n   Real AWS Resource Artifacts:")
            if deployment_artifacts.get('stack_arns'):
                print(f"   - CloudFormation Stacks: {len(deployment_artifacts['stack_arns'])}")
                for arn in deployment_artifacts['stack_arns'][:2]:  # Show first 2
                    print(f"     {arn}")
            if deployment_artifacts.get('agent_endpoints'):
                print(f"   - Bedrock Agent Endpoints: {len(deployment_artifacts['agent_endpoints'])}")
                for endpoint in deployment_artifacts['agent_endpoints'][:2]:
                    print(f"     {endpoint}")
            if deployment_artifacts.get('dashboard_urls'):
                print(f"   - CloudWatch Dashboards: {len(deployment_artifacts['dashboard_urls'])}")
                for url in deployment_artifacts['dashboard_urls'][:2]:
                    print(f"     {url}")
        
        # Display recommendations
        if deployment_result.output.recommendations:
            print(f"\n   Deployment Recommendations:")
            for i, rec in enumerate(deployment_result.output.recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Display operational documentation
        print(f"\n5. Operational Documentation Generated:")
        operational_docs = result.get('operational_documentation', {})
        if operational_docs:
            for doc_name in operational_docs.keys():
                print(f"   - {doc_name}")
        else:
            print(f"   - No operational documentation generated")
        
        # Show deployment scripts
        deployment_scripts = result.get('deployment_scripts', {})
        if deployment_scripts:
            print(f"   Deployment Scripts:")
            for script_name in deployment_scripts.keys():
                print(f"   - {script_name}")
        
        # Show monitoring configuration
        monitoring_config = result.get('monitoring_configuration', {})
        if monitoring_config:
            print(f"   Monitoring Configuration:")
            dashboards = monitoring_config.get('cloudwatch_dashboards', [])
            alarms = monitoring_config.get('alarms', [])
            print(f"   - Dashboards: {len(dashboards)}")
            print(f"   - Alarms: {len(alarms)}")
        
        # Show operational documentation
        operational_docs = result.get('operational_documentation', {})
        if operational_docs:
            print(f"   Operational Documentation:")
            for doc_name in operational_docs.keys():
                print(f"   - {doc_name}")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        logging.error(f"Deployment Manager demo failed: {str(e)}")
    
    # Show log file information
    print(f"\n6. Log Files Generated:")
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = [
            "deployment_manager.log",
            "bedrock_inference.log", 
            "autoninja.log",
            "errors.log"
        ]
        
        for log_file in log_files:
            log_path = log_dir / log_file
            if log_path.exists():
                size = log_path.stat().st_size
                print(f"   - {log_file}: {size} bytes")
            else:
                print(f"   - {log_file}: Not created")
    
    print(f"\n✅ Demo completed! Check the logs directory for detailed execution logs.")
    print(f"📁 Log files are in: {Path('logs').absolute()}")


if __name__ == "__main__":
    main()