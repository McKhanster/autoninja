# AutoNinja Multi-Agent: Final Implementation Plan

## AWS Native Multi-Agent Collaboration + AgentCore Integration

### Architecture

- **Supervisor Agent**: Bedrock Agent with `AgentCollaboration: SUPERVISOR`
- **5 Collaborator Agents**: Existing Bedrock Agents with Lambda action groups
- **AgentCore Integration**: AgentCore Memory for cross-job learning + observability
- **Rate Limiting**: DynamoDB-backed in Lambda action groups (30-second spacing)

**Hackathon Compliance:**
✅ Uses Bedrock Agents (supervisor + 5 collaborators)
✅ Uses AgentCore (Memory for persistent learning)
✅ Produces agents from natural language

---

## Implementation Steps (AWS Native Multi-Agent)

### Step 0: Refactor CloudFormation to Nested Stacks (2 hours)

**Problem**: Current `autoninja-complete.yaml` is 1595 lines - hard to read and maintain.

**Solution**: Break into modular nested stacks.

**New Structure:**

```
infrastructure/cloudformation/
├── autoninja-main.yaml              # Main orchestration stack (~200 lines)
├── stacks/
│   ├── storage.yaml                 # DynamoDB + S3 + Rate Limiter Table (~200 lines)
│   ├── lambda-layer.yaml            # Shared Lambda Layer (~100 lines)
│   ├── requirements-analyst.yaml    # Agent + Lambda + IAM (~250 lines)
│   ├── code-generator.yaml          # Agent + Lambda + IAM (~250 lines)
│   ├── solution-architect.yaml      # Agent + Lambda + IAM (~250 lines)
│   ├── quality-validator.yaml       # Agent + Lambda + IAM (~250 lines)
│   ├── deployment-manager.yaml      # Agent + Lambda + IAM (~250 lines)
│   ├── supervisor.yaml              # Supervisor Agent + IAM (~200 lines)
│   └── custom-orchestration.yaml    # Custom orchestration Lambda (~150 lines)
```

**Main Stack Template:**

