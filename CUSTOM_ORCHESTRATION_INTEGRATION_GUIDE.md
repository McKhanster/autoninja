# Custom Orchestration Integration Guide

## Overview

This guide explains how to integrate the Custom Orchestration Lambda into the AutoNinja CloudFormation template to fix throttling issues with Bedrock Agents.

## Problem

AWS Bedrock Agents use default orchestration that encourages parallel tool execution, causing throttling errors with Claude Sonnet 4.5's ~1 RPM rate limit.

## Solution

Implement Custom Orchestration Lambda that enforces sequential tool execution with 60-second rate limiting between Converse API calls.

## Files Created

1. **`lambda/custom-orchestration/handler.py`** - Custom orchestration Lambda function (DONE ✓)
2. **`infrastructure/cloudformation/custom-orchestration-resources.yaml`** - Resource definitions to add to CloudFormation (DONE ✓)

## CloudFormation Changes Required

### Step 1: Add Custom Orchestration Resources

Insert the following resources into `infrastructure/cloudformation/autoninja-complete.yaml`:

**Location**: After line 660 (after DeploymentManagerFunction), before line 662 (before Lambda Permissions section)

**Resources to Add**:
1. `CustomOrchestrationLambdaRole` - IAM role with Bedrock Converse permissions
2. `CustomOrchestrationFunction` - Lambda function
3. `CustomOrchestrationInvokePermission` - Permission for Bedrock to invoke Lambda
4. `CustomOrchestrationLogGroup` - CloudWatch log group

See `infrastructure/cloudformation/custom-orchestration-resources.yaml` for the complete resource definitions.

### Step 2: Update ALL 5 Sub-Agent Definitions

For EACH of the following agents, add custom orchestration configuration:

1. **RequirementsAnalystAgent** (line ~1036)
2. **CodeGeneratorAgent** (line ~1079)
3. **SolutionArchitectAgent** (line ~1120)
4. **QualityValidatorAgent** (line ~1163)
5. **DeploymentManagerAgent** (line ~1205)

**DO NOT modify SupervisorAgent** - it will be implemented later.

#### Changes for Each Agent:

1. **Add to DependsOn section**:
```yaml
DependsOn:
  - <AgentName>Function
  - <AgentName>AgentRole
  - DeploymentArtifactsBucketPolicy
  - CustomOrchestrationFunction  # ← ADD THIS LINE
```

2. **Add after `AutoPrepare: true`**, before `Instruction:``:
```yaml
AutoPrepare: true
OrchestrationType: CUSTOM_ORCHESTRATION  # ← ADD THIS LINE
CustomOrchestrationConfiguration:         # ← ADD THIS BLOCK
  Executor:
    Lambda: !GetAtt CustomOrchestrationFunction.Arn
Instruction: |
```

### Example: Requirements Analyst Agent (BEFORE)

```yaml
RequirementsAnalystAgent:
  Type: AWS::Bedrock::Agent
  DependsOn:
    - RequirementsAnalystFunction
    - RequirementsAnalystAgentRole
    - DeploymentArtifactsBucketPolicy
  Properties:
    AgentName: !Sub "autoninja-requirements-analyst-${Environment}"
    Description: Requirements Analyst agent - extracts and validates requirements from user requests
    AgentResourceRoleArn: !GetAtt RequirementsAnalystAgentRole.Arn
    FoundationModel: !Ref BedrockModel
    AgentCollaboration: DISABLED
    IdleSessionTTLInSeconds: 1800
    AutoPrepare: true
    Instruction: |
      You are a requirements analyst...
```

### Example: Requirements Analyst Agent (AFTER)

```yaml
RequirementsAnalystAgent:
  Type: AWS::Bedrock::Agent
  DependsOn:
    - RequirementsAnalystFunction
    - RequirementsAnalystAgentRole
    - DeploymentArtifactsBucketPolicy
    - CustomOrchestrationFunction  # ← ADDED
  Properties:
    AgentName: !Sub "autoninja-requirements-analyst-${Environment}"
    Description: Requirements Analyst agent - extracts and validates requirements from user requests
    AgentResourceRoleArn: !GetAtt RequirementsAnalystAgentRole.Arn
    FoundationModel: !Ref BedrockModel
    AgentCollaboration: DISABLED
    IdleSessionTTLInSeconds: 1800
    AutoPrepare: true
    OrchestrationType: CUSTOM_ORCHESTRATION  # ← ADDED
    CustomOrchestrationConfiguration:         # ← ADDED
      Executor:
        Lambda: !GetAtt CustomOrchestrationFunction.Arn
    Instruction: |
      You are a requirements analyst...
```

## Deployment Steps

### 1. Package Custom Orchestration Lambda

```bash
cd lambda/custom-orchestration
zip -r ../../build/custom-orchestration.zip handler.py
cd ../..
```

### 2. Upload to S3

```bash
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356
BUCKET_NAME=autoninja-deployment-artifacts-${AWS_REGION}

aws s3 cp build/custom-orchestration.zip \
  s3://${BUCKET_NAME}/lambda/custom-orchestration.zip \
  --sse aws:kms \
  --region ${AWS_REGION} \
  --profile ${AWS_PROFILE}
