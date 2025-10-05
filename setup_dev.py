#!/usr/bin/env python3
"""
Development environment setup script for AutoNinja AWS Bedrock.

This script sets up the development environment with proper Python virtual environment
and installs all necessary dependencies.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {command}")
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, check=check
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required.")
        sys.exit(1)
    print(f"Python version: {sys.version}")


def setup_virtual_environment():
    """Set up Python virtual environment."""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Virtual environment already exists.")
        return
    
    print("Creating virtual environment...")
    run_command(f"{sys.executable} -m venv venv")
    
    # Determine the correct activation script path
    if os.name == 'nt':  # Windows
        activate_script = venv_path / "Scripts" / "activate"
        pip_path = venv_path / "Scripts" / "pip"
    else:  # Unix/Linux/macOS
        activate_script = venv_path / "bin" / "activate"
        pip_path = venv_path / "bin" / "pip"
    
    print(f"Virtual environment created at: {venv_path.absolute()}")
    print(f"To activate: source {activate_script}")
    
    return pip_path


def install_dependencies(pip_path: Path):
    """Install project dependencies."""
    print("Installing dependencies...")
    
    # Upgrade pip first
    run_command(f"{pip_path} install --upgrade pip")
    
    # Install development dependencies
    run_command(f"{pip_path} install -r requirements-dev.txt")
    
    # Install the package in development mode
    run_command(f"{pip_path} install -e .")


def setup_pre_commit():
    """Set up pre-commit hooks."""
    print("Setting up pre-commit hooks...")
    
    # Create .pre-commit-config.yaml
    pre_commit_config = """
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements
      - id: check-docstring-first

  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
"""
    
    with open(".pre-commit-config.yaml", "w") as f:
        f.write(pre_commit_config.strip())
    
    # Install pre-commit hooks
    venv_path = Path("venv")
    if os.name == 'nt':  # Windows
        pre_commit_path = venv_path / "Scripts" / "pre-commit"
    else:  # Unix/Linux/macOS
        pre_commit_path = venv_path / "bin" / "pre-commit"
    
    run_command(f"{pre_commit_path} install")


def create_env_file():
    """Create environment configuration file."""
    env_content = """
# AWS Configuration
AWS_REGION=us-east-2
AWS_PROFILE=default

# Bedrock Configuration
BEDROCK_REGION=us-east-2

# DynamoDB Configuration
DYNAMODB_TABLE_PREFIX=autoninja-

# S3 Configuration
S3_BUCKET_PREFIX=autoninja-artifacts-

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# Logging Configuration
LOG_LEVEL=INFO

# Development Configuration
ENVIRONMENT=development
"""
    
    env_file = Path(".env.example")
    if not env_file.exists():
        with open(env_file, "w") as f:
            f.write(env_content.strip())
        print("Created .env.example file")


def main():
    """Main setup function."""
    print("Setting up AutoNinja AWS Bedrock development environment...")
    
    # Check Python version
    check_python_version()
    
    # Set up virtual environment
    pip_path = setup_virtual_environment()
    
    if pip_path:
        # Install dependencies
        install_dependencies(pip_path)
        
        # Set up pre-commit
        setup_pre_commit()
    
    # Create environment file
    create_env_file()
    
    print("\n" + "="*60)
    print("Development environment setup complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\activate")
    else:  # Unix/Linux/macOS
        print("   source venv/bin/activate")
    print("2. Copy .env.example to .env and configure your settings")
    print("3. Configure your AWS credentials")
    print("4. Run tests: pytest")
    print("5. Start development!")


if __name__ == "__main__":
    main()