# AutoNinja AWS Bedrock

A serverless, multi-agent system built on Amazon Bedrock that transforms natural language requests into production-ready AI agents using LangChain and LangGraph.

## Overview

AutoNinja AWS Bedrock leverages Amazon Bedrock's managed AI services, Knowledge Bases, and AgentCore orchestration framework to generate complete, deployable AI agents through a pipeline of specialized agents working collaboratively.

## Features

- **Multi-Agent Orchestration**: LangGraph-based workflow coordination
- **Specialized Agents**: Requirements analysis, solution architecture, code generation, quality validation, and deployment management
- **AWS-Native**: Built on Amazon Bedrock, DynamoDB, S3, and other AWS services
- **Production-Ready**: Comprehensive testing, monitoring, and deployment automation
- **Serverless-First**: Optimized for AWS Lambda and serverless architectures

## Architecture

The system implements a hierarchical multi-agent pattern with:

- **Master Orchestrator**: Central coordinator using LangGraph state management
- **Requirements Analyst**: Natural language processing and requirements extraction
- **Solution Architect**: AWS-native architecture design and service selection
- **Code Generator**: Production-ready code generation with AWS SDK integration
- **Quality Validator**: Comprehensive quality assurance and compliance validation
- **Deployment Manager**: Deployment automation and operational setup

## Quick Start

### Prerequisites

- Python 3.9 or higher
- AWS CLI configured with appropriate permissions
- Access to Amazon Bedrock services

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd autoninja-aws-bedrock
   ```

2. **Set up development environment**:
   ```bash
   python setup_dev.py
   ```

3. **Activate virtual environment**:
   ```bash
   # On Unix/Linux/macOS
   source venv/bin/activate
   
   # On Windows
   venv\Scripts\activate
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your AWS configuration
   ```

5. **Run tests**:
   ```bash
   make test
   ```

### Manual Setup

If you prefer manual setup:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements-dev.txt
pip install -e .

# Set up pre-commit hooks
pre-commit install
```

## Project Structure

```
autoninja/
├── autoninja/                 # Main package
│   ├── core/                 # Core components
│   ├── agents/               # LangChain agents
│   ├── tools/                # LangChain tools for AWS integration
│   ├── models/               # Data models and state management
│   ├── storage/              # DynamoDB and S3 integration
│   ├── api/                  # FastAPI application
│   └── utils/                # Utility functions
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── pyproject.toml           # Project configuration
└── setup_dev.py            # Development setup script
```

## Development Commands

```bash
# Run tests
make test

# Run linting
make lint

# Format code
make format

# Run security checks
make security

# Run all quality checks
make quality

# Clean build artifacts
make clean
```

## Configuration

The system uses environment variables for configuration. Copy `.env.example` to `.env` and configure:

- **AWS Configuration**: Region, profile, credentials
- **Bedrock Configuration**: Model settings, guardrails
- **Storage Configuration**: DynamoDB and S3 settings
- **API Configuration**: FastAPI server settings

## Testing

The project includes comprehensive testing:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Agent-to-agent communication testing
- **End-to-End Tests**: Complete pipeline validation

Run tests with:
```bash
pytest tests/ -v --cov=autoninja
```

## Code Quality

The project enforces code quality through:

- **Black**: Code formatting
- **isort**: Import sorting
- **pylint**: Code linting
- **mypy**: Type checking
- **bandit**: Security scanning
- **pre-commit**: Automated quality checks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run quality checks: `make quality`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For questions and support, please open an issue in the repository.