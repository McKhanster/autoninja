# Design: Bedrock Agent Throttling Fix

## Solution Overview

Implement AWS Bedrock's **Custom Orchestration** feature to gain full control over agent execution flow and enforce sequential tool execution, eliminating throttling errors caused by parallel Converse API calls.

## Why Custom Orchestration Over Advanced Prompts

AWS Bedrock offers two approaches to control agent behavior:

1. **Advanced Prompts**: Override default prompt templates (prompt-based control)
2. **Custom Orchestration**: Implement Lambda function to control execution flow (programmatic control)

**We choose Custom Orchestration because:**
- ✅ **Full programmatic control**: We can explicitly control when and how tools are invoked
- ✅ **Rate limiting built-in**: We can add delays between Converse API calls directly in code
- ✅ **Deterministic behavior**: No reliance on LLM interpreting orchestration instructions
- ✅ **Better debugging**: Can add logging, metrics, and observability at each step
- ✅ **State management**: Complete control over state transitions and decision logic
- ✅ **Error handling**: Can implement custom retry logic, backoff, and recovery

## Architecture Changes

### New Component: Custom Orchestration Lambda Function

Create a new Lambda function (`lambda/custom-orchestration/`) that:
1. Receives orchestration events from Bedrock Agent
2. Decides which action to invoke next
3. Controls timing between Converse API calls
4. Enforces sequential execution
5. Returns appropriate state transitions

### CloudFormation Changes

1. **New Lambda Function**: `CustomOrchestrationFunction`
2. **New IAM Role**: `CustomOrchestrationRole` (with permissions to invoke Bedrock Converse API and action Lambda functions)
3. **Agent Configuration Update**: Set `orchestrationType: CUSTOM_ORCHESTRATION` for all agents
4. **Lambda Permission**: Allow Bedrock Agents to invoke the custom orchestration function

### Affected Agents

All agents will use the same custom orchestration Lambda:
1. Requirements Analyst Agent
2. Code Generator Agent
3. Solution Architect Agent
4. Quality Validator Agent
5. Deployment Manager Agent
6. Supervisor Agent (if applicable)

## Implementation Details

### 1. Custom Orchestration Lambda Function

The Lambda function follows AWS Bedrock's orchestration protocol:

```python
def lambda_handler(event, context):
    """
    Custom orchestration handler for Bedrock Agents.
    Enforces sequential tool execution with rate limiting.
    """
    # Extract orchestration state
    state = event.get('orchestrationState')
    agent_id = event.get('agentId')
    session_id = event.get('sessionId')
    action_group_invocations = event.get('actionGroupInvocations', [])

    # State machine
    if state == 'START':
        # Analyze input, decide first action
        return invoke_model_for_planning(event)

    elif state == 'MODEL_INVOKED':
        # Model returned a plan, extract tool calls
        # Enforce sequential execution: return ONLY first tool
        return invoke_first_tool_only(event)

    elif state == 'TOOL_INVOKED':
        # Tool completed, rate limit before next step
        apply_rate_limiting()
        # Check if more tools needed
        if has_more_tools(event):
            return invoke_next_tool(event)
        else:
            return final_response(event)

    elif state == 'FINAL_RESPONSE':
        return event
```

### 2. CloudFormation Configuration for Custom Orchestration

```yaml
# New Lambda Function for Custom Orchestration
CustomOrchestrationFunction:
  Type: AWS::Lambda::Function
  Properties:
    FunctionName: !Sub "autoninja-custom-orchestration-${Environment}"
    Runtime: python3.12
    Handler: handler.lambda_handler
    Role: !GetAtt CustomOrchestrationRole.Arn
    Timeout: 300
    MemorySize: 512
    Environment:
      Variables:
        MIN_INTERVAL_SECONDS: "60"  # Rate limit: 60 seconds between Converse calls
        LOG_LEVEL: "INFO"
    Code:
      S3Bucket: !Ref DeploymentArtifactsBucket
      S3Key: lambda/custom-orchestration.zip

# IAM Role for Custom Orchestration Lambda
CustomOrchestrationRole:
  Type: AWS::IAM::Role
  Properties:
    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Service: lambda.amazonaws.com
          Action: sts:AssumeRole
    ManagedPolicyArns:
      - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    Policies:
      - PolicyName: BedrockConverseAccess
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
                - bedrock:Converse
              Resource: !Sub "arn:aws:bedrock:${AWS::Region}::foundation-model/*"

# Lambda Permission for Bedrock Agents to invoke Custom Orchestration
CustomOrchestrationLambdaPermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref CustomOrchestrationFunction
    Action: lambda:InvokeFunction
    Principal: bedrock.amazonaws.com
    SourceAccount: !Ref AWS::AccountId

# Update Agent Configuration (example for Requirements Analyst)
RequirementsAnalystAgent:
  Type: AWS::Bedrock::Agent
  Properties:
    AgentName: !Sub "autoninja-requirements-analyst-${Environment}"
    # ... existing properties ...
    OrchestrationType: CUSTOM_ORCHESTRATION  # <<< THIS IS THE KEY CHANGE
    CustomOrchestrationConfiguration:
      Executor:
        Lambda: !GetAtt CustomOrchestrationFunction.Arn
```

