# Design Document

## Overview

This design document outlines the complete AWS deployment infrastructure for AutoNinja, including a React-based frontend dashboard, AWS CodeCommit repository migration, and CI/CD pipeline implementation. The solution prioritizes simplicity, cost-effectiveness, and rapid deployment in the us-east-2 region.

### Design Goals

1. **Simplicity**: Minimal dependencies, straightforward architecture
2. **Cost-Effectiveness**: Use cheapest AWS services (Amplify Hosting, CodeCommit, CodePipeline)
3. **Functionality**: Working authentication and deployment automation
4. **Speed**: Rapid implementation with Create React App and CloudFormation
5. **AWS-Native**: All resources hosted on AWS infrastructure

## Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud (us-east-2)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐         ┌──────────────────┐                    │
│  │   CodeCommit     │────────▶│   CodePipeline   │                    │
│  │   Repository     │  Push   │   Orchestrator   │                    │
│  └──────────────────┘         └────────┬─────────┘                    │
│                                         │                               │
│                                         ▼                               │
│                              ┌──────────────────┐                      │
│                              │   CodeBuild      │                      │
│                              │   Projects       │                      │
│                              └────────┬─────────┘                      │
│                                       │                                 │
│                    ┌──────────────────┼──────────────────┐            │
│                    ▼                  ▼                   ▼            │
│         ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐    │
│         │  Frontend Build  │  │Backend Build │  │  CloudFormation│    │
│         │  (React App)     │  │(Lambda Pkgs) │  │  Deployment   │    │
│         └────────┬─────────┘  └──────┬───────┘  └──────┬────────┘    │
│                  │                    │                  │             │
│                  ▼                    ▼                  ▼             │
│         ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐    │
│         │  AWS Amplify     │  │  S3 Bucket   │  │ CloudFormation│    │
│         │  Hosting         │  │  (Artifacts) │  │    Stacks     │    │
│         └──────────────────┘  └──────────────┘  └──────────────┘    │
│                  │                                                     │
│                  ▼                                                     │
│         ┌──────────────────┐                                          │
│         │   End Users      │                                          │
│         │   (Browser)      │                                          │
│         └──────────────────┘                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```


### Component Architecture

#### 1. Frontend Application (React Dashboard)

**Technology Stack:**
- React 18.x (using Create React App)
- JSX (not TypeScript for simplicity)
- Minimal CSS (inline styles or single CSS file)
- No state management library (use React hooks)
- No routing library (single page application)

**Component Structure:**
```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── App.jsx              # Main application component
│   ├── LoginPage.jsx        # Password authentication page
│   ├── Dashboard.jsx        # Main dashboard after login
│   ├── index.jsx            # Entry point
│   └── index.css            # Minimal global styles
├── package.json
├── .gitignore
└── README.md
```

**Authentication Flow:**
1. User lands on LoginPage with password input
2. Password validated against environment variable
3. On success, set authentication state and show Dashboard
4. Use sessionStorage to persist auth state
5. No backend authentication service (client-side only for simplicity)

#### 2. AWS Amplify Hosting

**Why Amplify:**
- Cheapest option for static hosting ($0.15/GB served, $0.01/build minute)
- Free tier: 1000 build minutes/month, 15GB served/month
- Integrated CI/CD with Git
- Automatic HTTPS
- No need for CloudFront or S3 bucket policies

**Configuration:**
- Manual deployment (not connected to Git initially)
- Build settings defined in amplify.yml
- Environment variables for password
- Custom domain support (optional)

**Alternative (if Amplify unsuitable):**
- S3 Static Website Hosting + CloudFront
- Cost: ~$0.50/month (S3) + $0.085/GB (CloudFront)
- More complex setup but more control

#### 3. AWS CodeCommit Repository

**Repository Structure:**
```
autoninja-bedrock-agents/
├── frontend/                    # React application
├── lambda/                      # Lambda functions
├── shared/                      # Shared libraries
├── infrastructure/              # CloudFormation templates
│   └── cloudformation/
│       ├── autoninja-main.yaml
│       └── stacks/
│           ├── frontend-infrastructure.yaml  # NEW
│           ├── cicd-pipeline.yaml           # NEW
│           └── codecommit-repository.yaml   # NEW
├── buildspec.yml               # Frontend build spec
├── buildspec-backend.yml       # Backend build spec
└── README.md
```

**Access Methods:**
- HTTPS (with Git credentials)
- SSH (with SSH keys)
- IAM roles for CodePipeline

#### 4. CI/CD Pipeline Architecture

**Pipeline Stages:**

1. **Source Stage**
   - Trigger: Push to CodeCommit repository
   - Action: CodeCommit source action
   - Output: Source artifact

2. **Build Stage (Parallel)**
   - **Frontend Build Project**
     - Runtime: Node.js 18
     - Buildspec: buildspec.yml
     - Actions: npm install, npm run build
     - Output: Build artifact (build/ directory)
   
   - **Backend Build Project**
     - Runtime: Python 3.12
     - Buildspec: buildspec-backend.yml
     - Actions: Package Lambda functions, upload to S3
     - Output: Lambda deployment packages

3. **Deploy Stage (Sequential)**
   - **Frontend Deploy Action**
     - Deploy build artifact to Amplify
     - Use Amplify CLI or S3 sync
   
   - **Backend Deploy Action**
     - Execute CloudFormation change sets
     - Update Lambda functions
     - Update Bedrock agents if needed

**Pipeline Diagram:**
```
┌──────────────┐
│   Source     │  CodeCommit Push
│   Stage      │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────┐
│      Build Stage (Parallel)      │
├──────────────┬───────────────────┤
│  Frontend    │    Backend        │
│  Build       │    Build          │
│  (Node.js)   │    (Python)       │
└──────┬───────┴───────┬───────────┘
       │               │
       ▼               ▼
