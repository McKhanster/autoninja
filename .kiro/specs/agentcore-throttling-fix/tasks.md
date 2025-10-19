# Implementation Plan

## Overview

This implementation plan enhances the existing AutoNinja system with AgentCore capabilities and resolves throttling issues. The approach uses **AgentCore Memory for distributed rate limiting** and **adds AgentCore Runtime as an enhanced supervisor** while keeping the existing 5 collaborator Bedrock Agents unchanged.

**Key Strategy**: 
- Keep existing CloudFormation-based Bedrock supervisor agent unchanged
- Enhance supervisor with AgentCore Memory for rate limiting
- Add AgentCore Runtime capabilities via CloudFormation
- Use AgentCore Memory to store rate limiting data instead of DynamoDB
- Meet hackathon requirement of "at least 1 AgentCore primitive"

## Task List

- [ ] 1. Add AgentCore Memory for Rate Limiting

  - Add AWS::BedrockAgentCore::Memory resource to CloudFormation template
  - Configure Memory with 30-day event expiry for rate limiting data
  - Create IAM role for Memory access with appropriate permissions
  - Add Memory ID to stack outputs for AgentCore Runtime access
  - _Requirements: 2.1, 2.2, 4.1, 4.2_

- [ ] 2. Enhance Existing Supervisor with AgentCore Memory

  - [ ] 2.1 Update existing supervisor Lambda function

    - Modify lambda/supervisor/handler.py to use AgentCore Memory API for rate limiting
    - Replace DynamoDB rate limiting calls with AgentCore Memory API calls
    - Keep existing Bedrock Agent orchestration logic unchanged
    - Add exponential backoff retry logic for throttling exceptions
    - Update environment variables to include MEMORY_ID
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2_

  - [ ] 2.2 Implement Memory-based global rate limiting

    - Use bedrock-agentcore client to store/retrieve GLOBAL model invocation timestamps
    - Implement check_and_enforce_global_rate_limit() function using StoreMemoryRecord/RetrieveMemoryRecords APIs
    - Implement update_global_rate_limiter_timestamp() function using StoreMemoryRecord API
    - Configure 30-second minimum interval between ANY model invocations (including supervisor)
    - Ensure supervisor itself adheres to 30-second rate limit before making its own model calls
    - Add proper error handling for AgentCore Memory API calls
    - Remove existing DynamoDB rate limiting code from current implementation
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 4.1, 4.2, 4.4_

  - [ ] 2.3 Update Lambda dependencies and configuration

    - Update existing Lambda requirements to include bedrock-agentcore SDK
    - Update CloudFormation template to add MEMORY_ID environment variable to supervisor Lambda
    - Ensure existing environment variables remain unchanged
    - _Requirements: 1.9, 2.1_

- [ ] 3. Add AgentCore CloudFormation Resources

  - [ ] 3.1 Add AgentCore Memory resource

    - Add AWS::BedrockAgentCore::Memory resource to CloudFormation template
    - Configure Name: autoninja-rate-limiter-memory
    - Set EventExpiryDuration: 30 days
    - Add appropriate tags and description
    - _Requirements: 4.1, 4.2_

  - [ ] 3.2 Add AgentCore Runtime resource

    - Add AWS::BedrockAgentCore::Runtime resource to CloudFormation template
    - Configure AgentRuntimeName: autoninja-supervisor-runtime
    - Set up AgentRuntimeArtifact pointing to ECR image
    - Configure environment variables for collaborator agent access
    - Add Memory ID environment variable
    - _Requirements: 1.1, 1.2, 1.7, 1.8_

  - [ ] 3.3 Create IAM roles for AgentCore

    - Create IAM role for AgentCore Memory access
    - Create IAM role for AgentCore Runtime execution
    - Add permissions for bedrock-agent:InvokeAgent on collaborators
    - Add permissions for bedrock-agentcore:* on Memory resource
    - Add CloudWatch Logs permissions
    - _Requirements: 1.9, 7.1, 7.2_

  - [ ] 3.4 Update stack outputs

    - Add AgentCore Memory ID output
    - Add AgentCore Runtime ARN output
    - Add invocation commands for both supervisor options
    - Update documentation to show hybrid approach
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 4. Create Deployment Scripts

  - [ ] 4.1 Create AgentCore deployment script

    - Create scripts/deploy_agentcore_supervisor.sh
    - Implement agentcore configure and agentcore launch commands
    - Extract collaborator agent IDs from CloudFormation outputs
    - Set environment variables for AgentCore Runtime
    - Update CloudFormation stack with AgentCore Runtime ARN
    - _Requirements: 1.7, 1.8, 7.1_

  - [ ] 4.2 Update existing deployment scripts

    - Modify scripts/deploy_nested_stacks.sh to include AgentCore resources
    - Add conditional deployment of AgentCore components
    - Ensure backward compatibility with existing supervisor
    - _Requirements: 7.1, 7.2_

