"""
Solution Architect Lambda Function
Designs AWS architecture for requested agents
"""
import json
import os
import time
from typing import Dict, Any, List, Optional

# Import shared utilities from Lambda Layer
from shared.persistence.dynamodb_client import DynamoDBClient
from shared.persistence.s3_client import S3Client
from shared.utils.logger import get_logger
from shared.models.architecture import Architecture


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
    Designs complete AWS architecture based on requirements and code files.
    
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
    code_file_references = params.get('code_file_references', '')
    
    if not job_name:
        raise ValueError("Missing required parameter: job_name")
    
    # Parse requirements if it's a string
    if isinstance(requirements_str, str):
        try:
            requirements = json.loads(requirements_str)
        except json.JSONDecodeError:
            requirements = {}
    else:
        requirements = requirements_str or {}
    
    # STEP 1: Log raw input to DynamoDB immediately (before any processing)
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='solution-architect',
        action_name='design_architecture',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # STEP 3: Retrieve code files from Code Generator using s3_client
        logger.info(f"Retrieving code files from S3 for job {job_name}")
        code_artifacts = retrieve_code_artifacts(job_name)
        
        # STEP 4: Design AWS architecture based on requirements and code
        logger.info(f"Designing architecture for job {job_name}")
        architecture_data = design_architecture_from_requirements(requirements, code_artifacts)
        
        # STEP 5: Generate architecture design document
        architecture = Architecture(**architecture_data)
        diagram = generate_architecture_diagram(architecture_data)
        
        # Prepare response
        result = {
            "job_name": job_name,
            "architecture": architecture.to_dict(),
            "diagram": diagram,
            "status": "success"
        }
        
        # STEP 6: Log raw output to DynamoDB immediately after generation
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
        
        # STEP 7: Save architecture design to S3 using save_converted_artifact
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            artifact=architecture.to_dict(),
            filename='architecture_design.json',
            content_type='application/json'
        )
        
        # STEP 8: Save raw response to S3 using save_raw_response
        s3_client.save_raw_response(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            response=result,
            filename='raw_response.json'
        )
        
        logger.info(f"Architecture design completed for job {job_name}")
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


def retrieve_code_artifacts(job_name: str) -> Dict[str, Any]:
    """
    Retrieve code artifacts generated by Code Generator from S3.
    
    Args:
        job_name: Job identifier
        
    Returns:
        Dict containing code artifacts (lambda_code, agent_config, openapi_schemas, etc.)
    """
    code_artifacts = {}
    
    try:
        # Try to retrieve lambda code
        try:
            lambda_code = s3_client.get_artifact(
                job_name=job_name,
                phase='code',
                agent_name='code-generator',
                filename='lambda_handler.py'
            )
            code_artifacts['lambda_code'] = lambda_code
            logger.info(f"Retrieved lambda_handler.py from S3")
        except Exception as e:
            logger.warning(f"Could not retrieve lambda_handler.py: {str(e)}")
            code_artifacts['lambda_code'] = None
        
        # Try to retrieve agent config
        try:
            agent_config = s3_client.get_artifact(
                job_name=job_name,
                phase='code',
                agent_name='code-generator',
                filename='agent_config.json'
            )
            if isinstance(agent_config, str):
                agent_config = json.loads(agent_config)
            code_artifacts['agent_config'] = agent_config
            logger.info(f"Retrieved agent_config.json from S3")
        except Exception as e:
            logger.warning(f"Could not retrieve agent_config.json: {str(e)}")
            code_artifacts['agent_config'] = None
        
        # Try to retrieve OpenAPI schema
        try:
            openapi_schema = s3_client.get_artifact(
                job_name=job_name,
                phase='code',
                agent_name='code-generator',
                filename='openapi_schema.yaml'
            )
            code_artifacts['openapi_schema'] = openapi_schema
            logger.info(f"Retrieved openapi_schema.yaml from S3")
        except Exception as e:
            logger.warning(f"Could not retrieve openapi_schema.yaml: {str(e)}")
            code_artifacts['openapi_schema'] = None
        
        # Try to retrieve requirements.txt
        try:
            requirements_txt = s3_client.get_artifact(
                job_name=job_name,
                phase='code',
                agent_name='code-generator',
                filename='requirements.txt'
            )
            code_artifacts['requirements_txt'] = requirements_txt
            logger.info(f"Retrieved requirements.txt from S3")
        except Exception as e:
            logger.warning(f"Could not retrieve requirements.txt: {str(e)}")
            code_artifacts['requirements_txt'] = None
        
    except Exception as e:
        logger.error(f"Error retrieving code artifacts: {str(e)}")
    
    return code_artifacts


