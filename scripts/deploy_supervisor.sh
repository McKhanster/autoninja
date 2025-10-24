#!/bin/bash
# Comprehensive deployment script for AutoNinja
# Deploys collaborators stack, supervisor stack, and all Lambda functions

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
COLLABORATORS_STACK_NAME="autoninja-collaborators-${ENVIRONMENT}"
SUPERVISOR_STACK_NAME="autoninja-supervisor-${ENVIRONMENT}"

# Logging
LOG_FILE="deployment-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "doc/$LOG_FILE")
exec 2>&1

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              AUTONINJA COMPLETE DEPLOYMENT                                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Profile: $PROFILE"
echo "  Environment: $ENVIRONMENT"
echo "  AWS Account ID: $AWS_ACCOUNT_ID"
echo "  Deployment Bucket: $DEPLOYMENT_BUCKET"
echo "  Collaborators Stack: $COLLABORATORS_STACK_NAME"
echo "  Supervisor Stack: $SUPERVISOR_STACK_NAME"
echo "  Log File: $LOG_FILE"
echo ""

# ============================================================================
# Step 1: Ensure deployment bucket exists
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 1: Ensuring deployment bucket exists...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

if ! aws s3 ls "s3://${DEPLOYMENT_BUCKET}" --region "$REGION" --profile "$PROFILE" 2>&1 >/dev/null; then
    echo "Creating S3 bucket: $DEPLOYMENT_BUCKET"
    aws s3api create-bucket \
        --bucket "$DEPLOYMENT_BUCKET" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --create-bucket-configuration LocationConstraint="$REGION"
    
    aws s3api put-bucket-encryption \
        --bucket "$DEPLOYMENT_BUCKET" \
        --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}' \
        --region "$REGION" \
        --profile "$PROFILE"
    
    echo -e "${GREEN}✓ S3 bucket created${NC}"
else
    echo -e "${GREEN}✓ S3 bucket already exists${NC}"
fi
echo ""

# ============================================================================
# Step 2: Build Lambda packages
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 2: Building Lambda packages...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""


# Clean and create build directory
rm -rf build
mkdir -p build

# Build Lambda Layer
echo "Building Lambda Layer..."
mkdir -p "build/lambda-layer/python"
cp -r shared "build/lambda-layer/python/"

# Install layer dependencies if requirements.txt exists
if [ -f "shared/requirements.txt" ]; then
    echo "  Installing layer dependencies..."
    pip install -q -r "shared/requirements.txt" -t "build/lambda-layer/python/"
fi

echo "  Creating ZIP package..."
cd "build/lambda-layer"
zip -q -r "../autoninja-shared-layer.zip" .
cd ../..

SIZE=$(du -h "build/autoninja-shared-layer.zip" | cut -f1)
echo -e "${GREEN}✓ Built autoninja-shared-layer.zip ($SIZE)${NC}"
rm -rf "build/lambda-layer"

# Build custom-orchestration Lambda package
echo "Building custom-orchestration..."
mkdir -p "build/custom-orchestration"
cp -r "lambda/custom-orchestration/"* "build/custom-orchestration/"

if [ -f "build/custom-orchestration/requirements.txt" ]; then
    echo "  Installing Python dependencies..."
    pip install -q -r "build/custom-orchestration/requirements.txt" -t "build/custom-orchestration/"
fi

echo "  Creating ZIP package..."
cd "build/custom-orchestration"
zip -q -r "../custom-orchestration.zip" .
cd ../..

SIZE=$(du -h "build/custom-orchestration.zip" | cut -f1)
echo -e "${GREEN}✓ Built custom-orchestration.zip ($SIZE)${NC}"
rm -rf "build/custom-orchestration"

# Build supervisor Lambda package with collaborators
echo "Building supervisor-agentcore with collaborators..."
mkdir -p "build/supervisor-agentcore"

# Copy supervisor source files
cp -r "lambda/supervisor-agentcore/"* "build/supervisor-agentcore/"

# Copy shared utilities
echo "  Copying shared utilities..."
cp -r shared "build/supervisor-agentcore/"

# Install Python dependencies if requirements.txt exists
if [ -f "build/supervisor-agentcore/requirements.txt" ]; then
    echo "  Installing Python dependencies..."
    pip install -q -r "build/supervisor-agentcore/requirements.txt" -t "build/supervisor-agentcore/"
fi

# Create zip from build directory
echo "  Creating ZIP package..."
cd "build/supervisor-agentcore"
zip -q -r "../supervisor-agentcore.zip" .
cd ../..

