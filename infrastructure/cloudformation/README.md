# AutoNinja CloudFormation Deployment

This directory contains the CloudFormation template for deploying the complete AutoNinja multi-agent system.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Bedrock Model Access** - Ensure you have access to the Claude Sonnet model in your AWS region
4. **cfn-lint** (optional) - For template validation

## Template Overview

The `autoninja-complete.yaml` template deploys:

- **6 Bedrock Agents**: 1 supervisor + 5 collaborators
- **5 Lambda Functions**: One for each collaborator agent
- **DynamoDB Table**: For inference record persistence
- **S3 Bucket**: For artifact storage
- **IAM Roles**: For Lambda functions and Bedrock agents
- **CloudWatch Log Groups**: For monitoring and debugging
- **Lambda Layer**: For shared libraries (placeholder)

## Deployment Steps

### 1. Validate the Template

```bash
cfn-lint infrastructure/cloudformation/autoninja-complete.yaml
```

### 2. Create a Placeholder Lambda Layer

Before deploying, you need to create a placeholder Lambda layer zip file:

```bash
# Create a minimal layer structure
mkdir -p /tmp/layer/python
echo "# Placeholder" > /tmp/layer/python/__init__.py
cd /tmp/layer
zip -r layer.zip python/

# Upload to S3 (the bucket will be created by the stack, so use a temporary bucket or create it first)
# For now, we'll handle this in the deployment
```

### 3. Deploy the Stack

```bash
aws cloudformation create-stack \
  --stack-name autoninja-production \
  --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=BedrockModel,ParameterValue=anthropic.claude-3-7-sonnet-20250219-v1:0 \
    ParameterKey=LogRetentionDays,ParameterValue=30 \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2
```

**Note**: The stack creation will initially fail because the Lambda Layer references an S3 key that doesn't exist yet. This is expected and will be resolved in task 4.4 when we populate the actual layer code.

### 4. Monitor Deployment

```bash
# Watch stack events
aws cloudformation describe-stack-events \
  --stack-name autoninja-production \
  --region us-east-2 \
  --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' \
  --output table

# Check stack status
aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --region us-east-2 \
  --query 'Stacks[0].StackStatus'
```

### 5. Get Stack Outputs

Once the stack is created successfully:

```bash
aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --region us-east-2 \
  --query 'Stacks[0].Outputs'
```

## Parameters

| Parameter | Description | Default | Allowed Values |
|-----------|-------------|---------|----------------|
| Environment | Deployment environment | production | production, staging, development |
| BedrockModel | Foundation model ID | anthropic.claude-3-7-sonnet-20250219-v1:0 | Valid Bedrock model IDs |
| DynamoDBBillingMode | DynamoDB billing mode | PAY_PER_REQUEST | PAY_PER_REQUEST, PROVISIONED |
| S3BucketName | Custom S3 bucket name (optional) | (auto-generated) | Valid S3 bucket name |
| LogRetentionDays | CloudWatch log retention | 30 | 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, etc. |

## Stack Outputs

The stack provides the following outputs:

- **SupervisorAgentId**: The ID of the supervisor agent
- **SupervisorAgentArn**: The ARN of the supervisor agent
- **SupervisorAgentAliasId**: The alias ID for the supervisor agent
- **DynamoDBTableName**: The name of the inference records table
- **S3BucketName**: The name of the artifacts bucket
- **InvocationCommand**: AWS CLI command to invoke the supervisor agent
- **Console URLs**: Direct links to AWS Console for resources

## Testing the Deployment

After successful deployment, test the supervisor agent:

```bash
# Get the invocation command from stack outputs
AGENT_ID=$(aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --query 'Stacks[0].Outputs[?OutputKey==`SupervisorAgentId`].OutputValue' \
  --output text)

ALIAS_ID=$(aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --query 'Stacks[0].Outputs[?OutputKey==`SupervisorAgentAliasId`].OutputValue' \
  --output text)

# Invoke the agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id $ALIAS_ID \
  --session-id $(uuidgen) \
  --input-text "I would like a friend agent" \
  --region us-east-2 \
  response.json
```

## Updating the Stack

To update the stack with changes:

```bash
aws cloudformation update-stack \
  --stack-name autoninja-production \
  --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
  --parameters \
    ParameterKey=Environment,UsePreviousValue=true \
    ParameterKey=BedrockModel,UsePreviousValue=true \
    ParameterKey=DynamoDBBillingMode,UsePreviousValue=true \
    ParameterKey=LogRetentionDays,UsePreviousValue=true \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2
```

## Deleting the Stack

To delete all resources:

```bash
# Empty the S3 bucket first (required)
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
  --output text)

aws s3 rm s3://$BUCKET_NAME --recursive

# Delete the stack
aws cloudformation delete-stack \
  --stack-name autoninja-production \
  --region us-east-2
```

## Troubleshooting

### Stack Creation Fails

1. Check CloudFormation events for error messages
2. Verify Bedrock model access in your region
3. Ensure IAM permissions are sufficient
4. Check service quotas for Bedrock Agents and Lambda

### Lambda Layer Issues

The initial deployment will fail due to missing Lambda Layer code. This is expected and will be resolved in task 4.4.

### Agent Invocation Fails

1. Verify the agent is in PREPARED state
2. Check CloudWatch logs for the agent and Lambda functions
3. Ensure the agent alias is created successfully
4. Verify IAM permissions for the agent role

## Cost Estimation

Approximate monthly costs (us-east-2):

- **Bedrock Agents**: Pay per request (~$0.002 per 1K input tokens)
- **Lambda**: Pay per invocation and duration (free tier: 1M requests/month)
- **DynamoDB**: On-demand pricing (~$1.25 per million write requests)
- **S3**: Standard storage (~$0.023 per GB)
- **CloudWatch Logs**: ~$0.50 per GB ingested

Actual costs depend on usage patterns.

## Next Steps

After successful deployment:

1. Implement Lambda function logic (tasks 6-9)
2. Create OpenAPI schemas (task 5)
3. Populate Lambda Layer with shared libraries (task 4)
4. Test end-to-end workflow
5. Monitor CloudWatch logs and X-Ray traces

## Support

For issues or questions, refer to:
- [AWS Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- Project requirements and design documents in `.kiro/specs/autoninja-bedrock-agents/`
