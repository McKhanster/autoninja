# Deployment Scripts

This directory contains deployment scripts for AutoNinja AWS infrastructure.

## Prerequisites

- AWS CLI configured with appropriate credentials
- AWS Profile: `AdministratorAccess-784327326356`
- AWS Region: `us-east-2`
- GitHub repository (CodeCommit not available in this account)

## Environment Variables

Set these before running deployment scripts:

```bash
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356
export AWS_ACCOUNT_ID=784327326356
export DASHBOARD_PASSWORD=your-secure-password  # Required for frontend
export GITHUB_OWNER=your-github-username        # Optional for CI/CD
export GITHUB_REPO=autoninja-bedrock-agents     # Optional for CI/CD
export GITHUB_TOKEN=your-github-token           # Optional for CI/CD
```

## Deployment Scripts

### Individual Stack Deployment

#### 1. Frontend Infrastructure
Deploys AWS Amplify hosting for the AutoNinja dashboard.

```bash
DASHBOARD_PASSWORD=your-secure-password ./ops/scripts/deploy_frontend_infrastructure.sh
```

**Outputs:**
- Amplify App ID
- Amplify App URL
- Branch URL

#### 2. CI/CD Pipeline
Deploys CodePipeline and CodeBuild for automated deployments.

**Note:** Requires frontend infrastructure to be deployed first.

```bash
./ops/scripts/deploy_cicd_pipeline.sh
```

**Outputs:**
- Pipeline Name
- Pipeline ARN
- Build Project Names

### Deploy All Infrastructure

Deploy all stacks in the correct order:

```bash
DASHBOARD_PASSWORD=your-secure-password ./ops/scripts/deploy_all.sh
```

This will deploy:
1. Frontend Infrastructure (Amplify)
2. CI/CD Pipeline (CodePipeline + CodeBuild)

### Cleanup

Remove all deployed infrastructure:

```bash
./ops/scripts/cleanup_all.sh
```

**Warning:** This will delete all resources. You'll be prompted to confirm.

## Stack Dependencies

```
Frontend Infrastructure (autoninja-frontend-infrastructure)
    ↓
CI/CD Pipeline (autoninja-cicd-pipeline)
```

The CI/CD pipeline depends on the frontend infrastructure for the Amplify App ID.

## GitHub Integration

Since CodeCommit is not available in this AWS account, the CI/CD pipeline uses GitHub as the source repository.

### Setup GitHub Connection

1. **Option A: Manual Setup (Recommended)**
   - Deploy the pipeline stack
   - Go to AWS CodePipeline console
   - Update the source stage to connect to GitHub
   - Authorize AWS to access your GitHub repository

2. **Option B: Using GitHub Token**
   - Set `GITHUB_TOKEN` environment variable
   - The pipeline will attempt to use the token for authentication

### GitHub Repository Structure

Ensure your GitHub repository has:
- `buildspec-backend.yml` - CodeBuild spec for backend
- `buildspec-frontend.yml` - CodeBuild spec for frontend
- Backend code in root or specified directory
- Frontend code in `frontend/` directory

## Troubleshooting

### Stack Already Exists
If a stack is in `ROLLBACK_COMPLETE` state:
```bash
aws cloudformation delete-stack --stack-name <stack-name> --region us-east-2
aws cloudformation wait stack-delete-complete --stack-name <stack-name> --region us-east-2
```

### View Stack Events
```bash
aws cloudformation describe-stack-events \
  --stack-name <stack-name> \
  --region us-east-2 \
  --max-items 20
```

### View Stack Outputs
```bash
aws cloudformation describe-stacks \
  --stack-name <stack-name> \
  --region us-east-2 \
  --query 'Stacks[0].Outputs'
```

## Notes

- All scripts are idempotent and can be run multiple times
- Scripts use CloudFormation change sets for safe updates
- IAM capabilities are automatically granted where needed
- All resources are tagged with Environment and Application tags
