# OpenAPI Schema Deployment Guide

This guide explains how to deploy the OpenAPI schemas for the AutoNinja Bedrock Agents action groups.

## Overview

The AutoNinja system uses OpenAPI 3.0 schemas to define the interface between Bedrock Agents and their Lambda function action groups. Each of the 5 collaborator agents has a dedicated schema file:

1. **requirements-analyst-schema.yaml** - Requirements extraction, complexity analysis, and validation
2. **code-generator-schema.yaml** - Lambda code, agent config, and OpenAPI schema generation
3. **solution-architect-schema.yaml** - Architecture design, service selection, and IaC generation
4. **quality-validator-schema.yaml** - Code validation, security scanning, and compliance checking
5. **deployment-manager-schema.yaml** - CloudFormation generation, stack deployment, agent configuration, and testing

## Prerequisites

- AWS CLI configured with appropriate credentials
- S3 bucket created (either manually or via CloudFormation stack)
- Schema files in the `schemas/` directory

## Deployment Steps

### Step 1: Create or Identify S3 Bucket

If you haven't deployed the CloudFormation stack yet, you'll need to create an S3 bucket first:

```bash
# Set your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create S3 bucket (use your preferred region)
BUCKET_NAME="autoninja-artifacts-${ACCOUNT_ID}-production"
aws s3 mb s3://${BUCKET_NAME} --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket ${BUCKET_NAME} \
    --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket ${BUCKET_NAME} \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "aws:kms"
            },
            "BucketKeyEnabled": true
        }]
    }'
```

If you've already deployed the stack, get the bucket name from the stack outputs:

```bash
aws cloudformation describe-stacks \
    --stack-name autoninja-production \
    --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucketName`].OutputValue' \
    --output text
```

### Step 2: Upload OpenAPI Schemas to S3

Use the provided script to upload all schemas:

```bash
# Upload schemas using the script
./scripts/upload_schemas.sh ${BUCKET_NAME}
```

Or upload manually:

```bash
# Upload each schema file
aws s3 cp schemas/requirements-analyst-schema.yaml s3://${BUCKET_NAME}/schemas/
aws s3 cp schemas/code-generator-schema.yaml s3://${BUCKET_NAME}/schemas/
aws s3 cp schemas/solution-architect-schema.yaml s3://${BUCKET_NAME}/schemas/
aws s3 cp schemas/quality-validator-schema.yaml s3://${BUCKET_NAME}/schemas/
aws s3 cp schemas/deployment-manager-schema.yaml s3://${BUCKET_NAME}/schemas/

# Verify uploads
aws s3 ls s3://${BUCKET_NAME}/schemas/
```

### Step 3: Deploy or Update CloudFormation Stack

#### For New Deployments

```bash
aws cloudformation create-stack \
    --stack-name autoninja-production \
    --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
    --parameters \
        ParameterKey=Environment,ParameterValue=production \
        ParameterKey=BedrockModel,ParameterValue=anthropic.claude-sonnet-4-5-20250929-v1:0 \
        ParameterKey=S3BucketName,ParameterValue=${BUCKET_NAME} \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1

# Wait for stack creation
aws cloudformation wait stack-create-complete \
    --stack-name autoninja-production \
    --region us-east-1
```

#### For Existing Stack Updates

```bash
aws cloudformation update-stack \
    --stack-name autoninja-production \
    --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
    --parameters \
        ParameterKey=Environment,UsePreviousValue=true \
        ParameterKey=BedrockModel,UsePreviousValue=true \
        ParameterKey=S3BucketName,UsePreviousValue=true \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1

# Wait for stack update
aws cloudformation wait stack-update-complete \
    --stack-name autoninja-production \
    --region us-east-1
```

### Step 4: Verify Bedrock Agents

After deployment, verify that the agents have the action groups configured:

```bash
# Get supervisor agent ID from stack outputs
SUPERVISOR_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name autoninja-production \
    --query 'Stacks[0].Outputs[?OutputKey==`SupervisorAgentId`].OutputValue' \
    --output text)

# List all agents
aws bedrock-agent list-agents --region us-east-1

# Get details for a specific agent (e.g., Requirements Analyst)
REQUIREMENTS_AGENT_ID=$(aws bedrock-agent list-agents \
    --region us-east-1 \
    --query 'agentSummaries[?agentName==`autoninja-requirements-analyst-production`].agentId' \
    --output text)

aws bedrock-agent get-agent \
    --agent-id ${REQUIREMENTS_AGENT_ID} \
    --region us-east-1

# List action groups for the agent
aws bedrock-agent list-agent-action-groups \
    --agent-id ${REQUIREMENTS_AGENT_ID} \
    --agent-version DRAFT \
    --region us-east-1
```

## Schema Structure

Each OpenAPI schema follows this structure:

```yaml
openapi: 3.0.0
info:
  title: <Agent Name> Action Group API
  description: <Description>
  version: 1.0.0

paths:
  /<action-path>:
    post:
      summary: <Action summary>
      description: <Detailed description>
      operationId: <operationId>
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_name
                - <other required params>
              properties:
                job_name:
                  type: string
                  description: Unique job identifier
                # ... other properties
      responses:
        '200':
          description: Success response
          content:
            application/json:
              schema:
                # ... response schema
        '400':
          description: Invalid request
        '500':
          description: Internal server error
```

## Key Requirements

All schemas must:

1. **Include job_name parameter** - Required in all requests for tracking
2. **Define request/response schemas** - Use data models (Requirements, Architecture, CodeArtifacts, ValidationReport, DeploymentResults)
3. **Follow OpenAPI 3.0 spec** - Valid OpenAPI 3.0 format
4. **Include error responses** - 400 and 500 error schemas
5. **Use descriptive names** - Clear operationIds and descriptions

## Troubleshooting

### Schema Not Found Error

If you get an error about schemas not being found:

```bash
# Verify schemas are in S3
aws s3 ls s3://${BUCKET_NAME}/schemas/

# Check bucket policy allows Bedrock access
aws s3api get-bucket-policy --bucket ${BUCKET_NAME}
```

### Agent Not Updating

If the agent doesn't reflect schema changes:

```bash
# Prepare the agent to pick up changes
aws bedrock-agent prepare-agent \
    --agent-id ${AGENT_ID} \
    --region us-east-1

# Wait a few moments, then check status
aws bedrock-agent get-agent \
    --agent-id ${AGENT_ID} \
    --region us-east-1
```

### Schema Validation Errors

Validate your schema locally before uploading:

```bash
# Install swagger-cli if not already installed
npm install -g @apidevtools/swagger-cli

# Validate schema
swagger-cli validate schemas/requirements-analyst-schema.yaml
```

## Next Steps

After deploying the schemas:

1. Implement Lambda function handlers (Task 6-9)
2. Test each action group individually
3. Enable multi-agent collaboration in supervisor agent
4. Test end-to-end workflow

## References

- [AWS Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
- [AWS CloudFormation Bedrock Agent Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-bedrock-agent.html)
