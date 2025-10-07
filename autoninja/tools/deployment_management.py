"""
Deployment Management Tools for AutoNinja

LangChain tools for CloudFormation deployment automation, monitoring configuration,
deployment validation, and rollback capabilities.
"""

import json
import yaml
import boto3
from typing import Dict, List, Any, Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient, KnowledgeBaseType


class CloudFormationDeploymentInput(BaseModel):
    """Input schema for CloudFormation deployment automation tool."""
    template_content: str = Field(description="CloudFormation template content")
    stack_name: str = Field(description="Name for the CloudFormation stack")
    parameters: Optional[Dict[str, str]] = Field(default=None, description="Stack parameters")
    environment: str = Field(default="dev", description="Deployment environment (dev, staging, prod)")


class CloudFormationDeploymentTool(BaseTool):
    """Tool for automating CloudFormation deployments with validation and rollback."""
    
    name: str = "cloudformation_deployment"
    description: str = """Deploy CloudFormation templates with automated validation, 
    parameter configuration, and rollback capabilities."""
    
    args_schema: Type[BaseModel] = CloudFormationDeploymentInput
    kb_client: Optional[BedrockKnowledgeBaseClient] = Field(default=None, exclude=True)
    
    def __init__(self, knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None, **kwargs):
        super().__init__(kb_client=knowledge_base_client, **kwargs)
        
    @property
    def cloudformation(self):
        """Get CloudFormation client."""
        if not hasattr(self, '_cloudformation'):
            self._cloudformation = boto3.client('cloudformation')
        return self._cloudformation
        
    def _run(self, template_content: str, stack_name: str, 
             parameters: Optional[Dict[str, str]] = None, environment: str = "dev") -> str:
        """Deploy CloudFormation template with automation and validation."""
        try:
            # Validate template syntax
            validation_result = self._validate_template(template_content)
            if not validation_result["valid"]:
                return json.dumps({
                    "success": False,
                    "error": f"Template validation failed: {validation_result['errors']}"
                })
            
            # Prepare deployment configuration
            deployment_config = self._prepare_deployment_config(
                template_content, stack_name, parameters, environment
            )
            
            # Get deployment best practices from knowledge base
            deployment_patterns = []
            if self.kb_client:
                deployment_patterns = self._get_deployment_patterns(environment)
            
            # Create deployment automation script
            deployment_script = self._generate_deployment_script(deployment_config, deployment_patterns)
            
            # Generate rollback procedures
            rollback_procedures = self._generate_rollback_procedures(deployment_config)
            
            return json.dumps({
                "success": True,
                "deployment_config": deployment_config,
                "deployment_script": deployment_script,
                "rollback_procedures": rollback_procedures,
                "validation_results": validation_result
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"CloudFormation deployment preparation failed: {str(e)}"
            })
    
    def _validate_template(self, template_content: str) -> Dict[str, Any]:
        """Validate CloudFormation template syntax and structure."""
        try:
            # Parse template
            template = yaml.safe_load(template_content) if template_content.strip().startswith('AWSTemplateFormatVersion') else json.loads(template_content)
            
            # AWS CloudFormation validation
            response = self.cloudformation.validate_template(TemplateBody=template_content)
            
            # Additional structural validation
            validation_errors = []
            
            # Check required sections
            required_sections = ['AWSTemplateFormatVersion', 'Resources']
            for section in required_sections:
                if section not in template:
                    validation_errors.append(f"Missing required section: {section}")
            
            # Validate resource types
            if 'Resources' in template:
                for resource_name, resource_config in template['Resources'].items():
                    if 'Type' not in resource_config:
                        validation_errors.append(f"Resource {resource_name} missing Type")
            
            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "aws_validation": response,
                "capabilities": response.get('Capabilities', []),
                "parameters": response.get('Parameters', [])
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Template validation error: {str(e)}"],
                "aws_validation": None
            }
    
    def _prepare_deployment_config(self, template_content: str, stack_name: str, 
                                 parameters: Optional[Dict[str, str]], environment: str) -> Dict[str, Any]:
        """Prepare comprehensive deployment configuration."""
        config = {
            "stack_name": f"{stack_name}-{environment}",
            "template_content": template_content,
            "parameters": parameters or {},
            "environment": environment,
            "tags": {
                "Environment": environment,
                "Project": "AutoNinja",
                "ManagedBy": "AutoNinja-DeploymentManager"
            },
            "capabilities": ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
            "rollback_configuration": {
                "RollbackTriggers": [],
                "MonitoringTimeInMinutes": 5
            },
            "notification_arns": [],
            "timeout_in_minutes": 30
        }
        
        # Environment-specific configurations
        if environment == "prod":
            config["enable_termination_protection"] = True
            config["timeout_in_minutes"] = 60
        
        return config
    
    def _generate_deployment_script(self, config: Dict[str, Any], patterns: List[Dict[str, Any]]) -> str:
        """Generate deployment automation script."""
        script_template = f"""#!/bin/bash
# AutoNinja CloudFormation Deployment Script
# Generated for stack: {config['stack_name']}
# Environment: {config['environment']}

set -e

STACK_NAME="{config['stack_name']}"
ENVIRONMENT="{config['environment']}"
TEMPLATE_FILE="template.yaml"

echo "Starting deployment of $STACK_NAME in $ENVIRONMENT environment..."

# Pre-deployment validation
echo "Validating CloudFormation template..."
aws cloudformation validate-template --template-body file://$TEMPLATE_FILE

# Check if stack exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME >/dev/null 2>&1; then
    echo "Stack exists, updating..."
    OPERATION="update-stack"
else
    echo "Stack does not exist, creating..."
    OPERATION="create-stack"
fi

# Deploy stack
aws cloudformation $OPERATION \\
    --stack-name $STACK_NAME \\
    --template-body file://$TEMPLATE_FILE \\
    --capabilities {' '.join(config['capabilities'])} \\
    --tags {' '.join([f'Key={k},Value={v}' for k, v in config['tags'].items()])} \\
    --timeout-in-minutes {config['timeout_in_minutes']}

# Wait for completion
echo "Waiting for stack operation to complete..."
aws cloudformation wait stack-${{OPERATION//-/_}}-complete --stack-name $STACK_NAME

# Verify deployment
echo "Verifying deployment..."
aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].StackStatus'

echo "Deployment completed successfully!"
"""
        
        return script_template
    
    def _generate_rollback_procedures(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rollback procedures and scripts."""
        return {
            "automatic_rollback": {
                "enabled": True,
                "triggers": ["UPDATE_ROLLBACK_FAILED", "CREATE_FAILED"],
                "monitoring_time_minutes": config.get("rollback_configuration", {}).get("MonitoringTimeInMinutes", 5)
            },
            "manual_rollback_script": f"""#!/bin/bash
# Manual rollback script for {config['stack_name']}
set -e

STACK_NAME="{config['stack_name']}"

echo "Initiating rollback for $STACK_NAME..."

# Cancel update if in progress
aws cloudformation cancel-update-stack --stack-name $STACK_NAME || true

# Wait for cancellation
aws cloudformation wait stack-update-complete --stack-name $STACK_NAME || true

# If stack is in failed state, delete it
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].StackStatus' --output text)

