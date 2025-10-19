# Design Document

## Overview

This design addresses two critical issues for the AutoNinja hackathon submission:

1. **AgentCore Implementation**: Enhance the existing CloudFormation-based supervisor agent with Amazon Bedrock AgentCore Memory and Runtime capabilities to meet hackathon requirements
2. **Throttling Resolution**: Implement comprehensive rate limiting and retry mechanisms to eliminate `throttlingException` errors

The design follows an **enhancement architecture** approach - keeping the existing CloudFormation-based supervisor and 5 collaborator Bedrock Agents unchanged while adding AgentCore Memory for rate limiting and AgentCore Runtime capabilities. This minimizes risk and implementation time while meeting hackathon requirements.

### Key Design Principles

- **Minimal Risk**: Change only the supervisor component, keep collaborators unchanged
- **Hackathon Compliance**: Use AgentCore to meet "at least 1 primitive" requirement
- **Throttling Elimination**: Use AgentCore Memory to implement robust rate limiting and retry mechanisms
- **Enhanced Architecture**: CloudFormation Bedrock supervisor enhanced with AgentCore Memory + Runtime
- **Time Efficiency**: Complete implementation within hackathon deadline constraints

## Architecture

### High-Level Enhanced Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Request                               │
│              "I would like a friend agent"                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Enhanced Bedrock Supervisor (ENHANCED)                  │
│  - Standard AWS Bedrock Agent (CloudFormation)                      │
│  - Enhanced with AgentCore Memory for rate limiting                 │
│  - Enhanced with AgentCore Runtime capabilities                     │
│  - Sequential orchestration with Memory-based rate limiting         │
│  - Invokes 5 Bedrock collaborators via boto3                       │
│  - Implements exponential backoff for throttling                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │ 1. Requirements     │
                   │    Analyst Agent    │
                   │ (Bedrock - UNCHANGED)│
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ 2. Code Generator   │
                   │    Agent            │
                   │ (Bedrock - UNCHANGED)│
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ 3. Solution         │
                   │    Architect Agent  │
                   │ (Bedrock - UNCHANGED)│
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ 4. Quality          │
                   │    Validator Agent  │
                   │ (Bedrock - UNCHANGED)│
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ 5. Deployment       │
                   │    Manager Agent    │
                   │ (Bedrock - UNCHANGED)│
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │  Generated Agent    │
                   │  ARN + Endpoints    │
                   └─────────────────────┘

═══════════════════════════════════════════════════════════════════════
                    RATE LIMITING & THROTTLING PROTECTION
═══════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│                    Enhanced Rate Limiting                             │
│                                                                      │
│  ┌──────────────────────┐         ┌──────────────────────┐         │
│  │  DynamoDB Rate       │         │  Exponential Backoff │         │
│  │  Limiter Table       │         │  with Jitter         │         │
│  │                      │         │                      │         │
│  │  - Agent timestamps  │         │  - 1s, 2s, 4s, 8s   │         │
│  │  - 30s min interval  │         │  - Max 5 retries     │         │
│  │  - Conditional writes│         │  - Random jitter     │         │
│  └──────────────────────┘         └──────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

### Enhanced Supervisor Implementation

**Framework**: Standard AWS Bedrock Agent enhanced with AgentCore Memory SDK
**Deployment**: CloudFormation with AgentCore resources
**Runtime**: Standard Lambda execution enhanced with AgentCore Memory access
**Execution**: Standard Lambda timeout with AgentCore Memory for rate limiting
**Invocation**: Standardre invck Agent `InvokeAgent` API

### Rate Limiting Strategy

**Primary Protection**: AgentCore Memory-based distributed rate limiter
**Secondary Protection**: Exponential backoff with jitter
**Minimum Interval**: 30 seconds between ANY model invocations (including supervisor)
**Universal Enforcement**: ALL agents including supervisor must adhere to 30-second limit
**Retry Logic**: 5 attempts with exponential delays

## Components and Interfaces

### 1. Enhanced Supervisor Implementation

