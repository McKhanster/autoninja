# AutoNinja Deployment Fix - Complete Solution

## Problem Summary

**Primary Issue**: CloudFormation template validation failures in 4 nested stacks  
**Root Cause**: Malformed IAM Role `Policies` syntax (missing `PolicyName` and list indicator)  
**Secondary Issue**: Supervisor agent missing `AgentCollaborators` configuration  
**Impact**: Complete deployment failure - no stacks successfully created

---

## Fix #1: IAM Role Policies Syntax (CRITICAL - Blocks Deployment)

### Affected Files
- `infrastructure/cloudformation/stacks/code-generator.yaml` (line 66-68)
- `infrastructure/cloudformation/stacks/requirements-analyst.yaml` (line 66-68)
- `infrastructure/cloudformation/stacks/solution-architect.yaml` (line 66-68)
- `infrastructure/cloudformation/stacks/quality-validator.yaml` (line 66-68)

### Current (BROKEN) Code
```yaml
LambdaRole:
  Type: AWS::IAM::Role
  Properties:
    ManagedPolicyArns:
      - !Ref LambdaBasePolicyArn
    Policies:              # ❌ Missing list indicator
        PolicyDocument:    # ❌ Missing PolicyName
          Version: "2012-10-17"
```

### Fixed Code
```yaml
LambdaRole:
  Type: AWS::IAM::Role
  Properties:
    ManagedPolicyArns:
      - !Ref LambdaBasePolicyArn
    Policies:                        # ✅ List of policies
      - PolicyName: RateLimiterAccess  # ✅ Required PolicyName
        PolicyDocument:                # ✅ Proper indentation
          Version: "2012-10-17"
```

---

## Fix #2: Supervisor Agent Collaborators Configuration (IMPORTANT - Enables Multi-Agent)

### File
- `infrastructure/cloudformation/stacks/supervisor.yaml`

### Issue
The supervisor agent has `AgentCollaboration: SUPERVISOR` but is missing the `AgentCollaborators` property that defines which agents it coordinates.

### Solution
Add `AgentCollaborators` property to the supervisor agent resource. According to AWS documentation, we need:
- `CollaboratorName`: Friendly name for the collaborator
- `AgentDescriptor`: Contains the `AliasArn` of the collaborator agent
- `CollaborationInstruction`: When to use this collaborator
- `RelayConversationHistory`: Set to `TO_COLLABORATOR` to share context

### Implementation

**Add after line 113 (after `Instruction:` block, before `Tags:`):**

```yaml
      AgentCollaborators:
        - CollaboratorName: requirements-analyst
          AgentDescriptor:
            AliasArn: !Sub "${RequirementsAnalystAgentArn}/alias/production"
          CollaborationInstruction: >
            Use this agent to extract and validate requirements from user requests.
            Always pass job_name parameter. This agent generates requirements for all downstream agents.
          RelayConversationHistory: TO_COLLABORATOR
        
        - CollaboratorName: code-generator
          AgentDescriptor:
            AliasArn: !Sub "${CodeGeneratorAgentArn}/alias/production"
          CollaborationInstruction: >
            Use this agent to generate Lambda code, agent configurations, and OpenAPI schemas.
            Always pass job_name and requirements from Requirements Analyst.
          RelayConversationHistory: TO_COLLABORATOR
        
        - CollaboratorName: solution-architect
          AgentDescriptor:
            AliasArn: !Sub "${SolutionArchitectAgentArn}/alias/production"
          CollaborationInstruction: >
            Use this agent to design AWS architecture and generate CloudFormation templates.
            Always pass job_name, requirements, and code references from Code Generator.
          RelayConversationHistory: TO_COLLABORATOR
        
        - CollaboratorName: quality-validator
          AgentDescriptor:
            AliasArn: !Sub "${QualityValidatorAgentArn}/alias/production"
          CollaborationInstruction: >
            Use this agent to validate code quality, security, and compliance.
            Always pass job_name and all artifacts. Check is_valid before proceeding to deployment.
          RelayConversationHistory: TO_COLLABORATOR
        
        - CollaboratorName: deployment-manager
          AgentDescriptor:
            AliasArn: !Sub "${DeploymentManagerAgentArn}/alias/production"
          CollaborationInstruction: >
            Use this agent ONLY if Quality Validator returns is_valid=true.
            Pass job_name and all artifacts. This agent deploys the generated agent to AWS.
          RelayConversationHistory: TO_COLLABORATOR
```

**Note**: The `AliasArn` format needs to be constructed from the agent ARN + alias name. We need to update the parameters to pass alias ARNs instead of agent ARNs, OR construct them in the template.

### Parameter Updates Needed

Change the supervisor.yaml parameters from agent ARNs to alias ARNs:

**BEFORE:**
```yaml
Parameters:
  RequirementsAnalystAgentArn:
    Type: String
    Description: ARN of Requirements Analyst Agent
```

**AFTER:**
```yaml
Parameters:
  RequirementsAnalystAliasArn:
    Type: String
    Description: Alias ARN of Requirements Analyst Agent (format: arn:aws:bedrock:region:account:agent-alias/AGENT_ID/ALIAS_ID)
```

Repeat for all 5 collaborator parameters.

### Main Stack Updates

Update `infrastructure/cloudformation/autoninja-main.yaml` to pass alias ARNs:

**BEFORE (line 360):**
```yaml
Parameters:
  RequirementsAnalystAgentArn: !GetAtt RequirementsAnalystStack.Outputs.AgentArn
```

**AFTER:**
```yaml
Parameters:
  RequirementsAnalystAliasArn: !Sub 
    - "arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:agent-alias/${AgentId}/${AliasId}"
    - AgentId: !GetAtt RequirementsAnalystStack.Outputs.AgentId
      AliasId: !GetAtt RequirementsAnalystStack.Outputs.AgentAliasId
```

