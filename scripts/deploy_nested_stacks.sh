#!/bin/bash
# Deployment script for AutoNinja nested CloudFormation stacks
# Uploads nested stack templates and deploys main orchestrator stack

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
STACK_NAME="autoninja-${ENVIRONMENT}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AUTONINJA NESTED STACKS DEPLOYMENT SCRIPT                             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Profile: $PROFILE"
echo "  Environment: $ENVIRONMENT"
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

# Upload Lambda deployment packages (assume they're already built)
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

# Deploy main CloudFormation stack
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 6: Deploying main CloudFormation stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "This will create/update:"
echo "  • 1 Supervisor Agent (with AgentCollaboration: SUPERVISOR)"
echo "  • 5 Collaborator Agents (Requirements Analyst, Code Generator, Solution Architect, Quality Validator, Deployment Manager)"
echo "  • 6 Lambda functions"
echo "  • 1 Lambda Layer"
echo "  • 2 DynamoDB tables (inference records + rate limiter)"
echo "  • 1 S3 bucket (artifacts)"
echo "  • IAM roles and policies"
echo "  • CloudWatch log groups"
echo ""

aws cloudformation deploy \
    --template-file infrastructure/cloudformation/autoninja-main.yaml \
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

    # Associate collaborators with supervisor
    echo -e "${YELLOW}Step 7: Associating collaborators with supervisor...${NC}"
    echo "Configuring multi-agent collaboration..."
    echo ""

    # Get supervisor agent ID
    SUPERVISOR_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`SupervisorAgentId`].OutputValue' \
        --output text)

    # Get collaborator agent IDs
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

    # Get agent aliases - they're all "production"
    ALIAS_NAME="production"

    # Associate each collaborator
    declare -A COLLABORATORS=(
        ["Requirements Analyst"]="$REQ_AGENT_ID"
        ["Code Generator"]="$CODE_AGENT_ID"
        ["Solution Architect"]="$ARCH_AGENT_ID"
        ["Quality Validator"]="$QV_AGENT_ID"
        ["Deployment Manager"]="$DM_AGENT_ID"
    )

    for name in "${!COLLABORATORS[@]}"; do
        agent_id="${COLLABORATORS[$name]}"
        echo "  Associating $name (${agent_id})..."

        # Get alias ID for this agent
        ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
            --agent-id "$agent_id" \
            --region "$REGION" \
            --profile "$PROFILE" \
            --query "agentAliasSummaries[?agentAliasName=='${ALIAS_NAME}'].agentAliasId" \
            --output text)

        if [ -z "$ALIAS_ID" ]; then
            echo -e "    ${YELLOW}Warning: Could not find alias for $name${NC}"
            continue
        fi

        # Build alias ARN
        ALIAS_ARN="arn:aws:bedrock:${REGION}:${AWS_ACCOUNT_ID}:agent-alias/${agent_id}/${ALIAS_ID}"

        # Associate collaborator with supervisor
        aws bedrock-agent associate-agent-collaborator \
            --agent-id "$SUPERVISOR_ID" \
            --agent-version DRAFT \
            --collaborator-name "${name// /-}" \
            --agent-descriptor "{\"aliasArn\":\"${ALIAS_ARN}\"}" \
            --collaboration-instruction "Handle ${name} tasks. Always include job_name parameter in requests." \
            --relay-conversation-history TO_COLLABORATOR \
            --region "$REGION" \
            --profile "$PROFILE" \
            2>/dev/null || echo -e "    ${YELLOW}(Already associated)${NC}"

        echo -e "    ${GREEN}✓${NC} $name associated"
    done

    echo ""

    # Prepare supervisor
    echo "  Preparing supervisor agent..."
    aws bedrock-agent prepare-agent \
        --agent-id "$SUPERVISOR_ID" \
        --region "$REGION" \
        --profile "$PROFILE" > /dev/null 2>&1

    echo -e "${GREEN}✓ Collaborators associated and supervisor prepared${NC}"
    echo ""

    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                        DEPLOYMENT COMPLETE!                                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test supervisor agent with sample invocation"
    echo "  2. Monitor CloudWatch logs for orchestration activity"
    echo "  3. Check DynamoDB for rate limiter activity"
    echo ""
    echo "To invoke the supervisor:"
    echo "  export SUPERVISOR_ID=$SUPERVISOR_ID"
    echo '  export SUPERVISOR_ALIAS=$(aws cloudformation describe-stacks --stack-name autoninja-production --query "Stacks[0].Outputs[?OutputKey=='"'"'SupervisorAgentAliasId'"'"'].OutputValue" --output text --region us-east-2 --profile '$PROFILE')'
    echo "  aws bedrock-agent-runtime invoke-agent \\"
    echo "    --agent-id \$SUPERVISOR_ID \\"
    echo "    --agent-alias-id \$SUPERVISOR_ALIAS \\"
    echo "    --session-id job-\$(date +%s) \\"
    echo "    --input-text \"Build a friend agent for emotional support\" \\"
    echo "    --enable-trace \\"
    echo "    --region $REGION \\"
    echo "    --profile $PROFILE \\"
    echo "    output.json"
    echo ""
else
    echo ""
    echo -e "${RED}✗ CloudFormation stack deployment failed${NC}"
    echo ""
    echo "Check the CloudFormation console for details:"
    echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
    exit 1
fi
