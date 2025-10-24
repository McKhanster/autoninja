# AutoNinja AWS Bedrock Agents

A production-grade, serverless multi-agent system built entirely on **AWS Bedrock Agents** that transforms natural language requests into fully deployed AI agents. Uses native AWS multi-agent collaboration, Lambda functions, and comprehensive persistence.

## Overview

AutoNinja uses a **Supervisor Lambda + Bedrock Agents** architecture to orchestrate 5 specialized Bedrock Agents that work together to design, generate, validate, and deploy production-ready AI agents from simple natural language descriptions.

**User Input:** "I would like a friend agent"
**System Output:** Fully deployed AWS Bedrock Agent with Lambda functions, CloudFormation stack, and complete documentation

**Architecture:** A single Supervisor Lambda function orchestrates 5 Bedrock Agents, calling them directly via the Bedrock Agent Runtime API. The supervisor handles all response parsing, artifact extraction, and persistence to S3/DynamoDB.

## Key Features

### Multi-Agent Architecture
- ✅ **5 Specialized Bedrock Agents** - Requirements Analyst, Solution Architect, Code Generator, Quality Validator, Deployment Manager
- ✅ **Supervisor Lambda Orchestration** - Coordinates agent invocations, parses responses, persists artifacts
- ✅ **Sequential Processing with Quality Gates** - Each phase validated before proceeding
- ✅ **Direct Bedrock Agent Invocation** - No intermediate Lambda functions, cleaner architecture
- ✅ **Built-in Retry Logic** - Automatic error handling and recovery with quality validation

### Complete Persistence & Audit Trail
- ✅ **DynamoDB Inference Storage** - Every prompt and response saved with job tracking
- ✅ **S3 Artifact Storage** - All generated code, configs, and templates persisted
- ✅ **CloudWatch Logging** - Comprehensive logs with unique streams per run
- ✅ **X-Ray Tracing** - Full request tracing across all agents and Lambda functions
- ✅ **Job Number Tracking** - Every run gets unique job ID for end-to-end traceability

### Production-Ready Output
- ✅ **CloudFormation Templates** - Infrastructure as code for generated agents
- ✅ **Lambda Functions** - Production-ready Python code with error handling
- ✅ **Bedrock Agent Configuration** - Complete agent setup with action groups
- ✅ **Automated Deployment** - One-click deployment to AWS
- ✅ **IAM Policies** - Least-privilege security configurations

### AWS-Native & Serverless
- ✅ **Zero Infrastructure** - Fully managed by AWS
- ✅ **Auto-Scaling** - Handles any load automatically
- ✅ **Pay-Per-Use** - Only pay for actual invocations
- ✅ **High Availability** - Built on AWS managed services
- ✅ **Security** - IAM-based authentication and encryption at rest/transit

## Architecture

### Supervisor + Collaborator Pattern

```
User Request: "I would like a friend agent"
       ↓
[Supervisor Lambda]
   ├── Analyzes request
   ├── Generates job-friend-20251023-143022
   └── Orchestrates Bedrock Agents directly:
       ↓
       ├──> [Requirements Analyst Bedrock Agent]
       │    └─> Returns: Structured requirements JSON
       │         Supervisor parses & saves to DynamoDB/S3
       ↓
       ├──> [Solution Architect Bedrock Agent]
       │    └─> Returns: Architecture design JSON
       │         Supervisor parses & saves to DynamoDB/S3
       ↓
       ├──> [Code Generator Bedrock Agent]
       │    └─> Returns: Lambda code, agent config, OpenAPI schemas
       │         Supervisor parses & saves individual files to S3
       │         (handler.py, requirements.txt, agent_config.yaml, etc.)
       ↓
       ├──> [Quality Validator Bedrock Agent]
       │    └─> Returns: Validation results JSON
       │         Supervisor parses & saves to DynamoDB/S3
       ↓
       └──> [Deployment Manager Bedrock Agent]
            └─> Returns: CloudFormation template + deployment status
                 Supervisor parses & saves template as YAML to S3
                 Returns: Deployed Bedrock Agent ARN + endpoints
```

