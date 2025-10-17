# Requirements Document

## Introduction

The AutoNinja CloudFormation template is failing to deploy because Bedrock Agents cannot access their OpenAPI schemas stored in S3. The root cause is that the Bedrock Agent IAM roles are completely missing from the CloudFormation template. According to AWS documentation, each Bedrock Agent requires an IAM service role with specific permissions to access S3 schemas, invoke foundation models, and invoke Lambda functions.

## Glossary

- **Bedrock_Agent**: An AWS Bedrock Agent resource that orchestrates AI-powered workflows
- **Agent_Service_Role**: An IAM role that the Bedrock Agent assumes to access AWS resources
- **OpenAPI_Schema**: A YAML file stored in S3 that defines the action group API structure
- **Action_Group**: A collection of actions that a Bedrock Agent can perform via Lambda functions
- **CloudFormation_Template**: Infrastructure-as-code template that defines AWS resources

## Requirements

### Requirement 1

**User Story:** As a DevOps engineer, I want Bedrock Agents to successfully access their OpenAPI schemas from S3, so that the CloudFormation stack deploys without errors

#### Acceptance Criteria

1. WHEN the CloudFormation template is deployed, THE CloudFormation_Template SHALL create an IAM role for each Bedrock Agent
2. WHEN a Bedrock Agent is created, THE CloudFormation_Template SHALL assign the corresponding Agent_Service_Role to the agent via the AgentResourceRoleArn property
3. WHEN a Bedrock Agent needs to read its schema, THE Agent_Service_Role SHALL have s3:GetObject permission on the schema files in the ArtifactsBucket
4. WHEN a Bedrock Agent needs to list schemas, THE Agent_Service_Role SHALL have s3:ListBucket permission on the ArtifactsBucket
5. WHEN a Bedrock Agent needs to invoke a foundation model, THE Agent_Service_Role SHALL have bedrock:InvokeModel permission on the specified foundation model ARN

### Requirement 2

**User Story:** As a security engineer, I want Bedrock Agent roles to follow AWS security best practices, so that the system maintains proper access controls

#### Acceptance Criteria

1. WHEN an Agent_Service_Role is created, THE CloudFormation_Template SHALL include a trust policy allowing only bedrock.amazonaws.com to assume the role
2. WHEN defining trust policies, THE CloudFormation_Template SHALL include condition keys aws:SourceAccount and AWS:SourceArn to prevent confused deputy attacks
3. WHEN granting S3 permissions, THE Agent_Service_Role SHALL restrict access to only the schemas directory path (schemas/*)
4. WHEN granting model permissions, THE Agent_Service_Role SHALL restrict access to only the specific foundation model specified in the BedrockModel parameter

### Requirement 3

**User Story:** As a developer, I want each Bedrock Agent to have its own dedicated IAM role, so that permissions can be managed independently

#### Acceptance Criteria

1. THE CloudFormation_Template SHALL create five separate Agent_Service_Role resources: RequirementsAnalystAgentRole, CodeGeneratorAgentRole, SolutionArchitectAgentRole, QualityValidatorAgentRole, and DeploymentManagerAgentRole
2. WHEN an agent resource references its role, THE CloudFormation_Template SHALL use the !GetAtt function to retrieve the role ARN
3. WHEN an agent is deleted, THE CloudFormation_Template SHALL ensure the corresponding Agent_Service_Role is also deleted via CloudFormation dependency management

### Requirement 4

**User Story:** As a system administrator, I want the deployment script to upload schemas before creating agents, so that schemas are available when agents are initialized

#### Acceptance Criteria

1. WHEN the deploy_all.sh script runs, THE deployment script SHALL upload all OpenAPI schemas to S3 before deploying the CloudFormation stack
2. WHEN schemas are uploaded, THE deployment script SHALL use server-side encryption with aws:kms
3. WHEN the CloudFormation stack is deployed, THE CloudFormation_Template SHALL reference schemas using the S3 bucket and key paths where schemas were uploaded

### Requirement 5

**User Story:** As a developer, I want Lambda functions to have permission to be invoked by Bedrock Agents, so that action groups function correctly

#### Acceptance Criteria

1. WHEN a Lambda function is created for an action group, THE CloudFormation_Template SHALL create a Lambda permission resource allowing bedrock.amazonaws.com to invoke the function
2. WHEN defining Lambda permissions, THE CloudFormation_Template SHALL use condition keys to restrict invocation to only the specific Bedrock Agent that owns the action group
3. THE CloudFormation_Template SHALL create five Lambda permission resources: one for each agent's Lambda function
