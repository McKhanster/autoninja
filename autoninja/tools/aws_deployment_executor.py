"""
AWS Deployment Executor Tools

Tools that actually execute deployments to AWS, creating real resources.
"""

import json
import yaml
import boto3
import time
from typing import Dict, List, Any, Optional, Type
from datetime import datetime, UTC
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class CloudFormationExecutorInput(BaseModel):
    """Input schema for CloudFormation execution tool."""
    template_content: str = Field(description="CloudFormation template content")
    stack_name: str = Field(description="Name for the CloudFormation stack")
    parameters: Optional[Dict[str, str]] = Field(default=None, description="Stack parameters")
    environment: str = Field(default="dev", description="Deployment environment")


class CloudFormationExecutorTool(BaseTool):
    """Tool that actually executes CloudFormation deployments to AWS."""
    
    name: str = "cloudformation_executor"
    description: str = """Execute CloudFormation deployments to AWS, creating real resources."""
    
    args_schema: Type[BaseModel] = CloudFormationExecutorInput
    
    @property
    def cloudformation(self):
        """Get CloudFormation client."""
        if not hasattr(self, '_cloudformation'):
            self._cloudformation = boto3.client('cloudformation')
        return self._cloudformation
    
    @property
    def s3(self):
        """Get S3 client."""
        if not hasattr(self, '_s3'):
            self._s3 = boto3.client('s3')
        return self._s3
        
    def _run(self, template_content: str, stack_name: str, 
             parameters: Optional[Dict[str, str]] = None, environment: str = "dev") -> str:
        """Execute CloudFormation deployment to AWS."""
        
        deployment_id = f"{stack_name}-{environment}-{int(datetime.now(UTC).timestamp())}"
        
        try:
            logger.info(f"Starting CloudFormation deployment: {deployment_id}")
            
            # 1. Validate template
            validation_result = self._validate_template(template_content)
            if not validation_result["valid"]:
                return json.dumps({
                    "success": False,
                    "deployment_id": deployment_id,
                    "error": f"Template validation failed: {validation_result['errors']}"
                })
            
            # 2. Upload template to S3 if large
            template_url = None
            if len(template_content) > 51200:  # 50KB limit for direct template
                template_url = self._upload_template_to_s3(template_content, deployment_id)
            
            # 3. Prepare stack parameters
            stack_parameters = self._prepare_stack_parameters(parameters or {})
            
            # 4. Check if stack exists
            stack_exists = self._check_stack_exists(stack_name)
            
            # 5. Execute deployment
            if stack_exists:
                operation_result = self._update_stack(
                    stack_name, template_content, template_url, stack_parameters
                )
                operation = "UPDATE"
            else:
                operation_result = self._create_stack(
                    stack_name, template_content, template_url, stack_parameters
                )
                operation = "CREATE"
            
            if not operation_result["success"]:
                return json.dumps({
                    "success": False,
                    "deployment_id": deployment_id,
                    "error": operation_result["error"]
                })
            
            # 6. Wait for completion
            wait_result = self._wait_for_completion(stack_name, operation)
            
            # 7. Get deployment results
            if wait_result["success"]:
                stack_info = self._get_stack_info(stack_name)
                deployment_artifacts = self._extract_deployment_artifacts(stack_info)
                
                return json.dumps({
                    "success": True,
                    "deployment_id": deployment_id,
                    "operation": operation,
                    "stack_name": stack_name,
                    "stack_id": stack_info.get("stack_id"),
                    "stack_status": stack_info.get("status"),
                    "outputs": stack_info.get("outputs", {}),
                    "resources": stack_info.get("resources", []),
                    "deployment_artifacts": deployment_artifacts,
                    "deployment_time": wait_result.get("duration_seconds", 0),
                    "template_url": template_url
                }, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "deployment_id": deployment_id,
                    "error": wait_result["error"],
                    "stack_status": wait_result.get("final_status")
                })
                
        except Exception as e:
            logger.error(f"CloudFormation deployment failed: {str(e)}")
            return json.dumps({
                "success": False,
                "deployment_id": deployment_id,
                "error": f"Deployment execution failed: {str(e)}"
            })
    
    def _validate_template(self, template_content: str) -> Dict[str, Any]:
        """Validate CloudFormation template."""
        try:
            response = self.cloudformation.validate_template(TemplateBody=template_content)
            return {
                "valid": True,
                "capabilities": response.get('Capabilities', []),
                "parameters": response.get('Parameters', [])
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)]
            }
    
    def _upload_template_to_s3(self, template_content: str, deployment_id: str) -> str:
        """Upload large template to S3."""
        bucket_name = f"autoninja-templates-{boto3.Session().region_name}"
        key = f"templates/{deployment_id}.yaml"
        
        try:
            # Create bucket if it doesn't exist
            try:
                self.s3.head_bucket(Bucket=bucket_name)
            except:
                self.s3.create_bucket(Bucket=bucket_name)
            
            # Upload template
            self.s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=template_content,
                ContentType='text/yaml'
            )
            
            return f"https://{bucket_name}.s3.amazonaws.com/{key}"
            
        except Exception as e:
            logger.error(f"Failed to upload template to S3: {str(e)}")
            raise
    
    def _prepare_stack_parameters(self, parameters: Dict[str, str]) -> List[Dict[str, str]]:
        """Convert parameters to CloudFormation format."""
        return [
            {"ParameterKey": key, "ParameterValue": value}
            for key, value in parameters.items()
        ]
    
    def _check_stack_exists(self, stack_name: str) -> bool:
        """Check if CloudFormation stack exists."""
        try:
            self.cloudformation.describe_stacks(StackName=stack_name)
            return True
        except self.cloudformation.exceptions.ClientError:
            return False
    
    def _create_stack(self, stack_name: str, template_content: str, 
                     template_url: Optional[str], parameters: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create new CloudFormation stack."""
        try:
            kwargs = {
                'StackName': stack_name,
                'Parameters': parameters,
                'Capabilities': ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
                'Tags': [
                    {'Key': 'CreatedBy', 'Value': 'AutoNinja'},
                    {'Key': 'Environment', 'Value': 'dev'},
                    {'Key': 'Timestamp', 'Value': datetime.now(UTC).isoformat()}
                ]
            }
            
            if template_url:
                kwargs['TemplateURL'] = template_url
            else:
                kwargs['TemplateBody'] = template_content
            
            response = self.cloudformation.create_stack(**kwargs)
            
            return {
                "success": True,
                "stack_id": response['StackId']
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_stack(self, stack_name: str, template_content: str,
                     template_url: Optional[str], parameters: List[Dict[str, str]]) -> Dict[str, Any]:
        """Update existing CloudFormation stack."""
        try:
            kwargs = {
                'StackName': stack_name,
                'Parameters': parameters,
                'Capabilities': ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
            }
            
            if template_url:
                kwargs['TemplateURL'] = template_url
            else:
                kwargs['TemplateBody'] = template_content
            
            response = self.cloudformation.update_stack(**kwargs)
            
            return {
                "success": True,
                "stack_id": response['StackId']
            }
            
        except self.cloudformation.exceptions.ClientError as e:
            if "No updates are to be performed" in str(e):
                return {
                    "success": True,
                    "message": "No updates needed"
                }
            return {
                "success": False,
                "error": str(e)
            }
    
    def _wait_for_completion(self, stack_name: str, operation: str) -> Dict[str, Any]:
        """Wait for CloudFormation operation to complete."""
        start_time = time.time()
        max_wait_time = 1800  # 30 minutes
        
        try:
            if operation == "CREATE":
                waiter = self.cloudformation.get_waiter('stack_create_complete')
            else:
                waiter = self.cloudformation.get_waiter('stack_update_complete')
            
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={
                    'Delay': 30,
                    'MaxAttempts': 60
                }
            )
            
            duration = time.time() - start_time
            return {
                "success": True,
                "duration_seconds": duration
            }
            
        except Exception as e:
            # Get final stack status
            try:
                response = self.cloudformation.describe_stacks(StackName=stack_name)
                final_status = response['Stacks'][0]['StackStatus']
            except:
                final_status = "UNKNOWN"
            
            return {
                "success": False,
                "error": str(e),
                "final_status": final_status,
                "duration_seconds": time.time() - start_time
            }
    
    def _get_stack_info(self, stack_name: str) -> Dict[str, Any]:
        """Get comprehensive stack information."""
        try:
            # Get stack details
            stack_response = self.cloudformation.describe_stacks(StackName=stack_name)
            stack = stack_response['Stacks'][0]
            
            # Get stack resources
            resources_response = self.cloudformation.describe_stack_resources(StackName=stack_name)
            resources = resources_response['StackResources']
            
            return {
                "stack_id": stack['StackId'],
                "stack_name": stack['StackName'],
                "status": stack['StackStatus'],
                "creation_time": stack['CreationTime'].isoformat(),
                "outputs": {
                    output['OutputKey']: output['OutputValue'] 
                    for output in stack.get('Outputs', [])
                },
                "parameters": {
                    param['ParameterKey']: param['ParameterValue']
                    for param in stack.get('Parameters', [])
                },
                "resources": [
                    {
                        "logical_id": resource['LogicalResourceId'],
                        "physical_id": resource['PhysicalResourceId'],
                        "type": resource['ResourceType'],
                        "status": resource['ResourceStatus']
                    }
                    for resource in resources
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get stack info: {str(e)}")
            return {}
    
    def _extract_deployment_artifacts(self, stack_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract deployment artifacts from stack info."""
        artifacts = {
            "stack_arn": stack_info.get("stack_id"),
            "endpoints": [],
            "databases": [],
            "functions": [],
            "buckets": [],
            "roles": []
        }
        
        # Extract specific resource types
        for resource in stack_info.get("resources", []):
            resource_type = resource["type"]
            physical_id = resource["physical_id"]
            
            if "Lambda::Function" in resource_type:
                artifacts["functions"].append({
                    "name": resource["logical_id"],
                    "arn": physical_id,
                    "type": "lambda"
                })
            elif "DynamoDB::Table" in resource_type:
                artifacts["databases"].append({
                    "name": resource["logical_id"],
                    "table_name": physical_id,
                    "type": "dynamodb"
                })
            elif "S3::Bucket" in resource_type:
                artifacts["buckets"].append({
                    "name": resource["logical_id"],
                    "bucket_name": physical_id,
                    "type": "s3"
                })
            elif "IAM::Role" in resource_type:
                artifacts["roles"].append({
                    "name": resource["logical_id"],
                    "arn": physical_id,
                    "type": "iam_role"
                })
            elif "ApiGateway" in resource_type:
                artifacts["endpoints"].append({
                    "name": resource["logical_id"],
                    "id": physical_id,
                    "type": "api_gateway"
                })
        
        return artifacts


class BedrockAgentExecutorInput(BaseModel):
    """Input schema for Bedrock Agent execution tool."""
    agent_config: Dict[str, Any] = Field(description="Bedrock Agent configuration")
    action_groups: List[Dict[str, Any]] = Field(description="Action groups configuration")
    lambda_functions: List[Dict[str, Any]] = Field(description="Lambda functions to deploy")


class BedrockAgentExecutorTool(BaseTool):
    """Tool that actually creates Bedrock Agents in AWS."""
    
    name: str = "bedrock_agent_executor"
    description: str = """Create real Bedrock Agents in AWS with action groups and Lambda functions."""
    
    args_schema: Type[BaseModel] = BedrockAgentExecutorInput
    
    @property
    def bedrock_agent(self):
        """Get Bedrock Agent client."""
        if not hasattr(self, '_bedrock_agent'):
            self._bedrock_agent = boto3.client('bedrock-agent')
        return self._bedrock_agent
    
    @property
    def lambda_client(self):
        """Get Lambda client."""
        if not hasattr(self, '_lambda'):
            self._lambda = boto3.client('lambda')
        return self._lambda
        
    def _run(self, agent_config: Dict[str, Any], action_groups: List[Dict[str, Any]], 
             lambda_functions: List[Dict[str, Any]]) -> str:
        """Execute Bedrock Agent creation."""
        
        deployment_id = f"bedrock-agent-{int(datetime.now(UTC).timestamp())}"
        
        try:
            logger.info(f"Starting Bedrock Agent deployment: {deployment_id}")
            
            # 1. Deploy Lambda functions first
            deployed_functions = []
            for lambda_func in lambda_functions:
                function_result = self._deploy_lambda_function(lambda_func)
                if function_result["success"]:
                    deployed_functions.append(function_result)
                else:
                    return json.dumps({
                        "success": False,
                        "deployment_id": deployment_id,
                        "error": f"Lambda deployment failed: {function_result['error']}"
                    })
            
            # 2. Create Bedrock Agent
            agent_result = self._create_bedrock_agent(agent_config)
            if not agent_result["success"]:
                return json.dumps({
                    "success": False,
                    "deployment_id": deployment_id,
                    "error": f"Bedrock Agent creation failed: {agent_result['error']}"
                })
            
            agent_id = agent_result["agent_id"]
            
            # 3. Create Action Groups
            deployed_action_groups = []
            for action_group in action_groups:
                # Find corresponding Lambda function
                lambda_arn = None
                for func in deployed_functions:
                    if func["function_name"] == action_group.get("lambda_function"):
                        lambda_arn = func["function_arn"]
                        break
                
                if lambda_arn:
                    action_group_result = self._create_action_group(
                        agent_id, action_group, lambda_arn
                    )
                    if action_group_result["success"]:
                        deployed_action_groups.append(action_group_result)
            
            # 4. Prepare and create agent alias
            alias_result = self._create_agent_alias(agent_id)
            
            return json.dumps({
                "success": True,
                "deployment_id": deployment_id,
                "agent_id": agent_id,
                "agent_arn": agent_result["agent_arn"],
                "agent_alias": alias_result.get("alias_id"),
                "deployed_functions": deployed_functions,
                "deployed_action_groups": deployed_action_groups,
                "deployment_artifacts": {
                    "agent_endpoint": f"bedrock-agent://{agent_id}",
                    "lambda_functions": [f["function_arn"] for f in deployed_functions],
                    "action_groups": [ag["action_group_id"] for ag in deployed_action_groups]
                }
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Bedrock Agent deployment failed: {str(e)}")
            return json.dumps({
                "success": False,
                "deployment_id": deployment_id,
                "error": f"Bedrock Agent deployment failed: {str(e)}"
            })
    
    def _deploy_lambda_function(self, lambda_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy Lambda function."""
        try:
            function_name = lambda_config["function_name"]
            
            # Create deployment package
            zip_content = self._create_lambda_zip(lambda_config["code"])
            
            # Create or update function
            try:
                response = self.lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime=lambda_config.get("runtime", "python3.11"),
                    Role=lambda_config.get("role_arn", "arn:aws:iam::123456789012:role/lambda-role"),
                    Handler=lambda_config.get("handler", "index.lambda_handler"),
                    Code={'ZipFile': zip_content},
                    Environment={
                        'Variables': lambda_config.get("environment_variables", {})
                    },
                    Timeout=lambda_config.get("timeout", 300),
                    MemorySize=lambda_config.get("memory_size", 512)
                )
            except self.lambda_client.exceptions.ResourceConflictException:
                # Function exists, update it
                response = self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_content
                )
            
            return {
                "success": True,
                "function_name": function_name,
                "function_arn": response["FunctionArn"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_lambda_zip(self, code: str) -> bytes:
        """Create Lambda deployment package."""
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('index.py', code)
        
        return zip_buffer.getvalue()
    
    def _create_bedrock_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create Bedrock Agent."""
        try:
            response = self.bedrock_agent.create_agent(
                agentName=agent_config["agent_name"],
                description=agent_config.get("description", "AutoNinja generated agent"),
                foundationModel=agent_config.get("foundation_model", "anthropic.claude-3-sonnet-20240229-v1:0"),
                instruction=agent_config.get("instruction", "You are a helpful AI assistant."),
                agentResourceRoleArn=agent_config.get("role_arn", "arn:aws:iam::123456789012:role/bedrock-agent-role")
            )
            
            return {
                "success": True,
                "agent_id": response["agent"]["agentId"],
                "agent_arn": response["agent"]["agentArn"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_action_group(self, agent_id: str, action_group_config: Dict[str, Any], 
                           lambda_arn: str) -> Dict[str, Any]:
        """Create action group for Bedrock Agent."""
        try:
            response = self.bedrock_agent.create_agent_action_group(
                agentId=agent_id,
                agentVersion="DRAFT",
                actionGroupName=action_group_config["name"],
                description=action_group_config.get("description", "AutoNinja generated action group"),
                actionGroupExecutor={
                    'lambda': lambda_arn
                },
                apiSchema={
                    'payload': json.dumps(action_group_config.get("api_schema", {}))
                }
            )
            
            return {
                "success": True,
                "action_group_id": response["agentActionGroup"]["actionGroupId"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_agent_alias(self, agent_id: str) -> Dict[str, Any]:
        """Create agent alias for deployment."""
        try:
            # First prepare the agent
            self.bedrock_agent.prepare_agent(agentId=agent_id)
            
            # Create alias
            response = self.bedrock_agent.create_agent_alias(
                agentId=agent_id,
                aliasName="prod",
                description="Production alias for AutoNinja generated agent"
            )
            
            return {
                "success": True,
                "alias_id": response["agentAlias"]["aliasId"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class MonitoringExecutorInput(BaseModel):
    """Input schema for monitoring execution tool."""
    stack_name: str = Field(description="Name of the deployed stack")
    resources: List[Dict[str, Any]] = Field(description="List of deployed resources")
    environment: str = Field(default="dev", description="Environment")


class MonitoringExecutorTool(BaseTool):
    """Tool that actually creates CloudWatch dashboards and alarms."""
    
    name: str = "monitoring_executor"
    description: str = """Create real CloudWatch dashboards and alarms for deployed resources."""
    
    args_schema: Type[BaseModel] = MonitoringExecutorInput
    
    @property
    def cloudwatch(self):
        """Get CloudWatch client."""
        if not hasattr(self, '_cloudwatch'):
            self._cloudwatch = boto3.client('cloudwatch')
        return self._cloudwatch
        
    def _run(self, stack_name: str, resources: List[Dict[str, Any]], environment: str = "dev") -> str:
        """Execute monitoring setup."""
        
        monitoring_id = f"monitoring-{stack_name}-{int(datetime.now(UTC).timestamp())}"
        
        try:
            logger.info(f"Starting monitoring setup: {monitoring_id}")
            
            # 1. Create CloudWatch dashboard
            dashboard_result = self._create_dashboard(stack_name, resources)
            
            # 2. Create CloudWatch alarms
            alarms_result = self._create_alarms(stack_name, resources, environment)
            
            return json.dumps({
                "success": True,
                "monitoring_id": monitoring_id,
                "dashboard": dashboard_result,
                "alarms": alarms_result,
                "monitoring_artifacts": {
                    "dashboard_url": f"https://console.aws.amazon.com/cloudwatch/home#dashboards:name={stack_name}-dashboard",
                    "alarm_count": len(alarms_result.get("created_alarms", []))
                }
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Monitoring setup failed: {str(e)}")
            return json.dumps({
                "success": False,
                "monitoring_id": monitoring_id,
                "error": f"Monitoring setup failed: {str(e)}"
            })
    
    def _create_dashboard(self, stack_name: str, resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create CloudWatch dashboard."""
        try:
            dashboard_name = f"{stack_name}-dashboard"
            
            # Generate widgets based on resources
            widgets = []
            for resource in resources:
                if resource["type"] == "lambda":
                    widgets.extend(self._create_lambda_widgets(resource))
                elif resource["type"] == "dynamodb":
                    widgets.extend(self._create_dynamodb_widgets(resource))
            
            dashboard_body = {
                "widgets": widgets
            }
            
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            return {
                "success": True,
                "dashboard_name": dashboard_name,
                "widget_count": len(widgets)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_alarms(self, stack_name: str, resources: List[Dict[str, Any]], 
                      environment: str) -> Dict[str, Any]:
        """Create CloudWatch alarms."""
        created_alarms = []
        
        try:
            for resource in resources:
                if resource["type"] == "lambda":
                    alarms = self._create_lambda_alarms(resource, environment)
                    created_alarms.extend(alarms)
                elif resource["type"] == "dynamodb":
                    alarms = self._create_dynamodb_alarms(resource, environment)
                    created_alarms.extend(alarms)
            
            return {
                "success": True,
                "created_alarms": created_alarms
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_lambda_widgets(self, resource: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create Lambda-specific widgets."""
        function_name = resource["name"]
        
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
    
    def _create_dynamodb_widgets(self, resource: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create DynamoDB-specific widgets."""
        table_name = resource["table_name"]
        
        return [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", table_name],
                        [".", "ConsumedWriteCapacityUnits", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": f"DynamoDB Metrics - {table_name}"
                }
            }
        ]
    
    def _create_lambda_alarms(self, resource: Dict[str, Any], environment: str) -> List[str]:
        """Create Lambda-specific alarms."""
        function_name = resource["name"]
        alarms = []
        
        # Error rate alarm
        alarm_name = f"{function_name}-ErrorRate"
        self.cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='Errors',
            Namespace='AWS/Lambda',
            Period=300,
            Statistic='Sum',
            Threshold=5.0,
            ActionsEnabled=True,
            AlarmDescription=f'Error rate alarm for {function_name}',
            Dimensions=[
                {
                    'Name': 'FunctionName',
                    'Value': function_name
                }
            ]
        )
        alarms.append(alarm_name)
        
        return alarms
    
    def _create_dynamodb_alarms(self, resource: Dict[str, Any], environment: str) -> List[str]:
        """Create DynamoDB-specific alarms."""
        table_name = resource["table_name"]
        alarms = []
        
        # Throttled requests alarm
        alarm_name = f"{table_name}-ThrottledRequests"
        self.cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=1,
            MetricName='ThrottledRequests',
            Namespace='AWS/DynamoDB',
            Period=300,
            Statistic='Sum',
            Threshold=0.0,
            ActionsEnabled=True,
            AlarmDescription=f'Throttled requests alarm for {table_name}',
            Dimensions=[
                {
                    'Name': 'TableName',
                    'Value': table_name
                }
            ]
        )
        alarms.append(alarm_name)
        
        return alarms