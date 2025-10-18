# Design Document

## Overview

AutoNinja is a production-grade, serverless multi-agent system that transforms natural language requests into fully deployed AI agents. The system uses **Amazon Bedrock AgentCore Runtime** for the supervisor agent and **AWS Bedrock Agents** for 5 specialized collaborator agents in a supervisor-collaborator pattern.

**Reference:** 
- [Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- [Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)

### System Goals

1. **Automated Agent Generation**: Convert natural language descriptions into production-ready AWS Bedrock Agents
2. **Complete Audit Trail**: Persist every prompt, inference, and artifact with no exceptions
3. **AWS-Native Architecture**: Use only AWS managed services for zero infrastructure management
4. **Production Quality**: Generate secure, tested, and deployable agents with proper IAM policies
5. **Cost Efficiency**: Optimize for pay-per-use serverless pricing model
6. **Extended Execution Time**: Leverage AgentCore Runtime for up to 8-hour workflows
7. **Framework Flexibility**: Use AgentCore SDK for supervisor orchestration logic

### Key Design Principles

- **Persistence First**: All raw prompts and responses logged to DynamoDB before processing
- **Separation of Concerns**: Each agent has a single, well-defined responsibility
- **Idempotency**: All operations can be safely retried with job_name tracking
- **Least Privilege**: Every component has minimal IAM permissions required
- **Observability**: Comprehensive logging, tracing, and metrics at every layer
- **Hybrid Architecture**: AgentCore Runtime supervisor + Bedrock Agent collaborators
- **Sequential Orchestration**: Logical workflow (Requirements → Code → Architecture → Validation → Deployment)

## Architecture

### High-Level Architecture


```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Request                               │
│              "I would like a friend agent"                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Supervisor Agent (AgentCore Runtime)                    │
│  - Deployed to Amazon Bedrock AgentCore Runtime                     │
│  - Generates job_name: job-friend-20251013-143022                   │
│  - Implements sequential orchestration logic                        │
│  - Invokes collaborator Bedrock Agents via InvokeAgent API          │
│  - Passes job_name to ALL collaborators                             │
│  - Aggregates results and returns final agent ARN                   │
│  - Extended execution time (up to 8 hours)                          │
│  - Isolated microVM session per invocation                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │ 1. Requirements     │
                   │    Analyst Agent    │
                   │                     │
                   │ Generates reqs for  │
                   │ ALL sub-agents      │
                   └──────────┬──────────┘
                              │
                              │ Requirements distributed by Supervisor
                              │
                              ▼
                   ┌─────────────────────┐
                   │ 2. Code Generator   │
                   │    Agent            │
                   │                     │
                   │ - System prompts    │
                   │ - Agent config      │
                   │ - Lambda code       │
                   │ - OpenAPI schemas   │
                   └──────────┬──────────┘
                              │
                              │ Code files + Requirements
                              │
                              ▼
                   ┌─────────────────────┐
                   │ 3. Solution         │
                   │    Architect Agent  │
                   │                     │
                   │ - References code   │
                   │ - Designs arch      │
                   │ - Generates IaC     │
                   └──────────┬──────────┘
                              │
                              │ Requirements + Code + Architecture
                              │
                              ▼
                   ┌─────────────────────┐
                   │ 4. Quality          │
                   │    Validator Agent  │
                   │                     │
                   │ - Validates all     │
                   │ - Low threshold     │
                   │ GATE: Pass?         │
                   └──────────┬──────────┘
                              │
                              │ Green light (if pass)
                              │
                              ▼
                   ┌─────────────────────┐
                   │ 5. Deployment       │
                   │    Manager Agent    │
                   │                     │
                   │ - Gen CFN template  │
                   │ - Deploy stack      │
                   │ - Config agent      │
                   │ - Test deployment   │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │  Generated Agent    │
                   │  ARN + Endpoints    │
                   └─────────────────────┘

═══════════════════════════════════════════════════════════════════════
         PERSISTENCE & OBSERVABILITY (Run in Parallel)
═══════════════════════════════════════════════════════════════════════

Every Lambda function IMMEDIATELY logs to both layers:

┌─────────────────────────────────────────────────────────────────────┐
│                      Persistence Layer                               │
│                    (Runs with every Lambda)                          │
│                                                                      │
│  ┌──────────────────────┐         ┌──────────────────────┐         │
│  │  DynamoDB Table      │         │  S3 Bucket           │         │
│  │  inference-records   │         │  autoninja-artifacts │         │
│  │                      │         │                      │         │
│  │  1. Log raw input    │         │  1. Save raw resp    │         │
│  │  2. Log raw output   │         │  2. Save converted   │         │
│  │  3. Save metadata    │         │  3. Save artifacts   │         │
│  └──────────────────────┘         └──────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    Observability Layer                               │
│                    (Runs with every Lambda)                          │
│                                                                      │
│  CloudWatch Logs          X-Ray Tracing          CloudWatch Metrics │
│  - Structured logs        - Request traces       - Cost per job     │
│  - Per-job streams        - Service maps         - Duration         │
│  - Error tracking         - Latency analysis     - Token usage      │
└─────────────────────────────────────────────────────────────────────┘
```

### Workflow Sequence


1. **User Invokes Supervisor**: User sends request to supervisor agent via `InvokeAgent` API

2. **Job Generation**: Supervisor generates unique `job_name` (e.g., `job-friend-20251013-143022`)

3. **Requirements Phase**: Supervisor delegates to Requirements Analyst agent
   - Lambda receives request → **IMMEDIATELY logs raw input to DynamoDB**
   - Lambda extracts requirements for ALL sub-agents from user request
   - Lambda generates comprehensive requirements document
   - Lambda generates response → **IMMEDIATELY logs raw response to DynamoDB**
   - Lambda saves requirements JSON to S3
   - **Supervisor receives requirements and distributes to all downstream agents**
   - **Persistence and observability run in parallel with agent execution**

4. **Code Generation Phase**: Supervisor delegates to Code Generator agent with requirements
   - Lambda receives requirements → **IMMEDIATELY logs raw input to DynamoDB**
   - Lambda generates system prompts for the new agent
   - Lambda generates Bedrock Agent configuration JSON
   - Lambda generates Lambda function code with error handling
   - Lambda generates OpenAPI schemas for action groups
   - Lambda generates response → **IMMEDIATELY logs raw response to DynamoDB**
   - Lambda saves all generated code files to S3
   - **Persistence and observability run in parallel with agent execution**

5. **Architecture Phase**: Supervisor delegates to Solution Architect agent with requirements and code references
   - Lambda receives requirements + code file references → **IMMEDIATELY logs raw input to DynamoDB**
   - Lambda designs AWS architecture based on requirements
   - Lambda references code files generated by Code Generator
   - Lambda generates infrastructure-as-code (CloudFormation/Terraform)
   - Lambda generates response → **IMMEDIATELY logs raw response to DynamoDB**
   - Lambda saves architecture design and IaC templates to S3
   - **Persistence and observability run in parallel with agent execution**

6. **Validation Phase**: Supervisor delegates to Quality Validator agent with all artifacts
   - Lambda receives requirements + code + architecture → **IMMEDIATELY logs raw input to DynamoDB**
   - Lambda validates code quality, security, compliance
   - Lambda checks system prompts are clear and complete
   - Lambda validates IAM policies follow least-privilege
   - Lambda validates CloudFormation template syntax
   - Lambda generates response → **IMMEDIATELY logs raw response to DynamoDB**
   - Lambda saves validation report to S3
   - **Quality gates must pass before proceeding to deployment**
   - **Threshold set extremely low (e.g., 50% pass rate) for testing purposes**
   - **Persistence and observability run in parallel with agent execution**

7. **Deployment Phase**: Supervisor delegates to Deployment Manager agent **ONLY IF validation passes**
   - Lambda receives requirements + code + architecture + validation green light → **IMMEDIATELY logs raw input to DynamoDB**
   - Lambda generates complete CloudFormation template for the generated agent
   - Lambda deploys CloudFormation stack to AWS
   - Lambda configures Bedrock Agent with action groups
   - Lambda creates agent alias
   - Lambda tests the deployed agent with sample inputs
   - Lambda generates response → **IMMEDIATELY logs raw response to DynamoDB**
   - Lambda saves deployment results and agent ARN to S3
   - **Persistence and observability run in parallel with agent execution**

8. **Response**: Supervisor consolidates all results and returns deployed agent ARN to user

**Key Design Principles**:
- **Supervisor oversees all**: Coordinates the entire pipeline and distributes requirements
- **Requirements first**: Requirements Analyst generates requirements for ALL sub-agents
- **Code before architecture**: Code Generator creates all code/configs before Solution Architect designs IaC
- **Architecture references code**: Solution Architect references code files when generating IaC
- **Validation gates deployment**: Quality Validator must approve before Deployment Manager proceeds
- **Persistence is immediate**: Raw data saved BEFORE processing to prevent data loss
- **Observability is parallel**: Logging and tracing happen alongside execution
- **Fault tolerance**: If pipeline fails, saved data allows resuming from checkpoint

### Multi-Agent Collaboration Configuration

**Supervisor Agent**:
- `agentCollaboration`: `SUPERVISOR` (coordinates responses from all collaborators)
- Associates with 5 collaborator agents
- Receives all collaborator responses and consolidates final output
- Shares conversation history with collaborators (optional per collaborator)

**Collaborator Agents**:
- Each has dedicated Lambda function for action group
- Each has OpenAPI schema defining available actions
- Each has specific instructions describing role and responsibilities
- Each can access action groups, knowledge bases, and guardrails independently

## Components and Interfaces

### 1. Supervisor Agent (AgentCore Runtime)

**Purpose**: Orchestrate the complete workflow from user request to deployed agent using Amazon Bedrock AgentCore Runtime

**Reference:**
- [AgentCore Runtime Overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- [Get Started with AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-toolkit.html)
- [Invoke AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html)

**Implementation**:
- **Framework**: Amazon Bedrock AgentCore Python SDK (`bedrock-agentcore`)
- **Deployment**: Containerized via AgentCore starter toolkit
- **Runtime**: Isolated microVM sessions in AgentCore Runtime
- **Execution Time**: Up to 8 hours per session
- **Foundation Model**: `anthropic.claude-sonnet-4-5-20250929-v1:0` (via boto3)
- **Orchestration Type**: Sequential logical workflow (not intelligent routing)

**Code Structure**:
```python
from bedrock_agentcore import BedrockAgentCoreApp
import boto3
import json
from datetime import datetime

app = BedrockAgentCoreApp()
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

@app.entrypoint
def invoke(payload):
    """
    Supervisor agent entrypoint for orchestrating collaborator agents.
    
    Args:
        payload: Dict with 'prompt' key containing user request
        
    Returns:
        Dict with final deployed agent ARN and results
    """
    user_request = payload.get("prompt", "")
    
    # Generate unique job_name
    job_name = generate_job_name(user_request)
    
    # Sequential orchestration
    results = {}
    
    # 1. Requirements Analyst
    requirements = invoke_collaborator(
        agent_id="requirements-analyst-id",
        alias_id="requirements-analyst-alias",
        session_id=job_name,
        input_text=f"job_name: {job_name}\nrequest: {user_request}"
    )
    results['requirements'] = requirements
    
    # 2. Code Generator
    code = invoke_collaborator(
        agent_id="code-generator-id",
        alias_id="code-generator-alias",
        session_id=job_name,
        input_text=f"job_name: {job_name}\nrequirements: {json.dumps(requirements)}"
    )
    results['code'] = code
    
    # 3. Solution Architect
    architecture = invoke_collaborator(
        agent_id="solution-architect-id",
        alias_id="solution-architect-alias",
        session_id=job_name,
        input_text=f"job_name: {job_name}\nrequirements: {json.dumps(requirements)}\ncode: {json.dumps(code)}"
    )
    results['architecture'] = architecture
    
    # 4. Quality Validator
    validation = invoke_collaborator(
        agent_id="quality-validator-id",
        alias_id="quality-validator-alias",
        session_id=job_name,
        input_text=f"job_name: {job_name}\ncode: {json.dumps(code)}\narchitecture: {json.dumps(architecture)}"
    )
    results['validation'] = validation
    
    # 5. Deployment Manager (only if validation passes)
    if validation.get('is_valid', False):
        deployment = invoke_collaborator(
            agent_id="deployment-manager-id",
            alias_id="deployment-manager-alias",
            session_id=job_name,
            input_text=f"job_name: {job_name}\nall_artifacts: {json.dumps(results)}"
        )
        results['deployment'] = deployment
        
        return {
            "job_name": job_name,
            "agent_arn": deployment.get('agent_arn'),
            "status": "deployed",
            "results": results
        }
    else:
        return {
            "job_name": job_name,
            "status": "validation_failed",
            "validation_issues": validation.get('issues', []),
            "results": results
        }

def generate_job_name(user_request: str) -> str:
    """Generate unique job_name from user request"""
    # Extract keyword from request
    keyword = extract_keyword(user_request)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"job-{keyword}-{timestamp}"

def invoke_collaborator(agent_id: str, alias_id: str, session_id: str, input_text: str) -> dict:
    """Invoke a collaborator Bedrock Agent via InvokeAgent API"""
    response = bedrock_agent_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        inputText=input_text,
        enableTrace=True
    )
    
    # Parse streaming response
    result = ""
    for event in response.get('completion', []):
        if 'chunk' in event:
            result += event['chunk']['bytes'].decode('utf-8')
    
    return json.loads(result)
```

**Deployment**:
```bash
# Configure
agentcore configure -e supervisor_agent.py -r us-east-2

# Deploy to AgentCore Runtime
agentcore launch

# Test
agentcore invoke '{"prompt": "I would like a friend agent"}'
```

**IAM Permissions**:
- `bedrock-agent:InvokeAgent` - Invoke collaborator agents
- `bedrock-agent-runtime:InvokeAgent` - Invoke collaborator agents
- `dynamodb:PutItem`, `dynamodb:UpdateItem` - Logging
- `s3:PutObject`, `s3:GetObject` - Artifacts
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` - CloudWatch

**Collaborators** (invoked sequentially):
1. requirements-analyst (Bedrock Agent)
2. code-generator (Bedrock Agent)
3. solution-architect (Bedrock Agent)
4. quality-validator (Bedrock Agent)
5. deployment-manager (Bedrock Agent)

### 2. Requirements Analyst Agent

**Purpose**: Extract and validate requirements from natural language user requests

**Configuration**:
- **Foundation Model**: `anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Action Group**: `requirements-analyst-actions`
- **Lambda Function**: `requirements-analyst-lambda`
- **OpenAPI Schema**: `schemas/requirements-analyst-schema.yaml`

**Instructions**:
```
You are a requirements analyst for the AutoNinja system. Your role is to extract structured
requirements from user requests for AI agents. You generate requirements for ALL sub-agents
in the pipeline (Code Generator, Solution Architect, Quality Validator, Deployment Manager).

When you receive a request:
1. Extract the job_name parameter from the request
2. Analyze the user's description to identify:
   - Agent purpose and goals
   - Required capabilities and features
   - User interactions and workflows
   - Data requirements
   - Integration needs
   - System prompts requirements
   - Lambda function requirements
   - Architecture requirements
   - Deployment requirements
3. Generate comprehensive requirements document that covers:
   - What the Code Generator needs to build
   - What the Solution Architect needs to design
   - What the Quality Validator needs to check
   - What the Deployment Manager needs to deploy
4. Assess complexity (simple/moderate/complex)
5. Validate completeness of requirements
6. Return structured requirements in JSON format

The supervisor will distribute your requirements to all downstream agents.
Always use the job_name provided by the supervisor for tracking.
```

**Lambda Actions**:

1. **extract_requirements**
   - Input: `job_name` (string), `user_request` (string)
   - Output: `requirements` (object), `status` (string)
   - Logic: Parse user request, extract structured requirements, save to DynamoDB/S3

2. **analyze_complexity**
   - Input: `job_name` (string), `requirements` (object)
   - Output: `complexity_score` (string), `assessment` (object)
   - Logic: Analyze requirements complexity, estimate effort, save to DynamoDB/S3

3. **validate_requirements**
   - Input: `job_name` (string), `requirements` (object)
   - Output: `is_valid` (boolean), `missing_items` (array)
   - Logic: Check completeness, identify gaps, save to DynamoDB/S3

### 3. Solution Architect Agent

**Purpose**: Design AWS architecture for the requested agent

**Configuration**:
- **Foundation Model**: `anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Action Group**: `solution-architect-actions`
- **Lambda Function**: `solution-architect-lambda`
- **OpenAPI Schema**: `schemas/solution-architect-schema.yaml`

**Instructions**:
```
You are a solution architect for the AutoNinja system. Your role is to design AWS
architectures for AI agents based on requirements and code files generated by the Code Generator.

When you receive requirements and code file references:
1. Extract the job_name parameter from the request
2. Review the code files generated by the Code Generator:
   - Lambda function code
   - Agent configuration
   - OpenAPI schemas
   - System prompts
3. Design a complete AWS architecture including:
   - Bedrock Agent configuration
   - Lambda functions (reference existing code)
   - Data storage (DynamoDB, S3) if needed
   - IAM roles and policies
   - Integration points
4. Select appropriate AWS services
5. Generate infrastructure-as-code templates (CloudFormation/Terraform) that:
   - Reference the Lambda code files
   - Include the agent configuration
   - Set up proper IAM permissions
   - Configure action groups with OpenAPI schemas
6. Follow AWS best practices and Well-Architected Framework

Always reference the code files from the Code Generator when designing IaC.
Always use the job_name provided by the supervisor for tracking.
```

**Lambda Actions**:

1. **design_architecture**
   - Input: `job_name` (string), `requirements` (object)
   - Output: `architecture` (object), `diagram` (string)
   - Logic: Design complete architecture, save to DynamoDB/S3

2. **select_services**
   - Input: `job_name` (string), `requirements` (object)
   - Output: `services` (array), `rationale` (object)
   - Logic: Select AWS services, justify choices, save to DynamoDB/S3

3. **generate_iac**
   - Input: `job_name` (string), `architecture` (object)
   - Output: `cloudformation_template` (string), `terraform_module` (string)
   - Logic: Generate IaC templates, save to DynamoDB/S3

### 4. Code Generator Agent

**Purpose**: Generate production-ready Lambda functions and Bedrock Agent configurations

**Configuration**:
- **Foundation Model**: `anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Action Group**: `code-generator-actions`
- **Lambda Function**: `code-generator-lambda`
- **OpenAPI Schema**: `schemas/code-generator-schema.yaml`

**Instructions**:

```
You are a code generator for the AutoNinja system. Your role is to generate production-ready
code for AI agents based on architecture designs.

When you receive an architecture design:
1. Extract the job_name parameter from the request
2. Generate Lambda function code in Python with:
   - Proper error handling
   - Input validation
   - Structured logging
   - DynamoDB/S3 persistence
3. Generate Bedrock Agent configuration JSON
4. Generate OpenAPI schemas for action groups
5. Follow Python best practices and AWS Lambda patterns

Always use the job_name provided by the supervisor for tracking.
```

**Lambda Actions**:

1. **generate_lambda_code**
   - Input: `job_name` (string), `architecture` (object), `function_spec` (object)
   - Output: `lambda_code` (string), `requirements_txt` (string)
   - Logic: Generate Python Lambda code, save to DynamoDB/S3

2. **generate_agent_config**
   - Input: `job_name` (string), `architecture` (object)
   - Output: `agent_config` (object)
   - Logic: Generate Bedrock Agent configuration, save to DynamoDB/S3

3. **generate_openapi_schema**
   - Input: `job_name` (string), `action_group_spec` (object)
   - Output: `openapi_schema` (string)
   - Logic: Generate OpenAPI 3.0 schema, save to DynamoDB/S3

### 5. Quality Validator Agent

**Purpose**: Validate generated code for quality, security, and compliance

**Configuration**:
- **Foundation Model**: `anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Action Group**: `quality-validator-actions`
- **Lambda Function**: `quality-validator-lambda`
- **OpenAPI Schema**: `schemas/quality-validator-schema.yaml`

**Instructions**:
```
You are a quality validator for the AutoNinja system. Your role is to validate generated
code for quality, security, and compliance before deployment.

When you receive generated code:
1. Extract the job_name parameter from the request
2. Perform code quality validation:
   - Check for syntax errors
   - Verify error handling
   - Validate logging practices
   - Check code structure
3. Perform security scanning:
   - Check for hardcoded credentials
   - Validate IAM permissions
   - Check for injection vulnerabilities
   - Verify encryption usage
4. Perform compliance checks:
   - AWS best practices
   - Lambda best practices
   - Python PEP 8 standards
5. Generate quality report with findings and recommendations

Always use the job_name provided by the supervisor for tracking.
```

**Lambda Actions**:

1. **validate_code**
   - Input: `job_name` (string), `code` (string), `language` (string)
   - Output: `is_valid` (boolean), `issues` (array), `quality_score` (number)
   - Logic: Validate code quality, save to DynamoDB/S3

2. **security_scan**
   - Input: `job_name` (string), `code` (string), `iam_policies` (object)
   - Output: `vulnerabilities` (array), `risk_level` (string)
   - Logic: Scan for security issues, save to DynamoDB/S3

3. **compliance_check**
   - Input: `job_name` (string), `code` (string), `architecture` (object)
   - Output: `compliant` (boolean), `violations` (array)
   - Logic: Check compliance with standards, save to DynamoDB/S3

### 6. Deployment Manager Agent

**Purpose**: Deploy generated agents to AWS and verify successful deployment

**Configuration**:
- **Foundation Model**: `anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Action Group**: `deployment-manager-actions`
- **Lambda Function**: `deployment-manager-lambda`
- **OpenAPI Schema**: `schemas/deployment-manager-schema.yaml`

**Instructions**:
```
You are a deployment manager for the AutoNinja system. Your role is to deploy validated
agents to AWS and verify successful deployment.

When you receive requirements, code, architecture, and validation green light:
1. Extract the job_name parameter from the request
2. Gather all artifacts:
   - Requirements from Requirements Analyst
   - Code files from Code Generator (Lambda code, agent config, OpenAPI schemas, system prompts)
   - IaC templates from Solution Architect
   - Validation report from Quality Validator (must be green light)
3. Generate complete CloudFormation template that includes:
   - All Lambda functions with code
   - Bedrock Agent with configuration
   - Action groups with OpenAPI schemas
   - IAM roles and policies
   - All resources from architecture design
4. Deploy CloudFormation stack to AWS
5. Configure Bedrock Agent with action groups and aliases
6. Test the deployed agent with sample inputs to verify functionality
7. Return the deployed agent ARN, alias ID, and endpoints

You can ONLY proceed if the Quality Validator gives a green light.
Always use the job_name provided by the supervisor for tracking.
```

**Lambda Actions**:

1. **generate_cloudformation**
   - Input: `job_name` (string), `code` (object), `architecture` (object)
   - Output: `cloudformation_template` (string)
   - Logic: Generate complete CFN template, save to DynamoDB/S3

2. **deploy_stack**
   - Input: `job_name` (string), `cloudformation_template` (string), `stack_name` (string)
   - Output: `stack_id` (string), `status` (string), `outputs` (object)
   - Logic: Deploy CFN stack, wait for completion, save to DynamoDB/S3

3. **configure_agent**
   - Input: `job_name` (string), `agent_config` (object), `lambda_arns` (object)
   - Output: `agent_id` (string), `agent_arn` (string), `alias_id` (string)
   - Logic: Create Bedrock Agent, configure action groups, create alias, save to DynamoDB/S3

4. **test_deployment**
   - Input: `job_name` (string), `agent_id` (string), `alias_id` (string)
   - Output: `test_results` (object), `is_successful` (boolean)
   - Logic: Test deployed agent, verify responses, save to DynamoDB/S3

## Data Models

### DynamoDB Schema

**Table Name**: `autoninja-inference-records`

**Keys**:
- Partition Key: `job_name` (String) - e.g., "job-friend-20251013-143022"
- Sort Key: `timestamp` (String) - ISO 8601 format

**Attributes**:

```python
{
    "job_name": "job-friend-20251013-143022",  # Partition key
    "timestamp": "2025-10-13T14:30:22.123Z",   # Sort key
    "session_id": "abc-123-def-456",
    "agent_name": "requirements-analyst",
    "action_name": "extract_requirements",
    "inference_id": "unique-inference-id",
    "prompt": "Full raw prompt sent to Bedrock or Lambda",
    "response": "Full raw response from Bedrock or Lambda",
    "model_id": "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "tokens_used": 4532,
    "cost_estimate": 0.0226,
    "duration_seconds": 3.24,
    "artifacts_s3_uri": "s3://autoninja-artifacts/job-friend-20251013-143022/requirements/",
    "status": "success",  # success | error
    "error_message": null  # populated if status is error
}
```

**Indexes**:
- GSI on `session_id` for querying all inferences in a session
- GSI on `agent_name` + `timestamp` for agent-specific queries

### S3 Structure

**Bucket Name**: `autoninja-artifacts-{account-id}`

**Directory Structure**:
```
s3://autoninja-artifacts-{account-id}/
└── {job_name}/                           # e.g., job-friend-20251013-143022/
    ├── requirements/
    │   ├── raw_response.json             # Raw response from agent
    │   ├── requirements.json             # Converted/extracted requirements
    │   └── complexity_assessment.json
    ├── architecture/
    │   ├── raw_response.json
    │   ├── architecture_design.json
    │   ├── service_selection.json
    │   └── infrastructure_template.yaml
    ├── code/
    │   ├── raw_response.json
    │   ├── lambda_handler.py
    │   ├── requirements.txt
    │   ├── agent_config.json
    │   └── openapi_schema.yaml
    ├── validation/
    │   ├── raw_response.json
    │   ├── quality_report.json
    │   └── security_findings.json
    └── deployment/
        ├── raw_response.json
        ├── cloudformation_template.yaml
        ├── deployment_results.json
        └── agent_arn.txt
```

### Lambda Event/Response Models

**Lambda Input Event** (from Bedrock Agent):
```python
{
    "messageVersion": "1.0",
    "agent": {
        "name": "requirements-analyst",
        "id": "AGENT123",
        "alias": "PROD",
        "version": "1"
    },
    "inputText": "User's original request",
    "sessionId": "session-123",
    "actionGroup": "requirements-analyst-actions",
    "apiPath": "/extract-requirements",
    "httpMethod": "POST",
    "parameters": [
        {"name": "job_name", "type": "string", "value": "job-friend-20251013-143022"},
        {"name": "user_request", "type": "string", "value": "I would like a friend agent"}
    ],
    "requestBody": {
        "content": {
            "application/json": {
                "properties": [
                    {"name": "job_name", "type": "string", "value": "job-friend-20251013-143022"},
                    {"name": "user_request", "type": "string", "value": "I would like a friend agent"}
                ]
            }
        }
    }
}
```

**Lambda Response Event** (to Bedrock Agent):
```python
{
    "messageVersion": "1.0",
    "response": {
        "actionGroup": "requirements-analyst-actions",
        "apiPath": "/extract-requirements",
        "httpMethod": "POST",
        "httpStatusCode": 200,
        "responseBody": {
            "application/json": {
                "body": json.dumps({
                    "job_name": "job-friend-20251013-143022",
                    "requirements": {...},
                    "status": "success"
                })
            }
        }
    }
}
```

### Shared Library Models

**InferenceRecord** (Python dataclass):
```python
@dataclass
class InferenceRecord:
    job_name: str
    timestamp: str
    session_id: str
    agent_name: str
    action_name: str
    inference_id: str
    prompt: str  # Raw prompt
    response: str  # Raw response
    model_id: str
    tokens_used: int
    cost_estimate: float
    duration_seconds: float
    artifacts_s3_uri: str
    status: str  # "success" | "error"
    error_message: Optional[str] = None
```

## Error Handling

### Lambda Function Error Handling

All Lambda functions follow this error handling pattern:

```python
def lambda_handler(event, context):
    job_name = None
    start_time = time.time()
    
    try:
        # Extract job_name from event
        job_name = extract_job_name(event)
        
        # Log raw input to DynamoDB
        log_inference_input(job_name, event)
        
        # Execute business logic
        result = execute_business_logic(event)
        
        # Log raw output to DynamoDB
        duration = time.time() - start_time
        log_inference_output(job_name, result, duration)
        
        # Save artifacts to S3
        save_artifacts_to_s3(job_name, result)
        
        # Return response
        return format_response(result)
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        log_error_to_dynamodb(job_name, str(e))
        return format_error_response(400, str(e))
        
    except AWSError as e:
        logger.error(f"AWS error: {e}")
        log_error_to_dynamodb(job_name, str(e))
        return format_error_response(500, "AWS service error")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        log_error_to_dynamodb(job_name, str(e))
        return format_error_response(500, "Internal server error")
```

### Bedrock Agent Error Handling

Bedrock Agents have built-in retry logic:
- Automatic retry with exponential backoff for transient errors
- Maximum 3 retries per action
- Errors are logged to CloudWatch automatically

### CloudFormation Deployment Error Handling

Deployment Manager handles CloudFormation errors:
- Stack creation failures trigger automatic rollback
- Detailed error messages saved to DynamoDB and S3
- Failed deployments do not block the system
- Users receive clear error messages with troubleshooting steps

## Testing Strategy

### Unit Testing

**Lambda Functions**:
- Test each action handler independently
- Mock DynamoDB and S3 clients
- Verify correct persistence of raw prompts/responses
- Test error handling paths
- Verify response format matches OpenAPI schema

**Shared Libraries**:
- Test DynamoDB client operations
- Test S3 client operations
- Test job_name generation
- Test data model serialization/deserialization

**Test Framework**: pytest with moto for AWS mocking

### Integration Testing

**Agent-to-Lambda Integration**:
- Deploy agents and Lambda functions to test environment
- Invoke agents with test requests
- Verify Lambda functions receive correct event format
- Verify responses match expected format
- Check DynamoDB and S3 for persisted data

**Multi-Agent Collaboration**:
- Test supervisor delegation to collaborators
- Verify conversation history sharing
- Test parallel execution where applicable
- Verify consolidated responses

### End-to-End Testing

**Complete Workflow**:
- Invoke supervisor with sample user request
- Verify all 5 collaborators are invoked in sequence
- Check DynamoDB for all inference records
- Check S3 for all artifacts
- Verify deployed agent is functional
- Test deployed agent with sample inputs

**Test Cases**:
1. Simple agent (e.g., "friend agent")
2. Complex agent with multiple capabilities
3. Agent with knowledge base requirements
4. Agent with external API integrations

### Validation Testing

**CloudFormation Templates**:
- Use `cfn-lint` to validate template syntax
- Use `cfn_nag` to check security best practices
- Test template deployment in isolated account

**Python Code**:
- Use `pylint` for code quality
- Use `bandit` for security scanning
- Use `mypy` for type checking
- Use `black` for code formatting

**OpenAPI Schemas**:
- Validate against OpenAPI 3.0 specification
- Test schema with Bedrock Agent console
- Verify all required fields are present

### Critical OpenAPI Schema Constraints for Bedrock Agents

**IMPORTANT**: AWS Bedrock Agents have specific limitations on OpenAPI schema format that differ from standard OpenAPI 3.0 specifications. Violating these constraints will cause deployment failures.

#### ✅ Required Format
- **OpenAPI version**: Must be exactly `"3.0.0"` (string)
- **operationId**: Required for all operations (use camelCase, alphanumeric with hyphens/underscores only)
- **Inline schemas**: All schemas must be defined inline in CloudFormation `Payload` field
- **Simple types**: Use basic types (string, number, integer, boolean, object, array)

#### ❌ Unsupported Features
- **`additionalProperties`**: Not supported - use explicit properties or JSON strings instead
- **`$ref` references**: Not supported - inline all schemas, no components section
- **`enum` arrays**: Not supported - use string type with description instead
- **S3 schema references**: CloudFormation `ApiSchema.S3` doesn't work reliably - use `ApiSchema.Payload` with inline YAML
- **Complex nested objects**: Flatten to JSON strings when needed
- **`allOf`, `oneOf`, `anyOf`**: Not supported - use simple object schemas

#### 🔧 Workarounds

**For dynamic objects (maps/dictionaries)**:
```yaml
# ❌ DON'T USE
properties:
  data:
    type: object
    additionalProperties:
      type: string

# ✅ USE INSTEAD
properties:
  data:
    type: string
    description: JSON string containing key-value pairs
```

**For enums**:
```yaml
# ❌ DON'T USE
properties:
  status:
    type: string
    enum: [success, error, pending]

# ✅ USE INSTEAD
properties:
  status:
    type: string
    description: Status of operation (success, error, or pending)
```

**For error responses**:
```yaml
# ❌ DON'T USE
responses:
  '400':
    description: Bad request
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/Error'

# ✅ USE INSTEAD
responses:
  '400':
    description: Bad request
```

**For CloudFormation deployment**:
```yaml
# ❌ DON'T USE
ActionGroups:
  - ActionGroupName: my-actions
    ApiSchema:
      S3:
        S3BucketName: !Ref MyBucket
        S3ObjectKey: schemas/my-schema.yaml

# ✅ USE INSTEAD
ActionGroups:
  - ActionGroupName: my-actions
    ApiSchema:
      Payload: |
        openapi: 3.0.0
        info:
          title: My API
          version: 1.0.0
        paths:
          /my-action:
            post:
              operationId: myAction
              # ... rest of schema inline
```

#### 📝 Minimal Working Example
```yaml
openapi: 3.0.0
info:
  title: Example API
  version: 1.0.0
paths:
  /process:
    post:
      summary: Process data
      description: Processes input data and returns result
      operationId: processData
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_name
                - input
              properties:
                job_name:
                  type: string
                  description: Unique job identifier
                input:
                  type: string
                  description: Input data as JSON string
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_name:
                    type: string
                  result:
                    type: string
                  status:
                    type: string
        '400':
          description: Invalid request
        '500':
          description: Internal error
```

#### 🧪 Testing Schemas
1. Validate with standard OpenAPI validator first
2. Test inline in CloudFormation with minimal schema
3. Use AWS CLI to create action group directly for faster iteration:
   ```bash
   aws bedrock-agent create-agent-action-group \
     --agent-id <AGENT_ID> \
     --agent-version DRAFT \
     --action-group-name test-actions \
     --action-group-executor lambda=<LAMBDA_ARN> \
     --api-schema payload="$(cat schema.yaml)" \
     --region us-east-2
   ```
4. Check CloudWatch Logs for detailed error messages

#### 📚 References
- [AWS Bedrock Agent OpenAPI Schema Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-api-schema.html)
- [CloudFormation APISchema Property](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-bedrock-agent-apischema.html)

## Generated Agent Template

When the AutoNinja system generates a new agent, it must include ALL of the following core components. This template ensures every generated agent has a consistent, production-ready structure.

### Core Component Checklist

#### 1. System Prompts / Instructions
**Purpose**: Define the agent's identity, behavior, and capabilities

**Required Elements**:
- **Role Definition**: Clear statement of what the agent is (e.g., "You are a customer support agent for an insurance company")
- **Responsibilities**: Specific tasks the agent should perform
- **Behavioral Guidelines**: How the agent should interact (tone, style, constraints)
- **Example Interactions**: Sample conversations showing expected behavior
- **Constraints and Limitations**: What the agent should NOT do
- **Context Handling**: How to use conversation history and session state

**Example Template**:
```
You are a [ROLE] for [ORGANIZATION]. Your purpose is to [PRIMARY_GOAL].

Responsibilities:
- [RESPONSIBILITY_1]
- [RESPONSIBILITY_2]
- [RESPONSIBILITY_3]

Behavioral Guidelines:
- Be [TONE] and [STYLE]
- Always [BEHAVIOR_1]
- Never [BEHAVIOR_2]

When interacting with users:
1. [INTERACTION_STEP_1]
2. [INTERACTION_STEP_2]
3. [INTERACTION_STEP_3]

Constraints:
- Do not [CONSTRAINT_1]
- Only [CONSTRAINT_2]
- If [CONDITION], then [ACTION]
```

#### 2. Tool Use Capability (Action Groups)
**Purpose**: Enable the agent to perform actions via Lambda functions

**Required Elements**:
- **At least one action group** with Lambda function backend
- **OpenAPI 3.0 schema** defining all available tools/actions
- **Action descriptions** explaining when to use each tool
- **Input parameters** with types, descriptions, and validation rules
- **Output schemas** defining expected response structure
- **Error handling** for tool invocation failures

**Action Group Structure**:
```yaml
ActionGroup:
  Name: "primary-actions"
  Description: "Core actions for [AGENT_PURPOSE]"
  ActionGroupExecutor:
    Lambda: "arn:aws:lambda:region:account:function:agent-lambda"
  ApiSchema:
    Payload: |
      openapi: 3.0.0
      info:
        title: [AGENT_NAME] API
        version: 1.0.0
      paths:
        /action1:
          post:
            operationId: action1
            description: "Description of what this action does"
            requestBody:
              required: true
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      param1:
                        type: string
                        description: "Parameter description"
                    required: [param1]
            responses:
              200:
                description: "Success response"
                content:
                  application/json:
                    schema:
                      type: object
                      properties:
                        result:
                          type: string
```

#### 3. Communication Interface
**Purpose**: Define how the agent communicates with users and other systems

**Required Elements**:
- **Input Format**: How the agent receives requests (text, structured data, etc.)
- **Output Format**: How the agent returns responses (text, JSON, etc.)
- **Session Management**: How conversation state is maintained
- **Message Structure**: Standard format for all communications
- **Error Messages**: User-friendly error responses
- **Streaming Support**: Whether responses are streamed or batch

**Communication Model**:
```python
@dataclass
class AgentMessage:
    message_id: str
    session_id: str
    timestamp: str
    message_type: str  # "user_input" | "agent_response" | "tool_call" | "error"
    content: str
    metadata: Dict[str, Any]
    
@dataclass
class AgentResponse:
    response_id: str
    session_id: str
    timestamp: str
    response_text: str
    tool_calls: List[ToolCall]
    session_attributes: Dict[str, str]
    next_action: str  # "continue" | "end_session" | "request_input"
```

#### 4. Lambda Function Implementation
**Purpose**: Execute business logic for agent actions

**Required Elements**:
- **Handler function** with proper event parsing
- **Action routing** based on apiPath or function name
- **Input validation** for all parameters
- **Business logic** implementation
- **Error handling** with try-catch blocks
- **Structured logging** with context (session_id, action_name)
- **Response formatting** matching OpenAPI schema
- **Persistence calls** to DynamoDB/S3 if needed
- **requirements.txt** with all dependencies

**Lambda Handler Template**:
```python
import json
import logging
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for [AGENT_NAME] actions
    """
    try:
        # Parse event
        action_group = event.get('actionGroup')
        api_path = event.get('apiPath')
        parameters = event.get('parameters', [])
        session_id = event.get('sessionId')
        
        # Log input
        logger.info(f"Action: {api_path}, Session: {session_id}")
        
        # Route to action handler
        if api_path == '/action1':
            result = handle_action1(parameters, session_id)
        elif api_path == '/action2':
            result = handle_action2(parameters, session_id)
        else:
            raise ValueError(f"Unknown action: {api_path}")
        
        # Return formatted response
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': 'POST',
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result)
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return format_error_response(str(e))

def handle_action1(parameters: List[Dict], session_id: str) -> Dict[str, Any]:
    """Handle action1 logic"""
    # Extract parameters
    param1 = next((p['value'] for p in parameters if p['name'] == 'param1'), None)
    
    # Validate inputs
    if not param1:
        raise ValueError("param1 is required")
    
    # Execute business logic
    result = execute_business_logic(param1)
    
    # Return result
    return {'result': result, 'status': 'success'}

def format_error_response(error_message: str) -> Dict[str, Any]:
    """Format error response"""
    return {
        'messageVersion': '1.0',
        'response': {
            'httpStatusCode': 500,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({'error': error_message})
                }
            }
        }
    }
```

#### 5. IAM Roles and Policies
**Purpose**: Secure access control following least-privilege principles

**Required Elements**:
- **Bedrock Agent Execution Role**: Allows agent to invoke model and Lambda
- **Lambda Execution Role**: Allows Lambda to access AWS services
- **Resource-based policies**: Allow Bedrock to invoke Lambda
- **Service-specific policies**: For DynamoDB, S3, etc. if needed
- **KMS permissions**: For encryption/decryption if using customer-managed keys

**IAM Template**:
```yaml
BedrockAgentRole:
  Type: AWS::IAM::Role
  Properties:
    AssumeRolePolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            Service: bedrock.amazonaws.com
          Action: sts:AssumeRole
    ManagedPolicyArns:
      - !Ref BedrockAgentPolicy

BedrockAgentPolicy:
  Type: AWS::IAM::ManagedPolicy
  Properties:
    PolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Action:
            - bedrock:InvokeModel
          Resource: !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/*'
        - Effect: Allow
          Action:
            - lambda:InvokeFunction
          Resource: !GetAtt AgentLambda.Arn

LambdaExecutionRole:
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
      - !Ref LambdaPolicy

LambdaPolicy:
  Type: AWS::IAM::ManagedPolicy
  Properties:
    PolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Action:
            - logs:CreateLogStream
            - logs:PutLogEvents
          Resource: !Sub '${AgentLogGroup.Arn}:*'
```

#### 6. Bedrock Agent Configuration
**Purpose**: Define agent settings and behavior

**Required Elements**:
- **Agent Name**: Unique identifier
- **Description**: What the agent does
- **Foundation Model**: Model to use (e.g., Claude Sonnet 4.5)
- **Instructions**: System prompts (see #1)
- **Idle Session TTL**: Session timeout (default 30 minutes)
- **Agent Collaboration Mode**: DISABLED for standalone agents
- **Action Groups**: Tool definitions (see #2)
- **Knowledge Bases**: Optional RAG data sources
- **Guardrails**: Optional content filtering
- **Code Interpreter**: Optional code execution capability
- **User Input**: Optional ability to request more information

**Configuration Template**:
```yaml
Agent:
  Type: AWS::Bedrock::Agent
  Properties:
    AgentName: !Ref AgentName
    Description: "Description of agent purpose"
    AgentResourceRoleArn: !GetAtt BedrockAgentRole.Arn
    FoundationModel: anthropic.claude-sonnet-4-5-20250929-v1:0
    Instruction: |
      [SYSTEM PROMPTS FROM #1]
    IdleSessionTTLInSeconds: 1800
    AgentCollaboration: DISABLED
    ActionGroups:
      - ActionGroupName: "primary-actions"
        ActionGroupExecutor:
          Lambda: !GetAtt AgentLambda.Arn
        ApiSchema:
          Payload: !Sub |
            [OPENAPI SCHEMA FROM #2]
```

#### 7. CloudFormation Template
**Purpose**: Infrastructure as code for complete deployment

**Required Elements**:
- **Parameters**: Customizable values (environment, model, etc.)
- **Resources**: All AWS resources (agent, Lambda, IAM, logs, etc.)
- **Outputs**: Important values (agent ID, ARN, alias ID, endpoints)
- **Dependencies**: Proper DependsOn relationships
- **Metadata**: Template description and version

#### 8. Monitoring and Logging
**Purpose**: Observability and debugging

**Required Elements**:
- **CloudWatch Log Groups**: For agent and Lambda
- **Structured Logging**: JSON format with context
- **X-Ray Tracing**: End-to-end request tracing
- **Custom Metrics**: Optional performance metrics
- **Alarms**: Optional alerts for errors/latency

**Logging Configuration**:
```yaml
AgentLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub '/aws/bedrock/agents/${AgentName}'
    RetentionInDays: 30

LambdaLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub '/aws/lambda/${AgentName}-lambda'
    RetentionInDays: 30
```

#### 9. Testing Configuration
**Purpose**: Validate agent functionality

**Required Elements**:
- **Test cases** for each action
- **Sample inputs** with expected outputs
- **Integration test scenarios**
- **Test invocation script**

#### 10. Documentation
**Purpose**: Enable users to deploy and use the agent

**Required Elements**:
- **README.md**: Overview, features, architecture
- **DEPLOYMENT.md**: Step-by-step deployment guide
- **USAGE.md**: How to invoke and interact with agent
- **API_REFERENCE.md**: Complete action documentation
- **TROUBLESHOOTING.md**: Common issues and solutions

### Validation Checklist

Before deployment, the Quality Validator agent verifies:
- ✅ System prompts are clear, complete, and follow template
- ✅ At least one action group with valid OpenAPI schema
- ✅ Lambda function has proper error handling and logging
- ✅ Communication interface is well-defined
- ✅ IAM policies follow least-privilege principles
- ✅ CloudFormation template is syntactically valid
- ✅ No hardcoded credentials or secrets
- ✅ Encryption enabled for data at rest
- ✅ CloudWatch logging configured for agent and Lambda
- ✅ Test cases provided for all actions
- ✅ Documentation includes all required sections

**Threshold for Testing**: Set to extremely low (e.g., 50% pass rate) to allow testing with incomplete implementations

## Deployment Architecture

### AutoNinja System CloudFormation Template

**CRITICAL**: The entire AutoNinja system (1 supervisor + 5 collaborator agents + Lambda functions + DynamoDB + S3 + IAM + CloudWatch) is defined in a single CloudFormation template: `infrastructure/cloudformation/autoninja-complete.yaml`

This template is the **source of truth** for the AutoNinja system deployment. It creates all resources needed for the multi-agent system to function.

### Infrastructure Components


**CloudFormation Stack**: `autoninja-system`

**Resources Created**:

1. **Bedrock Agents** (6):
   - `SupervisorAgent` - Orchestrator
   - `RequirementsAnalystAgent` - Requirements extraction
   - `SolutionArchitectAgent` - Architecture design
   - `CodeGeneratorAgent` - Code generation
   - `QualityValidatorAgent` - Quality validation
   - `DeploymentManagerAgent` - Deployment

2. **Bedrock Agent Aliases** (6):
   - One production alias per agent
   - Version: DRAFT initially, then versioned

3. **Lambda Functions** (5):
   - `requirements-analyst-lambda`
   - `solution-architect-lambda`
   - `code-generator-lambda`
   - `quality-validator-lambda`
   - `deployment-manager-lambda`

4. **Lambda Layer** (1):
   - `autoninja-shared-layer` - Shared libraries

5. **IAM Roles** (11):
   - 6 Bedrock Agent execution roles
   - 5 Lambda execution roles

6. **IAM Policies** (11):
   - Least-privilege policies for each role

7. **Lambda Permissions** (5):
   - Resource-based policies allowing Bedrock invocation

8. **DynamoDB Table** (1):
   - `autoninja-inference-records`
   - On-demand billing
   - Point-in-time recovery enabled
   - Encryption at rest with KMS

9. **S3 Bucket** (1):
   - `autoninja-artifacts-{account-id}`
   - Versioning enabled
   - Encryption at rest with KMS
   - Lifecycle policy for archival

10. **CloudWatch Log Groups** (11):
    - 6 for Bedrock Agents
    - 5 for Lambda functions
    - 30-day retention by default

11. **Agent Collaborator Associations** (5):
    - Link supervisor to each collaborator

### Deployment Process

**Step 1: Deploy CloudFormation Stack**
```bash
aws cloudformation create-stack \
  --stack-name autoninja-system \
  --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
  --parameters ParameterKey=Environment,ParameterValue=production \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-2
```

**Step 2: Wait for Stack Creation**
```bash
aws cloudformation wait stack-create-complete \
  --stack-name autoninja-system \
  --region us-east-2
```

**Step 3: Get Outputs**
```bash
aws cloudformation describe-stacks \
  --stack-name autoninja-system \
  --query 'Stacks[0].Outputs'
```

**Step 4: Test System**
```bash
python examples/invoke_supervisor.py \
  --agent-id <supervisor-agent-id> \
  --alias-id <supervisor-alias-id> \
  --request "I would like a friend agent"
```

### Resource Dependencies

```
DynamoDB Table ──┐
S3 Bucket ───────┼──> Lambda Layer ──> Lambda Functions ──┐
IAM Roles ───────┘                                         │
                                                           ▼
                                              Collaborator Agents ──┐
                                                                    │
                                                                    ▼
                                                          Supervisor Agent
                                                                    │
                                                                    ▼
                                                    Agent Collaborator
                                                      Associations
```

### Deployment Validation

After deployment, validate:
1. All 6 agents are in `PREPARED` state
2. All 5 Lambda functions are active
3. DynamoDB table is active
4. S3 bucket is accessible
5. CloudWatch log groups exist
6. Agent collaborator associations are active
7. Test invocation succeeds

## Security Architecture

### IAM Permissions

**Bedrock Agent Execution Role** (per agent):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-5-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:{agent-name}-lambda"
    }
  ]
}
```

**Lambda Execution Role** (per function):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/{function-name}:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/autoninja-inference-records"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::autoninja-artifacts-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

**Deployment Manager Additional Permissions**:
```json
{
  "Effect": "Allow",
  "Action": [
    "cloudformation:CreateStack",
    "cloudformation:DescribeStacks",
    "cloudformation:UpdateStack",
    "bedrock:CreateAgent",
    "bedrock:CreateAgentActionGroup",
    "bedrock:CreateAgentAlias",
    "iam:CreateRole",
    "iam:AttachRolePolicy",
    "lambda:CreateFunction",
    "lambda:AddPermission"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:RequestedRegion": "us-east-2"
    }
  }
}
```

### Data Encryption

**At Rest**:
- DynamoDB: AWS KMS encryption with customer-managed key
- S3: AWS KMS encryption with customer-managed key
- CloudWatch Logs: Encrypted with AWS managed key

**In Transit**:
- All API calls use TLS 1.3
- Bedrock Agent to Lambda: HTTPS
- Lambda to DynamoDB/S3: HTTPS

### Network Security

- All resources deployed in AWS managed VPCs
- No public endpoints exposed
- Lambda functions can optionally run in VPC for additional isolation
- VPC endpoints for DynamoDB and S3 for private connectivity

### Secrets Management

- No hardcoded credentials in code
- IAM roles for authentication
- Secrets stored in AWS Secrets Manager if needed
- Environment variables for configuration

## Monitoring and Observability

### CloudWatch Metrics

**Custom Metrics**:
- `JobsCompleted` - Count of successful job completions
- `JobsFailed` - Count of failed jobs
- `AverageDuration` - Average time per job
- `TotalCost` - Estimated cost per job
- `TokensUsed` - Total tokens consumed per job

**Lambda Metrics** (automatic):
- Invocations
- Duration
- Errors
- Throttles
- Concurrent executions

**DynamoDB Metrics** (automatic):
- Read/write capacity units
- Throttled requests
- System errors

### CloudWatch Logs

**Log Groups**:
- `/aws/bedrock/agents/supervisor`
- `/aws/bedrock/agents/requirements-analyst`
- `/aws/bedrock/agents/solution-architect`
- `/aws/bedrock/agents/code-generator`
- `/aws/bedrock/agents/quality-validator`
- `/aws/bedrock/agents/deployment-manager`
- `/aws/lambda/requirements-analyst-lambda`
- `/aws/lambda/solution-architect-lambda`
- `/aws/lambda/code-generator-lambda`
- `/aws/lambda/quality-validator-lambda`
- `/aws/lambda/deployment-manager-lambda`

**Log Format** (structured JSON):
```json
{
  "timestamp": "2025-10-13T14:30:22.123Z",
  "level": "INFO",
  "job_name": "job-friend-20251013-143022",
  "agent_name": "requirements-analyst",
  "action_name": "extract_requirements",
  "message": "Successfully extracted requirements",
  "duration_ms": 3240,
  "tokens_used": 4532
}
```

### X-Ray Tracing

**Trace Segments**:
- Bedrock Agent invocation
- Lambda function execution
- DynamoDB operations
- S3 operations

**Service Map**:
Shows complete flow from supervisor through all collaborators to persistence layer

**Trace Filtering**:
- Filter by `job_name` annotation
- Filter by `agent_name` annotation
- Filter by error status

### CloudWatch Insights Queries

**Query all inferences for a job**:
```sql
fields @timestamp, agent_name, action_name, duration_seconds, tokens_used
| filter job_name = "job-friend-20251013-143022"
| sort @timestamp asc
```

**Query errors across all agents**:
```sql
fields @timestamp, agent_name, error_message
| filter level = "ERROR"
| stats count() by agent_name
```

**Query cost by agent**:
```sql
fields agent_name, cost_estimate
| stats sum(cost_estimate) as total_cost by agent_name
```

### Alarms

**Critical Alarms**:
- Lambda function errors > 5% of invocations
- DynamoDB throttling > 0
- Agent invocation failures > 10%
- Deployment failures > 20%

**Warning Alarms**:
- Lambda duration > 30 seconds
- Job completion time > 5 minutes
- Cost per job > $1.00

## Cost Optimization

### Pricing Model

**Bedrock API Calls**:
- Claude Sonnet 4.5: $0.003 per 1K input tokens, $0.015 per 1K output tokens
- Average 1,000 tokens per agent inference
- 5 agents × 2 inferences each = 10 total inferences
- Cost per generation: ~$0.195

**Lambda**:
- $0.20 per 1M requests
- $0.0000166667 per GB-second
- Average 10 invocations × 30 seconds × 1GB = 300 GB-seconds
- Cost per generation: ~$0.006

**DynamoDB**:
- On-demand: $1.25 per million write requests
- Average 10 writes per generation
- Cost per generation: ~$0.0000125

**S3**:
- Standard storage: $0.023 per GB
- Average 10 MB per generation
- Cost per generation: ~$0.0002

**Total Cost Per Generation**: ~$0.205

### Optimization Strategies

1. **Batch Processing**: Process multiple requests in parallel when possible
2. **Caching**: Cache common requirements and architectures
3. **Model Selection**: Use cheaper models for simple tasks
4. **Lambda Memory**: Optimize memory allocation for cost/performance
5. **S3 Lifecycle**: Archive old artifacts to Glacier after 90 days
6. **DynamoDB**: Use on-demand billing for variable workloads

## Scalability

### Horizontal Scaling

- **Bedrock Agents**: Automatically scale to handle concurrent requests
- **Lambda Functions**: Automatically scale to 1,000 concurrent executions (default)
- **DynamoDB**: On-demand mode scales automatically
- **S3**: Unlimited scalability

### Performance Targets

- **End-to-end latency**: < 90 seconds for simple agents
- **Concurrent jobs**: Support 100+ concurrent job executions
- **Throughput**: Process 1,000+ agent generations per day
- **Availability**: 99.9% uptime (AWS SLA)

### Bottlenecks and Mitigations

**Potential Bottleneck**: Lambda concurrent execution limit
- **Mitigation**: Request limit increase from AWS Support

**Potential Bottleneck**: Bedrock API rate limits
- **Mitigation**: Implement exponential backoff, request quota increase

**Potential Bottleneck**: DynamoDB write throttling
- **Mitigation**: Use on-demand mode, implement retry logic

## Future Enhancements

### Phase 1 (Current)
- ✅ Multi-agent architecture
- ✅ Complete persistence layer
- ✅ CloudFormation deployment

### Phase 2 (Next)
- Knowledge Base integration for RAG
- Guardrails for content filtering
- Human-in-the-loop approval workflow

### Phase 3 (Future)
- Custom model fine-tuning
- Multi-region deployment
- Advanced cost optimization
- Agent marketplace

### Phase 4 (Long-term)
- Self-improving agents
- Automated testing and validation
- Performance optimization recommendations
- Multi-cloud support
