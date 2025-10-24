#!/bin/bash
# Comprehensive cleanup script for AutoNinja
# Removes all resources: buckets, stacks, and artifacts

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
echo -e "${BLUE}║                    AUTONINJA COMPLETE CLEANUP                                  ║${NC}"
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
echo -e "${RED}WARNING: This will delete ALL AutoNinja resources!${NC}"
echo ""

# Confirm deletion
read -p "Are you sure you want to delete everything? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cleanup cancelled.${NC}"
    exit 0
fi
echo ""

# ============================================================================
# Step 1: Empty and Delete Deployment Bucket
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 1: Emptying and deleting deployment bucket...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

if aws s3 ls "s3://${DEPLOYMENT_BUCKET}" --region "$REGION" --profile "$PROFILE" 2>&1 >/dev/null; then
    echo "Emptying bucket: $DEPLOYMENT_BUCKET"
    aws s3 rm "s3://${DEPLOYMENT_BUCKET}" \
        --recursive \
        --region "$REGION" \
        --profile "$PROFILE"
    
    echo "Deleting bucket: $DEPLOYMENT_BUCKET"
    aws s3api delete-bucket \
        --bucket "$DEPLOYMENT_BUCKET" \
        --region "$REGION" \
        --profile "$PROFILE"
    
    echo -e "${GREEN}✓ Deployment bucket deleted${NC}"
else
    echo -e "${YELLOW}Deployment bucket not found, skipping${NC}"
fi
echo ""

# ============================================================================
# Step 2: Delete Supervisor Stack
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 2: Deleting supervisor stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

if aws cloudformation describe-stacks --stack-name "$SUPERVISOR_STACK_NAME" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1; then
    echo "Deleting stack: $SUPERVISOR_STACK_NAME"
    aws cloudformation delete-stack \
        --stack-name "$SUPERVISOR_STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE"
    
    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete \
        --stack-name "$SUPERVISOR_STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Supervisor stack deleted${NC}"
else
    echo -e "${YELLOW}Supervisor stack not found, skipping${NC}"
fi
echo ""

# ============================================================================
# Step 3: Delete Collaborators Stack
# ============================================================================
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 3: Deleting collaborators stack...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

if aws cloudformation describe-stacks --stack-name "$COLLABORATORS_STACK_NAME" --region "$REGION" --profile "$PROFILE" >/dev/null 2>&1; then
    echo "Deleting stack: $COLLABORATORS_STACK_NAME"
    aws cloudformation delete-stack \
        --stack-name "$COLLABORATORS_STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE"
    
    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete \
        --stack-name "$COLLABORATORS_STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Collaborators stack deleted${NC}"
else
    echo -e "${YELLOW}Collaborators stack not found, skipping${NC}"
fi
echo ""

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    CLEANUP COMPLETE!                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "All AutoNinja resources have been deleted:"
echo "  ✓ Deployment bucket: $DEPLOYMENT_BUCKET"
echo "  ✓ Supervisor stack: $SUPERVISOR_STACK_NAME"
echo "  ✓ Collaborators stack: $COLLABORATORS_STACK_NAME"
echo ""