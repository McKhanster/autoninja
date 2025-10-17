# Requirements Document

## Introduction

AutoNinja is a production-grade, serverless multi-agent system built on AWS Bedrock Agents that transforms natural language requests into fully deployed AI agents. The system leverages AWS Bedrock's native multi-agent collaboration (GA March 2025) to orchestrate 6 specialized agents working together to design, generate, validate, and deploy production-ready AI agents from simple natural language descriptions.

The system follows a supervisor-collaborator pattern where one orchestrator agent coordinates 5 specialist agents (Requirements Analyst, Solution Architect, Code Generator, Quality Validator, and Deployment Manager) to handle the complete lifecycle from user request to deployed agent. All interactions are persisted to DynamoDB and S3 for complete audit trails, with CloudWatch logging and X-Ray tracing for observability.

## Requirements

### Requirement 1: Multi-Agent Architecture with Supervisor Orchestration

**User Story:** As a system architect, I want a supervisor-collaborator multi-agent architecture using AWS Bedrock Agents, so that complex agent generation tasks can be broken down and handled by specialized agents working in coordination.

#### Acceptance Criteria

1. WHEN the system is deployed THEN it SHALL create exactly 6 AWS Bedrock Agents (1 supervisor + 5 collaborators)
2. WHEN the supervisor agent receives a user request THEN it SHALL delegate tasks to appropriate collaborator agents based on the workflow phase
3. WHEN a collaborator agent completes its task THEN it SHALL return structured results to the supervisor agent
4. WHEN multiple agents can work in parallel THEN the system SHALL execute them concurrently to optimize performance
5. WHEN agents communicate THEN the system SHALL automatically share conversation history and context between agents
6. WHEN an agent encounters an error THEN the system SHALL implement automatic retry logic with exponential backoff

### Requirement 2: Requirements Analyst Agent

**User Story:** As a requirements analyst agent, I want to extract and validate requirements from natural language user requests, so that downstream agents have clear specifications to work with.

#### Acceptance Criteria

1. WHEN the agent receives a user request THEN it SHALL extract structured requirements in JSON format
2. WHEN analyzing a request THEN it SHALL assess complexity and provide a complexity score
3. WHEN requirements are extracted THEN it SHALL validate completeness and flag missing information
4. WHEN processing completes THEN it SHALL save all outputs to DynamoDB with the job_name as partition key
5. WHEN processing completes THEN it SHALL save all artifacts to S3 under the job-specific prefix
6. WHEN the agent is invoked THEN it SHALL expose Lambda actions: extract_requirements, analyze_complexity, validate_requirements

### Requirement 3: Solution Architect Agent

**User Story:** As a solution architect agent, I want to design AWS architecture for the requested agent, so that the implementation follows AWS best practices and uses appropriate services.

#### Acceptance Criteria

1. WHEN the agent receives validated requirements THEN it SHALL design a complete AWS architecture
2. WHEN designing architecture THEN it SHALL select appropriate AWS services based on requirements
3. WHEN architecture is complete THEN it SHALL generate infrastructure-as-code templates (CloudFormation/Terraform)
4. WHEN processing completes THEN it SHALL save architecture design to DynamoDB with job_name and timestamp
5. WHEN processing completes THEN it SHALL save all architecture artifacts to S3 under the architecture/ prefix
6. WHEN the agent is invoked THEN it SHALL expose Lambda actions: design_architecture, select_services, generate_iac

### Requirement 4: Code Generator Agent

**User Story:** As a code generator agent, I want to generate production-ready Lambda functions and Bedrock Agent configurations, so that the designed agent can be deployed to AWS.

#### Acceptance Criteria

1. WHEN the agent receives architecture design THEN it SHALL generate Lambda function code in Python with error handling
2. WHEN generating code THEN it SHALL create Bedrock Agent configuration JSON with action groups
3. WHEN generating code THEN it SHALL create OpenAPI schemas for all action groups
4. WHEN code is generated THEN it SHALL follow AWS Lambda best practices and security guidelines
5. WHEN processing completes THEN it SHALL save all generated code to DynamoDB and S3 under the code/ prefix
6. WHEN the agent is invoked THEN it SHALL expose Lambda actions: generate_lambda_code, generate_agent_config, generate_openapi_schema, generate_system_prompts