```

### 3. Deploy CloudFormation Stack

```bash
# Using deploy_all.sh script
export AUTO_DEPLOY=true
./scripts/deploy_all.sh

# OR manually
aws cloudformation deploy \
  --template-file infrastructure/cloudformation/autoninja-complete.yaml \
  --stack-name autoninja-production \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2 \
  --profile AdministratorAccess-784327326356
```

## Verification Steps

### 1. Check CloudFormation Stack

```bash
aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --region us-east-2 \
  --profile AdministratorAccess-784327326356 \
  --query 'Stacks[0].StackStatus'
```

Expected: `UPDATE_COMPLETE`

### 2. Verify Custom Orchestration Lambda

```bash
aws lambda get-function \
  --function-name autoninja-custom-orchestration-production \
  --region us-east-2 \
  --profile AdministratorAccess-784327326356 \
  --query 'Configuration.FunctionName'
```

Expected: `autoninja-custom-orchestration-production`

### 3. Verify Agent Configuration

For each agent, check that Custom Orchestration is enabled:

```bash
export AGENT_ID=<RequirementsAnalystAgentId from stack outputs>

aws bedrock-agent get-agent \
  --agent-id ${AGENT_ID} \
  --region us-east-2 \
  --profile AdministratorAccess-784327326356 \
  --query 'agent.orchestrationType'
```

Expected: `CUSTOM_ORCHESTRATION`

### 4. Run Tests

```bash
cd tests/requirements-analyst
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356
python test_requirements_analyst_agent.py
```

Expected:
- ✅ No ThrottlingException errors
- ✅ Sequential tool execution visible in logs
- ✅ All tests pass

### 5. Check CloudWatch Logs

Monitor Custom Orchestration Lambda logs:

```bash
aws logs tail \
  /aws/lambda/autoninja-custom-orchestration-production \
  --follow \
  --region us-east-2 \
  --profile AdministratorAccess-784327326356
```

Look for:
- `rate_limiting` events showing 60-second waits
- `handle_model_invoked` showing sequential tool execution
- `executing_first_tool` when multiple tools are requested

## Rollback Plan

If issues occur, revert the changes:

1. Remove `OrchestrationType` and `CustomOrchestrationConfiguration` from all 5 agents
2. Remove `CustomOrchestrationFunction` dependency from agents' `DependsOn`
3. Keep Custom Orchestration resources (they won't be used but won't cause harm)
4. Deploy updated stack

## Expected Behavior After Fix

### Before (Parallel Execution - Causes Throttling)
```
User Request → Agent Planning → [Tool1, Tool2, Tool3] in parallel → THROTTLING ERROR
```

### After (Sequential Execution - No Throttling)
```
User Request → Agent Planning → Tool1 (60s wait) → Tool2 (60s wait) → Tool3 → Success
```

### Performance Impact
- **Execution Time**: Increased by N×60 seconds (where N = number of tool calls)
- **Example**: 3 tool calls = 3 minutes instead of 1 minute
- **Reliability**: 100% (no throttling errors)

## Checklist

- [ ] Custom Orchestration Lambda created (`lambda/custom-orchestration/handler.py`)
- [ ] Lambda packaged and uploaded to S3
- [ ] Custom Orchestration resources added to CloudFormation template
- [ ] ALL 5 sub-agents updated with `OrchestrationType: CUSTOM_ORCHESTRATION`
- [ ] `CustomOrchestrationFunction` added to each agent's `DependsOn`
- [ ] CloudFormation template validates successfully
- [ ] Stack deployed successfully
- [ ] Custom Orchestration Lambda exists and has correct permissions
- [ ] All 5 agents show `CUSTOM_ORCHESTRATION` as orchestration type
- [ ] Tests run without throttling errors
- [ ] CloudWatch logs show sequential execution and rate limiting

## Troubleshooting

### Issue: CloudFormation Validation Error

**Symptom**: Template validation fails
**Solution**: Check YAML syntax, ensure proper indentation (2 spaces)

### Issue: Lambda Permission Denied

**Symptom**: Bedrock can't invoke Custom Orchestration Lambda
**Solution**: Verify `CustomOrchestrationInvokePermission` resource exists

### Issue: Agent Still Uses Default Orchestration

**Symptom**: `orchestrationType` shows `DEFAULT` instead of `CUSTOM_ORCHESTRATION`
**Solution**: Ensure `OrchestrationType` and `CustomOrchestrationConfiguration` are added to agent properties

### Issue: Throttling Still Occurs

**Symptom**: Still seeing ThrottlingException
**Solution**: Check CloudWatch logs to verify Custom Orchestration is actually being invoked

## Support Files

- **Lambda Code**: `lambda/custom-orchestration/handler.py`
- **CloudFormation Resources**: `infrastructure/cloudformation/custom-orchestration-resources.yaml`
- **Design Document**: `.kiro/specs/bedrock-throttling-investigation/design.md`
- **Requirements**: `.kiro/specs/bedrock-throttling-investigation/requirements.md`
- **Root Cause Analysis**: `.kiro/specs/bedrock-throttling-investigation/root-cause-analysis.md`

## Questions?

Refer to AWS documentation:
- Custom Orchestration: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-custom-orchestration.html
- CloudFormation AWS::Bedrock::Agent: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-bedrock-agent.html
