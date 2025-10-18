# Task 11.0 Audit Findings

## Date: 2025-01-XX
## Task: Audit existing code for AgentCore Runtime integration

## Summary

Reviewed all spec documents (requirements.md, design.md, tasks.md) and the CloudFormation template (`infrastructure/cloudformation/autoninja-complete.yaml`) to understand the current supervisor agent implementation and identify what needs to change for AgentCore Runtime integration.

## Current Architecture

### Supervisor Agent (Regular Bedrock Agent)
- **Resource Name**: `SupervisorAgent` (line ~1550)
- **Type**: `AWS::Bedrock::Agent`
- **Configuration**:
  - AgentCollaboration: DISABLED
  - No action groups configured
  - No agent collaborators configured (commented out)
  - Has production alias: `SupervisorAgentAlias`
  - Uses IAM role: `SupervisorAgentRole`

### Collaborator Agents (5 agents - fully operational)
1. **Requirements Analyst** - Extracts requirements
2. **Code Generator** - Generates Lambda code, agent configs, OpenAPI schemas
3. **Solution Architect** - Designs architecture and IaC
4. **Quality Validator** - Validates code quality, security, compliance
5. **Deployment Manager** - Deploys agents to AWS

All collaborators have:
- Lambda functions with action groups
- OpenAPI schemas stored in S3
- IAM roles with proper permissions
- Production aliases
- Custom orchestration for rate limiting

### Supporting Infrastructure
- **DynamoDB Table**: `InferenceRecordsTable` - stores all inference records
- **S3 Bucket**: `ArtifactsBucket` - stores all artifacts
- **Lambda Layer**: `SharedLibrariesLayer` - shared persistence/utilities
- **Custom Orchestration Lambda**: Rate limiting for collaborators

## Required Changes for AgentCore Integration

### 1. REMOVE from CloudFormation Template

**Supervisor Bedrock Agent Resource** (lines ~1550-1580):
```yaml
SupervisorAgent:
  Type: AWS::Bedrock::Agent
  # ... entire resource definition
```

**Supervisor Agent Alias** (lines ~1590-1600):
```yaml
SupervisorAgentAlias:
  Type: AWS::Bedrock::AgentAlias
  # ... entire resource definition
```

**Supervisor Agent IAM Role** (lines ~850-880):
```yaml
SupervisorAgentRole:
  Type: AWS::IAM::Role
  # ... entire resource definition
```

**Rationale**: The supervisor will be deployed to AgentCore Runtime separately using the `agentcore` CLI, not via CloudFormation.

### 2. ADD to CloudFormation Template

**IAM Role for AgentCore Supervisor** (new resource):
```yaml
AgentCoreSupervisorRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub "AutoNinjaAgentCoreSupervisorRole-${Environment}"
    Description: Execution role for AgentCore Runtime supervisor agent
    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Service: bedrock.amazonaws.com
          Action: sts:AssumeRole
    Policies:
      - PolicyName: InvokeCollaboratorAgents
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
            - Sid: InvokeAllCollaborators
              Effect: Allow
              Action:
                - bedrock:InvokeAgent
                - bedrock-agent-runtime:InvokeAgent
              Resource:
                - !GetAtt RequirementsAnalystAgent.AgentArn
                - !GetAtt CodeGeneratorAgent.AgentArn
                - !GetAtt SolutionArchitectAgent.AgentArn
                - !GetAtt QualityValidatorAgent.AgentArn
                - !GetAtt DeploymentManagerAgent.AgentArn
            - Sid: InvokeBedrockModels
              Effect: Allow
              Action:
                - bedrock:InvokeModel
                - bedrock:InvokeModelWithResponseStream
              Resource:
                - !Sub "arn:aws:bedrock:*::foundation-model/*"
                - !Sub "arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:inference-profile/*"
            - Sid: DynamoDBAccess
              Effect: Allow
              Action:
                - dynamodb:PutItem
                - dynamodb:UpdateItem
                - dynamodb:Query
              Resource:
                - !GetAtt InferenceRecordsTable.Arn
                - !Sub "${InferenceRecordsTable.Arn}/index/*"
            - Sid: S3Access
              Effect: Allow
              Action:
                - s3:GetObject
                - s3:PutObject
              Resource: !Sub "${ArtifactsBucket.Arn}/*"
            - Sid: CloudWatchLogs
              Effect: Allow
              Action:
                - logs:CreateLogGroup
                - logs:CreateLogStream
                - logs:PutLogEvents
              Resource: !Sub "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/bedrock/agentcore/*"
```

