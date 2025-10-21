# Requirements: Bedrock Agent Throttling Fix

## Problem Statement

AWS Bedrock Agents are experiencing throttling errors when invoking Claude Sonnet 4.5 due to the default orchestration behavior that makes parallel tool calls, exceeding the model's rate limit (~1 request per minute for on-demand models).

## Business Requirements

### BR-1: Eliminate Throttling Errors
**Priority**: P0 (Critical)
**Description**: The system must not encounter `ThrottlingException` errors when executing agent workflows.
**Success Criteria**: Zero throttling errors in test execution and production usage.

### BR-2: Maintain Functionality
**Priority**: P0 (Critical)
**Description**: All agent capabilities must continue to work as before, with no loss of functionality.
**Success Criteria**: All existing tests pass with identical outputs.

### BR-3: Predictable Execution Time
**Priority**: P1 (High)
**Description**: Agent execution time must be predictable and documented.
**Success Criteria**: Execution time increases linearly with number of tool calls (N tools × 60 seconds).

## Technical Requirements

### TR-1: Custom Orchestration Implementation
**Description**: Implement AWS Bedrock's Custom Orchestration feature using a Lambda function.
**Components**:
- New Lambda function: `lambda/custom-orchestration/handler.py`
- State machine for orchestration flow (START → MODEL_INVOKED → TOOL_INVOKED → FINAL_RESPONSE)
- Rate limiting logic (minimum 60 seconds between Converse API calls)
- Comprehensive logging and error handling

### TR-2: CloudFormation Updates
**Description**: Update infrastructure to support custom orchestration.
**Components**:
- New `CustomOrchestrationFunction` Lambda resource
- New `CustomOrchestrationRole` IAM role with permissions:
  - `bedrock:InvokeModel`
  - `bedrock:Converse`
  - `lambda:InvokeFunction` (for action groups)
  - CloudWatch Logs permissions
- New `CustomOrchestrationLambdaPermission` allowing Bedrock to invoke the Lambda
- Update ALL 6 agents with:
  - `OrchestrationType: CUSTOM_ORCHESTRATION`
  - `CustomOrchestrationConfiguration` pointing to the Lambda

### TR-3: Sequential Tool Execution
**Description**: Enforce sequential (not parallel) tool execution.
**Implementation**:
- When model returns multiple tool calls, execute only the first one
- Wait for tool completion before proceeding to next tool
- Apply rate limiting delay (60+ seconds) between Converse API calls
- Continue until all tools are executed or final response is reached

### TR-4: Consistent Configuration Across Agents
**Description**: All 6 agents must have identical custom orchestration configuration.
**Affected Agents**:
1. Requirements Analyst Agent
2. Code Generator Agent
3. Solution Architect Agent
4. Quality Validator Agent
5. Deployment Manager Agent
6. Supervisor Agent

**Requirement**: Any configuration change to one agent's orchestration must be applied to all agents.

### TR-5: Observability and Monitoring
**Description**: Provide visibility into orchestration behavior.
**Requirements**:
- Log each state transition (START, MODEL_INVOKED, TOOL_INVOKED, FINAL_RESPONSE)
- Log rate limiting delays
- Log tool invocation details (which tool, parameters, result)
- Include timing information for each step
- Use structured JSON logging for easy parsing

### TR-6: Error Handling and Recovery
**Description**: Handle errors gracefully without causing system failures.
**Requirements**:
- Catch and log all exceptions in custom orchestration Lambda
- Return appropriate error responses to Bedrock Agent
- Don't retry on throttling (let rate limiting prevent it)
- Log errors to CloudWatch for debugging

## Acceptance Criteria

### AC-1: No Throttling Errors
- ✅ Run `tests/requirements-analyst/test_requirements_analyst_agent.py` - zero ThrottlingException errors
- ✅ Run all agent tests - zero ThrottlingException errors
- ✅ Monitor CloudWatch logs - no throttling errors in 24-hour period

### AC-2: Sequential Execution Verified
- ✅ CloudWatch logs show state transitions in sequence
- ✅ Timestamps between tool calls show 60+ second delays
- ✅ No evidence of parallel tool invocations

### AC-3: All Tests Pass
- ✅ `tests/requirements-analyst/test_requirements_analyst_agent.py` - all tests pass
- ✅ All other agent tests pass
- ✅ Response quality identical to before (verified manually)

