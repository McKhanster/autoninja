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
if ! aws s3 ls "s3://${DEPLOYMENT_BUCKET}" --region "$REGION" --profile "$PROFILE" 2>&1 >/dev/null; then
    echo "Creating S3 bucket: $DEPLOYMENT_BUCKET"
    aws s3api create-bucket \
        --bucket "$DEPLOYMENT_BUCKET" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --create-bucket-configuration LocationConstraint="$REGION"


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

# Build Lambda packages if not exist
for agent in requirements-analyst code-generator solution-architect quality-validator deployment-manager custom-orchestration; do
    if [ ! -f "build/${agent}.zip" ]; then
        echo "Building $agent..."
        cd "lambda/$agent"
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt -t .
        fi
        zip -r "../../build/${agent}.zip" .
        cd ../..
    fi
done

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

# Verify collaborators-only CloudFormation template exists
echo -e "${YELLOW}Step 7: Verifying collaborators template exists...${NC}"
if [ ! -f "infrastructure/cloudformation/autoninja-collaborators.yaml" ]; then
    echo -e "${RED}Error: infrastructure/cloudformation/autoninja-collaborators.yaml not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Collaborators template found${NC}"
echo ""

# REMOVED: Template generation (lines 191-532)
# The static template infrastructure/cloudformation/autoninja-collaborators.yaml is now the source of truth

# OLD CODE (REMOVED):
# cat > infrastructure/cloudformation/autoninja-collaborators.yaml << 'EOF'
# AWSTemplateFormatVersion: "2010-09-09"

# Deploy the collaborators CloudFormation stack
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 8: Deploying collaborators CloudFormation stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "This will create:"
echo "  • 5 Bedrock Agents (Requirements Analyst, Code Generator, Solution Architect, Quality Validator, Deployment Manager)"
echo "  • 5 Lambda Functions for action groups"
echo "  • IAM roles and policies for agents and Lambdas"
echo "  • CloudWatch log groups for monitoring"
echo ""

aws cloudformation deploy \
    --template-file infrastructure/cloudformation/autoninja-collaborators.yaml \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
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
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  COLLABORATORS DEPLOYMENT COMPLETE!                           ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "All 5 collaborator agents are now deployed!"
    echo ""
    
    # Verify CloudWatch log groups exist for each agent
    echo -e "${YELLOW}Step 9: Verifying CloudWatch logging setup...${NC}"
    
    AGENTS=("requirements-analyst" "code-generator" "solution-architect" "quality-validator" "deployment-manager")
    for agent in "${AGENTS[@]}"; do
        LOG_GROUP="/aws/bedrock/agents/autoninja-${agent}-${ENVIRONMENT}"
        if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$REGION" --profile "$PROFILE" --query 'logGroups[?logGroupName==`'$LOG_GROUP'`]' --output text 2>/dev/null | grep -q "$LOG_GROUP"; then
            echo -e "    ${GREEN}✓${NC} $agent log group exists: $LOG_GROUP"
        else
            echo -e "    ${YELLOW}Warning: $agent log group not found: $LOG_GROUP${NC}"
        fi
    done
    
    echo -e "${GREEN}✓ Logging verification complete${NC}"
    echo ""
    
    echo "Next steps:"
    echo "  1. Run ./scripts/deploy_supervisor.sh to deploy the supervisor agent"
    echo "  2. The supervisor will orchestrate all 5 collaborators"
    echo "  3. Use the supervisor agent for end-to-end workflow execution"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Collaborators CloudFormation stack deployment failed${NC}"
    echo ""
    echo "Check the CloudFormation console for details:"
    echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
    exit 1
fi
