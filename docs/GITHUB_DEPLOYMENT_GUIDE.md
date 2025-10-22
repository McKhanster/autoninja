# GitHub-Based Deployment Guide

This guide explains how to deploy AutoNinja using GitHub as the source repository, replacing the deprecated AWS CodeCommit service.

## Overview

Since AWS CodeCommit is no longer available for new customers, we use GitHub as the Git repository with the following deployment approach:

- **Frontend**: AWS Amplify connected to GitHub (automatic deployments)
- **Backend**: GitHub Actions for CloudFormation deployments
- **CI/CD**: GitHub Actions workflows

## Prerequisites

1. **GitHub Account**: Create a GitHub account if you don't have one
2. **AWS Account**: AWS account with appropriate permissions
3. **AWS CLI**: Installed and configured
4. **Git**: Installed locally
5. **Node.js 18+**: For frontend development
6. **Python 3.12**: For backend development

## Step 1: Create GitHub Repository

### 1.1 Create Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `autoninja-bedrock-agents`
3. Description: "AutoNinja multi-agent Bedrock system"
4. Choose Private or Public
5. Do NOT initialize with README (we already have one)
6. Click "Create repository"

### 1.2 Push Code to GitHub

```bash
# If not already initialized
git init

# Add GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/autoninja-bedrock-agents.git

# Verify current branch
git branch

# If not on main, create and switch to main
git checkout -b main

# Add all files
git add .

# Commit
git commit -m "Initial commit: AutoNinja deployment infrastructure"

# Push to GitHub
git push -u origin main
```

## Step 2: Configure AWS Credentials for GitHub Actions

### 2.1 Create IAM User for GitHub Actions

```bash
# Set environment variables
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356

# Create IAM user
aws iam create-user --user-name github-actions-autoninja

# Attach necessary policies (adjust as needed for least privilege)
aws iam attach-user-policy \
  --user-name github-actions-autoninja \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# Create access key
aws iam create-access-key --user-name github-actions-autoninja
```

Save the `AccessKeyId` and `SecretAccessKey` from the output.

### 2.2 Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:
   - Name: `AWS_ACCESS_KEY_ID`, Value: (from previous step)
   - Name: `AWS_SECRET_ACCESS_KEY`, Value: (from previous step)
   - Name: `DASHBOARD_PASSWORD`, Value: (choose a secure password)

## Step 3: Deploy Frontend Infrastructure

### 3.1 Deploy Amplify Stack

```bash
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356
export DASHBOARD_PASSWORD=your-secure-password

./ops/scripts/deploy_frontend_infrastructure.sh
```

This creates the AWS Amplify app but doesn't connect it to GitHub yet.

### 3.2 Connect Amplify to GitHub

#### Option A: Using AWS Console (Recommended)

1. Go to AWS Amplify Console: https://console.aws.amazon.com/amplify/
2. Select your app (autoninja-frontend-production)
3. Click **Set up CI/CD**
4. Choose **GitHub** as the repository service
5. Authorize AWS Amplify to access your GitHub account
6. Select repository: `YOUR_USERNAME/autoninja-bedrock-agents`
7. Select branch: `main`
8. Configure build settings:
   - Build command: `npm run build`
   - Base directory: `frontend`
   - Build output directory: `build`
9. Click **Save and deploy**

#### Option B: Using AWS CLI

```bash
# Get Amplify App ID
AMPLIFY_APP_ID=$(aws cloudformation describe-stacks \
  --stack-name autoninja-frontend-infrastructure \
  --region us-east-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppId`].OutputValue' \
  --output text)

# Create GitHub connection (requires GitHub personal access token)
aws amplify create-branch \
  --app-id $AMPLIFY_APP_ID \
  --branch-name main \
  --region us-east-2
```

### 3.3 Configure Environment Variables in Amplify

1. In Amplify Console, go to **App settings** → **Environment variables**
2. Add:
   - Key: `REACT_APP_DASHBOARD_PASSWORD`, Value: (your password)
   - Key: `NODE_ENV`, Value: `production`

### 3.4 Verify Frontend Deployment

1. Wait for Amplify build to complete
2. Get the Amplify URL:

```bash
aws cloudformation describe-stacks \
  --stack-name autoninja-frontend-infrastructure \
  --region us-east-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppUrl`].OutputValue' \
  --output text
```

3. Open the URL in your browser
4. Test login with your password

## Step 4: Configure Backend Deployment

### 4.1 Verify GitHub Actions Workflows

The repository includes two GitHub Actions workflows:

- `.github/workflows/deploy-backend.yml` - Deploys Lambda functions and CloudFormation
- `.github/workflows/deploy-frontend.yml` - Builds and deploys frontend

### 4.2 Test Backend Deployment

Push a change to trigger the workflow:

```bash
# Make a small change
echo "# Deployment test" >> README.md

# Commit and push
git add README.md
git commit -m "Test: Trigger backend deployment"
git push origin main
```

