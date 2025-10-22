# AutoNinja Product Overview

AutoNinja is a serverless multi-agent system that generates production-ready AWS Bedrock Agents from natural language descriptions. It's a "meta-agent" - an AI system that creates other AI agents.

## Core Functionality

Users provide a simple request like "Build a customer service agent" and receive a fully deployed Bedrock Agent with:
- Lambda functions with production-ready code
- CloudFormation infrastructure templates
- OpenAPI schemas for action groups
- Complete agent configuration
- Deployed agent ARN ready for use

## Architecture Pattern

Uses a supervisor-collaborator pattern with 6 specialized Bedrock Agents:
- **Supervisor Agent**: Orchestrates workflow, generates job IDs, delegates tasks (deployed to Bedrock AgentCore Runtime)
- **Requirements Analyst**: Extracts structured specifications from user input
- **Code Generator**: Produces Lambda handlers, agent configs, and OpenAPI schemas
- **Solution Architect**: Designs AWS architecture and CloudFormation IaC
- **Quality Validator**: Scans for quality, security, and compliance issues
- **Deployment Manager**: Deploys via CloudFormation and tests the agent

## Key Features

- Fully autonomous execution from request to deployed agent
- Complete audit trail: Every prompt/response saved to DynamoDB, all artifacts to S3
- Serverless and scalable: Pay-per-use (~$0.20/job), auto-scales to 100+ concurrent jobs
- Production-ready output: Least-privilege IAM, KMS encryption, CloudWatch logging
- Reduces agent development time from days to minutes

## Job Tracking

Every run gets a unique job ID (e.g., `job-friend-20251013-143022`) that tracks all inference records, artifacts, and logs end-to-end.