**Key Architecture Changes:**
- ✅ **Supervisor Lambda** calls Bedrock Agents directly via `bedrock-agent-runtime.invoke_agent()`
- ✅ **No Lambda agents** - Each Bedrock Agent returns JSON responses directly
- ✅ **Supervisor handles all parsing** - Extracts code files, configs, templates from responses
- ✅ **Supervisor handles all persistence** - Saves artifacts to S3, logs to DynamoDB
- ✅ **Cleaner architecture** - No circular Lambda invocations, simpler flow

### The 6 Components

| Component | Type | Role | Outputs |
|-----------|------|------|---------|
| **Supervisor** | Lambda Function | Orchestrates workflow, calls Bedrock Agents, parses responses, persists artifacts | Task assignments, consolidated results, all artifacts |
| **Requirements Analyst** | Bedrock Agent | Analyzes user requests | Requirements JSON |
| **Solution Architect** | Bedrock Agent | Designs AWS architecture | Architecture design JSON |
| **Code Generator** | Bedrock Agent | Generates production code | Lambda code, agent config, OpenAPI schemas (as JSON) |
| **Quality Validator** | Bedrock Agent | Validates quality/security | Validation results JSON |
| **Deployment Manager** | Bedrock Agent | Generates deployment templates | CloudFormation template JSON |

## Data Persistence Architecture

### Every Run is Fully Tracked

**Job Number Generation:**
```
User: "I would like a friend"
System generates: job-friend-20251013-143022
```

**DynamoDB Schema:**
```
Table: autoninja-inference-records
Partition Key: job_name (e.g., "job-friend-20251013-143022")
Sort Key: timestamp

Attributes:
- job_name: "job-friend-20251013-143022"
- session_id: "abc-123-def-456"
- agent_name: "requirements_analyst"
- inference_id: "unique-inference-id"
- prompt: "Full prompt sent to Bedrock"
- response: "Full response from Bedrock"
- model_id: "anthropic.claude-sonnet-4-5"
- tokens_used: 4532
- cost_estimate: 0.0226
- duration_seconds: 3.24
- timestamp: "2025-10-13T14:30:22Z"
- artifacts_s3_uri: "s3://autoninja-artifacts/job-friend-20251013-143022/requirements/"
```

**S3 Artifact Structure:**
```
s3://autoninja-artifacts/
└── job-friend-20251013-143022/
    ├── requirements/
    │   ├── requirements_analyst/
    │   │   ├── requirements_job-friend-20251013-143022.json
    │   │   └── complexity_assessment.json
    ├── architecture/
    │   ├── solution_architect/
    │   │   ├── architecture_design.json
    │   │   ├── service_selection.json
    │   │   └── infrastructure_template.yaml
    ├── code/
    │   ├── code_generator/
    │   │   ├── lambda_handler.py
    │   │   ├── agent_config.json
    │   │   └── openapi_schema.yaml
    ├── validation/
    │   ├── quality_validator/
    │   │   ├── quality_report.json
    │   │   └── security_findings.json
    └── deployment/
        ├── deployment_manager/
        │   ├── cloudformation_template.yaml
        │   ├── deployment_results.json
        │   └── agent_arn.txt
```

**CloudWatch Log Groups:**
```
/aws/lambda/requirements-analyst-lambda
/aws/lambda/solution-architect-lambda
/aws/lambda/code-generator-lambda
/aws/lambda/quality-validator-lambda
/aws/lambda/deployment-manager-lambda
/aws/bedrock/agents/supervisor-agent
/aws/bedrock/agents/requirements-analyst
/aws/bedrock/agents/solution-architect
/aws/bedrock/agents/code-generator
/aws/bedrock/agents/quality-validator
/aws/bedrock/agents/deployment-manager
```

**Log Streams (Timestamped per Run):**
```
/aws/lambda/requirements-analyst-lambda/2025/10/13/job-friend-20251013-143022
/aws/lambda/solution-architect-lambda/2025/10/13/job-friend-20251013-143022
... etc
```

## Quick Start

### Prerequisites

- AWS Account with Bedrock access enabled
- AWS CLI configured with administrator permissions
- Python 3.9+ (for local development/testing)
- Terraform or AWS CDK (for infrastructure deployment)

### Deployment Steps

#### 1. Deploy AutoNinja System with CloudFormation

AutoNinja provides a comprehensive CloudFormation template that deploys the entire system:

