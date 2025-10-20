---
Metadata:
  AWSToolsMetrics:
    IaC_Generator: "arn:aws:cloudformation:us-east-2:784327326356:generatedTemplate/0e1c6fc3-2d95-49f2-bba8-098a646c51da"
Resources:
  BedrockAgent:
    UpdateReplacePolicy: "Retain"
    Type: "AWS::Bedrock::Agent"
    DeletionPolicy: "Retain"
    Properties:
      AgentCollaborators: []
      Description: "Code Generator agent - extracts and validates requirements from\
        \ user requests"
      PromptOverrideConfiguration:
        PromptConfigurations: []
      AgentCollaboration: "DISABLED"
      Instruction: "You are a requirements analyst for the AutoNinja system. Your\
        \ role is to extract structured\nrequirements from user requests for AI agents.\
        \ You generate requirements for ALL sub-agents\nin the pipeline (Code Generator,\
        \ Solution Architect, Quality Validator, Deployment Manager).\n\nWhen you\
        \ receive a request:\n1. Extract the job_name parameter from the request\n\
        2. Analyze the user's description to identify agent purpose, capabilities,\
        \ interactions, data needs, and integrations\n3. Generate comprehensive requirements\
        \ document covering what each downstream agent needs\n4. Assess complexity\
        \ (simple/moderate/complex)\n5. Validate completeness of requirements\n6.\
        \ Return structured requirements in JSON format\n\nAlways use the job_name\
        \ provided by the supervisor for tracking.\n"
      TestAliasTags: {}
      AgentResourceRoleArn: "arn:aws:iam::784327326356:role/autoninja-collaborators-production-CodeGe-AgentRole-3dHisTDi0ayU"
      OrchestrationType: "DEFAULT"
      FoundationModel: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
      IdleSessionTTLInSeconds: 1800
      AgentName: "autoninja-code-generator-production"
      KnowledgeBases: []
      ActionGroups:
      - Description: "Actions for requirements analysis"
        ApiSchema:
          S3:
            S3BucketName: "autoninja-deployment-artifacts-us-east-2"
            S3ObjectKey: "schemas/code-generator-schema.yaml"
        ActionGroupExecutor:
          Lambda: "arn:aws:lambda:us-east-2:784327326356:function:autoninja-code-generator-production"
        ActionGroupName: "code-generator-actions"
        ActionGroupState: "ENABLED"
      Tags:
        Environment: "production"
        Application: "AutoNinja"
  BedrockAgentAliasE1:
    UpdateReplacePolicy: "Retain"
    Type: "AWS::Bedrock::AgentAlias"
    DeletionPolicy: "Retain"
    Properties:
      AgentAliasName: "production"
      Description: "Production alias for Code Generator agent"
      AgentId:
        Ref: "BedrockAgent"
      RoutingConfiguration:
      - AgentVersion: "1"
      Tags: {}
  BedrockAgentUv:
    UpdateReplacePolicy: "Retain"
    Type: "AWS::Bedrock::Agent"
    DeletionPolicy: "Retain"
    Properties:
      AgentCollaborators: []
      Description: "Deployment Manager agent - extracts and validates requirements\
        \ from user requests"
      PromptOverrideConfiguration:
        PromptConfigurations: []
      AgentCollaboration: "SUPERVISOR"
      Instruction: "You are a requirements analyst for the AutoNinja system. Your\
        \ role is to extract structured\nrequirements from user requests for AI agents.\
        \ You generate requirements for ALL sub-agents\nin the pipeline (Code Generator,\
        \ Solution Architect, Quality Validator, Deployment Manager).\n\nWhen you\
        \ receive a request:\n1. Extract the job_name parameter from the request\n\
        2. Analyze the user's description to identify agent purpose, capabilities,\
        \ interactions, data needs, and integrations\n3. Generate comprehensive requirements\
        \ document covering what each downstream agent needs\n4. Assess complexity\
        \ (simple/moderate/complex)\n5. Validate completeness of requirements\n6.\
        \ Return structured requirements in JSON format\n\nAlways use the job_name\
        \ provided by the supervisor for tracking.\n"
      TestAliasTags: {}
      AgentResourceRoleArn: "arn:aws:iam::784327326356:role/autoninja-collaborators-production-Deploy-AgentRole-T1h4DaX2ecd3"
      OrchestrationType: "DEFAULT"
      FoundationModel: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
      IdleSessionTTLInSeconds: 1800
      AgentName: "autoninja-deployment-manager-production"
      KnowledgeBases: []
      ActionGroups:
      - Description: "Actions for requirements analysis"
        ApiSchema:
          S3:
            S3BucketName: "autoninja-deployment-artifacts-us-east-2"
            S3ObjectKey: "schemas/deployment-manager-schema.yaml"
        ActionGroupExecutor:
          Lambda: "arn:aws:lambda:us-east-2:784327326356:function:autoninja-deployment-manager-production"
        ActionGroupName: "deployment-manager-actions"
        ActionGroupState: "ENABLED"
      Tags:
        Environment: "production"
        Application: "AutoNinja"
  BedrockAgentAlias:
    UpdateReplacePolicy: "Retain"
    Type: "AWS::Bedrock::AgentAlias"
    DeletionPolicy: "Retain"
    Properties:
      AgentAliasName: "AgentTestAlias"
      Description: "Test Alias for Agent"
      AgentId:
        Ref: "BedrockAgent"
      RoutingConfiguration:
      - AgentVersion: "DRAFT"
      Tags: {}
  BedrockAgentAliasMf:
    UpdateReplacePolicy: "Retain"
    Type: "AWS::Bedrock::AgentAlias"
    DeletionPolicy: "Retain"
    Properties:
      AgentAliasName: "production"
      Description: "Production alias for Deployment Manager agent"
      AgentId:
        Ref: "BedrockAgentUv"
      RoutingConfiguration:
      - AgentVersion: "1"
      Tags: {}
  BedrockAgentAliasSl:
    UpdateReplacePolicy: "Retain"
    Type: "AWS::Bedrock::AgentAlias"
    DeletionPolicy: "Retain"
    Properties:
      AgentAliasName: "AgentTestAlias"
      Description: "Test Alias for Agent"
      AgentId:
        Ref: "BedrockAgentUv"
      RoutingConfiguration:
      - AgentVersion: "DRAFT"
      Tags: {}
