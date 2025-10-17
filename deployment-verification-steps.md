# Deployment Verification Steps

## Current Status

The CloudFormation stack deployment failed with the following error:
```
CreateAgentActionGroupRequest caught an error. Failed to create OpenAPI 3 model from the JSON/YAML object that you provided for action: quality-validator-actions
```

## Root Cause (from CloudTrail)

The actual error from CloudTrail event `4a7a85cf-5624-4edf-a02d-30fc679b8b0e`:
```json
"responseElements": {
    "message": "Failed to create OpenAPI 3 model from the JSON/YAML object that you provided for action: quality-validator-actions",
    "fieldList": [
        {
            "message": "Failed to download the file containing OpenAPI schema for action group quality-validator-actions due to insufficient permissions. Failed to download file due to access denied",
            "name": "S3FileAccessDenied"
        }
    ]
}
```

**The Bedrock Agent service cannot read the schema files from S3 due to missing IAM permissions.**

## Solution Implemented

Tasks 1-4 added the required S3 permissions to all Bedrock Agent IAM roles:

```yaml
- Sid: ReadSchemasFromS3
  Effect: Allow
  Action:
    - s3:GetObject
  Resource: !Sub "${ArtifactsBucket.Arn}/schemas/*"
  Condition:
    StringEquals:
      "aws:ResourceAccount": !Ref AWS::AccountId

- Sid: ListSchemasBucket
  Effect: Allow
  Action:
    - s3:ListBucket
  Resource: !GetAtt ArtifactsBucket.Arn
  Condition:
    StringEquals:
      "aws:ResourceAccount": !Ref AWS::AccountId
```

These permissions were added to:
- RequirementsAnalystAgentRole (lines 704-758)
- CodeGeneratorAgentRole (lines 759-813)
- SolutionArchitectAgentRole (lines 814-868)
- QualityValidatorAgentRole (lines 869-923)
- DeploymentManagerAgentRole (lines 924-978)
- SupervisorAgentRole (lines 979-1033)

## Deployment Steps

### 1. Update the CloudFormation Stack

Since AWS credentials are not configured in this environment, you need to run the deployment from your AWS console or configured terminal:

```bash
# Option 1: Using the deploy script with AUTO_DEPLOY
export AUTO_DEPLOY=true
./scripts/deploy_all.sh

# Option 2: Manual CloudFormation update
aws cloudformation deploy \
  --template-file infrastructure/cloudformation/autoninja-complete.yaml \
  --stack-name autoninja-production \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2 \
  --profile default
```

### 2. Verify Resources Created Successfully

After deployment completes, check:

```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --region us-east-2 \
  --query 'Stacks[0].StackStatus'

# Check for any failed resources
aws cloudformation describe-stack-events \
  --stack-name autoninja-production \
  --region us-east-2 \
  --max-items 50 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED` || ResourceStatus==`UPDATE_FAILED`]'
```

### 3. Verify Agent Status

Check that all agents show PREPARED status:

```bash
# Get agent IDs from stack outputs
aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --region us-east-2 \
  --query 'Stacks[0].Outputs'

# Check each agent status (replace AGENT_ID with actual ID)
aws bedrock-agent get-agent \
  --agent-id AGENT_ID \
  --region us-east-2 \
  --query 'agent.agentStatus'
```

Expected output: `"PREPARED"`

### 4. Verify Schema Access

Test that agents can access schemas:

```bash
# List schemas in S3
aws s3 ls s3://autoninja-artifacts-784327326356-production/schemas/ --region us-east-2

# Test IAM policy simulation (replace ROLE_ARN with actual role ARN)
aws iam simulate-principal-policy \
  --policy-source-arn ROLE_ARN \
  --action-names s3:GetObject s3:ListBucket \
  --resource-arns \
    "arn:aws:s3:::autoninja-artifacts-784327326356-production/schemas/*" \
    "arn:aws:s3:::autoninja-artifacts-784327326356-production"
```

Expected: All actions should show `"EvalDecision": "allowed"`

## Requirements Verification

This task addresses the following requirements:

- **1.1**: Bedrock Agent service can read OpenAPI schema files from S3 ✓
- **1.2**: IAM policies grant s3:GetObject permission for schemas/* prefix ✓
- **1.3**: IAM policies grant s3:ListBucket permission on artifacts bucket ✓
- **1.4**: Permissions include resource account condition for security ✓
- **1.5**: All six agent roles have schema read permissions ✓
- **4.1**: CloudFormation template validates successfully ✓
- **4.2**: Stack deploys without permission errors (pending redeployment)
- **4.3**: All agents reach PREPARED status (pending redeployment)

## Next Steps

1. **Redeploy the stack** using one of the commands above
2. **Monitor CloudFormation events** for any errors
3. **Verify all agents** reach PREPARED status
4. **Test agent invocation** to ensure end-to-end functionality

## Troubleshooting

If deployment still fails:

1. Check CloudFormation events:
   ```bash
   aws cloudformation describe-stack-events \
     --stack-name autoninja-production \
     --region us-east-2 \
     --max-items 20
   ```

2. Check CloudTrail for detailed error messages:
   - Go to CloudTrail console
   - Filter by Event name: `CreateAgentActionGroup` or `UpdateAgentActionGroup`
   - Look for `ValidationException` errors
   - Check `responseElements.fieldList` for specific permission issues

3. Verify S3 bucket policy doesn't block Bedrock service:
   ```bash
   aws s3api get-bucket-policy \
     --bucket autoninja-artifacts-784327326356-production \
     --region us-east-2
   ```
