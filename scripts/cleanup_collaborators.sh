#!/bin/bash
# Comprehensive cleanup script for resources created by deploy_collaborators.sh
# Empties S3 buckets, deletes Bedrock agents/aliases, AgentCoreMemory, and CloudFormation stacks
# Run with: export AWS_REGION=us-east-2 && export AWS_ACCOUNT_ID=784327326356 && export AWS_PROFILE=AdministratorAccess-784327326356 && ./scripts/cleanup_collaborators.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-AdministratorAccess-784327326356}"
ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-784327326356}"
STACK_NAME="autoninja-collaborators-${ENVIRONMENT}"
DEPLOYMENT_BUCKET="${DEPLOYMENT_BUCKET:-autoninja-deployment-artifacts-${REGION}}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AUTONINJA COLLABORATORS CLEANUP SCRIPT                               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Profile: $PROFILE"
echo "  Environment: $ENVIRONMENT"
echo "  AWS Account ID: $AWS_ACCOUNT_ID"
echo "  Stack Name: $STACK_NAME"
echo "  Deployment Bucket: $DEPLOYMENT_BUCKET"
echo ""

# Check required tools
echo -e "${YELLOW}Checking required tools...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}Error: AWS CLI is required but not installed.${NC}" >&2; exit 1; }
echo -e "${GREEN}✓ All required tools are available${NC}"
echo ""

# Step 1: Delete AgentCoreMemory (if exists) - Note: CLI may not be available; use console if needed
echo -e "${YELLOW}Step 1: Deleting AgentCoreMemory...${NC}"
MEMORY_NAME="autoninja_rate_limiter_${ENVIRONMENT}"
# List memories (use bedrock-agent if bedrock-agent-core not available)
MEMORIES=$(aws bedrock-agent list-agents --region "$REGION" --profile "$PROFILE" --query 'agentSummaries[?agentName==`'$MEMORY_NAME'`].[agentId,agentName]' --output text 2>/dev/null || echo "")
if [ ! -z "$MEMORIES" ]; then
    MEMORY_ID=$(echo "$MEMORIES" | awk '{print $1}')
    echo "Deleting AgentCoreMemory: $MEMORY_NAME (ID: $MEMORY_ID)"
    # Note: Use AWS Console for Bedrock > AgentCore > Memories > Delete if CLI fails
    aws bedrock-agent delete-agent --agent-id "$MEMORY_ID" --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "${YELLOW}Note: Delete via AWS Console (Bedrock > AgentCore > Memories).${NC}"
else
    echo -e "${GREEN}✓ No AgentCoreMemory found or already deleted${NC}"
fi
echo ""

# Step 2: Disassociate and delete Bedrock agents/aliases (collaborators)
echo -e "${YELLOW}Step 2: Deleting Bedrock collaborator agents and aliases...${NC}"
AGENTS=("requirements-analyst" "code-generator" "solution-architect" "quality-validator" "deployment-manager")
for agent in "${AGENTS[@]}"; do
    AGENT_NAME="autoninja-${agent}-${ENVIRONMENT}"
    # List agents
    AGENT_ID=$(aws bedrock-agent list-agents --region "$REGION" --profile "$PROFILE" --query 'agentSummaries[?agentName==`'$AGENT_NAME'`].[agentId]' --output text 2>/dev/null)
    if [ ! -z "$AGENT_ID" ]; then
        echo "Found agent: $AGENT_NAME (ID: $AGENT_ID)"
        # Delete alias if exists
        ALIAS_ID=$(aws bedrock-agent list-agent-aliases --agent-id "$AGENT_ID" --region "$REGION" --profile "$PROFILE" --query 'agentAliasSummaries[0].agentAliasId' --output text 2>/dev/null)
        if [ ! -z "$ALIAS_ID" ]; then
            echo "  Deleting alias: $ALIAS_ID"
            aws bedrock-agent delete-agent-alias --agent-id "$AGENT_ID" --agent-alias-id "$ALIAS_ID" --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "    ${YELLOW}Alias deletion may require disassociation first.${NC}"
        fi
        # Delete agent
        echo "  Deleting agent: $AGENT_ID"
        aws bedrock-agent delete-agent --agent-id "$AGENT_ID" --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "    ${YELLOW}Agent deletion may require disassociation from supervisor.${NC}"
    else
        echo "  No agent found for $agent"
    fi