- [ ] 5. Implement Enhanced Throttling Protection

  - [ ] 5.1 Add exponential backoff with jitter

    - Implement retry logic with exponential backoff (1s, 2s, 4s, 8s, 16s)
    - Add random jitter to prevent thundering herd
    - Configure maximum 5 retry attempts
    - Log all throttling events to CloudWatch
    - _Requirements: 2.1, 2.2, 2.5, 2.6, 8.1, 8.2_

  - [ ] 5.2 Add CloudWatch metrics for throttling

    - Send custom metrics for throttling events
    - Track rate limiting wait times
    - Monitor AgentCore Memory usage
    - Create CloudWatch dashboard for monitoring
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 6. Testing and Validation

  - [ ] 6.1 Create unit tests for enhanced supervisor

    - Test Memory-based rate limiting functions
    - Test exponential backoff retry logic
    - Test sequential agent orchestration
    - Verify proper error handling
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ] 6.2 Create integration tests

    - Test end-to-end workflow with enhanced supervisor using AgentCore Memory
    - Verify no throttling exceptions occur
    - Test enhanced architecture (Bedrock agents with AgentCore Memory)
    - Validate Memory-based rate limiting effectiveness
    - _Requirements: 5.1, 5.2, 5.7, 5.8_

  - [ ] 6.3 Create load tests

    - Test concurrent invocations with rate limiting
    - Verify system handles multiple requests without throttling
    - Test Memory consistency across distributed requests
    - Validate performance under load
    - _Requirements: 5.5, 8.7, 8.9_

- [ ] 7. Documentation and Hackathon Preparation

  - [ ] 7.1 Update architecture documentation

    - Document hybrid architecture approach
    - Highlight AgentCore Memory usage for rate limiting
    - Show AgentCore Runtime supervisor implementation
    - Create architecture diagram showing AgentCore components
    - _Requirements: 6.1, 6.2, 6.9_

  - [ ] 7.2 Create demo materials

    - Prepare demo script showing AgentCore invocation
    - Create video demonstrating AgentCore features
    - Document hackathon compliance (AgentCore Memory + Runtime)
    - Prepare code repository for submission
    - _Requirements: 6.4, 6.5, 6.6, 6.7_

  - [ ] 7.3 Update deployment documentation

    - Document AgentCore deployment process
    - Provide troubleshooting guide
    - Include monitoring and observability setup
    - Create quick start guide for judges
    - _Requirements: 6.3, 6.8_

## Implementation Notes

### Critical Rate Limiting Requirement

**UNIVERSAL 30-SECOND RULE**: ALL agents including the supervisor MUST wait at least 30 seconds between ANY model invocations. This is a global rate limit that applies to the entire system - no agent is exempt.

### AgentCore Memory for Rate Limiting

Instead of using DynamoDB for rate limiting, we'll use AgentCore Memory which provides:
- Built-in distributed storage for global rate limiting
- Automatic expiry (30 days)
- Native integration with AgentCore Runtime
- Simplified access patterns
- Global consistency for the 30-second rule

**Memory Structure**:
```python
# Store GLOBAL rate limiting data in Memory
memory_client.store_memory_record(
    memory_id=memory_id,
    actor_id="rate-limiter",
    session_id="global-model-invocations",  # Global key for ALL model calls
    content={
        "last_invocation": timestamp,
        "last_agent": agent_name,  # Track which agent made the call
        "invocation_count": count
    }
)
```

### Enhanced Architecture Benefits

1. **Hackathon Compliance**: Uses AgentCore Memory + Runtime (2 primitives)
2. **Risk Mitigation**: Keeps existing CloudFormation architecture intact
3. **Enhanced Features**: Memory-based rate limiting, better observability
4. **Minimal Changes**: All existing agents remain unchanged

### CloudFormation Template Structure

```yaml
# Add to existing template
AgentCoreMemory:
  Type: AWS::BedrockAgentCore::Memory
  Properties:
    Name: autoninja-rate-limiter-memory
    EventExpiryDuration: 30
    Description: "Memory store for AutoNinja rate limiting"

AgentCoreRuntime:
  Type: AWS::BedrockAgentCore::Runtime
  Properties:
    AgentRuntimeName: autoninja-supervisor-runtime
    AgentRuntimeArtifact:
      # Will be populated by deployment script
    EnvironmentVariables:
      MEMORY_ID: !Ref AgentCoreMemory
      REQUIREMENTS_ANALYST_AGENT_ID: !Ref RequirementsAnalystAgent
      # ... other agent IDs
```

### Testing Strategy

1. **Unit Tests**: Test Memory API integration and rate limiting logic
2. **Integration Tests**: Test full workflow with enhanced supervisor using AgentCore Memory
3. **Load Tests**: Verify rate limiting prevents throttling under load
4. **Compatibility Tests**: Ensure existing supervisor still works

This approach provides a comprehensive solution that meets hackathon requirements while minimizing risk by enhancing the existing architecture with AgentCore capabilities rather than replacing it.