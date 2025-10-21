# AutoNinja Standardization Plan

**Goal:** Replicate the Code Generator pattern across all 5 collaborator agents for 100% consistency and reliability.

**Approach:** One-shot CloudFormation deployment that creates all resources from a single template.

---

## Phase 1: Preparation (Complete)

✅ **Code Generator validated** - End-to-end tests passed  
✅ **Complete metadata extracted** - All configuration documented  
✅ **Blueprint created** - `CODE_GENERATOR_BLUEPRINT.md`  
✅ **Pattern identified** - Know exactly what works

---

## Phase 2: Agent Standardization

### Strategy

**For each agent (Requirements Analyst, Solution Architect, Quality Validator, Deployment Manager):**

1. Copy Code Generator Lambda handler
2. Update agent-specific details (name, instructions, actions)
3. Keep ALL patterns identical (event parsing, logging, responses)
4. Discard old implementation
5. Verify against Code Generator blueprint

### Agent-Specific Details

#### Requirements Analyst
```yaml
Agent Name: autoninja-requirements-analyst-production
Instructions: |
  You are a requirements analyst for the AutoNinja system. You receive a job_name 
  from the orchestrator supervisor. Extract and validate requirements from user requests.
  Use action group functions: 1. /extract-requirements to analyze user requests.
  2. /analyze-complexity to assess complexity. 3. /validate-requirements to check completeness.
  Always include the job_name in all action calls.

Actions:
  - /extract-requirements (job_name, user_request)
  - /analyze-complexity (job_name, requirements)
  - /validate-requirements (job_name, requirements)

S3 Phase: requirements
Lambda Memory: 512MB
Lambda Timeout: 300s
```

#### Solution Architect
```yaml
Agent Name: autoninja-solution-architect-production
Instructions: |
  You are a solution architect for the AutoNinja system. You receive a job_name 
  from the orchestrator supervisor. Design AWS architectures based on requirements 
  and code files. Use action group functions: 1. /design-architecture to create 
  architecture designs. 2. /select-services to choose AWS services. 3. /generate-iac 
  to create CloudFormation templates. Always include the job_name in all action calls.

Actions:
  - /design-architecture (job_name, requirements, code_file_references)
  - /select-services (job_name, requirements)
  - /generate-iac (job_name, architecture, code_files)

S3 Phase: architecture
Lambda Memory: 512MB
Lambda Timeout: 300s
```

#### Quality Validator
```yaml
Agent Name: autoninja-quality-validator-production
Instructions: |
  You are a quality validator for the AutoNinja system. You receive a job_name 
  from the orchestrator supervisor. Validate generated code for quality, security, 
  and compliance. Use action group functions: 1. /validate-code to check code quality.
  2. /security-scan to find vulnerabilities. 3. /compliance-check to verify standards.
  Always include the job_name in all action calls.

Actions:
  - /validate-code (job_name, code, language)
  - /security-scan (job_name, code, iam_policies)
  - /compliance-check (job_name, code, architecture)

S3 Phase: validation
Lambda Memory: 512MB
Lambda Timeout: 300s
```

#### Deployment Manager
```yaml
Agent Name: autoninja-deployment-manager-production
Instructions: |
  You are a deployment manager for the AutoNinja system. You receive a job_name 
  from the orchestrator supervisor. Deploy validated agents to AWS. Use action group 
  functions: 1. /generate-cloudformation to create CFN templates. 2. /deploy-stack 
  to deploy to AWS. 3. /configure-agent to set up Bedrock Agent. 4. /test-deployment 
  to verify functionality. Always include the job_name in all action calls.

Actions:
  - /generate-cloudformation (job_name, requirements, code, architecture)
  - /deploy-stack (job_name, cloudformation_template, stack_name)
  - /configure-agent (job_name, agent_config, lambda_arns)
  - /test-deployment (job_name, agent_id, alias_id)

S3 Phase: deployment
Lambda Memory: 1024MB
Lambda Timeout: 900s
```

---

## Phase 3: CloudFormation Template Creation

### Template Structure

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'AutoNinja Multi-Agent System - Complete One-Shot Deployment'

Parameters:
  Environment:
    Type: String
    Default: production
  FoundationModel:
    Type: String
    Default: us.anthropic.claude-3-7-sonnet-20250219-v1:0
  LogLevel:
    Type: String
    Default: INFO

