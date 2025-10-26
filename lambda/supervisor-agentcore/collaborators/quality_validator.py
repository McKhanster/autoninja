"""
Quality Validator Module
Validates requirements, architecture, and code
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
    
    # Try to find JSON in markdown code blocks with closing marker
    json_block_pattern = r'```json\s*\n(.*?)\n```'
    matches = re.findall(json_block_pattern, text, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    # Try to find JSON block that starts with ```json but may not have closing marker
    if text.strip().startswith('```json'):
        # Remove the opening marker and any trailing closing marker
        content = text.strip()
        content = content.replace('```json', '', 1).strip()
        content = content.rstrip('`').strip()
        if content.startswith('{') or content.startswith('['):
            return content
    
    # Try to find any code block with closing marker
    code_block_pattern = r'```\s*\n(.*?)\n```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    
    if matches:
        potential_json = matches[0].strip()
        if potential_json.startswith('{') or potential_json.startswith('['):
            return potential_json
    
    # If no code blocks, return as-is
    result = text.strip()
    
    # Fix: If response starts with a quote (missing opening brace), prepend {
    if result.startswith('"') and not result.startswith('{"'):
        result = '{' + result
    
    # Fix: If response ends without closing brace, append }
    if result.startswith('{') and not result.endswith('}'):
        result = result + '}'
    
    # Try to parse and catch specific errors
    try:
        json.loads(result)
        return result
    except json.JSONDecodeError as e:
        # If it's a missing comma error, try to fix it
        if "Expecting ',' delimiter" in str(e):
            # Try to add missing commas before quotes that follow closing braces/brackets
            result = re.sub(r'([}\]"])\s*\n\s*"', r'\1,\n"', result)
            # Try again
            try:
                json.loads(result)
                return result
            except:
                pass
        # Return as-is if we can't fix it
        return result


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


def validate_validation_structure(validation: Dict[str, Any]) -> None:
    """Validate validation result has expected structure"""
    required_fields = ['is_valid', 'validation_type', 'score']
    
    for field in required_fields:
        if field not in validation:
            raise ValueError(f"Missing required field: {field}")


def validate(job_name: str, validation_type: str, data: Dict[str, Any], 
             requirements: Dict[str, Any] = None, architecture: Dict[str, Any] = None,
             session_id: str = None) -> Dict[str, Any]:
    """
    Validate requirements, architecture, or code
    
    Args:
        job_name: Unique job identifier
        validation_type: Type of validation ('requirements', 'architecture', 'code')
        data: Data to validate
        requirements: Requirements context (optional)
        architecture: Architecture context (optional)
        session_id: Session identifier for Bedrock Agent
        
    Returns:
        Dict with validation results
    """
    start_time = time.time()
    
    stack_outputs = get_stack_outputs()
    agent_id = stack_outputs.get('QualityValidatorAgentId')
    agent_alias_id = stack_outputs.get('QualityValidatorAliasId')
    
    if not agent_id or not agent_alias_id:
        raise ValueError("Could not find Quality Validator agent IDs")
    
    logger.info(f"Validating {validation_type} for job: {job_name}")
    
    apply_rate_limiting('quality-validator-bedrock')
    
    input_data = {
        "type": validation_type,
        "data": data,
        "requirements": requirements or {},
        "architecture": architecture or {}
    }
    
    # logger.info(f"QV input_data: {input_data}")
    bedrock_response = invoke_bedrock_agent(
        agent_id=agent_id,
        alias_id=agent_alias_id,
        session_id=session_id or f"{job_name}-qv-{validation_type}",
        input_text=json.dumps(input_data)
    )
    logger.info(f"QV bedrock_response length: {bedrock_response} chars")

    
    # Extract JSON from markdown if needed
    json_text = extract_json_from_markdown(bedrock_response)
    
    validation = json.loads(json_text)
    # validate_validation_structure(validation)
    
    result = {
        "job_name": job_name,
        "validation_type": validation_type,
        "is_valid": validation.get('is_valid', False),
        "score": validation.get('score', 0),
        "issues": validation.get('issues', []),
        "recommendations": validation.get('recommendations', []),
        "status": "success"
    }
    
    s3_client.save_converted_artifact(
        job_name=job_name,
        phase='validation',
        agent_name='quality-validator',
        artifact=result,
        filename=f'{validation_type}_validation.json',
        content_type='application/json'
    )
    
    logger.info(f"Validation completed in {time.time() - start_time:.2f}s")
    
    return result
