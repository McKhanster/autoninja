---
inclusion: always
---

# AutoNinja Implementation Patterns and Standards

This steering file ensures consistency across all Lambda function implementations in the AutoNinja project.

## Critical Implementation Rules

### 1. Reference Implementation: Requirements Analyst

**The Requirements Analyst Lambda function (`lambda/requirements-analyst/handler.py`) is the CANONICAL reference implementation.**

All other Lambda functions MUST follow its exact patterns for:
- Event parsing
- Parameter extraction
- Action routing
- DynamoDB logging
- S3 artifact saving
- Response formatting
- Error handling

### 2. What "EXACT Structure" Means

When the spec says "copy the EXACT structure," it means:

✅ **DO copy:**
- Control flow pattern (event parsing → routing → action handlers → error handling)
- DynamoDB logging calls (log_inference_input → business logic → log_inference_output)
- S3 artifact saving pattern (save_raw_response + save_converted_artifact)
- Response format structure
- Error handling try-catch blocks
- Parameter extraction logic

❌ **DO NOT copy:**
- Business logic (requirements extraction, code generation, etc.)
- Function names (use appropriate names for your agent)
- Specific data processing (each agent has unique logic)

### 3. DynamoDB Logging Pattern (CRITICAL)

**One record per action, not two:**

```python
# STEP 1: Create record and get timestamp
record = dynamodb_client.log_inference_input(
    job_name=job_name,
    session_id=session_id,
    agent_name="your-agent-name",
    action_name="your-action-name",
    prompt=json.dumps(event),
    inference_id=f"{job_name}-{action_name}-{int(time.time())}",
    model_id="N/A"
)
timestamp = record['timestamp']  # SAVE THIS

# STEP 2: Execute business logic
result = your_business_logic()

# STEP 3: Update the SAME record
dynamodb_client.log_inference_output(
    job_name=job_name,
    timestamp=timestamp,  # USE THE SAVED TIMESTAMP
    response=json.dumps(result),
    tokens_used=0,
    cost_estimate=0.0,
    duration_seconds=time.time() - start_time,
    artifacts_s3_uri=s3_uri,
    status='success'
)
```

**Verification:** Each action should create exactly 1 DynamoDB record with both `prompt` and `response` fields populated.

### 4. Event Parsing Pattern

**Always use this exact pattern from Requirements Analyst:**

```python
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract parameters from Bedrock Agent event
    api_path = event.get('apiPath', '')
    parameters = event.get('parameters', [])
    
    # Convert parameters array to dict
    params = {}
    for param in parameters:
        params[param['name']] = param['value']
    
    # Extract from requestBody if not in parameters
    request_body = event.get('requestBody', {})
    if request_body:
        content = request_body.get('content', {})
        app_json = content.get('application/json', {})
        properties = app_json.get('properties', [])
        for prop in properties:
            if prop['name'] not in params:
                params[prop['name']] = prop['value']
    
    # Extract required fields
    job_name = params.get('job_name')
    session_id = event.get('sessionId', 'unknown')
    
    # Route to action handler
    if api_path == '/your-action':
        return handle_your_action(event, params, session_id, start_time)
```

### 5. Response Format Pattern

**Always use this exact format:**

```python
return {
    'messageVersion': '1.0',
    'response': {
        'actionGroup': event.get('actionGroup', 'your-action-group'),
        'apiPath': event.get('apiPath', ''),
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

### 6. Error Handling Pattern

**Always use this exact pattern:**

```python
try:
    # Your business logic here
    result = do_something()
    
except Exception as e:
    logger.error(f"Error in action: {str(e)}")
    
    # Log error to DynamoDB
    if job_name and timestamp:
        dynamodb_client.log_error_to_dynamodb(
            job_name=job_name,
            timestamp=timestamp,
            error_message=str(e),
            duration_seconds=time.time() - start_time
        )
    
    # Return error response
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'your-action-group'),
            'apiPath': event.get('apiPath', ''),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 500,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({
                        'error': str(e),
                        'status': 'error'
                    })
                }
            }
        }
    }
```

### 7. S3 Artifact Saving Pattern

**Always save both raw and converted artifacts:**

```python
# Save raw response
s3_uri_raw = s3_client.save_raw_response(
    job_name=job_name,
    phase='your-phase',  # e.g., 'code', 'architecture', 'validation'
    agent_name='your-agent-name',
    response=result
)

# Save converted artifact
s3_uri_converted = s3_client.save_converted_artifact(
    job_name=job_name,
    phase='your-phase',
    agent_name='your-agent-name',
    artifact=converted_data,
    filename='your-artifact.json'
)
```

### 8. AWS Resource Names

**Always use environment variables, never hardcode:**

```python
# ✅ CORRECT
bucket_name = os.environ.get('S3_BUCKET_NAME', f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID')}-production")
table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'autoninja-inference-records-production')