Resources:
  # ========================================
  # SHARED INFRASTRUCTURE
  # ========================================
  
  DynamoDBTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub 'autoninja-inference-records-${Environment}'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: job_name
          AttributeType: S
        - AttributeName: timestamp
          AttributeType: S
        - AttributeName: agent_name
          AttributeType: S
      KeySchema:
        - AttributeName: job_name
          KeyType: HASH
        - AttributeName: timestamp
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: AgentNameTimestampIndex
          KeySchema:
            - AttributeName: agent_name
              KeyType: HASH
            - AttributeName: timestamp
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true
  
  S3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'autoninja-artifacts-${AWS::AccountId}-${Environment}'
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
  
  LambdaLayer:
    Type: AWS::Lambda::LayerVersion
    Properties:
      LayerName: !Sub 'autoninja-shared-layer-${Environment}'
      Description: Shared libraries for AutoNinja Lambda functions
      Content:
        S3Bucket: !Ref S3Bucket
        S3Key: layers/autoninja-shared-layer.zip
      CompatibleRuntimes:
        - python3.12
  
  # ========================================
  # LAMBDA BASE POLICY (Shared)
  # ========================================
  
  LambdaBasePolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: !Sub 'AutoNinjaLambdaBasePolicy-${Environment}'
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - logs:CreateLogGroup
              - logs:CreateLogStream
              - logs:PutLogEvents
            Resource: !Sub 'arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/autoninja-*'
          - Effect: Allow
            Action:
              - dynamodb:PutItem
              - dynamodb:GetItem
              - dynamodb:Query
              - dynamodb:Scan
              - dynamodb:UpdateItem
            Resource:
              - !GetAtt DynamoDBTable.Arn
              - !Sub '${DynamoDBTable.Arn}/index/*'
          - Effect: Allow
            Action:
              - s3:PutObject
              - s3:GetObject
              - s3:ListBucket
            Resource:
              - !GetAtt S3Bucket.Arn
              - !Sub '${S3Bucket.Arn}/*'
          - Effect: Allow
            Action:
              - xray:PutTraceSegments
              - xray:PutTelemetryRecords
            Resource: '*'
  
  # ========================================
  # REQUIREMENTS ANALYST
  # ========================================
  
  RequirementsAnalystRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub 'AutoNinjaRequirementsAnalystRole-${Environment}'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - !Ref LambdaBasePolicy
  
  RequirementsAnalystFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub 'autoninja-requirements-analyst-${Environment}'
      Runtime: python3.12
      Handler: handler.lambda_handler
      Role: !GetAtt RequirementsAnalystRole.Arn
      Timeout: 300
      MemorySize: 512
      Layers:
        - !Ref LambdaLayer
      Environment:
        Variables:
          ENVIRONMENT: !Ref Environment
          DYNAMODB_TABLE_NAME: !Ref DynamoDBTable
          S3_BUCKET_NAME: !Ref S3Bucket
          LOG_LEVEL: !Ref LogLevel
      Code:
        S3Bucket: !Ref S3Bucket
        S3Key: lambda/requirements-analyst.zip
  
  RequirementsAnalystPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref RequirementsAnalystFunction
      Action: lambda:InvokeFunction
      Principal: bedrock.amazonaws.com
      SourceAccount: !Ref AWS::AccountId
      SourceArn: !Sub 'arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:agent/*'
  
  RequirementsAnalystAgentRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub 'AutoNinjaRequirementsAnalystAgentRole-${Environment}'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: bedrock.amazonaws.com
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                aws:SourceAccount: !Ref AWS::AccountId
              ArnLike:
                aws:SourceArn: !Sub 'arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:agent/*'
      Policies:
        - PolicyName: BedrockAgentPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - bedrock:InvokeModel
                Resource: !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/${FoundationModel}'
              - Effect: Allow
                Action:
                  - lambda:InvokeFunction
                Resource: !GetAtt RequirementsAnalystFunction.Arn
  
  RequirementsAnalystAgent:
    Type: AWS::Bedrock::Agent
    Properties:
      AgentName: !Sub 'autoninja-requirements-analyst-${Environment}'
      FoundationModel: !Ref FoundationModel
      Instruction: |
        You are a requirements analyst for the AutoNinja system. You receive a job_name 
        from the orchestrator supervisor. Extract and validate requirements from user requests.
        Use action group functions: 1. /extract-requirements to analyze user requests.
        2. /analyze-complexity to assess complexity. 3. /validate-requirements to check completeness.
        Always include the job_name in all action calls.
      IdleSessionTTLInSeconds: 600
      AgentResourceRoleArn: !GetAtt RequirementsAnalystAgentRole.Arn
      ActionGroups:
        - ActionGroupName: requirements-analyst-actions
          ActionGroupState: ENABLED
          ActionGroupExecutor:
            Lambda: !GetAtt RequirementsAnalystFunction.Arn
          ApiSchema:
            Payload: |
              openapi: 3.0.0
              info:
                title: Requirements Analyst API
                version: 1.0.0
              paths:
                /extract-requirements:
                  post:
                    operationId: extractRequirements
                    requestBody:
                      required: true
                      content:
                        application/json:
                          schema:
                            type: object
                            required: [job_name, user_request]
                            properties:
                              job_name: {type: string}
                              user_request: {type: string}
                    responses:
                      '200': {description: Success}
                      '400': {description: Invalid request}
                      '500': {description: Internal error}
                /analyze-complexity:
                  post:
                    operationId: analyzeComplexity
                    requestBody:
                      required: true
                      content:
                        application/json:
                          schema:
                            type: object
                            required: [job_name, requirements]
                            properties:
                              job_name: {type: string}
                              requirements: {type: string}
                    responses:
                      '200': {description: Success}
                /validate-requirements:
                  post:
                    operationId: validateRequirements
                    requestBody:
                      required: true
                      content:
                        application/json:
                          schema:
                            type: object
                            required: [job_name, requirements]
                            properties:
                              job_name: {type: string}
                              requirements: {type: string}
                    responses:
                      '200': {description: Success}
  
  RequirementsAnalystAlias:
    Type: AWS::Bedrock::AgentAlias
    Properties:
      AgentId: !GetAtt RequirementsAnalystAgent.AgentId
      AgentAliasName: production
      Description: Production alias for Requirements Analyst
  
  # ========================================
  # CODE GENERATOR (Same pattern)
  # ========================================
  
  # ... Repeat for Code Generator ...
  
  # ========================================
  # SOLUTION ARCHITECT (Same pattern)
  # ========================================
  
  # ... Repeat for Solution Architect ...
  
  # ========================================
  # QUALITY VALIDATOR (Same pattern)
  # ========================================
  
  # ... Repeat for Quality Validator ...
  
  # ========================================
  # DEPLOYMENT MANAGER (Same pattern, 1024MB, 900s)
  # ========================================
  
  # ... Repeat for Deployment Manager ...
  
  # ========================================
  # SUPERVISOR AGENT
  # ========================================
  
  SupervisorAgentRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub 'AutoNinjaSupervisorAgentRole-${Environment}'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: bedrock.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: SupervisorPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: bedrock:InvokeModel
                Resource: !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/${FoundationModel}'
  
  SupervisorAgent:
    Type: AWS::Bedrock::Agent
    DependsOn:
      - RequirementsAnalystAgent
      - CodeGeneratorAgent
      - SolutionArchitectAgent
      - QualityValidatorAgent
      - DeploymentManagerAgent
    Properties:
      AgentName: !Sub 'autoninja-supervisor-${Environment}'
      FoundationModel: !Ref FoundationModel
      Instruction: |
        You are the AutoNinja orchestrator supervisor. Coordinate 5 specialist agents 
        to generate production-ready AI agents from user descriptions. For each request:
        1. Generate unique job_name: job-{keyword}-{YYYYMMDD-HHMMSS}
        2. Pass job_name to ALL collaborators
        3. Delegate to Requirements Analyst → Code Generator → Solution Architect → Quality Validator → Deployment Manager
        4. Consolidate results and provide deployed agent ARN
      IdleSessionTTLInSeconds: 600
      AgentResourceRoleArn: !GetAtt SupervisorAgentRole.Arn
      AgentCollaboration: SUPERVISOR
  
  SupervisorAlias:
    Type: AWS::Bedrock::AgentAlias
    Properties:
      AgentId: !GetAtt SupervisorAgent.AgentId
      AgentAliasName: production
      Description: Production alias for Supervisor
  
  # ========================================
  # AGENT COLLABORATOR ASSOCIATIONS
  # ========================================
  
  SupervisorRequirementsAnalystAssociation:
    Type: AWS::Bedrock::AgentCollaborator
    Properties:
      AgentId: !GetAtt SupervisorAgent.AgentId
      AgentVersion: DRAFT
      CollaboratorName: requirements-analyst
      CollaborationInstruction: Use for extracting and validating requirements from user requests
      RelayConversationHistory: ENABLED
      CollaboratorAgent:
        AgentId: !GetAtt RequirementsAnalystAgent.AgentId
        AgentAliasArn: !GetAtt RequirementsAnalystAlias.AgentAliasArn
  
  # ... Repeat for other 4 collaborators ...