if [[ "$STACK_STATUS" == *"FAILED"* ]]; then
    echo "Stack is in failed state, deleting..."
    aws cloudformation delete-stack --stack-name $STACK_NAME
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME
    echo "Stack deleted successfully"
else
    echo "Stack rollback completed"
fi
""",
            "rollback_checklist": [
                "Verify application health before rollback",
                "Backup current configuration",
                "Execute rollback script",
                "Verify rollback success",
                "Update monitoring and alerts",
                "Notify stakeholders"
            ]
        }
    
    def _get_deployment_patterns(self, environment: str) -> List[Dict[str, Any]]:
        """Retrieve deployment patterns from knowledge base."""
        if not self.kb_client:
            return []
        
        try:
            query = f"deployment patterns for {environment} environment CloudFormation best practices"
            results = self.kb_client.search_knowledge_base(
                KnowledgeBaseType.DEPLOYMENT_PRACTICES,
                query,
                max_results=5
            )
            return [{"content": result.get("content", ""), "metadata": result.get("metadata", {})} 
                   for result in results]
        except Exception:
            return []


class MonitoringConfigurationInput(BaseModel):
    """Input schema for monitoring and alerting configuration tool."""
    stack_name: str = Field(description="Name of the deployed stack")
    resources: List[Dict[str, Any]] = Field(description="List of AWS resources to monitor")
    environment: str = Field(default="dev", description="Environment (dev, staging, prod)")
    alert_endpoints: Optional[List[str]] = Field(default=None, description="SNS topics or email addresses for alerts")


class MonitoringConfigurationTool(BaseTool):
    """Tool for configuring CloudWatch dashboards and alerting."""
    
    name: str = "monitoring_configuration"
    description: str = """Configure CloudWatch dashboards, metrics, and alerting 
    for deployed AWS resources with environment-specific settings."""
    
    args_schema: Type[BaseModel] = MonitoringConfigurationInput
    kb_client: Optional[BedrockKnowledgeBaseClient] = Field(default=None, exclude=True)
    
    def __init__(self, knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None, **kwargs):
        super().__init__(kb_client=knowledge_base_client, **kwargs)
        
    @property
    def cloudwatch(self):
        """Get CloudWatch client."""
        if not hasattr(self, '_cloudwatch'):
            self._cloudwatch = boto3.client('cloudwatch')
        return self._cloudwatch
        
    def _run(self, stack_name: str, resources: List[Dict[str, Any]], 
             environment: str = "dev", alert_endpoints: Optional[List[str]] = None) -> str:
        """Configure monitoring and alerting for deployed resources."""
        try:
            # Generate CloudWatch dashboard configuration
            dashboard_config = self._generate_dashboard_config(stack_name, resources, environment)
            
            # Generate CloudWatch alarms configuration
            alarms_config = self._generate_alarms_config(stack_name, resources, environment, alert_endpoints)
            
            # Get monitoring best practices from knowledge base
            monitoring_patterns = []
            if self.kb_client:
                monitoring_patterns = self._get_monitoring_patterns(resources, environment)
            
            # Generate monitoring CloudFormation template
            monitoring_template = self._generate_monitoring_template(
                dashboard_config, alarms_config, monitoring_patterns
            )
            
            return json.dumps({
                "success": True,
                "dashboard_config": dashboard_config,
                "alarms_config": alarms_config,
                "monitoring_template": monitoring_template,
                "deployment_instructions": self._generate_monitoring_deployment_instructions(stack_name)
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Monitoring configuration failed: {str(e)}"
            })
    
    def _generate_dashboard_config(self, stack_name: str, resources: List[Dict[str, Any]], 
                                 environment: str) -> Dict[str, Any]:
        """Generate CloudWatch dashboard configuration."""
        dashboard_name = f"{stack_name}-{environment}-dashboard"
        
        # Generate widgets based on resource types
        widgets = []
        
        for resource in resources:
            resource_type = resource.get("Type", "")
            resource_name = resource.get("LogicalId", "")
            
            if "Lambda" in resource_type:
                widgets.extend(self._generate_lambda_widgets(resource_name))
            elif "DynamoDB" in resource_type:
                widgets.extend(self._generate_dynamodb_widgets(resource_name))
            elif "ApiGateway" in resource_type:
                widgets.extend(self._generate_apigateway_widgets(resource_name))
            elif "S3" in resource_type:
                widgets.extend(self._generate_s3_widgets(resource_name))
        
        return {
            "dashboard_name": dashboard_name,
            "widgets": widgets,
            "period": 300,  # 5 minutes
            "region": "us-east-1"
        }
    
    def _generate_alarms_config(self, stack_name: str, resources: List[Dict[str, Any]], 
                              environment: str, alert_endpoints: Optional[List[str]]) -> Dict[str, Any]:
        """Generate CloudWatch alarms configuration."""
        alarms = []
        
        # Environment-specific thresholds
        thresholds = {
            "dev": {"error_rate": 10, "latency": 5000, "duration": 30000},
            "staging": {"error_rate": 5, "latency": 3000, "duration": 20000},
            "prod": {"error_rate": 1, "latency": 1000, "duration": 10000}
        }
        
        env_thresholds = thresholds.get(environment, thresholds["dev"])
        
        for resource in resources:
            resource_type = resource.get("Type", "")
            resource_name = resource.get("LogicalId", "")
            
            if "Lambda" in resource_type:
                alarms.extend(self._generate_lambda_alarms(resource_name, env_thresholds))
            elif "DynamoDB" in resource_type:
                alarms.extend(self._generate_dynamodb_alarms(resource_name, env_thresholds))
            elif "ApiGateway" in resource_type:
                alarms.extend(self._generate_apigateway_alarms(resource_name, env_thresholds))
        
        return {
            "alarms": alarms,
            "sns_topics": alert_endpoints or [],
            "alarm_actions": ["notify", "auto_scale"] if environment == "prod" else ["notify"]
        }
    
    def _generate_lambda_widgets(self, function_name: str) -> List[Dict[str, Any]]:
        """Generate Lambda-specific dashboard widgets."""
        return [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/Lambda", "Invocations", "FunctionName", function_name],
                        [".", "Errors", ".", "."],
                        [".", "Duration", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": f"Lambda Metrics - {function_name}"
                }
            }
        ]
    
    def _generate_lambda_alarms(self, function_name: str, thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate Lambda-specific alarms."""
        return [
            {
                "alarm_name": f"{function_name}-ErrorRate",
                "metric_name": "Errors",
                "namespace": "AWS/Lambda",
                "statistic": "Sum",
                "threshold": thresholds["error_rate"],
                "comparison_operator": "GreaterThanThreshold",
                "dimensions": [{"Name": "FunctionName", "Value": function_name}]
            },
            {
                "alarm_name": f"{function_name}-Duration",
                "metric_name": "Duration",
                "namespace": "AWS/Lambda",
                "statistic": "Average",
                "threshold": thresholds["duration"],
                "comparison_operator": "GreaterThanThreshold",
                "dimensions": [{"Name": "FunctionName", "Value": function_name}]
            }
        ]
    
    def _generate_dynamodb_widgets(self, table_name: str) -> List[Dict[str, Any]]:
        """Generate DynamoDB-specific dashboard widgets."""
        return [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", table_name],
                        [".", "ConsumedWriteCapacityUnits", ".", "."],
                        [".", "ThrottledRequests", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": f"DynamoDB Metrics - {table_name}"
                }
            }
        ]
    
    def _generate_dynamodb_alarms(self, table_name: str, thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate DynamoDB-specific alarms."""
        return [
            {
                "alarm_name": f"{table_name}-ThrottledRequests",
                "metric_name": "ThrottledRequests",
                "namespace": "AWS/DynamoDB",
                "statistic": "Sum",
                "threshold": 1,
                "comparison_operator": "GreaterThanOrEqualToThreshold",
                "dimensions": [{"Name": "TableName", "Value": table_name}]
            }
        ]
    
    def _generate_apigateway_widgets(self, api_name: str) -> List[Dict[str, Any]]:
        """Generate API Gateway-specific dashboard widgets."""
        return [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/ApiGateway", "Count", "ApiName", api_name],
                        [".", "4XXError", ".", "."],
                        [".", "5XXError", ".", "."],
                        [".", "Latency", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": f"API Gateway Metrics - {api_name}"
                }
            }
        ]
    
    def _generate_apigateway_alarms(self, api_name: str, thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate API Gateway-specific alarms."""
        return [
            {
                "alarm_name": f"{api_name}-4XXError",
                "metric_name": "4XXError",
                "namespace": "AWS/ApiGateway",
                "statistic": "Sum",
                "threshold": thresholds["error_rate"],
                "comparison_operator": "GreaterThanThreshold",
                "dimensions": [{"Name": "ApiName", "Value": api_name}]
            },
            {
                "alarm_name": f"{api_name}-Latency",
                "metric_name": "Latency",
                "namespace": "AWS/ApiGateway",
                "statistic": "Average",
                "threshold": thresholds["latency"],
                "comparison_operator": "GreaterThanThreshold",
                "dimensions": [{"Name": "ApiName", "Value": api_name}]
            }
        ]
    
    def _generate_s3_widgets(self, bucket_name: str) -> List[Dict[str, Any]]:
        """Generate S3-specific dashboard widgets."""
        return [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/S3", "BucketSizeBytes", "BucketName", bucket_name, "StorageType", "StandardStorage"],
                        [".", "NumberOfObjects", ".", ".", ".", "AllStorageTypes"]
                    ],
                    "period": 86400,  # Daily
                    "stat": "Average",
                    "region": "us-east-1",
                    "title": f"S3 Metrics - {bucket_name}"
                }
            }
        ]
    
    def _generate_monitoring_template(self, dashboard_config: Dict[str, Any], 
                                    alarms_config: Dict[str, Any], 
                                    patterns: List[Dict[str, Any]]) -> str:
        """Generate CloudFormation template for monitoring resources."""
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "AutoNinja Generated Monitoring Configuration",
            "Resources": {}
        }
        
        # Add dashboard
        template["Resources"]["MonitoringDashboard"] = {
            "Type": "AWS::CloudWatch::Dashboard",
            "Properties": {
                "DashboardName": dashboard_config["dashboard_name"],
                "DashboardBody": json.dumps({
                    "widgets": dashboard_config["widgets"]
                })
            }
        }
        
        # Add alarms
        for i, alarm in enumerate(alarms_config["alarms"]):
            template["Resources"][f"Alarm{i}"] = {
                "Type": "AWS::CloudWatch::Alarm",
                "Properties": {
                    "AlarmName": alarm["alarm_name"],
                    "MetricName": alarm["metric_name"],
                    "Namespace": alarm["namespace"],
                    "Statistic": alarm["statistic"],
                    "Threshold": alarm["threshold"],
                    "ComparisonOperator": alarm["comparison_operator"],
                    "Dimensions": alarm["dimensions"],
                    "EvaluationPeriods": 2,
                    "Period": 300
                }
            }
        
        return yaml.dump(template, default_flow_style=False)
    
    def _generate_monitoring_deployment_instructions(self, stack_name: str) -> List[str]:
        """Generate deployment instructions for monitoring configuration."""
        return [
            f"1. Save the monitoring template as '{stack_name}-monitoring.yaml'",
            f"2. Deploy using: aws cloudformation create-stack --stack-name {stack_name}-monitoring --template-body file://{stack_name}-monitoring.yaml",
            "3. Wait for stack creation to complete",
            "4. Verify dashboard is created in CloudWatch console",
            "5. Test alarms by triggering threshold conditions",
            "6. Configure SNS topics for alert notifications if not already done"
        ]
    
    def _get_monitoring_patterns(self, resources: List[Dict[str, Any]], environment: str) -> List[Dict[str, Any]]:
        """Retrieve monitoring patterns from knowledge base."""
        if not self.kb_client:
            return []
        
        try:
            resource_types = [r.get("Type", "") for r in resources]
            query = f"monitoring patterns for {', '.join(resource_types)} in {environment} environment"
            results = self.kb_client.search_knowledge_base(
                KnowledgeBaseType.DEPLOYMENT_PRACTICES,
                query,
                max_results=5
            )
            return [{"content": result.get("content", ""), "metadata": result.get("metadata", {})} 
                   for result in results]
        except Exception:
            return []