def design_architecture_from_requirements(
    requirements: Dict[str, Any],
    code_artifacts: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Design AWS architecture based on requirements and code artifacts.
    
    Args:
        requirements: Requirements dictionary
        code_artifacts: Code artifacts from Code Generator
        
    Returns:
        Architecture data dictionary
    """
    # Extract key information from requirements
    arch_reqs = requirements.get('architecture_requirements', {})
    lambda_reqs = requirements.get('lambda_requirements', {})
    data_needs = requirements.get('data_needs', [])
    integrations = requirements.get('integrations', [])
    
    # Determine services needed
    services = ["AWS Bedrock Agent", "AWS Lambda"]
    
    # Check if DynamoDB is needed
    storage = arch_reqs.get('storage', {})
    dynamodb_tables = []
    if storage.get('dynamodb_tables', 0) > 0 or any('dynamodb' in need.lower() for need in data_needs):
        services.append("Amazon DynamoDB")
        dynamodb_tables.append({
            "name": "agent-data-table",
            "partition_key": "id",
            "sort_key": "timestamp",
            "billing_mode": "PAY_PER_REQUEST"
        })
    
    # Check if S3 is needed
    s3_buckets = []
    if storage.get('s3_buckets', 0) > 0 or any('s3' in need.lower() or 'file' in need.lower() for need in data_needs):
        services.append("Amazon S3")
        s3_buckets.append({
            "name": "agent-artifacts-bucket",
            "versioning": True,
            "encryption": "AES256"
        })
    
    # Add CloudWatch for logging
    services.append("Amazon CloudWatch")
    
    # Build resources configuration
    bedrock_config = arch_reqs.get('bedrock', {})
    compute_config = arch_reqs.get('compute', {})
    
    # Extract agent config from code artifacts if available
    agent_config = code_artifacts.get('agent_config') or {}
    agent_name = agent_config.get('name', 'generated-agent')
    foundation_model = bedrock_config.get('foundation_model', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0')
    action_groups_count = bedrock_config.get('action_groups', 1)
    
    # Build Lambda function configuration
    lambda_functions = []
    lambda_actions = lambda_reqs.get('actions', [])
    
    for i, action in enumerate(lambda_actions):
        func_config = {
            "name": f"{agent_name}-{action.get('name', f'action-{i}')}",
            "runtime": lambda_reqs.get('runtime', 'python3.12'),
            "memory": compute_config.get('memory_mb', lambda_reqs.get('memory', 512)),
            "timeout": compute_config.get('timeout_seconds', lambda_reqs.get('timeout', 60)),
            "handler": "handler.lambda_handler",
            "environment_variables": lambda_reqs.get('environment_variables', {})
        }
        lambda_functions.append(func_config)
    
    # If no actions defined, create a default Lambda
    if not lambda_functions:
        lambda_functions.append({
            "name": f"{agent_name}-lambda",
            "runtime": "python3.12",
            "memory": 512,
            "timeout": 60,
            "handler": "handler.lambda_handler",
            "environment_variables": {"LOG_LEVEL": "INFO"}
        })
    
    # Build IAM policies
    iam_policies = {
        "lambda_execution_role": [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
        ],
        "bedrock_agent_role": [
            "bedrock:InvokeModel",
            "lambda:InvokeFunction"
        ]
    }
    
    # Add DynamoDB permissions if needed
    if dynamodb_tables:
        iam_policies["lambda_execution_role"].extend([
            "dynamodb:PutItem",
            "dynamodb:GetItem",
            "dynamodb:Query",
            "dynamodb:UpdateItem"
        ])
    
    # Add S3 permissions if needed
    if s3_buckets:
        iam_policies["lambda_execution_role"].extend([
            "s3:GetObject",
            "s3:PutObject",
            "s3:ListBucket"
        ])
    
    # Build integration points
    integration_points = [
        "User -> Bedrock Agent (InvokeAgent API)",
        "Bedrock Agent -> Lambda Function (Action Groups)"
    ]
    
    if dynamodb_tables:
        integration_points.append("Lambda Function -> DynamoDB (Data Persistence)")
    
    if s3_buckets:
        integration_points.append("Lambda Function -> S3 (Artifact Storage)")
    
    # Add external integrations
    for integration in integrations:
        if integration.lower() not in ['aws bedrock agent runtime', 'bedrock']:
            integration_points.append(f"Lambda Function -> {integration}")
    
    # Build complete architecture data
    architecture_data = {
        "services": services,
        "resources": {
            "bedrock_agent": {
                "name": agent_name,
                "foundation_model": foundation_model,
                "action_groups": action_groups_count,
                "instructions": agent_config.get('instructions', 'AI agent to assist users')
            },
            "lambda_functions": lambda_functions,
            "dynamodb_tables": dynamodb_tables,
            "s3_buckets": s3_buckets
        },
        "iam_policies": iam_policies,
        "integration_points": integration_points
    }
    
    return architecture_data


def generate_architecture_diagram(architecture_data: Dict[str, Any]) -> str:
    """
    Generate a simple text-based architecture diagram.
    
    Args:
        architecture_data: Architecture data dictionary
        
    Returns:
        String representation of architecture diagram
    """
    services = architecture_data.get('services', [])
    resources = architecture_data.get('resources', {})
    integration_points = architecture_data.get('integration_points', [])
    
    diagram = "Architecture Diagram:\n"
    diagram += "=" * 70 + "\n\n"
    
    diagram += "Services:\n"
    for service in services:
        diagram += f"  - {service}\n"
    diagram += "\n"
    
    diagram += "Resources:\n"
    if 'bedrock_agent' in resources:
        agent = resources['bedrock_agent']
        diagram += f"  Bedrock Agent:\n"
        diagram += f"    Name: {agent.get('name', 'N/A')}\n"
        diagram += f"    Model: {agent.get('foundation_model', 'N/A')}\n"
        diagram += f"    Action Groups: {agent.get('action_groups', 0)}\n"
    
    lambda_functions = resources.get('lambda_functions', [])
    if lambda_functions:
        diagram += f"\n  Lambda Functions ({len(lambda_functions)}):\n"
        for func in lambda_functions:
            diagram += f"    - {func.get('name', 'N/A')}\n"
            diagram += f"      Runtime: {func.get('runtime', 'N/A')}\n"
            diagram += f"      Memory: {func.get('memory', 'N/A')} MB\n"
            diagram += f"      Timeout: {func.get('timeout', 'N/A')}s\n"
    
    dynamodb_tables = resources.get('dynamodb_tables', [])
    if dynamodb_tables:
        diagram += f"\n  DynamoDB Tables ({len(dynamodb_tables)}):\n"
        for table in dynamodb_tables:
            diagram += f"    - {table.get('name', 'N/A')}\n"
    
    s3_buckets = resources.get('s3_buckets', [])
    if s3_buckets:
        diagram += f"\n  S3 Buckets ({len(s3_buckets)}):\n"
        for bucket in s3_buckets:
            diagram += f"    - {bucket.get('name', 'N/A')}\n"
    
    diagram += "\n" + "=" * 70 + "\n"
    diagram += "Integration Flow:\n"
    for i, point in enumerate(integration_points, 1):
        diagram += f"  {i}. {point}\n"
    
    return diagram


def select_aws_services(requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Select appropriate AWS services based on requirements.
    
    Args:
        requirements: Requirements dictionary
        
    Returns:
        List of service dictionaries with name, purpose, and justification
    """
    services = []
    
    # Core services - always needed
    services.append({
        "name": "AWS Bedrock Agent",
        "purpose": "AI agent runtime and orchestration",
        "justification": "Native AWS service for building conversational AI agents with built-in session management"
    })
    
    services.append({
        "name": "AWS Lambda",
        "purpose": "Serverless compute for action groups",
        "justification": "Scalable, pay-per-use compute for agent actions with automatic scaling"
    })
    
    services.append({
        "name": "Amazon CloudWatch",
        "purpose": "Logging and monitoring",
        "justification": "Centralized logging and metrics for observability and debugging"
    })
    
    # Check for data persistence needs
    data_needs = requirements.get('data_needs', [])
    arch_reqs = requirements.get('architecture_requirements', {})
    storage = arch_reqs.get('storage', {})
    
    needs_dynamodb = (
        storage.get('dynamodb_tables', 0) > 0 or
        any('dynamodb' in need.lower() or 'database' in need.lower() or 'persist' in need.lower() 
            for need in data_needs)
    )
    
    if needs_dynamodb:
        services.append({
            "name": "Amazon DynamoDB",
            "purpose": "NoSQL database for data persistence",
            "justification": "Serverless, scalable database with single-digit millisecond latency for storing agent data"
        })
    
    needs_s3 = (
        storage.get('s3_buckets', 0) > 0 or
        any('s3' in need.lower() or 'file' in need.lower() or 'artifact' in need.lower() or 'storage' in need.lower()
            for need in data_needs)
    )
    
    if needs_s3:
        services.append({
            "name": "Amazon S3",
            "purpose": "Object storage for artifacts and files",
            "justification": "Durable, scalable storage with 99.999999999% durability for files and documents"
        })
    
    # Check for specific integrations
    integrations = requirements.get('integrations', [])
    
    for integration in integrations:
        integration_lower = integration.lower()
        
        if 'api gateway' in integration_lower:
            services.append({
                "name": "Amazon API Gateway",
                "purpose": "REST API management",
                "justification": "Managed API service for exposing agent functionality via HTTP endpoints"
            })
        
        if 'sns' in integration_lower or 'notification' in integration_lower:
            services.append({
                "name": "Amazon SNS",
                "purpose": "Pub/sub messaging and notifications",
                "justification": "Managed messaging service for sending notifications and event-driven communication"
            })
        
        if 'sqs' in integration_lower or 'queue' in integration_lower:
            services.append({
                "name": "Amazon SQS",
                "purpose": "Message queuing",
                "justification": "Managed queue service for decoupling components and handling asynchronous processing"
            })
        
        if 'step functions' in integration_lower or 'workflow' in integration_lower:
            services.append({
                "name": "AWS Step Functions",
                "purpose": "Workflow orchestration",
                "justification": "Serverless workflow service for coordinating complex multi-step processes"
            })
    
    # Check capabilities for additional services
    capabilities = requirements.get('capabilities', [])
    
    for capability in capabilities:
        capability_lower = capability.lower()
        
        if 'image' in capability_lower or 'vision' in capability_lower:
            services.append({
                "name": "Amazon Rekognition",
                "purpose": "Image and video analysis",
                "justification": "Managed computer vision service for analyzing images and videos"
            })
        
        if 'translate' in capability_lower or 'translation' in capability_lower:
            services.append({
                "name": "Amazon Translate",
                "purpose": "Language translation",
                "justification": "Neural machine translation service for real-time language translation"
            })
        
        if 'speech' in capability_lower or 'voice' in capability_lower:
            services.append({
                "name": "Amazon Polly",
                "purpose": "Text-to-speech",
                "justification": "Text-to-speech service with lifelike voices"
            })
    
    # Security services - always recommended
    services.append({
        "name": "AWS IAM",
        "purpose": "Identity and access management",
        "justification": "Fine-grained access control and security policies for all AWS resources"
    })
    
    services.append({
        "name": "AWS KMS",
        "purpose": "Encryption key management",
        "justification": "Managed encryption service for securing data at rest and in transit"
    })
    
    return services


def generate_service_rationale(requirements: Dict[str, Any], services: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate rationale for service selection.
    
    Args:
        requirements: Requirements dictionary
        services: List of selected services
        
    Returns:
        Rationale dictionary with architecture pattern, cost, scalability, and security info
    """
    # Determine architecture pattern
    has_storage = any(s['name'] in ['Amazon DynamoDB', 'Amazon S3'] for s in services)
    has_messaging = any(s['name'] in ['Amazon SNS', 'Amazon SQS'] for s in services)
    has_orchestration = any(s['name'] == 'AWS Step Functions' for s in services)
    
    if has_orchestration:
        architecture_pattern = "Event-driven serverless architecture with workflow orchestration"
    elif has_messaging:
        architecture_pattern = "Event-driven serverless microservices"
    elif has_storage:
        architecture_pattern = "Serverless microservices with data persistence"
    else:
        architecture_pattern = "Simple serverless architecture"
    
    # Cost optimization strategy
    cost_optimization = [
        "Pay-per-use pricing model - no idle costs",
        "Serverless services eliminate infrastructure management overhead",
        "DynamoDB on-demand billing for unpredictable workloads" if has_storage else None,
        "Lambda automatic scaling reduces over-provisioning",
        "CloudWatch Logs retention policies to manage storage costs"
    ]
    cost_optimization = [c for c in cost_optimization if c is not None]
    
    # Scalability characteristics
    scalability = [
        "Automatic scaling with no manual intervention required",
        "Bedrock Agent handles concurrent sessions automatically",
        "Lambda scales to thousands of concurrent executions",
        "DynamoDB auto-scales read/write capacity" if has_storage else None,
        "S3 provides unlimited storage capacity" if any(s['name'] == 'Amazon S3' for s in services) else None
    ]
    scalability = [s for s in scalability if s is not None]
    
    # Security features
    security = [
        "AWS IAM for fine-grained access control with least-privilege policies",
        "KMS encryption for data at rest",
        "TLS 1.3 for data in transit",
        "VPC integration available for network isolation",
        "CloudTrail audit logging for compliance",
        "Bedrock Agent built-in guardrails for content filtering"
    ]
    
    # Reliability features
    reliability = [
        "Multi-AZ deployment for high availability",
        "Automatic retries and error handling",
        "DynamoDB point-in-time recovery" if has_storage else None,
        "S3 versioning for data protection" if any(s['name'] == 'Amazon S3' for s in services) else None,
        "CloudWatch alarms for proactive monitoring"
    ]
    reliability = [r for r in reliability if r is not None]
    
    # Complexity assessment
    complexity = requirements.get('complexity', 'moderate')
    service_count = len(services)
    
    if service_count <= 5:
        complexity_note = "Simple architecture with minimal services - easy to deploy and maintain"
    elif service_count <= 8:
        complexity_note = "Moderate complexity - balanced between functionality and maintainability"
    else:
        complexity_note = "Complex architecture with multiple integrations - requires careful orchestration"
    
    return {
        "architecture_pattern": architecture_pattern,
        "cost_optimization": cost_optimization,
        "scalability": scalability,
        "security": security,
        "reliability": reliability,
        "complexity_assessment": complexity_note,
        "service_count": service_count,
        "estimated_monthly_cost": estimate_monthly_cost(requirements, services)
    }


def estimate_monthly_cost(requirements: Dict[str, Any], services: List[Dict[str, Any]]) -> str:
    """
    Estimate monthly cost based on services and usage patterns.
    
    Args:
        requirements: Requirements dictionary
        services: List of selected services
        
    Returns:
        Cost estimate string
    """
    # Simple cost estimation based on service count and complexity
    complexity = requirements.get('complexity', 'moderate')
    service_count = len(services)
    
    # Base costs (rough estimates for low-moderate usage)
    base_cost = 0
    
    # Bedrock Agent + Lambda (base)
    base_cost += 50  # Bedrock Agent inference costs
    base_cost += 10  # Lambda execution costs
    
    # Storage costs
    if any(s['name'] == 'Amazon DynamoDB' for s in services):
        base_cost += 25  # DynamoDB on-demand
    
    if any(s['name'] == 'Amazon S3' for s in services):
        base_cost += 5  # S3 storage
    
    # Additional services
    if any(s['name'] == 'Amazon API Gateway' for s in services):
        base_cost += 15
    
    if any(s['name'] in ['Amazon SNS', 'Amazon SQS'] for s in services):
        base_cost += 10
    
    if any(s['name'] == 'AWS Step Functions' for s in services):
        base_cost += 20
    
    # CloudWatch
    base_cost += 10  # Logs and metrics
    
    # Adjust for complexity
    if complexity == 'simple':
        multiplier = 0.7
    elif complexity == 'complex':
        multiplier = 1.5
    else:
        multiplier = 1.0
    
    estimated_cost = int(base_cost * multiplier)
    
    return f"${estimated_cost}-${estimated_cost * 2}/month (varies with usage)"


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
    
    if not job_name:
        raise ValueError("Missing required parameter: job_name")
    
    # Parse requirements if it's a string
    if isinstance(requirements_str, str):
        try:
            requirements = json.loads(requirements_str)
        except json.JSONDecodeError:
            requirements = {}
    else:
        requirements = requirements_str or {}
    
    # STEP 1: Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='solution-architect',
        action_name='select_services',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # STEP 3: Select appropriate AWS services based on requirements
        logger.info(f"Selecting services for job {job_name}")
        services = select_aws_services(requirements)
        
        # STEP 4: Generate service selection rationale
        rationale = generate_service_rationale(requirements, services)
        
        # Prepare response
        result = {
            "job_name": job_name,
            "services": services,
            "rationale": rationale,
            "status": "success"
        }
        
        # STEP 5: Log raw output to DynamoDB immediately with stored timestamp
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
        
        # STEP 6: Save service selection to S3 using save_converted_artifact
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            artifact=result,
            filename='service_selection.json',
            content_type='application/json'
        )
        
        # STEP 7: Save raw response to S3 using save_raw_response
        s3_client.save_raw_response(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            response=result,
            filename='select_services_raw_response.json'
        )
        
        logger.info(f"Service selection completed for job {job_name}")
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
    Generates infrastructure-as-code templates (CloudFormation).
    
    Args:
        event: Full Bedrock Agent event
        params: Extracted parameters (job_name, architecture)
        session_id: Bedrock session ID
        start_time: Request start time
        
    Returns:
        Dict with job_name, cloudformation_template, and status
    """
    job_name = params.get('job_name')
    architecture_str = params.get('architecture')
    
    if not job_name:
        raise ValueError("Missing required parameter: job_name")
    
    # Parse architecture if it's a string
    if isinstance(architecture_str, str):
        try:
            architecture = json.loads(architecture_str)
        except json.JSONDecodeError:
            architecture = {}
    else:
        architecture = architecture_str or {}
    
    # STEP 1: Log raw input to DynamoDB immediately
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='solution-architect',
        action_name='generate_iac',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']
    
    try:
        # STEP 3: Generate CloudFormation template referencing Lambda code files
        logger.info(f"Generating IaC templates for job {job_name}")
        
        # Retrieve code artifacts from Code Generator
        code_artifacts = retrieve_code_artifacts(job_name)
        
        # STEP 4: Include Bedrock Agent configuration from Code Generator
        agent_config = code_artifacts.get('agent_config') or {}
        
        # STEP 5: Set up IAM roles and policies
        # STEP 6: Configure action groups with OpenAPI schemas
        cloudformation_template = generate_complete_cloudformation_template(
            job_name=job_name,
            architecture=architecture,
            code_artifacts=code_artifacts,
            agent_config=agent_config
        )
        
        # Prepare response
        result = {
            "job_name": job_name,
            "cloudformation_template": cloudformation_template,
            "terraform_module": "",  # Not implemented yet
            "status": "success"
        }
        
        # STEP 7: Log raw output to DynamoDB immediately with stored timestamp
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            filename='infrastructure_template.yaml'
        )
        
        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )
        
        # STEP 8: Save IaC templates to S3 using save_converted_artifact
        s3_client.save_converted_artifact(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            artifact=cloudformation_template,
            filename='infrastructure_template.yaml',
            content_type='text/yaml'
        )
        
        # STEP 9: Save raw response to S3 using save_raw_response
        s3_client.save_raw_response(
            job_name=job_name,
            phase='architecture',
            agent_name='solution-architect',
            response=result,
            filename='generate_iac_raw_response.json'
        )
        
        logger.info(f"IaC generation completed for job {job_name}")
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


