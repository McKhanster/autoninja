# Task 11.1: Supervisor Orchestration Logic Design

## Date: 2025-01-XX
## Task: Design supervisor orchestration logic with AgentCore Runtime

## Overview

This document describes the design of the AutoNinja supervisor agent that will be deployed to Amazon Bedrock AgentCore Runtime. The supervisor orchestrates 5 collaborator Bedrock Agents in a sequential workflow to transform natural language requests into fully deployed AI agents.

## Architecture Decision: AgentCore Runtime for Supervisor

### Why AgentCore Runtime?

1. **Extended Execution Time**: Up to 8 hours for complex agent generation workflows
2. **Framework Flexibility**: Can use custom orchestration logic without framework constraints
3. **Session Isolation**: Each user request runs in dedicated microVM with isolated resources
4. **Better Observability**: Built-in tracing for agent reasoning steps and tool invocations
5. **Consumption-Based Pricing**: Only pay for actual processing time, not idle waiting

### Why NOT AgentCore for Collaborators?

1. **Simplicity**: Collaborators have simple, well-defined actions (no complex orchestration needed)
2. **Native Action Groups**: Regular Bedrock Agents have mature action group support
3. **Proven Stability**: Regular Bedrock Agents are production-tested
4. **Easier Deployment**: CloudFormation support for regular agents is mature

## Supervisor Agent Design

### Core Responsibilities

1. **Job Name Generation**: Create unique identifier for each request
2. **Sequential Orchestration**: Invoke collaborators in logical order
3. **Data Flow Management**: Pass outputs from one agent as inputs to the next
4. **Validation Gating**: Check Quality Validator results before deployment
5. **Error Handling**: Retry failed invocations with exponential backoff
6. **Result Aggregation**: Collect and return final deployed agent ARN

### Orchestration Workflow

```
User Request
     ↓
Generate job_name: job-{keyword}-{YYYYMMDD-HHMMSS}
     ↓
┌────────────────────────────────────────────────────────┐
│ 1. Requirements Analyst                                 │
│    Input: user_request, job_name                       │
│    Output: requirements (JSON)                         │
└────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────┐
│ 2. Code Generator                                       │
│    Input: requirements, job_name                       │
│    Output: lambda_code, agent_config, openapi_schemas │
└────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────┐
│ 3. Solution Architect                                   │
│    Input: requirements, code_references, job_name      │
│    Output: architecture, iac_templates                 │
└────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────┐
│ 4. Quality Validator                                    │
│    Input: requirements, code, architecture, job_name   │
│    Output: validation_report, is_valid (boolean)       │
└────────────────────────────────────────────────────────┘
     ↓
   [GATE: is_valid == True?]
     ↓ YES                    ↓ NO
┌────────────────────┐   Return validation
│ 5. Deployment Mgr  │   failures to user
│    Input: all      │
│    artifacts       │
│    Output: agent   │
│    ARN, endpoints  │
└────────────────────┘
     ↓
Return deployed agent ARN to user
```

### Implementation Structure