SIZE=$(du -h "build/supervisor-agentcore.zip" | cut -f1)
echo -e "${GREEN}✓ Built supervisor-agentcore.zip ($SIZE)${NC}"

# Clean up build directory
rm -rf "build/supervisor-agentcore"

# Upload Lambda packages and layer
echo ""
echo "Uploading Lambda packages and layer to S3..."

aws s3 cp "build/autoninja-shared-layer.zip" \
    "s3://${DEPLOYMENT_BUCKET}/layers/autoninja-shared-layer.zip" \
    --sse aws:kms \
    --region "$REGION" \
    --profile "$PROFILE" \
    --quiet
echo -e "  ${GREEN}✓${NC} autoninja-shared-layer.zip"

aws s3 cp "build/custom-orchestration.zip" \
    "s3://${DEPLOYMENT_BUCKET}/lambda/custom-orchestration.zip" \
    --sse aws:kms \
    --region "$REGION" \
    --profile "$PROFILE" \
    --quiet
echo -e "  ${GREEN}✓${NC} custom-orchestration.zip"

aws s3 cp "build/supervisor-agentcore.zip" \
    "s3://${DEPLOYMENT_BUCKET}/lambda/supervisor-agentcore.zip" \
    --sse aws:kms \
    --region "$REGION" \
    --profile "$PROFILE" \
    --quiet
echo -e "  ${GREEN}✓${NC} supervisor-agentcore.zip"

echo -e "${GREEN}✓ All Lambda packages and layer uploaded${NC}"
echo ""

