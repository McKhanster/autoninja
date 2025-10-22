# Technology Stack

## Core Technologies

- **Language**: Python 3.12
- **Cloud Platform**: AWS (us-east-2 primary region)
- **Infrastructure**: CloudFormation (nested stacks)
- **AI/ML**: AWS Bedrock Agents with Claude Sonnet 4.5 (`us.anthropic.claude-3-7-sonnet-20250219-v1:0`)
- **Compute**: AWS Lambda (Python 3.12 runtime)
- **Storage**: DynamoDB (inference records), S3 (artifacts)
- **Orchestration**: Bedrock AgentCore Runtime (supervisor agent)

## Key AWS Services

- **Bedrock Agents**: Multi-agent collaboration with supervisor-collaborator pattern
- **Lambda**: Serverless compute for agent action groups
- **DynamoDB**: Audit trail and inference record persistence
- **S3**: Artifact storage (code, configs, templates)
- **CloudWatch**: Logging and monitoring
- **X-Ray**: Distributed tracing
- **IAM**: Least-privilege security policies

## Python Dependencies

Core dependencies (see `shared/requirements.txt`):
- `boto3>=1.34.0` - AWS SDK
- `botocore>=1.34.0` - AWS SDK core

Development dependencies (see `pyproject.toml`):
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `black>=23.0.0` - Code formatting
- `flake8>=6.0.0` - Linting
- `mypy>=1.5.0` - Type checking

## Project Structure

- **Lambda Layer**: Shared libraries packaged as Lambda Layer (`shared/`)
- **Lambda Functions**: One per collaborator agent (`lambda/*/handler.py`)
- **OpenAPI Schemas**: Action group definitions (`schemas/*.yaml`)
- **CloudFormation**: Nested stack architecture (`infrastructure/cloudformation/`)

## Common Commands

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r shared/requirements.txt

# Set AWS environment
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356
export DYNAMODB_TABLE_NAME=autoninja-inference-records-production
export S3_BUCKET_NAME=autoninja-artifacts-784327326356-production
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific agent tests
python tests/requirements-analyst/test_requirements_analyst_agent.py

# Run with coverage
pytest tests/ --cov=lambda --cov=shared
```

### Code Quality
```bash
# Format code
black lambda/ shared/ tests/ --line-length 100

# Lint code
flake8 lambda/ shared/ tests/ --max-line-length 100

# Type check
mypy lambda/ shared/
```

### Building & Packaging
```bash
# Package Lambda Layer (shared libraries)
./scripts/package_lambda_layer.sh

# Upload OpenAPI schemas to S3
./scripts/upload_schemas.sh

# Package individual Lambda function
cd lambda/requirements-analyst && zip -r ../../build/requirements-analyst.zip .
```

### Deployment
```bash
# Deploy individual agent
./scripts/deploy_requirements_analyst.sh
./scripts/deploy_code_generator.sh

# Deploy entire system
./scripts/deploy_all.sh

# Deploy with auto-confirmation
export AUTO_DEPLOY=true && ./scripts/deploy_all.sh

# Deploy CloudFormation manually
aws cloudformation deploy \
  --template-file infrastructure/cloudformation/autoninja-main.yaml \
  --stack-name autoninja-production \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2
```

## Configuration

Environment variables used across Lambda functions:
- `DYNAMODB_TABLE_NAME` - DynamoDB table for inference records
- `S3_BUCKET_NAME` - S3 bucket for artifacts
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `AWS_REGION` - AWS region (default: us-east-2)