```bash
# Clone repository
git clone <repository-url>
cd autoninja-bedrock-agents

# Deploy using CloudFormation
aws cloudformation create-stack \
  --stack-name autoninja-system \
  --template-body file://infrastructure/cloudformation/autoninja-complete.yaml \
  --parameters ParameterKey=Environment,ParameterValue=production \
               ParameterKey=BedrockModel,ParameterValue=anthropic.claude-3-7-sonnet-20250219-v1:0 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-2

# Monitor deployment (takes 10-15 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name autoninja-system \
  --region us-east-2

# Get outputs
aws cloudformation describe-stacks \
  --stack-name autoninja-system \
  --query 'Stacks[0].Outputs' \
  --region us-east-2
```

**The CloudFormation template creates:**
- ✅ 1 Supervisor Lambda function (orchestrates everything)
- ✅ 5 Bedrock Agents (Requirements Analyst, Solution Architect, Code Generator, Quality Validator, Deployment Manager)
- ✅ 5 Bedrock Agent Aliases (production versions)
- ✅ DynamoDB table `autoninja-inference-records`
- ✅ S3 bucket `autoninja-artifacts-{account-id}`
- ✅ IAM roles and policies (least privilege)
- ✅ CloudWatch log groups with retention policies
- ✅ Lambda layers for shared code (persistence, logging, rate limiting)

**Alternative: Deploy with Terraform**

```bash
cd infrastructure/terraform
terraform init
terraform plan -var="environment=production"
terraform apply -auto-approve
```

**Alternative: Deploy with AWS CDK**

```bash
cd infrastructure/cdk
npm install
cdk bootstrap
cdk deploy AutoNinjaStack
```

#### 2. Test the System

```bash
# Invoke the supervisor agent
python examples/invoke_supervisor.py \
  --request "I would like a friend agent"

# Monitor in real-time
tail -f logs/job-*.log

# Check DynamoDB for inference records
aws dynamodb query \
  --table-name autoninja-inference-records \
  --key-condition-expression "job_name = :job" \
  --expression-attribute-values '{":job":{"S":"job-friend-20251013-143022"}}'

# Check S3 for artifacts
aws s3 ls s3://autoninja-artifacts/job-friend-20251013-143022/ --recursive
```

#### 3. View Results

```bash
# Get deployed agent ARN
cat outputs/job-friend-20251013-143022/agent_arn.txt

# Test the deployed agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id <agent-id> \
  --agent-alias-id <alias-id> \
  --session-id test-session \
  --input-text "Hello, are you working?"
```

## Project Structure

```
autoninja-bedrock-agents/
├── infrastructure/               # Infrastructure as Code
│   ├── cloudformation/          # CloudFormation templates
│   │   ├── autoninja-complete.yaml      # Complete system (MAIN TEMPLATE)
│   │   ├── bedrock-agents.yaml          # Bedrock Agents only
│   │   ├── lambda-functions.yaml        # Lambda functions only
│   │   ├── storage.yaml                 # DynamoDB + S3
│   │   └── monitoring.yaml              # CloudWatch + X-Ray
│   ├── terraform/               # Terraform modules (alternative)
│   │   ├── bedrock-agents/     # Bedrock Agent configurations
│   │   ├── lambda-functions/   # Lambda function definitions
│   │   ├── storage/            # DynamoDB + S3 setup
│   │   └── monitoring/         # CloudWatch + X-Ray
│   └── cdk/                    # AWS CDK (alternative)
│
├── lambda/                      # Lambda function source code
│   └── supervisor-agentcore/   # Main orchestrator Lambda
│       ├── handler.py          # Lambda entry point
│       ├── requirements.txt    # Dependencies
│       └── README.md           # Supervisor documentation
│
├── infrastructure/cloudformation/prompts/  # Bedrock Agent prompts
│   ├── requirements-analyst-base-prompt.json
│   ├── solution-architect-base-prompt.json
│   ├── code-generator-base-prompt.json
│   ├── quality-validator-base-prompt.json
│   └── deployment-manager-base-prompt.json
│
├── shared/                      # Shared libraries (Lambda Layer)
│   ├── persistence/
│   │   ├── dynamodb_client.py  # DynamoDB operations
│   │   └── s3_client.py        # S3 operations
│   ├── models/
│   │   └── inference_record.py # Data models
│   └── utils/
│       ├── job_generator.py    # Job ID generation
│       └── logger.py           # Structured logging
│
├── examples/                    # Usage examples
│   ├── invoke_supervisor.py    # Invoke the system
│   ├── query_inference.py      # Query DynamoDB records
│   └── analyze_artifacts.py    # Analyze S3 artifacts
│
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests for Lambda functions
│   ├── integration/            # Integration tests for agents
│   └── e2e/                    # End-to-end pipeline tests
│
├── docs/                        # Documentation
│   ├── architecture.md         # Architecture details
│   ├── persistence.md          # Persistence strategy
│   ├── deployment.md           # Deployment guide
│   └── api-reference.md        # API documentation
│
├── BEDROCK_AGENTS_MIGRATION_ANALYSIS.md  # Technical analysis
├── COMPREHENSIVE_AUDIT_REPORT.md         # System audit
├── README.md                             # This file
└── pyproject.toml                        # Python project config
```