def generate_complete_cloudformation_template(
    job_name: str,
    architecture: Dict[str, Any],
    code_artifacts: Dict[str, Any],
    agent_config: Dict[str, Any]
) -> str:
    """
    Generate a complete CloudFormation template based on architecture design,
    code artifacts, and agent configuration.
    
    Args:
        job_name: Job identifier
        architecture: Architecture data dictionary
        code_artifacts: Code artifacts from Code Generator
        agent_config: Bedrock Agent configuration
        
    Returns:
        CloudFormation template as YAML string
    """
    resources = architecture.get('resources', {})
    bedrock_agent = resources.get('bedrock_agent', {})
    lambda_functions = resources.get('lambda_functions', [])
    dynamodb_tables = resources.get('dynamodb_tables', [])
    s3_buckets = resources.get('s3_buckets', [])
    iam_policies = architecture.get('iam_policies', {})
    
    # Extract agent details
    agent_name = agent_config.get('name', bedrock_agent.get('name', job_name))
    foundation_model = agent_config.get('foundation_model', bedrock_agent.get('foundation_model', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'))
    agent_instructions = agent_config.get('instructions', bedrock_agent.get('instructions', 'AI agent to assist users'))
    
    # Get Lambda code
    lambda_code = code_artifacts.get('lambda_code', '')
    if not lambda_code:
        lambda_code = """import json

def lambda_handler(event, context):
    \"\"\"Default Lambda handler for generated agent.\"\"\"
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Hello from generated agent!'})
    }
"""
    
    # Escape the Lambda code for YAML
    lambda_code_escaped = lambda_code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    
    # Start building template
    template = f"""AWSTemplateFormatVersion: '2010-09-09'
Description: Generated agent infrastructure for {job_name}

Parameters:
  Environment:
    Type: String
    Default: production
    Description: Environment name
  
  FoundationModel:
    Type: String
    Default: {foundation_model}
    Description: Bedrock foundation model ID

Resources:
"""
    
    # Add DynamoDB tables if needed
    if dynamodb_tables:
        for i, table in enumerate(dynamodb_tables):
            table_name = table.get('name', f'{job_name}-table-{i}')
            partition_key = table.get('partition_key', 'id')
            sort_key = table.get('sort_key')
            billing_mode = table.get('billing_mode', 'PAY_PER_REQUEST')
            
            template += f"""
  DynamoDBTable{i}:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub '${{Environment}}-{table_name}'
      BillingMode: {billing_mode}
      AttributeDefinitions:
        - AttributeName: {partition_key}
          AttributeType: S
"""
            if sort_key:
                template += f"""        - AttributeName: {sort_key}
          AttributeType: S
"""
            
            template += f"""      KeySchema:
        - AttributeName: {partition_key}
          KeyType: HASH
"""
            if sort_key:
                template += f"""        - AttributeName: {sort_key}
          KeyType: RANGE
"""
            
            template += """      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true
      Tags:
        - Key: Project
          Value: AutoNinja
        - Key: GeneratedBy
          Value: SolutionArchitect

"""
    
    # Add S3 buckets if needed
    if s3_buckets:
        for i, bucket in enumerate(s3_buckets):
            bucket_name = bucket.get('name', f'{job_name}-bucket-{i}')
            versioning = bucket.get('versioning', True)
            encryption = bucket.get('encryption', 'AES256')
            
            template += f"""
  S3Bucket{i}:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub '${{Environment}}-{bucket_name}-${{AWS::AccountId}}'
      VersioningConfiguration:
        Status: {'Enabled' if versioning else 'Suspended'}
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: {encryption}
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      Tags:
        - Key: Project
          Value: AutoNinja
        - Key: GeneratedBy
          Value: SolutionArchitect

"""
    
    # Add Lambda Execution Role
    lambda_policy_actions = iam_policies.get('lambda_execution_role', [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents'
    ])
    
    template += """
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
        - PolicyName: LambdaPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
"""
    
    for action in lambda_policy_actions:
        template += f"""                  - {action}
"""
    
    template += """                Resource: '*'
      Tags:
        - Key: Project
          Value: AutoNinja
        - Key: GeneratedBy
          Value: SolutionArchitect

"""
    
    # Add Lambda Functions
    if not lambda_functions:
        lambda_functions = [{
            'name': f'{agent_name}-lambda',
            'runtime': 'python3.12',
            'memory': 512,
            'timeout': 60,
            'handler': 'handler.lambda_handler',
            'environment_variables': {'LOG_LEVEL': 'INFO'}
        }]
    
    for i, func in enumerate(lambda_functions):
        func_name = func.get('name', f'{agent_name}-lambda-{i}')
        runtime = func.get('runtime', 'python3.12')
        memory = func.get('memory', 512)
        timeout = func.get('timeout', 60)
        handler = func.get('handler', 'handler.lambda_handler')
        env_vars = func.get('environment_variables', {})
        
        template += f"""
  AgentLambdaFunction{i}:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub '${{Environment}}-{func_name}'
      Runtime: {runtime}
      Handler: {handler}
      Role: !GetAtt LambdaExecutionRole.Arn
      Code:
        ZipFile: |
{chr(10).join('          ' + line for line in lambda_code.split(chr(10)))}
      MemorySize: {memory}
      Timeout: {timeout}
      Environment:
        Variables:
"""
        
        if env_vars:
            for key, value in env_vars.items():
                template += f"""          {key}: {value}
"""
        else:
            template += """          LOG_LEVEL: INFO
"""
        
        template += """      Tags:
        - Key: Project
          Value: AutoNinja
        - Key: GeneratedBy
          Value: SolutionArchitect

"""
        
        # Add Lambda permission for Bedrock to invoke
        template += f"""
  LambdaInvokePermission{i}:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref AgentLambdaFunction{i}
      Action: lambda:InvokeFunction
      Principal: bedrock.amazonaws.com
      SourceAccount: !Ref AWS::AccountId

"""
    
    # Add Bedrock Agent Execution Role
    bedrock_policy_actions = iam_policies.get('bedrock_agent_role', [
        'bedrock:InvokeModel',
        'lambda:InvokeFunction'
    ])
    
    template += """
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
            Condition:
              StringEquals:
                aws:SourceAccount: !Ref AWS::AccountId
      Policies:
        - PolicyName: BedrockAgentPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
"""
    
    for action in bedrock_policy_actions:
        template += f"""                  - {action}
"""
    
    template += """                Resource: '*'
      Tags:
        - Key: Project
          Value: AutoNinja
        - Key: GeneratedBy
          Value: SolutionArchitect

"""
    
    # Add CloudWatch Log Group for Bedrock Agent
    template += f"""
  BedrockAgentLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/aws/bedrock/agents/${{Environment}}-{agent_name}'
      RetentionInDays: 30

"""
    
    # Add Bedrock Agent
    # Note: OpenAPI schema would be referenced from S3 or inline
    openapi_schema = code_artifacts.get('openapi_schema', '')
    
    template += f"""
  BedrockAgent:
    Type: AWS::Bedrock::Agent
    Properties:
      AgentName: !Sub '${{Environment}}-{agent_name}'
      AgentResourceRoleArn: !GetAtt BedrockAgentRole.Arn
      FoundationModel: !Ref FoundationModel
      Instruction: |
        {agent_instructions}
      IdleSessionTTLInSeconds: 1800
      Tags:
        Project: AutoNinja
        GeneratedBy: SolutionArchitect

"""
    
    # Add Bedrock Agent Alias
    template += """
  BedrockAgentAlias:
    Type: AWS::Bedrock::AgentAlias
    Properties:
      AgentId: !Ref BedrockAgent
      AgentAliasName: prod
      Description: Production alias for generated agent

"""
    
    # Add Outputs
    template += f"""
Outputs:
  AgentId:
    Description: Bedrock Agent ID
    Value: !Ref BedrockAgent
    Export:
      Name: !Sub '${{Environment}}-{agent_name}-AgentId'
  
  AgentArn:
    Description: Bedrock Agent ARN
    Value: !GetAtt BedrockAgent.AgentArn
    Export:
      Name: !Sub '${{Environment}}-{agent_name}-AgentArn'
  
  AgentAliasId:
    Description: Bedrock Agent Alias ID
    Value: !GetAtt BedrockAgentAlias.AgentAliasId
    Export:
      Name: !Sub '${{Environment}}-{agent_name}-AgentAliasId'
  
  LambdaFunctionArn:
    Description: Lambda Function ARN
    Value: !GetAtt AgentLambdaFunction0.Arn
    Export:
      Name: !Sub '${{Environment}}-{agent_name}-LambdaArn'
"""
    
    if dynamodb_tables:
        template += """
  DynamoDBTableName:
    Description: DynamoDB Table Name
    Value: !Ref DynamoDBTable0
    Export:
      Name: !Sub '${Environment}-DynamoDBTableName'
"""
    
    if s3_buckets:
        template += """
  S3BucketName:
    Description: S3 Bucket Name
    Value: !Ref S3Bucket0
    Export:
      Name: !Sub '${Environment}-S3BucketName'
"""
    
    return template


def generate_cloudformation_template(job_name: str, architecture: Dict[str, Any]) -> str:
    """
    Legacy function - redirects to generate_complete_cloudformation_template.
    Kept for backward compatibility.
    
    Args:
        job_name: Job identifier
        architecture: Architecture data dictionary
        
    Returns:
        CloudFormation template as YAML string
    """
    return generate_complete_cloudformation_template(
        job_name=job_name,
        architecture=architecture,
        code_artifacts={},
        agent_config={}
    )
