/aws/lambda/autoninja-supervisor-production: 

timestamp,message
1761073090118,"INIT_START Runtime Version: python:3.12.v89	Runtime Version ARN: arn:aws:lambda:us-east-2::runtime:644f999c44288c3dd580a0b58d0576fe347ce4d089106e2c52ed35b626e0fb3c
"
1761073090422,"[INFO]	2025-10-21T18:58:10.422Z		Found credentials in environment variables.
"
1761073090651,"START RequestId: fcb560f5-8304-4333-a094-74147cedb3c8 Version: $LATEST
"
1761073090653,"[INFO]	2025-10-21T18:58:10.653Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:10.652304"", ""level"": ""INFO"", ""message"": ""Lambda handler invoked"", ""function"": ""lambda_handler"", ""event_keys"": [""messageVersion"", ""parameters"", ""inputText"", ""sessionAttributes"", ""promptSessionAttributes"", ""sessionId"", ""httpMethod"", ""apiPath"", ""requestBody"", ""agent"", ""actionGroup""]}
"
1761073090653,"{""timestamp"": ""2025-10-21T18:58:10.652304"", ""level"": ""INFO"", ""message"": ""Lambda handler invoked"", ""function"": ""lambda_handler"", ""event_keys"": [""messageVersion"", ""parameters"", ""inputText"", ""sessionAttributes"", ""promptSessionAttributes"", ""sessionId"", ""httpMethod"", ""apiPath"", ""requestBody"", ""agent"", ""actionGroup""]}
"
1761073090653,"[INFO]	2025-10-21T18:58:10.653Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:10.653427"", ""level"": ""INFO"", ""message"": ""Starting orchestration for request: Build a simple friend agent for emotional support..."", ""function"": ""lambda_handler"", ""session_id"": ""e2e-test-1761073084"", ""request_length"": 49}
"
1761073090653,"{""timestamp"": ""2025-10-21T18:58:10.653427"", ""level"": ""INFO"", ""message"": ""Starting orchestration for request: Build a simple friend agent for emotional support..."", ""function"": ""lambda_handler"", ""session_id"": ""e2e-test-1761073084"", ""request_length"": 49}
"
1761073090653,"[INFO]	2025-10-21T18:58:10.653Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:10.653638"", ""level"": ""INFO"", ""message"": ""Starting orchestration for job: job-friend-20251021-185810"", ""function"": ""lambda_handler"", ""job_name"": ""job-friend-20251021-185810""}
"
1761073090653,"{""timestamp"": ""2025-10-21T18:58:10.653638"", ""level"": ""INFO"", ""message"": ""Starting orchestration for job: job-friend-20251021-185810"", ""function"": ""lambda_handler"", ""job_name"": ""job-friend-20251021-185810""}
"
1761073090653,"[INFO]	2025-10-21T18:58:10.653Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:10.653797"", ""level"": ""INFO"", ""message"": ""Invoking Requirements Analyst"", ""function"": ""lambda_handler""}
"
1761073090653,"{""timestamp"": ""2025-10-21T18:58:10.653797"", ""level"": ""INFO"", ""message"": ""Invoking Requirements Analyst"", ""function"": ""lambda_handler""}
"
1761073090654,"[INFO]	2025-10-21T18:58:10.654Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:10.653964"", ""level"": ""INFO"", ""message"": ""Starting invoke for requirements-analyst"", ""function"": ""invoke_collaborator_with_rate_limiting"", ""agent_id"": ""YWWLBLR4..."", ""input_length"": 95}
"
1761073090654,"{""timestamp"": ""2025-10-21T18:58:10.653964"", ""level"": ""INFO"", ""message"": ""Starting invoke for requirements-analyst"", ""function"": ""invoke_collaborator_with_rate_limiting"", ""agent_id"": ""YWWLBLR4..."", ""input_length"": 95}
"
1761073090654,"{""timestamp"": ""2025-10-21T18:58:10.654121"", ""level"": ""DEBUG"", ""message"": ""Checking global rate limit"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073090984,"[INFO]	2025-10-21T18:58:10.984Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:10.984386"", ""level"": ""INFO"", ""message"": ""No previous rate limit record found, no wait needed"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073090984,"{""timestamp"": ""2025-10-21T18:58:10.984386"", ""level"": ""INFO"", ""message"": ""No previous rate limit record found, no wait needed"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073090984,"{""timestamp"": ""2025-10-21T18:58:10.984729"", ""level"": ""DEBUG"", ""message"": ""Rate limit check completed"", ""function"": ""check_and_enforce_global_rate_limit"", ""duration"": 0.33060669898986816, ""wait_time"": 0.0}
"
1761073090985,"{""timestamp"": ""2025-10-21T18:58:10.984876"", ""level"": ""DEBUG"", ""message"": ""Updating rate limiter for requirements-analyst"", ""function"": ""update_global_rate_limiter_timestamp""}
"
1761073091126,"[INFO]	2025-10-21T18:58:11.126Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:11.125879"", ""level"": ""INFO"", ""message"": ""Updated global rate limiter: requirements-analyst made model invocation"", ""function"": ""update_global_rate_limiter_timestamp"", ""duration"": 0.14099621772766113}
"
1761073091126,"{""timestamp"": ""2025-10-21T18:58:11.125879"", ""level"": ""INFO"", ""message"": ""Updated global rate limiter: requirements-analyst made model invocation"", ""function"": ""update_global_rate_limiter_timestamp"", ""duration"": 0.14099621772766113}
"
1761073102560,"[WARNING]	2025-10-21T18:58:22.560Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:22.560449"", ""level"": ""WARNING"", ""message"": ""Throttling detected for requirements-analyst, retrying in 30.06s"", ""function"": ""invoke_collaborator_with_rate_limiting"", ""attempt"": 1, ""error"": ""An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency."", ""traceback"": ""Traceback (most recent call last):
  File \""/var/task/handler.py\"", line 224, in invoke_collaborator_with_rate_limiting
    for event in response.get('completion', []):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 592, in __iter__
    parsed_event = self._parse_event(event)
                   ^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 608, in _parse_event
    raise EventStreamError(parsed_response, self._operation_name)
