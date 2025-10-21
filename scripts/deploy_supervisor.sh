#!/bin/bash
# Deployment script for AutoNinja supervisor agent (Step 2 of multi-agent setup)
# Deploys the supervisor agent and configures multi-agent collaboration

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

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AUTONINJA SUPERVISOR AGENT DEPLOYMENT (STEP 2)                        ║${NC}"
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
echo ""

# Check that collaborators stack exists
echo -e "${YELLOW}Step 1: Verifying collaborators stack exists...${NC}"
if ! aws cloudformation describe-stacks --stack-name "$COLLABORATORS_STACK_NAME" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1; then
    echo -e "${RED}Error: Collaborators stack '$COLLABORATORS_STACK_NAME' not found.${NC}"
    echo "Please run ./scripts/deploy_collaborators.sh first."
    exit 1
fi
echo -e "${GREEN}✓ Collaborators stack found${NC}"
echo ""

# Get collaborator agent details from stack outputs
echo -e "${YELLOW}Step 2: Getting collaborator agent details...${NC}"


# Build Lambda packages if not exist
for agent in supervisor-agentcore; do
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
for agent in supervisor-agentcore; do
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

# Get all agent IDs, ARNs, and Alias IDs
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

# Deploy supervisor CloudFormation stack
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 3: Deploying supervisor CloudFormation stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "This will create:"
echo "  • 1 Supervisor Agent (with AgentCollaboration: SUPERVISOR)"
echo "  • AgentCollaborators configuration for all 5 collaborators"
echo "  • IAM roles and policies for supervisor"
echo "  • CloudWatch log groups"
echo ""

aws cloudformation deploy \
    --template-file infrastructure/cloudformation/stacks/supervisor.yaml \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        RequirementsAnalystAgentArn="$REQ_AGENT_ARN" \
        RequirementsAnalystAgentId="$REQ_AGENT_ID" \
        RequirementsAnalystAliasId="$REQ_ALIAS_ID" \
        CodeGeneratorAgentArn="$CODE_AGENT_ARN" \
        CodeGeneratorAgentId="$CODE_AGENT_ID" \
        CodeGeneratorAliasId="$CODE_ALIAS_ID" \
        SolutionArchitectAgentArn="$ARCH_AGENT_ARN" \
        SolutionArchitectAgentId="$ARCH_AGENT_ID" \
        SolutionArchitectAliasId="$ARCH_ALIAS_ID" \
        QualityValidatorAgentArn="$QV_AGENT_ARN" \
        QualityValidatorAgentId="$QV_AGENT_ID" \
        QualityValidatorAliasId="$QV_ALIAS_ID" \
        DeploymentManagerAgentArn="$DM_AGENT_ARN" \
        DeploymentManagerAgentId="$DM_AGENT_ID" \
        DeploymentManagerAliasId="$DM_ALIAS_ID" \
        ArtifactsBucketName="$ARTIFACTS_BUCKET_NAME" \
        InferenceRecordsTableArn="$INFERENCE_TABLE_ARN" \
        ArtifactsBucketArn="$ARTIFACTS_BUCKET_ARN" \
        DeploymentBucket="$DEPLOYMENT_BUCKET" \
        AgentCoreMemoryId="$AGENTCORE_MEMORY_ID" \
        AgentCoreMemoryArn="$AGENTCORE_MEMORY_ARN" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Supervisor CloudFormation stack deployed successfully${NC}"
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

    echo -e "${YELLOW}Supervisor Agent Details:${NC}"
    echo "  Agent ID: $SUPERVISOR_ID"
    echo "  Alias ID: $SUPERVISOR_ALIAS_ID"
    echo ""

    # Get stack outputs
    echo -e "${YELLOW}Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name "$SUPERVISOR_STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    SUPERVISOR DEPLOYMENT COMPLETE!                            ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Multi-agent collaboration is now configured!"
    echo ""
    
    # Verify CloudWatch log groups exist
    echo -e "${YELLOW}Step 4: Verifying CloudWatch logging setup...${NC}"
    
    # Check supervisor log group
    SUPERVISOR_LOG_GROUP="/aws/bedrock/agents/autoninja-supervisor-${ENVIRONMENT}"
    if aws logs describe-log-groups --log-group-name-prefix "$SUPERVISOR_LOG_GROUP" --region "$REGION" --profile "$PROFILE" --query 'logGroups[?logGroupName==`'$SUPERVISOR_LOG_GROUP'`]' --output text 2>/dev/null | grep -q "$SUPERVISOR_LOG_GROUP"; then
        echo -e "    ${GREEN}✓${NC} Supervisor log group exists: $SUPERVISOR_LOG_GROUP"
    else
        echo -e "    ${YELLOW}Warning: Supervisor log group not found: $SUPERVISOR_LOG_GROUP${NC}"
    fi
    
    # Check model invocation log group
    MODEL_LOG_GROUP="/aws/bedrock/modelinvocations"
    if aws logs describe-log-groups --log-group-name-prefix "$MODEL_LOG_GROUP" --region "$REGION" --profile "$PROFILE" --query 'logGroups[?logGroupName==`'$MODEL_LOG_GROUP'`]' --output text 2>/dev/null | grep -q "$MODEL_LOG_GROUP"; then
        echo -e "    ${GREEN}✓${NC} Model invocation log group exists: $MODEL_LOG_GROUP"
    else
        echo -e "    ${YELLOW}Warning: Model invocation log group not found: $MODEL_LOG_GROUP${NC}"
    fi
    
    echo -e "${GREEN}✓ Logging verification complete${NC}"
    echo ""
    
    echo "To invoke the supervisor:"
    echo "  export SUPERVISOR_ID=$SUPERVISOR_ID"
    echo "  export SUPERVISOR_ALIAS_ID=$SUPERVISOR_ALIAS_ID"
    echo "  aws bedrock-agent-runtime invoke-agent \\"
    echo "    --agent-id \$SUPERVISOR_ID \\"
    echo "    --agent-alias-id \$SUPERVISOR_ALIAS_ID \\"
    echo "    --session-id job-\$(date +%s) \\"
    echo "    --input-text \"Build a friend agent for emotional support\" \\"
    echo "    --enable-trace \\"
    echo "    --region $REGION \\"
    echo "    --profile $PROFILE \\"
    echo "    output.json"
    echo ""
    echo "To monitor logs:"
    echo "  # Supervisor agent logs:"
    echo "  aws logs tail $SUPERVISOR_LOG_GROUP --follow --region $REGION --profile $PROFILE"
    echo ""
    echo "  # Model invocation logs:"
    echo "  aws logs tail $MODEL_LOG_GROUP --follow --region $REGION --profile $PROFILE"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Supervisor CloudFormation stack deployment failed${NC}"
    echo ""
    echo "Check the CloudFormation console for details:"
    echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
    exit 1
fi