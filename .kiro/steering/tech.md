# Technology Stack & Build System

## Core Technologies
- **Python 3.9+**: Primary language with type hints and modern features
- **LangChain/LangGraph**: Agent orchestration and workflow management
- **Amazon Bedrock**: Managed AI services and foundation models
- **AWS SDK (boto3/botocore)**: Deep AWS service integration
- **FastAPI + Uvicorn**: API layer and service interfaces
- **Pydantic v2**: Data validation and settings management

## AWS Services
- **Amazon Bedrock**: Foundation models, knowledge bases, guardrails
- **DynamoDB**: State persistence and session management
- **S3**: Artifact storage and deployment packages
- **Lambda**: Serverless compute for agent execution
- **X-Ray**: Distributed tracing and observability
- **CloudWatch**: Logging and metrics

## Development Tools
- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting (black profile)
- **pylint**: Code linting and quality checks
- **mypy**: Static type checking (strict mode)
- **pytest**: Testing framework with async support
- **pre-commit**: Automated quality checks
- **bandit**: Security scanning

## Build & Development Commands

### Environment Setup
```bash
# Automated setup
python setup_dev.py

# Manual setup
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements-dev.txt
pip install -e .
```

### Quality & Testing
```bash
make test          # Run full test suite with coverage
make lint          # Run all linting tools
make format        # Format code with black/isort
make security      # Run security checks
make quality       # Run all quality checks
make clean         # Clean build artifacts
```

### Development Workflow
```bash
pytest tests/ -v --cov=autoninja    # Run tests with coverage
black autoninja/ tests/             # Format code
pylint autoninja/                   # Lint code
mypy autoninja/                     # Type checking
pre-commit run --all-files          # Run all hooks

```

## Configuration Management
- **Environment Variables**: Use `.env` files for configuration
- **Pydantic Settings**: Type-safe configuration with validation
- **AWS Configuration**: Region, credentials, service settings
- **Prefixed Settings**: `BEDROCK_*` for Bedrock-specific config

## Testing Strategy
- **Unit Tests**: Individual component testing (`tests/unit/`)
- **Integration Tests**: Agent-to-agent communication (`tests/integration/`)
- **End-to-End Tests**: Complete pipeline validation (`tests/e2e/`)
- **Mocking**: Use `moto` for AWS service mocking
- **Coverage**: Maintain high test coverage with reporting