### Requirement 5: Quality Validator Agent

**User Story:** As a quality validator agent, I want to validate generated code for quality, security, and compliance, so that only production-ready code is deployed.

#### Acceptance Criteria

1. WHEN the agent receives generated code THEN it SHALL perform code quality validation checks
2. WHEN validating code THEN it SHALL perform security scanning for common vulnerabilities
3. WHEN validating code THEN it SHALL check compliance with AWS best practices
4. WHEN validation completes THEN it SHALL generate a quality report with findings and recommendations
5. WHEN processing completes THEN it SHALL save validation results to DynamoDB and S3 under the validation/ prefix
6. WHEN the agent is invoked THEN it SHALL expose Lambda actions: validate_code, security_scan, compliance_check

### Requirement 6: Deployment Manager Agent

**User Story:** As a deployment manager agent, I want to deploy generated agents to AWS and verify successful deployment, so that users receive fully functional deployed agents.

#### Acceptance Criteria

1. WHEN the agent receives validated code THEN it SHALL generate a complete CloudFormation template
2. WHEN the template is ready THEN it SHALL deploy the CloudFormation stack to AWS
3. WHEN the stack is deployed THEN it SHALL configure the Bedrock Agent with action groups and aliases
4. WHEN deployment completes THEN it SHALL test the deployed agent to verify functionality
5. WHEN processing completes THEN it SHALL save deployment results and agent ARN to DynamoDB and S3 under the deployment/ prefix
6. WHEN the agent is invoked THEN it SHALL expose Lambda actions: generate_cloudformation, deploy_stack, configure_agent, test_deployment

### Requirement 7: Complete Persistence and Audit Trail

**User Story:** As a system administrator, I want every inference and artifact to be persisted with job tracking, so that I have complete audit trails and can debug issues.

#### Acceptance Criteria

1. WHEN a user request is received THEN the system SHALL generate a unique job_name in format "job-{keyword}-{timestamp}"
2. WHEN any agent makes an inference THEN it SHALL save the complete raw prompt and raw response to DynamoDB with NO exceptions
3. WHEN saving to DynamoDB THEN it SHALL include job_name, session_id, agent_name, inference_id, prompt (raw), response (raw), tokens_used, cost_estimate, duration_seconds, and timestamp
4. WHEN any agent generates artifacts THEN it SHALL extract the inference from the raw response
5. WHEN inference is extracted THEN it SHALL convert it to its final form (config, code, or instruction) if needed
6. WHEN the final form is ready THEN it SHALL save it to S3 under s3://autoninja-artifacts/{job_name}/{phase}/{agent_name}/
7. WHEN saving artifacts to S3 THEN it SHALL save both the raw response AND the converted final form
8. WHEN querying inference records THEN the system SHALL support querying by job_name as partition key
9. WHEN artifacts are stored THEN the DynamoDB record SHALL include the S3 URI in the artifacts_s3_uri field
10. WHEN any data is generated THEN it SHALL be persisted with NO exceptions - all prompts, responses, and artifacts MUST be saved

### Requirement 8: CloudWatch Logging and X-Ray Tracing

**User Story:** As a DevOps engineer, I want comprehensive logging and tracing across all agents and Lambda functions, so that I can monitor system health and debug issues.

#### Acceptance Criteria

1. WHEN any Lambda function executes THEN it SHALL write structured logs to CloudWatch with log group /aws/lambda/{function-name}
2. WHEN any Bedrock Agent executes THEN it SHALL write logs to CloudWatch with log group /aws/bedrock/agents/{agent-name}
3. WHEN a job executes THEN it SHALL create timestamped log streams with the job_name for traceability
4. WHEN any AWS service is invoked THEN the system SHALL enable X-Ray tracing for end-to-end request tracking
5. WHEN viewing X-Ray traces THEN they SHALL be tagged with job_name for filtering
6. WHEN log retention is configured THEN it SHALL default to 30 days with configurable retention periods

