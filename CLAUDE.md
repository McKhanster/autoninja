# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoNinja is a production-grade, serverless multi-agent system built on AWS Bedrock Agents that transforms natural language requests into fully deployed AI agents. The system uses a supervisor + collaborator pattern with 6 specialized Bedrock Agents orchestrated to design, generate, validate, and deploy production-ready agents.

## Architecture

### Multi-Agent System
- **Supervisor Agent**: Orchestrates the workflow and delegates tasks
- **5 Collaborator Agents**: Requirements Analyst, Solution Architect, Code Generator, Quality Validator, Deployment Manager
- Each collaborator has Lambda functions for action execution
- Complete persistence via DynamoDB (inference records) and S3 (artifacts)

### Key Components
- **Lambda Functions** (`lambda/`): Business logic for each agent action
- **Shared Libraries** (`shared/`): Lambda Layer with common utilities (DynamoDB client, S3 client, logger, models)
- **OpenAPI Schemas** (`schemas/`): Define action groups for Bedrock Agents
- **Infrastructure** (`infrastructure/cloudformation/`): CloudFormation templates for deployment

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r shared/requirements.txt

# Set environment variables
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356
export DYNAMODB_TABLE_NAME=autoninja-inference-records-production
export S3_BUCKET_NAME=autoninja-artifacts-784327326356-production
```

### Testing
```bash
# Run unit tests for specific agent
python tests/requirements-analyst/test_requirements_analyst_agent.py
python tests/code-generator/test_code_generator_agent.py

# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=lambda --cov=shared
```

### Building and Packaging
```bash
# Package Lambda Layer (shared libraries)
./scripts/package_lambda_layer.sh

# Package individual Lambda function
cd lambda/requirements-analyst && zip -r ../../build/requirements-analyst.zip .

# Upload OpenAPI schemas to S3
./scripts/upload_schemas.sh
```

### Deployment
```bash
# Deploy individual agent Lambda function
./scripts/deploy_requirements_analyst.sh
./scripts/deploy_code_generator.sh

# Deploy entire system (packages, uploads, and deploys CloudFormation)
./scripts/deploy_all.sh

# Deploy with auto-deployment (skips confirmation)
export AUTO_DEPLOY=true && ./scripts/deploy_all.sh

# Deploy CloudFormation stack manually
aws cloudformation deploy \
  --template-file infrastructure/cloudformation/autoninja-complete.yaml \
  --stack-name autoninja-production \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2 \
  --profile AdministratorAccess-784327326356
```

### Code Quality
```bash
# Format code with black
black lambda/ shared/ tests/ --line-length 100

# Lint with flake8
flake8 lambda/ shared/ tests/ --max-line-length 100

# Type checking with mypy
mypy lambda/ shared/
```

## Critical Implementation Patterns

### Reference Implementation
**The Requirements Analyst Lambda function (`lambda/requirements-analyst/handler.py`) is the CANONICAL reference implementation.** All other Lambda functions MUST follow its exact patterns. See `.kiro/steering/autoninja-implementation-patterns.md` for detailed patterns.

### DynamoDB Logging Pattern (CRITICAL)
Each action must create exactly ONE DynamoDB record, not two:

```python
# Step 1: Create record and save timestamp
record = dynamodb_client.log_inference_input(
    job_name=job_name,
    session_id=session_id,
    agent_name="your-agent",
    action_name="your-action",
    prompt=json.dumps(event),
    model_id="lambda-function"
)
timestamp = record['timestamp']  # SAVE THIS

# Step 2: Execute business logic
result = your_business_logic()

# Step 3: Update the SAME record (not create new one)
dynamodb_client.log_inference_output(
    job_name=job_name,
    timestamp=timestamp,  # Use saved timestamp
    response=json.dumps(result),
    duration_seconds=time.time() - start_time,
    artifacts_s3_uri=s3_uri,
    status='success'
)
```

### Event Parsing Pattern
Always extract parameters from both `parameters` array and `requestBody.content.application/json.properties`:

```python
api_path = event.get('apiPath', '')
parameters = event.get('parameters', [])
params = {param['name']: param['value'] for param in parameters}

# Also check requestBody
request_body = event.get('requestBody', {})
content = request_body.get('content', {})
json_content = content.get('application/json', {})
properties = json_content.get('properties', [])
for prop in properties:
    if prop['name'] not in params:
        params[prop['name']] = prop['value']

job_name = params.get('job_name', 'unknown')
```

### Response Format
Always return responses in this exact Bedrock Agent format:

```python
return {
    'messageVersion': '1.0',
    'response': {
        'actionGroup': event.get('actionGroup'),
        'apiPath': event.get('apiPath'),
        'httpMethod': event.get('httpMethod', 'POST'),
        'httpStatusCode': 200,
        'responseBody': {
            'application/json': {
                'body': json.dumps({
                    'job_name': job_name,
                    'your_data': your_data,
                    'status': 'success'
                })
            }
        }
    }
}
```

### S3 Artifact Saving
Always save both raw and converted artifacts:

```python
# Save raw response
s3_client.save_raw_response(
    job_name=job_name,
    phase='requirements',  # or 'code', 'architecture', 'validation', 'deployment'
    agent_name='your-agent',
    response=result,
    filename='your_action_raw_response.json'
)

