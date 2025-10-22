#!/bin/bash

# Deploy All Infrastructure Stacks
# This script deploys all AutoNinja deployment infrastructure in the correct order

set -e

# Configuration
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-AdministratorAccess-784327326356}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-784327326356}"

# Check for required environment variables
if [ -z "$DASHBOARD_PASSWORD" ]; then
  echo "Error: DASHBOARD_PASSWORD environment variable is required"
  echo "Usage: DASHBOARD_PASSWORD=your-secure-password ./deploy_all.sh"
  exit 1
fi

echo "=========================================="
echo "AutoNinja Infrastructure Deployment"
echo "=========================================="
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo "=========================================="
echo ""

# Step 1: Deploy Frontend Infrastructure
echo "Step 1/2: Deploying Frontend Infrastructure..."
./ops/scripts/deploy_frontend_infrastructure.sh
echo ""

# Step 2: Deploy CI/CD Pipeline
echo "Step 2/2: Deploying CI/CD Pipeline..."
./ops/scripts/deploy_cicd_pipeline.sh
echo ""

echo "=========================================="
echo "All Stacks Deployed Successfully!"
echo "=========================================="
echo ""
echo "Summary:"
echo "1. Frontend Infrastructure: autoninja-frontend-infrastructure"
echo "2. CI/CD Pipeline: autoninja-cicd-pipeline"
echo ""
echo "Next steps:"
echo "1. Configure GitHub connection in CodePipeline (if needed)"
echo "2. Push code to GitHub repository"
echo "3. Monitor pipeline execution"
echo "4. Access frontend at the Amplify URL"