### 4.3 Monitor Deployment

1. Go to your GitHub repository
2. Click **Actions** tab
3. Watch the workflow execution
4. Check for any errors

## Step 5: Deploy Backend Infrastructure

### 5.1 Manual Deployment (First Time)

```bash
export AWS_REGION=us-east-2
export AWS_PROFILE=AdministratorAccess-784327326356

# Package Lambda layer
./scripts/package_lambda_layer.sh

# Upload schemas
./scripts/upload_schemas.sh

# Deploy nested stacks
export AUTO_DEPLOY=true
./scripts/deploy_nested_stacks.sh
```

### 5.2 Verify Backend Deployment

```bash
# List CloudFormation stacks
aws cloudformation list-stacks \
  --region us-east-2 \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName, `autoninja`)].StackName'
```

## Step 6: Test End-to-End Workflow

### 6.1 Make a Frontend Change

```bash
# Edit a frontend file
echo "// Test change" >> frontend/src/App.js

# Commit and push
git add frontend/src/App.js
git commit -m "Test: Frontend deployment"
git push origin main
```

### 6.2 Verify Automatic Deployment

1. Check Amplify Console for build progress
2. Wait for build to complete
3. Refresh your frontend URL
4. Verify changes are live

### 6.3 Make a Backend Change

```bash
# Edit a Lambda function
echo "# Test change" >> lambda/requirements-analyst/handler.py

# Commit and push
git add lambda/requirements-analyst/handler.py
git commit -m "Test: Backend deployment"
git push origin main
```

### 6.4 Verify GitHub Actions Deployment

1. Go to GitHub Actions tab
2. Watch the deploy-backend workflow
3. Verify successful completion

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         GitHub                              │
│                    (Source Repository)                      │
└────────────┬────────────────────────┬──────────────────────┘
             │                        │
             │ Push Event             │ Push Event
             ▼                        ▼
┌────────────────────────┐  ┌──────────────────────────────┐
│   AWS Amplify          │  │   GitHub Actions             │
│   (Frontend CI/CD)     │  │   (Backend CI/CD)            │
└────────────┬───────────┘  └──────────┬───────────────────┘
             │                         │
             │ Deploy                  │ Deploy
             ▼                         ▼
┌────────────────────────┐  ┌──────────────────────────────┐
│   Amplify Hosting      │  │   CloudFormation             │
│   (React Frontend)     │  │   (Lambda + Infrastructure)  │
└────────────────────────┘  └──────────────────────────────┘
```

## Troubleshooting

### Issue: Amplify build fails

**Solution:**
1. Check build logs in Amplify Console
2. Verify `buildspec.yml` is correct
3. Check environment variables are set
4. Ensure Node.js version matches (18.x)

### Issue: GitHub Actions fails

**Solution:**
1. Check workflow logs in GitHub Actions tab
2. Verify AWS credentials are correct
3. Check IAM permissions
4. Ensure all required secrets are set

### Issue: Cannot connect Amplify to GitHub

**Solution:**
1. Revoke and re-authorize GitHub access in Amplify
2. Check GitHub personal access token permissions
3. Ensure repository is accessible

### Issue: Backend deployment fails

**Solution:**
1. Check CloudFormation events in AWS Console
2. Verify S3 bucket exists for artifacts
3. Check Lambda function permissions
4. Review CloudWatch logs

## Cost Optimization

### Amplify Hosting Costs

- Build minutes: ~$0.01/minute
- Hosting: ~$0.15/GB served
- Free tier: 1000 build minutes/month, 15GB served/month

### GitHub Actions Costs

- Free tier: 2000 minutes/month for private repos
- Unlimited for public repos

### Estimated Monthly Cost

- Amplify: $1-2/month (within free tier initially)
- GitHub Actions: $0 (within free tier)
- Backend infrastructure: ~$5-10/month (Lambda, DynamoDB, S3)

**Total: ~$6-12/month**

## Security Best Practices

1. **Use least-privilege IAM policies** for GitHub Actions user
2. **Rotate AWS access keys** regularly
3. **Use GitHub secrets** for sensitive data
4. **Enable branch protection** on main branch
5. **Require pull request reviews** before merging
6. **Enable AWS CloudTrail** for audit logging
7. **Use strong passwords** for dashboard authentication

## Next Steps

1. ✅ Set up GitHub repository
2. ✅ Configure AWS credentials
3. ✅ Deploy frontend infrastructure
4. ✅ Connect Amplify to GitHub
5. ✅ Configure GitHub Actions
6. ✅ Deploy backend infrastructure
7. ✅ Test end-to-end workflow
8. 📝 Set up monitoring and alerts
9. 📝 Configure custom domain (optional)
10. 📝 Set up staging environment (optional)

## Additional Resources

- [AWS Amplify Documentation](https://docs.aws.amazon.com/amplify/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
