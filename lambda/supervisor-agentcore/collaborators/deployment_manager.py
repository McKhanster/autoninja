"""
Deployment Manager Module
Deploys Bedrock Agents to AWS
"""
import json
import os
import time
import zipfile
import io
from typing import Dict, Any
import boto3
from botocore.config import Config

from shared.persistence.dynamodb_client import DynamoDBClient
from shared.persistence.s3_client import S3Client
from shared.utils.logger import get_logger
from shared.utils.agentcore_rate_limiter import apply_rate_limiting

# Configure boto3 clients with extended timeouts
config = Config(
    read_timeout=300,  # 5 minutes
    connect_timeout=60,  # 1 minute
    retries={'max_attempts': 3}
)

dynamodb_client = DynamoDBClient()
s3_client = S3Client()
cloudformation = boto3.client('cloudformation')
s3 = boto3.client('s3')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', config=config)
logger = get_logger(__name__)


def get_stack_outputs():
    """Get CloudFormation stack outputs for agent IDs and aliases"""
    try:
        response = cloudformation.describe_stacks(StackName='autoninja-collaborators-production')
        outputs = response['Stacks'][0]['Outputs']
        return {item['OutputKey']: item['OutputValue'] for item in outputs}
    except Exception as e:
        logger.warning(f"Failed to get stack outputs: {e}")
        return {}


def invoke_bedrock_agent(agent_id: str, alias_id: str, session_id: str, input_text: str) -> str:
    """Invoke Bedrock Agent and return response"""
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=input_text
        )
        
        completion = ""
        for event in response['completion']:
            if 'chunk' in event:
                completion += event['chunk']['bytes'].decode()
        
        return completion
    except Exception as e:
        logger.error(f"Bedrock Agent invocation failed: {e}")
        raise