```python
# File: lambda/supervisor-agentcore/supervisor_agent.py

from bedrock_agentcore import BedrockAgentCoreApp
import boto3
import json
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional

app = BedrockAgentCoreApp()

# Initialize AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-2')
dynamodb = boto3.client('dynamodb', region_name='us-east-2')
s3 = boto3.client('s3', region_name='us-east-2')

# Collaborator agent configuration (from CloudFormation outputs)
COLLABORATORS = {
    'requirements_analyst': {
        'agent_id': 'AGENT_ID_FROM_CFN',  # Will be set via environment variable
        'alias_id': 'ALIAS_ID_FROM_CFN',
        'name': 'Requirements Analyst'
    },
    'code_generator': {
        'agent_id': 'AGENT_ID_FROM_CFN',
        'alias_id': 'ALIAS_ID_FROM_CFN',
        'name': 'Code Generator'
    },
    'solution_architect': {
        'agent_id': 'AGENT_ID_FROM_CFN',
        'alias_id': 'ALIAS_ID_FROM_CFN',
        'name': 'Solution Architect'
    },
    'quality_validator': {
        'agent_id': 'AGENT_ID_FROM_CFN',
        'alias_id': 'ALIAS_ID_FROM_CFN',
        'name': 'Quality Validator'
    },
    'deployment_manager': {
        'agent_id': 'AGENT_ID_FROM_CFN',
        'alias_id': 'ALIAS_ID_FROM_CFN',
        'name': 'Deployment Manager'
    }
}

@app.entrypoint
def invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervisor agent entrypoint for orchestrating collaborator agents.
    
    Args:
        payload: Dict with 'prompt' key containing user request
        
    Returns:
        Dict with final deployed agent ARN and results
    """
    try:
        # Extract user request
        user_request = payload.get("prompt", "")
        if not user_request:
            return {
                "error": "No prompt provided",
                "status": "error"
            }
        
        # Generate unique job_name
        job_name = generate_job_name(user_request)
        print(f"[SUPERVISOR] Starting job: {job_name}")
        
        # Initialize results dictionary
        results = {
            "job_name": job_name,
            "user_request": user_request,
            "timestamp": datetime.utcnow().isoformat(),
            "collaborators": {}
        }
        
        # STEP 1: Requirements Analyst
        print(f"[SUPERVISOR] Invoking Requirements Analyst...")
        requirements = invoke_collaborator(
            collaborator='requirements_analyst',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "user_request": user_request,
                "action": "extract_requirements"
            }
        )
        results['collaborators']['requirements_analyst'] = requirements
        print(f"[SUPERVISOR] Requirements Analyst complete")
        
        # STEP 2: Code Generator
        print(f"[SUPERVISOR] Invoking Code Generator...")
        code = invoke_collaborator(
            collaborator='code_generator',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "requirements": requirements,
                "action": "generate_all"  # Generate lambda code, agent config, and schemas
            }
        )
        results['collaborators']['code_generator'] = code
        print(f"[SUPERVISOR] Code Generator complete")
        
        # STEP 3: Solution Architect
        print(f"[SUPERVISOR] Invoking Solution Architect...")
        architecture = invoke_collaborator(
            collaborator='solution_architect',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "requirements": requirements,
                "code_references": {
                    "lambda_code": f"s3://bucket/{job_name}/code/lambda_handler.py",
                    "agent_config": f"s3://bucket/{job_name}/code/agent_config.json",
                    "openapi_schemas": f"s3://bucket/{job_name}/code/openapi_schema.yaml"
                },
                "action": "design_architecture"
            }
        )
        results['collaborators']['solution_architect'] = architecture
        print(f"[SUPERVISOR] Solution Architect complete")
        
        # STEP 4: Quality Validator
        print(f"[SUPERVISOR] Invoking Quality Validator...")
        validation = invoke_collaborator(
            collaborator='quality_validator',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "requirements": requirements,
                "code": code,
                "architecture": architecture,
                "action": "validate_all"  # Run all validation checks
            }
        )
        results['collaborators']['quality_validator'] = validation
        print(f"[SUPERVISOR] Quality Validator complete")
        
        # STEP 5: Check validation gate
        is_valid = validation.get('is_valid', False)
        if not is_valid:
            print(f"[SUPERVISOR] Validation failed, stopping workflow")
            return {
                "job_name": job_name,
                "status": "validation_failed",
                "validation_issues": validation.get('issues', []),
                "quality_score": validation.get('quality_score', 0),
                "results": results
            }
        
        # STEP 6: Deployment Manager (only if validation passed)
        print(f"[SUPERVISOR] Validation passed, invoking Deployment Manager...")
        deployment = invoke_collaborator(
            collaborator='deployment_manager',
            session_id=job_name,
            input_data={
                "job_name": job_name,
                "requirements": requirements,
                "code": code,
                "architecture": architecture,
                "validation": validation,
                "action": "deploy_all"  # Generate CFN, deploy, configure, test
            }
        )
        results['collaborators']['deployment_manager'] = deployment
        print(f"[SUPERVISOR] Deployment Manager complete")
        
        # Return final result
        return {
            "job_name": job_name,
            "status": "deployed",
            "agent_arn": deployment.get('agent_arn'),
            "agent_alias_id": deployment.get('alias_id'),
            "endpoints": deployment.get('endpoints', {}),
            "results": results
        }
        
    except Exception as e:
        print(f"[SUPERVISOR] Error: {str(e)}")
        return {
            "error": str(e),
            "status": "error",
            "job_name": job_name if 'job_name' in locals() else None
        }


def generate_job_name(user_request: str) -> str:
    """
    Generate unique job_name from user request.
    
    Format: job-{keyword}-{YYYYMMDD-HHMMSS}
    
    Args:
        user_request: User's natural language request
        
    Returns:
        Unique job name string
    """
    # Extract keyword from request (first meaningful word)
    words = re.findall(r'\b\w+\b', user_request.lower())
    # Filter out common words
    stop_words = {'i', 'want', 'need', 'would', 'like', 'a', 'an', 'the', 'to', 'for'}
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    keyword = keywords[0] if keywords else 'agent'
    
    # Generate timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    
    return f"job-{keyword}-{timestamp}"


def invoke_collaborator(
    collaborator: str,
    session_id: str,
    input_data: Dict[str, Any],
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Invoke a collaborator Bedrock Agent via InvokeAgent API.
    
    Args:
        collaborator: Name of collaborator ('requirements_analyst', 'code_generator', etc.)
        session_id: Session ID (use job_name for consistency)
        input_data: Input data to pass to collaborator
        max_retries: Maximum number of retry attempts
        
    Returns:
        Parsed response from collaborator
        
    Raises:
        Exception: If invocation fails after all retries
    """
    config = COLLABORATORS[collaborator]
    agent_id = config['agent_id']
    alias_id = config['alias_id']
    agent_name = config['name']
    
    # Format input as text (Bedrock Agents expect text input)
    input_text = json.dumps(input_data)
    
    for attempt in range(max_retries):
        try:
            print(f"[SUPERVISOR] Invoking {agent_name} (attempt {attempt + 1}/{max_retries})...")
            
            # Invoke the collaborator agent
            response = bedrock_agent_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=True  # Enable tracing for debugging
            )
            
            # Parse streaming response
            result = parse_streaming_response(response)
            
            print(f"[SUPERVISOR] {agent_name} invocation successful")
            return result
            
        except Exception as e:
            print(f"[SUPERVISOR] {agent_name} invocation failed (attempt {attempt + 1}): {str(e)}")
            
            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                print(f"[SUPERVISOR] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # All retries exhausted
                raise Exception(f"Failed to invoke {agent_name} after {max_retries} attempts: {str(e)}")


def parse_streaming_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse streaming response from InvokeAgent API.
    
    Args:
        response: Response from bedrock_agent_runtime.invoke_agent()
        
    Returns:
        Parsed result as dictionary
    """
    result_text = ""
    
    # Process streaming response
    for event in response.get('completion', []):
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                result_text += chunk['bytes'].decode('utf-8')
    
    # Try to parse as JSON
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        # If not JSON, return as text
        return {"result": result_text}


if __name__ == "__main__":
    # For local testing
    app.run()
```

