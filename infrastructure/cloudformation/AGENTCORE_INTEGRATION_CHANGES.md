# AgentCore Integration Changes to CloudFormation Template

## Summary

This document describes the changes made to `infrastructure/cloudformation/autoninja-complete.yaml` to integrate the AgentCore Runtime supervisor agent (deployed separately via `agentcore` CLI) with the 5 collaborator Bedrock Agents.

## Changes Made

### 1. Added New Parameter

**Parameter:** `SupervisorAgentCoreRuntimeArn`
- **Type:** String
- **Description:** ARN of the deployed AgentCore Runtime supervisor agent
- **Default:** Empty string (optional)
- **Pattern:** `^$|^arn:aws:bedrock-agentcore:[a-z0-9-]+:[0-9]{12}:runtime/[a-zA-Z0-9_-]+$`
- **Purpose:** Allows users to specify the AgentCore Runtime ARN after deploying the supervisor separately

### 2. Added New Condition

**Condition:** `HasSupervisorAgentCoreArn`
- **Logic:** `!Not [!Equals [!Ref SupervisorAgentCoreRuntimeArn, ""]]`
- **Purpose:** Checks if the AgentCore Runtime ARN parameter is provided

### 3. Removed Resources

The following resources were **REMOVED** because the supervisor is now deployed to AgentCore Runtime:

1. **SupervisorAgentRole** (IAM Role)
   - Previously: IAM execution role for Bedrock supervisor agent
   - Now: Managed automatically by `agentcore` CLI with name `AmazonBedrockAgentCoreSDKRuntime-{region}-{random-id}`

2. **SupervisorAgent** (AWS::Bedrock::Agent)
   - Previously: Bedrock Agent resource for supervisor
   - Now: Deployed separately to AgentCore Runtime using `agentcore launch`

3. **SupervisorAgentAlias** (AWS::Bedrock::AgentAlias)
   - Previously: Production alias for supervisor Bedrock Agent
   - Now: Not needed - AgentCore Runtime uses qualifiers (DEFAULT)

4. **SupervisorAgentLogGroup** (AWS::Logs::LogGroup)
   - Previously: CloudWatch log group for supervisor agent
   - Now: Managed automatically by AgentCore Runtime at `/aws/bedrock-agentcore/runtimes/{agent-name}-{id}-{qualifier}`

### 4. Updated Outputs

**Removed Outputs:**
- `SupervisorAgentId`
- `SupervisorAgentArn`
- `SupervisorAgentAliasId`
- `SupervisorAgentAliasArn`
- `SupervisorAgentConsoleUrl`
- `InvocationCommand`

**Added Outputs:**

1. **SupervisorAgentCoreRuntimeArn**
   - **Description:** ARN of the AgentCore Runtime supervisor agent
   - **Value:** Returns the parameter value if provided, otherwise shows deployment instructions
   - **Export:** `${AWS::StackName}-SupervisorAgentCoreRuntimeArn`

2. **SupervisorInvocationCommand**
   - **Description:** Command to invoke the AgentCore Runtime supervisor
   - **Value:** Shows `agentcore invoke` command or AWS SDK example if ARN is provided
   - **Purpose:** Provides users with the correct invocation method

3. **SupervisorAgentCoreConsoleUrl**
   - **Description:** AWS Console URL for AgentCore Runtime observability
   - **Value:** Links to GenAI Observability dashboard for AgentCore

### 5. Added Documentation Comment

Added a comprehensive comment in the IAM section explaining:
- The AgentCore execution role is created automatically by `agentcore` CLI
- Required permissions for the AgentCore role to invoke collaborators
- How to find and update the AgentCore execution role after deployment

### 6. Preserved Resources

The following resources remain **UNCHANGED** and are still managed by CloudFormation:

**Collaborator Agents (5):**
1. RequirementsAnalystAgent
2. CodeGeneratorAgent
3. SolutionArchitectAgent
4. QualityValidatorAgent
5. DeploymentManagerAgent

**Collaborator Agent Aliases (5):**
1. RequirementsAnalystAgentAlias
2. CodeGeneratorAgentAlias
3. SolutionArchitectAgentAlias
4. QualityValidatorAgentAlias
5. DeploymentManagerAgentAlias

