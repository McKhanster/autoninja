# Supervisor Empty Response Fix

## Problem Identified

The supervisor was getting empty responses from Bedrock agents even though the underlying Lambda functions were working correctly. The issue was in the **agent instructions** - they weren't telling the agents to return the Lambda function results to the caller.

## Root Cause

1. **Bedrock agents with action groups** call Lambda functions successfully
2. **Lambda functions** return proper JSON responses (confirmed in DynamoDB logs)
3. **Agent instructions** didn't specify how to return Lambda results to the caller
4. **Supervisor** expected JSON responses but got empty completions

## Changes Made

### 1. Updated Agent Instructions

Modified all agent CloudFormation templates to include explicit instructions:

```yaml
Instruction: |
  [Agent role description]
  
  When you receive [input]:
  1. Extract the job_name and [parameters] from the input
  2. Call the [action-name] action with the job_name and [parameters]
  3. Take the JSON response from [action-name] and return it directly to the caller
  4. If asked to [other tasks], call the appropriate actions
  5. Always return the complete JSON response from the action functions

  IMPORTANT: You must return the exact JSON response from the action functions to the caller.
  Do not summarize or modify the JSON - return it exactly as received from the functions.
```

### 2. Updated Supervisor Response Handling

Modified `lambda/supervisor-agentcore/handler.py` to:
- Handle both JSON and natural language responses from agents
- Extract JSON from agent responses when possible
- Provide better error handling for empty responses
- Log response types for debugging

### 3. Files Modified

- `infrastructure/cloudformation/stacks/requirements-analyst.yaml`
- `infrastructure/cloudformation/stacks/code-generator.yaml`
- `infrastructure/cloudformation/stacks/solution-architect.yaml`
- `infrastructure/cloudformation/stacks/quality-validator.yaml`
- `infrastructure/cloudformation/stacks/deployment-manager.yaml`
- `lambda/supervisor-agentcore/handler.py`

## Deployment Steps

1. **Deploy CloudFormation updates** (agents need to be re-prepared):
   ```bash
   # Deploy each agent stack with updated instructions
   aws cloudformation update-stack --stack-name autoninja-requirements-analyst-production --template-body file://infrastructure/cloudformation/stacks/requirements-analyst.yaml --parameters file://parameters.json --capabilities CAPABILITY_IAM
   
   # Repeat for other agents...
   ```

2. **Deploy supervisor Lambda**:
   ```bash
   # Package and deploy supervisor with updated response handling
   cd lambda/supervisor-agentcore
   zip -r supervisor-agentcore.zip .
   aws s3 cp supervisor-agentcore.zip s3://deployment-bucket/lambda/
   aws lambda update-function-code --function-name autoninja-supervisor-production --s3-bucket deployment-bucket --s3-key lambda/supervisor-agentcore.zip
   ```

3. **Test the fix**:
   ```bash
   python test_supervisor_fix.py
   ```

## Expected Behavior After Fix

1. **Supervisor invokes requirements-analyst** with clear instruction
2. **Requirements-analyst calls extract-requirements Lambda** (working)
3. **Requirements-analyst returns Lambda JSON response** to supervisor (fixed)
4. **Supervisor receives and parses response** (improved handling)
5. **Process continues to next agent** (code-generator, etc.)

## Verification

- Check CloudWatch logs for successful agent invocations
- Verify DynamoDB records show complete pipeline execution
- Confirm S3 artifacts are created for all phases
- Test end-to-end with `tests/supervisor/test_e2e.py`