# ❌ WRONG
bucket_name = "autoninja-artifacts-784327326356-production"  # Hardcoded account ID
```

### 9. Test File Pattern

**Always follow this structure:**

```python
import os
import json
from lambda.your_agent import handler

class Context:
    def get_remaining_time_in_millis(self):
        return 300000

def create_test_event(api_path: str, job_name: str, params: dict):
    """Create a test event matching Bedrock Agent format"""
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

def test_your_action():
    event = create_test_event(
        api_path='/your-action',
        job_name='job-test-20251015-120000',
        params={'job_name': 'job-test-20251015-120000', 'other_param': 'value'}
    )
    
    response = handler.lambda_handler(event, Context())
    
    assert response['response']['httpStatusCode'] == 200
    body = json.loads(response['response']['responseBody']['application/json']['body'])
    assert body['status'] == 'success'
    print(f"✅ Test passed: {body}")
```

### 10. Code Replacement Best Practices

When using `strReplace` tool:

1. **Read extra context:** Include 2-3 lines before and after the target code
2. **Check for multi-line strings:** Don't accidentally leave orphaned closing quotes
3. **Verify indentation:** Python is indentation-sensitive
4. **Test after replacement:** Run diagnostics to catch syntax errors

### 11. Verification Checklist

Before marking a task complete, verify:

- [ ] Code follows Requirements Analyst pattern exactly
- [ ] DynamoDB logging creates 1 record per action (not 2)
- [ ] Both `prompt` and `response` fields are populated in DynamoDB
- [ ] Both raw and converted artifacts saved to S3
- [ ] No hardcoded AWS resource names
- [ ] Error handling matches Requirements Analyst pattern
- [ ] Response format matches Requirements Analyst pattern
- [ ] All tests pass with no errors or warnings
- [ ] getDiagnostics shows no issues

## Common Mistakes to Avoid

### ❌ Mistake 1: Creating 2 DynamoDB records per action
```python
# WRONG - creates 2 records
dynamodb_client.log_inference_input(...)
dynamodb_client.log_inference_output(...)  # Creates new record
```

### ✅ Correct: Update the same record
```python
# CORRECT - creates 1 record, then updates it
record = dynamodb_client.log_inference_input(...)
timestamp = record['timestamp']
# ... business logic ...
dynamodb_client.log_inference_output(job_name, timestamp, ...)  # Updates existing
```

### ❌ Mistake 2: Hardcoding bucket names
```python
# WRONG
bucket = "autoninja-artifacts-784327326356-production"
```

### ✅ Correct: Use environment variables
```python
# CORRECT
bucket = os.environ.get('S3_BUCKET_NAME', f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID')}-production")
```

### ❌ Mistake 3: Different event parsing logic
```python
# WRONG - custom parsing that differs from Requirements Analyst
job_name = event['parameters'][0]['value']
```

### ✅ Correct: Use Requirements Analyst pattern
```python
# CORRECT - same parsing as Requirements Analyst
params = {}
for param in event.get('parameters', []):
    params[param['name']] = param['value']
job_name = params.get('job_name')
```

### ❌ Mistake 4: Leaving orphaned code
```python
# WRONG - replaced function but left closing quote
def old_function():
    return """
    Some multi-line
    string
"""  # <-- This gets orphaned if you don't include it in strReplace
```

### ✅ Correct: Include full context
```python
# CORRECT - include the full function including closing elements
def old_function():
    return """
    Some multi-line
    string
"""

def new_function():
    return "new implementation"
```

## Reference Files

When implementing a new Lambda function, always have these files open:

1. **`lambda/requirements-analyst/handler.py`** - Canonical reference implementation
2. **`shared/persistence/dynamodb_client.py`** - DynamoDB logging methods
3. **`shared/persistence/s3_client.py`** - S3 artifact saving methods
4. **`tests/requirement_analyst/test_handler.py`** - Test pattern reference

## Quick Reference: Implementation Checklist

For each new Lambda function:

1. [ ] Copy main `lambda_handler()` structure from Requirements Analyst
2. [ ] Copy event parsing logic exactly
3. [ ] Copy action routing pattern
4. [ ] For each action handler:
   - [ ] Call `log_inference_input()` first, save timestamp
   - [ ] Execute business logic (your custom code)
   - [ ] Call `log_inference_output()` with saved timestamp
   - [ ] Save raw response to S3
   - [ ] Save converted artifact to S3
   - [ ] Return response in Requirements Analyst format
5. [ ] Copy error handling pattern exactly
6. [ ] Create test file following Requirements Analyst test pattern
7. [ ] Run tests and verify DynamoDB has 1 record per action
8. [ ] Run getDiagnostics to verify no errors/warnings

## When in Doubt

**Always refer back to Requirements Analyst implementation.** It is the source of truth for all patterns.
