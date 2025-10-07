# Project Structure & Organization

## Package Architecture
```
autoninja/                     # Main package
├── __init__.py               # Package version and metadata
├── core/                     # Core infrastructure components
├── agents/                   # LangChain agent implementations
├── tools/                    # LangChain tools for AWS integration
├── models/                   # Data models and state management
├── storage/                  # DynamoDB and S3 integration
├── api/                      # FastAPI application layer
└── utils/                    # Utility functions and helpers
```

## Core Module (`autoninja/core/`)
- **bedrock_client.py**: Bedrock client management, circuit breakers, model selection
- **config.py**: Pydantic settings and environment configuration
- **knowledge_base.py**: Bedrock Knowledge Base integration
- **guardrails.py**: Bedrock Guardrails for content filtering
- **logging_config.py**: Structured logging configuration
- **pipeline_logging.py**: Pipeline-specific logging and tracing

## Agent Architecture (`autoninja/agents/`)
- Each agent is a separate module implementing LangChain agent patterns
- Agents use tools from `autoninja/tools/` for AWS service integration
- Follow naming convention: `{purpose}_agent.py` (e.g., `requirements_analyst.py`)

## Tool Organization (`autoninja/tools/`)
- **requirements_analysis.py**: Natural language processing tools
- **solution_architecture.py**: AWS architecture design tools
- **code_generation.py**: Code generation and templating tools
- **quality_validation.py**: Quality assurance and validation tools
- **deployment_management.py**: Deployment automation tools

## State Management (`autoninja/models/`)
- **state.py**: LangGraph state models, Pydantic schemas, enums
- Use TypedDict for LangGraph state flow
- Use Pydantic BaseModel for validation and serialization
- Enum classes for controlled vocabularies

## Storage Layer (`autoninja/storage/`)
- **dynamodb.py**: DynamoDB operations and session persistence
- **s3.py**: S3 operations for artifact storage
- Abstract storage interfaces for testability

## Testing Structure
```
tests/
├── unit/                     # Unit tests (fast, isolated)
├── integration/              # Integration tests (AWS services)
└── e2e/                      # End-to-end pipeline tests
```

## Naming Conventions
- **Files**: Snake_case (e.g., `bedrock_client.py`)
- **Classes**: PascalCase (e.g., `BedrockClientManager`)
- **Functions/Variables**: Snake_case (e.g., `get_bedrock_client`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`)
- **Private members**: Leading underscore (e.g., `_internal_method`)

## Import Organization
1. Standard library imports
2. Third-party imports (langchain, boto3, etc.)
3. Local imports (autoninja modules)
4. Use absolute imports within the package

## Configuration Files
- **pyproject.toml**: Project metadata, dependencies, tool configuration
- **requirements.txt**: Production dependencies
- **requirements-dev.txt**: Development dependencies
- **.env.example**: Environment variable template
- **Makefile**: Development commands and automation

## Logging Strategy
- Use structured logging with JSON format
- Session-based logging for pipeline tracing
- Separate log files for different components
- AWS X-Ray integration for distributed tracing

## Error Handling Patterns
- Use custom exception classes for domain-specific errors
- Implement circuit breakers for external service calls
- Exponential backoff retry logic for transient failures
- Comprehensive error logging with context