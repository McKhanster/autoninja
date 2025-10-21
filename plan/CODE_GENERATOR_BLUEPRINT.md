# Code Generator Complete Blueprint

**Purpose:** This document contains ALL metadata and configuration for the Code Generator agent, which will serve as the template for all 5 collaborator agents.

## Overview

The Code Generator is the ONLY validated agent with proven end-to-end functionality. All other agents will be standardized to match this exact pattern.

---

## 1. Bedrock Agent Configuration

### Agent Details

```json
{
  "agentId": "JYHLGG522G",
  "agentName": "autoninja-code-generator-production",
  "agentArn": "arn:aws:bedrock:us-east-2:784327326356:agent/JYHLGG522G",
  "agentStatus": "PREPARED",
  "foundationModel": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
  "idleSessionTTLInSeconds": 600,
  "agentResourceRoleArn": "arn:aws:iam::784327326356:role/service-role/AmazonBedrockExecutionRoleForAgents_9T2URGTFNQC"
}
```

### Agent Instructions

```
You are a code generator for the AutoNinja system. IMPORTANT: You MUST use the action group functions to generate code. When you receive a request: 1. If job_name is not provided, generate one in format job-{keyword}-{YYYYMMDD-HHMMSS}. 2. Use the /generate-lambda-code action to generate Lambda code. 3. Use the /generate-agent-config action for agent config. 4. Use the /generate-openapi-schema action for schemas. Always call the action functions.
```

**CRITICAL NOTE:** Job name will be provided by orchestrator. Instructions should be updated to:

```
You are a code generator for the AutoNinja system. You receive a job_name from the orchestrator supervisor. Use the action group functions to generate code: 1. Use /generate-lambda-code to generate Lambda code. 2. Use /generate-agent-config for agent config. 3. Use /generate-openapi-schema for schemas. Always include the job_name in all action calls.
```

### Agent Aliases

1. **production** (BGDDCLWZBQ) - Routes to version 1
2. **AgentTestAlias** (TSTALIASID) - Routes to DRAFT

---

## 2. Action Group Configuration

### Action Group Details

```json
{
  "actionGroupId": "ZKYOK7KZMT",
  "actionGroupName": "code-generator-actions",
  "actionGroupState": "ENABLED",
  "actionGroupExecutor": {
    "lambda": "arn:aws:lambda:us-east-2:784327326356:function:autoninja-code-generator-production"
  }
}
```

### OpenAPI Schema (Inline Payload)

```yaml
openapi: 3.0.0
info:
  title: Code Generator Action Group API
  description: API for generating Lambda code, agent configurations, and OpenAPI schemas
  version: 1.0.0

paths:
  /generate-lambda-code:
    post:
      summary: Generate Lambda function code
      description: Generates production-ready Python Lambda function code with error handling, logging, and persistence
      operationId: generateLambdaCode
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_name
                - requirements
              properties:
                job_name:
                  type: string
                  description: Unique job identifier in format job-{keyword}-{YYYYMMDD-HHMMSS}
                requirements:
                  type: string
                  description: JSON string containing requirements from Requirements Analyst
                function_spec:
                  type: string
                  description: JSON string containing specific function specifications
      responses:
        "200":
          description: Lambda code successfully generated
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_name:
                    type: string
                  lambda_code:
                    type: string
                  requirements_txt:
                    type: string
                  status:
                    type: string
        "400":
          description: Invalid request
        "500":
          description: Internal server error

  /generate-agent-config:
    post:
      summary: Generate Bedrock Agent configuration
      description: Creates Bedrock Agent configuration JSON with agent name, instructions, foundation model, and action groups
      operationId: generateAgentConfig
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_name
                - requirements
              properties:
                job_name:
                  type: string
                requirements:
                  type: string
      responses:
        "200":
          description: Agent configuration successfully generated
        "400":
          description: Invalid request
        "500":
          description: Internal server error

  /generate-openapi-schema:
    post:
      summary: Generate OpenAPI schema for action groups
      description: Creates OpenAPI 3.0 schema defining all endpoints, parameters, and request/response formats
      operationId: generateOpenapiSchema
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_name
                - action_group_spec
              properties:
                job_name:
                  type: string
                action_group_spec:
                  type: string
      responses:
        "200":
          description: OpenAPI schema successfully generated
        "400":
          description: Invalid request
        "500":
          description: Internal server error
```