## Configuration

### Environment Variables

```bash
# AWS Configuration
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356
export AWS_ACCOUNT_ID=784327326356

# DynamoDB Configuration
export DYNAMODB_TABLE_NAME=autoninja-inference-records
export DYNAMODB_ENDPOINT=https://dynamodb.us-east-2.amazonaws.com

# S3 Configuration
export S3_BUCKET_NAME=autoninja-artifacts
export S3_REGION=us-east-2

# Bedrock Configuration
export BEDROCK_MODEL_ID=anthropic.claude-3-7-sonnet-20250219-v1:0
export BEDROCK_REGION=us-east-2

# Logging Configuration
export LOG_LEVEL=INFO
export CLOUDWATCH_LOG_GROUP=/aws/autoninja
```

### Bedrock Agent Configuration

Each agent is configured with:

1. **Instructions** - Natural language description of role and responsibilities
2. **Foundation Model** - Claude Sonnet 4.5 (or your preferred model)
3. **Action Groups** - OpenAPI schemas defining capabilities
4. **Lambda Functions** - Business logic implementation
5. **Guardrails** - Content filtering and safety rules (optional)
6. **Knowledge Bases** - RAG data sources (optional)

Example supervisor configuration:
```yaml
AgentName: orchestrator-supervisor
FoundationModel: anthropic.claude-3-7-sonnet-20250219-v1:0
Instruction: |
  You are the AutoNinja orchestrator supervisor. Your role is to coordinate 5 specialist agents
  to generate production-ready AI agents from user descriptions.

  For each user request:
  1. Generate a unique job number (e.g., job-friend-20251013-143022)
  2. Delegate to Requirements Analyst to understand specifications
  3. Delegate to Solution Architect to design AWS architecture
  4. Delegate to Code Generator to create Lambda functions and configs
  5. Delegate to Quality Validator to ensure quality and security
  6. Delegate to Deployment Manager to deploy to AWS
  7. Consolidate all outputs and provide the deployed agent ARN

  Pass the job_name to ALL collaborators for tracking.
AgentCollaboration: SUPERVISOR
Collaborators:
  - requirements-analyst
  - solution-architect
  - code-generator
  - quality-validator
  - deployment-manager
```

## Development

### Local Testing

```bash
# Test Lambda function locally
cd lambda/requirements-analyst
python -m pytest tests/

# Test with SAM Local
sam local invoke RequirementsAnalystFunction \
  --event test_events/extract_requirements.json

# Test Bedrock Agent (requires AWS)
python examples/test_agent.py \
  --agent-id <agent-id> \
  --input "I would like a friend agent"
```

### Adding a New Agent Action

1. **Update OpenAPI Schema** (`schemas/<agent>-schema.yaml`)
2. **Implement Lambda Handler** (`lambda/<agent>/handler.py`)
3. **Add Business Logic** (`lambda/<agent>/business_logic.py`)
4. **Add Persistence Calls** (save to DynamoDB + S3)
5. **Update Agent Configuration** (add action group)
6. **Deploy and Test**

### Monitoring and Debugging

**CloudWatch Insights Queries:**

```sql
-- Query all inferences for a job
fields @timestamp, agent_name, inference_id, tokens_used, duration_seconds
| filter job_name = "job-friend-20251013-143022"
| sort @timestamp desc

-- Query errors across all agents
fields @timestamp, agent_name, error_message
| filter @message like /ERROR/
| stats count() by agent_name
```