## Job Name Generation Strategy

### Format
```
job-{keyword}-{YYYYMMDD-HHMMSS}
```

### Examples
- User: "I would like a friend agent" → `job-friend-20250115-143022`
- User: "Create a customer support agent" → `job-customer-20250115-143045`
- User: "Build an invoice processing agent" → `job-invoice-20250115-143102`

### Algorithm
1. Extract words from user request
2. Filter out stop words (i, want, need, would, like, a, an, the, to, for)
3. Take first meaningful word (length > 2)
4. Append UTC timestamp in YYYYMMDD-HHMMSS format
5. Prefix with "job-"

## Error Handling Strategy

### Retry Logic
- **Max Retries**: 3 attempts per collaborator
- **Backoff**: Exponential (2^attempt seconds)
- **Retry Conditions**: All exceptions (network, throttling, service errors)

### Error Scenarios

#### 1. Collaborator Invocation Failure
```python
try:
    result = invoke_collaborator(...)
except Exception as e:
    # Log error
    # Return error response to user
    return {
        "error": f"Failed to invoke {collaborator}: {str(e)}",
        "status": "error",
        "job_name": job_name
    }
```

#### 2. Validation Failure (Not an Error)
```python
if not validation.get('is_valid'):
    # This is expected behavior, not an error
    return {
        "status": "validation_failed",
        "validation_issues": validation.get('issues'),
        "job_name": job_name
    }
```

