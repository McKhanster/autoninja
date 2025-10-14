#!/bin/bash

# Script to upload OpenAPI schemas to S3 bucket
# Usage: ./scripts/upload_schemas.sh <bucket-name>

set -e

if [ -z "$1" ]; then
    echo "Error: S3 bucket name is required"
    echo "Usage: $0 <bucket-name>"
    exit 1
fi

BUCKET_NAME=$1
SCHEMAS_DIR="schemas"

echo "Uploading OpenAPI schemas to s3://${BUCKET_NAME}/schemas/"

# Upload each schema file with KMS encryption
for schema_file in ${SCHEMAS_DIR}/*.yaml; do
    if [ -f "$schema_file" ]; then
        filename=$(basename "$schema_file")
        echo "Uploading $filename..."
        aws s3 cp "$schema_file" "s3://${BUCKET_NAME}/schemas/$filename" --sse aws:kms
    fi
done

echo "All schemas uploaded successfully!"
echo ""
echo "Uploaded files:"
aws s3 ls "s3://${BUCKET_NAME}/schemas/"