**CloudFormation Outputs** (update Outputs section):
```yaml
# Remove old supervisor outputs, add these:
AgentCoreSupervisorRoleArn:
  Description: IAM Role ARN for AgentCore Runtime supervisor (use this when deploying with agentcore CLI)
  Value: !GetAtt AgentCoreSupervisorRole.Arn
  Export:
    Name: !Sub "${AWS::StackName}-AgentCoreSupervisorRoleArn"

AgentCoreSupervisorInvocationNote:
  Description: Instructions for invoking the AgentCore supervisor
  Value: "Deploy supervisor with 'agentcore launch' then invoke with 'agentcore invoke' or boto3 bedrock-agentcore client"

# Keep all collaborator agent IDs and ARNs for supervisor to reference
RequirementsAnalystAgentId:
  Description: Requirements Analyst Agent ID (for supervisor to invoke)
  Value: !GetAtt RequirementsAnalystAgent.AgentId
  Export:
    Name: !Sub "${AWS::StackName}-RequirementsAnalystAgentId"

RequirementsAnalystAgentAliasId:
  Description: Requirements Analyst Agent Alias ID (for supervisor to invoke)
  Value: !GetAtt RequirementsAnalystAgentAlias.AgentAliasId
  Export:
    Name: !Sub "${AWS::StackName}-RequirementsAnalystAgentAliasId"

# ... similar exports for other 4 collaborators
```

### 3. KEEP Unchanged

**All Collaborator Agents**: No changes needed - they will work with AgentCore supervisor
**Lambda Functions**: No changes needed
**DynamoDB and S3**: No changes needed
**Custom Orchestration Lambda**: No changes needed

## Compatibility Analysis

### ✅ No Breaking Changes
- Collaborator agents are independent and don't know/care who invokes them
- AgentCore supervisor will use standard `InvokeAgent` API (same as regular Bedrock Agent)
- All persistence (DynamoDB/S3) works the same way
- Custom orchestration applies only to collaborators, not supervisor

### ✅ Hybrid Architecture Benefits
- **AgentCore Runtime Supervisor**: Extended execution time (8 hours), framework flexibility, better isolation
- **Regular Bedrock Agent Collaborators**: Simpler deployment, native action groups, proven stability
- **Best of Both Worlds**: Supervisor gets advanced features, collaborators stay simple

### ✅ Migration Path
1. Deploy updated CloudFormation stack (removes old supervisor, adds AgentCore IAM role)
2. Deploy AgentCore supervisor separately using `agentcore` CLI
3. Configure supervisor with collaborator agent IDs from CloudFormation outputs
4. Test end-to-end workflow
5. Apply custom orchestration to collaborators (existing script)

## Next Steps

1. ✅ **Task 11.0 Complete**: Audit complete, findings documented
2. **Task 11.1**: Design supervisor orchestration logic with AgentCore
3. **Task 11.2**: Implement supervisor agent code for AgentCore Runtime
4. **Task 11.3**: Create requirements.txt and configuration
5. **Task 11.4**: Test supervisor locally
6. **Task 11.5**: Deploy to AgentCore Runtime
7. **Task 11.6**: Update CloudFormation template (apply changes documented above)
8. **Task 11.7**: Configure custom orchestration for collaborators
9. **Task 11.8**: Test end-to-end orchestration

## Risks and Mitigations

### Risk 1: AgentCore Runtime is new technology
**Mitigation**: Follow AWS documentation closely, use starter toolkit, test locally first

### Risk 2: Collaborator invocation from AgentCore might differ
**Mitigation**: Use standard boto3 `bedrock-agent-runtime` client, same API as regular agents

### Risk 3: IAM permissions might be insufficient
**Mitigation**: Grant broad permissions initially, narrow down after testing

### Risk 4: CloudFormation stack update might fail
**Mitigation**: Test in development environment first, have rollback plan

## Conclusion

The current architecture is well-suited for AgentCore integration. The collaborator agents are independent and require no changes. The main work is:
1. Remove old supervisor Bedrock Agent from CloudFormation
2. Create new IAM role for AgentCore supervisor
3. Implement supervisor logic using AgentCore SDK
4. Deploy supervisor separately with `agentcore` CLI
5. Update CloudFormation outputs to reference AgentCore supervisor

**Estimated Effort**: Medium complexity, low risk due to clean separation of concerns.
