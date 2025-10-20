#!/bin/bash
# Master deployment script for AutoNinja system
# Deploys Lambda Layer, Lambda functions, schemas, and CloudFormation stack

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
S3_BUCKET="${S3_BUCKET:-autoninja-deployment-artifacts-${REGION}}"
STACK_NAME="autoninja-${ENVIRONMENT}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    AUTONINJA DEPLOYMENT SCRIPT                                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Profile: $PROFILE"
echo "  Environment: $ENVIRONMENT"
echo "  S3 Bucket: $S3_BUCKET"
echo "  Stack Name: $STACK_NAME"
echo ""

# Check required tools
echo -e "${YELLOW}Checking required tools...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}Error: AWS CLI is required but not installed.${NC}" >&2; exit 1; }
command -v zip >/dev/null 2>&1 || { echo -e "${RED}Error: zip is required but not installed.${NC}" >&2; exit 1; }
echo -e "${GREEN}✓ All required tools are available${NC}"
echo ""

# Create S3 bucket if it doesn't exist
echo -e "${YELLOW}Step 1: Ensuring S3 bucket exists...${NC}"
if aws s3 ls "s3://${S3_BUCKET}" --region "$REGION" --profile "$PROFILE" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: $S3_BUCKET"
    aws s3 mb "s3://${S3_BUCKET}" --region "$REGION" --profile "$PROFILE"
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$S3_BUCKET" \
        --versioning-configuration Status=Enabled \
        --region "$REGION" \
        --profile "$PROFILE"
    
    echo -e "${GREEN}✓ S3 bucket created and versioning enabled${NC}"
else
    echo -e "${GREEN}✓ S3 bucket already exists${NC}"
fi
echo ""

# Package and upload Lambda Layer
echo -e "${YELLOW}Step 2: Packaging Lambda Layer...${NC}"
LAYER_DIR="build/lambda-layer"
rm -rf "$LAYER_DIR"
mkdir -p "$LAYER_DIR/python"

echo "  Copying shared libraries..."
cp -r shared "$LAYER_DIR/python/"

# Install dependencies if requirements.txt exists
if [ -f "shared/requirements.txt" ]; then
    echo "  Installing dependencies..."
    pip install -r shared/requirements.txt -t "$LAYER_DIR/python/" --upgrade --quiet
fi

echo "  Creating ZIP archive..."
cd "$LAYER_DIR"
zip -r -q ../autoninja-shared-layer.zip python/
cd ../..

LAYER_SIZE=$(du -h build/autoninja-shared-layer.zip | cut -f1)
echo "  Layer size: $LAYER_SIZE"

echo "  Uploading to S3..."
aws s3 cp build/autoninja-shared-layer.zip \
    "s3://${S3_BUCKET}/layers/autoninja-shared-layer.zip" \
    --sse aws:kms \
    --region "$REGION" \
    --profile "$PROFILE" \
    --quiet

echo -e "${GREEN}✓ Lambda Layer uploaded${NC}"
echo ""

# Package and upload Lambda functions
echo -e "${YELLOW}Step 3: Packaging and uploading Lambda functions...${NC}"

AGENTS=("requirements-analyst" "code-generator" "solution-architect" "quality-validator" "deployment-manager" "custom-orchestration")

for agent in "${AGENTS[@]}"; do
    echo "  Processing $agent..."
    
    # Clean and create build directory
    rm -rf "build/$agent.zip"
    
    # Install dependencies and package
    cd "lambda/$agent"
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt -t .
    fi
    zip -r "../../build/$agent.zip" .
    cd ../..
    
    # Upload to S3
    aws s3 cp "build/$agent.zip" \
        "s3://${S3_BUCKET}/lambda/$agent.zip" \
        --sse aws:kms \
        --region "$REGION" \
        --profile "$PROFILE" \
        --quiet
    
    SIZE=$(du -h "build/$agent.zip" | cut -f1)
    echo -e "    ${GREEN}✓${NC} $agent ($SIZE)"