Outputs:
  SupervisorAgentId:
    Value: !GetAtt SupervisorAgent.AgentId
  SupervisorAgentArn:
    Value: !GetAtt SupervisorAgent.AgentArn
  DynamoDBTableName:
    Value: !Ref DynamoDBTable
  S3BucketName:
    Value: !Ref S3Bucket
```

---

## Phase 4: Implementation Steps

### Step 1: Prepare Lambda Code Packages

For each agent:
```bash
# 1. Copy Code Generator handler as template
cp lambda/code-generator/handler.py lambda/{agent}/handler.py

# 2. Update agent-specific details:
#    - Agent name in logger.set_context()
#    - Action names in routing
#    - S3 phase in artifact saving
#    - Business logic functions

# 3. Package for deployment
cd lambda/{agent}
zip -r ../../build/{agent}.zip handler.py

# 4. Upload to S3
aws s3 cp ../../build/{agent}.zip s3://{bucket}/lambda/{agent}.zip
```

### Step 2: Package Lambda Layer

```bash
cd shared
mkdir -p python/shared
cp -r models persistence utils python/shared/
cp requirements.txt python/
cd python
pip install -r requirements.txt -t .
cd ..
zip -r ../build/autoninja-shared-layer.zip python
aws s3 cp ../build/autoninja-shared-layer.zip s3://{bucket}/layers/
```

### Step 3: Deploy CloudFormation Template

```bash
aws cloudformation create-stack \
  --stack-name autoninja-production \
  --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=FoundationModel,ParameterValue=us.anthropic.claude-3-7-sonnet-20250219-v1:0 \
    ParameterKey=LogLevel,ParameterValue=INFO \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-2

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name autoninja-production \
  --region us-east-2
