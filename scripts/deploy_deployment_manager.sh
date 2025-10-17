#!/bin/bash
# Script to deploy Deployment Manager Lambda function

set -e

# Configuration
FUNCTION_NAME="autoninja-deployment-manager-production"
HANDLER_DIR="lambda/deployment-manager"
BUILD_DIR="build/deployment-manager"
ZIP_FILE="build/deployment-manager.zip"

# Check required environment variables
if [ -z "$AWS_REGION" ]; then
    echo "Error: AWS_REGION environment variable not set"
    exit 1
fi

if [ -z "$AWS_PROFILE" ]; then
    echo "Warning: AWS_PROFILE not set, using default profile"
fi

echo "========================================="
echo "Deploying Deployment Manager Lambda"
echo "========================================="
echo "Function: $FUNCTION_NAME"
echo "Region: $AWS_REGION"
echo "Profile: ${AWS_PROFILE:-default}"
echo ""

# Clean and create build directory
echo "1. Preparing build directory..."
rm -rf "$BUILD_DIR" "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

# Copy handler code
echo "2. Copying handler code..."
cp "$HANDLER_DIR/handler.py" "$BUILD_DIR/"

# Create deployment package
echo "3. Creating deployment package..."
cd "$BUILD_DIR"
zip -r "../$(basename $ZIP_FILE)" .
cd ../..

echo "   Package size: $(du -h $ZIP_FILE | cut -f1)"

# Update Lambda function code
echo "4. Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$AWS_REGION" \
    ${AWS_PROFILE:+--profile "$AWS_PROFILE"} \
    --output json | jq -r '.FunctionArn, .LastModified, .CodeSize'

echo ""
echo "✅ Deployment complete!"
echo ""
echo "To test the function, run:"
echo "  python tests/deployment-manager/test_deployment-manager_agent.py"