---

## Fix #3: Missing AWS_ACCOUNT_ID in Deployment Script

### File
- `scripts/deploy_nested_stacks.sh`

### Issue
Line 267 references `${AWS_ACCOUNT_ID}` but it's never set.

### Solution
Add at the top of the script (after line 20):

```bash
# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region "$REGION" --profile "$PROFILE")
echo "  Account ID: $AWS_ACCOUNT_ID"
```

---

## Implementation Steps

### Step 1: Fix IAM Role Policies (5 minutes)

```bash
# Fix code-generator.yaml
sed -i '66,68s/    Policies:/    Policies:\n      - PolicyName: RateLimiterAccess/' infrastructure/cloudformation/stacks/code-generator.yaml

# Repeat for other 3 files
for file in requirements-analyst solution-architect quality-validator; do
    sed -i '66,68s/    Policies:/    Policies:\n      - PolicyName: RateLimiterAccess/' infrastructure/cloudformation/stacks/${file}.yaml
done
```

**OR manually edit each file** - replace lines 66-68 as shown in Fix #1.

### Step 2: Update Supervisor Stack (10 minutes)

1. Update parameters to use alias ARNs instead of agent ARNs
2. Add `AgentCollaborators` property to supervisor agent
3. Update main stack to pass alias ARNs

### Step 3: Fix Deployment Script (2 minutes)

Add `AWS_ACCOUNT_ID` variable to `scripts/deploy_nested_stacks.sh`.

### Step 4: Validate Templates (3 minutes)

```bash
# Validate all nested stacks
for template in infrastructure/cloudformation/stacks/*.yaml; do
    echo "Validating $(basename $template)..."
    aws cloudformation validate-template \
        --template-body file://$template \
        --region us-east-2 \
        --profile AdministratorAccess-784327326356 > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "  ✅ Valid"
    else
        echo "  ❌ FAILED"
    fi
done
```

### Step 5: Deploy (15 minutes)

```bash
# Clean up failed stack
aws cloudformation delete-stack \
    --stack-name autoninja-production \
    --region us-east-2 \
    --profile AdministratorAccess-784327326356

# Wait for deletion
aws cloudformation wait stack-delete-complete \
    --stack-name autoninja-production \
    --region us-east-2 \
    --profile AdministratorAccess-784327326356

# Deploy with fixes
./scripts/deploy_nested_stacks.sh
```

---

## Verification Checklist

After deployment:

- [ ] All 9 nested stacks reach `CREATE_COMPLETE` status
  - [ ] StorageStack
  - [ ] LambdaLayerStack
  - [ ] CustomOrchestrationStack
  - [ ] RequirementsAnalystStack
  - [ ] CodeGeneratorStack
  - [ ] SolutionArchitectStack
  - [ ] QualityValidatorStack
  - [ ] DeploymentManagerStack
  - [ ] SupervisorStack

- [ ] Supervisor agent has 5 collaborators associated
  ```bash
  aws bedrock-agent list-agent-collaborators \
      --agent-id <SUPERVISOR_AGENT_ID> \
      --agent-version DRAFT \
      --region us-east-2
  ```

- [ ] Can invoke supervisor agent successfully
  ```bash
  aws bedrock-agent-runtime invoke-agent \
      --agent-id <SUPERVISOR_AGENT_ID> \
      --agent-alias-id <SUPERVISOR_ALIAS_ID> \
      --session-id test-$(date +%s) \
      --input-text "Build a simple greeting agent" \
      --region us-east-2 \
      output.json
  ```

---

## Alternative Approach: Post-Deployment Association

If CloudFormation `AgentCollaborators` property doesn't work as expected, we can associate collaborators post-deployment using the AWS CLI in the deployment script:

```bash
# After supervisor stack is created
SUPERVISOR_ID=$(aws cloudformation describe-stacks \
    --stack-name autoninja-production-SupervisorStack-XXX \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentId`].OutputValue' \
    --output text)

# Associate each collaborator
aws bedrock-agent associate-agent-collaborator \
    --agent-id "$SUPERVISOR_ID" \
    --agent-version DRAFT \
    --collaborator-name "requirements-analyst" \
    --agent-descriptor "aliasArn=arn:aws:bedrock:us-east-2:123456789012:agent-alias/AGENT_ID/ALIAS_ID" \
    --collaboration-instruction "Extract and validate requirements" \
    --relay-conversation-history TO_COLLABORATOR \
    --region us-east-2
```

This is already partially implemented in `scripts/deploy_nested_stacks.sh` (lines 230-280), but it uses the wrong API format. The script needs to be updated to use `aliasArn` in the `--agent-descriptor` parameter.

---

## Timeline

| Task | Duration | Priority |
|------|----------|----------|
| Fix IAM Role Policies (4 files) | 5 min | CRITICAL |
| Update Supervisor Stack | 10 min | HIGH |
| Fix Deployment Script | 2 min | MEDIUM |
| Validate Templates | 3 min | HIGH |
| Delete Failed Stack | 5 min | - |
| Re-deploy | 15 min | - |
| Verify Deployment | 5 min | HIGH |
| **TOTAL** | **45 min** | |

---

## Next Steps After Successful Deployment

1. Test supervisor agent with simple request
2. Monitor CloudWatch logs for all 6 agents
3. Verify DynamoDB rate limiter table is being used
4. Update spec files with actual implementation details
5. Document any deviations from FINAL_IMPLEMENTATION.md

---

## References

- [AWS Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)
- [CloudFormation Agent Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrock-agent.html)
- [AgentCollaborator Property](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-bedrock-agent-agentcollaborator.html)
- [IAM Role Policies Syntax](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-iam-role-policy.html)
