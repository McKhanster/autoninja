# Design Document

## Overview

This design adds the missing Bedrock Agent IAM roles to the AutoNinja CloudFormation template, enabling agents to access their OpenAPI schemas stored in S3. The solution follows AWS security best practices from the official Bedrock Agents documentation, including proper trust policies, condition keys for confused deputy prevention, and least-privilege permissions.

## Architecture

### Current State

The CloudFormation template currently has:
- 5 Lambda functions with their own IAM roles
- S3 bucket (ArtifactsBucket) with a bucket policy allowing bedrock.amazonaws.com to read objects
- 5 Bedrock Agent resources that reference `AgentResourceRoleArn` properties
- **MISSING**: The actual IAM roles that the agents need to assume

### Target State

The CloudFormation template will have:
- 5 new IAM roles (one per Bedrock Agent) with trust policies and permissions
- Each Bedrock Agent resource will reference its corresponding role via `!GetAtt`
- 5 Lambda permission resources allowing Bedrock to invoke the Lambda functions
- Proper dependency ordering to ensure roles exist before agents are created

## Components and Interfaces

### Component 1: Bedrock Agent IAM Roles

**Location:** `infrastructure/cloudformation/autoninja-complete.yaml`

**Resources to Add:**
1. `RequirementsAnalystAgentRole` (AWS::IAM::Role)
2. `CodeGeneratorAgentRole` (AWS::IAM::Role)
3. `SolutionArchitectAgentRole` (AWS::IAM::Role)
4. `QualityValidatorAgentRole` (AWS::IAM::Role)
5. `DeploymentManagerAgentRole` (AWS::IAM::Role)

**Role Structure (template for all 5 roles):**

```yaml
RequirementsAnalystAgentRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub "AutoNinjaRequirementsAnalystAgentRole-${Environment}"
    Description: Service role for Requirements Analyst Bedrock Agent
    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Service: bedrock.amazonaws.com
          Action: sts:AssumeRole
          Condition:
            StringEquals:
              aws:SourceAccount: !Ref AWS::AccountId
            ArnLike:
              AWS:SourceArn: !Sub "arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:agent/*"
    Policies:
      - PolicyName: BedrockAgentPermissions
        PolicyDocument:
          Version: "2012-10-17"
          Statement:
            # Permission to invoke foundation model
            - Sid: InvokeFoundationModel
              Effect: Allow
              Action:
                - bedrock:InvokeModel
              Resource: !Sub "arn:aws:bedrock:${AWS::Region}::foundation-model/*"
            # Permission to read schemas from S3
            - Sid: ReadSchemasFromS3
              Effect: Allow
              Action:
                - s3:GetObject
              Resource: !Sub "${ArtifactsBucket.Arn}/schemas/*"
              Condition:
                StringEquals:
                  aws:ResourceAccount: !Ref AWS::AccountId
            # Permission to list bucket (required for schema access)
            - Sid: ListSchemasBucket
              Effect: Allow
              Action:
                - s3:ListBucket
              Resource: !GetAtt ArtifactsBucket.Arn
              Condition:
                StringEquals:
                  aws:ResourceAccount: !Ref AWS::AccountId
    Tags:
      - Key: Environment
        Value: !Ref Environment
      - Key: Application
        Value: AutoNinja
```

**Design Decisions:**
- **Inline policies vs managed policies**: Using inline policies to keep all permissions in one place and ensure they're deleted with the role
- **Wildcard foundation model ARN**: Using `foundation-model/*` to support different models without template changes
- **Condition keys**: Including `aws:SourceAccount` and `AWS:SourceArn` to prevent confused deputy attacks
- **S3 path restriction**: Limiting access to `schemas/*` path only, not the entire bucket

### Component 2: Lambda Permissions

**Location:** `infrastructure/cloudformation/autoninja-complete.yaml`

**Resources to Add:**
1. `RequirementsAnalystLambdaInvokePermission` (AWS::Lambda::Permission)
2. `CodeGeneratorLambdaInvokePermission` (AWS::Lambda::Permission)
3. `SolutionArchitectLambdaInvokePermission` (AWS::Lambda::Permission)
4. `QualityValidatorLambdaInvokePermission` (AWS::Lambda::Permission)
5. `DeploymentManagerLambdaInvokePermission` (AWS::Lambda::Permission)

**Permission Structure (template):**

```yaml
RequirementsAnalystLambdaInvokePermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref RequirementsAnalystFunction
    Action: lambda:InvokeFunction
    Principal: bedrock.amazonaws.com
    SourceAccount: !Ref AWS::AccountId
    SourceArn: !GetAtt RequirementsAnalystAgent.AgentArn
```

**Design Decisions:**
- **SourceArn specificity**: Each permission is scoped to the specific agent that needs to invoke it
- **No wildcard principals**: Using `bedrock.amazonaws.com` with source conditions for security

### Component 3: Agent Resource Updates

**Location:** `infrastructure/cloudformation/bedrock-agents-section.yaml` (to be merged into main template)

**Changes Required:**
- Update each agent's `DependsOn` to include the agent role
- Update `AgentResourceRoleArn` to reference the role ARN

**Example:**

```yaml
RequirementsAnalystAgent:
  Type: AWS::Bedrock::Agent
  DependsOn:
    - RequirementsAnalystFunction
    - RequirementsAnalystAgentRole  # ADD THIS
  Properties:
    AgentResourceRoleArn: !GetAtt RequirementsAnalystAgentRole.Arn  # UPDATE THIS
    # ... rest of properties
```

### Component 4: Template Organization

**Insertion Point:** After Lambda roles section, before Lambda functions section