```yaml
# infrastructure/cloudformation/autoninja-main.yaml

AWSTemplateFormatVersion: "2010-09-09"
Description: AutoNinja Multi-Agent System - Main Stack

Parameters:
  Environment:
    Type: String
    Default: production
  BedrockModel:
    Type: String
    Default: us.anthropic.claude-sonnet-4-5-20250929-v1:0
  DeploymentBucket:
    Type: String
    Default: autoninja-deployment-artifacts-us-east-2

Resources:
  # Storage Layer (DynamoDB + S3 + Rate Limiter)
  StorageStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/storage.yaml"
      Parameters:
        Environment: !Ref Environment

  # Lambda Layer
  LambdaLayerStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/lambda-layer.yaml"
      Parameters:
        Environment: !Ref Environment
        DeploymentBucket: !Ref DeploymentBucket

  # Requirements Analyst
  RequirementsAnalystStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/requirements-analyst.yaml"
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !Ref DeploymentBucket
        DynamoDBTable: !GetAtt StorageStack.Outputs.InferenceRecordsTable
        S3Bucket: !GetAtt StorageStack.Outputs.ArtifactsBucket
        RateLimiterTable: !GetAtt StorageStack.Outputs.RateLimiterTable
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn

  # Code Generator
  CodeGeneratorStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/code-generator.yaml"
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !Ref DeploymentBucket
        DynamoDBTable: !GetAtt StorageStack.Outputs.InferenceRecordsTable
        S3Bucket: !GetAtt StorageStack.Outputs.ArtifactsBucket
        RateLimiterTable: !GetAtt StorageStack.Outputs.RateLimiterTable
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn

  # Solution Architect
  SolutionArchitectStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/solution-architect.yaml"
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !Ref DeploymentBucket
        DynamoDBTable: !GetAtt StorageStack.Outputs.InferenceRecordsTable
        S3Bucket: !GetAtt StorageStack.Outputs.ArtifactsBucket
        RateLimiterTable: !GetAtt StorageStack.Outputs.RateLimiterTable
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn

  # Quality Validator
  QualityValidatorStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/quality-validator.yaml"
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !Ref DeploymentBucket
        DynamoDBTable: !GetAtt StorageStack.Outputs.InferenceRecordsTable
        S3Bucket: !GetAtt StorageStack.Outputs.ArtifactsBucket
        RateLimiterTable: !GetAtt StorageStack.Outputs.RateLimiterTable
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn

  # Deployment Manager
  DeploymentManagerStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/deployment-manager.yaml"
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !Ref DeploymentBucket
        DynamoDBTable: !GetAtt StorageStack.Outputs.InferenceRecordsTable
        S3Bucket: !GetAtt StorageStack.Outputs.ArtifactsBucket
        RateLimiterTable: !GetAtt StorageStack.Outputs.RateLimiterTable
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn

  # Custom Orchestration (Optional)
  CustomOrchestrationStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/custom-orchestration.yaml"
      Parameters:
        Environment: !Ref Environment
        DeploymentBucket: !Ref DeploymentBucket

  # Supervisor Agent
  SupervisorStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - RequirementsAnalystStack
      - CodeGeneratorStack
      - SolutionArchitectStack
      - QualityValidatorStack
      - DeploymentManagerStack
    Properties:
      TemplateURL: !Sub "https://${DeploymentBucket}.s3.${AWS::Region}.amazonaws.com/stacks/supervisor.yaml"
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        RequirementsAnalystAgentArn: !GetAtt RequirementsAnalystStack.Outputs.AgentArn
        CodeGeneratorAgentArn: !GetAtt CodeGeneratorStack.Outputs.AgentArn
        SolutionArchitectAgentArn: !GetAtt SolutionArchitectStack.Outputs.AgentArn
        QualityValidatorAgentArn: !GetAtt QualityValidatorStack.Outputs.AgentArn
        DeploymentManagerAgentArn: !GetAtt DeploymentManagerStack.Outputs.AgentArn

Outputs:
  SupervisorAgentId:
    Description: Supervisor Agent ID
    Value: !GetAtt SupervisorStack.Outputs.AgentId
    Export:
      Name: !Sub "${AWS::StackName}-SupervisorAgentId"

  SupervisorAgentAliasId:
    Description: Supervisor Agent Alias ID
    Value: !GetAtt SupervisorStack.Outputs.AgentAliasId
    Export:
      Name: !Sub "${AWS::StackName}-SupervisorAgentAliasId"

  RequirementsAnalystAgentId:
    Value: !GetAtt RequirementsAnalystStack.Outputs.AgentId

  CodeGeneratorAgentId:
    Value: !GetAtt CodeGeneratorStack.Outputs.AgentId

  SolutionArchitectAgentId:
    Value: !GetAtt SolutionArchitectStack.Outputs.AgentId

  QualityValidatorAgentId:
    Value: !GetAtt QualityValidatorStack.Outputs.AgentId

  DeploymentManagerAgentId:
    Value: !GetAtt DeploymentManagerStack.Outputs.AgentId

  ArtifactsBucket:
    Value: !GetAtt StorageStack.Outputs.ArtifactsBucket

  InferenceRecordsTable:
    Value: !GetAtt StorageStack.Outputs.InferenceRecordsTable

  RateLimiterTable:
    Value: !GetAtt StorageStack.Outputs.RateLimiterTable
```

**Benefits:**

- ✅ Each stack is <300 lines - easy to read and edit
- ✅ Modular - can deploy/update individual agents
- ✅ Maintainable - clear separation of concerns
- ✅ Still one-click deploy via main stack
- ✅ CloudFormation updates nested stacks in parallel

**Updated Deployment Script:**

```bash
# scripts/deploy_all.sh - Add before CloudFormation deploy

# Upload nested stack templates
echo -e "${YELLOW}Step 6a: Uploading nested CloudFormation templates...${NC}"
for template in infrastructure/cloudformation/stacks/*.yaml; do
    filename=$(basename "$template")
    aws s3 cp "$template" \
        "s3://${S3_BUCKET}/stacks/$filename" \
        --sse aws:kms \
        --region "$REGION" \
        --profile "$PROFILE" \
        --quiet
    echo -e "    ${GREEN}✓${NC} $filename"
done

# Deploy main stack (references nested templates from S3)
echo -e "${YELLOW}Step 7: Deploying CloudFormation stack (nested)...${NC}"
aws cloudformation deploy \
    --template-file infrastructure/cloudformation/autoninja-main.yaml \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        DeploymentBucket="$S3_BUCKET" \
    --region "$REGION" \
    --profile "$PROFILE"
```