┌──────────────────────────────────┐
│     Deploy Stage (Sequential)    │
├──────────────┬───────────────────┤
│  Amplify     │  CloudFormation   │
│  Deploy      │  Deploy           │
└──────────────┴───────────────────┘
```


## Components and Interfaces

### 1. Frontend Application Components

#### LoginPage Component
```jsx
// LoginPage.jsx
// Props: onLogin (callback function)
// State: password (string), error (string)
// Methods: handleSubmit(), validatePassword()
```

**Interface:**
- Input: Password string
- Output: Authentication success/failure
- Side effects: Set sessionStorage auth token

#### Dashboard Component
```jsx
// Dashboard.jsx
// Props: onLogout (callback function)
// State: None (stateless for MVP)
// Methods: handleLogout()
```

**Interface:**
- Input: None (authenticated user)
- Output: Dashboard UI
- Side effects: None

#### App Component
```jsx
// App.jsx
// State: isAuthenticated (boolean)
// Methods: handleLogin(), handleLogout(), checkAuth()
```

**Interface:**
- Manages authentication state
- Routes between LoginPage and Dashboard
- Persists auth state in sessionStorage

### 2. CloudFormation Stack Interfaces

#### Frontend Infrastructure Stack

**Inputs (Parameters):**
- Environment (production/staging/development)
- BranchName (Git branch for deployment)
- DashboardPassword (password for authentication)

**Resources Created:**
- AWS::Amplify::App
- AWS::Amplify::Branch
- AWS::IAM::Role (for Amplify)

**Outputs:**
- AmplifyAppId
- AmplifyAppUrl
- AmplifyBranchName

#### CodeCommit Repository Stack

**Inputs (Parameters):**
- RepositoryName
- RepositoryDescription

**Resources Created:**
- AWS::CodeCommit::Repository
- AWS::IAM::Policy (for repository access)

**Outputs:**
- RepositoryArn
- RepositoryCloneUrlHttp
- RepositoryCloneUrlSsh
- RepositoryName

#### CI/CD Pipeline Stack

**Inputs (Parameters):**
- Environment
- CodeCommitRepositoryName
- CodeCommitRepositoryArn
- AmplifyAppId
- ArtifactsBucketName

**Resources Created:**
- AWS::CodePipeline::Pipeline
- AWS::CodeBuild::Project (frontend)
- AWS::CodeBuild::Project (backend)
- AWS::IAM::Role (for CodePipeline)
- AWS::IAM::Role (for CodeBuild)
- AWS::S3::Bucket (pipeline artifacts)

**Outputs:**
- PipelineName
- PipelineArn
- FrontendBuildProjectName
- BackendBuildProjectName

### 3. Build Specification Interfaces

#### Frontend Buildspec (buildspec.yml)

**Phases:**
1. **install**: Install Node.js dependencies
2. **pre_build**: Run linting (optional)
3. **build**: Execute `npm run build`
4. **post_build**: Prepare artifacts

**Artifacts:**
- Base directory: `frontend/build`
- Files: `**/*`

**Environment Variables:**
- REACT_APP_API_ENDPOINT (optional)
- NODE_ENV=production

#### Backend Buildspec (buildspec-backend.yml)

**Phases:**
1. **install**: Install Python dependencies
2. **pre_build**: Package Lambda layer
3. **build**: Package Lambda functions
4. **post_build**: Upload to S3

**Artifacts:**
- Lambda function ZIP files
- CloudFormation templates

**Environment Variables:**
- AWS_REGION=us-east-2
- DEPLOYMENT_BUCKET


## Data Models

### 1. Authentication State Model

```javascript
// Stored in sessionStorage
{
  "isAuthenticated": boolean,
  "timestamp": number,        // Unix timestamp
  "expiresAt": number        // Unix timestamp (optional)
}
```

### 2. CloudFormation Stack Parameters Model

```yaml
# Frontend Infrastructure Parameters
Environment: String (production|staging|development)
BranchName: String (default: main)
DashboardPassword: String (NoEcho: true)

# CodeCommit Repository Parameters
RepositoryName: String (default: autoninja-bedrock-agents)
RepositoryDescription: String

# CI/CD Pipeline Parameters
CodeCommitRepositoryName: String
CodeCommitRepositoryArn: String
AmplifyAppId: String
ArtifactsBucketName: String
```

### 3. Build Artifact Structure

```
# Frontend Build Artifact
frontend/build/
├── index.html
├── static/
│   ├── css/
│   │   └── main.[hash].css
│   └── js/
│       ├── main.[hash].js
│       └── [chunk].[hash].js
├── manifest.json
└── asset-manifest.json

# Backend Build Artifacts
build/
├── lambda/
│   ├── requirements-analyst.zip
│   ├── code-generator.zip
│   ├── solution-architect.zip
│   ├── quality-validator.zip
│   └── deployment-manager.zip
└── layers/
    └── autoninja-shared-layer.zip
```

### 4. Pipeline Artifact Model

```json
{
  "sourceArtifact": {
    "name": "SourceOutput",
    "location": "s3://pipeline-artifacts-bucket/source/",
    "files": ["**/*"]
  },
  "frontendBuildArtifact": {
    "name": "FrontendBuildOutput",
    "location": "s3://pipeline-artifacts-bucket/frontend-build/",
    "files": ["frontend/build/**/*"]
  },
  "backendBuildArtifact": {
    "name": "BackendBuildOutput",
    "location": "s3://pipeline-artifacts-bucket/backend-build/",
    "files": ["build/**/*"]
  }
}
```

## Error Handling

### 1. Frontend Error Handling

**Authentication Errors:**
- Invalid password: Display error message "Invalid password. Please try again."
- Empty password: Display error message "Password is required."
- Session expired: Redirect to login page

**Network Errors:**
- API unavailable: Display error message "Service temporarily unavailable."
- Timeout: Display error message "Request timed out. Please try again."

**Error Display Strategy:**
- Use inline error messages below input fields
- Use toast notifications for system errors
- Log errors to browser console for debugging

### 2. Build Error Handling

**Frontend Build Errors:**
- Dependency installation failure: Fail build with clear error message
- Build compilation errors: Display compilation errors in CodeBuild logs
- Artifact upload failure: Retry up to 3 times

**Backend Build Errors:**
- Lambda packaging failure: Fail build and notify via CloudWatch
- S3 upload failure: Retry with exponential backoff
- CloudFormation validation errors: Display validation errors in logs

**Error Recovery:**
- CodeBuild: Automatic retry on transient failures
- CodePipeline: Manual retry option in console
- CloudFormation: Automatic rollback on stack update failure

### 3. Deployment Error Handling

**Amplify Deployment Errors:**
- Build failure: Display build logs in Amplify console
- Deployment timeout: Automatic retry after 5 minutes
- Invalid configuration: Fail deployment with validation error

**CloudFormation Deployment Errors:**
- Stack update failure: Automatic rollback to previous version
- Resource creation failure: Display error in CloudFormation events
- Permission errors: Fail with IAM permission error message

**Monitoring and Alerts:**
- CloudWatch alarms for build failures
- SNS notifications for deployment failures (optional)
- CloudWatch Logs for detailed error investigation


## Testing Strategy

### 1. Frontend Testing

**Unit Testing (Optional for MVP):**
- Test authentication logic
- Test component rendering
- Use Jest and React Testing Library

**Manual Testing:**
- Test login flow with correct password
- Test login flow with incorrect password
- Test dashboard display after authentication
- Test logout functionality
- Test session persistence across page refreshes
- Test responsive design on mobile and desktop

**Browser Compatibility:**
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

### 2. Infrastructure Testing

**CloudFormation Template Validation:**
```bash
# Validate frontend infrastructure template
aws cloudformation validate-template \
  --template-body file://infrastructure/cloudformation/stacks/frontend-infrastructure.yaml

