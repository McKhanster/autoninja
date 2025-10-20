#!/bin/bash
# Deployment script for AutoNinja collaborator agents (Step 1 of multi-agent setup)
# Deploys the 5 collaborator agents without supervisor

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-default}"
ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DEPLOYMENT_BUCKET="${DEPLOYMENT_BUCKET:-autoninja-deployment-artifacts-${REGION}}"
STACK_NAME="autoninja-collaborators-${ENVIRONMENT}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AUTONINJA COLLABORATOR AGENTS DEPLOYMENT (STEP 1)                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Profile: $PROFILE"
echo "  Environment: $ENVIRONMENT"
echo "  AWS Account ID: $AWS_ACCOUNT_ID"
echo "  Deployment Bucket: $DEPLOYMENT_BUCKET"
echo "  Stack Name: $STACK_NAME"
echo ""

# Check required tools
echo -e "${YELLOW}Checking required tools...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}Error: AWS CLI is required but not installed.${NC}" >&2; exit 1; }
echo -e "${GREEN}✓ All required tools are available${NC}"
echo ""

# Ensure deployment bucket exists
echo -e "${YELLOW}Step 1: Ensuring deployment bucket exists...${NC}"
if aws s3 ls "s3://${DEPLOYMENT_BUCKET}" --region "$REGION" --profile "$PROFILE" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: $DEPLOYMENT_BUCKET"
    aws s3 mb "s3://${DEPLOYMENT_BUCKET}" --region "$REGION" --profile "$PROFILE"

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$DEPLOYMENT_BUCKET" \
        --versioning-configuration Status=Enabled \
        --region "$REGION" \
        --profile "$PROFILE"

    echo -e "${GREEN}✓ S3 bucket created and versioning enabled${NC}"
else
    echo -e "${GREEN}✓ S3 bucket already exists${NC}"
fi
echo ""

