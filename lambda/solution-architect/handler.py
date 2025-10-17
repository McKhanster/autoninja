"""
Solution Architect Lambda Function
Designs AWS architecture, selects services, and generates infrastructure-as-code
"""
import json
import os
import time
from typing import Dict, Any, List, Optional

# Import shared utilities from Lambda Layer
from shared.persistence.dynamodb_client import DynamoDBClient
from shared.persistence.s3_client import S3Client
from shared.utils.logger import get_logger


# Initialize clients
dynamodb_client = DynamoDBClient()
s3_client = S3Client()
logger = get_logger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Solution Architect agent.
    Routes requests to appropriate action handlers based on apiPath.
    
    Args:
        event: Bedrock Agent input event
        context: Lambda context
        
    Returns:
        Bedrock Agent response event
    """
    start_time = time.time()
    job_name = None
    timestamp = None
    
    try:
        # Parse Bedrock Agent event
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', 'POST')
        action_group = event.get('actionGroup', 'solution-architect-actions')
        session_id = event.get('sessionId', 'unknown')
        
        # Extract parameters from request body
        request_body = event.get('requestBody', {})
        content = request_body.get('content', {})
        json_content = content.get('application/json', {})
        properties = json_content.get('properties', [])
        
        # Convert properties array to dict
        params = {prop['name']: prop['value'] for prop in properties}
        job_name = params.get('job_name', 'unknown')
        
        # Set logger context
        logger.set_context(
            job_name=job_name,
            agent_name='solution-architect',
            action_name=api_path
        )
        
        logger.info(f"Processing request for apiPath: {api_path}")
        
        # Route to appropriate action handler
        if api_path == '/design-architecture':
            result = handle_design_architecture(event, params, session_id, start_time)
        elif api_path == '/select-services':
            result = handle_select_services(event, params, session_id, start_time)
        elif api_path == '/generate-iac':
            result = handle_generate_iac(event, params, session_id, start_time)
        else:
            raise ValueError(f"Unknown apiPath: {api_path}")
        
        # Format successful response
        response = {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': http_method,
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result)
                    }
                }
            }
        }
        
        logger.info(f"Request completed successfully in {time.time() - start_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", error=str(e))
        
        # Log error to DynamoDB if we have job_name and timestamp
        if job_name and timestamp:
            try:
                dynamodb_client.log_error_to_dynamodb(
                    job_name=job_name,
                    timestamp=timestamp,
                    error_message=str(e),
                    duration_seconds=time.time() - start_time
                )
            except Exception as log_error:
                logger.error(f"Failed to log error to DynamoDB: {str(log_error)}")
        
        # Return error response
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'solution-architect-actions'),
                'apiPath': event.get('apiPath', '/'),
                'httpMethod': event.get('httpMethod', 'POST'),
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': str(e),
                            'status': 'error'
                        })
                    }
                }
            }
        }


def handle_design_architecture(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle design_architecture action.
    Designs complete AWS architecture based on requirements.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, requirements, code_file_references)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, architecture, diagram, and status
    """
    job_name = params.get('job_name')
    requirements_str = params.get('requirements')
    code_file_references_str = params.get('code_file_references', '{}')
    
    if not job_name or not requirements_str:
        raise ValueError("Missing required parameters: job_name and requirements")
    
    # Parse requirements if it's a string
    if isinstance(requirements_str, str):
        try:
            requirements = json.loads(requirements_str)
        except json.JSONDecodeError:
            requirements = {}
    else:
        requirements = requirements_str or {}
    
    # Parse code_file_references if it's a string
    if isinstance(code_file_references_str, str):
        try:
            code_file_references = json.loads(code_file_references_str)
        except json.JSONDecodeError:
            code_file_references = {}
    else:
        code_file_references = code_file_references_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='solution-architect',
        action_name='design_architecture',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Design architecture based on requirements
        logger.info(f"Designing architecture for job: {job_name}")
        
        arch_reqs = requirements.get('architecture_requirements', {})
        
        architecture = {
            "services": [
                "AWS Bedrock Agent",
                "AWS Lambda",
                "Amazon DynamoDB",
                "Amazon S3",
                "AWS IAM",
                "Amazon CloudWatch"
            ],
            "resources": {
                "bedrock_agent": {
                    "name": f"{requirements.get('agent_purpose', 'agent').lower().replace(' ', '-')}",
                    "foundation_model": arch_reqs.get('bedrock', {}).get('foundation_model', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'),
                    "action_groups": arch_reqs.get('bedrock', {}).get('action_groups', 1)
                },
                "lambda_functions": [
                    {
                        "name": f"{requirements.get('agent_purpose', 'agent').lower().replace(' ', '-')}-lambda",
                        "runtime": "python3.12",
                        "memory": arch_reqs.get('compute', {}).get('memory_mb', 512),
                        "timeout": arch_reqs.get('compute', {}).get('timeout_seconds', 60)
                    }
                ],
                "dynamodb_tables": [],
                "s3_buckets": []
            },
            "iam_policies": {
                "lambda_execution_role": {
                    "policies": ["AWSLambdaBasicExecutionRole", "DynamoDBAccess", "S3Access"]
                },
                "bedrock_agent_role": {
                    "policies": ["BedrockInvokeModel", "LambdaInvokeFunction"]
                }
            },
            "integration_points": [
                {
                    "source": "Bedrock Agent",
                    "target": "Lambda Function",
                    "method": "Action Group"
                }
            ],
            "service_rationale": {
                "AWS Bedrock Agent": "Provides conversational AI capabilities",
                "AWS Lambda": "Serverless compute for action handlers",
                "Amazon DynamoDB": "NoSQL database for state management",
                "Amazon S3": "Object storage for artifacts",
                "AWS IAM": "Identity and access management",
                "Amazon CloudWatch": "Logging and monitoring"
            },
            "cost_estimate": "$50-100/month for moderate usage",
            "scalability_notes": "Serverless architecture scales automatically"
        }
        
        diagram = """
        User -> Bedrock Agent -> Lambda Function -> DynamoDB/S3
        """
        
        # Prepare response
        result = {
            "job_name": job_name,
            "architecture": architecture,
            "diagram": diagram,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            filename='architecture_design.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save architecture design to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            artifact=architecture,
            filename='architecture_design.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            response=result,
            filename='design_architecture_raw_response.json'
        )
        
        logger.info(f"Architecture designed successfully for job {job_name}")
        return result
        
    except Exception as e:
        # Log error to DynamoDB
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )
        raise