### 3. Implementation Strategy

**CRITICAL**: All 6 agents must receive identical custom orchestration configuration simultaneously.

#### Phase 1: Create Custom Orchestration Lambda
1. Implement `lambda/custom-orchestration/handler.py`
2. Add rate limiting logic (60 second intervals minimum)
3. Implement state machine for orchestration flow
4. Add comprehensive logging and error handling
5. Package and upload to S3

#### Phase 2: Update CloudFormation for ALL Agents
1. Add `CustomOrchestrationFunction` resource
2. Add `CustomOrchestrationRole` with proper permissions
3. Add `CustomOrchestrationLambdaPermission`
4. Update **ALL 6 agents** with:
   - `OrchestrationType: CUSTOM_ORCHESTRATION`
   - `CustomOrchestrationConfiguration` pointing to the Lambda
5. Deploy stack update (updates all agents simultaneously)

#### Phase 3: Testing
1. Run `tests/requirements-analyst/test_requirements_analyst_agent.py`
2. Verify sequential execution in CloudWatch logs
3. Verify no throttling errors
4. Test other agents to ensure consistency

## Configuration Details

### All Agents Must Have Identical Orchestration Structure

**EVERY agent** (Requirements Analyst, Code Generator, Solution Architect, Quality Validator, Deployment Manager, Supervisor) must have:

```yaml
AgentName: !Sub "autoninja-{agent-name}-${Environment}"
# ... existing properties (Instruction, ActionGroups, etc.) ...
OrchestrationType: CUSTOM_ORCHESTRATION
CustomOrchestrationConfiguration:
  Executor:
    Lambda: !GetAtt CustomOrchestrationFunction.Arn
```

### Single Orchestration Lambda for All Agents

The same `CustomOrchestrationFunction` will handle orchestration for **all 6 agents**. This provides:
- ✅ Consistent behavior across all agents
- ✅ Centralized rate limiting logic
- ✅ Single point of configuration
- ✅ Easier maintenance and updates

## Testing Strategy

### Unit Tests
- Test custom orchestration Lambda function in isolation
- Verify state machine transitions
- Validate rate limiting logic
- Test error handling

### CloudFormation Validation
- Verify `CustomOrchestrationConfiguration` is correctly applied to ALL 6 agents
- Validate IAM permissions for custom orchestration Lambda
- Ensure Lambda permission allows Bedrock Agent invocation

### Integration Tests
- Run `tests/requirements-analyst/test_requirements_analyst_agent.py`
- Monitor CloudWatch logs for sequential tool execution
- Verify no throttling errors occur
- Measure execution time compared to before
- Test all other agents for consistency

### Validation Criteria
- ✅ No ThrottlingException errors in CloudWatch
- ✅ Tool calls appear sequentially in orchestration logs (not parallel)
- ✅ All tests pass successfully
- ✅ Response quality maintained (same output as before)
- ✅ Rate limiting delays visible in logs (60+ seconds between Converse calls)

## Rollback Plan

If the fix causes issues:
1. Remove `OrchestrationType` and `CustomOrchestrationConfiguration` from all agents
2. Deploy stack update (reverts to default orchestration)
3. System returns to previous behavior
4. Custom orchestration Lambda can remain (unused) or be deleted

## Performance Impact

### Expected Changes
- **Execution Time**: Increased by N×60 seconds (where N = number of sequential tool calls)
- **Throughput**: Reduced (serial vs parallel execution)
- **Reliability**: Significantly improved (no throttling)
- **Cost**: Unchanged (same number of API calls, just sequential)

### Example Scenario
- **Before**: Extract requirements → 3 parallel tool calls → 1 minute total → Throttling error
- **After**: Extract requirements → 3 sequential tool calls → 3 minutes total → Success

## Documentation Updates

1. **CLAUDE.md**: Add section on Bedrock Agent orchestration behavior
2. **README.md**: Update performance characteristics section
3. **Test Documentation**: Update timing expectations
4. **Architecture Docs**: Document the prompt override pattern

## References

- AWS Bedrock Custom Orchestration: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-custom-orchestration.html
- AWS CloudFormation AWS::Bedrock::Agent: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-bedrock-agent.html
- AWS Bedrock Agent Orchestration: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-how.html
- Claude Sonnet 4.5 Rate Limits: https://docs.anthropic.com/en/api/rate-limits
