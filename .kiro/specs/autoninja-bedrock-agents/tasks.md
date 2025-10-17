# Implementation Plan

## Overview

This implementation plan breaks down the AutoNinja AWS Bedrock Agents system into discrete, manageable coding tasks. Each task builds incrementally on previous tasks, following test-driven development principles where appropriate. The plan prioritizes core functionality and marks optional testing tasks with "\*".

## Task List

- [x] 1. Set up project structure

  - Create directory structure: lambda/, schemas/, shared/, infrastructure/cloudformation/, examples/, docs/, tests/
  - Create placeholder files in each directory to establish structure
  - Ensure no files are in root except README.md, pyproject.toml, .gitignore
  - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10, 18.11_

- [x] 2. Create CloudFormation template for AutoNinja system (Foundation)

  - [x] 2.1 Define template structure and parameters

    - Read about cloudformation and template from AWS Documentation MCP
    - Create infrastructure/cloudformation/autoninja-complete.yaml
    - Define parameters: Environment, BedrockModel, DynamoDBBillingMode, S3BucketName, LogRetentionDays
    - Add template description and metadata
    - _Requirements: 9.1, 9.10_

  - [x] 2.2 Define DynamoDB table resource

    - Read about DynamoDB from AWS Documentation MCP
    - Table name: autoninja-inference-records
    - Partition key: job_name (String), Sort key: timestamp (String)
    - GSI on session_id, GSI on agent_name + timestamp
    - On-demand billing, point-in-time recovery, KMS encryption
    - _Requirements: 9.4, 9.8_

  - [x] 2.3 Define S3 bucket resource

    - Read about S3 from AWS Documentation MCP
    - Bucket name: autoninja-artifacts-{account-id}
    - Versioning enabled, KMS encryption, bucket policy, lifecycle policy
    - _Requirements: 9.4, 9.9_

  - [x] 2.4 Define Lambda Layer resource

    - Read about Lambda from AWS Documentation MCP
    - Layer name: autoninja-shared-layer
    - Placeholder for shared code (will be populated later)
    - Compatible with Python 3.9+
    - _Requirements: 9.4, 9.10_

  - [x] 2.5 Define IAM roles for Lambda functions

    - Create 5 Lambda execution roles (one per collaborator agent)
    - Attach policies for CloudWatch Logs, DynamoDB, S3, X-Ray
    - Deployment Manager role includes CloudFormation, Bedrock, IAM permissions
    - _Requirements: 9.5, 9.6, 13.2, 13.3_

  - [x] 2.6 Define Lambda function resources (placeholder implementations)

    - Create 5 Lambda functions with minimal handler code
    - Attach Lambda Layer, set environment variables
    - Enable X-Ray tracing, set memory and timeout
    - _Requirements: 9.3, 9.4_

  - [x] 2.7 Define Lambda permissions

    - Resource-based policies allowing bedrock.amazonaws.com to invoke each Lambda
    - _Requirements: 9.7, 13.3_

  - [x] 2.8 Define IAM roles for Bedrock Agents

    - Create 6 Bedrock Agent execution roles (1 supervisor + 5 collaborators)
    - Policies for InvokeModel and InvokeFunction
    - _Requirements: 9.5, 9.6, 13.1_

  - [x] 2.9 Define Bedrock collaborator agent resources

    - Read about Bedrock Agent and AgentCore from AWS Documentation MCP
    - Create 5 collaborator agents with basic instructions
    - Set foundation model (anthropic.claude-sonnet-4-5-20250929-v1:0), IAM role
    - Configure action groups with Lambda ARNs (OpenAPI schemas will be added later)
    - Set agentCollaboration to DISABLED (collaborators don't coordinate)
    - Enable CloudWatch Logs for each agent
    - Configure idle session timeout (default 30 minutes)
    - Optional: Enable code interpreter if needed
    - Optional: Enable user input if needed
    - Optional: Add guardrails for content filtering
    - Optional: Add knowledge bases for RAG
    - _Requirements: 9.2, 9.4, 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 2.10 Define Bedrock collaborator agent aliases

    - Create production alias for each of the 5 collaborator agents
    - _Requirements: 9.2, 9.4_

  - [x] 2.11 Define Bedrock supervisor agent resource

    - Read about Bedrock Agent and AgentCore from AWS Documentation MCP
    - Create supervisor agent with comprehensive instructions for orchestration
    - Set foundation model (anthropic.claude-sonnet-4-5-20250929-v1:0), IAM role
    - Set agentCollaboration to SUPERVISOR (coordinates responses from collaborators)
    - No action groups (coordination only)
    - Enable CloudWatch Logs
    - Configure idle session timeout (default 30 minutes)
    - Optional: Add guardrails for content filtering
    - _Requirements: 9.2, 9.4, 1.1, 1.2, 1.3, 1.4_

  - [x] 2.12 Define Bedrock supervisor agent alias

    - Create production alias for supervisor agent
    - _Requirements: 9.2, 9.4_

  - [x] 2.13 Define agent collaborator associations

    - Associate 5 collaborator agents with supervisor agent using AssociateAgentCollaborator
    - Provide collaboration instructions for each collaborator (when to use them)
    - Configure conversation history sharing (optional per collaborator)
    - Set collaborator names and descriptions
    - _Requirements: 9.4, 9.11, 1.5_

  - [x] 2.14 Define CloudWatch log groups and monitoring

    - Create log groups for 6 Bedrock Agents: /aws/bedrock/agents/{agent-name}
    - Create log groups for 5 Lambda functions: /aws/lambda/{function-name}
    - Set retention period (default 30 days, configurable via parameter)
    - Enable CloudWatch Logs for all Bedrock Agents
    - Enable CloudWatch Logs for all Lambda functions
    - Configure structured logging format (JSON)
    - _Requirements: 8.1, 8.2, 9.4, 9.10_

  - [x] 2.15 Define stack outputs

    - Output supervisor agent ID, ARN, alias ID
    - Output collaborator agent IDs
    - Output DynamoDB table name, S3 bucket name
    - Output invocation command
    - _Requirements: 9.10_

  - [x] 2.16 Validate and deploy CloudFormation template
    - Use cfn-lint to validate syntax
    - Deploy to test AWS account
    - Verify all resources are created
    - Test basic invocation of supervisor agent
    - _Requirements: 17.8, 9.1_

- [x] 3. Define data models for structured communications and persistence

  - [x] 3.1 Define InferenceRecord model

    - Create shared/models/inference_record.py
    - Define InferenceRecord dataclass with fields: job_name, timestamp, session_id, agent_name, action_name, inference_id, prompt (raw), response (raw), model_id, tokens_used, cost_estimate, duration_seconds, artifacts_s3_uri, status, error_message
    - Implement to_dynamodb() method for DynamoDB serialization
    - Implement from_dynamodb() method for DynamoDB deserialization
    - _Requirements: 7.3, 11.3_

  - [x] 3.2 Define Requirements model

    - Create shared/models/requirements.py
    - Define Requirements dataclass for structured requirements
    - Include fields for agent purpose, capabilities, interactions, data needs, integrations, system prompts, Lambda requirements, architecture requirements, deployment requirements
    - Implement to_json() and from_json() methods
    - _Requirements: 2.1_

  - [x] 3.3 Define Architecture model

    - Create shared/models/architecture.py
    - Define Architecture dataclass for architecture design
    - Include fields for services, resources, IAM policies, integration points
    - Implement to_json() and from_json() methods
    - _Requirements: 3.1_

  - [x] 3.4 Define Code Artifacts model

    - Create shared/models/code_artifacts.py
    - Define CodeArtifacts dataclass for generated code
    - Include fields for lambda_code, agent_config, openapi_schemas, system_prompts, requirements_txt
    - Implement to_json() and from_json() methods
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 3.5 Define Validation Report model

    - Create shared/models/validation_report.py
    - Define ValidationReport dataclass for quality validation results
    - Include fields for is_valid, quality_score, issues, vulnerabilities, compliance_violations, risk_level
    - Implement to_json() and from_json() methods
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 3.6 Define Deployment Results model

    - Create shared/models/deployment_results.py
    - Define DeploymentResults dataclass for deployment outcomes
    - Include fields for stack_id, agent_id, agent_arn, alias_id, test_results, is_successful
    - Implement to_json() and from_json() methods
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 3.7 Define Agent Communication models
    - Create shared/models/agent_messages.py
    - Define message formats for supervisor-to-collaborator communication
    - Define message formats for collaborator-to-supervisor responses
    - Ensure all messages include job_name for tracking
    - Implement validation methods for message structure
    - _Requirements: 1.2, 1.3, 7.1_

- [x] 4. Implement shared libraries (persistence layer)

  - [x] 4.0 Add DynamoDB, S3 and Lambda layer back into the CloudFormation Template

  - [x] 4.1 Implement DynamoDB client wrapper

    - Create shared/persistence/dynamodb_client.py
    - Implement log_inference_input() to save raw prompts immediately using InferenceRecord model
    - Implement log_inference_output() to save raw responses immediately using InferenceRecord model
    - Implement log_error_to_dynamodb() for error tracking
    - Implement query methods for retrieving records by job_name
    - NO MOCKING - all calls must be real and persisted
    - _Requirements: 7.2, 7.3, 7.10, 11.1_

  - [x] 4.2 Implement S3 client wrapper

    - Create shared/persistence/s3_client.py
    - Implement save_raw_response() to save raw agent responses
    - Implement save_converted_artifact() to save processed data using appropriate models (Requirements, Architecture, CodeArtifacts, etc.)
    - Implement proper S3 key structure: {job_name}/{phase}/{agent_name}/{filename}
    - Implement methods to retrieve artifacts by job_name and deserialize to models
    - NO MOCKING - all calls must be real and persisted
    - _Requirements: 7.4, 7.5, 7.6, 7.7, 11.2_

  - [x] 4.3 Implement utility modules

    - Create shared/utils/job_generator.py for job_name generation (format: job-{keyword}-{YYYYMMDD-HHMMSS})
    - Create shared/utils/logger.py for structured logging (JSON format with job_name, agent_name, action_name)
    - _Requirements: 11.4, 11.5, 7.1_

  - [x] 4.4 Package shared libraries as Lambda Layer
  - Update the stack
    - Create proper directory structure for Lambda Layer: python/shared/{models,persistence,utils}
    - Include all model classes, persistence clients, and utilities
    - Update CloudFormation template with actual Layer code
    - Redeploy CloudFormation stack with updated Layer
    - _Requirements: 11.6_

- [x] 5. Create OpenAPI schemas for all action groups

  - Create schemas/requirements-analyst-schema.yaml with actions: extract_requirements, analyze_complexity, validate_requirements
  - Create schemas/code-generator-schema.yaml with actions: generate_lambda_code, generate_agent_config, generate_openapi_schema
  - Create schemas/solution-architect-schema.yaml with actions: design_architecture, select_services, generate_iac
  - Create schemas/quality-validator-schema.yaml with actions: validate_code, security_scan, compliance_check
  - Create schemas/deployment-manager-schema.yaml with actions: generate_cloudformation, deploy_stack, configure_agent, test_deployment
  - Ensure all schemas include job_name as required parameter
  - Define request/response schemas using the data models (Requirements, Architecture, CodeArtifacts, ValidationReport, DeploymentResults)
  - Update CloudFormation template to reference these schemas in action groups
  - Redeploy CloudFormation stack with updated schemas
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 6. Implement Requirements Analyst Lambda function

  - [x] 6.1 Create Lambda handler with proper event parsing

    - Parse Bedrock Agent input event format
    - Extract job_name, user_request, and other parameters
    - Route to appropriate action handler based on apiPath
    - _Requirements: 2.1, 10.1, 10.2_

  - [x] 6.2 Implement extract_requirements action

    - Log raw input to DynamoDB immediately
    - Extract requirements for ALL sub-agents (Code Generator, Solution Architect, Quality Validator, Deployment Manager)
    - Generate comprehensive requirements JSON
    - Log raw output to DynamoDB immediately
    - Save requirements JSON to S3
    - Return formatted response to Bedrock Agent
    - _Requirements: 2.1, 2.4, 2.5, 7.2, 7.3, 7.4, 7.5, 7.6, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

  - [x] 6.3 Implement analyze_complexity action

    - Log raw input to DynamoDB immediately
    - Analyze requirements complexity
    - Generate complexity assessment
    - Log raw output to DynamoDB immediately
    - Save assessment to S3
    - Return formatted response
    - _Requirements: 2.2, 7.2, 7.3, 7.6, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 6.4 Implement validate_requirements action

    - Log raw input to DynamoDB immediately
    - Validate requirements completeness
    - Identify missing items
    - Log raw output to DynamoDB immediately
    - Save validation results to S3
    - Return formatted response
    - _Requirements: 2.3, 7.2, 7.3, 7.6, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 6.5 Implement error handling
    - Add try-catch blocks for all actions
    - Log errors to DynamoDB with error_message field
    - Return structured error responses
    - _Requirements: 10.4, 10.11_

- [x] 7. Implement Code Generator Lambda function

  - Read about Bedrock Agents and AgentCore from the AWS Documentation MCP.

  - [x] 7.1 Create Lambda handler with proper event parsing

    - **CRITICAL**: Review `lambda/requirements-analyst/handler.py` line-by-line to understand the EXACT pattern
    - Copy the main `lambda_handler()` structure from Requirements Analyst
    - Parse Bedrock Agent input event format (same as Requirements Analyst)
    - Extract job_name, requirements, and other parameters from `properties` array
    - Route to appropriate action handler based on apiPath (same pattern as Requirements Analyst)
    - _Requirements: 4.1, 10.1, 10.2_

  - [x] 7.2 Implement generate_lambda_code action

    - **CRITICAL**: Copy the EXACT structure from `handle_extract_requirements()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start (before any processing)
    - **STEP 2**: Store the returned `timestamp` value in a variable
    - **STEP 3**: Generate Python Lambda function code with error handling (your custom logic here)
    - **STEP 4**: Generate requirements.txt with dependencies (your custom logic here)
    - **STEP 5**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` IMMEDIATELY after generation
    - **STEP 6**: Save generated code files to S3 using `s3_client.save_converted_artifact()`
    - **STEP 7**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 8**: Return formatted response to Bedrock Agent (same format as Requirements Analyst)
    - **VERIFICATION**: After implementation, check DynamoDB to confirm BOTH input and output records are created for EACH invocation
    - _Requirements: 4.1, 4.4, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 7.3 Implement generate_agent_config action

    - **CRITICAL**: Copy the EXACT structure from `handle_analyze_complexity()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value
    - **STEP 3**: Generate Bedrock Agent configuration JSON (your custom logic)
    - **STEP 4**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp`
    - **STEP 5**: Save config JSON to S3 using `s3_client.save_converted_artifact()`
    - **STEP 6**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 7**: Return formatted response
    - **VERIFICATION**: Check DynamoDB for both input and output records
    - _Requirements: 4.2, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 7.4 Implement generate_openapi_schema action

    - **CRITICAL**: Copy the EXACT structure from `handle_validate_requirements()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value
    - **STEP 3**: Generate OpenAPI 3.0 schema (your custom logic)
    - **STEP 4**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp`
    - **STEP 5**: Save schema YAML to S3 using `s3_client.save_converted_artifact()`
    - **STEP 6**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 7**: Return formatted response
    - **VERIFICATION**: Check DynamoDB for both input and output records
    - _Requirements: 4.3, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 7.5 Implement error handling

    - **CRITICAL**: Copy the EXACT error handling pattern from Requirements Analyst
    - Add try-catch blocks for all actions (same structure as Requirements Analyst)
    - Log errors to DynamoDB using `dynamodb_client.log_error_to_dynamodb()`
    - Return structured error responses (same format as Requirements Analyst)
    - _Requirements: 10.4, 10.11_

  - [x] 7.6 Test implementation and verify DynamoDB logging
    - **CRITICAL**: Review `tests/requirement_analyst/test_requirements_analyst_agent.py` to understand test pattern
    - Create `tests/code_generator/test_code_generator_agent.py` following the same structure
    - Run the test with all 3 actions (generate_lambda_code, generate_agent_config, generate_openapi_schema)
    - **VERIFICATION STEP 1**: After running tests, query DynamoDB to confirm records exist:
      ```bash
      aws dynamodb query --table-name autoninja-inference-records-production \
        --index-name AgentNameTimestampIndex \
        --key-condition-expression "agent_name = :agent" \
        --expression-attribute-values '{":agent":{"S":"code-generator"}}' \
        --region us-east-2
      ```
    - **VERIFICATION STEP 2**: Confirm you see 6 records total (3 input + 3 output) for the 3 test invocations
    - **VERIFICATION STEP 3**: Check each record has both `prompt` and `response` fields populated
    - **FAILURE CONDITION**: If you see fewer than 6 records, the logging is NOT working correctly - review the code against Requirements Analyst implementation

- [x] 8. Implement Solution Architect Lambda function

  - [x] 8.1 Create Lambda handler with proper event parsing

    - **CRITICAL**: Copy the EXACT structure from `lambda/requirements-analyst/handler.py` main `lambda_handler()` function
    - Parse Bedrock Agent input event format (same as Requirements Analyst and Code Generator)
    - Extract job_name, requirements, code_file_references, and other parameters from `properties` array
    - Route to appropriate action handler based on apiPath (same pattern)
    - _Requirements: 3.1, 10.1, 10.2_

  - [x] 8.2 Implement design_architecture action

    - **CRITICAL**: Copy the EXACT structure from `handle_extract_requirements()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start (before any processing)
    - **STEP 2**: Store the returned `timestamp` value in a variable
    - **STEP 3**: Retrieve code files from Code Generator using `s3_client` (your custom logic)
    - **STEP 4**: Design AWS architecture based on requirements and code (your custom logic)
    - **STEP 5**: Generate architecture design document (your custom logic)
    - **STEP 6**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` IMMEDIATELY after generation
    - **STEP 7**: Save architecture design to S3 using `s3_client.save_converted_artifact()`
    - **STEP 8**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 9**: Return formatted response to Bedrock Agent (same format as Requirements Analyst)
    - **VERIFICATION**: Check DynamoDB for both input and output records
    - _Requirements: 3.1, 3.4, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 8.3 Implement select_services action

    - **CRITICAL**: Copy the EXACT structure from `handle_analyze_complexity()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value
    - **STEP 3**: Select appropriate AWS services based on requirements (your custom logic)
    - **STEP 4**: Generate service selection rationale (your custom logic)
    - **STEP 5**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp`
    - **STEP 6**: Save service selection to S3 using `s3_client.save_converted_artifact()`
    - **STEP 7**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 8**: Return formatted response
    - **VERIFICATION**: Check DynamoDB for both input and output records
    - _Requirements: 3.2, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 8.4 Implement generate_iac action

    - **CRITICAL**: Copy the EXACT structure from `handle_validate_requirements()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value
    - **STEP 3**: Generate CloudFormation template referencing Lambda code files (your custom logic)
    - **STEP 4**: Include Bedrock Agent configuration from Code Generator (your custom logic)
    - **STEP 5**: Set up IAM roles and policies (your custom logic)
    - **STEP 6**: Configure action groups with OpenAPI schemas (your custom logic)
    - **STEP 7**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp`
    - **STEP 8**: Save IaC templates to S3 using `s3_client.save_converted_artifact()`
    - **STEP 9**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 10**: Return formatted response
    - **VERIFICATION**: Check DynamoDB for both input and output records
    - _Requirements: 3.3, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 8.5 Implement error handling

    - **CRITICAL**: Copy the EXACT error handling pattern from Requirements Analyst
    - Add try-catch blocks for all actions (same structure as Requirements Analyst)
    - Log errors to DynamoDB using `dynamodb_client.log_error_to_dynamodb()`
    - Return structured error responses (same format as Requirements Analyst)
    - _Requirements: 10.4, 10.11_

  - [x] 8.6 Test implementation and verify DynamoDB logging
    - Create `tests/solution_architect/test_solution_architect_agent.py` following the same structure as Requirements Analyst test
    - Run the test with all 3 actions (design_architecture, select_services, generate_iac)
    - **VERIFICATION**: Query DynamoDB to confirm 6 records total (3 input + 3 output) exist for solution-architect agent
    - **FAILURE CONDITION**: If you see fewer than 6 records, review the code against Requirements Analyst implementation

- [x] 9. Implement Quality Validator BEDROCK Agent Lambda function

  - [x] 9.1 Create Lambda handler with proper BEDROCK Agent event parsing
        **BEFORE YOU START - IMPORTANT TIPS:**
  - ✅ Check actual AWS resources first: Run `aws s3 ls | grep autoninja` to get the real bucket name
  - ✅ DynamoDB logging creates 1 record per action (not 2): `log_inference_input()` creates, `log_inference_output()` updates
  - ✅ When replacing functions, read extra context to avoid leaving orphaned code (especially multi-line strings)
  - ✅ "EXACT structure" means the flow pattern (logging → processing → saving), NOT the business logic
  - ✅ Test files need correct bucket name: `f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID')}-production"`

    - **CRITICAL**: Copy the EXACT structure from `lambda/requirements-analyst/handler.py` main `lambda_handler()` function
    - Parse BEDROCK Agent input event format (same as Requirements Analyst)
    - Extract job_name, code, architecture, and other parameters from `properties` array
    - Route to appropriate action handler based on apiPath (same pattern)
    - _Requirements: 5.1, 10.1, 10.2_

  - [x] 9.2 Implement validate_code action

    - **CRITICAL**: Copy the EXACT structure from `handle_extract_requirements()` in Requirements Analyst
    - **WHAT "EXACT STRUCTURE" MEANS**: Same flow of logging → processing → saving, NOT the same business logic
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start (before any processing)
    - **STEP 2**: Store the returned `timestamp` value in a variable (e.g., `timestamp = dynamodb_client.log_inference_input(...)['timestamp']`)
    - **STEP 3**: Perform code quality validation - syntax, error handling, logging, structure (your custom logic)
    - **STEP 4**: Calculate quality score (your custom logic)
    - **STEP 5**: Set extremely low threshold (e.g., 50% pass rate) for testi (your custom logic)
    - **STEP 6**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` IMMEDIATELY after validation
    - **NOTE**: This UPDATES the same DynamoDB record created in STEP 1, doesn't create a new one
    - **STEP 7**: Save validation report to S3 using `s3_client.save_converted_artifact()`
    - **STEP 8**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 9**: Return formatted response to BEDROCK Agent with is_valid, issues, quality_score (same format as Requirements Analyst)
    - **VERIFICATION**: Check DynamoDB - should see 1 record with both `prompt` and `response` fields populated
    - _Requirements: 5.1, 5.4, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8, 17.2, 17.3_

  - [x] 9.3 Implement security_scan action

    - **CRITICAL**: Copy the EXACT structure from `handle_analyze_complexity()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value in a variable
    - **STEP 3**: Scan for hardcoded credentials (your custom logic)
    - **STEP 4**: Validate IAM permissions follow least-privilege (your custom logic)
    - **STEP 5**: Check for injection vulnerabilities (your custom logic)
    - **STEP 6**: Verify encryption usage (your custom logic)
    - **STEP 7**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` to UPDATE the record
    - **STEP 8**: Save security findings to S3 using `s3_client.save_converted_artifact()`
    - **STEP 9**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 10**: Return formatted response to BEDROCK Agent with vulnerabilities and risk_level
    - **VERIFICATION**: Check DynamoDB - should see 1 record with both `prompt` and `response` fields
    - _Requirements: 5.2, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 9.4 Implement compliance_check action

    - **CRITICAL**: Copy the EXACT structure from `handle_validate_requirements()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value in a variable
    - **STEP 3**: Check AWS best practices compliance (your custom logic)
    - **STEP 4**: Check Lambda best practices compliance (your custom logic)
    - **STEP 5**: Check Python PEP 8 standards (your custom logic)
    - **STEP 6**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` to UPDATE the record
    - **STEP 7**: Save compliance report to S3 using `s3_client.save_converted_artifact()`
    - **STEP 8**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 9**: Return formatted response to BEDROCK Agent with compliant flag and violations
    - **VERIFICATION**: Check DynamoDB - should see 1 record with both `prompt` and `response` fields
    - _Requirements: 5.3, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 9.5 Implement error handling

    - **CRITICAL**: Copy the EXACT error handling pattern from Requirements Analyst
    - Add try-catch blocks for all actions (same structure as Requirements Analyst)
    - Log errors to DynamoDB using `dynamodb_client.log_error_to_dynamodb()`
    - Return structured error responses to BEDROCK Agent (same format as Requirements Analyst)
    - _Requirements: 10.4, 10.11_

  - [x] 9.6 Test implementation and verify DynamoDB logging

    - **IMPORTANT**: First verify the S3 bucket name by running `aws s3 ls | grep autoninja` to get the actual bucket name
    - Update test file to use correct bucket: `f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID', '784327326356')}-production"`
    - Create `tests/quality_validator/test_handler.py` following the same structure as `tests/solution_architect/test_handler.py`
    - Run the test with all 3 actions (validate_code, security_scan, compliance_check)
    - **VERIFICATION**: Query DynamoDB to confirm 3 records total (one per action, each containing both input and output)
    - **NOTE**: Each record is created by `log_inference_input()` and then UPDATED by `log_inference_output()` - not separate records
    - **VERIFICATION COMMAND**: `aws dynamodb scan --table-name autoninja-inference-records-production --filter-expression "agent_name = :agent AND begins_with(job_name, :job)" --expression-attribute-values '{":agent":{"S":"quality-validator"}, ":job":{"S":"job-test-"}}' --region us-east-2 --query 'Count'`
    - **SUCCESS CRITERIA**: All 3 tests pass AND 3 DynamoDB records exist AND artifacts saved to S3
    - **FAILURE CONDITION**: If you see fewer than 3 records, review the code against Requirements Analyst implementation

  - [x] 9.7 Package and deploy Quality Validator Lambda to AWS

    - Make the deployment script executable: `chmod +x scripts/deploy_quality_validator.sh`
    - Run deployment script: `./scripts/deploy_quality_validator.sh`
    - Verify Lambda function updated successfully in AWS Console
    - _Requirements: 10.9_

  - [x] 9.8 Update BEDROCK Agent with OpenAPI schema

    - Upload `schemas/quality-validator-schema.yaml` to S3 bucket for schemas
    - Update Quality Validator BEDROCK Agent action group to reference the schema
    - Prepare the BEDROCK Agent (creates new version)
    - Create/update alias to point to new version
    - _Requirements: 12.4_

  - [-] 9.9 Test Quality Validator BEDROCK Agent end-to-end
    - Create test script `tests/quality_validator/test_quality_validator_agent.py`
    - Invoke BEDROCK Agent with test code samples
    - Verify all 3 actions work: validate_code, security_scan, compliance_check
    - Verify responses contain expected validation results
    - Verify DynamoDB records created for BEDROCK Agent invocations
    - Verify S3 artifacts saved correctly
    - _Requirements: 17.1, 17.2, 17.3_

- [-] 10. Implement Deployment Manager Bedrock Agent

  - Read .kiro/specs/autoninja-bedrock-agents/design.md and .kiro/specs/autoninja-bedrock-agents/requirements.md

  - ✅ Check actual AWS resources first: Run `aws s3 ls | grep autoninja` to get the real bucket name
  - ✅ DynamoDB logging creates 1 record per action (not 2): `log_inference_input()` creates, `log_inference_output()` updates
  - ✅ When replacing functions, read extra context to avoid leaving orphaned code (especially multi-line strings)
  - ✅ "EXACT structure" means the flow pattern (logging → processing → saving), NOT the business logic
  - ✅ Test files need correct bucket name: `f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID')}-production"`
  - ✅ Use `s3_client.get_artifact()` for retrieving files - it handles missing files gracefully

  - [x] 10.1 Create Lambda handler with proper event parsing

    - Read about Bedrock Agent from the AWS MCP
    - **CRITICAL**: Copy the EXACT structure from `lambda/requirements-analyst/handler.py` main `lambda_handler()` function
    - Parse Bedrock Agent input event format (same as Requirements Analyst)
    - Extract job_name, requirements, code, architecture, validation_status, and other parameters from `properties` array
    - Check validation_status before proceeding (must be green light) - add this validation logic
    - Route to appropriate action handler based on apiPath (same pattern)
    - _Requirements: 6.1, 10.1, 10.2_

  - [x] 10.2 Implement generate_cloudformation action

    - Read about Bedrock Agent from the AWS MCP
    - **CRITICAL**: Copy the EXACT structure from `handle_extract_requirements()` in Requirements Analyst
    - **WHAT "EXACT STRUCTURE" MEANS**: Same flow of logging → processing → saving, NOT the same business logic
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start (before any processing)
    - **STEP 2**: Store the returned `timestamp` value in a variable (e.g., `timestamp = dynamodb_client.log_inference_input(...)['timestamp']`)
    - **STEP 3**: Gather all artifacts from S3 using `s3_client` - requirements, code, architecture, validation (your custom logic)
    - **TIP**: Use `s3_client.get_artifact()` which handles missing files gracefully (returns None instead of crashing)
    - **STEP 4**: Generate complete CloudFormation template including Lambda functions, Bedrock Agent, action groups, IAM roles (your custom logic)
    - **STEP 5**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` IMMEDIATELY after generation
    - **NOTE**: This UPDATES the same DynamoDB record created in STEP 1, doesn't create a new one
    - **STEP 6**: Save CloudFormation template to S3 using `s3_client.save_converted_artifact()`
    - **STEP 7**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 8**: Return formatted response with template (same format as Requirements Analyst)
    - **VERIFICATION**: Check DynamoDB - should see 1 record with both `prompt` and `response` fields populated
    - _Requirements: 6.1, 6.2, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 10.3 Implement deploy_stack action

    - Read about Bedrock Agent from the AWS MCP
    - **CRITICAL**: Copy the EXACT structure from `handle_analyze_complexity()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value in a variable
    - **STEP 3**: Deploy CloudFormation stack to AWS using boto3 (your custom logic)
    - **STEP 4**: Wait for stack creation to complete (your custom logic)
    - **STEP 5**: Handle deployment failures with proper error messages (your custom logic)
    - **STEP 6**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` to UPDATE the record
    - **STEP 7**: Save deployment results to S3 using `s3_client.save_converted_artifact()`
    - **STEP 8**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 9**: Return formatted response with stack_id, status, outputs
    - **VERIFICATION**: Check DynamoDB - should see 1 record with both `prompt` and `response` fields
    - _Requirements: 6.2, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 10.4 Implement configure_agent action

    - Read about Bedrock Agent from the AWS MCP
    - **CRITICAL**: Copy the EXACT structure from `handle_validate_requirements()` in Requirements Analyst
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value in a variable
    - **STEP 3**: Create Bedrock Agent using boto3 (your custom logic)
    - **STEP 4**: Configure action groups with OpenAPI schemas (your custom logic)
    - **STEP 5**: Create agent alias (your custom logic)
    - **STEP 6**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` to UPDATE the record
    - **STEP 7**: Save agent configuration to S3 using `s3_client.save_converted_artifact()`
    - **STEP 8**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 9**: Return formatted response with agent_id, agent_arn, alias_id
    - **VERIFICATION**: Check DynamoDB - should see 1 record with both `prompt` and `response` fields
    - _Requirements: 6.3, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 10.5 Implement test_deployment action

    - Read about Bedrock Agent from the AWS MCP
    - **CRITICAL**: Copy the EXACT structure from any action handler in Requirements Analyst (e.g., `handle_extract_requirements()`)
    - **STEP 1**: Call `dynamodb_client.log_inference_input()` IMMEDIATELY at the start
    - **STEP 2**: Store the returned `timestamp` value in a variable
    - **STEP 3**: Test deployed agent with sample inputs using InvokeAgent API (your custom logic)
    - **STEP 4**: Verify agent responds correctly (your custom logic)
    - **STEP 5**: Call `dynamodb_client.log_inference_output()` with the stored `timestamp` to UPDATE the record
    - **STEP 6**: Save test results to S3 using `s3_client.save_converted_artifact()`
    - **STEP 7**: Save raw response to S3 using `s3_client.save_raw_response()`
    - **STEP 8**: Return formatted response with test_results and is_successful
    - **VERIFICATION**: Check DynamoDB - should see 1 record with both `prompt` and `response` fields
    - _Requirements: 6.4, 7.2, 7.3, 7.6, 7.7, 10.3, 10.5, 10.6, 10.7, 10.8_

  - [x] 10.6 Implement error handling

    - Read about Bedrock Agent from the AWS MCP
    - **CRITICAL**: Copy the EXACT error handling pattern from Requirements Analyst
    - Add try-catch blocks for all actions (same structure as Requirements Analyst)
    - Log errors to DynamoDB using `dynamodb_client.log_error_to_dynamodb()`
    - Return structured error responses (same format as Requirements Analyst)
    - _Requirements: 10.4, 10.11_

  - [x] 10.7 Test implementation and verify DynamoDB logging

    - Read about Bedrock Agent from the AWS MCP
    - **IMPORTANT**: First verify the S3 bucket name by running `aws s3 ls | grep autoninja` to get the actual bucket name
    - Update test file to use correct bucket: `f"autoninja-artifacts-{os.environ.get('AWS_ACCOUNT_ID', '784327326356')}-production"`
    - Create `tests/deployment_manager/test_handler.py` following the same structure as `tests/solution_architect/test_handler.py`
    - Run the test with all 4 actions (generate_cloudformation, deploy_stack, configure_agent, test_deployment)
    - **VERIFICATION**: Query DynamoDB to confirm 4 records total (one per action, each containing both input and output)
    - **NOTE**: Each record is created by `log_inference_input()` and then UPDATED by `log_inference_output()` - not separate records
    - **VERIFICATION COMMAND**: `aws dynamodb scan --table-name autoninja-inference-records-production --filter-expression "agent_name = :agent AND begins_with(job_name, :job)" --expression-attribute-values '{":agent":{"S":"deployment-manager"}, ":job":{"S":"job-test-"}}' --region us-east-2 --query 'Count'`
    - **SUCCESS CRITERIA**: All 4 tests pass AND 4 DynamoDB records exist AND artifacts saved to S3
    - **FAILURE CONDITION**: If you see fewer than 4 records, review the code against Requirements Analyst implementation

  - [x] 10.8 Update BEDROCK Agent with OpenAPI schema

    - Upload `schemas/deployment-manager-schema.yaml` to S3 bucket for schemas
    - Update Deployment Manager BEDROCK Agent action group to reference the schema
    - Prepare the BEDROCK Agent (creates new version)
    - Create/update alias to point to new version

  - [x] 10.9 Test Deployment Manager BEDROCK Agent end-to-end
    - Create test script `tests/deployment-manager/test_deployment_manager_agent.py`
    - Invoke BEDROCK Agent with test code samples
    - Verify all 3 actions work
    - Verify responses contain expected validation results
    - Verify DynamoDB records created for BEDROCK Agent invocations
    - Verify S3 artifacts saved correctly

  - [ ] 10.10 Comprehensive E2E test for each Bedrock Agent
    - [ ] 10.10.1 Test Requirements Analyst Agent E2E
      - Invoke agent via InvokeAgent API with realistic user request
      - Verify extract_requirements action returns structured requirements
      - Verify analyze_complexity action returns complexity assessment
      - Verify validate_requirements action returns validation results
      - Verify all DynamoDB records created with both prompt and response
      - Verify all S3 artifacts saved correctly
      - _Requirements: 15.4, 17.1, 17.2, 17.3_
    
    - [ ] 10.10.2 Test Code Generator Agent E2E
      - Invoke agent via InvokeAgent API with requirements from previous test
      - Verify generate_lambda_code action returns Python code
      - Verify generate_agent_config action returns Bedrock Agent config
      - Verify generate_openapi_schema action returns valid OpenAPI schema
      - Verify all DynamoDB records created with both prompt and response
      - Verify all S3 artifacts saved correctly
      - _Requirements: 15.4, 17.1, 17.2, 17.3_
    
    - [ ] 10.10.3 Test Solution Architect Agent E2E
      - Invoke agent via InvokeAgent API with requirements and code references
      - Verify design_architecture action returns architecture design
      - Verify select_services action returns AWS service selection
      - Verify generate_iac action returns CloudFormation template
      - Verify all DynamoDB records created with both prompt and response
      - Verify all S3 artifacts saved correctly
      - _Requirements: 15.4, 17.1, 17.2, 17.3_
    
    - [ ] 10.10.4 Test Quality Validator Agent E2E
      - Invoke agent via InvokeAgent API with code, architecture, and requirements
      - Verify validate_code action returns quality report
      - Verify security_scan action returns security findings
      - Verify compliance_check action returns compliance report
      - Verify all DynamoDB records created with both prompt and response
      - Verify all S3 artifacts saved correctly
      - _Requirements: 15.4, 17.1, 17.2, 17.3_
    
    - [ ] 10.10.5 Test Deployment Manager Agent E2E
      - Invoke agent via InvokeAgent API with all artifacts and validation green light
      - Verify generate_cloudformation action returns complete CFN template
      - Verify deploy_stack action deploys stack successfully (or simulates)
      - Verify configure_agent action returns agent configuration
      - Verify test_deployment action returns test results
      - Verify all DynamoDB records created with both prompt and response
      - Verify all S3 artifacts saved correctly
      - _Requirements: 15.4, 17.1, 17.2, 17.3_

- [ ] 11. Implement Orchestrator/Supervisor Agent

  **IMPORTANT**: Read AWS Bedrock Agent multi-agent collaboration documentation before starting:
  - Multi-agent collaboration overview: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html
  - Creating multi-agent collaboration: https://docs.aws.amazon.com/bedrock/latest/userguide/create-multi-agent-collaboration.html
  - InvokeAgent API reference: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_InvokeAgent.html
  - Custom orchestration (optional advanced feature): https://docs.aws.amazon.com/bedrock/latest/userguide/agents-custom-orchestration.html

  **Key AWS Concepts**:
  - Supervisor agent coordinates responses from collaborator agents OR routes to appropriate collaborator
  - Maximum 10 collaborator agents per supervisor
  - Each collaborator must have an alias (not just agent ID)
  - Collaboration instructions tell supervisor when to use each collaborator
  - Conversation history sharing is optional per collaborator
  - Supervisor uses `agentCollaboration: SUPERVISOR` or `SUPERVISOR_ROUTER`
  - Collaborators use `agentCollaboration: DISABLED`

  - [ ] 11.1 Design supervisor agent orchestration logic

    - Read AWS documentation on multi-agent collaboration patterns
    - Define supervisor agent instructions that:
      - Generate unique job_name from user request (format: job-{keyword}-{YYYYMMDD-HHMMSS})
      - Pass job_name to ALL collaborators in every request
      - Understand the pipeline order: Requirements → Code → Architecture → Validation → Deployment
      - Delegate to Requirements Analyst first to generate requirements for ALL sub-agents
      - Distribute requirements to all downstream agents
      - Coordinate responses from collaborators
      - Handle validation gates (Quality Validator must approve before Deployment Manager)
    - Define collaboration instructions for each collaborator (when to use them)
    - Decide on conversation history sharing strategy per collaborator
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 9.2_

  - [ ] 11.2 Implement supervisor agent Lambda function (if using custom orchestration)

    **NOTE**: This task is OPTIONAL. AWS Bedrock provides built-in orchestration for supervisor agents.
    Only implement custom orchestration if you need complex workflow logic beyond AWS's built-in capabilities.

    - Read AWS documentation on custom orchestration
    - Create `lambda/supervisor-orchestrator/handler.py`
    - Implement state machine for orchestration:
      - START → Invoke Requirements Analyst
      - Requirements complete → Invoke Code Generator with requirements
      - Code complete → Invoke Solution Architect with requirements + code
      - Architecture complete → Invoke Quality Validator with all artifacts
      - Validation pass → Invoke Deployment Manager with all artifacts + green light
      - Validation fail → Return error to user
    - Implement job_name generation and distribution logic
    - Implement error handling and retry logic
    - Log all orchestration decisions to DynamoDB
    - _Requirements: 1.2, 1.3, 1.4, 7.1, 10.1, 10.2_

  - [ ] 11.3 Update CloudFormation template with supervisor agent

    - Read existing CloudFormation template at `infrastructure/cloudformation/autoninja-complete.yaml`
    - Verify all 5 collaborator agents are already defined (from task 2.9)
    - Verify all 5 collaborator agent aliases are already defined (from task 2.10)
    - Update supervisor agent resource (already exists from task 2.11) with:
      - Comprehensive orchestration instructions
      - Foundation model: anthropic.claude-sonnet-4-5-20250929-v1:0
      - agentCollaboration: SUPERVISOR (or SUPERVISOR_ROUTER for lower latency)
      - IAM role with permissions to invoke collaborator agents
      - Optional: Custom orchestration Lambda ARN (if using custom orchestration)
    - Update supervisor agent alias (already exists from task 2.12)
    - Update agent collaborator associations (already exists from task 2.13) with:
      - Associate all 5 collaborator agents using AssociateAgentCollaborator
      - Provide collaboration instructions for each collaborator
      - Configure conversation history sharing per collaborator
    - Add IAM permissions for supervisor to invoke collaborator agents
    - _Requirements: 9.2, 9.4, 9.11, 1.5_

  - [ ] 11.4 Create supervisor agent invocation script

    - Create `examples/invoke_supervisor.py` script
    - Use boto3 bedrock-agent-runtime client
    - Implement InvokeAgent API call with:
      - agentId: supervisor agent ID
      - agentAliasId: supervisor agent alias ID
      - sessionId: unique session ID (or reuse for conversation)
      - inputText: user request
      - enableTrace: true (for debugging)
    - Handle streaming response from InvokeAgent
    - Parse and display agent responses
    - Display trace information for debugging
    - _Requirements: 16.5_

  - [ ] 11.5 Test supervisor agent orchestration

    - Deploy updated CloudFormation template with supervisor agent
    - Invoke supervisor agent with test request: "I would like a friend agent"
    - Verify supervisor generates job_name correctly
    - Verify supervisor delegates to Requirements Analyst first
    - Verify supervisor distributes requirements to downstream agents
    - Verify supervisor coordinates responses from all collaborators
    - Verify supervisor handles validation gates correctly
    - Verify all DynamoDB records created with job_name
    - Verify all S3 artifacts saved under job_name prefix
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 15.4_

  - [ ] 11.6 Implement end-to-end integration test

    - Create `tests/integration/test_supervisor_e2e.py`
    - Test complete workflow from user request to deployed agent:
      - Invoke supervisor with realistic user request
      - Wait for Requirements Analyst to complete
      - Wait for Code Generator to complete
      - Wait for Solution Architect to complete
      - Wait for Quality Validator to complete
      - Wait for Deployment Manager to complete (or simulate)
    - Verify all agents invoked in correct order
    - Verify job_name used consistently across all agents
    - Verify all DynamoDB records created
    - Verify all S3 artifacts saved
    - Verify final response contains deployed agent ARN
    - _Requirements: 15.4, 17.1, 17.2, 17.3_

  - [ ] 11.7 Document supervisor agent architecture

    - Create `docs/supervisor-agent-architecture.md`
    - Document supervisor agent design decisions
    - Document orchestration workflow and state transitions
    - Document collaboration instructions for each collaborator
    - Document job_name generation and distribution strategy
    - Document error handling and retry logic
    - Include architecture diagrams (use Mermaid)
    - _Requirements: 16.1, 16.2_

- [ ] 12. Create example scripts and documentation

  - [ ] 12.1 Create query_inference.py script

    - Script to query DynamoDB for inference records by job_name
    - Display all inferences in chronological order
    - Show tokens used, cost, duration for each inference
    - _Requirements: 16.6_

  - [ ] 12.2 Create analyze_artifacts.py script

    - Script to list and download artifacts from S3 for a given job_name
    - Display artifact structure
    - Option to download specific artifacts
    - _Requirements: 16.6_

  - [ ] 12.3 Create deployment guide documentation

    - Document CloudFormation deployment steps
    - Document prerequisites (AWS account, Bedrock access, CLI configuration)
    - Document how to monitor deployment progress
    - Document how to get stack outputs
    - _Requirements: 16.2_

  - [ ] 12.4 Create usage examples documentation

    - Document how to invoke the supervisor agent
    - Provide example user requests
    - Document how to query inference records
    - Document how to retrieve artifacts
    - _Requirements: 16.5, 16.6_

  - [ ] 12.5 Create troubleshooting guide
    - Document common issues and solutions
    - Document how to check CloudWatch logs
    - Document how to view X-Ray traces
    - Document how to debug failed deployments
    - _Requirements: 16.4_

- [ ]\* 13. Implement unit tests for shared libraries

  - Write unit tests for DynamoDB client operations (NO MOCKING - test against real DynamoDB)
  - Write unit tests for S3 client operations (NO MOCKING - test against real S3)
  - Write unit tests for job_name generation
  - Write unit tests for InferenceRecord data model
  - Use pytest for testing framework
  - _Requirements: 15.1, 17.5_

- [ ]\* 14. Implement integration tests for Lambda functions

  - Write integration tests for Requirements Analyst Lambda (NO MOCKING - real LLM calls)
  - Write integration tests for Code Generator Lambda (NO MOCKING - real LLM calls)
  - Write integration tests for Solution Architect Lambda (NO MOCKING - real LLM calls)
  - Write integration tests for Quality Validator Lambda (NO MOCKING - real LLM calls)
  - Write integration tests for Deployment Manager Lambda (NO MOCKING - real LLM calls)
  - All LLM calls must be real and persisted to DynamoDB/S3
  - Deploy to test environment and verify end-to-end flow
  - _Requirements: 15.2, 17.5_

- [ ]\* 15. Implement end-to-end tests
  - Test complete workflow from user request to deployed agent (NO MOCKING - real LLM calls)
  - Verify all inference records are saved to DynamoDB
  - Verify all artifacts are saved to S3
  - Verify deployed agent responds correctly
  - Test with multiple agent types (simple, complex, with knowledge bases)
  - All LLM calls must be real and persisted
  - _Requirements: 15.4, 17.5_