# Upload nested CloudFormation templates
echo -e "${YELLOW}Step 2: Uploading nested CloudFormation templates...${NC}"
for template in infrastructure/cloudformation/stacks/*.yaml; do
    if [ -f "$template" ]; then
        filename=$(basename "$template")
        aws s3 cp "$template" \
            "s3://${DEPLOYMENT_BUCKET}/stacks/$filename" \
            --sse aws:kms \
            --region "$REGION" \
            --profile "$PROFILE" \
            --quiet
        echo -e "    ${GREEN}✓${NC} $filename"
    fi
done
echo -e "${GREEN}✓ All nested stack templates uploaded${NC}"
echo ""

# Upload Lambda deployment packages
echo -e "${YELLOW}Step 3: Uploading Lambda deployment packages...${NC}"

# Check if Lambda packages exist
LAMBDA_PACKAGES_EXIST=true
for agent in requirements-analyst code-generator solution-architect quality-validator deployment-manager custom-orchestration; do
    if [ ! -f "build/${agent}.zip" ]; then
        echo -e "${YELLOW}Warning: build/${agent}.zip not found${NC}"
        LAMBDA_PACKAGES_EXIST=false
    fi
done

if [ "$LAMBDA_PACKAGES_EXIST" = false ]; then
    echo -e "${YELLOW}Building Lambda packages...${NC}"
    ./scripts/deploy_all.sh
    echo ""
fi

# Upload Lambda packages
for agent in requirements-analyst code-generator solution-architect quality-validator deployment-manager custom-orchestration; do
    if [ -f "build/${agent}.zip" ]; then
        aws s3 cp "build/${agent}.zip" \
            "s3://${DEPLOYMENT_BUCKET}/lambda/${agent}.zip" \
            --sse aws:kms \
            --region "$REGION" \
            --profile "$PROFILE" \
            --quiet
        SIZE=$(du -h "build/${agent}.zip" | cut -f1)
        echo -e "    ${GREEN}✓${NC} ${agent}.zip ($SIZE)"
    fi
done
echo -e "${GREEN}✓ All Lambda packages uploaded${NC}"
echo ""

# Upload Lambda Layer
echo -e "${YELLOW}Step 4: Uploading Lambda Layer...${NC}"
if [ -f "build/autoninja-shared-layer.zip" ]; then
    aws s3 cp build/autoninja-shared-layer.zip \
        "s3://${DEPLOYMENT_BUCKET}/layers/autoninja-shared-layer.zip" \
        --sse aws:kms \
        --region "$REGION" \
        --profile "$PROFILE" \
        --quiet
    LAYER_SIZE=$(du -h build/autoninja-shared-layer.zip | cut -f1)
    echo -e "    ${GREEN}✓${NC} autoninja-shared-layer.zip ($LAYER_SIZE)"
else
    echo -e "${YELLOW}Warning: build/autoninja-shared-layer.zip not found. Building...${NC}"
    ./scripts/package_lambda_layer.sh
    aws s3 cp build/autoninja-shared-layer.zip \
        "s3://${DEPLOYMENT_BUCKET}/layers/autoninja-shared-layer.zip" \
        --sse aws:kms \
        --region "$REGION" \
        --profile "$PROFILE" \
        --quiet
fi
echo -e "${GREEN}✓ Lambda Layer uploaded${NC}"
echo ""

# Upload OpenAPI schemas
echo -e "${YELLOW}Step 5: Uploading OpenAPI schemas...${NC}"
for schema in schemas/*-schema.yaml; do
    if [ -f "$schema" ]; then
        filename=$(basename "$schema")
        aws s3 cp "$schema" \
            "s3://${DEPLOYMENT_BUCKET}/schemas/$filename" \
            --sse aws:kms \
            --region "$REGION" \
            --profile "$PROFILE" \
            --quiet
        echo -e "    ${GREEN}✓${NC} $filename"
    fi
done
echo -e "${GREEN}✓ All schemas uploaded${NC}"
echo ""

# Configure Bedrock model invocation logging (optional but recommended)
echo -e "${YELLOW}Step 6: Configuring Bedrock model invocation logging...${NC}"
LOG_GROUP_NAME="/aws/bedrock/modelinvocations"

# Check if log group exists
if ! aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --region "$REGION" --profile "$PROFILE" --query 'logGroups[?logGroupName==`'$LOG_GROUP_NAME'`]' --output text 2>/dev/null | grep -q "$LOG_GROUP_NAME"; then
    echo "Creating CloudWatch log group for Bedrock model invocations..."
    aws logs create-log-group \
        --log-group-name "$LOG_GROUP_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" 2>/dev/null || echo "    ${YELLOW}Log group may already exist${NC}"
    
    # Set retention policy
    aws logs put-retention-policy \
        --log-group-name "$LOG_GROUP_NAME" \
        --retention-in-days 30 \
        --region "$REGION" \
        --profile "$PROFILE" 2>/dev/null || echo "    ${YELLOW}Could not set retention policy${NC}"
fi

# Configure Bedrock logging (this may fail if already configured, which is fine)
aws bedrock put-model-invocation-logging-configuration \
    --logging-config '{
        "cloudWatchConfig": {
            "logGroupName": "'$LOG_GROUP_NAME'",
            "roleArn": "arn:aws:iam::'$AWS_ACCOUNT_ID':role/service-role/AmazonBedrockExecutionRoleForAgents_*"
        },
        "textDataDeliveryEnabled": true,
        "imageDataDeliveryEnabled": true,
        "embeddingDataDeliveryEnabled": true
    }' \
    --region "$REGION" \
    --profile "$PROFILE" 2>/dev/null || echo "    ${YELLOW}Bedrock logging may already be configured${NC}"

echo -e "${GREEN}✓ Bedrock logging configuration attempted${NC}"
echo ""

# Create collaborators-only CloudFormation template
echo -e "${YELLOW}Step 7: Creating collaborators-only template...${NC}"
cat > infrastructure/cloudformation/autoninja-collaborators.yaml << 'EOF'
AWSTemplateFormatVersion: "2010-09-09"
Description: >
  AutoNinja Collaborators Stack - 5 collaborator Bedrock Agents with complete infrastructure.
  This is Step 1 of multi-agent collaboration setup.

Parameters:
  Environment:
    Type: String
    Description: Deployment environment
    Default: production

  BedrockModel:
    Type: String
    Description: Foundation model ID for Bedrock Agents
    Default: us.anthropic.claude-sonnet-4-5-20250929-v1:0

  DynamoDBBillingMode:
    Type: String
    Description: Billing mode for DynamoDB tables
    Default: PAY_PER_REQUEST

  S3BucketName:
    Type: String
    Description: Optional custom name for S3 artifacts bucket
    Default: ""

  DeploymentBucket:
    Type: String
    Description: S3 bucket containing Lambda deployment packages and CloudFormation templates
    Default: ""

  LogRetentionDays:
    Type: Number
    Description: CloudWatch log retention period in days
    Default: 30

Conditions:
  UseDefaultDeploymentBucket: !Equals [!Ref DeploymentBucket, ""]

Resources:
  # Storage Stack - DynamoDB + S3 + Rate Limiter
  StorageStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub
        - "https://${Bucket}.s3.${AWS::Region}.amazonaws.com/stacks/storage.yaml"
        - Bucket: !If
            - UseDefaultDeploymentBucket
            - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
            - !Ref DeploymentBucket
      Parameters:
        Environment: !Ref Environment
        DynamoDBBillingMode: !Ref DynamoDBBillingMode
        S3BucketName: !Ref S3BucketName

  # Lambda Layer Stack - Shared Libraries + Base IAM Policy
  LambdaLayerStack:
    Type: AWS::CloudFormation::Stack
    DependsOn: StorageStack
    Properties:
      TemplateURL: !Sub
        - "https://${Bucket}.s3.${AWS::Region}.amazonaws.com/stacks/lambda-layer.yaml"
        - Bucket: !If
            - UseDefaultDeploymentBucket
            - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
            - !Ref DeploymentBucket
      Parameters:
        Environment: !Ref Environment
        DeploymentBucket: !If
          - UseDefaultDeploymentBucket
          - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
          - !Ref DeploymentBucket
        InferenceRecordsTableArn: !GetAtt StorageStack.Outputs.InferenceRecordsTableArn
        ArtifactsBucketArn: !GetAtt StorageStack.Outputs.ArtifactsBucketArn

  # Custom Orchestration Stack - Rate Limiting Lambda
  CustomOrchestrationStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub
        - "https://${Bucket}.s3.${AWS::Region}.amazonaws.com/stacks/custom-orchestration.yaml"
        - Bucket: !If
            - UseDefaultDeploymentBucket
            - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
            - !Ref DeploymentBucket
      Parameters:
        Environment: !Ref Environment
        DeploymentBucket: !If
          - UseDefaultDeploymentBucket
          - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
          - !Ref DeploymentBucket
        LogRetentionDays: !Ref LogRetentionDays

  # Collaborator Agent Stacks (5 agents)
  RequirementsAnalystStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub
        - "https://${Bucket}.s3.${AWS::Region}.amazonaws.com/stacks/requirements-analyst.yaml"
        - Bucket: !If
            - UseDefaultDeploymentBucket
            - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
            - !Ref DeploymentBucket
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !If
          - UseDefaultDeploymentBucket
          - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
          - !Ref DeploymentBucket
        InferenceRecordsTableName: !GetAtt StorageStack.Outputs.InferenceRecordsTableName
        ArtifactsBucketName: !GetAtt StorageStack.Outputs.ArtifactsBucketName
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn
        LambdaBasePolicyArn: !GetAtt LambdaLayerStack.Outputs.LambdaBasePolicyArn
        LogRetentionDays: !Ref LogRetentionDays

  CodeGeneratorStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub
        - "https://${Bucket}.s3.${AWS::Region}.amazonaws.com/stacks/code-generator.yaml"
        - Bucket: !If
            - UseDefaultDeploymentBucket
            - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
            - !Ref DeploymentBucket
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !If
          - UseDefaultDeploymentBucket
          - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
          - !Ref DeploymentBucket
        InferenceRecordsTableName: !GetAtt StorageStack.Outputs.InferenceRecordsTableName
        ArtifactsBucketName: !GetAtt StorageStack.Outputs.ArtifactsBucketName
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn
        LambdaBasePolicyArn: !GetAtt LambdaLayerStack.Outputs.LambdaBasePolicyArn
        LogRetentionDays: !Ref LogRetentionDays

  SolutionArchitectStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub
        - "https://${Bucket}.s3.${AWS::Region}.amazonaws.com/stacks/solution-architect.yaml"
        - Bucket: !If
            - UseDefaultDeploymentBucket
            - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
            - !Ref DeploymentBucket
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !If
          - UseDefaultDeploymentBucket
          - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
          - !Ref DeploymentBucket
        InferenceRecordsTableName: !GetAtt StorageStack.Outputs.InferenceRecordsTableName
        ArtifactsBucketName: !GetAtt StorageStack.Outputs.ArtifactsBucketName
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn
        LambdaBasePolicyArn: !GetAtt LambdaLayerStack.Outputs.LambdaBasePolicyArn
        LogRetentionDays: !Ref LogRetentionDays

  QualityValidatorStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub
        - "https://${Bucket}.s3.${AWS::Region}.amazonaws.com/stacks/quality-validator.yaml"
        - Bucket: !If
            - UseDefaultDeploymentBucket
            - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
            - !Ref DeploymentBucket
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !If
          - UseDefaultDeploymentBucket
          - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
          - !Ref DeploymentBucket
        InferenceRecordsTableName: !GetAtt StorageStack.Outputs.InferenceRecordsTableName
        ArtifactsBucketName: !GetAtt StorageStack.Outputs.ArtifactsBucketName
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn
        LambdaBasePolicyArn: !GetAtt LambdaLayerStack.Outputs.LambdaBasePolicyArn
        LogRetentionDays: !Ref LogRetentionDays

  DeploymentManagerStack:
    Type: AWS::CloudFormation::Stack
    DependsOn:
      - StorageStack
      - LambdaLayerStack
    Properties:
      TemplateURL: !Sub
        - "https://${Bucket}.s3.${AWS::Region}.amazonaws.com/stacks/deployment-manager.yaml"
        - Bucket: !If
            - UseDefaultDeploymentBucket
            - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
            - !Ref DeploymentBucket
      Parameters:
        Environment: !Ref Environment
        BedrockModel: !Ref BedrockModel
        DeploymentBucket: !If
          - UseDefaultDeploymentBucket
          - !Sub "autoninja-deployment-artifacts-${AWS::Region}"
          - !Ref DeploymentBucket
        InferenceRecordsTableName: !GetAtt StorageStack.Outputs.InferenceRecordsTableName
        ArtifactsBucketName: !GetAtt StorageStack.Outputs.ArtifactsBucketName
        LambdaLayerArn: !GetAtt LambdaLayerStack.Outputs.LayerArn
        LambdaBasePolicyArn: !GetAtt LambdaLayerStack.Outputs.LambdaBasePolicyArn
        LogRetentionDays: !Ref LogRetentionDays

Outputs:
  # Collaborator Agent IDs and Alias IDs for supervisor setup
  RequirementsAnalystAgentId:
    Description: Requirements Analyst Agent ID
    Value: !GetAtt RequirementsAnalystStack.Outputs.AgentId
    Export:
      Name: !Sub "${AWS::StackName}-RequirementsAnalystAgentId"

  RequirementsAnalystAgentArn:
    Description: Requirements Analyst Agent ARN
    Value: !GetAtt RequirementsAnalystStack.Outputs.AgentArn
    Export:
      Name: !Sub "${AWS::StackName}-RequirementsAnalystAgentArn"

  RequirementsAnalystAliasId:
    Description: Requirements Analyst Agent Alias ID
    Value: !GetAtt RequirementsAnalystStack.Outputs.AgentAliasId
    Export:
      Name: !Sub "${AWS::StackName}-RequirementsAnalystAliasId"

  CodeGeneratorAgentId:
    Description: Code Generator Agent ID
    Value: !GetAtt CodeGeneratorStack.Outputs.AgentId
    Export:
      Name: !Sub "${AWS::StackName}-CodeGeneratorAgentId"

  CodeGeneratorAgentArn:
    Description: Code Generator Agent ARN
    Value: !GetAtt CodeGeneratorStack.Outputs.AgentArn
    Export:
      Name: !Sub "${AWS::StackName}-CodeGeneratorAgentArn"

  CodeGeneratorAliasId:
    Description: Code Generator Agent Alias ID
    Value: !GetAtt CodeGeneratorStack.Outputs.AgentAliasId
    Export:
      Name: !Sub "${AWS::StackName}-CodeGeneratorAliasId"

  SolutionArchitectAgentId:
    Description: Solution Architect Agent ID
    Value: !GetAtt SolutionArchitectStack.Outputs.AgentId
    Export:
      Name: !Sub "${AWS::StackName}-SolutionArchitectAgentId"

  SolutionArchitectAgentArn:
    Description: Solution Architect Agent ARN
    Value: !GetAtt SolutionArchitectStack.Outputs.AgentArn
    Export:
      Name: !Sub "${AWS::StackName}-SolutionArchitectAgentArn"

  SolutionArchitectAliasId:
    Description: Solution Architect Agent Alias ID
    Value: !GetAtt SolutionArchitectStack.Outputs.AgentAliasId
    Export:
      Name: !Sub "${AWS::StackName}-SolutionArchitectAliasId"

  QualityValidatorAgentId:
    Description: Quality Validator Agent ID
    Value: !GetAtt QualityValidatorStack.Outputs.AgentId
    Export:
      Name: !Sub "${AWS::StackName}-QualityValidatorAgentId"

  QualityValidatorAgentArn:
    Description: Quality Validator Agent ARN
    Value: !GetAtt QualityValidatorStack.Outputs.AgentArn
    Export:
      Name: !Sub "${AWS::StackName}-QualityValidatorAgentArn"

  QualityValidatorAliasId:
    Description: Quality Validator Agent Alias ID
    Value: !GetAtt QualityValidatorStack.Outputs.AgentAliasId
    Export:
      Name: !Sub "${AWS::StackName}-QualityValidatorAliasId"

  DeploymentManagerAgentId:
    Description: Deployment Manager Agent ID
    Value: !GetAtt DeploymentManagerStack.Outputs.AgentId
    Export:
      Name: !Sub "${AWS::StackName}-DeploymentManagerAgentId"

  DeploymentManagerAgentArn:
    Description: Deployment Manager Agent ARN
    Value: !GetAtt DeploymentManagerStack.Outputs.AgentArn
    Export:
      Name: !Sub "${AWS::StackName}-DeploymentManagerAgentArn"

  DeploymentManagerAliasId:
    Description: Deployment Manager Agent Alias ID
    Value: !GetAtt DeploymentManagerStack.Outputs.AgentAliasId
    Export:
      Name: !Sub "${AWS::StackName}-DeploymentManagerAliasId"

  # Storage Outputs
  InferenceRecordsTableName:
    Description: DynamoDB inference records table name
    Value: !GetAtt StorageStack.Outputs.InferenceRecordsTableName
    Export:
      Name: !Sub "${AWS::StackName}-InferenceRecordsTableName"


  ArtifactsBucketName:
    Description: S3 artifacts bucket name
    Value: !GetAtt StorageStack.Outputs.ArtifactsBucketName
    Export:
      Name: !Sub "${AWS::StackName}-ArtifactsBucketName"

  Environment:
    Description: Deployment environment
    Value: !Ref Environment
    Export:
      Name: !Sub "${AWS::StackName}-Environment"
EOF

echo -e "${GREEN}✓ Collaborators template created${NC}"
echo ""

# Deploy collaborators CloudFormation stack
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 8: Deploying collaborators CloudFormation stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "This will create:"
echo "  • 5 Collaborator Agents (Requirements Analyst, Code Generator, Solution Architect, Quality Validator, Deployment Manager)"
echo "  • 5 Lambda functions"
echo "  • 1 Lambda Layer"
echo "  • 2 DynamoDB tables (inference records + rate limiter)"
echo "  • 1 S3 bucket (artifacts)"
echo "  • IAM roles and policies"
echo "  • CloudWatch log groups"
echo ""

aws cloudformation deploy \
    --template-file infrastructure/cloudformation/autoninja-collaborators.yaml \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        DeploymentBucket="$DEPLOYMENT_BUCKET" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Collaborators CloudFormation stack deployed successfully${NC}"
    echo ""

    # Get stack outputs
    echo -e "${YELLOW}Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table

    echo ""
    
    # Verify CloudWatch log groups exist for collaborators
    echo -e "${YELLOW}Verifying CloudWatch logging setup...${NC}"
    
    # Check collaborator log groups
    for agent in requirements-analyst code-generator solution-architect quality-validator deployment-manager; do
        LOG_GROUP="/aws/bedrock/agents/autoninja-${agent}-${ENVIRONMENT}"
        if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$REGION" --profile "$PROFILE" --query 'logGroups[?logGroupName==`'$LOG_GROUP'`]' --output text 2>/dev/null | grep -q "$LOG_GROUP"; then
            echo -e "    ${GREEN}✓${NC} ${agent} log group exists"
        else
            echo -e "    ${YELLOW}Warning: ${agent} log group not found${NC}"
        fi
    done
    
    # Check model invocation log group
    MODEL_LOG_GROUP="/aws/bedrock/modelinvocations"
    if aws logs describe-log-groups --log-group-name-prefix "$MODEL_LOG_GROUP" --region "$REGION" --profile "$PROFILE" --query 'logGroups[?logGroupName==`'$MODEL_LOG_GROUP'`]' --output text 2>/dev/null | grep -q "$MODEL_LOG_GROUP"; then
        echo -e "    ${GREEN}✓${NC} Model invocation log group configured"
    else
        echo -e "    ${YELLOW}Warning: Model invocation log group not found${NC}"
    fi
    
    echo -e "${GREEN}✓ Logging verification complete${NC}"
    echo ""
    
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    COLLABORATORS DEPLOYMENT COMPLETE!                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run ./scripts/deploy_supervisor.sh to deploy supervisor agent"
    echo "  2. The supervisor will be configured with multi-agent collaboration"
    echo ""
    echo "To monitor collaborator logs:"
    echo "  # Requirements Analyst logs:"
    echo "  aws logs tail /aws/bedrock/agents/autoninja-requirements-analyst-${ENVIRONMENT} --follow --region $REGION --profile $PROFILE"
    echo ""
    echo "  # Model invocation logs (all agents):"
    echo "  aws logs tail /aws/bedrock/modelinvocations --follow --region $REGION --profile $PROFILE"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Collaborators CloudFormation stack deployment failed${NC}"
    echo ""
    echo "Check the CloudFormation console for details:"
    echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
    exit 1
fi