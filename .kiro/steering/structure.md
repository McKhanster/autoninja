# Project Structure

## Directory Organization

```
autoninja-bedrock-agents/
├── infrastructure/cloudformation/    # CloudFormation IaC templates
│   ├── autoninja-main.yaml          # Main nested stack orchestrator
│   ├── autoninja-collaborators.yaml # Collaborator agents stack
│   └── stacks/                      # Individual component stacks
│       ├── storage.yaml             # DynamoDB + S3
│       ├── lambda-layer.yaml        # Shared libraries layer
│       ├── custom-orchestration.yaml # Rate limiting
│       ├── requirements-analyst.yaml
│       ├── code-generator.yaml
│       ├── solution-architect.yaml
│       ├── quality-validator.yaml
│       ├── deployment-manager.yaml
│       └── supervisor.yaml          # Supervisor agent
│
├── lambda/                          # Lambda function implementations
│   ├── requirements-analyst/
│   │   └── handler.py              # CANONICAL reference implementation
│   ├── code-generator/
│   │   └── handler.py
│   ├── solution-architect/
│   │   └── handler.py
│   ├── quality-validator/
│   │   └── handler.py
│   ├── deployment-manager/
│   │   └── handler.py
│   └── supervisor-agentcore/       # AgentCore supervisor
│       ├── handler.py
│       ├── supervisor_agent.py
│       └── requirements.txt
│
├── shared/                          # Lambda Layer shared libraries
│   ├── persistence/
│   │   ├── dynamodb_client.py      # DynamoDB operations
│   │   └── s3_client.py            # S3 operations
│   ├── utils/
│   │   ├── logger.py               # Structured logging
│   │   ├── job_generator.py        # Job ID generation
│   │   ├── rate_limiter.py         # Rate limiting
│   │   └── agentcore_rate_limiter.py
│   ├── models/                     # Data models
│   │   ├── inference_record.py
│   │   ├── requirements.py
│   │   ├── code_artifacts.py
│   │   ├── architecture.py
│   │   ├── validation_report.py
│   │   └── deployment_results.py
│   └── requirements.txt            # Shared dependencies
│
├── schemas/                         # OpenAPI schemas for action groups
│   ├── requirements-analyst-schema.yaml
│   ├── code-generator-schema.yaml
│   ├── solution-architect-schema.yaml
│   ├── quality-validator-schema.yaml
│   └── deployment-manager-schema.yaml
│
├── scripts/                         # Deployment and utility scripts
│   ├── deploy_supervisor.sh
│   ├── deploy_collaborators.sh
│   ├── deploy_requirements_analyst.sh
│   ├── deploy_code_generator.sh
│   ├── package_lambda_layer.sh
│   └── upload_schemas.sh
│
├── tests/                           # Test suite
│   ├── requirements-analyst/
│   ├── code-generator/
│   ├── solution-architect/
│   ├── quality-validator/
│   ├── deployment-manager/
│   └── supervisor/
│
├── docs/                            # Documentation
│   ├── architecture_description.md
│   ├── architecture_diagram.png
│   └── hackathon.md
│
├── plan/                            # Planning documents
├── examples/                        # Usage examples
├── .bedrock_agentcore.yaml         # AgentCore configuration
├── pyproject.toml                  # Python project config
├── README.md                       # Main documentation
└── CLAUDE.md                       # AI assistant guidance
```

## Key Directories

### `/lambda`
Contains Lambda function implementations for each agent. Each agent has its own directory with a `handler.py` entry point. The Requirements Analyst (`lambda/requirements-analyst/handler.py`) is the canonical reference implementation that all other agents should follow.

### `/shared`
Lambda Layer containing shared libraries used across all Lambda functions. Includes:
- Persistence clients (DynamoDB, S3)
- Utilities (logging, job generation, rate limiting)
- Data models (Pydantic models for type safety)

### `/infrastructure/cloudformation`
CloudFormation templates using nested stack architecture:
- `autoninja-main.yaml` - Main orchestrator that deploys all components
- `stacks/` - Individual component stacks for modularity

### `/schemas`
OpenAPI 3.0 schemas defining action groups for each Bedrock Agent. These schemas define the API contract between agents and their Lambda functions.

### `/scripts`
Bash scripts for deployment, packaging, and configuration. All scripts are idempotent and can be run multiple times safely.

## File Naming Conventions

- Lambda handlers: `handler.py` (entry point for each Lambda)
- CloudFormation stacks: `kebab-case.yaml`
- Python modules: `snake_case.py`
- OpenAPI schemas: `agent-name-schema.yaml`
- Deployment scripts: `deploy_component.sh`

## Import Patterns

Lambda functions import from the shared layer:
```python
from shared.persistence.dynamodb_client import DynamoDBClient
from shared.persistence.s3_client import S3Client
from shared.utils.logger import get_logger
from shared.models.code_artifacts import CodeArtifacts
```

## Data Flow

1. User request → Supervisor Agent (AgentCore)
2. Supervisor generates job ID → Delegates to collaborators
3. Each collaborator:
   - Receives event via Lambda
   - Logs input to DynamoDB immediately
   - Executes business logic
   - Saves artifacts to S3
   - Logs output to DynamoDB
   - Returns response to supervisor
4. Supervisor aggregates results → Returns deployed agent ARN