```

### Step 4: Verify Deployment

```bash
# Check all agents created
aws bedrock-agent list-agents --region us-east-2

# Check all Lambda functions
aws lambda list-functions --region us-east-2 | grep autoninja

# Check DynamoDB table
aws dynamodb describe-table --table-name autoninja-inference-records-production

# Check S3 bucket
aws s3 ls | grep autoninja
```

---

## Phase 5: Testing

### Test Each Agent Individually

```bash
# Test Requirements Analyst
python tests/requirement_analyst/test_requirements_analyst_agent.py

# Test Code Generator (already tested ✅)
python tests/code_generator/test_code_generator_agent.py

# Test Solution Architect
python tests/solution_architect/test_solution_architect_agent.py

# Test Quality Validator
python tests/quality_validator/test_quality_validator_agent.py

# Test Deployment Manager
python tests/deployment_manager/test_deployment_manager_agent.py
```

### Verify DynamoDB Records

```bash
for agent in requirements-analyst code-generator solution-architect quality-validator deployment-manager; do
  count=$(aws dynamodb scan \
    --table-name autoninja-inference-records-production \
    --filter-expression "agent_name = :agent" \
    --expression-attribute-values "{\":agent\":{\"S\":\"$agent\"}}" \
    --select COUNT \
    --region us-east-2 | jq -r '.Count')
  echo "$agent: $count records"
done
```

**Expected:** Each agent should have 3-4 records (one per action)

---

## Success Criteria

- [ ] All 5 Lambda functions deployed
- [ ] All 5 Bedrock Agents created and PREPARED
- [ ] All 5 agents have action groups configured
- [ ] Supervisor agent created with 5 collaborator associations
- [ ] DynamoDB table created with GSI
- [ ] S3 bucket created with encryption
- [ ] Lambda Layer deployed and attached to all functions
- [ ] All agents tested individually
- [ ] All agents have DynamoDB records
- [ ] All agents have S3 artifacts
- [ ] CloudFormation stack shows CREATE_COMPLETE
- [ ] No manual configuration required

---

## Timeline

- **Phase 2 (Standardization):** 2-3 hours
- **Phase 3 (CloudFormation):** 2-3 hours
- **Phase 4 (Implementation):** 1-2 hours
- **Phase 5 (Testing):** 1-2 hours

**Total:** 6-10 hours for complete standardization and one-shot deployment

---

## Rollback Plan

If deployment fails:
```bash
# Delete stack
aws cloudformation delete-stack --stack-name autoninja-production

# Clean up S3 bucket (if needed)
aws s3 rm s3://autoninja-artifacts-{AccountId}-production --recursive

# Verify cleanup
aws cloudformation describe-stacks --stack-name autoninja-production
```

---

## Next Steps

1. Review this plan
2. Confirm approach
3. Begin Phase 2 (Agent Standardization)
4. Create complete CloudFormation template
5. Deploy and test

**Ready to proceed?**
