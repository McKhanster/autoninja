# Lambda Layer Deployment Guide

This guide explains how to package and deploy the AutoNinja shared libraries as a Lambda Layer.

## Prerequisites

- Python 3.9 or higher
- AWS CLI configured with appropriate credentials
- Access to the S3 bucket specified in your CloudFormation stack

## Step 1: Package the Lambda Layer

Run the packaging script to create the Lambda Layer ZIP file:

```bash
./scripts/package_lambda_layer.sh
```

This will:
1. Create a `build/lambda-layer/python/` directory structure
2. Copy the `shared/` directory into it
3. Install dependencies from `shared/requirements.txt`
4. Create a ZIP file at `build/autoninja-shared-layer.zip`

## Step 2: Upload to S3

Upload the Lambda Layer ZIP to your S3 artifacts bucket:

```bash
# Get your bucket name from CloudFormation outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name autoninja-production \
  --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucketName`].OutputValue' \
  --output text)

# Upload the layer
aws s3 cp build/autoninja-shared-layer.zip \
  s3://${BUCKET_NAME}/layers/autoninja-shared-layer.zip
```

Or use the script with the S3_BUCKET environment variable:

```bash
S3_BUCKET=your-bucket-name ./scripts/package_lambda_layer.sh
```

## Step 3: Update CloudFormation Stack

After uploading the Lambda Layer, update your CloudFormation stack to use it:

```bash
aws cloudformation update-stack \
  --stack-name autoninja-production \
  --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=BedrockModel,ParameterValue=anthropic.claude-sonnet-4-5-20250929-v1:0
```

The stack update will:
1. Create the Lambda Layer from the uploaded ZIP
2. Attach the layer to all 5 Lambda functions
3. Make the shared libraries available at `/opt/python/shared/`

## Step 4: Verify Deployment

Verify that the Lambda Layer is attached to your functions:

```bash
# Check Requirements Analyst function
aws lambda get-function \
  --function-name autoninja-requirements-analyst-production \
  --query 'Configuration.Layers[*].Arn'

# Check all functions
for func in requirements-analyst code-generator solution-architect quality-validator deployment-manager; do
  echo "Checking $func..."
  aws lambda get-function \
    --function-name autoninja-${func}-production \
    --query 'Configuration.Layers[*].Arn'
done
```

## Updating the Lambda Layer

When you make changes to the shared libraries:

1. Package the updated layer:
   ```bash
   ./scripts/package_lambda_layer.sh
   ```

2. Upload to S3:
   ```bash
   aws s3 cp build/autoninja-shared-layer.zip \
     s3://${BUCKET_NAME}/layers/autoninja-shared-layer.zip
   ```

3. Update the CloudFormation stack (this will create a new layer version):
   ```bash
   aws cloudformation update-stack \
     --stack-name autoninja-production \
     --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
     --capabilities CAPABILITY_NAMED_IAM
   ```

## Testing the Lambda Layer

You can test that the shared libraries are accessible in Lambda functions:

```python
# Test script to run in Lambda console
from shared.persistence import DynamoDBClient, S3Client
from shared.utils import generate_job_name, get_logger

def lambda_handler(event, context):
    # Test job name generation
    job_name = generate_job_name("test request")
    print(f"Generated job name: {job_name}")
    
    # Test logger
    logger = get_logger(__name__, job_name=job_name)
    logger.info("Testing shared libraries")
    
    # Test DynamoDB client
    db_client = DynamoDBClient()
    print(f"DynamoDB table: {db_client.table_name}")
    
    # Test S3 client
    s3_client = S3Client()
    print(f"S3 bucket: {s3_client.bucket_name}")
    
    return {"statusCode": 200, "body": "Shared libraries working!"}
```

## Troubleshooting

### Layer not found

If Lambda functions can't find the layer:
- Verify the layer ZIP was uploaded to the correct S3 location
- Check CloudFormation events for errors during stack update
- Verify the layer ARN in the Lambda function configuration

### Import errors

If you get import errors:
- Verify the directory structure is correct: `python/shared/`
- Check that `__init__.py` files exist in all directories
- Verify dependencies are installed in the layer

### Permission errors

If you get permission errors accessing DynamoDB or S3:
- Verify the Lambda execution roles have the correct policies
- Check that environment variables are set correctly
- Verify the DynamoDB table and S3 bucket exist

## Directory Structure

The Lambda Layer should have this structure:

```
autoninja-shared-layer.zip
└── python/
    └── shared/
        ├── __init__.py
        ├── persistence/
        │   ├── __init__.py
        │   ├── dynamodb_client.py
        │   └── s3_client.py
        └── utils/
            ├── __init__.py
            ├── job_generator.py
            └── logger.py
```

## References

- [AWS Lambda Layers Documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Lambda Layer Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