### Requirement 9: Infrastructure as Code Deployment

**User Story:** As a DevOps engineer, I want to deploy the entire AutoNinja system using CloudFormation, so that I can provision all resources consistently and repeatably.

#### Acceptance Criteria

1. WHEN deploying the system THEN it SHALL provide a single CloudFormation template that creates all resources
2. WHEN the template is deployed THEN it SHALL create 6 Bedrock Agents with proper configurations
3. WHEN the template is deployed THEN it SHALL create 5 Lambda functions with proper IAM roles and permissions
4. WHEN the template is deployed THEN it SHALL create DynamoDB table with partition key job_name and sort key timestamp
5. WHEN the template is deployed THEN it SHALL create S3 bucket with encryption enabled and proper bucket policies
6. WHEN the template is deployed THEN it SHALL create all IAM roles and policies following least-privilege principles
7. WHEN the template is deployed THEN it SHALL create CloudWatch log groups with configurable retention
8. WHEN the template is deployed THEN it SHALL create Lambda layers for shared code
9. WHEN the template is deployed THEN it SHALL establish agent collaborator associations between supervisor and collaborators
10. WHEN deployment completes THEN it SHALL output the supervisor agent ID, ARN, and invocation command

### Requirement 10: Lambda Function Implementation

**User Story:** As a developer, I want Lambda functions for each collaborator agent that implement the business logic, so that agents can perform their specialized tasks.

#### Acceptance Criteria

1. WHEN a Lambda function is invoked by Bedrock THEN it SHALL receive the action name and parameters from the OpenAPI schema
2. WHEN processing a request THEN it SHALL extract the job_name from parameters and use it for all persistence operations
3. WHEN a Lambda function receives input THEN it SHALL log the complete raw input to DynamoDB before processing
4. WHEN executing business logic THEN it SHALL implement error handling with try-catch blocks and proper error messages
5. WHEN business logic produces output THEN it SHALL log the complete raw output to DynamoDB before returning
6. WHEN saving to DynamoDB THEN it SHALL use the shared persistence layer from Lambda Layer and save ALL prompts and responses
7. WHEN generating artifacts THEN it SHALL extract data from raw responses and convert to final form (code, config, instruction)
8. WHEN saving to S3 THEN it SHALL use the shared S3 client from Lambda Layer and save both raw responses AND converted final forms
9. WHEN logging THEN it SHALL use structured logging with job_name, agent_name, and action_name
10. WHEN returning results THEN it SHALL return JSON responses that conform to the OpenAPI schema
11. WHEN an error occurs THEN it SHALL log the error to DynamoDB and return a structured error response
12. WHEN any data is generated THEN it SHALL be persisted with NO exceptions

### Requirement 11: Shared Libraries Lambda Layer

**User Story:** As a developer, I want shared libraries packaged as a Lambda Layer, so that common code is reused across all Lambda functions without duplication.

#### Acceptance Criteria

1. WHEN the Lambda Layer is created THEN it SHALL include DynamoDB client utilities for inference record operations that save raw prompts and responses
2. WHEN the Lambda Layer is created THEN it SHALL include S3 client utilities for artifact storage operations that save both raw and converted forms
3. WHEN the Lambda Layer is created THEN it SHALL include data models for inference records with fields for raw prompt, raw response, and converted artifacts
4. WHEN the Lambda Layer is created THEN it SHALL include job ID generation utilities
5. WHEN the Lambda Layer is created THEN it SHALL include structured logging utilities that log all data transformations
6. WHEN the Lambda Layer is created THEN it SHALL include utilities to extract and convert inference data from raw responses to final forms
7. WHEN Lambda functions use the layer THEN they SHALL import shared modules from /opt/python/
8. WHEN persistence utilities are used THEN they SHALL enforce that ALL data is persisted with NO exceptions