---

### Step 1: Collaborator Agents (ALREADY DONE ✓)

You already have 5 collaborator agents:

- Requirements Analyst
- Code Generator
- Solution Architect
- Quality Validator
- Deployment Manager

**After refactoring**: Each agent will have its own stack file, but logic remains unchanged.

---

### Step 2: Add Rate Limiting to Collaborators (1 hour)

**2.1 Add DynamoDB Table to CloudFormation**

```yaml
# infrastructure/cloudformation/autoninja-complete.yaml

RateLimiterStateTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: !Sub "autoninja-rate-limiter-${Environment}"
    AttributeDefinitions:
      - AttributeName: job_name
        AttributeType: S
      - AttributeName: timestamp
        AttributeType: S
    KeySchema:
      - AttributeName: job_name
        KeyType: HASH
      - AttributeName: timestamp
        KeyType: RANGE
    BillingMode: PAY_PER_REQUEST
    TimeToLiveSpecification:
      AttributeName: ttl
      Enabled: true
```

**2.2 Create Rate Limiter Library**

```python
# shared/utils/rate_limiter.py

import boto3
import time
import os
from datetime import datetime, timedelta

class DistributedRateLimiter:
    def __init__(self, min_interval_seconds=30):
        self.dynamodb = boto3.client('dynamodb')
        self.table_name = os.environ.get('RATE_LIMITER_TABLE', 'autoninja-rate-limiter-production')
        self.min_interval = min_interval_seconds

    def enforce_rate_limit(self, job_name: str, agent_name: str):
        """Enforce 30-second spacing between model invocations"""
        while True:
            current_time = datetime.utcnow()

            # Get last invocation for this job
            response = self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='job_name = :job',
                ExpressionAttributeValues={':job': {'S': job_name}},
                ScanIndexForward=False,
                Limit=1
            )

            if response['Items']:
                last_timestamp = datetime.fromisoformat(response['Items'][0]['timestamp']['S'])
                elapsed = (current_time - last_timestamp).total_seconds()

                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    print(f"[RATE LIMIT] {agent_name} waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                    continue

            # Record this invocation
            ttl = int((current_time + timedelta(hours=24)).timestamp())
            self.dynamodb.put_item(
                TableName=self.table_name,
                Item={
                    'job_name': {'S': job_name},
                    'timestamp': {'S': current_time.isoformat()},
                    'agent_name': {'S': agent_name},
                    'ttl': {'N': str(ttl)}
                }
            )
            return
```

**2.3 Update Lambda Handlers**

Add to each `lambda/*/handler.py` after parameter extraction:

```python
from shared.utils.rate_limiter import DistributedRateLimiter

def lambda_handler(event, context):
    # ... existing parameter extraction ...

    job_name = params.get('job_name')

    # ENFORCE RATE LIMIT
    rate_limiter = DistributedRateLimiter()
    rate_limiter.enforce_rate_limit(job_name, 'agent-name')

    # ... rest of handler ...
```

**2.4 Update IAM Roles**

Add to all 5 Lambda roles:

```yaml
- PolicyName: RateLimiterAccess
  PolicyDocument:
    Statement:
      - Effect: Allow
        Action:
          - dynamodb:PutItem
          - dynamodb:Query
        Resource: !GetAtt RateLimiterStateTable.Arn
```

---

### Step 3: Create Supervisor Agent (30 min)

**3.1 Add to CloudFormation**