botocore.exceptions.EventStreamError: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
""}
"
1761073102560,"{""timestamp"": ""2025-10-21T18:58:22.560449"", ""level"": ""WARNING"", ""message"": ""Throttling detected for requirements-analyst, retrying in 30.06s"", ""function"": ""invoke_collaborator_with_rate_limiting"", ""attempt"": 1, ""error"": ""An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency."", ""traceback"": ""Traceback (most recent call last):
  File \""/var/task/handler.py\"", line 224, in invoke_collaborator_with_rate_limiting
    for event in response.get('completion', []):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 592, in __iter__
    parsed_event = self._parse_event(event)
                   ^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 608, in _parse_event
    raise EventStreamError(parsed_response, self._operation_name)
botocore.exceptions.EventStreamError: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
""}
"
1761073132624,"{""timestamp"": ""2025-10-21T18:58:52.624428"", ""level"": ""DEBUG"", ""message"": ""Checking global rate limit"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073132840,"[INFO]	2025-10-21T18:58:52.840Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:52.839937"", ""level"": ""INFO"", ""message"": ""No previous rate limit record found, no wait needed"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073132840,"{""timestamp"": ""2025-10-21T18:58:52.839937"", ""level"": ""INFO"", ""message"": ""No previous rate limit record found, no wait needed"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073132840,"{""timestamp"": ""2025-10-21T18:58:52.840303"", ""level"": ""DEBUG"", ""message"": ""Rate limit check completed"", ""function"": ""check_and_enforce_global_rate_limit"", ""duration"": 0.2158806324005127, ""wait_time"": 0.0}
"
1761073132840,"{""timestamp"": ""2025-10-21T18:58:52.840437"", ""level"": ""DEBUG"", ""message"": ""Updating rate limiter for requirements-analyst"", ""function"": ""update_global_rate_limiter_timestamp""}
"
1761073132951,"[INFO]	2025-10-21T18:58:52.951Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:58:52.951733"", ""level"": ""INFO"", ""message"": ""Updated global rate limiter: requirements-analyst made model invocation"", ""function"": ""update_global_rate_limiter_timestamp"", ""duration"": 0.11129379272460938}
"
1761073132952,"{""timestamp"": ""2025-10-21T18:58:52.951733"", ""level"": ""INFO"", ""message"": ""Updated global rate limiter: requirements-analyst made model invocation"", ""function"": ""update_global_rate_limiter_timestamp"", ""duration"": 0.11129379272460938}
"
1761073158351,"[WARNING]	2025-10-21T18:59:18.351Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:59:18.351581"", ""level"": ""WARNING"", ""message"": ""Throttling detected for requirements-analyst, retrying in 30.70s"", ""function"": ""invoke_collaborator_with_rate_limiting"", ""attempt"": 2, ""error"": ""An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency."", ""traceback"": ""Traceback (most recent call last):
  File \""/var/task/handler.py\"", line 224, in invoke_collaborator_with_rate_limiting
    for event in response.get('completion', []):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 592, in __iter__
    parsed_event = self._parse_event(event)
                   ^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 608, in _parse_event
    raise EventStreamError(parsed_response, self._operation_name)