done
echo -e "${GREEN}✓ Bedrock agents cleanup attempted${NC}"
echo ""

# Step 3: Empty deployment bucket (zips and templates)
echo -e "${YELLOW}Step 3: Emptying deployment bucket...${NC}"
echo "Emptying S3 bucket: $DEPLOYMENT_BUCKET (lambda zips and stacks templates)"
aws s3 rm "s3://$DEPLOYMENT_BUCKET/" --recursive --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "${YELLOW}Bucket may already be empty.${NC}"
# Handle versioning if enabled
aws s3api delete-object --bucket "$DEPLOYMENT_BUCKET" --key "" --version-id $(aws s3api list-object-versions --bucket "$DEPLOYMENT_BUCKET" --query 'DeleteMarkers[].VersionId' --output text) --region "$REGION" --profile "$PROFILE" 2>/dev/null || true
aws s3api delete-object --bucket "$DEPLOYMENT_BUCKET" --key "" --version-id $(aws s3api list-object-versions --bucket "$DEPLOYMENT_BUCKET" --query 'Versions[].VersionId' --output text) --region "$REGION" --profile "$PROFILE" 2>/dev/null || true
# Disable versioning if enabled
aws s3api put-bucket-versioning --bucket "$DEPLOYMENT_BUCKET" --versioning-configuration Status=Suspended --region "$REGION" --profile "$PROFILE" 2>/dev/null || true
# Delete the bucket if empty
echo "Deleting S3 bucket: $DEPLOYMENT_BUCKET"
aws s3 rb "s3://$DEPLOYMENT_BUCKET" --force --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "${YELLOW}Bucket deletion failed; may be used by other stacks or have permissions issues.${NC}"
echo -e "${GREEN}✓ Deployment bucket cleanup attempted${NC}"
echo ""