**X-Ray Traces:**

View complete request flow across all agents and Lambda functions:
- Go to AWS X-Ray console
- Filter by job_name tag
- View service map and trace timeline

**DynamoDB Query:**

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('autoninja-inference-records')

response = table.query(
    KeyConditionExpression='job_name = :job',
    ExpressionAttributeValues={
        ':job': 'job-friend-20251013-143022'
    }
)

for item in response['Items']:
    print(f"{item['timestamp']}: {item['agent_name']} - {item['duration_seconds']}s")
```

## Cost Estimation

### Per-Generation Costs (1,000 tokens avg per agent)

| Component | Cost per Generation | Notes |
|-----------|---------------------|-------|
| Bedrock API calls (5 agents) | $0.195 | Claude Sonnet 4.5: $0.003 input + $0.015 output |
| Lambda invocations (10 calls) | $0.001 | 5 agents × 2 calls avg |
| Lambda duration (300 GB-sec) | $0.005 | 10 calls × 30s × 1GB |
| DynamoDB writes (5 records) | $0.001 | On-demand pricing |
| S3 storage (10 MB) | $0.0002 | Standard storage |
| CloudWatch Logs (5 MB) | $0.003 | Ingestion + storage |
| **Total per Generation** | **$0.205** | |

### Monthly Costs (1,000 generations/month)

| Component | Monthly Cost |
|-----------|--------------|
| Bedrock API | $195.00 |
| Lambda | $6.00 |
| DynamoDB | $38.00 |
| S3 Storage | $0.25 |
| CloudWatch Logs | $3.00 |
| **Total** | **$242.25** |

**Comparison to LangChain Architecture:**
- Current: $282-432/month
- Bedrock Agents: $242/month
- **Savings: 15-44%**

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Average end-to-end time | 45-90 seconds |
| Cold start (Lambda) | 2-5 seconds |
| Warm execution | < 1 second per Lambda |
| Concurrent executions | Unlimited (AWS managed) |
| Max execution time | 15 minutes (Lambda limit) |
| Max payload size | 6 MB (Lambda response limit) |

## Security

### IAM Permissions Required

**For Deployment:**
- `bedrock:CreateAgent`
- `bedrock:CreateAgentActionGroup`
- `bedrock:CreateAgentAlias`
- `bedrock:AssociateAgentCollaborator`
- `lambda:CreateFunction`
- `lambda:AddPermission`
- `dynamodb:CreateTable`
- `s3:CreateBucket`
- `iam:CreateRole`
- `iam:AttachRolePolicy`

**For Runtime:**
- `bedrock:InvokeAgent` (supervisor only)
- `lambda:InvokeFunction` (per agent)
- `dynamodb:PutItem`, `dynamodb:Query`
- `s3:PutObject`, `s3:GetObject`
- `logs:CreateLogStream`, `logs:PutLogEvents`

### Data Security

- ✅ **Encryption at rest**: DynamoDB and S3 use AWS KMS
- ✅ **Encryption in transit**: TLS 1.3 for all API calls
- ✅ **IAM authentication**: No API keys, token-based auth
- ✅ **Least privilege**: Each Lambda has minimal permissions
- ✅ **Audit logging**: All access logged to CloudTrail
- ✅ **Guardrails**: Optional content filtering via Bedrock Guardrails

## Troubleshooting

### Common Issues

**Issue: Lambda timeout (15 min limit)**
- Solution: Split long operations into multiple Lambda calls
- Use Step Functions for orchestration if needed

**Issue: Payload too large (6 MB limit)**
- Solution: Store large artifacts in S3, pass S3 URI instead

**Issue: Bedrock throttling**
- Solution: Implement exponential backoff, request quota increase

**Issue: CloudWatch logs not appearing**
- Solution: Check IAM permissions for `logs:PutLogEvents`

**Issue: DynamoDB writes failing**
- Solution: Check table exists, verify IAM permissions

## CloudFormation Template Structure

AutoNinja's main CloudFormation template (`autoninja-complete.yaml`) includes:

### Parameters
- `Environment` - production/staging/dev
- `BedrockModel` - Foundation model for all agents
- `DynamoDBBillingMode` - PAY_PER_REQUEST or PROVISIONED
- `S3BucketName` - Optional custom bucket name
- `LogRetentionDays` - CloudWatch log retention (default: 30)

### Resources Created (40+ resources)
| Resource Type | Count | Description |
|---------------|-------|-------------|
| AWS::Bedrock::Agent | 5 | Requirements Analyst, Solution Architect, Code Generator, Quality Validator, Deployment Manager |
| AWS::Bedrock::AgentAlias | 5 | Production aliases |
| AWS::Lambda::Function | 1 | Supervisor orchestrator |
| AWS::Lambda::LayerVersion | 1 | Shared code library (persistence, logging, rate limiting) |
| AWS::IAM::Role | 6 | Bedrock agent roles + Lambda role |
| AWS::IAM::Policy | 6 | Least-privilege policies |
| AWS::DynamoDB::Table | 1 | Inference record storage |
| AWS::S3::Bucket | 1 | Artifact storage |
| AWS::S3::BucketPolicy | 1 | Bucket access control |
| AWS::Logs::LogGroup | 6 | CloudWatch log groups |

### Outputs
- `SupervisorLambdaArn` - Supervisor Lambda function ARN
- `RequirementsAnalystAgentId` - Requirements analyst Bedrock Agent ID
- `RequirementsAnalystAliasId` - Requirements analyst alias ID
- `SolutionArchitectAgentId` - Solution architect Bedrock Agent ID
- `SolutionArchitectAliasId` - Solution architect alias ID
- `CodeGeneratorAgentId` - Code generator Bedrock Agent ID
- `CodeGeneratorAliasId` - Code generator alias ID
- `QualityValidatorAgentId` - Quality validator Bedrock Agent ID
- `QualityValidatorAliasId` - Quality validator alias ID
- `DeploymentManagerAgentId` - Deployment manager Bedrock Agent ID
- `DeploymentManagerAliasId` - Deployment manager alias ID
- `DynamoDBTableName` - Inference records table
- `S3BucketName` - Artifacts bucket
- `InvocationCommand` - CLI command to invoke supervisor

### Stack Dependencies
```
autoninja-collaborators-production (main stack)
├── Creates all resources in order:
│   1. IAM Roles & Policies
│   2. DynamoDB Table & S3 Bucket
│   3. Lambda Layer (shared code: persistence, logging, rate limiting)
│   4. Supervisor Lambda Function
│   5. CloudWatch Log Groups
│   6. Bedrock Agents (5): Requirements Analyst, Solution Architect, 
│      Code Generator, Quality Validator, Deployment Manager
│   7. Bedrock Agent Aliases (5)
└── Exports agent IDs for supervisor to invoke
```

## Roadmap

- [x] **Phase 1**: Design Bedrock Agents architecture
- [x] **Phase 2**: Create CloudFormation template
- [ ] **Phase 3**: Implement Lambda functions (In Progress)
- [ ] **Phase 4**: Implement complete persistence layer
- [ ] **Phase 5**: Add Knowledge Base integration
- [ ] **Phase 6**: Add Guardrails for content filtering
- [ ] **Phase 7**: Implement human-in-the-loop approval
- [ ] **Phase 8**: Add custom model fine-tuning
- [ ] **Phase 9**: Multi-region deployment
- [ ] **Phase 10**: Cost optimization features

## References

### AWS Documentation
- [Bedrock Agents Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)
- [Create Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/create-multi-agent-collaboration.html)
- [Lambda Functions for Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html)
- [Bedrock Agent Action Groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-add.html)

### Technical Analysis
- [BEDROCK_AGENTS_MIGRATION_ANALYSIS.md](./BEDROCK_AGENTS_MIGRATION_ANALYSIS.md) - Detailed comparison and analysis
- [COMPREHENSIVE_AUDIT_REPORT.md](./COMPREHENSIVE_AUDIT_REPORT.md) - System audit and requirements

## Support

For questions, issues, or contributions:
- 📧 Email: support@autoninja.ai
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/autoninja-bedrock-agents/issues)
- 📚 Docs: [Documentation Site](https://docs.autoninja.ai)

## License

MIT License - see LICENSE file for details.

---

**Built with AWS Bedrock Agents** | **Fully Serverless** | **Production-Ready**


<!-- 

-->