def package_lambda_code(lambda_code: Dict[str, str]) -> bytes:
    """Package Lambda code files into ZIP"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, code_content in lambda_code.items():
            zip_file.writestr(filename, code_content)
    return zip_buffer.getvalue()


def upload_to_s3(bucket: str, key: str, content: bytes or str) -> str:
    """Upload content to S3 and return S3 URI"""
    if isinstance(content, str):
        content = content.encode('utf-8')
    s3.put_object(Bucket=bucket, Key=key, Body=content, ServerSideEncryption='aws:kms')
    return f"s3://{bucket}/{key}"


def deploy(job_name: str, code: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """
    Deploy Bedrock Agent to AWS
    
    Args:
        job_name: Unique job identifier
        code: Generated code from code generator
        session_id: Session identifier for Bedrock Agent
        
    Returns:
        Dict with deployment results
    """
    start_time = time.time()
    
    stack_outputs = get_stack_outputs()
    agent_id = stack_outputs.get('DeploymentManagerAgentId')
    agent_alias_id = stack_outputs.get('DeploymentManagerAliasId')
    
    # Log raw input
    raw_request = json.dumps({"job_name": job_name, "code": code}, default=str)
    logger.info(f"RAW REQUEST for {job_name}: {raw_request}")
    
    # Log to DynamoDB
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='deployment-manager',
        action_name='deploy',
        prompt=raw_request,
        model_id='bedrock-agent'
    )['timestamp']
    
    logger.info(f"Deploying agent for job: {job_name}")
    
    # Get deployment bucket from environment or construct from current region
    current_region = os.environ.get('AWS_REGION', boto3.Session().region_name or 'us-east-2')
    deployment_bucket = os.environ.get('DEPLOYMENT_BUCKET', f'autoninja-deployment-artifacts-{current_region}')
    agent_config = code.get('agent_config', {})
    agent_name = agent_config.get('name', job_name)
    lambda_code = code.get('lambda_code', {})
    openapi_schema = code.get('openapi_schema', {})
    
    # Generate valid CloudFormation stack name
    stack_name = job_name.replace('_', '-').replace('/', '-')
    if not stack_name[0].isalpha():
        stack_name = 'stack-' + stack_name
    stack_name = f"{stack_name}-stack"
    
    # Generate CloudFormation template
    logger.info("Generating CloudFormation infrastructure template...")
    
    cf_template = None
    if agent_id and agent_alias_id:
        try:
            apply_rate_limiting('deployment-manager-bedrock')
            
            template_input = {
                "code": code,
                "agent_config": agent_config,
                "deployment_bucket": deployment_bucket,
                "agent_name": agent_name
            }
            logger.info(f"DM template_input: {template_input}")
            cf_template = invoke_bedrock_agent(
                agent_id=agent_id,
                alias_id=agent_alias_id,
                session_id=session_id,
                input_text=json.dumps(template_input)
            )
            logger.info(f"DM cf_template: {cf_template}")
        except Exception as agent_error:
            logger.warning(f"Failed to generate template via Bedrock Agent: {agent_error}")
            cf_template = None
    
    
    # Package Lambda code
    logger.info("Packaging Lambda code...")
    lambda_zip = package_lambda_code(lambda_code)
    
    # Upload artifacts to S3
    logger.info("Uploading artifacts to S3...")
    lambda_s3_uri = upload_to_s3(deployment_bucket, f"{agent_name}/lambda.zip", lambda_zip)
    
    schema_content = json.dumps(openapi_schema) if isinstance(openapi_schema, dict) else str(openapi_schema)
    schema_s3_uri = upload_to_s3(deployment_bucket, f"{agent_name}/schema.yaml", schema_content)
    
    logger.info(f"Artifacts uploaded: {lambda_s3_uri}, {schema_s3_uri}")
    
    # Deploy CloudFormation stack
    logger.info(f"Deploying CloudFormation stack: {stack_name}...")
    try:
        response = cloudformation.create_stack(
            StackName=stack_name,
            TemplateBody=cf_template,
            Capabilities=['CAPABILITY_IAM'],
            Parameters=[
                {'ParameterKey': 'DeploymentBucket', 'ParameterValue': deployment_bucket}
            ]
        )
        stack_id = response['StackId']
        
        # Wait for stack creation
        logger.info("Waiting for stack creation...")
        waiter = cloudformation.get_waiter('stack_create_complete')
        waiter.wait(StackName=stack_name, WaiterConfig={'Delay': 30, 'MaxAttempts': 20})
        
        # Get stack outputs
        stack_info = cloudformation.describe_stacks(StackName=stack_name)['Stacks'][0]
        outputs = {output['OutputKey']: output['OutputValue'] for output in stack_info.get('Outputs', [])}
        
        result = {
            "job_name": job_name,
            "stack_name": stack_name,
            "stack_id": stack_id,
            "stack_status": stack_info['StackStatus'],
            "agent_id": outputs.get('AgentId'),
            "agent_alias_id": outputs.get('AgentAliasId'),
            "lambda_arn": outputs.get('LambdaArn'),
            "s3_locations": {
                "lambda_code": lambda_s3_uri,
                "schema": schema_s3_uri
            },
            "status": "success"
        }
        
    except Exception as deploy_error:
        logger.error(f"Deployment failed: {str(deploy_error)}")
        result = {
            "job_name": job_name,
            "stack_name": stack_name,
            "status": "error",
            "error": str(deploy_error)
        }
    
    # Log raw output
    duration = time.time() - start_time
    raw_response = json.dumps(result, default=str)
    logger.info(f"RAW RESPONSE for {job_name}: {raw_response}")
    
    # Log to DynamoDB
    s3_uri = s3_client.get_s3_uri(
        job_name=job_name,
        phase='deployment',
        agent_name='deployment-manager',
        filename='deployment_result.json'
    )
    
    dynamodb_client.log_inference_output(
        job_name=job_name,
        timestamp=timestamp,
        response=raw_response,
        duration_seconds=duration,
        artifacts_s3_uri=s3_uri,
        status=result['status']
    )
    
    # Save artifacts to S3
    s3_client.save_converted_artifact(
        job_name=job_name,
        phase='deployment',
        agent_name='deployment-manager',
        artifact=result,
        filename='deployment_result.json',
        content_type='application/json'
    )
    
    if cf_template:
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='deployment',
            agent_name='deployment-manager',
            artifact=cf_template,
            filename='cloudformation_template.yaml',
            content_type='text/yaml'
        )
    
    logger.info(f"Deployment completed in {duration:.2f}s")
    
    return result