**File**: `lambda/supervisor/handler.py` (enhanced eent.py`ile)

```python
import boto3
import json
import time
import random
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
bedrock_agentcore = boto3.client('bedrock-agentcore')
s3 = boto3.client('s3')

# Configuration
MEMORY_ID = os.environ.get('MEMORY_ID')
MIN_INTERVAL_SECONDS = 30  # 30 seconds minimum between ANY model invocations
MAX_RETRIES = 5
BASE_DELAY = 1.0
GLOBAL_RATE_LIMIT_KEY = "global-model-invocations"  # Track all model calls

def lambda_handler(event, context):
    """
    Enhanced Bedrock Agent supervisor with AgentCore Memory rate limiting.
    
    Args:
        payload: Dict with 'prompt' key containing user request
        
    Returns:
        Dict with final deployed agent ARN and results
    """
    try:
        user_request = payload.get("prompt", "")
        
        # Generate unique job_name
        job_name = generate_job_name(user_request)
        
        # Log start of orchestration
        log_to_cloudwatch(f"Starting orchestration for job: {job_name}")
        
        # Sequential orchestration with rate limiting
        results = {}
        
        # 1. Requirements Analyst
        requirements = invoke_collaborator_with_rate_limiting(
            agent_id=get_agent_id("requirements-analyst"),
            alias_id=get_alias_id("requirements-analyst"),
            session_id=job_name,
            input_text=f"job_name: {job_name}\nrequest: {user_request}",
            agent_name="requirements-analyst"
        )
        results['requirements'] = requirements
        
        # 2. Code Generator
        code = invoke_collaborator_with_rate_limiting(
            agent_id=get_agent_id("code-generator"),
            alias_id=get_alias_id("code-generator"),
            session_id=job_name,
            input_text=f"job_name: {job_name}\nrequirements: {json.dumps(requirements)}",
            agent_name="code-generator"
        )
        results['code'] = code
        
        # 3. Solution Architect
        architecture = invoke_collaborator_with_rate_limiting(
            agent_id=get_agent_id("solution-architect"),
            alias_id=get_alias_id("solution-architect"),
            session_id=job_name,
            input_text=f"job_name: {job_name}\nrequirements: {json.dumps(requirements)}\ncode: {json.dumps(code)}",
            agent_name="solution-architect"
        )
        results['architecture'] = architecture
        
        # 4. Quality Validator
        validation = invoke_collaborator_with_rate_limiting(
            agent_id=get_agent_id("quality-validator"),
            alias_id=get_alias_id("quality-validator"),
            session_id=job_name,
            input_text=f"job_name: {job_name}\ncode: {json.dumps(code)}\narchitecture: {json.dumps(architecture)}",
            agent_name="quality-validator"
        )
        results['validation'] = validation
        
        # 5. Deployment Manager (only if validation passes)
        if validation.get('is_valid', False):
            deployment = invoke_collaborator_with_rate_limiting(
                agent_id=get_agent_id("deployment-manager"),
                alias_id=get_alias_id("deployment-manager"),
                session_id=job_name,
                input_text=f"job_name: {job_name}\nall_artifacts: {json.dumps(results)}",
                agent_name="deployment-manager"
            )
            results['deployment'] = deployment
            
            return {
                "job_name": job_name,
                "agent_arn": deployment.get('agent_arn'),
                "status": "deployed",
                "results": results
            }
        else:
            return {
                "job_name": job_name,
                "status": "validation_failed",
                "validation_issues": validation.get('issues', []),
                "results": results
            }
            
    except Exception as e:
        log_to_cloudwatch(f"Error in supervisor orchestration: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

def invoke_collaborator_with_rate_limiting(
    agent_id: str, 
    alias_id: str, 
    session_id: str, 
    input_text: str,
    agent_name: str
) -> Dict[str, Any]:
    """
    Invoke a collaborator agent with rate limiting and retry logic.
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Check and enforce GLOBAL rate limiting (applies to ALL agents including supervisor)
            wait_time = check_and_enforce_global_rate_limit()
            if wait_time > 0:
                log_to_cloudwatch(f"Global rate limiting: waiting {wait_time}s before invoking {agent_name}")
                time.sleep(wait_time)
            
            # Update global rate limiter timestamp BEFORE making the call
            update_global_rate_limiter_timestamp(agent_name)
            
            # Invoke the collaborator
            response = bedrock_agent_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=True
            )
            
            # Parse streaming response
            result = ""
            for event in response.get('completion', []):
                if 'chunk' in event:
                    result += event['chunk']['bytes'].decode('utf-8')
            
            log_to_cloudwatch(f"Successfully invoked {agent_name} on attempt {attempt + 1}")
            return json.loads(result) if result else {}
            
        except Exception as e:
            if "throttlingException" in str(e) and attempt < MAX_RETRIES - 1:
                # Exponential backoff with jitter
                delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                log_to_cloudwatch(f"Throttling detected for {agent_name}, retrying in {delay:.2f}s (attempt {attempt + 1})")
                time.sleep(delay)
                continue
            else:
                log_to_cloudwatch(f"Failed to invoke {agent_name} after {attempt + 1} attempts: {str(e)}")
                raise e
    
    raise Exception(f"Failed to invoke {agent_name} after {MAX_RETRIES} attempts")

def check_and_enforce_global_rate_limit() -> float:
    """
    Check global rate limiter using AgentCore Memory for ANY model invocation.
    This applies to ALL agents including the supervisor.
    
    Returns:
        float: Seconds to wait (0 if no wait needed)
    """
    try:
        # Retrieve global rate limiting data from AgentCore Memory
        response = bedrock_agentcore.retrieve_memory_records(
            memoryId=MEMORY_ID,
            actorId="rate-limiter",
            sessionId=GLOBAL_RATE_LIMIT_KEY,
            maxResults=1
        )
        
        if response.get('memoryRecords'):
            record = response['memoryRecords'][0]
            content = json.loads(record['content'])
            last_invocation = datetime.fromisoformat(content['last_invocation'])
            elapsed = (datetime.now() - last_invocation).total_seconds()
            
            if elapsed < MIN_INTERVAL_SECONDS:
                wait_time = MIN_INTERVAL_SECONDS - elapsed
                log_to_cloudwatch(f"Global rate limit: waiting {wait_time:.2f}s since last model invocation")
                return wait_time
        
        return 0.0
        
    except Exception as e:
        log_to_cloudwatch(f"Error checking global rate limit: {str(e)}")
        return 0.0

def update_global_rate_limiter_timestamp(agent_name: str):
    """
    Update the global rate limiter timestamp for ANY model invocation using AgentCore Memory.
    This records that ANY agent (including supervisor) made a model call.
    """
    try:
        content = {
            "last_invocation": datetime.now().isoformat(),
            "last_agent": agent_name,
            "invocation_count": 1,
            "created_at": datetime.now().isoformat()
        }
        
        # Update global rate limit tracker
        bedrock_agentcore.store_memory_record(
            memoryId=MEMORY_ID,
            actorId="rate-limiter",
            sessionId=GLOBAL_RATE_LIMIT_KEY,
            content=json.dumps(content)
        )
        
        # Also update individual agent tracker for monitoring
        bedrock_agentcore.store_memory_record(
            memoryId=MEMORY_ID,
            actorId="rate-limiter",
            sessionId=agent_name,
            content=json.dumps(content)
        )
        
        log_to_cloudwatch(f"Updated global rate limiter: {agent_name} made model invocation")
    except Exception as e:
        log_to_cloudwatch(f"Error updating global rate limiter for {agent_name}: {str(e)}")

def generate_job_name(user_request: str) -> str:
    """Generate unique job_name from user request"""
    # Extract keyword from request
    keyword = extract_keyword(user_request)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"job-{keyword}-{timestamp}"

def extract_keyword(request: str) -> str:
    """Extract a keyword from the user request"""
    # Simple keyword extraction
    words = request.lower().split()
    keywords = ['friend', 'customer', 'support', 'chat', 'assistant', 'agent']
    
    for word in words:
        if word in keywords:
            return word
    
    return 'agent'  # default

def get_agent_id(agent_name: str) -> str:
    """Get agent ID from environment or CloudFormation outputs"""
    # These would be set as environment variables during deployment
    agent_ids = {
        'requirements-analyst': os.environ.get('REQUIREMENTS_ANALYST_AGENT_ID'),
        'code-generator': os.environ.get('CODE_GENERATOR_AGENT_ID'),
        'solution-architect': os.environ.get('SOLUTION_ARCHITECT_AGENT_ID'),
        'quality-validator': os.environ.get('QUALITY_VALIDATOR_AGENT_ID'),
        'deployment-manager': os.environ.get('DEPLOYMENT_MANAGER_AGENT_ID')
    }
    return agent_ids.get(agent_name)

def get_alias_id(agent_name: str) -> str:
    """Get alias ID from environment or CloudFormation outputs"""
    # These would be set as environment variables during deployment
    alias_ids = {
        'requirements-analyst': os.environ.get('REQUIREMENTS_ANALYST_ALIAS_ID'),
        'code-generator': os.environ.get('CODE_GENERATOR_ALIAS_ID'),
        'solution-architect': os.environ.get('SOLUTION_ARCHITECT_ALIAS_ID'),
        'quality-validator': os.environ.get('QUALITY_VALIDATOR_ALIAS_ID'),
        'deployment-manager': os.environ.get('DEPLOYMENT_MANAGER_ALIAS_ID')
    }
    return alias_ids.get(agent_name)

def log_to_cloudwatch(message: str):
    """Log message to CloudWatch"""
    print(f"[{datetime.now().isoformat()}] {message}")
```

### 2. AgentCore Memory for Rate Limiting

**Memory Name**: `autoninja-rate-limiter-memory`

**Memory Structure**:
```python
# Store rate limiting data in AgentCore Memory
{
    "actor_id": "rate-limiter",
    "session_id": agent_name,  # e.g., "requirements-analyst"
    "content": {
        "last_invocation": "2025-10-19T16:30:22.123Z",
        "invocation_count": 1,
        "created_at": "2025-10-19T16:30:22.123Z"
    }
}
```

**CloudFormation Resource**:
```yaml
AgentCoreMemory:
  Type: AWS::BedrockAgentCore::Memory
  Properties:
    Name: !Sub "autoninja-rate-limiter-memory-${Environment}"
    Description: "Memory store for AutoNinja agent rate limiting"
    EventExpiryDuration: 30  # 30 days retention
    Tags:
      Environment: !Ref Environment
      Project: AutoNinja
      Purpose: RateLimiting

AgentCoreMemoryRole:
  Type: AWS::IAM::Role
  Properties:
    AssumeRolePolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            Service: bedrock-agentcore.amazonaws.com
          Action: sts:AssumeRole
    Policies:
      - PolicyName: AgentCoreMemoryAccess
        PolicyDocument:
          Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - bedrock-agentcore:StoreMemoryRecord
                - bedrock-agentcore:RetrieveMemoryRecords
                - bedrock-agentcore:ListMemoryRecords
              Resource: !GetAtt AgentCoreMemory.MemoryArn
```

### 3. CloudFormation Template Updates

**Remove Supervisor Agent Resources**:
- Remove `SupervisorAgentRole`
- Remove `SupervisorAgent`
- Remove `SupervisorAgentAlias`
- Remove `SupervisorAgentLogGroup`

**Add AgentCore-Specific Resources**:
```yaml
# Add parameter for AgentCore Runtime ARN
SupervisorAgentCoreRuntimeArn:
  Type: String
  Description: >
    ARN of the deployed AgentCore Runtime supervisor agent. This is deployed separately
    using the agentcore CLI. Example: arn:aws:bedrock-agentcore:us-east-2:123456789012:runtime/autoninja_supervisor-xxxxx
  Default: ""
  AllowedPattern: "^$|^arn:aws:bedrock-agentcore:[a-z0-9-]+:[0-9]{12}:runtime/[a-zA-Z0-9_-]+$"
  ConstraintDescription: >
    Must be a valid AgentCore Runtime ARN or empty string. Format: arn:aws:bedrock-agentcore:region:account:runtime/name

# Add condition for AgentCore ARN
Conditions:
  HasSupervisorAgentCoreArn: !Not [!Equals [!Ref SupervisorAgentCoreRuntimeArn, ""]]

# Add AgentCore Memory for rate limiting
AgentCoreMemory:
  Type: AWS::BedrockAgentCore::Memory
  Properties:
    Name: !Sub "autoninja-rate-limiter-memory-${Environment}"
    Description: "Memory store for AutoNinja agent rate limiting"
    EventExpiryDuration: 30  # 30 days retention
    Tags:
      Environment: !Ref Environment
      Project: AutoNinja

# Update outputs
SupervisorAgentCoreRuntimeArn:
  Description: >
    ARN of the AgentCore Runtime supervisor agent. This agent is deployed separately using
    the agentcore CLI and orchestrates all 5 collaborator agents. Use this ARN to invoke
    the supervisor via the InvokeAgentRuntime API.
  Value: !If
    - HasSupervisorAgentCoreArn
    - !Ref SupervisorAgentCoreRuntimeArn
    - "NOT_DEPLOYED - Deploy supervisor using: agentcore launch"
  Export:
    Name: !Sub "${AWS::StackName}-SupervisorAgentCoreRuntimeArn"

SupervisorInvocationCommand:
  Description: Command to invoke the AgentCore Runtime supervisor agent
  Value: !If
    - HasSupervisorAgentCoreArn
    - !Sub |
        # Using agentcore CLI (recommended):
        agentcore invoke '{"prompt": "I would like a friend agent"}'
        
        # Or using AWS SDK (Python):
        # import boto3, json
        # client = boto3.client('bedrock-agentcore', region_name='${AWS::Region}')
        # response = client.invoke_agent_runtime(
        #     agentRuntimeArn='${SupervisorAgentCoreRuntimeArn}',
        #     runtimeSessionId='unique-session-id',
        #     payload=json.dumps({"prompt": "I would like a friend agent"}).encode(),
        #     qualifier="DEFAULT"
        # )
    - "Deploy supervisor first using: agentcore launch"
```

### 4. AgentCore Deployment Configuration

**File**: `lambda/supervisor-agentcore/requirements.txt`

```txt
bedrock-agentcore
boto3>=1.34.0
```

**Note**: AgentCore uses the starter toolkit for configuration, not a YAML file. The toolkit creates a hidden `.bedrock_agentcore.yaml` file during the `agentcore configure` command.

### 5. Deployment Scripts

**File**: `scripts/deploy_agentcore_supervisor.sh`

```bash
#!/bin/bash

set -e

# Configuration
REGION="us-east-2"
PROFILE="AdministratorAccess-784327326356"
STACK_NAME="autoninja-production"

echo "=== Deploying Enhanced Supervisor with AgentCore ==="

# Deploy CloudFormation stack with AgentCore resources
echo "Deploying CloudFormation stack with AgentCore Memory and Runtime..."
aws cloudformation deploy \
    --template-file infrastructure/cloudformation/autoninja-complete.yaml \
    --stack-name "$STACK_NAME" \
    --parameter-overrides \
        Environment=production \
        BedrockModel=anthropic.claude-sonnet-4-5-20250929-v1:0 \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --profile "$PROFILE"

# Get AgentCore Memory ID
MEMORY_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreMemoryId`].OutputValue' \
    --output text \
    --region "$REGION" \
    --profile "$PROFILE")

echo "Enhanced supervisor deployed successfully!"
echo "AgentCore Memory ID: $MEMORY_ID"

# Test the deployment
echo "Testing enhanced supervisor..."
aws bedrock-agent-runtime invoke-agent \
    --agent-id $(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`SupervisorAgentId`].OutputValue' --output text) \
    --agent-alias-id production \
    --session-id test-$(date +%s) \
    --input-text "Build a simple greeting agent" \
    --region "$REGION" \
    --profile "$PROFILE" \
    output.json

echo "=== Enhanced Supervisor Deployment Complete ==="
echo "Invocation: Use standard Bedrock Agent InvokeAgent API with AgentCore Memory rate limiting"
```

## Data Models

### Rate Limiter Memory Record

```python
@dataclass
class RateLimiterRecord:
    agent_name: str
    last_invocation: datetime
    invocation_count: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def to_memory_content(self) -> str:
        """Convert to AgentCore Memory content format"""
        content = {
            'last_invocation': self.last_invocation.isoformat(),
            'invocation_count': self.invocation_count or 1,
            'created_at': (self.created_at or datetime.now()).isoformat()
        }
        return json.dumps(content)
    
    @classmethod
    def from_memory_record(cls, memory_record: Dict[str, Any], agent_name: str) -> 'RateLimiterRecord':
        """Create from AgentCore Memory record"""
        content = json.loads(memory_record['content'])
        return cls(
            agent_name=agent_name,
            last_invocation=datetime.fromisoformat(content['last_invocation']),
            invocation_count=content.get('invocation_count'),
            created_at=datetime.fromisoformat(content['created_at']) if 'created_at' in content else None
        )
```

### AgentCore Response Model

```python
@dataclass
class AgentCoreResponse:
    job_name: str
    status: str  # "deployed", "validation_failed", "error"
    agent_arn: Optional[str] = None
    validation_issues: Optional[List[str]] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentCoreResponse':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls(**data)
```

## Error Handling

### Throttling Exception Handling

```python
def handle_throttling_exception(e: Exception, attempt: int, agent_name: str) -> bool:
    """
    Handle throttling exceptions with exponential backoff.
    
    Returns:
        bool: True if should retry, False if max attempts reached
    """
    if "throttlingException" not in str(e):
        return False
    
    if attempt >= MAX_RETRIES:
        return False
    
    # Exponential backoff with jitter
    delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
    
    # Log throttling event
    log_throttling_event(agent_name, attempt, delay)
    
    # Wait before retry
    time.sleep(delay)
    
    return True

def log_throttling_event(agent_name: str, attempt: int, delay: float):
    """Log throttling event to CloudWatch"""
    log_to_cloudwatch(f"THROTTLING: {agent_name} attempt {attempt + 1}, waiting {delay:.2f}s")
    
    # Optional: Send CloudWatch metric
    try:
        cloudwatch = boto3.client('cloudwatch')
        cloudwatch.put_metric_data(
            Namespace='AutoNinja/Throttling',
            MetricData=[
                {
                    'MetricName': 'ThrottlingEvents',
                    'Dimensions': [
                        {
                            'Name': 'AgentName',
                            'Value': agent_name
                        }
                    ],
                    'Value': 1,
                    'Unit': 'Count'
                }
            ]
        )
    except Exception as metric_error:
        log_to_cloudwatch(f"Failed to send throttling metric: {str(metric_error)}")
```

## Testing Strategy

### 1. Unit Tests

**File**: `tests/agentcore/test_supervisor.py`

```python
import unittest
from unittest.mock import Mock, patch
from lambda.supervisor_agentcore.supervisor_agent import (
    invoke_collaborator_with_rate_limiting,
    check_and_enforce_rate_limit,
    update_rate_limiter_timestamp
)

class TestAgentCoreSupervisor(unittest.TestCase):
    
    @patch('lambda.supervisor_agentcore.supervisor_agent.dynamodb')
    def test_rate_limiting_enforced(self, mock_dynamodb):
        """Test that rate limiting enforces minimum interval"""
        # Mock recent invocation
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'agent_name': {'S': 'test-agent'},
                'last_invocation': {'S': datetime.now().isoformat()}
            }
        }
        
        wait_time = check_and_enforce_rate_limit('test-agent')
        self.assertGreater(wait_time, 0)
    
    @patch('lambda.supervisor_agentcore.supervisor_agent.bedrock_agent_runtime')
    @patch('lambda.supervisor_agentcore.supervisor_agent.time.sleep')
    def test_throttling_retry_logic(self, mock_sleep, mock_bedrock):
        """Test exponential backoff on throttling"""
        # Mock throttling exception then success
        mock_bedrock.invoke_agent.side_effect = [
            Exception("throttlingException: Rate limit exceeded"),
            {'completion': [{'chunk': {'bytes': b'{"result": "success"}'}}]}
        ]
        
        result = invoke_collaborator_with_rate_limiting(
            "test-agent-id", "test-alias", "test-session", "test-input", "test-agent"
        )
        
        self.assertEqual(result, {"result": "success"})
        mock_sleep.assert_called_once()  # Should have slept for backoff
```

### 2. Integration Tests

**File**: `tests/integration/test_agentcore_integration.py`

```python
import unittest
import boto3
from lambda.supervisor_agentcore.supervisor_agent import invoke

class TestAgentCoreIntegration(unittest.TestCase):
    
    def setUp(self):
        self.dynamodb = boto3.client('dynamodb', region_name='us-east-2')
        self.s3 = boto3.client('s3', region_name='us-east-2')
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from user request to deployed agent"""
        payload = {"prompt": "Build a simple greeting agent"}
        
        result = invoke(payload)
        
        self.assertIn('job_name', result)
        self.assertIn('status', result)
        
        # Verify rate limiter table was used
        job_name = result['job_name']
        # Check DynamoDB for rate limiter entries
        # Check S3 for artifacts
        # Verify no throttling exceptions occurred
    
    def test_throttling_recovery(self):
        """Test system recovers from throttling exceptions"""
        # This would require controlled throttling simulation
        pass
```

### 3. Load Tests

**File**: `tests/load/test_concurrent_requests.py`

```python
import concurrent.futures
import time
from lambda.supervisor_agentcore.supervisor_agent import invoke

def test_concurrent_invocations():
    """Test multiple concurrent invocations don't cause throttling"""
    
    def invoke_agent(request_id):
        payload = {"prompt": f"Build agent {request_id}"}
        return invoke(payload)
    
    # Test 5 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(invoke_agent, i) for i in range(5)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # Verify all succeeded without throttling
    for result in results:
        assert result['status'] != 'error'
        assert 'throttling' not in str(result).lower()
```

## Monitoring and Observability

### CloudWatch Metrics

```python
def send_custom_metrics(job_name: str, agent_name: str, duration: float, success: bool):
    """Send custom metrics to CloudWatch"""
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        metrics = [
            {
                'MetricName': 'AgentInvocationDuration',
                'Dimensions': [
                    {'Name': 'AgentName', 'Value': agent_name},
                    {'Name': 'JobName', 'Value': job_name}
                ],
                'Value': duration,
                'Unit': 'Seconds'
            },
            {
                'MetricName': 'AgentInvocationSuccess',
                'Dimensions': [
                    {'Name': 'AgentName', 'Value': agent_name}
                ],
                'Value': 1 if success else 0,
                'Unit': 'Count'
            }
        ]
        
        cloudwatch.put_metric_data(
            Namespace='AutoNinja/AgentCore',
            MetricData=metrics
        )
    except Exception as e:
        log_to_cloudwatch(f"Failed to send metrics: {str(e)}")
```

### CloudWatch Dashboard

```json
{
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AutoNinja/AgentCore", "AgentInvocationDuration", "AgentName", "requirements-analyst"],
                    [".", ".", ".", "code-generator"],
                    [".", ".", ".", "solution-architect"],
                    [".", ".", ".", "quality-validator"],
                    [".", ".", ".", "deployment-manager"]
                ],
                "period": 300,
                "stat": "Average",
                "region": "us-east-2",
                "title": "Agent Invocation Duration"
            }
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AutoNinja/Throttling", "ThrottlingEvents"]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "us-east-2",
                "title": "Throttling Events"
            }
        }
    ]
}
```

## Security Considerations

### IAM Permissions for AgentCore

The AgentCore runtime will need IAM permissions to:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agent:InvokeAgent",
                "bedrock-agent-runtime:InvokeAgent"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-2:784327326356:agent/*",
                "arn:aws:bedrock:us-east-2:784327326356:agent-alias/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:StoreMemoryRecord",
                "bedrock-agentcore:RetrieveMemoryRecords",
                "bedrock-agentcore:ListMemoryRecords"
            ],
            "Resource": [
                "arn:aws:bedrock-agentcore:us-east-2:784327326356:memory/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-2:784327326356:table/autoninja-inference-records-production"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::autoninja-artifacts-784327326356-production/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:us-east-2:784327326356:log-group:/aws/bedrock-agentcore/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData"
            ],
            "Resource": "*"
        }
    ]
}
```

## Deployment Strategy

### Phase 1: Preparation
1. Update CloudFormation template to remove supervisor agent
2. Add rate limiter DynamoDB table
3. Deploy updated CloudFormation stack

### Phase 2: AgentCore Enhancement Implementation
1. Enhance existing supervisor with AgentCore Memory integration
2. Update CloudFormation template with AgentCore resources
3. Test locally with AgentCore Memory

### Phase 3: Integration
1. Deploy enhanced CloudFormation stack with AgentCore resources
2. Configure AgentCore Memory ID in supervisor Lambda
3. Test end-to-end workflow with Memory-based rate limiting

### Phase 4: Validation
1. Run comprehensive tests
2. Verify no throttling exceptions
3. Validate hackathon requirements met
4. Prepare demo and documentation

This design provides a comprehensive solution for implementing AgentCore while resolving throttling issues, meeting hackathon requirements with minimal risk to the existing system.