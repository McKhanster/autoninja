#!/bin/bash

# Deploy CodeCommit Repository Stack
# This script deploys the CodeCommit repository for AutoNinja

set -e

# Configuration
STACK_NAME="autoninja-codecommit-repository"
TEMPLATE_FILE="ops/cloudformation/codecommit-repository.yaml"
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-AdministratorAccess-784327326356}"

# Parameters
ENVIRONMENT="${ENVIRONMENT:-production}"
REPOSITORY_NAME="${REPOSITORY_NAME:-autoninja-bedrock-agents}"
REPOSITORY_DESCRIPTION="${REPOSITORY_DESCRIPTION:-AutoNinja multi-agent Bedrock system for generating production-ready AWS Bedrock Agents}"

echo "=========================================="
echo "Deploying CodeCommit Repository Stack"
echo "=========================================="
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo "Repository Name: $REPOSITORY_NAME"
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
    RepositoryName=$REPOSITORY_NAME \
    RepositoryDescription="$REPOSITORY_DESCRIPTION"

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
echo "Clone URLs:"
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --profile $PROFILE \
  --query 'Stacks[0].Outputs[?OutputKey==`RepositoryCloneUrlHttp`].OutputValue' \
  --output text

echo ""
echo "To configure Git remote:"
echo "git remote add codecommit \$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --profile $PROFILE --query 'Stacks[0].Outputs[?OutputKey==\`RepositoryCloneUrlHttp\`].OutputValue' --output text)"
