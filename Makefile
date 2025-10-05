.PHONY: help setup install test lint format clean docs

# Default target
help:
	@echo "Available commands:"
	@echo "  setup     - Set up development environment"
	@echo "  install   - Install dependencies"
	@echo "  test      - Run tests"
	@echo "  lint      - Run linting"
	@echo "  format    - Format code"
	@echo "  clean     - Clean up build artifacts"
	@echo "  docs      - Build documentation"

# Set up development environment
setup:
	python setup_dev.py

# Install dependencies
install:
	pip install -r requirements-dev.txt
	pip install -e .

# Run tests
test:
	pytest tests/ -v --cov=autoninja --cov-report=html --cov-report=term

# Run linting
lint:
	pylint autoninja/
	mypy autoninja/
	flake8 autoninja/
	bandit -r autoninja/

# Format code
format:
	black autoninja/ tests/
	isort autoninja/ tests/

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build documentation
docs:
	cd docs && make html

# Run security checks
security:
	bandit -r autoninja/
	safety check

# Run all quality checks
quality: lint security test

# Install pre-commit hooks
pre-commit:
	pre-commit install
	pre-commit run --all-files