```yaml
# infrastructure/cloudformation/autoninja-complete.yaml

SupervisorAgentRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub "AutoNinjaSupervisorAgentRole-${Environment}"
    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Service: bedrock.amazonaws.com
          Action: sts:AssumeRole
    Policies:
      - PolicyName: InvokeModel
        PolicyDocument:
          Statement:
            - Effect: Allow
              Action: bedrock:InvokeModel
              Resource: !Sub "arn:aws:bedrock:${AWS::Region}::foundation-model/${BedrockModel}"
      - PolicyName: InvokeCollaborators
        PolicyDocument:
          Statement:
            - Effect: Allow
              Action: bedrock:InvokeAgent
              Resource:
                - !GetAtt RequirementsAnalystAgent.AgentArn
                - !GetAtt CodeGeneratorAgent.AgentArn
                - !GetAtt SolutionArchitectAgent.AgentArn
                - !GetAtt QualityValidatorAgent.AgentArn
                - !GetAtt DeploymentManagerAgent.AgentArn

SupervisorAgent:
  Type: AWS::Bedrock::Agent
  DependsOn:
    - RequirementsAnalystAgent
    - CodeGeneratorAgent
    - SolutionArchitectAgent
    - QualityValidatorAgent
    - DeploymentManagerAgent
  Properties:
    AgentName: !Sub "autoninja-supervisor-${Environment}"
    AgentResourceRoleArn: !GetAtt SupervisorAgentRole.Arn
    FoundationModel: !Ref BedrockModel
    AgentCollaboration: SUPERVISOR
    IdleSessionTTLInSeconds: 3600
    AutoPrepare: true
    Instruction: |
      You are the AutoNinja supervisor. Orchestrate 5 collaborator agents to generate a Bedrock Agent from natural language.

      WORKFLOW:
      1. Extract job_name from user request (format: job-{keyword}-{YYYYMMDD-HHMMSS})
      2. Route to Requirements Analyst: Pass job_name + user_request
      3. Route to Code Generator: Pass job_name + requirements
      4. Route to Solution Architect: Pass job_name + requirements + code
      5. Route to Quality Validator: Pass job_name + all artifacts
      6. VALIDATION GATE: If is_valid == false, STOP and return failures
      7. If valid, route to Deployment Manager: Pass job_name + all artifacts
      8. Return deployed agent ARN

      RULES:
      - ALWAYS include job_name in every collaborator invocation
      - NEVER invoke collaborators in parallel
      - Only invoke Deployment Manager if validation passes

SupervisorAgentAlias:
  Type: AWS::Bedrock::AgentAlias
  Properties:
    AgentId: !GetAtt SupervisorAgent.AgentId
    AgentAliasName: production
```

---

### Step 4: Associate Collaborators (30 min)

**Update `scripts/deploy_all.sh`** - Add after CloudFormation deployment:

```bash
# Step 8: Associate Collaborators with Supervisor
echo -e "${YELLOW}Step 8: Associating collaborators with supervisor...${NC}"

SUPERVISOR_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`SupervisorAgentId`].OutputValue' \
    --output text)

# Get collaborator IDs and aliases from stack outputs
declare -A COLLABORATORS=(
    ["Requirements Analyst"]="REQUIREMENTS_ANALYST"
    ["Code Generator"]="CODE_GENERATOR"
    ["Solution Architect"]="SOLUTION_ARCHITECT"
    ["Quality Validator"]="QUALITY_VALIDATOR"
    ["Deployment Manager"]="DEPLOYMENT_MANAGER"
)

for name in "${!COLLABORATORS[@]}"; do
    key="${COLLABORATORS[$name]}"

    AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey==\`${key}AgentId\`].OutputValue" \
        --output text)

    ALIAS_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey==\`${key}AliasId\`].OutputValue" \
        --output text)

    echo "  Associating $name..."

    aws bedrock-agent associate-agent-collaborator \
        --agent-id "$SUPERVISOR_ID" \
        --agent-version DRAFT \
        --collaborator-name "$name" \
        --agent-descriptor "agentId=$AGENT_ID,agentAliasArn=arn:aws:bedrock:${REGION}:${AWS_ACCOUNT_ID}:agent-alias/${AGENT_ID}/${ALIAS_ID}" \
        --collaboration-instruction "Handle $name tasks. Always include job_name parameter." \
        --relay-conversation-history TO_COLLABORATOR \
        --region "$REGION" \
        --profile "$PROFILE" \
        2>/dev/null || echo "    Already associated"
done

# Prepare supervisor
echo "  Preparing supervisor agent..."
aws bedrock-agent prepare-agent \
    --agent-id "$SUPERVISOR_ID" \
    --region "$REGION" \
    --profile "$PROFILE" > /dev/null 2>&1

echo -e "${GREEN}✓ Collaborators associated and supervisor prepared${NC}"
```