**Supporting Resources:**
- All Lambda functions (5)
- All IAM roles for Lambda functions (5)
- All IAM roles for Bedrock collaborator agents (5)
- DynamoDB table
- S3 bucket
- Lambda Layer
- CloudWatch log groups for collaborators
- Custom orchestration Lambda

## Deployment Workflow

### Step 1: Deploy CloudFormation Stack (Collaborators Only)

```bash
aws cloudformation create-stack \
  --stack-name autoninja-system \
  --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
  --parameters ParameterKey=Environment,ParameterValue=production \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-2
```

This creates:
- 5 collaborator Bedrock Agents
- 5 Lambda functions
- DynamoDB table
- S3 bucket
- All supporting infrastructure

### Step 2: Deploy Supervisor to AgentCore Runtime

```bash
cd lambda/supervisor-agentcore
agentcore configure -e supervisor_agent.py -r us-east-2 -n autoninja_supervisor -ni
agentcore launch
```

This creates:
- AgentCore Runtime supervisor agent
- Container image in ECR
- IAM execution role (AmazonBedrockAgentCoreSDKRuntime-*)
- CloudWatch log group
- Memory resource

### Step 3: Get AgentCore Runtime ARN

```bash
agentcore status
```

Output will show:
```
Agent ARN: arn:aws:bedrock-agentcore:us-east-2:123456789012:runtime/autoninja_supervisor-xxxxx
```

### Step 4: Update CloudFormation Stack with AgentCore ARN (Optional)

```bash
aws cloudformation update-stack \
  --stack-name autoninja-system \
  --use-previous-template \
  --parameters \
    ParameterKey=Environment,UsePreviousValue=true \
    ParameterKey=BedrockModel,UsePreviousValue=true \
    ParameterKey=DynamoDBBillingMode,UsePreviousValue=true \
    ParameterKey=S3BucketName,UsePreviousValue=true \
    ParameterKey=LogRetentionDays,UsePreviousValue=true \
    ParameterKey=SupervisorAgentCoreRuntimeArn,ParameterValue=arn:aws:bedrock-agentcore:us-east-2:123456789012:runtime/autoninja_supervisor-xxxxx \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-2
```

This updates the stack outputs to show the correct invocation commands.

### Step 5: Grant AgentCore Role Permissions to Invoke Collaborators

The AgentCore execution role needs permissions to invoke the 5 collaborator agents. You can either:

**Option A: Attach AWS Managed Policy (Quick)**
```bash
AGENTCORE_ROLE=$(aws iam list-roles --query "Roles[?contains(RoleName, 'AmazonBedrockAgentCoreSDKRuntime')].RoleName" --output text)

aws iam attach-role-policy \
  --role-name $AGENTCORE_ROLE \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

**Option B: Create Custom Policy (Least Privilege)**
```bash
# Get collaborator agent ARNs from CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name autoninja-system \
  --query 'Stacks[0].Outputs'

# Create custom policy with specific agent ARNs
# (See lambda/supervisor-agentcore/README.md for policy template)
```

### Step 6: Test End-to-End

```bash
agentcore invoke '{"prompt": "I would like a friend agent"}'
```

## IAM Permissions Required

### AgentCore Execution Role Permissions

The AgentCore execution role (created by `agentcore` CLI) needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeCollaboratorAgents",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock-agent-runtime:InvokeAgent"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-2:123456789012:agent/*",
        "arn:aws:bedrock:us-east-2:123456789012:agent-alias/*"
      ]
    },
    {
      "Sid": "DynamoDBLogging",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-2:123456789012:table/autoninja-inference-records-*"
    },
    {
      "Sid": "S3Artifacts",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::autoninja-artifacts-*/*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-2:123456789012:log-group:/aws/bedrock-agentcore/*"
    }
  ]
}
```

## Validation

### Template Validation

```bash
cfn-lint infrastructure/cloudformation/autoninja-complete.yaml
```

**Result:** ✅ No errors (only minor warnings about action names and optimization suggestions)

### Resource Verification