def handle_select_services(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle select_services action.
    Selects appropriate AWS services based on requirements.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, requirements)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, services, rationale, and status
    """
    job_name = params.get('job_name')
    requirements_str = params.get('requirements')
    
    if not job_name or not requirements_str:
        raise ValueError("Missing required parameters: job_name and requirements")
    
    # Parse requirements if it's a string
    if isinstance(requirements_str, str):
        try:
            requirements = json.loads(requirements_str)
        except json.JSONDecodeError:
            requirements = {}
    else:
        requirements = requirements_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='solution-architect',
        action_name='select_services',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Select services based on requirements
        logger.info(f"Selecting services for job: {job_name}")
        
        services = [
            "AWS Bedrock Agent",
            "AWS Lambda",
            "Amazon DynamoDB",
            "Amazon S3",
            "AWS IAM",
            "Amazon CloudWatch"
        ]
        
        rationale = {
            "AWS Bedrock Agent": "Best choice for conversational AI with built-in orchestration",
            "AWS Lambda": "Serverless compute eliminates infrastructure management",
            "Amazon DynamoDB": "Fast, scalable NoSQL database for session state",
            "Amazon S3": "Durable object storage for artifacts and logs",
            "AWS IAM": "Fine-grained access control for security",
            "Amazon CloudWatch": "Comprehensive monitoring and logging"
        }
        
        # Prepare response
        result = {
            "job_name": job_name,
            "services": services,
            "rationale": json.dumps(rationale),
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            filename='service_selection.json'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save service selection to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            artifact={"services": services, "rationale": rationale},
            filename='service_selection.json',
            content_type='application/json'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            response=result,
            filename='select_services_raw_response.json'
        )
        
        logger.info(f"Services selected successfully for job {job_name}")
        return result
        
    except Exception as e:
        # Log error to DynamoDB
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )
        raise


def handle_generate_iac(
    event: Dict[str, Any],
    params: Dict[str, str],
    session_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle generate_iac action.
    Generates CloudFormation template for the architecture.
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, architecture, code_references)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, cloudformation_template, and status
    """
    job_name = params.get('job_name')
    architecture_str = params.get('architecture')
    code_references_str = params.get('code_references', '{}')
    
    if not job_name or not architecture_str:
        raise ValueError("Missing required parameters: job_name and architecture")
    
    # Parse architecture if it's a string
    if isinstance(architecture_str, str):
        try:
            architecture = json.loads(architecture_str)
        except json.JSONDecodeError:
            architecture = {}
    else:
        architecture = architecture_str or {}
    
    # Parse code_references if it's a string
    if isinstance(code_references_str, str):
        try:
            code_references = json.loads(code_references_str)
        except json.JSONDecodeError:
            code_references = {}
    else:
        code_references = code_references_str or {}
    
    # Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='solution-architect',
        action_name='generate_iac',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # Generate CloudFormation template
        logger.info(f"Generating IaC for job: {job_name}")
        
        resources = architecture.get('resources', {})
        bedrock_agent = resources.get('bedrock_agent', {})
        lambda_functions = resources.get('lambda_functions', [])
        
        agent_name = bedrock_agent.get('name', 'generated-agent')
        
        cloudformation_template = f"""AWSTemplateFormatVersion: '2010-09-09'
Description: Generated agent infrastructure

Parameters:
  Environment:
    Type: String
    Default: production
    Description: Environment name

Resources:
  # Lambda Execution Role
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: DynamoDBAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:PutItem
                  - dynamodb:GetItem
                  - dynamodb:Query
                Resource: '*'
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:PutObject
                  - s3:GetObject
                Resource: '*'

  # Lambda Function
  LambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub '${{Environment}}-{agent_name}-lambda'
      Runtime: python3.12
      Handler: handler.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Code:
        ZipFile: |
          def lambda_handler(event, context):
              return {{'statusCode': 200, 'body': 'Hello'}}
      Timeout: {lambda_functions[0].get('timeout', 60) if lambda_functions else 60}
      MemorySize: {lambda_functions[0].get('memory', 512) if lambda_functions else 512}

  # Bedrock Agent Role
  BedrockAgentRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: bedrock.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: BedrockAgentPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - bedrock:InvokeModel
                Resource: '*'
              - Effect: Allow
                Action:
                  - lambda:InvokeFunction
                Resource: !GetAtt LambdaFunction.Arn

Outputs:
  LambdaFunctionArn:
    Value: !GetAtt LambdaFunction.Arn
    Description: Lambda function ARN
  BedrockAgentRoleArn:
    Value: !GetAtt BedrockAgentRole.Arn
    Description: Bedrock agent role ARN
"""
        
        # Prepare response
        result = {
            "job_name": job_name,
            "cloudformation_template": cloudformation_template,
            "status": "success"
        }
        
        # Log raw output to DynamoDB immediately
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            filename='cloudformation_template.yaml'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # Save CloudFormation template to S3
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            artifact=cloudformation_template,
            filename='cloudformation_template.yaml',
            content_type='application/x-yaml'
        )
        
        # Also save raw response to S3
        s3_client.save_raw_response(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            response=result,
            filename='generate_iac_raw_response.json'
        )
        
        logger.info(f"IaC generated successfully for job {job_name}")
        return result
        
    except Exception as e:
        # Log error to DynamoDB
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )
        raise