### AC-4: Configuration Consistency
- ✅ All 6 agents have `OrchestrationType: CUSTOM_ORCHESTRATION`
- ✅ All 6 agents reference the same `CustomOrchestrationFunction`
- ✅ CloudFormation template validates successfully
- ✅ Stack updates successfully without errors

### AC-5: Observability
- ✅ Custom orchestration logs visible in CloudWatch
- ✅ Logs include state transitions, tool calls, timing, and rate limiting delays
- ✅ Logs are structured JSON format
- ✅ Can trace execution flow from logs

### AC-6: Documentation Updated
- ✅ CLAUDE.md includes section on custom orchestration
- ✅ README.md updated with new performance characteristics
- ✅ Test documentation updated with timing expectations
- ✅ Architecture documentation includes custom orchestration

## Non-Functional Requirements

### NFR-1: Performance
- **Requirement**: System must complete single-agent workflows within reasonable time
- **Metric**: N tool calls should take approximately N × 60 seconds (plus model inference time)
- **Acceptable Range**: N × 60 seconds ± 10 seconds

### NFR-2: Reliability
- **Requirement**: System must be 100% reliable with no throttling errors
- **Metric**: Zero ThrottlingException errors in production
- **Target**: 100% success rate

### NFR-3: Maintainability
- **Requirement**: Custom orchestration Lambda must be easy to modify and debug
- **Implementation**:
  - Clear code structure with comments
  - Comprehensive logging
  - Unit tests for state machine logic
  - Follows AutoNinja implementation patterns

### NFR-4: Cost
- **Requirement**: Solution must not significantly increase AWS costs
- **Impact**:
  - One additional Lambda function (minimal invocations)
  - Same number of Converse API calls (just sequential, not parallel)
  - Negligible cost increase

## Out of Scope

The following are explicitly out of scope for this fix:

1. **Provisioned Throughput**: Not migrating to provisioned throughput models
2. **Different Model**: Not switching to a different foundation model
3. **Parallel Execution Optimization**: Not attempting to optimize for parallel execution (that's what causes throttling)
4. **Multi-Agent Orchestration**: Not changing supervisor-collaborator patterns
5. **Request Batching**: Not implementing request batching or queuing

## Dependencies

### DEP-1: AWS Bedrock Custom Orchestration Feature
- **Status**: Available (GA)
- **Region**: us-east-2 (confirmed available)

### DEP-2: Claude Sonnet 4.5 Model
- **Model ID**: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- **Rate Limit**: ~1 RPM for on-demand
- **Status**: Available in us-east-2

### DEP-3: Existing Infrastructure
- **Requirements**:
  - All 6 agents deployed and functional
  - CloudFormation stack: `autoninja-production`
  - S3 bucket for Lambda code
  - DynamoDB table for inference records

## Risks and Mitigations

### RISK-1: Increased Execution Time
- **Risk**: Sequential execution will be slower than parallel execution
- **Impact**: Medium - workflows will take longer to complete
- **Mitigation**: Document expected timing, adjust test timeouts
- **Decision**: Acceptable trade-off for reliability

### RISK-2: CloudFormation Update Failure
- **Risk**: Stack update could fail if configuration is invalid
- **Impact**: High - could break existing agents
- **Mitigation**:
  - Validate CloudFormation template before deployment
  - Test in non-production environment first
  - Have rollback plan ready

### RISK-3: Custom Orchestration Bugs
- **Risk**: Custom orchestration Lambda could have bugs
- **Impact**: High - could break all agents
- **Mitigation**:
  - Comprehensive unit testing
  - Integration testing before production deployment
  - Detailed logging for debugging
  - Rollback plan (revert to default orchestration)

## Success Metrics

- **Primary**: Zero throttling errors in 30-day period post-deployment
- **Secondary**: All tests passing with 100% success rate
- **Tertiary**: Execution time predictable and documented

## Timeline

- **Phase 1** (Custom Orchestration Lambda): 1 day
- **Phase 2** (CloudFormation Updates): 1 day
- **Phase 3** (Testing and Validation): 1 day
- **Total**: 3 days

## Approval

This requirements document must be reviewed and approved before implementation begins.
