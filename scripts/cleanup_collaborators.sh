#!/bin/bash
# Cleanup script for AutoNinja collaborators stack
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
ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ENVIRONMENT="${ENVIRONMENT:-production}"
STACK_NAME="autoninja-collaborators-${ENVIRONMENT}"
DEPLOYMENT_BUCKET="autoninja-deployment-artifacts-${REGION}"
ARTIFACTS_BUCKET="autoninja-artifacts-${ACCOUNT_ID}-${ENVIRONMENT}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AUTONINJA COLLABORATORS CLEANUP SCRIPT                                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Profile: $PROFILE"
echo "  Account ID: $ACCOUNT_ID"
echo "  Environment: $ENVIRONMENT"
echo "  Stack Name: $STACK_NAME"
echo "  Deployment Bucket: $DEPLOYMENT_BUCKET"
echo "  Artifacts Bucket: $ARTIFACTS_BUCKET"
echo ""

# Function to empty a versioned S3 bucket
empty_bucket() {
    local BUCKET=$1
    echo -e "${YELLOW}Emptying bucket: $BUCKET${NC}"
    
    # Check if bucket exists
    if ! aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" --profile "$PROFILE" 2>/dev/null; then
        echo -e "${GREEN}  ✓ Bucket does not exist or already deleted${NC}"
        return 0
    fi
    
    # Delete all object versions
    echo "  Deleting object versions..."
    aws s3api list-object-versions \
        --bucket "$BUCKET" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --output json \
        --query 'Versions[].{Key:Key,VersionId:VersionId}' 2>/dev/null | \
    jq -r '.[]? | "--key \"\(.Key)\" --version-id \"\(.VersionId)\""' | \
    while read -r args; do
        if [ -n "$args" ]; then
            aws s3api delete-object \
                --bucket "$BUCKET" \
                --region "$REGION" \
                --profile "$PROFILE" \
                $args 2>/dev/null || true
        fi
    done
    
    # Delete all delete markers
    echo "  Deleting delete markers..."
    aws s3api list-object-versions \
        --bucket "$BUCKET" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --output json \
        --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' 2>/dev/null | \
    jq -r '.[]? | "--key \"\(.Key)\" --version-id \"\(.VersionId)\""' | \
    while read -r args; do
        if [ -n "$args" ]; then
            aws s3api delete-object \
                --bucket "$BUCKET" \
                --region "$REGION" \
                --profile "$PROFILE" \
                $args 2>/dev/null || true
        fi
    done
    
    # Delete any remaining objects (non-versioned)
    echo "  Deleting remaining objects..."
    aws s3 rm "s3://$BUCKET" --recursive --region "$REGION" --profile "$PROFILE" 2>/dev/null || true
    
    echo -e "${GREEN}  ✓ Bucket emptied${NC}"
}

# Function to delete a bucket
delete_bucket() {
    local BUCKET=$1
    echo -e "${YELLOW}Deleting bucket: $BUCKET${NC}"
    
    if aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" --profile "$PROFILE" 2>/dev/null; then
        aws s3 rb "s3://$BUCKET" --region "$REGION" --profile "$PROFILE" 2>/dev/null || true
        echo -e "${GREEN}  ✓ Bucket deleted${NC}"
    else
        echo -e "${GREEN}  ✓ Bucket does not exist${NC}"
    fi
}

# Step 1: Empty and delete S3 buckets
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 1: Emptying and deleting S3 buckets${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Empty artifacts bucket (created by storage stack)
empty_bucket "$ARTIFACTS_BUCKET"
delete_bucket "$ARTIFACTS_BUCKET"

echo ""

# Empty deployment bucket (created by deploy script)
empty_bucket "$DEPLOYMENT_BUCKET"
delete_bucket "$DEPLOYMENT_BUCKET"

echo ""

# Step 2: Delete the collaborators CloudFormation stack (which will delete nested stacks)
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 2: Deleting collaborators CloudFormation stack${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if stack exists
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_STATUS" = "DOES_NOT_EXIST" ]; then
    echo -e "${GREEN}✓ Stack does not exist${NC}"
else
    echo "Current stack status: $STACK_STATUS"
    
    # If stack is in ROLLBACK_COMPLETE, we need to delete it
    if [ "$STACK_STATUS" = "ROLLBACK_COMPLETE" ] || [ "$STACK_STATUS" = "CREATE_FAILED" ] || [ "$STACK_STATUS" = "DELETE_FAILED" ]; then
        echo "Stack is in $STACK_STATUS state, deleting..."
    fi
    
    echo "Deleting stack: $STACK_NAME"
    aws cloudformation delete-stack \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$PROFILE" 2>/dev/null || echo "Stack deletion initiated or already in progress"
    
    echo "Waiting for stack deletion to complete..."
    echo "(This may take several minutes as nested stacks are deleted)"
    
    # Wait for deletion with timeout
    WAIT_COUNT=0
    MAX_WAIT=60  # 60 iterations * 10 seconds = 10 minutes max
    
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        CURRENT_STATUS=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --profile "$PROFILE" \
            --query 'Stacks[0].StackStatus' \
            --output text 2>/dev/null || echo "DELETE_COMPLETE")
        
        if [ "$CURRENT_STATUS" = "DELETE_COMPLETE" ]; then
            echo -e "${GREEN}✓ Stack deleted successfully${NC}"
            break
        elif [ "$CURRENT_STATUS" = "DELETE_FAILED" ]; then
            echo -e "${RED}✗ Stack deletion failed${NC}"
            echo "Check the CloudFormation console for details:"
            echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
            exit 1
        fi
        
        echo "  Status: $CURRENT_STATUS (waiting...)"
        sleep 10
        WAIT_COUNT=$((WAIT_COUNT + 1))
    done
    
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
        echo -e "${YELLOW}Warning: Stack deletion is taking longer than expected${NC}"
        echo "Check the CloudFormation console for progress:"
        echo "  https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
    fi
fi

echo ""

# Step 3: Clean up generated template file
echo -e "${YELLOW}Step 3: Cleaning up generated files${NC}"
if [ -f "infrastructure/cloudformation/autoninja-collaborators.yaml" ]; then
    rm -f infrastructure/cloudformation/autoninja-collaborators.yaml
    echo -e "${GREEN}✓ Removed generated collaborators template${NC}"
else
    echo -e "${GREEN}✓ No generated template to remove${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    COLLABORATORS CLEANUP COMPLETE!                            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "All AutoNinja collaborators resources have been cleaned up:"
echo "  • S3 buckets emptied and deleted"
echo "    - Artifacts bucket: $ARTIFACTS_BUCKET"
echo "    - Deployment bucket: $DEPLOYMENT_BUCKET"
echo "  • CloudFormation stack and nested stacks deleted"
echo "    - Storage stack (DynamoDB tables, S3 bucket)"
echo "    - Lambda Layer stack"
echo "    - Custom Orchestration stack"
echo "    - 5 Collaborator agent stacks"
echo "  • Generated template files removed"
echo ""
echo "Resources cleaned up include:"
echo "  • 5 Bedrock Agents (Requirements Analyst, Code Generator, Solution Architect, Quality Validator, Deployment Manager)"
echo "  • 5 Lambda functions"
echo "  • 1 Lambda Layer"
echo "  • 2 DynamoDB tables (inference records + rate limiter)"
echo "  • IAM roles and policies"
echo "  • CloudWatch log groups"
echo ""