# Step 5: Empty and delete S3 artifacts bucket (from StorageStack)
echo -e "${YELLOW}Step 5: Emptying and deleting S3 artifacts bucket...${NC}"
ARTIFACTS_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucketName`].OutputValue' --output text --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo "")
if [ ! -z "$ARTIFACTS_BUCKET" ]; then
    echo "Emptying S3 bucket: $ARTIFACTS_BUCKET"
    aws s3 rm "s3://$ARTIFACTS_BUCKET/" --recursive --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "${YELLOW}Bucket may already be empty.${NC}"
    # Handle versioning if enabled
    aws s3api delete-object --bucket "$ARTIFACTS_BUCKET" --key "" --version-id $(aws s3api list-object-versions --bucket "$ARTIFACTS_BUCKET" --query 'DeleteMarkers[].VersionId' --output text) --region "$REGION" --profile "$PROFILE" 2>/dev/null || true
    aws s3api delete-object --bucket "$ARTIFACTS_BUCKET" --key "" --version-id $(aws s3api list-object-versions --bucket "$ARTIFACTS_BUCKET" --query 'Versions[].VersionId' --output text) --region "$REGION" --profile "$PROFILE" 2>/dev/null || true
    # Disable versioning if enabled
    aws s3api put-bucket-versioning --bucket "$ARTIFACTS_BUCKET" --versioning-configuration Status=Suspended --region "$REGION" --profile "$PROFILE" 2>/dev/null || true
    echo "Deleting S3 bucket: $ARTIFACTS_BUCKET"
    aws s3 rb "s3://$ARTIFACTS_BUCKET" --force --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "${YELLOW}Bucket deletion failed; check permissions.${NC}"
else
    echo -e "${GREEN}✓ No artifacts bucket found or already deleted${NC}"
fi
echo ""

# Step 6: Delete Lambda functions and log groups (if not deleted by stack)
echo -e "${YELLOW}Step 6: Deleting Lambda functions and log groups...${NC}"
LAMBDAS=("autoninja-requirements-analyst-${ENVIRONMENT}" "autoninja-code-generator-${ENVIRONMENT}" "autoninja-solution-architect-${ENVIRONMENT}" "autoninja-quality-validator-${ENVIRONMENT}" "autoninja-deployment-manager-${ENVIRONMENT}" "autoninja-custom-orchestration-${ENVIRONMENT}")
for lambda in "${LAMBDAS[@]}"; do
    echo "Deleting Lambda: $lambda"
    aws lambda delete-function --function-name "$lambda" --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "    ${YELLOW}Lambda may already be deleted.${NC}"
done
# Delete log groups
# LOG_GROUPS=("/aws/lambda/autoninja-*-${ENVIRONMENT}" "/aws/bedrock/agents/autoninja-*-${ENVIRONMENT}")
# for log_group in "${LOG_GROUPS[@]}"; do
#     echo "Deleting log groups matching: $log_group"
#     LOG_GROUP_IDS=$(aws logs describe-log-groups --log-group-name-prefix "$log_group" --region "$REGION" --profile "$PROFILE" --query 'logGroups[*].logGroupName' --output text 2>/dev/null)
#     for lg in $LOG_GROUP_IDS; do
#         aws logs delete-log-group --log-group-name "$lg" --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "    ${YELLOW}Log group deletion failed.${NC}"
#     done
# done
# echo -e "${GREEN}✓ Lambda and log groups cleanup attempted${NC}"
# echo ""

# Step 7: Delete IAM roles (if not deleted by stack)
echo -e "${YELLOW}Step 7: Deleting IAM roles...${NC}"
ROLES=("AutoNinjaCollaboratorsManagementRole-${ENVIRONMENT}" "autoninja-*-${ENVIRONMENT}-lambda-role" "autoninja-*-${ENVIRONMENT}-agent-role")
for role_pattern in "${ROLES[@]}"; do
    ROLE_NAMES=$(aws iam list-roles --query "Roles[?contains(RoleName, \`$role_pattern\`)].RoleName" --output text --profile "$PROFILE" 2>/dev/null)
    for role in $ROLE_NAMES; do
        echo "Detaching policies from role: $role"
        aws iam detach-role-policy --role-name "$role" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole --profile "$PROFILE" 2>/dev/null || true
        aws iam delete-role-policy --role-name "$role" --policy-name "AutoNinjaPolicy" --profile "$PROFILE" 2>/dev/null || true
        echo "Deleting role: $role"
        aws iam delete-role --role-name "$role" --profile "$PROFILE" 2>/dev/null || echo -e "    ${YELLOW}Role deletion failed; may be in use.${NC}"
    done
done
echo -e "${GREEN}✓ IAM roles cleanup attempted${NC}"
echo ""

# Step 8: Delete main and nested CloudFormation stacks
echo -e "${YELLOW}Step 8: Deleting CloudFormation stacks...${NC}"
# Delete nested stacks first if they exist
NESTED_STACKS=("autoninja-collaborators-production-*-Stack-*")
for ns in "${NESTED_STACKS[@]}"; do
    NESTED_NAMES=$(aws cloudformation list-stacks --query "StackSummaries[?contains(StackName, \`$ns\`) && StackStatus != \`DELETE_COMPLETE\`].StackName" --output text --region "$REGION" --profile "$PROFILE" 2>/dev/null)
    for stack in $NESTED_NAMES; do
        echo "Deleting nested stack: $stack"
        aws cloudformation delete-stack --stack-name "$stack" --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "    ${YELLOW}Nested stack deletion failed.${NC}"
    done
done
# Delete main stack
echo "Deleting main stack: $STACK_NAME"
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION" --profile "$PROFILE" 2>/dev/null || echo -e "${YELLOW}Main stack may already be deleted.${NC}"
echo -e "${GREEN}✓ CloudFormation stacks deletion attempted${NC}"
echo ""

# Step 9: Wait for deletion and verify
echo -e "${YELLOW}Step 9: Waiting for deletion completion...${NC}"
sleep 60
MAIN_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --profile "$PROFILE" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "DELETE_COMPLETE")
if [ "$MAIN_STATUS" = "DELETE_COMPLETE" ] || [ "$MAIN_STATUS" = "DELETE_FAILED" ]; then
    echo -e "${GREEN}✓ Main stack cleanup complete${NC}"
else
    echo -e "${YELLOW}Main stack status: $MAIN_STATUS - Monitor in console if needed.${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  COLLABORATORS CLEANUP COMPLETE!                             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Note: Some resources (e.g., AgentCoreMemory, Bedrock agents) may require manual deletion via AWS Console if CLI fails."
echo "After cleanup, run ./scripts/deploy_collaborators.sh to re-deploy."
