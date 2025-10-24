"""
Requirements Analyst Module
Analyzes user requests and generates structured requirements
"""
import json
import time
from typing import Dict, Any
import boto3
from botocore.config import Config

# Import shared utilities
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

# Initialize clients
dynamodb_client = DynamoDBClient()
s3_client = S3Client()
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', config=config)
cloudformation = boto3.client('cloudformation')
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


def extract_json_from_markdown(text: str) -> str:
    """Extract JSON from markdown code blocks or return text as-is if already JSON"""
    import re
    
    # Try to find JSON in markdown code blocks - more flexible pattern
    # Matches ```json ... ``` with any whitespace
    json_block_pattern = r'```json\s*(.*?)```'
    matches = re.findall(json_block_pattern, text, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    # Try to find any code block - more flexible pattern
    code_block_pattern = r'```\s*(.*?)```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    
    if matches:
        potential_json = matches[0].strip()
        if potential_json.startswith('{') or potential_json.startswith('['):
            return potential_json
    
    # If no code blocks, return as-is (might already be pure JSON)
    result = text.strip()
    
    # Fix: If response starts with a quote (missing opening brace), prepend {
    if result.startswith('"') and not result.startswith('{"'):
        result = '{' + result
    
    # Fix: If response ends without closing brace, append }
    if result.startswith('{') and not result.endswith('}'):
        result = result + '}'
    
    return result


def validate_requirements_structure(requirements: Dict[str, Any]) -> None:
    """Validate requirements have expected structure"""
    required_sections = ['executive_summary', 'for_solution_architect', 'for_code_generator', 
                        'for_quality_validator', 'for_deployment_manager', 'validation_criteria']
    
    for section in required_sections:
        if section not in requirements:
            raise ValueError(f"Missing required section: {section}")


def analyze(job_name: str, user_request: str, session_id: str) -> Dict[str, Any]:
    """
    Analyze user request and generate structured requirements
    
    Args:
        job_name: Unique job identifier
        user_request: User's natural language request
        session_id: Session identifier for Bedrock Agent
        
    Returns:
        Dict with requirements structure
    """
    start_time = time.time()
    
    # Get agent IDs from CloudFormation
    stack_outputs = get_stack_outputs()
    agent_id = stack_outputs.get('RequirementsAnalystAgentId')
    agent_alias_id = stack_outputs.get('RequirementsAnalystAliasId')
    
    if not agent_id or not agent_alias_id:
        raise ValueError("Could not find Requirements Analyst agent IDs in CloudFormation outputs")
    
    # Log raw input
    raw_request = json.dumps({"job_name": job_name, "user_request": user_request}, default=str)
    logger.info(f"RAW REQUEST for {job_name}: {raw_request}")
    
    # Log to DynamoDB
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='requirements-analyst',
        action_name='analyze',
        prompt=raw_request,
        model_id='bedrock-agent'
    )['timestamp']
    
    logger.info(f"Requirements analysis for job: {job_name}")
    
    # Rate limit before calling Bedrock Agent
    apply_rate_limiting('requirements-analyst-bedrock')
    
    # Call Bedrock Agent
    logger.info(f"RA user_request: {user_request}")
    bedrock_response = invoke_bedrock_agent(
        agent_id=agent_id,
        alias_id=agent_alias_id,
        session_id=session_id,
        input_text=user_request
    )
    logger.info(f"RA bedrock_response: {bedrock_response}")
    
    # Extract JSON from markdown if needed
    json_text = extract_json_from_markdown(bedrock_response)
    logger.info(f"RA extracted JSON (first 500 chars): {json_text}")
    
    # Parse AI response
    requirements = json.loads(json_text)
    validate_requirements_structure(requirements)
    
    # Prepare result
    result = {
        "job_name": job_name,
        "requirements": requirements,
        "status": "success"
    }
    
    # Log raw output
    duration = time.time() - start_time
    raw_response = json.dumps(result, default=str)
    logger.info(f"RAW RESPONSE for {job_name}: {raw_response}")
    
    # Log to DynamoDB
    s3_uri = s3_client.get_s3_uri(
        job_name=job_name,
        phase='requirements',
        agent_name='requirements-analyst',
        filename='requirements_analysis.json'
    )
    
    dynamodb_client.log_inference_output(
        job_name=job_name,
        timestamp=timestamp,
        response=raw_response,
        duration_seconds=duration,
        artifacts_s3_uri=s3_uri,
        status='success'
    )
    
    # Save artifacts to S3
    s3_client.save_converted_artifact(
        job_name=job_name,
        phase='requirements',
        agent_name='requirements-analyst',
        artifact=result,
        filename='requirements_analysis.json',
        content_type='application/json'
    )
    
    logger.info(f"Requirements analysis completed in {duration:.2f}s")
    
    return result
