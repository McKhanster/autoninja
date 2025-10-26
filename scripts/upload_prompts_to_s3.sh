#!/bin/bash

# Upload prompts to S3 script
# Usage: ./upload_prompts_to_s3.sh <bucket-name> [environment]

set -e

BUCKET_NAME=${1:-"autoninja-deployment-artifacts-us-east-2"}
ENVIRONMENT=${2:-"production"}
PROMPTS_DIR="infrastructure/cloudformation/prompts"

echo "Uploading prompts to S3 bucket: $BUCKET_NAME"
echo "Environment: $ENVIRONMENT"

# Upload all .md prompt files
for file in $PROMPTS_DIR/*.md; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        s3_key="prompts/$ENVIRONMENT/$filename"
        
        echo "Uploading $filename to s3://$BUCKET_NAME/$s3_key"
        aws s3 cp "$file" "s3://$BUCKET_NAME/$s3_key" \
            --content-type "text/markdown" \
            --metadata "environment=$ENVIRONMENT,type=prompt"
    fi
done

echo "All prompts uploaded successfully!"
echo ""
echo "To use in CloudFormation, reference as:"
echo "  S3Bucket: $BUCKET_NAME"
echo "  S3Key: prompts/$ENVIRONMENT/[prompt-file].md"