#!/bin/bash
# Script to package shared libraries as a Lambda Layer

set -e

echo "Packaging AutoNinja shared libraries as Lambda Layer..."

# Create temporary directory for layer structure
LAYER_DIR="build/lambda-layer"
rm -rf "$LAYER_DIR"
mkdir -p "$LAYER_DIR/python"

# Copy shared libraries to python/ directory (Lambda Layer convention)
echo "Copying shared libraries..."
cp -r shared "$LAYER_DIR/python/"

# Install dependencies if requirements.txt exists
if [ -f "shared/requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r shared/requirements.txt -t "$LAYER_DIR/python/" --upgrade
fi

# Create ZIP file
echo "Creating ZIP archive..."
cd "$LAYER_DIR"
zip -r ../autoninja-shared-layer.zip python/
cd ../..

echo "Lambda Layer package created: build/autoninja-shared-layer.zip"
echo "Size: $(du -h build/autoninja-shared-layer.zip | cut -f1)"

# Upload to S3 if bucket name is provided
if [ ! -z "$S3_BUCKET" ]; then
    echo "Uploading to S3 bucket: $S3_BUCKET"
    aws s3 cp build/autoninja-shared-layer.zip "s3://$S3_BUCKET/layers/autoninja-shared-layer.zip" \
        --sse aws:kms \
        ${AWS_REGION:+--region "$AWS_REGION"} \
        ${AWS_PROFILE:+--profile "$AWS_PROFILE"}
    echo "Upload complete!"
else
    echo "To upload to S3, set S3_BUCKET environment variable and run again"
fi
