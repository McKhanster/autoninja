#!/bin/bash
# Cleanup script for AutoNinja supervisor agent resources
# Removes the supervisor agent CloudFormation stack and related resources

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
SUPERVISOR_STACK_NAME="autoninja-supervisor-${ENVIRONMENT}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    AUTONINJA SUPERVISOR CLEANUP                                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Profile: $PROFILE"
echo "  Environment: $ENVIRONMENT"
echo "  AWS Account ID: $AWS_ACCOUNT_ID"
echo "  Supervisor Stack: $SUPERVISOR_STACK_NAME"
echo ""

# Check if supervisor stack exists
echo -e "${YELLOW}Step 1: Checking if supervisor stack exists...${NC}"
if ! aws cloudformation describe-stacks --stack-name "$SUPERVISOR_STACK_NAME" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1; then
    echo -e "${YELLOW}Supervisor stack '$SUPERVISOR_STACK_NAME' not found. Nothing to clean up.${NC}"
    exit 0
fi

# Get supervisor stack status
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].StackStatus' \
    --output text)

echo -e "${GREEN}✓ Supervisor stack found (Status: $STACK_STATUS)${NC}"
echo ""

# Get supervisor agent details before deletion
echo -e "${YELLOW}Step 2: Getting supervisor agent details...${NC}"
SUPERVISOR_ID=$(aws cloudformation describe-stacks \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentId`].OutputValue' \
    --output text 2>/dev/null || echo "")

SUPERVISOR_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentAliasId`].OutputValue' \
    --output text 2>/dev/null || echo "")

# Check if supervisor created its own AgentCore Memory
MEMORY_ID=$(aws cloudformation describe-stacks \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreMemoryId`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -n "$SUPERVISOR_ID" ]; then
    echo -e "    ${GREEN}✓${NC} Supervisor Agent ID: $SUPERVISOR_ID"
    if [ -n "$SUPERVISOR_ALIAS_ID" ]; then
        echo -e "    ${GREEN}✓${NC} Supervisor Alias ID: $SUPERVISOR_ALIAS_ID"
    fi
    if [ -n "$MEMORY_ID" ]; then
        echo -e "    ${GREEN}✓${NC} AgentCore Memory ID: $MEMORY_ID"
    fi
else
    echo -e "    ${YELLOW}Warning: Could not retrieve supervisor agent details${NC}"
fi
echo ""

# Delete supervisor CloudFormation stack
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 3: Deleting supervisor CloudFormation stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "This will delete:"
echo "  • Supervisor Agent (ID: ${SUPERVISOR_ID:-unknown})"
echo "  • Agent Alias (ID: ${SUPERVISOR_ALIAS_ID:-unknown})"
echo "  • IAM roles and policies"
echo "  • CloudWatch log groups"
echo ""

# Confirm deletion
read -p "Are you sure you want to delete the supervisor stack? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deletion cancelled.${NC}"
    exit 0
fi

# Delete the stack
echo -e "${YELLOW}Deleting supervisor stack...${NC}"
aws cloudformation delete-stack \
    --stack-name "$SUPERVISOR_STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Supervisor stack deletion initiated${NC}"
    echo ""
    
    # Wait for deletion to complete
    echo -e "${YELLOW}Waiting for stack deletion to complete...${NC}"
    echo "This may take several minutes..."
    
    aws cloudformation wait stack-delete-complete \
        --stack-name "$SUPERVISOR_STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Supervisor stack deleted successfully${NC}"
        echo ""
        
        # Verify deletion
        echo -e "${YELLOW}Step 4: Verifying deletion...${NC}"
        if ! aws cloudformation describe-stacks --stack-name "$SUPERVISOR_STACK_NAME" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Supervisor stack no longer exists${NC}"
        else
            echo -e "${YELLOW}Warning: Stack still exists, may be in DELETE_FAILED state${NC}"
        fi
        
        echo ""
        echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                    SUPERVISOR CLEANUP COMPLETE!                               ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "Resources cleaned up:"
        echo "  • Supervisor Agent: ${SUPERVISOR_ID:-unknown}"
        echo "  • Agent Alias: ${SUPERVISOR_ALIAS_ID:-unknown}"
        echo "  • CloudFormation stack: $SUPERVISOR_STACK_NAME"
        echo ""
        echo "Note: Collaborator agents are still running."
        echo "To clean up collaborators, run: ./scripts/cleanup_collaborators.sh"
        echo ""
    else
        echo -e "${RED}✗ Stack deletion failed or timed out${NC}"
        echo ""
        echo "Check the CloudFormation console for details:"
        echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
        echo ""
        echo "You may need to manually delete resources that are preventing stack deletion."
        exit 1
    fi
else
    echo -e "${RED}✗ Failed to initiate supervisor stack deletion${NC}"
    echo ""
    echo "Check the CloudFormation console for details:"
    echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
    exit 1
fi