---

## 3. Lambda Function Configuration

### Function Details

```json
{
  "FunctionName": "autoninja-code-generator-production",
  "FunctionArn": "arn:aws:lambda:us-east-2:784327326356:function:autoninja-code-generator-production",
  "Runtime": "python3.12",
  "Role": "arn:aws:iam::784327326356:role/AutoNinjaCodeGeneratorRole-production",
  "Handler": "handler.lambda_handler",
  "CodeSize": 18024,
  "Description": "Code Generator agent Lambda function (placeholder)",
  "Timeout": 300,
  "MemorySize": 512
}
```

### Environment Variables

```json
{
  "ENVIRONMENT": "production",
  "DYNAMODB_TABLE_NAME": "autoninja-inference-records-production",
  "S3_BUCKET_NAME": "autoninja-artifacts-784327326356-production",
  "LOG_LEVEL": "INFO"
}
```

### Lambda Layer

```
arn:aws:lambda:us-east-2:784327326356:layer:autoninja-shared-layer-production:3
```

---

## 4. IAM Configuration

### Lambda Execution Role

**Role Name:** `AutoNinjaCodeGeneratorRole-production`  
**Role ARN:** `arn:aws:iam::784327326356:role/AutoNinjaCodeGeneratorRole-production`

**Trust Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Attached Policies:**

- `AutoNinjaLambdaBasePolicy-production`

### Bedrock Agent Execution Role

**Role Name:** `AmazonBedrockExecutionRoleForAgents_9T2URGTFNQC`  
**Role ARN:** `arn:aws:iam::784327326356:role/service-role/AmazonBedrockExecutionRoleForAgents_9T2URGTFNQC`