#### 3. Deployment Failure
```python
try:
    deployment = invoke_collaborator('deployment_manager', ...)
except Exception as e:
    # Log error
    # Save partial results to S3
    # Return error with recovery instructions
    return {
        "error": "Deployment failed",
        "details": str(e),
        "status": "deployment_error",
        "job_name": job_name,
        "recovery": "Check CloudWatch logs and retry deployment manually"
    }
```

## Data Flow Between Collaborators

### 1. Requirements Analyst → Code Generator
```json
{
  "job_name": "job-friend-20250115-143022",
  "requirements": {
    "agent_purpose": "Friendly conversational agent",
    "capabilities": ["casual_conversation", "emotional_support"],
    "system_prompts": "You are a friendly agent...",
    "lambda_requirements": {...},
    "architecture_requirements": {...}
  }
}
```

### 2. Code Generator → Solution Architect
```json
{
  "job_name": "job-friend-20250115-143022",
  "requirements": {...},
  "code_references": {
    "lambda_code": "s3://bucket/job-friend-20250115-143022/code/lambda_handler.py",
    "agent_config": "s3://bucket/job-friend-20250115-143022/code/agent_config.json",
    "openapi_schemas": "s3://bucket/job-friend-20250115-143022/code/openapi_schema.yaml"
  }
}
```

### 3. Solution Architect → Quality Validator
```json
{
  "job_name": "job-friend-20250115-143022",
  "requirements": {...},
  "code": {...},
  "architecture": {
    "services": ["Bedrock Agent", "Lambda", "CloudWatch"],
    "iac_template": "s3://bucket/job-friend-20250115-143022/architecture/cloudformation.yaml"
  }
}
```

### 4. Quality Validator → Deployment Manager
```json
{
  "job_name": "job-friend-20250115-143022",
  "requirements": {...},
  "code": {...},
  "architecture": {...},
  "validation": {
    "is_valid": true,
    "quality_score": 85,
    "issues": [],
    "security_findings": []
  }
}
```

## Configuration Management

### Environment Variables
```bash
# Collaborator agent IDs (from CloudFormation outputs)
REQUIREMENTS_ANALYST_AGENT_ID=AGENT123
REQUIREMENTS_ANALYST_ALIAS_ID=ALIAS123
CODE_GENERATOR_AGENT_ID=AGENT456
CODE_GENERATOR_ALIAS_ID=ALIAS456
SOLUTION_ARCHITECT_AGENT_ID=AGENT789
SOLUTION_ARCHITECT_ALIAS_ID=ALIAS789
QUALITY_VALIDATOR_AGENT_ID=AGENT012
QUALITY_VALIDATOR_ALIAS_ID=ALIAS012
DEPLOYMENT_MANAGER_AGENT_ID=AGENT345
DEPLOYMENT_MANAGER_ALIAS_ID=ALIAS345

# AWS resources
DYNAMODB_TABLE_NAME=autoninja-inference-records-production
S3_BUCKET_NAME=autoninja-artifacts-{account-id}-production

# Configuration
AWS_REGION=us-east-2
LOG_LEVEL=INFO
```

