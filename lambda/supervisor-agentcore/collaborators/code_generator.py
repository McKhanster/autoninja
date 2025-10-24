"""
Code Generator Module
Generates Lambda code, agent configurations, and OpenAPI schemas
"""
import json
import time
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


def extract_json_from_markdown(text: str) -> str:
    """Extract JSON from markdown code blocks or return text as-is if already JSON"""
    import re
    
    # Try to find JSON in markdown code blocks
    json_block_pattern = r'```json\s*\n(.*?)\n```'
    matches = re.findall(json_block_pattern, text, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    # Try to find any code block
    code_block_pattern = r'```\s*\n(.*?)\n```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    
    if matches:
        potential_json = matches[0].strip()
        if potential_json.startswith('{') or potential_json.startswith('['):
            return potential_json
    
    # If no code blocks, return as-is
    return text.strip()


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


def validate_code_structure(code: Dict[str, Any]) -> None:
    """Validate code has expected structure"""
    required_sections = ['lambda_code', 'agent_config', 'openapi_schema']
    
    for section in required_sections:
        if section not in code:
            raise ValueError(f"Missing required section: {section}")


def generate(job_name: str, requirements: Dict[str, Any], architecture: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """
    Generate code based on requirements and architecture
    
    Args:
        job_name: Unique job identifier
        requirements: Requirements from requirements analyst
        architecture: Architecture from solution architect
        session_id: Session identifier for Bedrock Agent
        
    Returns:
        Dict with generated code
    """
    start_time = time.time()
    
    stack_outputs = get_stack_outputs()
    agent_id = stack_outputs.get('CodeGeneratorAgentId')
    agent_alias_id = stack_outputs.get('CodeGeneratorAliasId')
    
    if not agent_id or not agent_alias_id:
        raise ValueError("Could not find Code Generator agent IDs")
    
    logger.info(f"Code generation for job: {job_name}")
    
    # Log input to DynamoDB
    input_data = {
        "requirements": requirements,
        "architecture": architecture
    }
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='code-generator',
        action_name='generate',
        prompt=json.dumps(input_data, default=str),
        model_id='bedrock-agent'
    )['timestamp']
    
    apply_rate_limiting('code-generator-bedrock')
    
    logger.info(f"CG input_data: {input_data}")
    bedrock_response = invoke_bedrock_agent(
        agent_id=agent_id,
        alias_id=agent_alias_id,
        session_id=session_id,
        input_text=json.dumps(input_data)
    )
    logger.info(f"CG bedrock_response: {bedrock_response}")
    
    # Extract JSON from markdown if needed
    json_text = extract_json_from_markdown(bedrock_response)
    logger.info(f"CG extracted JSON (first 500 chars): {json_text[:500]}")
    
    code = json.loads(json_text)
    validate_code_structure(code)
    
    result = {
        "job_name": job_name,
        "code": code,
        "status": "success"
    }
    
    # Log output to DynamoDB
    duration = time.time() - start_time
    s3_uri = s3_client.get_s3_uri(
        job_name=job_name,
        phase='code',
        agent_name='code-generator',
        filename='code_generation.json'
    )
    
    dynamodb_client.log_inference_output(
        job_name=job_name,
        timestamp=timestamp,
        response=json.dumps(result, default=str),
        duration_seconds=duration,
        artifacts_s3_uri=s3_uri,
        status='success'
    )
    
    s3_client.save_converted_artifact(
        job_name=job_name,
        phase='code',
        agent_name='code-generator',
        artifact=result,
        filename='code_generation.json',
        content_type='application/json'
    )
    
    logger.info(f"Code generation completed in {duration:.2f}s")
    
    return result
