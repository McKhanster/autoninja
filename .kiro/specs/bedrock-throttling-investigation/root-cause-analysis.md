# Root Cause Analysis: Bedrock Agent Throttling

## Problem Statement

When testing the Requirements Analyst Bedrock Agent (`tests/requirements-analyst/test_requirements_analyst_agent.py`), throttling errors occur due to Bedrock Agent's automatic successive calls to the foundation model, which exceed Claude Sonnet 4.5's rate limit (~1 request per minute for on-demand models).

## Investigation Findings

### 1. AWS Bedrock Agent Default Orchestration Behavior

AWS Bedrock Agents use a **default orchestration prompt** that includes the following instruction:

```
"ALWAYS optimize the plan by using multiple function calls at the same time whenever possible."
```

This instruction causes the agent to:
- Make parallel tool/function calls when it determines multiple actions can be performed concurrently
- Trigger multiple simultaneous Converse API calls to the foundation model
- Exceed the rate limit for Claude Sonnet 4.5 (approximately 1 RPM for on-demand models)

### 2. Evidence from Test Execution

From `tests/requirements-analyst/test_requirements_analyst_agent.py`:
- The test includes a `BedrockRateLimiter` with 60-second intervals between tests
- Despite this rate limiting, throttling errors still occur
- The throttling happens **within a single test**, not between tests
- This indicates the agent itself is making multiple rapid calls during orchestration

### 3. Why the Rate Limiter Doesn't Help

The existing `BedrockRateLimiter` in the test file only controls the interval between **user-initiated test invocations**. It does NOT control:
- How many times Bedrock Agent internally calls the foundation model during orchestration
- Parallel tool execution decisions made by the agent's orchestration layer
- Retry logic built into AWS's managed orchestration

### 4. AWS Documentation Reference

According to AWS Bedrock Agents documentation on **Advanced Prompts**:
- Bedrock Agents have a default orchestration template
- This template can be overridden using `PromptOverrideConfiguration`
- The orchestration prompt controls how the agent plans and executes tool calls
- You can modify the orchestration template to enforce sequential execution

## Root Cause

**The root cause is AWS Bedrock's default orchestration prompt that encourages parallel tool execution, which is incompatible with Claude Sonnet 4.5's strict rate limits on on-demand inference.**

The problematic instruction is NOT in our codebase—it's part of AWS's managed Bedrock Agent service. Therefore, we cannot fix this by modifying our Lambda functions, test code, or application logic.

## Why This Happens Specifically with Claude Sonnet 4.5

1. **Model Rate Limits**: Claude Sonnet 4.5 on-demand has approximately 1 RPM rate limit
2. **Parallel Execution**: Bedrock Agent's default prompt encourages concurrent tool calls
3. **Multiple Converse API Calls**: Each tool invocation triggers a Converse API call
4. **Rate Limit Exceeded**: When 2+ tools are called in parallel, the rate limit is instantly exceeded

## Solution Approach

The solution is to use AWS Bedrock's **Advanced Prompts** feature to:
1. Override the default orchestration template
2. Remove or modify the instruction about parallel tool execution
3. Add explicit instruction to execute tools sequentially
4. Maintain a reasonable delay between tool executions

This must be configured in the CloudFormation template using the `PromptOverrideConfiguration` property for each Bedrock Agent.

## Impact on System Behavior

### Before Fix (Current State)
- Agent receives user request
- Agent plans to use multiple tools
- Agent executes tools in parallel (per default prompt)
- Multiple simultaneous Converse API calls
- Throttling errors occur

### After Fix (Expected State)
- Agent receives user request
- Agent plans to use multiple tools
- Agent executes tools sequentially (per overridden prompt)
- Single Converse API call at a time
- No throttling errors

### Trade-offs
- **Slower execution time**: Sequential tool execution will take longer than parallel
- **Better reliability**: No throttling errors
- **Predictable behavior**: Easier to reason about and debug

## Implementation Requirements

1. **CloudFormation Changes**: Add `PromptOverrideConfiguration` to all Bedrock Agent resources
2. **Orchestration Template**: Create custom orchestration prompt that enforces sequential execution
3. **Test Updates**: Update test expectations for sequential execution timing
4. **Documentation**: Update CLAUDE.md with the orchestration behavior

## References

- AWS Bedrock Agents Advanced Prompts: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-advanced-prompts.html
- AWS Bedrock Agent CloudFormation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-bedrock-agent.html
- Claude Sonnet 4.5 Rate Limits: https://docs.anthropic.com/en/api/rate-limits