botocore.exceptions.EventStreamError: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
""}
"
1761073158351,"{""timestamp"": ""2025-10-21T18:59:18.351581"", ""level"": ""WARNING"", ""message"": ""Throttling detected for requirements-analyst, retrying in 30.70s"", ""function"": ""invoke_collaborator_with_rate_limiting"", ""attempt"": 2, ""error"": ""An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency."", ""traceback"": ""Traceback (most recent call last):
  File \""/var/task/handler.py\"", line 224, in invoke_collaborator_with_rate_limiting
    for event in response.get('completion', []):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 592, in __iter__
    parsed_event = self._parse_event(event)
                   ^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 608, in _parse_event
    raise EventStreamError(parsed_response, self._operation_name)
botocore.exceptions.EventStreamError: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
""}
"
1761073189047,"{""timestamp"": ""2025-10-21T18:59:49.047595"", ""level"": ""DEBUG"", ""message"": ""Checking global rate limit"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073189240,"[INFO]	2025-10-21T18:59:49.240Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:59:49.240505"", ""level"": ""INFO"", ""message"": ""No previous rate limit record found, no wait needed"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073189240,"{""timestamp"": ""2025-10-21T18:59:49.240505"", ""level"": ""INFO"", ""message"": ""No previous rate limit record found, no wait needed"", ""function"": ""check_and_enforce_global_rate_limit""}
"
1761073189240,"{""timestamp"": ""2025-10-21T18:59:49.240821"", ""level"": ""DEBUG"", ""message"": ""Rate limit check completed"", ""function"": ""check_and_enforce_global_rate_limit"", ""duration"": 0.19323039054870605, ""wait_time"": 0.0}
"
1761073189241,"{""timestamp"": ""2025-10-21T18:59:49.240968"", ""level"": ""DEBUG"", ""message"": ""Updating rate limiter for requirements-analyst"", ""function"": ""update_global_rate_limiter_timestamp""}
"
1761073189371,"[INFO]	2025-10-21T18:59:49.371Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T18:59:49.371537"", ""level"": ""INFO"", ""message"": ""Updated global rate limiter: requirements-analyst made model invocation"", ""function"": ""update_global_rate_limiter_timestamp"", ""duration"": 0.13056683540344238}
"
1761073189371,"{""timestamp"": ""2025-10-21T18:59:49.371537"", ""level"": ""INFO"", ""message"": ""Updated global rate limiter: requirements-analyst made model invocation"", ""function"": ""update_global_rate_limiter_timestamp"", ""duration"": 0.13056683540344238}
"
1761073200147,"[WARNING]	2025-10-21T19:00:00.147Z	fcb560f5-8304-4333-a094-74147cedb3c8	{""timestamp"": ""2025-10-21T19:00:00.147637"", ""level"": ""WARNING"", ""message"": ""Throttling detected for requirements-analyst, retrying in 30.08s"", ""function"": ""invoke_collaborator_with_rate_limiting"", ""attempt"": 3, ""error"": ""An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency."", ""traceback"": ""Traceback (most recent call last):
  File \""/var/task/handler.py\"", line 224, in invoke_collaborator_with_rate_limiting
    for event in response.get('completion', []):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 592, in __iter__
    parsed_event = self._parse_event(event)
                   ^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 608, in _parse_event
    raise EventStreamError(parsed_response, self._operation_name)
