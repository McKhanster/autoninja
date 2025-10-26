# Using S3-stored Prompts in CloudFormation

## Example: Solution Architect Stack Update

### Before (Embedded Prompt)
```yaml
PromptOverrideConfiguration:
  PromptConfigurations:
    - PromptType: ORCHESTRATION
      PromptCreationMode: OVERRIDDEN
      PromptState: ENABLED
      BasePromptTemplate: |
        # Long embedded prompt content here...
        You are a Senior AWS Solutions Architect...
        [500+ lines of prompt text]
```

### After (S3 Reference)
```yaml
Parameters:
  DeploymentBucket:
    Type: String
    Description: S3 bucket containing prompts and schemas
    Default: autoninja-deployment-artifacts-us-east-2
  
  Environment:
    Type: String
    Default: production

Resources:
  # Custom Resource to Read Prompt from S3
  PromptReader:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.12
      Handler: index.handler
      Role: !GetAtt PromptReaderRole.Arn
      Code:
        ZipFile: |
          import boto3
          import cfnresponse
          
          def handler(event, context):
              try:
                  if event['RequestType'] == 'Delete':
                      cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
                      return
                  
                  s3 = boto3.client('s3')
                  bucket = event['ResourceProperties']['Bucket']
                  key = event['ResourceProperties']['Key']
                  
                  response = s3.get_object(Bucket=bucket, Key=key)
                  prompt = response['Body'].read().decode('utf-8')
                  
                  cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                      'Prompt': prompt
                  })
              except Exception as e:
                  print(f"Error: {e}")
                  cfnresponse.send(event, context, cfnresponse.FAILED, {
                      'Error': str(e)
                  })

  PromptReaderRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: S3ReadAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                Resource: !Sub 'arn:aws:s3:::${DeploymentBucket}/prompts/*'

  # Read the SA prompt from S3
  ReadSAPrompt:
    Type: Custom::PromptReader
    Properties:
      ServiceToken: !GetAtt PromptReader.Arn
      Bucket: !Ref DeploymentBucket
      Key: !Sub 'prompts/${Environment}/sa-nova.md'

  # Bedrock Agent using S3 prompt
  Agent:
    Type: AWS::Bedrock::Agent
    Properties:
      AgentName: !Sub "autoninja-solution-architect-${Environment}"
      PromptOverrideConfiguration:
        PromptConfigurations:
          - PromptType: ORCHESTRATION
            PromptCreationMode: OVERRIDDEN
            PromptState: ENABLED
            BasePromptTemplate: !GetAtt ReadSAPrompt.Prompt
```

## Upload Script Usage

```bash
# Upload prompts to S3
./scripts/upload_prompts_to_s3.sh autoninja-deployment-artifacts-us-east-2 production

# Deploy CloudFormation with S3 prompts
aws cloudformation update-stack \
  --stack-name autoninja-solution-architect-production \
  --template-body file://infrastructure/cloudformation/stacks/solution-architect.yaml \
  --parameters ParameterKey=DeploymentBucket,ParameterValue=autoninja-deployment-artifacts-us-east-2 \
  --capabilities CAPABILITY_IAM
```

## Benefits

1. **Easy Updates**: Change prompts without redeploying CloudFormation
2. **Version Control**: Keep prompts in git, upload to S3 as needed
3. **Environment Separation**: Different prompts per environment
4. **Cleaner Templates**: No huge embedded text blocks
5. **Reusability**: Same prompt can be used across multiple stacks

## File Structure

```
s3://autoninja-deployment-artifacts-us-east-2/
├── prompts/
│   ├── production/
│   │   ├── ra-nova.md
│   │   ├── sa-nova.md
│   │   ├── cg-nova.md
│   │   ├── qv-nova.md
│   │   └── dm-nova.md
│   ├── staging/
│   │   └── [same files]
│   └── development/
│       └── [same files]
└── schemas/
    └── [existing schema files]
```