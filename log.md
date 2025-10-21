INIT_START Runtime Version: python:3.12.v89	Runtime Version ARN: arn:aws:lambda:us-east-2::runtime:644f999c44288c3dd580a0b58d0576fe347ce4d089106e2c52ed35b626e0fb3c
[INFO]	2025-10-21T12:19:33.556Z		Found credentials in environment variables.
START RequestId: f89a64a5-e8dc-4a7a-a6ad-db83119ff44e Version: $LATEST
[INFO]	2025-10-21T12:19:34.069Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	Starting orchestration for request: Build a simple friend agent for emotional support...
[INFO]	2025-10-21T12:19:34.069Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:19:34.069333] Starting orchestration for job: job-friend-20251021-121934
[2025-10-21T12:19:34.069333] Starting orchestration for job: job-friend-20251021-121934
[INFO]	2025-10-21T12:19:34.515Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:19:34.515276] Updated global rate limiter: requirements-analyst made model invocation
[2025-10-21T12:19:34.515276] Updated global rate limiter: requirements-analyst made model invocation
[INFO]	2025-10-21T12:19:44.245Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:19:44.245328] Throttling detected for requirements-analyst, retrying in 1.34s (attempt 1)
[2025-10-21T12:19:44.245328] Throttling detected for requirements-analyst, retrying in 1.34s (attempt 1)
[INFO]	2025-10-21T12:19:45.951Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:19:45.951211] Updated global rate limiter: requirements-analyst made model invocation
[2025-10-21T12:19:45.951211] Updated global rate limiter: requirements-analyst made model invocation
[INFO]	2025-10-21T12:19:49.533Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:19:49.533749] Throttling detected for requirements-analyst, retrying in 2.35s (attempt 2)
[2025-10-21T12:19:49.533749] Throttling detected for requirements-analyst, retrying in 2.35s (attempt 2)
[INFO]	2025-10-21T12:19:52.249Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:19:52.249830] Updated global rate limiter: requirements-analyst made model invocation
[2025-10-21T12:19:52.249830] Updated global rate limiter: requirements-analyst made model invocation
[INFO]	2025-10-21T12:19:55.617Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:19:55.617781] Throttling detected for requirements-analyst, retrying in 4.04s (attempt 3)
[2025-10-21T12:19:55.617781] Throttling detected for requirements-analyst, retrying in 4.04s (attempt 3)
[INFO]	2025-10-21T12:19:59.959Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:19:59.959384] Updated global rate limiter: requirements-analyst made model invocation
[2025-10-21T12:19:59.959384] Updated global rate limiter: requirements-analyst made model invocation
[INFO]	2025-10-21T12:20:09.798Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:20:09.798275] Throttling detected for requirements-analyst, retrying in 8.68s (attempt 4)
[2025-10-21T12:20:09.798275] Throttling detected for requirements-analyst, retrying in 8.68s (attempt 4)
[INFO]	2025-10-21T12:20:18.961Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:20:18.961822] Updated global rate limiter: requirements-analyst made model invocation
[2025-10-21T12:20:18.961822] Updated global rate limiter: requirements-analyst made model invocation
[INFO]	2025-10-21T12:20:22.101Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:20:22.101319] Failed to invoke requirements-analyst after 5 attempts: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
[INFO]	2025-10-21T12:20:22.101Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	[2025-10-21T12:20:22.101485] Error in supervisor orchestration: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
[2025-10-21T12:20:22.101319] Failed to invoke requirements-analyst after 5 attempts: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
[ERROR]	2025-10-21T12:20:22.101Z	f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	Orchestration error: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
[2025-10-21T12:20:22.101485] Error in supervisor orchestration: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
END RequestId: f89a64a5-e8dc-4a7a-a6ad-db83119ff44e
REPORT RequestId: f89a64a5-e8dc-4a7a-a6ad-db83119ff44e	Duration: 48034.79 ms	Billed Duration: 48895 ms	Memory Size: 512 MB	Max Memory Used: 97 MB	Init Duration: 859.43 ms	
XRAY TraceId: 1-68f77a55-1b6d5e656828c14463db47b1	SegmentId: a11737b016c69f59	Sampled: true	