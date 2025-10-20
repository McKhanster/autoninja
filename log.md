Analysis of the Throttling Issue
The throttling error you're experiencing is occurring at the Bedrock Agent Runtime level, specifically with the InvokeAgent API call. From the logs, I can see:

ERROR: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
Root Cause Analysis
The Issue is NOT with your rate limiting implementation - Your AgentCore Memory-based rate limiting code in lambda/supervisor-agentcore/handler.py is correctly implemented with a 30-second minimum interval.

The Issue is with Bedrock Agent Runtime quotas - The throttling is happening at the AWS service level before your rate limiting logic even gets a chance to work.

Multiple rapid invocations - Looking at the test logs, you're making two rapid test invocations (test sessions 1760892208 and 1760892229) which are triggering the service-level throttling.

Key Findings from AWS Documentation
From my research of the AWS Bedrock quotas documentation, I found that while there are extensive quotas for model inference (InvokeModel), the specific quota for InvokeAgent requests per second is not clearly documented in the general quotas. However, based on the error message and typical AWS patterns, Bedrock Agents likely have:

Very low TPS limits (likely 1-5 requests per second per account)
Burst capacity limitations
Account-level throttling across all agents
Why Your Rate Limiting Isn't Preventing This
Your current rate limiting implementation has a logical gap:

Your rate limiter only activates WITHIN agent invocations - It controls the rate between collaborator agent calls within a single supervisor invocation
It doesn't control the rate of supervisor invocations themselves - Multiple test runs or user requests can still hit the supervisor rapidly
The throttling happens at the entry point - Before your Lambda function even executes
Solutions
Immediate Fix (Deploy and Test)
Add delays between test runs:

# Instead of running tests back-to-back, add delays
python tests/supervisor/test_supervisor.py
sleep 60  # Wait 1 minute between tests
python tests/supervisor/test_supervisor.py
Implement request-level rate limiting in your test script:

import time

def test_with_rate_limiting():
    # Add a delay before each test
    time.sleep(30)  # 30 second delay
    return invoke_supervisor_agent(agent_id, alias_id, prompt)
Long-term Solutions
Request quota increases through AWS Support for:

InvokeAgent requests per second
Bedrock Agent Runtime quotas
Implement application-level rate limiting before calling the supervisor:

# Add to your application layer
last_supervisor_call = get_last_call_time()
if time.time() - last_supervisor_call < 30:
    wait_time = 30 - (time.time() - last_supervisor_call)
    time.sleep(wait_time)
Use exponential backoff in your test scripts and applications when calling the supervisor.

Recommended Next Steps
Deploy the current supervisor (your rate limiting implementation is correct)
Modify your test script to add delays between invocations
Test with proper spacing (30+ seconds between calls)
Monitor CloudWatch logs to verify the internal rate limiting is working
Request quota increases if you need higher throughput
The throttling issue is a service-level constraint, not a bug in your implementation. Your AgentCore Memory-based rate limiting will work correctly for the internal orchestration between collaborator agents.

Credits used: 5.78
Elapsed time: 8m 27s