### Configuration File (.bedrock_agentcore.yaml)
```yaml
bedrock_agentcore:
  agent_runtime_arn: arn:aws:bedrock-agentcore:us-east-2:123456789012:agent-runtime/abc123
  region: us-east-2
  execution_role_arn: arn:aws:iam::123456789012:role/AutoNinjaAgentCoreSupervisorRole-production

deployment:
  entrypoint: supervisor_agent.py
  requirements_file: requirements.txt
  python_version: "3.12"
  
observability:
  cloudwatch_logs: true
  log_group: /aws/bedrock/agentcore/autoninja-supervisor-production
  
environment_variables:
  REQUIREMENTS_ANALYST_AGENT_ID: ${CFN_OUTPUT:RequirementsAnalystAgentId}
  REQUIREMENTS_ANALYST_ALIAS_ID: ${CFN_OUTPUT:RequirementsAnalystAgentAliasId}
  # ... other agent IDs
```

## Observability and Logging

### CloudWatch Logs
- **Log Group**: `/aws/bedrock/agentcore/autoninja-supervisor-production`
- **Log Format**: Structured JSON with timestamps
- **Log Levels**: INFO, WARN, ERROR

### Log Messages
```python
# Start of workflow
print(f"[SUPERVISOR] Starting job: {job_name}")

# Before each collaborator invocation
print(f"[SUPERVISOR] Invoking {agent_name}...")

# After successful invocation
print(f"[SUPERVISOR] {agent_name} complete")

# On validation gate
print(f"[SUPERVISOR] Validation {'passed' if is_valid else 'failed'}")

# On error
print(f"[SUPERVISOR] Error: {str(e)}")
```

### Tracing
- Enable `enableTrace=True` in InvokeAgent calls
- AgentCore Runtime provides built-in tracing for:
  - Agent reasoning steps
  - Tool invocations
  - Model interactions
  - Execution timeline

## Testing Strategy

### Local Testing
```bash
# Start supervisor locally
python supervisor_agent.py

# Test with curl
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "I would like a friend agent"}'
```

### Mock Collaborators for Local Testing
```python
# Add mock mode for local testing
MOCK_MODE = os.environ.get('MOCK_MODE', 'false').lower() == 'true'

def invoke_collaborator(collaborator, session_id, input_data, max_retries=3):
    if MOCK_MODE:
        # Return mock responses for local testing
        return get_mock_response(collaborator, input_data)
    else:
        # Real invocation
        # ... existing code
```

### Integration Testing
1. Deploy supervisor to AgentCore Runtime
2. Invoke with test request
3. Verify all collaborators invoked in correct order
4. Check DynamoDB for inference records
5. Check S3 for artifacts
6. Verify final response contains agent ARN

## Deployment Process

### 1. Configure
```bash
agentcore configure -e supervisor_agent.py -r us-east-2
```

### 2. Deploy
```bash
agentcore launch
```

### 3. Test
```bash
agentcore invoke '{"prompt": "I would like a friend agent"}'
```

### 4. Get ARN
```bash
# ARN is in .bedrock_agentcore.yaml or from launch output
cat .bedrock_agentcore.yaml | grep agent_runtime_arn
```

## Success Criteria

- ✅ Supervisor generates unique job_name for each request
- ✅ Supervisor invokes all 5 collaborators in correct sequential order
- ✅ Supervisor passes job_name to all collaborators
- ✅ Supervisor waits for each collaborator to complete before proceeding
- ✅ Supervisor checks validation gate before invoking Deployment Manager
- ✅ Supervisor aggregates results from all collaborators
- ✅ Supervisor returns final deployed agent ARN
- ✅ Supervisor handles errors with retry logic
- ✅ Supervisor logs all orchestration steps to CloudWatch
- ✅ Supervisor completes within 8-hour execution limit

## Next Steps

1. ✅ **Task 11.1 Complete**: Design documented
2. **Task 11.2**: Implement supervisor agent code
3. **Task 11.3**: Create requirements.txt and configuration
4. **Task 11.4**: Test locally with mock collaborators
5. **Task 11.5**: Deploy to AgentCore Runtime
6. **Task 11.6**: Update CloudFormation template
7. **Task 11.7**: Configure custom orchestration for collaborators
8. **Task 11.8**: Test end-to-end orchestration
