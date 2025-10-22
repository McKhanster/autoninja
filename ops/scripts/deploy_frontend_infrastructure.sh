#!/bin/bash

# Deploy Frontend Infrastructure Stack
# This script deploys the AWS Amplify frontend hosting infrastructure

set -e

# Configuration
STACK_NAME="autoninja-frontend-infrastructure"
TEMPLATE_FILE="ops/cloudformation/frontend-infrastructure.yaml"
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-AdministratorAccess-784327326356}"

# Parameters
ENVIRONMENT="${ENVIRONMENT:-production}"
BRANCH_NAME="${BRANCH_NAME:-main}"
DASHBOARD_PASSWORD="${DASHBOARD_PASSWORD}"

# Validate required parameters
if [ -z "$DASHBOARD_PASSWORD" ]; then
  echo "Error: DASHBOARD_PASSWORD environment variable is required"
  echo "Usage: DASHBOARD_PASSWORD=your-secure-password ./deploy_frontend_infrastructure.sh"
  exit 1
fi

echo "=========================================="
echo "Deploying Frontend Infrastructure Stack"
echo "=========================================="
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo "Branch Name: $BRANCH_NAME"
echo "=========================================="

# Validate template
echo "Validating CloudFormation template..."
aws cloudformation validate-template \
  --template-body file://$TEMPLATE_FILE \
  --region $REGION \
  --profile $PROFILE

# Deploy stack
echo "Deploying stack..."
aws cloudformation deploy \
  --template-file $TEMPLATE_FILE \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION \
  --profile $PROFILE \
  --parameter-overrides \
    Environment=$ENVIRONMENT \
    BranchName=$BRANCH_NAME \
    DashboardPassword=$DASHBOARD_PASSWORD

# Get stack outputs
echo "=========================================="
echo "Stack Outputs:"
echo "=========================================="
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Amplify App URL:"
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppUrl`].OutputValue' \
  --output text

echo ""
echo "Next steps:"
echo "1. Build the frontend: cd frontend && npm run build"
echo "2. Deploy to Amplify using the Amplify console or CLI"