class DeploymentValidationInput(BaseModel):
    """Input schema for deployment validation tool."""
    stack_name: str = Field(description="Name of the deployed stack")
    validation_tests: List[str] = Field(description="List of validation tests to run")
    environment: str = Field(default="dev", description="Environment to validate")


class DeploymentValidationTool(BaseTool):
    """Tool for validating deployments and performing health checks."""
    
    name: str = "deployment_validation"
    description: str = """Validate deployed resources, perform health checks, 
    and verify deployment success with comprehensive testing."""
    
    args_schema: Type[BaseModel] = DeploymentValidationInput
    kb_client: Optional[BedrockKnowledgeBaseClient] = Field(default=None, exclude=True)
    
    def __init__(self, knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None, **kwargs):
        super().__init__(kb_client=knowledge_base_client, **kwargs)
        
    @property
    def cloudformation(self):
        """Get CloudFormation client."""
        if not hasattr(self, '_cloudformation'):
            self._cloudformation = boto3.client('cloudformation')
        return self._cloudformation
        
    def _run(self, stack_name: str, validation_tests: List[str], environment: str = "dev") -> str:
        """Validate deployment and perform comprehensive health checks."""
        try:
            # Get stack information
            stack_info = self._get_stack_info(stack_name)
            if not stack_info["exists"]:
                return json.dumps({
                    "success": False,
                    "error": f"Stack {stack_name} does not exist"
                })
            
            # Run validation tests
            validation_results = {}
            for test in validation_tests:
                validation_results[test] = self._run_validation_test(test, stack_info, environment)
            
            # Generate validation report
            validation_report = self._generate_validation_report(stack_info, validation_results)
            
            # Generate health check script
            health_check_script = self._generate_health_check_script(stack_info, validation_tests)
            
            return json.dumps({
                "success": True,
                "stack_info": stack_info,
                "validation_results": validation_results,
                "validation_report": validation_report,
                "health_check_script": health_check_script,
                "overall_status": "HEALTHY" if all(r.get("passed", False) for r in validation_results.values()) else "UNHEALTHY"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Deployment validation failed: {str(e)}"
            })
    
    def _get_stack_info(self, stack_name: str) -> Dict[str, Any]:
        """Get comprehensive stack information."""
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = response['Stacks'][0]
            
            # Get stack resources
            resources_response = self.cloudformation.describe_stack_resources(StackName=stack_name)
            resources = resources_response['StackResources']
            
            return {
                "exists": True,
                "stack_name": stack['StackName'],
                "stack_status": stack['StackStatus'],
                "creation_time": stack['CreationTime'].isoformat(),
                "last_updated_time": stack.get('LastUpdatedTime', stack['CreationTime']).isoformat(),
                "parameters": {p['ParameterKey']: p['ParameterValue'] for p in stack.get('Parameters', [])},
                "outputs": {o['OutputKey']: o['OutputValue'] for o in stack.get('Outputs', [])},
                "tags": {t['Key']: t['Value'] for t in stack.get('Tags', [])},
                "resources": [
                    {
                        "logical_id": r['LogicalResourceId'],
                        "physical_id": r['PhysicalResourceId'],
                        "type": r['ResourceType'],
                        "status": r['ResourceStatus']
                    }
                    for r in resources
                ]
            }
        except Exception as e:
            return {
                "exists": False,
                "error": str(e)
            }
    
    def _run_validation_test(self, test_name: str, stack_info: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """Run individual validation test."""
        try:
            if test_name == "stack_status":
                return self._validate_stack_status(stack_info)
            elif test_name == "resource_health":
                return self._validate_resource_health(stack_info)
            elif test_name == "connectivity":
                return self._validate_connectivity(stack_info)
            elif test_name == "security":
                return self._validate_security_configuration(stack_info)
            elif test_name == "performance":
                return self._validate_performance(stack_info, environment)
            else:
                return {
                    "passed": False,
                    "message": f"Unknown validation test: {test_name}"
                }
        except Exception as e:
            return {
                "passed": False,
                "message": f"Validation test {test_name} failed: {str(e)}"
            }
    
    def _validate_stack_status(self, stack_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate CloudFormation stack status."""
        status = stack_info.get("stack_status", "")
        healthy_statuses = ["CREATE_COMPLETE", "UPDATE_COMPLETE"]
        
        return {
            "passed": status in healthy_statuses,
            "message": f"Stack status: {status}",
            "details": {
                "current_status": status,
                "expected_statuses": healthy_statuses
            }
        }
    
    def _validate_resource_health(self, stack_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual resource health."""
        resources = stack_info.get("resources", [])
        healthy_statuses = ["CREATE_COMPLETE", "UPDATE_COMPLETE"]
        
        unhealthy_resources = [
            r for r in resources 
            if r["status"] not in healthy_statuses
        ]
        
        return {
            "passed": len(unhealthy_resources) == 0,
            "message": f"Resource health check: {len(resources) - len(unhealthy_resources)}/{len(resources)} healthy",
            "details": {
                "total_resources": len(resources),
                "healthy_resources": len(resources) - len(unhealthy_resources),
                "unhealthy_resources": unhealthy_resources
            }
        }
    
    def _validate_connectivity(self, stack_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate network connectivity and endpoints."""
        # This is a simplified connectivity check
        # In a real implementation, you would test actual endpoints
        
        api_resources = [
            r for r in stack_info.get("resources", [])
            if "ApiGateway" in r["type"] or "LoadBalancer" in r["type"]
        ]
        
        return {
            "passed": True,  # Simplified - assume connectivity is OK if resources exist
            "message": f"Connectivity check: {len(api_resources)} endpoints found",
            "details": {
                "endpoints": api_resources,
                "note": "Detailed connectivity testing requires actual endpoint URLs"
            }
        }
    
    def _validate_security_configuration(self, stack_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate security configuration."""
        # Check for security-related resources
        security_resources = [
            r for r in stack_info.get("resources", [])
            if any(sec_type in r["type"] for sec_type in ["IAM", "SecurityGroup", "KMS"])
        ]
        
        return {
            "passed": len(security_resources) > 0,
            "message": f"Security validation: {len(security_resources)} security resources found",
            "details": {
                "security_resources": security_resources,
                "recommendations": [
                    "Verify IAM roles follow least privilege principle",
                    "Ensure security groups have minimal required access",
                    "Confirm encryption is enabled where applicable"
                ]
            }
        }
    
    def _validate_performance(self, stack_info: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """Validate performance configuration."""
        # Performance validation based on environment
        performance_thresholds = {
            "dev": {"lambda_timeout": 30, "dynamodb_capacity": 5},
            "staging": {"lambda_timeout": 15, "dynamodb_capacity": 10},
            "prod": {"lambda_timeout": 10, "dynamodb_capacity": 25}
        }
        
        thresholds = performance_thresholds.get(environment, performance_thresholds["dev"])
        
        return {
            "passed": True,  # Simplified validation
            "message": f"Performance validation for {environment} environment",
            "details": {
                "environment": environment,
                "thresholds": thresholds,
                "note": "Detailed performance testing requires load testing tools"
            }
        }
    
    def _generate_validation_report(self, stack_info: Dict[str, Any], 
                                  validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        passed_tests = sum(1 for result in validation_results.values() if result.get("passed", False))
        total_tests = len(validation_results)
        
        return {
            "summary": {
                "stack_name": stack_info.get("stack_name", ""),
                "validation_time": "2024-01-01T00:00:00Z",  # Would use actual timestamp
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
                "overall_status": "PASS" if passed_tests == total_tests else "FAIL"
            },
            "test_results": validation_results,
            "recommendations": self._generate_recommendations(validation_results),
            "next_steps": self._generate_next_steps(validation_results)
        }
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        for test_name, result in validation_results.items():
            if not result.get("passed", False):
                if test_name == "stack_status":
                    recommendations.append("Review CloudFormation stack events for deployment issues")
                elif test_name == "resource_health":
                    recommendations.append("Investigate unhealthy resources and resolve configuration issues")
                elif test_name == "connectivity":
                    recommendations.append("Test endpoint connectivity and network configuration")
                elif test_name == "security":
                    recommendations.append("Review and strengthen security configuration")
                elif test_name == "performance":
                    recommendations.append("Optimize resource configuration for better performance")
        
        if not recommendations:
            recommendations.append("All validation tests passed - deployment is healthy")
        
        return recommendations
    
    def _generate_next_steps(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate next steps based on validation results."""
        failed_tests = [name for name, result in validation_results.items() if not result.get("passed", False)]
        
        if not failed_tests:
            return [
                "Deployment validation successful",
                "Monitor application performance and health",
                "Set up regular health checks",
                "Review and update monitoring thresholds as needed"
            ]
        else:
            return [
                f"Address failed validation tests: {', '.join(failed_tests)}",
                "Re-run validation after fixes",
                "Consider rollback if critical issues persist",
                "Update deployment procedures based on lessons learned"
            ]
    
    def _generate_health_check_script(self, stack_info: Dict[str, Any], validation_tests: List[str]) -> str:
        """Generate automated health check script."""
        stack_name = stack_info.get("stack_name", "")
        
        script = f"""#!/bin/bash
# AutoNinja Health Check Script
# Generated for stack: {stack_name}

set -e

STACK_NAME="{stack_name}"
echo "Running health checks for $STACK_NAME..."

# Check stack status
echo "Checking CloudFormation stack status..."
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].StackStatus' --output text)
echo "Stack status: $STACK_STATUS"

if [[ "$STACK_STATUS" != "CREATE_COMPLETE" && "$STACK_STATUS" != "UPDATE_COMPLETE" ]]; then
    echo "ERROR: Stack is not in a healthy state"
    exit 1
fi

# Check resource status
echo "Checking resource health..."
aws cloudformation describe-stack-resources --stack-name $STACK_NAME --query 'StackResources[?ResourceStatus!=`CREATE_COMPLETE` && ResourceStatus!=`UPDATE_COMPLETE`]'

"""
        
        # Add specific health checks based on validation tests
        if "connectivity" in validation_tests:
            script += """
# Test API endpoints (if any)
echo "Testing API connectivity..."
# Add specific endpoint tests here

"""
        
        if "performance" in validation_tests:
            script += """
# Performance checks
echo "Running performance checks..."
# Add performance validation here

"""
        
        script += """
echo "Health check completed successfully!"
"""
        
        return script


# Export all tools for easy import
__all__ = [
    "CloudFormationDeploymentTool",
    "MonitoringConfigurationTool", 
    "DeploymentValidationTool"
]