### Requirement 12: OpenAPI Schemas for Action Groups

**User Story:** As a system integrator, I want OpenAPI schemas that define the interface between Bedrock Agents and Lambda functions, so that agents know what actions are available and how to invoke them.

#### Acceptance Criteria

1. WHEN an action group is defined THEN it SHALL have a complete OpenAPI 3.0 schema
2. WHEN the schema is defined THEN it SHALL include all action endpoints with proper HTTP methods
3. WHEN the schema is defined THEN it SHALL include request body schemas with required parameters including job_name
4. WHEN the schema is defined THEN it SHALL include response schemas with success and error formats
5. WHEN the schema is defined THEN it SHALL include descriptions for all actions, parameters, and responses
6. WHEN Bedrock Agent uses the schema THEN it SHALL be able to invoke Lambda functions with properly formatted requests

### Requirement 13: Security and IAM Configuration

**User Story:** As a security engineer, I want all IAM roles and policies to follow least-privilege principles, so that the system is secure and compliant.

#### Acceptance Criteria

1. WHEN Bedrock Agents are created THEN each SHALL have a dedicated IAM role with minimal permissions
2. WHEN Lambda functions are created THEN each SHALL have a dedicated IAM role with minimal permissions
3. WHEN Lambda needs to be invoked by Bedrock THEN it SHALL have resource-based policies allowing bedrock.amazonaws.com
4. WHEN data is stored in DynamoDB THEN it SHALL be encrypted at rest using AWS KMS
5. WHEN data is stored in S3 THEN it SHALL be encrypted at rest using AWS KMS
6. WHEN API calls are made THEN they SHALL use TLS 1.3 for encryption in transit
7. WHEN CloudTrail is enabled THEN all API calls SHALL be logged for audit purposes

### Requirement 14: Cost Optimization and Monitoring

**User Story:** As a finance manager, I want to track costs per generation and optimize resource usage, so that the system operates cost-effectively.

#### Acceptance Criteria

1. WHEN an inference is made THEN the system SHALL calculate and store estimated cost based on tokens used
2. WHEN storing inference records THEN it SHALL include tokens_used and cost_estimate fields
3. WHEN Lambda functions execute THEN they SHALL use appropriate memory settings to balance cost and performance
4. WHEN DynamoDB is configured THEN it SHALL use on-demand billing mode by default
5. WHEN S3 lifecycle policies are configured THEN they SHALL archive old artifacts to cheaper storage tiers
6. WHEN CloudWatch metrics are available THEN they SHALL include cost per generation and monthly cost projections

### Requirement 15: Testing and Validation

**User Story:** As a QA engineer, I want comprehensive testing capabilities for the system, so that I can verify functionality before and after deployment.

#### Acceptance Criteria

1. WHEN the system provides test utilities THEN it SHALL include scripts to invoke the supervisor agent
2. WHEN testing locally THEN it SHALL support SAM Local for Lambda function testing
3. WHEN testing agents THEN it SHALL provide example test events for each action
4. WHEN integration testing THEN it SHALL verify end-to-end flow from user request to deployed agent
5. WHEN testing completes THEN it SHALL verify that all artifacts are saved to DynamoDB and S3
6. WHEN testing completes THEN it SHALL verify that the deployed agent responds correctly to test inputs

### Requirement 16: Documentation and Examples

**User Story:** As a new user, I want comprehensive documentation and examples, so that I can understand and use the system effectively.

#### Acceptance Criteria

1. WHEN documentation is provided THEN it SHALL include architecture diagrams showing agent interactions
2. WHEN documentation is provided THEN it SHALL include deployment guides for CloudFormation, Terraform, and CDK
3. WHEN documentation is provided THEN it SHALL include API reference for all Lambda actions
4. WHEN documentation is provided THEN it SHALL include troubleshooting guides for common issues
5. WHEN examples are provided THEN they SHALL include scripts to invoke the supervisor agent
6. WHEN examples are provided THEN they SHALL include scripts to query DynamoDB and S3 for results
7. WHEN examples are provided THEN they SHALL include CloudWatch Insights queries for monitoring