**Rationale:** 
- Logical grouping: IAM roles together
- Dependency order: Roles must exist before agents reference them
- Maintainability: Easy to find all IAM resources in one section

## Data Models

### IAM Role ARN Format
```
arn:aws:iam::{AccountId}:role/AutoNinja{AgentName}AgentRole-{Environment}
```

### S3 Schema Path Format
```
s3://{BucketName}/schemas/{agent-name}-schema.yaml
```

### Lambda Permission Source ARN Format
```
arn:aws:bedrock:{Region}:{AccountId}:agent/{AgentId}
```

## Error Handling

### Scenario 1: Schema Not Found in S3

**Problem:** Agent tries to access schema that wasn't uploaded

**Solution:** 
- Deploy script uploads schemas before CloudFormation deployment (already implemented)
- CloudFormation template doesn't validate schema existence (AWS handles this at runtime)
- If schema is missing, agent creation will fail with clear error message

**Error Message Example:**
```
Resource handler returned message: "Invalid request provided: 
Could not access S3 object at s3://bucket/schemas/agent-schema.yaml"
```

### Scenario 2: Insufficient S3 Permissions

**Problem:** Agent role lacks s3:GetObject permission

**Solution:**
- Template includes explicit s3:GetObject on schemas/* path
- Template includes s3:ListBucket permission (required by Bedrock)
- Condition keys ensure cross-account access is prevented

### Scenario 3: Confused Deputy Attack

**Problem:** Malicious actor tries to use Bedrock service to access resources

**Solution:**
- Trust policy includes `aws:SourceAccount` condition
- Trust policy includes `AWS:SourceArn` condition with agent ARN pattern
- S3 permissions include `aws:ResourceAccount` condition

### Scenario 4: Lambda Invocation Denied

**Problem:** Agent cannot invoke Lambda function

**Solution:**
- Lambda::Permission resource explicitly allows bedrock.amazonaws.com
- Permission scoped to specific agent via SourceArn
- Permission created before agent is prepared/deployed

## Testing Strategy

### Unit Testing (CloudFormation Validation)

**Test 1: Template Syntax Validation**
```bash
aws cloudformation validate-template \
  --template-body file://infrastructure/cloudformation/autoninja-complete.yaml
```

**Expected:** No syntax errors, returns template description

**Test 2: IAM Policy Validation**
```bash
# Use IAM Policy Simulator to validate permissions
aws iam simulate-custom-policy \
  --policy-input-list file://extracted-agent-policy.json \
  --action-names bedrock:InvokeModel s3:GetObject s3:ListBucket \
  --resource-arns "arn:aws:bedrock:us-east-2::foundation-model/*" \
                  "arn:aws:s3:::bucket/schemas/test.yaml" \
                  "arn:aws:s3:::bucket"
```

**Expected:** All actions allowed

### Integration Testing (Deployment)

**Test 3: Stack Deployment**
```bash
./scripts/deploy_all.sh
```

**Expected:** 
- All resources created successfully
- No permission errors in CloudFormation events
- Stack status: CREATE_COMPLETE

**Test 4: Agent Preparation**
```bash
aws bedrock-agent prepare-agent \
  --agent-id <agent-id> \
  --region us-east-2
```

**Expected:**
- Agent status: PREPARED
- No schema access errors
- Action groups properly configured

**Test 5: Agent Invocation**
```bash
python tests/requirements_analyst/test_requirements_analyst_agent.py
```

**Expected:**
- Agent successfully invokes Lambda function
- Lambda function executes without permission errors
- Response returned successfully

### Security Testing

**Test 6: Cross-Account Access Prevention**
```bash
# Attempt to assume role from different account (should fail)
aws sts assume-role \
  --role-arn arn:aws:iam::{AccountId}:role/AutoNinjaRequirementsAnalystAgentRole-production \
  --role-session-name test \
  --profile different-account
```

**Expected:** Access denied due to condition keys

**Test 7: S3 Path Restriction**
```bash
# Attempt to read non-schema file (should fail)
# This would be tested by modifying agent role temporarily
```

**Expected:** Access denied for paths outside schemas/*

## Implementation Notes

### Order of Operations

1. **Add IAM roles** to CloudFormation template (after Lambda roles section)
2. **Add Lambda permissions** to CloudFormation template (after Lambda functions section)
3. **Update agent DependsOn** in bedrock-agents-section.yaml
4. **Update agent AgentResourceRoleArn** in bedrock-agents-section.yaml
5. **Merge bedrock-agents-section.yaml** into autoninja-complete.yaml (if not already done)
6. **Validate template** with AWS CLI
7. **Deploy stack** with deploy_all.sh script

### CloudFormation Resource Naming

All resources follow the pattern:
- IAM Roles: `AutoNinja{AgentName}AgentRole-${Environment}`
- Lambda Permissions: `{AgentName}LambdaInvokePermission`

### AWS Documentation References

- [Create a service role for Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-permissions.html)
- [AWS::Bedrock::Agent AgentActionGroup](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-bedrock-agent-agentactiongroup.html)
- [Preventing confused deputy](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html)

## Rollback Strategy

If deployment fails:
1. CloudFormation automatically rolls back to previous state
2. Schemas remain in S3 (no cleanup needed)
3. Lambda functions remain deployed (no impact)
4. Re-run deployment after fixing issues

## Performance Considerations

- IAM role creation adds ~10-15 seconds to stack deployment time
- No runtime performance impact (roles are cached by AWS)
- S3 schema access is fast (<100ms) and cached by Bedrock

## Security Considerations

- All roles follow least-privilege principle
- Condition keys prevent confused deputy attacks
- S3 access restricted to schemas directory only
- No wildcard permissions on sensitive actions
- Encryption enforced via bucket policy (already exists)
