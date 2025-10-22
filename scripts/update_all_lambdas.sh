#!/bin/bash

# Update all Lambda functions with latest code
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-AdministratorAccess-784327326356}"
ENVIRONMENT="${ENVIRONMENT:-production}"
DEPLOYMENT_BUCKET="autoninja-deployment-artifacts-${REGION}"

echo -e "${YELLOW}=== Updating All Lambda Functions ===${NC}"
echo "Region: $REGION"
echo "Profile: $PROFILE"
echo "Environment: $ENVIRONMENT"
echo ""

# List of all Lambda functions to update
LAMBDAS=(
    "autoninja-supervisor-production:supervisor-agentcore"
    "autoninja-requirements-analyst-production:requirements-analyst"
    "autoninja-code-generator-production:code-generator"
    "autoninja-solution-architect-production:solution-architect"
    "autoninja-quality-validator-production:quality-validator"
    "autoninja-deployment-manager-production:deployment-manager"
)

# Update each Lambda function
for lambda_info in "${LAMBDAS[@]}"; do
    IFS=':' read -r function_name s3_key <<< "$lambda_info"
    
    echo -e "${YELLOW}Updating $function_name...${NC}"
    
    # Update Lambda function code from S3
    aws lambda update-function-code \
        --function-name "$function_name" \
        --s3-bucket "$DEPLOYMENT_BUCKET" \
        --s3-key "lambda/${s3_key}.zip" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --no-cli-pager
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Updated $function_name${NC}"
        
        # Wait for update to complete
        echo "  Waiting for update to complete..."
        aws lambda wait function-updated \
            --function-name "$function_name" \
            --profile "$PROFILE" \
            --region "$REGION"
        
        echo -e "${GREEN}  ✓ Update completed${NC}"
    else
        echo -e "${RED}✗ Failed to update $function_name${NC}"
    fi
    
    echo ""
done

echo -e "${GREEN}=== All Lambda Functions Updated! ===${NC}"
echo ""
echo "All Lambda functions now have:"
echo "  • Raw request/response logging"
echo "  • Fixed rate limiter API calls"
echo "  • Improved error handling"
echo "  • Shared utilities included"
echo ""
echo "Ready to test with: ./tests/supervisor/test_e2e.py"