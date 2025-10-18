# AutoNinja Supervisor Agent (AgentCore Runtime)

This directory contains the supervisor agent implementation for the AutoNinja system, deployed to Amazon Bedrock AgentCore Runtime.

## Overview

The supervisor agent orchestrates 5 collaborator Bedrock Agents in a sequential workflow:

1. **Requirements Analyst** - Extracts structured requirements
2. **Code Generator** - Generates Lambda code, agent configs, OpenAPI schemas
3. **Solution Architect** - Designs AWS architecture and IaC templates
4. **Quality Validator** - Validates code quality, security, compliance
5. **Deployment Manager** - Deploys agent to AWS (if validation passes)

## Architecture

- **Supervisor**: Deployed to AgentCore Runtime (this agent)
- **Collaborators**: 5 Regular Bedrock Agents with Lambda action groups
- **Orchestration**: Sequential logical workflow with validation gate
- **Communication**: Supervisor invokes collaborators via `InvokeAgent` API

## Files

- `supervisor_agent.py` - Main supervisor agent implementation
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Prerequisites

1. **AWS Account** with credentials configured
2. **Python 3.10+** installed
3. **AgentCore CLI** installed: `pip install bedrock-agentcore-starter-toolkit`
4. **Collaborator Agents** deployed (via CloudFormation)
5. **Environment Variables** set (see Configuration section)

## Configuration

### Environment Variables

The supervisor requires the following environment variables (set automatically by AgentCore deployment):

```bash
# Collaborator Agent IDs (from CloudFormation outputs)
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

# AWS Resources
DYNAMODB_TABLE_NAME=autoninja-inference-records-production
S3_BUCKET_NAME=autoninja-artifacts-{account-id}-production
AWS_ACCOUNT_ID=123456789012

# Configuration
AWS_REGION=us-east-2
LOG_LEVEL=INFO

# Local Testing
MOCK_MODE=false  # Set to 'true' for local testing with mock collaborators
```

### AgentCore Configuration

The AgentCore configuration is stored in `.bedrock_agentcore.yaml` (created by `agentcore configure`):

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
```

## Local Testing

### 1. Install Dependencies

```bash
cd lambda/supervisor-agentcore
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Mock Mode

```bash
export MOCK_MODE=true
```

### 3. Start Supervisor Locally

```bash
python supervisor_agent.py
```

### 4. Test with curl

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "I would like a friend agent"}'
```

Expected response (mock mode):
```json
{
  "job_name": "job-friend-20250115-143022",
  "status": "deployed",
  "agent_arn": "arn:aws:bedrock:us-east-2:123456789012:agent/mock-agent-job-friend-20250115-143022",
  "message": "Agent successfully generated and deployed!",
  "results": {...}
}
```

## Deployment to AgentCore Runtime

### 1. Configure Deployment

```bash
cd lambda/supervisor-agentcore
agentcore configure -e supervisor_agent.py -r us-east-2
```

This creates `.bedrock_agentcore.yaml` with deployment configuration.

### 2. Set Environment Variables

Before deploying, you need to get the collaborator agent IDs from CloudFormation:

```bash
# Get CloudFormation stack outputs
aws cloudformation describe-stacks \
  --stack-name autoninja-system \
  --query 'Stacks[0].Outputs' \
  --region us-east-2

# Set environment variables in .bedrock_agentcore.yaml or via agentcore CLI
```

### 3. Deploy to AgentCore Runtime

```bash
agentcore launch
```

This command:
- Builds container using AWS CodeBuild
- Creates ECR repository and IAM roles
- Deploys to AgentCore Runtime
- Configures CloudWatch logging

Note the **Agent Runtime ARN** from the output - you'll need it to invoke the supervisor.

### 4. Test Deployed Supervisor

```bash
agentcore invoke '{"prompt": "I would like a friend agent"}'
```

## Invocation

### Using AgentCore CLI

```bash
agentcore invoke '{"prompt": "Create a customer support agent"}'
```

### Using boto3 (Python)

```python
import boto3
import json
import uuid

# Initialize client
client = boto3.client('bedrock-agentcore', region_name='us-east-2')

# Prepare payload
payload = json.dumps({"prompt": "I would like a friend agent"}).encode()

# Invoke supervisor
response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-2:123456789012:agent-runtime/abc123',
    runtimeSessionId=str(uuid.uuid4()),
    payload=payload,
    qualifier="DEFAULT"
)

# Parse response
content = []
for chunk in response.get("response", []):
    content.append(chunk.decode('utf-8'))
    
result = json.loads(''.join(content))
print(json.dumps(result, indent=2))
```

### Using AWS CLI

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-2:123456789012:agent-runtime/abc123 \
  --runtime-session-id $(uuidgen) \
  --payload '{"prompt": "I would like a friend agent"}' \
  --qualifier DEFAULT \
  --region us-east-2
```

## Monitoring

### CloudWatch Logs

View supervisor logs:

```bash
aws logs tail /aws/bedrock/agentcore/autoninja-supervisor-production --follow
```

### AgentCore Observability

Enable CloudWatch Transaction Search for detailed tracing:

1. Go to AWS Console → CloudWatch → Transaction Search
2. Enable for AgentCore Runtime
3. View traces with agent reasoning steps, tool invocations, and model interactions

## Workflow

The supervisor implements this sequential workflow:

```
User Request
     ↓
Generate job_name
     ↓
Requirements Analyst → requirements.json
     ↓
Code Generator → lambda_code, agent_config, openapi_schemas
     ↓
Solution Architect → architecture, iac_templates
     ↓
Quality Validator → validation_report, is_valid
     ↓
[GATE: is_valid == True?]
     ↓ YES                    ↓ NO
Deployment Manager      Return validation
     ↓                   failures to user
Return agent ARN
```

## Error Handling

The supervisor implements:

- **Retry Logic**: 3 attempts per collaborator with exponential backoff
- **Validation Gate**: Blocks deployment if quality validation fails
- **Error Logging**: All errors logged to CloudWatch
- **Graceful Degradation**: Returns partial results on failure

## Troubleshooting

### Issue: "Missing configuration for {agent}"

**Solution**: Set environment variables for collaborator agent IDs:

```bash
export REQUIREMENTS_ANALYST_AGENT_ID=AGENT123
export REQUIREMENTS_ANALYST_ALIAS_ID=ALIAS123
# ... etc
```

### Issue: "Failed to invoke {agent} after 3 attempts"

**Possible causes**:
1. Collaborator agent not deployed
2. IAM permissions insufficient
3. Network/throttling issues

**Solution**: Check CloudWatch logs for detailed error messages.

### Issue: Port 8080 in use (local testing)

**Solution**: Kill process using port 8080:

```bash
# Find process
lsof -i :8080

# Kill process
kill -9 <PID>
```

## IAM Permissions

The supervisor requires these IAM permissions (configured in CloudFormation):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock-agent-runtime:InvokeAgent"
      ],
      "Resource": "arn:aws:bedrock:us-east-2:*:agent/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-2:*:table/autoninja-inference-records-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::autoninja-artifacts-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-2:*:log-group:/aws/bedrock/agentcore/*"
    }
  ]
}
```

## Next Steps

1. Deploy collaborator agents via CloudFormation
2. Get agent IDs from CloudFormation outputs
3. Configure supervisor with agent IDs
4. Deploy supervisor to AgentCore Runtime
5. Test end-to-end workflow
6. Configure custom orchestration for collaborators (rate limiting)

## Resources

- [AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- [AgentCore Starter Toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-toolkit.html)
- [Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)
- [InvokeAgentRuntime API](https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_InvokeAgentRuntime.html)
