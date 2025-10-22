#!/bin/bash

# Deploy CI/CD Pipeline Stack
# This script deploys the CodePipeline and CodeBuild infrastructure

set -e

# Configuration
STACK_NAME="autoninja-cicd-pipeline"
TEMPLATE_FILE="ops/cloudformation/cicd-pipeline.yaml"
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-AdministratorAccess-784327326356}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-784327326356}"

# Parameters
ENVIRONMENT="${ENVIRONMENT:-production}"
CODECOMMIT_STACK_NAME="${CODECOMMIT_STACK_NAME:-autoninja-codecommit-repository}"
FRONTEND_STACK_NAME="${FRONTEND_STACK_NAME:-autoninja-frontend-infrastructure}"

echo "=========================================="
echo "Deploying CI/CD Pipeline Stack"
echo "=========================================="
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo "=========================================="

# GitHub repository configuration (using GitHub instead of CodeCommit)
GITHUB_OWNER="${GITHUB_OWNER:-your-github-username}"
GITHUB_REPO="${GITHUB_REPO:-autoninja-bedrock-agents}"
GITHUB_TOKEN="${GITHUB_TOKEN}"

if [ -z "$GITHUB_TOKEN" ]; then
  echo "Warning: GITHUB_TOKEN not set. Pipeline will need manual GitHub connection setup."
fi

echo "GitHub Owner: $GITHUB_OWNER"
echo "GitHub Repo: $GITHUB_REPO"

# Get Amplify App ID from stack outputs
echo "Retrieving Amplify App details..."
AMPLIFY_APP_ID=$(aws cloudformation describe-stacks \
  --stack-name $FRONTEND_STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

echo "Amplify App ID: $AMPLIFY_APP_ID"

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
    AmplifyAppId=$AMPLIFY_APP_ID

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
echo "Pipeline Name:"
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query 'Stacks[0].Outputs[?OutputKey==`PipelineName`].OutputValue' \
  --output text

echo ""
echo "Next steps:"
echo "1. Configure GitHub connection in CodePipeline console (if not using GITHUB_TOKEN)"
echo "2. Push code to GitHub to trigger the pipeline"
echo "3. Monitor pipeline execution in the CodePipeline console"