# Validate CodeCommit repository template
aws cloudformation validate-template \
  --template-body file://infrastructure/cloudformation/stacks/codecommit-repository.yaml

# Validate CI/CD pipeline template
aws cloudformation validate-template \
  --template-body file://infrastructure/cloudformation/stacks/cicd-pipeline.yaml
```

**Stack Deployment Testing:**
1. Deploy to development environment first
2. Verify all resources created successfully
3. Test resource connectivity and permissions
4. Verify outputs are correct
5. Test stack updates and rollbacks
6. Clean up development resources

### 3. CI/CD Pipeline Testing

**Build Testing:**
```bash
# Test frontend build locally
cd frontend
npm install
npm run build
# Verify build/ directory created

# Test backend build locally
./scripts/package_lambda_layer.sh
# Verify build/ directory contains ZIP files
```

**Pipeline Testing:**
1. Push test commit to CodeCommit
2. Verify pipeline triggers automatically
3. Monitor build logs in CodeBuild
4. Verify artifacts uploaded to S3
5. Verify deployment to Amplify
6. Test deployed application

**Integration Testing:**
- End-to-end test: Code push → Build → Deploy → Verify
- Test pipeline failure scenarios
- Test manual approval stages (if added)
- Test rollback on deployment failure

### 4. Security Testing

**IAM Permission Testing:**
- Verify least-privilege access for all roles
- Test that unauthorized actions are denied
- Verify cross-account access is blocked

**Authentication Testing:**
- Test password validation logic
- Test session expiration
- Test logout clears session data

**Network Security Testing:**
- Verify HTTPS enforcement
- Test CORS configuration (if applicable)
- Verify no sensitive data in client-side code

## Implementation Phases

### Phase 1: Git Branch and Frontend Setup
**Duration:** 1-2 hours

1. Create deployment-infrastructure branch
2. Initialize React application with Create React App
3. Implement LoginPage component
4. Implement Dashboard component
5. Implement App component with authentication logic
6. Test locally with `npm start`

**Deliverables:**
- Working React application
- Login and dashboard functionality
- Local testing complete

### Phase 2: Frontend Infrastructure
**Duration:** 1-2 hours

1. Create frontend-infrastructure.yaml CloudFormation template
2. Define Amplify App resource
3. Define IAM roles and policies
4. Add stack parameters and outputs
5. Validate template syntax
6. Deploy stack to AWS
7. Manual deploy of React app to Amplify

**Deliverables:**
- CloudFormation template for frontend
- Deployed Amplify application
- Accessible frontend URL

### Phase 3: CodeCommit Repository Migration
**Duration:** 1 hour

1. Create codecommit-repository.yaml CloudFormation template
2. Deploy CodeCommit repository stack
3. Configure Git credentials for HTTPS access
4. Add CodeCommit as remote repository
5. Push code to CodeCommit
6. Verify repository contents

**Deliverables:**
- CodeCommit repository created
- Code migrated to CodeCommit
- Git remote configured

### Phase 4: CI/CD Pipeline Implementation
**Duration:** 2-3 hours

1. Create buildspec.yml for frontend builds
2. Create buildspec-backend.yml for backend builds
3. Create cicd-pipeline.yaml CloudFormation template
4. Define CodePipeline resource with stages
5. Define CodeBuild projects
6. Define IAM roles and policies
7. Deploy pipeline stack
8. Test pipeline with code push

**Deliverables:**
- Working CI/CD pipeline
- Automated frontend deployments
- Automated backend deployments

### Phase 5: Testing and Documentation
**Duration:** 1-2 hours

1. End-to-end testing of entire workflow
2. Update README with deployment instructions
3. Document pipeline usage
4. Document troubleshooting steps
5. Create deployment runbook

**Deliverables:**
- Tested and verified system
- Complete documentation
- Deployment runbook

## Cost Estimation

### Monthly Costs (Estimated)

**AWS Amplify Hosting:**
- Build minutes: 100 minutes/month × $0.01 = $1.00
- Data transfer: 5GB/month × $0.15 = $0.75
- **Subtotal: $1.75/month** (within free tier initially)

**AWS CodeCommit:**
- 5 active users: Free (up to 5 users)
- Storage: 1GB: Free (up to 50GB)
- **Subtotal: $0.00/month**

**AWS CodePipeline:**
- 1 active pipeline: $1.00/month (first pipeline free)
- **Subtotal: $0.00/month** (first pipeline free)

**AWS CodeBuild:**
- Build minutes: 100 minutes/month × $0.005 = $0.50
- **Subtotal: $0.50/month** (within free tier initially)

**S3 Storage (Pipeline Artifacts):**
- Storage: 1GB × $0.023 = $0.02
- Requests: Minimal
- **Subtotal: $0.05/month**

**Total Estimated Monthly Cost: $2.30/month**
(Most costs covered by AWS Free Tier for first 12 months)

### One-Time Costs

- Development time: 8-10 hours
- Testing time: 2-3 hours
- Documentation time: 1-2 hours

**Total Implementation Time: 11-15 hours**

## Security Considerations

### 1. Authentication and Authorization

- Frontend password stored as Amplify environment variable
- Use strong password (minimum 12 characters)
- Consider adding password hashing in future iteration
- Session timeout after 24 hours
- No sensitive data in localStorage or sessionStorage

### 2. IAM Permissions

- All IAM roles follow least-privilege principle
- CodePipeline role: Only access to required resources
- CodeBuild role: Only access to S3 and CloudFormation
- Amplify role: Only access to deployment resources
- No wildcard permissions in production

### 3. Data Protection

- All data in transit encrypted with TLS 1.2+
- S3 buckets encrypted at rest with KMS
- CodeCommit repository encrypted at rest
- No secrets in source code (use environment variables)
- Sensitive parameters use NoEcho in CloudFormation

### 4. Network Security

- Amplify app uses HTTPS only
- S3 buckets block public access
- CodeCommit requires IAM authentication
- VPC endpoints for private communication (optional)

### 5. Audit and Compliance

- CloudTrail logging enabled for all API calls
- CloudWatch Logs for build and deployment logs
- S3 access logging for artifact buckets
- Regular security audits of IAM policies

## Monitoring and Observability

### 1. CloudWatch Metrics

**Amplify Metrics:**
- Build success/failure rate
- Build duration
- Deployment duration
- HTTP 4xx/5xx error rates

**CodePipeline Metrics:**
- Pipeline execution success rate
- Stage duration
- Failed executions

**CodeBuild Metrics:**
- Build success rate
- Build duration
- Failed builds

### 2. CloudWatch Alarms

**Critical Alarms:**
- Pipeline execution failure
- Build failure rate > 50%
- Amplify deployment failure

**Warning Alarms:**
- Build duration > 10 minutes
- Deployment duration > 5 minutes

### 3. CloudWatch Logs

**Log Groups:**
- `/aws/amplify/[app-id]` - Amplify build logs
- `/aws/codebuild/[project-name]` - CodeBuild logs
- `/aws/codepipeline/[pipeline-name]` - Pipeline logs

**Log Retention:**
- Development: 7 days
- Production: 30 days

### 4. Dashboards

**Deployment Dashboard:**
- Pipeline execution status
- Build success rate
- Deployment frequency
- Average build duration

## Disaster Recovery

### 1. Backup Strategy

**Code Repository:**
- CodeCommit automatic backups
- Mirror to GitHub (optional)
- Daily snapshots

**Infrastructure:**
- CloudFormation templates in version control
- Infrastructure as Code ensures reproducibility
- Stack exports for cross-stack references

### 2. Recovery Procedures

**Frontend Recovery:**
1. Redeploy from last successful build
2. Rollback Amplify deployment
3. Restore from CloudFormation stack

**Pipeline Recovery:**
1. Retry failed pipeline execution
2. Redeploy pipeline stack
3. Restore from CloudFormation template

**Repository Recovery:**
1. Restore from CodeCommit backup
2. Push from local Git repository
3. Restore from GitHub mirror

### 3. Recovery Time Objectives

- Frontend recovery: < 15 minutes
- Pipeline recovery: < 30 minutes
- Full system recovery: < 1 hour

## Future Enhancements

### Short-Term (Next 3 months)

1. Add user management with AWS Cognito
2. Implement API Gateway for backend communication
3. Add monitoring dashboard in frontend
4. Implement automated testing in pipeline
5. Add staging environment

### Medium-Term (3-6 months)

1. Multi-region deployment
2. Blue-green deployment strategy
3. Automated rollback on errors
4. Performance monitoring and optimization
5. Cost optimization analysis

### Long-Term (6-12 months)

1. Multi-tenant support
2. Advanced analytics and reporting
3. Integration with third-party services
4. Mobile application
5. Enterprise features (SSO, RBAC)
