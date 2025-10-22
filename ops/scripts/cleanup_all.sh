#!/bin/bash

# Cleanup All Infrastructure Stacks
# This script deletes all AutoNinja deployment infrastructure in reverse order

set -e

# Configuration
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-AdministratorAccess-784327326356}"

echo "=========================================="
echo "AutoNinja Infrastructure Cleanup"
echo "=========================================="
echo "Region: $REGION"
echo "WARNING: This will delete all deployment infrastructure!"
echo "=========================================="
echo ""

read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Cleanup cancelled."
  exit 0
fi

# Step 1: Delete CI/CD Pipeline (must be deleted first due to dependencies)
echo "Step 1/2: Deleting CI/CD Pipeline..."
aws cloudformation delete-stack \
  --stack-name autoninja-cicd-pipeline \
  --region $REGION \
  --profile $PROFILE

echo "Waiting for CI/CD Pipeline stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name autoninja-cicd-pipeline \
  --region $REGION \
  --profile $PROFILE || echo "Stack may not exist or already deleted"

echo ""

# Step 2: Delete Frontend Infrastructure
echo "Step 2/2: Deleting Frontend Infrastructure..."
aws cloudformation delete-stack \
  --stack-name autoninja-frontend-infrastructure \
  --region $REGION \
  --profile $PROFILE

echo "Waiting for Frontend Infrastructure stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name autoninja-frontend-infrastructure \
  --region $REGION \
  --profile $PROFILE || echo "Stack may not exist or already deleted"

echo ""

echo "=========================================="
echo "All Stacks Deleted Successfully!"
echo "=========================================="