### Requirement 17: Task Completion and Quality Gates

**User Story:** As a project manager, I want clear criteria for task completion with quality gates, so that I know when a task block is truly complete and ready for production.

#### Acceptance Criteria

1. WHEN a task is marked as complete THEN it SHALL have passed all associated tests with NO failures
2. WHEN a task is marked as complete THEN it SHALL have NO errors in the code
3. WHEN a task is marked as complete THEN it SHALL have NO warnings in the code
4. WHEN a task block contains multiple tasks THEN the block SHALL be complete if and only if ALL tasks have passed testing with no errors or warnings
5. WHEN testing is performed THEN it SHALL include unit tests for individual functions
6. WHEN testing is performed THEN it SHALL include integration tests for component interactions
7. WHEN testing is performed THEN it SHALL include validation of CloudFormation templates
8. WHEN code is validated THEN it SHALL use linters and static analysis tools to detect errors and warnings
9. WHEN a task fails quality gates THEN it SHALL NOT be marked as complete until all issues are resolved

### Requirement 19: Implementation Consistency and Pattern Adherence

**User Story:** As a developer implementing Lambda functions, I want a clear reference implementation and explicit pattern to follow, so that all agents have consistent structure and behavior without recurring mistakes.

#### Acceptance Criteria

1. WHEN implementing a new Lambda function THEN it SHALL use the Requirements Analyst handler as the canonical reference implementation
2. WHEN the spec says "copy EXACT structure" THEN it SHALL mean: copy the control flow pattern (event parsing → routing → action handlers → error handling), NOT the business logic
3. WHEN implementing action handlers THEN they SHALL follow the 3-phase pattern: (1) log input, (2) execute business logic, (3) log output and save artifacts
4. WHEN calling log_inference_input() THEN it SHALL create a new DynamoDB record and return a timestamp
5. WHEN calling log_inference_output() THEN it SHALL UPDATE the existing record (not create a new one) using the timestamp from log_inference_input()
6. WHEN extracting parameters from Bedrock Agent events THEN it SHALL use the exact same parsing logic as Requirements Analyst
7. WHEN returning responses THEN it SHALL use the exact same response format as Requirements Analyst
8. WHEN handling errors THEN it SHALL use the exact same error handling pattern as Requirements Analyst
9. WHEN writing tests THEN it SHALL follow the same test structure as Requirements Analyst tests
10. WHEN verifying DynamoDB logging THEN it SHALL expect 1 record per action (not 2), with both prompt and response fields populated

### Requirement 18: Project Structure and File Organization

**User Story:** As a developer, I want all files organized in their appropriate directories, so that the project structure is clean and maintainable.

#### Acceptance Criteria

1. WHEN files are created THEN they SHALL be placed in the appropriate directory based on their purpose
2. WHEN Lambda function code is created THEN it SHALL be placed in lambda/{agent-name}/ directory
3. WHEN CloudFormation templates are created THEN they SHALL be placed in infrastructure/cloudformation/ directory
4. WHEN Terraform modules are created THEN they SHALL be placed in infrastructure/terraform/ directory
5. WHEN OpenAPI schemas are created THEN they SHALL be placed in schemas/ directory
6. WHEN shared libraries are created THEN they SHALL be placed in shared/ directory with appropriate subdirectories
7. WHEN test files are created THEN they SHALL be placed in tests/ directory with subdirectories for unit/integration/e2e
8. WHEN documentation is created THEN it SHALL be placed in docs/ directory
9. WHEN example scripts are created THEN they SHALL be placed in examples/ directory
10. WHEN files are in the root directory THEN they SHALL only be project-level files (README.md, pyproject.toml, LICENSE, .gitignore)
11. WHEN the project structure is reviewed THEN there SHALL be NO files in the root directory that belong in subdirectories
