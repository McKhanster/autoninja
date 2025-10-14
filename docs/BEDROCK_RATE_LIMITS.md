# AWS Bedrock Rate Limits and Quotas

## Overview
This document tracks the rate limits and quotas for AWS Bedrock models used in the AutoNinja system.

## On-Demand Throughput Limits

### Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)

**Default On-Demand Limits (Free Tier / Standard):**
- **Requests Per Minute (RPM)**: ~1 request/minute (based on testing with Claude Sonnet 4.5)
- **Tokens Per Minute (TPM)**: Varies based on model and region
- **Concurrent Requests**: Limited

**Observed Behavior:**
- Throttling occurs when making requests less than 60 seconds apart
- Error: `throttlingException: Your request rate is too high`
- **Recommended interval between requests: 60 seconds minimum**
- Actual limit may vary by region, account age, and usage history

## Testing Recommendations

### Sequential Testing
When running multiple tests against Bedrock agents:
1. Add 15-second pauses between test invocations
2. Monitor for throttling errors
3. Implement exponential backoff for retries

### Example Test Timing
```python
# Test 1
invoke_agent(...)
time.sleep(15)  # Wait 15 seconds

# Test 2
invoke_agent(...)
time.sleep(15)  # Wait 15 seconds

# Test 3
invoke_agent(...)
```

## Quota Increases

To request higher limits:
1. Go to AWS Service Quotas console
2. Navigate to Amazon Bedrock quotas
3. Search for specific model quotas
4. Request quota increase with justification

**Common Quotas to Increase:**
- Model invocation requests per minute
- Tokens per minute
- Concurrent requests

## Production Considerations

### For Production Workloads
Consider using **Provisioned Throughput** instead of on-demand:
- Guaranteed capacity
- No throttling
- Predictable costs
- Higher throughput

### Cost vs Performance Trade-offs
- **On-Demand**: Pay per request, subject to throttling, good for development/testing
- **Provisioned**: Fixed hourly cost, no throttling, good for production

## Regional Variations

Rate limits may vary by region:
- **us-east-1**: Typically higher limits
- **us-east-2**: Standard limits (our deployment region)
- **us-west-2**: Standard limits

## Monitoring

### CloudWatch Metrics
Monitor these metrics to track usage:
- `ModelInvocations`
- `ModelInvocationThrottles`
- `ModelInvocationLatency`

### Setting Up Alarms
Create CloudWatch alarms for:
- Throttling rate > 5%
- High latency (> 10 seconds)
- Failed invocations

## References

- [AWS Bedrock Quotas](https://docs.aws.amazon.com/general/latest/gr/bedrock.html)
- [Request Quota Increase](https://console.aws.amazon.com/servicequotas/home/services/bedrock/quotas)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)

## Last Updated
2025-10-14

## Notes
- Rate limits are subject to change by AWS
- Actual limits may vary based on account age, usage history, and region
- Always test in your specific environment to determine actual limits
