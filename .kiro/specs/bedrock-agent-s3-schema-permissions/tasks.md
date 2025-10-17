# Implementation Plan

- [x] 1. Add Bedrock Agent IAM roles to CloudFormation template

  - Add 5 IAM role resources (one per agent) with trust policies and permissions
  - Include bedrock:InvokeModel, s3:GetObject, and s3:ListBucket permissions
  - Add condition keys for security (aws:SourceAccount, AWS:SourceArn, aws:ResourceAccount)
  - Insert after Lambda roles section in autoninja-complete.yaml
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 3.1_

- [x] 2. Add Lambda invoke permissions for Bedrock Agents

  - Create 5 AWS::Lambda::Permission resources (one per Lambda function)
  - Set Principal to bedrock.amazonaws.com
  - Add SourceAccount and SourceArn conditions for security
  - Insert after Lambda functions section in autoninja-complete.yaml
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 3. Update Bedrock Agent resources to reference IAM roles

  - Update DependsOn to include agent role for each agent
  - Update AgentResourceRoleArn to use !GetAtt for each agent role
  - Modify bedrock-agents-section.yaml or autoninja-complete.yaml (wherever agents are defined)
  - _Requirements: 1.2, 3.2, 3.3_

- [x] 4. Validate CloudFormation template syntax

  - Run aws cloudformation validate-template command
  - Fix any syntax errors or validation issues
  - Verify all resource references are correct
  - _Requirements: 4.3_

- [x] 5. Deploy and test the updated CloudFormation stack
  - Run ./scripts/deploy_all.sh to upload schemas and deploy stack
  - Verify all resources created successfully
  - Check CloudFormation events for any permission errors
  - Verify agent status shows PREPARED after deployment
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1, 4.2, 4.3_