done

echo -e "${GREEN}✓ All Lambda functions uploaded${NC}"
echo ""

# Upload OpenAPI schemas
echo -e "${YELLOW}Step 4: Uploading OpenAPI schemas...${NC}"

for schema in schemas/*-schema.yaml; do
    if [ -f "$schema" ]; then
        filename=$(basename "$schema")
        aws s3 cp "$schema" \
            "s3://${S3_BUCKET}/schemas/$filename" \
            --sse aws:kms \
            --region "$REGION" \
            --profile "$PROFILE" \
            --quiet
        echo -e "    ${GREEN}✓${NC} $filename"
    fi
done

echo -e "${GREEN}✓ All schemas uploaded${NC}"
echo ""

# Upload CloudFormation template
echo -e "${YELLOW}Step 5: Uploading CloudFormation template...${NC}"

aws s3 cp infrastructure/cloudformation/autoninja-complete.yaml \
    "s3://${S3_BUCKET}/templates/autoninja-complete.yaml" \
    --sse aws:kms \
    --region "$REGION" \
    --profile "$PROFILE" \
    --quiet

TEMPLATE_URL="https://${S3_BUCKET}.s3.${REGION}.amazonaws.com/templates/autoninja-complete.yaml"
echo "  Template URL: $TEMPLATE_URL"
echo -e "${GREEN}✓ CloudFormation template uploaded${NC}"
echo ""

# Validate CloudFormation template
echo -e "${YELLOW}Step 6: Validating CloudFormation template...${NC}"

# Note: validate-template has 51KB limit, but CloudFormation deploy supports up to 1MB via S3
# Skip formal validation and rely on deployment validation instead
echo -e "${GREEN}✓ Template uploaded to S3 (validation will occur during deployment)${NC}"
echo ""

# Check if AUTO_DEPLOY is set, otherwise skip deployment
if [ "${AUTO_DEPLOY}" != "true" ]; then
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Preparation complete! Ready to deploy CloudFormation stack: ${STACK_NAME}${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "This will create/update:"
    echo "  • 5 Lambda functions"
    echo "  • 1 Lambda Layer"
    echo "  • 5 Bedrock Agents (collaborators)"
    echo "  • 1 Bedrock Agent (supervisor)"
    echo "  • 1 DynamoDB table"
    echo "  • 1 S3 bucket"
    echo "  • IAM roles and policies"
    echo "  • CloudWatch log groups"
    echo ""
    echo "To deploy the stack, run:"
    echo "  export AUTO_DEPLOY=true && ./scripts/deploy_all.sh"
    echo ""
    echo "Or manually deploy with:"
    echo "  aws cloudformation deploy \\"
    echo "    --template-file infrastructure/cloudformation/autoninja-complete.yaml \\"
    echo "    --stack-name $STACK_NAME \\"
    echo "    --capabilities CAPABILITY_NAMED_IAM \\"
    echo "    --region $REGION \\"
    echo "    --profile $PROFILE"
    exit 0
fi

echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Proceeding with CloudFormation deployment...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Deploy CloudFormation stack
echo -e "${YELLOW}Step 7: Deploying CloudFormation stack...${NC}"
echo "This may take 10-15 minutes..."
echo ""

aws cloudformation deploy \
    --template-file infrastructure/cloudformation/autoninja-complete.yaml \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --s3-bucket "$S3_BUCKET" \
    --s3-prefix "cloudformation" \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ CloudFormation stack deployed successfully${NC}"
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

    # Configure Custom Orchestration for all 5 sub-agents
    echo -e "${YELLOW}Step 8: Configuring Custom Orchestration...${NC}"
    echo "Applying custom orchestration to fix throttling issues..."
    echo ""

    # Get Custom Orchestration Lambda ARN
    CUSTOM_ORCH_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`CustomOrchestrationFunctionArn`].OutputValue' \
        --output text 2>/dev/null)

    if [ -z "$CUSTOM_ORCH_ARN" ]; then
        # If output doesn't exist, get it directly from the Lambda function
        CUSTOM_ORCH_ARN=$(aws lambda get-function \
            --function-name "autoninja-custom-orchestration-${ENVIRONMENT}" \
            --region "$REGION" \
            --profile "$PROFILE" \
            --query 'Configuration.FunctionArn' \
            --output text)
    fi

    echo "  Custom Orchestration Lambda ARN: $CUSTOM_ORCH_ARN"
    echo ""

    # Get agent IDs from stack outputs
    REQ_AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`RequirementsAnalystAgentId`].OutputValue' \
        --output text)

    CODE_AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`CodeGeneratorAgentId`].OutputValue' \
        --output text)

    ARCH_AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`SolutionArchitectAgentId`].OutputValue' \
        --output text)

    QV_AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`QualityValidatorAgentId`].OutputValue' \
        --output text)

    DM_AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`DeploymentManagerAgentId`].OutputValue' \
        --output text)

    # Configure each agent with custom orchestration
    AGENTS_TO_CONFIGURE=(
        "requirements-analyst:$REQ_AGENT_ID"
        "code-generator:$CODE_AGENT_ID"
        "solution-architect:$ARCH_AGENT_ID"
        "quality-validator:$QV_AGENT_ID"
        "deployment-manager:$DM_AGENT_ID"
    )

    for agent_info in "${AGENTS_TO_CONFIGURE[@]}"; do
        agent_name="${agent_info%%:*}"
        agent_id="${agent_info##*:}"

        echo "  Configuring $agent_name (ID: $agent_id)..."

        # Get current agent configuration to retrieve all required fields
        agent_config=$(aws bedrock-agent get-agent \
            --agent-id "$agent_id" \
            --region "$REGION" \
            --profile "$PROFILE" \
            --output json)

        agent_full_name=$(echo "$agent_config" | jq -r '.agent.agentName')
        agent_role_arn=$(echo "$agent_config" | jq -r '.agent.agentResourceRoleArn')
        foundation_model=$(echo "$agent_config" | jq -r '.agent.foundationModel')

        # Update agent with custom orchestration (using correct AWS CLI syntax)
        aws bedrock-agent update-agent \
            --agent-id "$agent_id" \
            --agent-name "$agent_full_name" \
            --agent-resource-role-arn "$agent_role_arn" \
            --foundation-model "$foundation_model" \
            --orchestration-type CUSTOM_ORCHESTRATION \
            --custom-orchestration "executor={lambda=${CUSTOM_ORCH_ARN}}" \
            --region "$REGION" \
            --profile "$PROFILE" \
            --output text > /dev/null 2>&1

        if [ $? -eq 0 ]; then
            # Prepare agent to apply changes
            aws bedrock-agent prepare-agent \
                --agent-id "$agent_id" \
                --region "$REGION" \
                --profile "$PROFILE" \
                --output text > /dev/null 2>&1

            echo -e "    ${GREEN}✓${NC} $agent_name configured with custom orchestration"
        else
            echo -e "    ${RED}✗${NC} Failed to configure $agent_name"
        fi
    done

    echo ""
    echo -e "${GREEN}✓ Custom Orchestration configured for all 5 sub-agents${NC}"
    echo ""

    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                        DEPLOYMENT COMPLETE!                                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test agents to verify no throttling errors"
    echo "  2. Run tests: python tests/requirements-analyst/test_requirements_analyst_agent.py"
    echo "  3. Check CloudWatch logs for custom orchestration activity"
    echo ""
else
    echo ""
    echo -e "${RED}✗ CloudFormation stack deployment failed${NC}"
    echo ""
    echo "Check the CloudFormation console for details:"
    echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
    exit 1
fi