botocore.exceptions.EventStreamError: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
""}
"
1761073200148,"{""timestamp"": ""2025-10-21T19:00:00.147637"", ""level"": ""WARNING"", ""message"": ""Throttling detected for requirements-analyst, retrying in 30.08s"", ""function"": ""invoke_collaborator_with_rate_limiting"", ""attempt"": 3, ""error"": ""An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency."", ""traceback"": ""Traceback (most recent call last):
  File \""/var/task/handler.py\"", line 224, in invoke_collaborator_with_rate_limiting
    for event in response.get('completion', []):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 592, in __iter__
    parsed_event = self._parse_event(event)
                   ^^^^^^^^^^^^^^^^^^^^^^^^
  File \""/var/lang/lib/python3.12/site-packages/botocore/eventstream.py\"", line 608, in _parse_event
    raise EventStreamError(parsed_response, self._operation_name)
botocore.exceptions.EventStreamError: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
""}
"






aws/lambda/autoninja-requirements-analyst-production: 


timestamp,message
1761073155636,"INIT_START Runtime Version: python:3.12.v89	Runtime Version ARN: arn:aws:lambda:us-east-2::runtime:644f999c44288c3dd580a0b58d0576fe347ce4d089106e2c52ed35b626e0fb3c
"
1761073245945,"START RequestId: cc98d7d8-bd6d-4de2-8c36-2b565485b61d Version: $LATEST
"
1761073245946,"[INFO]	2025-10-21T19:00:45.946Z	cc98d7d8-bd6d-4de2-8c36-2b565485b61d	Processing request for apiPath: /validate-requirements
"
1761073245948,"{""timestamp"": ""2025-10-21T19:00:45.946306Z"", ""level"": ""INFO"", ""logger"": ""handler"", ""message"": ""Processing request for apiPath: /validate-requirements"", ""module"": ""logger"", ""function"": ""_log"", ""line"": 88, ""job_name"": ""job-friend-20251021-185810"", ""agent_name"": ""requirements-analyst"", ""action_name"": ""/validate-requirements""}
"
1761073246055,"[INFO]	2025-10-21T19:00:46.055Z	cc98d7d8-bd6d-4de2-8c36-2b565485b61d	Validating requirements for job: job-friend-20251021-185810
"
1761073246055,"{""timestamp"": ""2025-10-21T19:00:46.055792Z"", ""level"": ""INFO"", ""logger"": ""handler"", ""message"": ""Validating requirements for job: job-friend-20251021-185810"", ""module"": ""logger"", ""function"": ""_log"", ""line"": 88, ""job_name"": ""job-friend-20251021-185810"", ""agent_name"": ""requirements-analyst"", ""action_name"": ""/validate-requirements""}
"
1761073246220,"[INFO]	2025-10-21T19:00:46.219Z	cc98d7d8-bd6d-4de2-8c36-2b565485b61d	Requirements validated successfully for job job-friend-20251021-185810
"
1761073246220,"{""timestamp"": ""2025-10-21T19:00:46.219906Z"", ""level"": ""INFO"", ""logger"": ""handler"", ""message"": ""Requirements validated successfully for job job-friend-20251021-185810"", ""module"": ""logger"", ""function"": ""_log"", ""line"": 88, ""job_name"": ""job-friend-20251021-185810"", ""agent_name"": ""requirements-analyst"", ""action_name"": ""/validate-requirements""}
"
1761073246220,"{""timestamp"": ""2025-10-21T19:00:46.220176Z"", ""level"": ""INFO"", ""logger"": ""handler"", ""message"": ""Request completed successfully in 0.27s"", ""module"": ""logger"", ""function"": ""_log"", ""line"": 88, ""job_name"": ""job-friend-20251021-185810"", ""agent_name"": ""requirements-analyst"", ""action_name"": ""/validate-requirements""}
"
1761073246220,"[INFO]	2025-10-21T19:00:46.220Z	cc98d7d8-bd6d-4de2-8c36-2b565485b61d	Request completed successfully in 0.27s
"
1761073246222,"END RequestId: cc98d7d8-bd6d-4de2-8c36-2b565485b61d
"
1761073246222,"REPORT RequestId: cc98d7d8-bd6d-4de2-8c36-2b565485b61d	Duration: 276.68 ms	Billed Duration: 889 ms	Memory Size: 512 MB	Max Memory Used: 90 MB	Init Duration: 611.77 ms	
XRAY TraceId: 1-68f7d85d-0f0bfbbe2ab8f94854bf83a8	SegmentId: 9c54e4124923ee8f	Sampled: true	
"
1761073289236,"START RequestId: 7126765e-c362-44b0-9e2e-65447b28e438 Version: $LATEST
"
1761073289236,"[INFO]	2025-10-21T19:01:29.236Z	7126765e-c362-44b0-9e2e-65447b28e438	Processing request for apiPath: /extract-requirements
"
1761073289237,"{""timestamp"": ""2025-10-21T19:01:29.236903Z"", ""level"": ""INFO"", ""logger"": ""handler"", ""message"": ""Processing request for apiPath: /extract-requirements"", ""module"": ""logger"", ""function"": ""_log"", ""line"": 88, ""job_name"": ""job-friend-20251021-185810"", ""agent_name"": ""requirements-analyst"", ""action_name"": ""/extract-requirements""}
"
1761073289243,"{""timestamp"": ""2025-10-21T19:01:29.243042Z"", ""level"": ""INFO"", ""logger"": ""handler"", ""message"": ""Extracting requirements for job: job-friend-20251021-185810"", ""module"": ""logger"", ""function"": ""_log"", ""line"": 88, ""job_name"": ""job-friend-20251021-185810"", ""agent_name"": ""requirements-analyst"", ""action_name"": ""/extract-requirements""}
"
1761073289243,"[INFO]	2025-10-21T19:01:29.242Z	7126765e-c362-44b0-9e2e-65447b28e438	Extracting requirements for job: job-friend-20251021-185810
"
1761073289389,"[INFO]	2025-10-21T19:01:29.389Z	7126765e-c362-44b0-9e2e-65447b28e438	Requirements extracted successfully for job job-friend-20251021-185810
"
1761073289389,"{""timestamp"": ""2025-10-21T19:01:29.389318Z"", ""level"": ""INFO"", ""logger"": ""handler"", ""message"": ""Requirements extracted successfully for job job-friend-20251021-185810"", ""module"": ""logger"", ""function"": ""_log"", ""line"": 88, ""job_name"": ""job-friend-20251021-185810"", ""agent_name"": ""requirements-analyst"", ""action_name"": ""/extract-requirements""}
"
1761073289389,"{""timestamp"": ""2025-10-21T19:01:29.389587Z"", ""level"": ""INFO"", ""logger"": ""handler"", ""message"": ""Request completed successfully in 0.15s"", ""module"": ""logger"", ""function"": ""_log"", ""line"": 88, ""job_name"": ""job-friend-20251021-185810"", ""agent_name"": ""requirements-analyst"", ""action_name"": ""/extract-requirements""}
"
1761073289389,"[INFO]	2025-10-21T19:01:29.389Z	7126765e-c362-44b0-9e2e-65447b28e438	Request completed successfully in 0.15s
"
1761073289391,"END RequestId: 7126765e-c362-44b0-9e2e-65447b28e438
"
1761073289391,"REPORT RequestId: 7126765e-c362-44b0-9e2e-65447b28e438	Duration: 154.90 ms	Billed Duration: 155 ms	Memory Size: 512 MB	Max Memory Used: 90 MB	
XRAY TraceId: 1-68f7d889-129879857058863f5436f351	SegmentId: 9295a73e1f108890	Sampled: true	
"