# Save converted artifact
s3_client.save_converted_artifact(
    job_name=job_name,
    phase='requirements',
    agent_name='your-agent',
    artifact=converted_data,
    filename='your_artifact.json',
    content_type='application/json'
)
```

### Error Handling
Always log errors to DynamoDB before returning error response:

```python
except Exception as e:
    logger.error(f"Error: {str(e)}")

    if job_name and timestamp:
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )

    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup'),
            'apiPath': event.get('apiPath'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 500,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({'error': str(e), 'status': 'error'})
                }
            }
        }
    }
```

## Data Persistence Architecture

### Job Naming Convention
Jobs are identified by unique job names: `job-{keyword}-{YYYYMMDD}-{HHMMSS}`
Example: `job-friend-20251013-143022`

### DynamoDB Schema
Table: `autoninja-inference-records-production`
- Partition Key: `job_name`
- Sort Key: `timestamp`
- Each record contains: job_name, timestamp, session_id, agent_name, action_name, inference_id, prompt, response, tokens_used, cost_estimate, duration_seconds, artifacts_s3_uri, status, error_message

### S3 Artifact Structure
```
s3://autoninja-artifacts-{account-id}-production/
└── {job_name}/
    ├── requirements/{agent_name}/
    ├── architecture/{agent_name}/
    ├── code/{agent_name}/
    ├── validation/{agent_name}/
    └── deployment/{agent_name}/
```

## Important Files

### Reference Implementation
- `lambda/requirements-analyst/handler.py` - Canonical pattern for all Lambda functions
- `.kiro/steering/autoninja-implementation-patterns.md` - Comprehensive implementation patterns

### Shared Libraries
- `shared/persistence/dynamodb_client.py` - DynamoDB operations
- `shared/persistence/s3_client.py` - S3 operations
- `shared/utils/logger.py` - Structured logging
- `shared/utils/job_generator.py` - Job name generation

### Configuration
- `pyproject.toml` - Python project configuration
- `shared/requirements.txt` - Shared dependencies

### Infrastructure
- `infrastructure/cloudformation/autoninja-complete.yaml` - Main CloudFormation template (deploys entire system)

## Common Mistakes to Avoid

1. **Creating 2 DynamoDB records per action** - Use `log_inference_input()` to create, then `log_inference_output()` with the same timestamp to update
2. **Hardcoding AWS resource names** - Always use environment variables (`DYNAMODB_TABLE_NAME`, `S3_BUCKET_NAME`)
3. **Different event parsing logic** - Always follow Requirements Analyst pattern exactly
4. **Inconsistent response format** - Always return Bedrock Agent format with messageVersion, response, actionGroup, etc.
5. **Not saving both raw and converted artifacts** - Always save both to S3
6. **Missing error logging** - Always call `log_error_to_dynamodb()` before returning error response

## Verification Checklist

Before marking any Lambda implementation complete:
- [ ] Code follows Requirements Analyst pattern exactly
- [ ] DynamoDB logging creates 1 record per action (not 2)
- [ ] Both `prompt` and `response` fields populated in DynamoDB
- [ ] Both raw and converted artifacts saved to S3
- [ ] No hardcoded AWS resource names
- [ ] Error handling matches Requirements Analyst pattern
- [ ] Response format matches Requirements Analyst pattern
- [ ] Tests pass with no errors
- [ ] No linter warnings or errors

## Testing Best Practices

Test files must match Bedrock Agent event format:
```python
def create_test_event(api_path: str, job_name: str, params: dict):
    return {
        'messageVersion': '1.0',
        'agent': {'name': 'your-agent', 'id': 'TEST123', 'alias': 'PROD', 'version': '1'},
        'sessionId': 'test-session-123',
        'actionGroup': 'your-action-group',
        'apiPath': api_path,
        'httpMethod': 'POST',
        'parameters': [{'name': k, 'type': 'string', 'value': v} for k, v in params.items()],
        'requestBody': {
            'content': {
                'application/json': {
                    'properties': [{'name': k, 'type': 'string', 'value': v} for k, v in params.items()]
                }
            }
        }
    }
```

## AWS Configuration

Default AWS configuration:
- Region: `us-east-2`
- Profile: `AdministratorAccess-784327326356`
- Account ID: `784327326356`
- Bedrock Model: `anthropic.claude-sonnet-4-5-20250929-v1:0` (or `us.anthropic.claude-sonnet-4-5-20250929-v1:0` for some regions)

## When in Doubt

Always refer back to Requirements Analyst implementation (`lambda/requirements-analyst/handler.py`). It is the source of truth for all patterns.