# Upload schemas
echo "Uploading OpenAPI schemas to S3..."
for schema in schemas/*.yaml; do
    if [ -f "$schema" ]; then
        schema_name=$(basename "$schema")
        aws s3 cp "$schema" \
            "s3://${DEPLOYMENT_BUCKET}/schemas/${schema_name}" \
            --region "$REGION" \
            --profile "$PROFILE" \
            --quiet
        echo -e "  ${GREEN}✓${NC} Uploaded ${schema_name}"
    fi
done
echo ""

# Upload nested CloudFormation templates
echo -e "${YELLOW}Step 3: Uploading nested CloudFormation templates...${NC}"
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

# ============================================================================
# Step 4: Deploy or Update Collaborators Stack
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 4: Deploying Collaborators Stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if stack exists
if aws cloudformation describe-stacks --stack-name "$COLLABORATORS_STACK_NAME" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1; then
    echo "Stack exists, updating..."
    STACK_ACTION="update"
else
    echo "Stack does not exist, creating..."
    STACK_ACTION="create"
fi

aws cloudformation deploy \
    --template-file infrastructure/cloudformation/autoninja-collaborators.yaml \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        DeploymentBucket="$DEPLOYMENT_BUCKET" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --no-fail-on-empty-changeset

echo -e "${GREEN}✓ Collaborators stack deployed${NC}"
echo ""

# Get all agent IDs, ARNs, and Alias IDs
echo "Getting collaborator agent details..."
REQ_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`RequirementsAnalystAgentId`].OutputValue' \
    --output text)

REQ_AGENT_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`RequirementsAnalystAgentArn`].OutputValue' \
    --output text)

REQ_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`RequirementsAnalystAliasId`].OutputValue' \
    --output text)

CODE_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`CodeGeneratorAgentId`].OutputValue' \
    --output text)

CODE_AGENT_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`CodeGeneratorAgentArn`].OutputValue' \
    --output text)

CODE_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`CodeGeneratorAliasId`].OutputValue' \
    --output text)

ARCH_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`SolutionArchitectAgentId`].OutputValue' \
    --output text)

ARCH_AGENT_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`SolutionArchitectAgentArn`].OutputValue' \
    --output text)

ARCH_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`SolutionArchitectAliasId`].OutputValue' \
    --output text)

QV_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`QualityValidatorAgentId`].OutputValue' \
    --output text)

QV_AGENT_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`QualityValidatorAgentArn`].OutputValue' \
    --output text)

QV_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`QualityValidatorAliasId`].OutputValue' \
    --output text)

DM_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`DeploymentManagerAgentId`].OutputValue' \
    --output text)

DM_AGENT_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`DeploymentManagerAgentArn`].OutputValue' \
    --output text)

DM_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`DeploymentManagerAliasId`].OutputValue' \
    --output text)


AGENTCORE_MEMORY_ID=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreMemoryId`].OutputValue' \
    --output text)


AGENTCORE_MEMORY_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreMemoryArn`].OutputValue' \
    --output text)

echo -e "    ${GREEN}✓${NC} Requirements Analyst: $REQ_AGENT_ID (alias: $REQ_ALIAS_ID)"
echo -e "    ${GREEN}✓${NC} Code Generator: $CODE_AGENT_ID (alias: $CODE_ALIAS_ID)"
echo -e "    ${GREEN}✓${NC} Solution Architect: $ARCH_AGENT_ID (alias: $ARCH_ALIAS_ID)"
echo -e "    ${GREEN}✓${NC} Quality Validator: $QV_AGENT_ID (alias: $QV_ALIAS_ID)"
echo -e "    ${GREEN}✓${NC} Deployment Manager: $DM_AGENT_ID (alias: $DM_ALIAS_ID)"
echo ""

# Get storage outputs
INFERENCE_TABLE_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`InferenceRecordsTableName`].OutputValue' \
    --output text)

ARTIFACTS_BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$COLLABORATORS_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucketName`].OutputValue' \
    --output text)

INFERENCE_TABLE_ARN="arn:aws:dynamodb:${REGION}:${AWS_ACCOUNT_ID}:table/${INFERENCE_TABLE_NAME}"
ARTIFACTS_BUCKET_ARN="arn:aws:s3:::${ARTIFACTS_BUCKET_NAME}"

# ============================================================================
# Step 5: Deploy or Update Supervisor Stack
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 5: Deploying Supervisor Stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if stack exists
if aws cloudformation describe-stacks --stack-name "$SUPERVISOR_STACK_NAME" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1; then
    echo "Stack exists, updating..."
else
    echo "Stack does not exist, creating..."
fi

aws cloudformation deploy \
    --template-file infrastructure/cloudformation/stacks/supervisor.yaml \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        ArtifactsBucketName="$ARTIFACTS_BUCKET_NAME" \
        InferenceRecordsTableName="$INFERENCE_TABLE_NAME" \
        InferenceRecordsTableArn="$INFERENCE_TABLE_ARN" \
        ArtifactsBucketArn="$ARTIFACTS_BUCKET_ARN" \
        DeploymentBucket="$DEPLOYMENT_BUCKET" \
        AgentCoreMemoryId="$AGENTCORE_MEMORY_ID" \
        AgentCoreMemoryArn="$AGENTCORE_MEMORY_ARN" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --no-fail-on-empty-changeset

echo ""
echo -e "${GREEN}✓ Supervisor stack deployed${NC}"
echo ""

# ============================================================================
# Step 6: Prepare Bedrock Agent
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 6: Preparing Bedrock Agent...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Get supervisor agent details
SUPERVISOR_ID=$(aws cloudformation describe-stacks \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentId`].OutputValue' \
    --output text)

SUPERVISOR_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentAliasId`].OutputValue' \
    --output text)

if [ -n "$SUPERVISOR_ID" ]; then
    echo "Preparing Supervisor Agent: $SUPERVISOR_ID"
    aws bedrock-agent prepare-agent \
        --agent-id "$SUPERVISOR_ID" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --no-cli-pager
    
    echo -e "${GREEN}✓ Supervisor Agent prepared${NC}"
else
    echo -e "${RED}✗ Could not find Supervisor Agent ID${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    DEPLOYMENT COMPLETE!                                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Supervisor Agent Details:${NC}"
echo "  Agent ID: $SUPERVISOR_ID"
echo "  Alias ID: $SUPERVISOR_ALIAS_ID"
echo ""
echo -e "${YELLOW}Deployment Summary:${NC}"
echo "  ✓ Deployment bucket: $DEPLOYMENT_BUCKET"
echo "  ✓ Collaborators stack: $COLLABORATORS_STACK_NAME"
echo "  ✓ Supervisor stack: $SUPERVISOR_STACK_NAME"
echo "  ✓ Lambda package uploaded and deployed"
echo "  ✓ Bedrock Agent prepared"
echo ""
echo "To invoke the supervisor:"
echo "  aws bedrock-agent-runtime invoke-agent \\"
echo "    --agent-id $SUPERVISOR_ID \\"
echo "    --agent-alias-id $SUPERVISOR_ALIAS_ID \\"
echo "    --session-id job-\$(date +%s) \\"
echo "    --input-text \"Build a friend agent for emotional support\" \\"
echo "    --enable-trace \\"
echo "    --region $REGION \\"
echo "    --profile $PROFILE \\"
echo "    output.json"
echo ""
echo "To run tests:"
echo "  python tests/supervisor/test_e2e.py"
echo ""
echo "Log file saved to: $LOG_FILE"
echo ""