2025-10-21 14:58:04,025 - INFO - AutoNinja End-to-End Orchestration Test
2025-10-21 14:58:04,025 - INFO - Supervisor Agent ID: RD5P02TYHO
2025-10-21 14:58:04,026 - INFO - Supervisor Alias ID: VXDMLS0YZJ

2025-10-21 14:58:04,026 - INFO - AWS Region: us-east-2
2025-10-21 14:58:04,026 - INFO - AWS Profile: AdministratorAccess-784327326356
2025-10-21 14:58:04,026 - INFO - DynamoDB Table: autoninja-inference-records-production
2025-10-21 14:58:04,026 - INFO - S3 Bucket: autoninja-artifacts-784327326356-production
2025-10-21 14:58:04,026 - INFO -
================================================================================
2025-10-21 14:58:04,026 - INFO - STARTING END-TO-END ORCHESTRATION TEST
2025-10-21 14:58:04,026 - INFO - ================================================================================
2025-10-21 14:58:04,026 - INFO -
### STEP 1: Invoke Supervisor (Orchestrates All Agents) ###
2025-10-21 14:58:04,026 - INFO - ================================================================================
2025-10-21 14:58:04,026 - INFO - INVOKING SUPERVISOR AGENT
2025-10-21 14:58:04,026 - INFO - Agent ID: RD5P02TYHO
2025-10-21 14:58:04,026 - INFO - Alias ID: VXDMLS0YZJ
2025-10-21 14:58:04,026 - INFO - Session ID: e2e-test-1761073084
2025-10-21 14:58:04,026 - INFO - Prompt: Build a simple friend agent for emotional support
2025-10-21 14:58:04,026 - INFO - ================================================================================
2025-10-21 14:58:04,035 - INFO - Loading cached SSO token for autoninja
2025-10-21 14:59:10,205 - ERROR - ✗ Failed to invoke supervisor: AWSHTTPSConnectionPool(host='bedrock-agent-runtime.us-east-2.amazonaws.com', port=443): Read timed out.
2025-10-21 14:59:10,205 - ERROR - ✗ Test failed with exception: AWSHTTPSConnectionPool(host='bedrock-agent-runtime.us-east-2.amazonaws.com', port=443): Read timed out.
Traceback (most recent call last):
  File "/home/mcesel/Documents/proj/autoninja2/venv/lib/python3.12/site-packages/urllib3/response.py", line 779, in _error_catcher
    yield
  File "/home/mcesel/Documents/proj/autoninja2/venv/lib/python3.12/site-packages/urllib3/response.py", line 1248, in read_chunked
    self._update_chunk_length()
  File "/home/mcesel/Documents/proj/autoninja2/venv/lib/python3.12/site-packages/urllib3/response.py", line 1167, in _update_chunk_length
    line = self._fp.fp.readline()  # type: ignore[union-attr]
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/socket.py", line 707, in readinto
    return self._sock.recv_into(b)
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/ssl.py", line 1252, in recv_into
    return self.read(nbytes, buffer)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/ssl.py", line 1104, in read
    return self._sslobj.read(len, buffer)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TimeoutError: The read operation timed out

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/mcesel/Documents/proj/autoninja2/tests/supervisor/test_e2e.py", line 362, in test_e2e_orchestration
    supervisor_result = invoke_supervisor(prompt)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mcesel/Documents/proj/autoninja2/tests/supervisor/test_e2e.py", line 96, in invoke_supervisor
    for event in response.get('completion', []):
  File "/home/mcesel/Documents/proj/autoninja2/venv/lib/python3.12/site-packages/botocore/eventstream.py", line 591, in __iter__
    for event in self._event_generator:
  File "/home/mcesel/Documents/proj/autoninja2/venv/lib/python3.12/site-packages/botocore/eventstream.py", line 598, in _create_raw_event_generator
    for chunk in self._raw_stream.stream():
  File "/home/mcesel/Documents/proj/autoninja2/venv/lib/python3.12/site-packages/urllib3/response.py", line 1088, in stream
    yield from self.read_chunked(amt, decode_content=decode_content)
  File "/home/mcesel/Documents/proj/autoninja2/venv/lib/python3.12/site-packages/urllib3/response.py", line 1231, in read_chunked
    with self._error_catcher():
  File "/usr/lib/python3.12/contextlib.py", line 158, in __exit__
    self.gen.throw(value)
  File "/home/mcesel/Documents/proj/autoninja2/venv/lib/python3.12/site-packages/urllib3/response.py", line 784, in _error_catcher
    raise ReadTimeoutError(self._pool, None, "Read timed out.") from e  # type: ignore[arg-type]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