**Trust Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AmazonBedrockAgentInferenceProfilesCrossRegionPolicyProd",
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "784327326356"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock:us-east-2:784327326356:agent/*"
        }
      }
    }
  ]
}
```

**Attached Policies:**

- `AmazonBedrockAgentInferenceProfilesCrossRegionPolicy_C9PO6CN7KFH`

**Inline Policy (AmazonBedrockAgentInferenceProfilesCrossRegionPolicy_C9PO6CN7KFH):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AmazonBedrockAgentInferenceProfilesCrossRegionPolicyProd",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:GetInferenceProfile",
        "bedrock:GetFoundationModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-2:784327326356:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0"
      ]
    }
  ]
}
```

**Policy Explanation:**

- **InvokeModel**: Allows the agent to invoke the Claude Sonnet 4.5 foundation model
- **InvokeModelWithResponseStream**: Enables streaming responses from the model
- **GetInferenceProfile**: Retrieves inference profile configuration for cross-region inference
- **GetFoundationModel**: Gets foundation model metadata and capabilities

**Resource Scope:**

- Specific inference profile in us-east-2 region
- Foundation model accessible across all regions (for cross-region inference)

**Note:** This role does NOT include Lambda invocation permissions. Lambda invocation is handled via resource-based policies on the Lambda functions themselves (see Lambda Permission resources in CloudFormation).

### Lambda Resource-Based Policy (for Bedrock Agent Invocation)

Each Lambda function has a resource-based policy that allows Bedrock Agents to invoke it:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-2:784327326356:function:autoninja-code-generator-production",
      "Condition": {
        "StringEquals": {
          "AWS:SourceAccount": "784327326356"
        }
      }
    }
  ]
}
```

**CloudFormation Resource:**

```yaml
CodeGeneratorLambdaPermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref CodeGeneratorFunction
    Action: lambda:InvokeFunction
    Principal: bedrock.amazonaws.com
    SourceAccount: !Ref AWS::AccountId
```

**Security Note:** The resource-based policy ensures that only Bedrock Agents from the same AWS account can invoke the Lambda function, preventing unauthorized cross-account invocations.

---

## 5. Lambda Handler Implementation Pattern

### File Structure

```
lambda/code-generator/
├── handler.py (770 lines)
└── __pycache__/
```

### Key Implementation Patterns

#### 1. Main Handler Structure

```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    start_time = time.time()
    job_name = None
    timestamp = None

    try:
        # Parse Bedrock Agent event
        api_path = event.get('apiPath', '')
        params = extract_parameters(event)
        job_name = params.get('job_name', 'unknown')

        # Set logger context
        logger.set_context(job_name=job_name, agent_name='code-generator', action_name=api_path)

        # Route to action handler
        if api_path == '/action-1':
            result = handle_action_1(event, params, session_id, start_time)
        elif api_path == '/action-2':
            result = handle_action_2(event, params, session_id, start_time)
        else:
            raise ValueError(f"Unknown apiPath: {api_path}")

        # Return formatted response
        return format_success_response(result, event)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if job_name and timestamp:
            dynamodb_client.log_error_to_dynamodb(job_name, timestamp, str(e), time.time() - start_time)
        return format_error_response(e, event)
```

#### 2. Action Handler Pattern

```python
def handle_action(event, params, session_id, start_time):
    job_name = params.get('job_name')

    # Validate required parameters
    if not job_name:
        raise ValueError("Missing required parameter: job_name")

    # Log input to DynamoDB IMMEDIATELY
    timestamp = dynamodb_client.log_inference_input(
        job_name=job_name,
        session_id=session_id,
        agent_name='code-generator',
        action_name='action_name',
        prompt=json.dumps(event, default=str),
        model_id='lambda-function'
    )['timestamp']

    try:
        # Execute business logic
        result = do_business_logic()

        # Log output to DynamoDB IMMEDIATELY
        duration = time.time() - start_time
        s3_uri = s3_client.get_s3_uri(job_name, 'phase', 'agent', 'file.json')

        dynamodb_client.log_inference_output(
            job_name=job_name,
            timestamp=timestamp,
            response=json.dumps(result, default=str),
            duration_seconds=duration,
            artifacts_s3_uri=s3_uri,
            status='success'
        )

        # Save artifacts to S3
        s3_client.save_converted_artifact(job_name, 'phase', 'agent', artifact, 'file.json')
        s3_client.save_raw_response(job_name, 'phase', 'agent', result, 'raw_response.json')

        return result

    except Exception as e:
        dynamodb_client.log_error_to_dynamodb(job_name, timestamp, str(e), time.time() - start_time)
        raise
```

#### 3. Parameter Extraction

```python
# Extract parameters from Bedrock Agent event
request_body = event.get('requestBody', {})
content = request_body.get('content', {})
json_content = content.get('application/json', {})
properties = json_content.get('properties', [])

# Convert properties array to dict
params = {prop['name']: prop['value'] for prop in properties}
```

#### 4. Response Formatting

```python
# Success response
{
    'messageVersion': '1.0',
    'response': {
        'actionGroup': event.get('actionGroup'),
        'apiPath': event.get('apiPath'),
        'httpMethod': event.get('httpMethod', 'POST'),
        'httpStatusCode': 200,
        'responseBody': {
            'application/json': {
                'body': json.dumps(result)
            }
        }
    }
}

# Error response
{
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

---

## 6. Persistence Pattern

### DynamoDB Logging

- **1 record per action** (create + update pattern)
- `log_inference_input()` creates record, returns timestamp
- `log_inference_output()` updates same record using timestamp
- All fields populated: prompt, response, duration, status, s3_uri

### S3 Artifact Saving

- **Raw response** saved: `{job_name}/{phase}/{agent}/raw_response.json`
- **Converted artifacts** saved: `{job_name}/{phase}/{agent}/{filename}`
- Both saved for complete audit trail

---

## 7. Testing Pattern

### Unit Test Structure

```python
def create_test_event(api_path: str, job_name: str, params: dict):
    return {
        'messageVersion': '1.0',
        'agent': {'name': 'agent-name', 'id': 'ID', 'alias': 'ALIAS', 'version': '1'},
        'sessionId': 'test-session-123',
        'actionGroup': 'action-group-name',
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

---

## 8. Agent-Specific Customizations

### What Changes Per Agent

| Component             | Code Generator                      | Requirements Analyst                      | Solution Architect                      | Quality Validator                      | Deployment Manager                      |
| --------------------- | ----------------------------------- | ----------------------------------------- | --------------------------------------- | -------------------------------------- | --------------------------------------- |
| **Agent Name**        | code-generator                      | requirements-analyst                      | solution-architect                      | quality-validator                      | deployment-manager                      |
| **Instructions**      | Generate code                       | Extract requirements                      | Design architecture                     | Validate quality                       | Deploy to AWS                           |
| **Action Group Name** | code-generator-actions              | requirements-analyst-actions              | solution-architect-actions              | quality-validator-actions              | deployment-manager-actions              |
| **Actions**           | 3 actions                           | 3 actions                                 | 3 actions                               | 3 actions                              | 4 actions                               |
| **Lambda Function**   | autoninja-code-generator-production | autoninja-requirements-analyst-production | autoninja-solution-architect-production | autoninja-quality-validator-production | autoninja-deployment-manager-production |
| **IAM Role**          | AutoNinjaCodeGeneratorRole          | AutoNinjaRequirementsAnalystRole          | AutoNinjaSolutionArchitectRole          | AutoNinjaQualityValidatorRole          | AutoNinjaDeploymentManagerRole          |
| **S3 Phase**          | code                                | requirements                              | architecture                            | validation                             | deployment                              |

### What Stays the Same

- ✅ Foundation model
- ✅ Runtime (python3.12)
- ✅ Handler name (handler.lambda_handler)
- ✅ Memory (512MB, except Deployment Manager: 1024MB)
- ✅ Timeout (300s, except Deployment Manager: 900s)
- ✅ Environment variables structure
- ✅ Lambda Layer
- ✅ Event parsing logic
- ✅ Response formatting
- ✅ DynamoDB logging pattern
- ✅ S3 artifact saving pattern
- ✅ Error handling pattern

---

## 9. CloudFormation Template Structure

### Resources Per Agent (5 agents × 11 resources = 55 resources)

1. **Lambda Execution Role** - IAM role for Lambda
2. **Lambda Execution Policy** - Inline policy for Lambda role
3. **Lambda Function** - The function itself
4. **Lambda Permission** - Allow Bedrock to invoke
5. **Bedrock Agent Role** - IAM role for Bedrock Agent
6. **Bedrock Agent Policy** - Inline policy for agent role
7. **Bedrock Agent** - The agent itself
8. **Bedrock Action Group** - Links agent to Lambda
9. **Bedrock Agent Alias (production)** - Production version
10. **Bedrock Agent Alias (test)** - Test/DRAFT version
11. **CloudWatch Log Group** - For Lambda logs

### Shared Resources (6 resources)

1. **DynamoDB Table** - autoninja-inference-records-production
2. **S3 Bucket** - autoninja-artifacts-{AccountId}-production
3. **Lambda Layer** - autoninja-shared-layer-production
4. **Supervisor Agent** - Orchestrator
5. **Supervisor Agent Alias** - Production alias
6. **Agent Collaborator Associations** - Link supervisor to 5 collaborators

**Total Resources:** 55 + 6 = **61 resources**

---

## 10. Key Success Factors

### Why Code Generator Works

1. ✅ **Correct event parsing** - Extracts parameters from properties array
2. ✅ **Immediate DynamoDB logging** - Logs before and after processing
3. ✅ **Proper timestamp handling** - Saves timestamp from log_inference_input()
4. ✅ **Complete S3 persistence** - Saves both raw and converted artifacts
5. ✅ **Consistent response format** - Matches Bedrock Agent expectations
6. ✅ **Comprehensive error handling** - Try-catch with DynamoDB error logging
7. ✅ **Proper imports** - Uses shared layer correctly
8. ✅ **Type hints** - Clean, maintainable code
9. ✅ **Structured logging** - Context-aware logging
10. ✅ **Job name tracking** - Consistent across all operations

---

## Next Steps

See `STANDARDIZATION_PLAN.md` for the detailed plan to replicate this pattern across all 5 agents.