---

### Step 5: AgentCore Integration via Memory (1 hour)

**Add AgentCore Memory for cross-job learning:**

**5.1 Create AgentCore Memory**

```bash
# Create memory for supervisor
agentcore memory create \
  --memory-name autoninja-supervisor-memory \
  --event-expiry-days 30 \
  --region us-east-2
```

**5.2 Attach Memory to Supervisor**

Update supervisor agent configuration to use AgentCore Memory for:

- Storing successful agent patterns
- Learning from validation failures
- Improving code generation over time

**5.3 Update Supervisor to Use Memory**

Add memory retrieval to supervisor instruction:

```yaml
Instruction: |
  You are the AutoNinja supervisor with access to historical job data via AgentCore Memory.

  Before starting each job:
  1. Query memory for similar past jobs
  2. Learn from successful patterns
  3. Avoid past validation failures

  [rest of instruction...]
```

---

### Step 6: One-Click Deployment

**Existing script works!** Just run:

```bash
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356
export AUTO_DEPLOY=true
./scripts/deploy_all.sh
```

This now:

1. Deploys 5 collaborator agents
2. Deploys supervisor agent
3. Associates collaborators
4. Prepares supervisor
5. Sets up rate limiting
6. Configures AgentCore Memory

---

### Step 7: Testing

```bash
# Get supervisor details
SUPERVISOR_ID=$(aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --query 'Stacks[0].Outputs[?OutputKey==`SupervisorAgentId`].OutputValue' \
  --output text)

SUPERVISOR_ALIAS=$(aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --query 'Stacks[0].Outputs[?OutputKey==`SupervisorAgentAliasId`].OutputValue' \
  --output text)

# Invoke supervisor
aws bedrock-agent-runtime invoke-agent \
  --agent-id $SUPERVISOR_ID \
  --agent-alias-id $SUPERVISOR_ALIAS \
  --session-id test-$(date +%s) \
  --input-text "Build a friend agent for emotional support" \
  --enable-trace \
  output.json

# View result
cat output.json | jq '.completion[] | select(.chunk) | .chunk.bytes' -r | base64 -d
```

---

## What You Get

✅ **Native Multi-Agent Collaboration** - AWS handles orchestration
✅ **5 Collaborator Agents** - Existing Lambda-based agents
✅ **1 Supervisor Agent** - Routes to collaborators automatically
✅ **30-Second Rate Limiting** - DynamoDB-enforced spacing
✅ **AgentCore Memory** - Learns from past jobs
✅ **Full Observability** - CloudWatch + Bedrock traces
✅ **One-Click Deploy** - `./scripts/deploy_all.sh`

---

## AgentCore Integration Points

1. **Memory**: Supervisor uses AgentCore Memory for learning
2. **Observability**: AgentCore-enhanced tracing
3. **Future**: Can add AgentCore MCP tools for collaborators

---

## Cost Per Job

- Supervisor: 3 model invocations @ $0.003 = $0.009
- Collaborators: 5 model invocations @ $0.003 = $0.015
- Lambda: 5 executions ≈ $0.000001
- DynamoDB: 10 operations ≈ $0.0000025
- AgentCore Memory: Minimal storage cost
- **Total**: ~$0.025/job

---

## Deployment Time

- CloudFormation: ~10 min
- Collaborator association: ~2 min
- AgentCore Memory setup: ~1 min
- **Total**: ~13 minutes

---

## Validation Checklist

- [ ] Supervisor agent created with `AgentCollaboration: SUPERVISOR`
- [ ] 5 collaborators associated via `AssociateAgentCollaborator`
- [ ] Supervisor prepared (status = PREPARED)
- [ ] Rate limiter table exists
- [ ] Lambda roles have DynamoDB permissions
- [ ] AgentCore Memory created and attached
- [ ] Test invocation returns deployed agent ARN
- [ ] CloudWatch shows rate limiting logs
- [ ] Bedrock traces show collaborator routing

This is the AWS-native approach that satisfies all requirements!