urllib3.exceptions.ReadTimeoutError: AWSHTTPSConnectionPool(host='bedrock-agent-runtime.us-east-2.amazonaws.com', port=443): Read timed out.
2025-10-21 14:59:10,208 - INFO -
================================================================================
2025-10-21 14:59:10,208 - INFO - TEST RESULTS SUMMARY
2025-10-21 14:59:10,208 - INFO - ================================================================================
2025-10-21 14:59:10,208 - INFO - ✗ FAIL - Supervisor Invocation
2025-10-21 14:59:10,208 - INFO - ✗ FAIL - Cloudwatch Logs
2025-10-21 14:59:10,209 - INFO - ✗ FAIL - Dynamodb Records
2025-10-21 14:59:10,209 - INFO - ✗ FAIL - S3 Artifacts
2025-10-21 14:59:10,209 - INFO - ✗ FAIL - Cloudformation Deployment
2025-10-21 14:59:10,209 - INFO - ================================================================================
2025-10-21 14:59:10,209 - INFO - TOTAL: 0/5 tests passed
2025-10-21 14:59:10,209 - INFO - ================================================================================
2025-10-21 14:59:10,209 - INFO -
================================================================================
2025-10-21 14:59:10,209 - INFO - TESTING VALIDATION FAILURE PATH
2025-10-21 14:59:10,209 - INFO - ================================================================================
2025-10-21 14:59:10,209 - INFO - ================================================================================
2025-10-21 14:59:10,209 - INFO - INVOKING SUPERVISOR AGENT
2025-10-21 14:59:10,209 - INFO - Agent ID: RD5P02TYHO
2025-10-21 14:59:10,209 - INFO - Alias ID: VXDMLS0YZJ
2025-10-21 14:59:10,209 - INFO - Session ID: e2e-test-1761073150
2025-10-21 14:59:10,209 - INFO - Prompt: Build an invalid agent with contradictory requirements
2025-10-21 14:59:10,209 - INFO - ================================================================================
2025-10-21 14:59:13,527 - ERROR - ✗ Failed to invoke supervisor: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.
2025-10-21 14:59:13,527 - ERROR - Validation failure test error: An error occurred (throttlingException) when calling the InvokeAgent operation: Your request rate is too high. Reduce the frequency of requests. Check your Bedrock model invocation quotas to find the acceptable frequency.