**Collaborator Agents:** ✅ All 5 agents still defined
- RequirementsAnalystAgent
- CodeGeneratorAgent
- SolutionArchitectAgent
- QualityValidatorAgent
- DeploymentManagerAgent

**Collaborator Agent Aliases:** ✅ All 5 aliases still defined
- RequirementsAnalystAgentAlias
- CodeGeneratorAgentAlias
- SolutionArchitectAgentAlias
- QualityValidatorAgentAlias
- DeploymentManagerAgentAlias

**Supervisor Resources:** ✅ All removed (now managed by AgentCore)
- SupervisorAgentRole ❌ (removed)
- SupervisorAgent ❌ (removed)
- SupervisorAgentAlias ❌ (removed)
- SupervisorAgentLogGroup ❌ (removed)

## Benefits of AgentCore Integration

1. **Extended Execution Time:** Up to 8 hours (vs 30 minutes for Bedrock Agents)
2. **Framework Flexibility:** Can use LangGraph, Strands, or custom orchestration logic
3. **Better Session Isolation:** Each invocation runs in isolated microVM
4. **Built-in Observability:** X-Ray tracing, CloudWatch metrics, GenAI dashboard
5. **Consumption-Based Pricing:** Pay only for actual execution time
6. **Container-Based Deployment:** Full control over dependencies and runtime environment

## Migration Notes

### Breaking Changes

1. **Invocation Method Changed:**
   - **Before:** `aws bedrock-agent-runtime invoke-agent --agent-id ... --agent-alias-id ...`
   - **After:** `agentcore invoke '{"prompt": "..."}'` or use `bedrock-agentcore` SDK

2. **ARN Format Changed:**
   - **Before:** `arn:aws:bedrock:region:account:agent/agent-id`
   - **After:** `arn:aws:bedrock-agentcore:region:account:runtime/agent-name-id`

3. **IAM Role Management:**
   - **Before:** Managed by CloudFormation
   - **After:** Managed by `agentcore` CLI (must update permissions manually)

### Non-Breaking Changes

- All collaborator agents remain unchanged
- DynamoDB and S3 persistence unchanged
- Lambda functions unchanged
- CloudWatch logging for collaborators unchanged

## Troubleshooting

### Issue: AgentCore supervisor can't invoke collaborators

**Symptom:** Error "Access Denied" when supervisor tries to invoke collaborator agents

**Solution:** Grant AgentCore execution role permissions to invoke agents (see Step 5 above)

### Issue: CloudFormation outputs show "NOT_DEPLOYED"

**Symptom:** `SupervisorAgentCoreRuntimeArn` output shows "NOT_DEPLOYED - Deploy supervisor using: agentcore launch"

**Solution:** Either:
1. Deploy supervisor using `agentcore launch` (Step 2)
2. Update stack with `SupervisorAgentCoreRuntimeArn` parameter (Step 4)

### Issue: Can't find AgentCore execution role

**Symptom:** Need to update IAM permissions but can't find the role

**Solution:**
```bash
aws iam list-roles --query "Roles[?contains(RoleName, 'AmazonBedrockAgentCoreSDKRuntime')].{Name:RoleName,Arn:Arn}"
```

## References

- [AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- [AgentCore Starter Toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-toolkit.html)
- [Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)
- [Supervisor Agent Implementation](lambda/supervisor-agentcore/README.md)
- [Deployment Info](lambda/supervisor-agentcore/DEPLOYMENT_INFO.md)

## Completion Checklist

- [x] Removed SupervisorAgentRole from CloudFormation
- [x] Removed SupervisorAgent from CloudFormation
- [x] Removed SupervisorAgentAlias from CloudFormation
- [x] Removed SupervisorAgentLogGroup from CloudFormation
- [x] Added SupervisorAgentCoreRuntimeArn parameter
- [x] Added HasSupervisorAgentCoreArn condition
- [x] Updated outputs to reference AgentCore Runtime
- [x] Added documentation comment about IAM permissions
- [x] Verified all 5 collaborator agents still defined
- [x] Verified all 5 collaborator agent aliases still defined
- [x] Validated template with cfn-lint (no errors)
- [x] Documented deployment workflow
- [x] Documented IAM permissions required
- [x] Documented troubleshooting steps
