# Task 11 Execution Guide: Supervisor Agent with AgentCore Runtime

## Overview

This guide provides step-by-step instructions for executing Task 11, which integrates Amazon Bedrock AgentCore Runtime for the supervisor agent.

## Critical Rules

### Before Starting ANY Sub-Task

1. ✅ Read ALL spec documents:
   - `.kiro/specs/autoninja-bedrock-agents/requirements.md`
   - `.kiro/specs/autoninja-bedrock-agents/design.md`
   - `.kiro/specs/autoninja-bedrock-agents/tasks.md`

2. ✅ Audit existing code for compatibility

3. ✅ Use AWS Documentation MCP for non-simple errors

4. ❌ NEVER mark a task complete if errors exist

## Task 11 Sub-Tasks

### 11.0: Read Spec Documents and Audit Code

**Purpose:** Understand the full context and identify compatibility issues

**Steps:**
1. Read `requirements.md` - Focus on Requirements 1 and 2
2. Read `design.md` - Focus on Component 1 (Supervisor Agent)
3. Read `tasks.md` - Focus on Task 11 details
4. Read `infrastructure/cloudformation/autoninja-complete.yaml`
5. Identify existing supervisor agent resources:
   - Supervisor Bedrock Agent (from task 2.11)
   - Supervisor agent alias (from task 2.12)
   - Agent collaborator associations (from task 2.13)
6. Document what needs to be removed/updated

**Completion Criteria:**
- [ ] All spec documents read
- [ ] Existing supervisor resources identified
- [ ] Compatibility issues documented

### 11.1: Design Supervisor Orchestration Logic

**Purpose:** Design the sequential orchestration workflow

**Steps:**
1. Read spec documents (requirements.md, design.md, tasks.md)
2. Design job_name generation logic
3. Design sequential workflow:
   - Requirements Analyst → Code Generator → Solution Architect → Quality Validator → Deployment Manager
4. Design error handling and retry logic
5. Design CloudWatch logging strategy
6. Document collaboration instructions for each collaborator

**Completion Criteria:**
- [ ] Orchestration logic designed
- [ ] Workflow documented
- [ ] Error handling planned

### 11.2: Implement Supervisor Agent Code

**Purpose:** Write the AgentCore Runtime supervisor agent

**Steps:**
1. Read spec documents
2. Review existing supervisor in CloudFormation
3. Install dependencies:
   ```bash
   pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
   ```
4. Create `lambda/supervisor-agentcore/supervisor_agent.py`
5. Implement using code example from design.md
6. Implement helper functions:
   - `generate_job_name(user_request)`
   - `invoke_collaborator(agent_id, alias_id, session_id, input_text)`
   - `wait_for_completion(response)`
   - `extract_result(response)`
7. Implement error handling
8. Run `getDiagnostics` on the file
9. Fix any errors or warnings

**Completion Criteria:**
- [ ] Code written
- [ ] getDiagnostics shows NO errors or warnings
- [ ] Error handling implemented

### 11.3: Create Requirements and Configuration

**Purpose:** Set up dependencies and configuration

**Steps:**
1. Read spec documents
2. Create `lambda/supervisor-agentcore/requirements.txt`:
   ```
   bedrock-agentcore
   strands-agents
   boto3
   ```
3. Create `.bedrock_agentcore.yaml` or use agentcore CLI
4. Configure IAM permissions in CloudFormation

**Completion Criteria:**
- [ ] requirements.txt created
- [ ] Configuration created
- [ ] IAM permissions documented

### 11.4: Test Supervisor Agent Locally

**Purpose:** Verify the agent works before deploying

**Steps:**
1. Read spec documents
2. Start agent locally:
   ```bash
   cd lambda/supervisor-agentcore
   python supervisor_agent.py
   ```
3. If startup fails, use AWS Documentation MCP to research solutions
4. Test with curl:
   ```bash
   curl -X POST http://localhost:8080/invocations \
     -H "Content-Type: application/json" \
     -d '{"prompt": "I would like a friend agent"}'
   ```
5. Verify job_name generation
6. Verify orchestration logic (mock collaborator responses)
7. Fix any errors

**Completion Criteria:**
- [ ] Agent starts successfully
- [ ] Tests pass
- [ ] NO errors

### 11.5: Deploy to AgentCore Runtime

**Purpose:** Deploy the supervisor to AWS

**Steps:**
1. Read spec documents
2. Configure deployment:
   ```bash
   cd lambda/supervisor-agentcore
   agentcore configure -e supervisor_agent.py -r us-east-2
   ```
3. Deploy:
   ```bash
   agentcore launch
   ```
4. If deployment fails:
   - Check CloudWatch logs
   - Use AWS Documentation MCP to research solutions
5. Note the AgentCore Runtime ARN
6. Verify in AWS Console
7. Check CloudWatch logs for errors

**Completion Criteria:**
- [ ] Deployment succeeds
- [ ] ARN captured
- [ ] NO errors in CloudWatch logs

### 11.6: Update CloudFormation Template

**Purpose:** Remove old supervisor, add AgentCore outputs

**Steps:**
1. Read spec documents
2. Audit `infrastructure/cloudformation/autoninja-complete.yaml`
3. Identify resources to remove:
   - Supervisor Bedrock Agent
   - Supervisor agent alias
   - Agent collaborator associations
4. Remove those resources
5. Add CloudFormation outputs:
   - SupervisorAgentCoreRuntimeArn
   - SupervisorInvocationCommand
6. Update IAM permissions for AgentCore execution role
7. Verify collaborator agents still defined
8. Validate template:
   ```bash
   cfn-lint infrastructure/cloudformation/autoninja-complete.yaml
   ```
9. If validation fails, use AWS Documentation MCP to research solutions
10. Fix errors

**Completion Criteria:**
- [ ] Old resources removed
- [ ] New outputs added
- [ ] Template validates with NO errors

### 11.7: Configure Custom Orchestration

**Purpose:** Apply rate limiting to collaborators

**Steps:**
1. Read spec documents
2. Verify `lambda/custom-orchestration/handler.py` exists
3. Verify `scripts/configure_custom_orchestration.sh` exists
4. Deploy CloudFormation stack:
   ```bash
   ./scripts/deploy_all.sh
   ```
5. If deployment fails:
   - Check CloudWatch logs
   - Use AWS Documentation MCP to research solutions
6. After deployment completes, run:
   ```bash
   ./scripts/configure_custom_orchestration.sh
   ```
7. Verify each collaborator has orchestrationType: CUSTOM_ORCHESTRATION

**Completion Criteria:**
- [ ] Stack deployed successfully
- [ ] Custom orchestration configured
- [ ] All collaborators have CUSTOM_ORCHESTRATION

### 11.8: Test End-to-End

**Purpose:** Verify the complete workflow

**Steps:**
1. Read spec documents
2. Invoke supervisor:
   ```bash
   agentcore invoke '{"prompt": "I would like a friend agent"}'
   ```
3. If invocation fails:
   - Check CloudWatch logs
   - Use AWS Documentation MCP to research solutions
4. Verify:
   - [ ] Supervisor generates job_name
   - [ ] Requirements Analyst invoked
   - [ ] Code Generator invoked
   - [ ] Solution Architect invoked
   - [ ] Quality Validator invoked
   - [ ] Deployment Manager invoked (if validation passes)
   - [ ] DynamoDB records created
   - [ ] S3 artifacts saved
   - [ ] Final response contains agent ARN
5. Fix any errors

**Completion Criteria:**
- [ ] Full workflow completes successfully
- [ ] All collaborators invoked
- [ ] All artifacts saved
- [ ] NO errors

## Error Handling Guide

### When You Encounter an Error

1. **Identify the error type:**
   - Simple (syntax, typo) → Fix directly
   - Complex (AWS API, config) → Use AWS Documentation MCP

2. **For complex errors:**
   ```
   Use AWS Documentation MCP:
   - Search for relevant documentation
   - Read the documentation page
   - Apply the solution
   - Document the fix
   ```

3. **Verify the fix:**
   - Re-run the failing operation
   - Check for new errors
   - Repeat until resolved

4. **Only then mark task complete**

### Common Errors and Solutions

**AgentCore deployment fails:**
- Check CloudWatch logs: `/aws/bedrock-agentcore/...`
- Search AWS Documentation MCP: "AgentCore Runtime deployment errors"
- Verify IAM permissions
- Check requirements.txt dependencies

**CloudFormation validation fails:**
- Run cfn-lint for detailed errors
- Search AWS Documentation MCP: "CloudFormation [specific error]"
- Check resource dependencies
- Verify IAM role ARNs

**Collaborator invocation fails:**
- Check agent IDs and alias IDs are correct
- Verify IAM permissions for InvokeAgent
- Check CloudWatch logs for collaborator agents
- Search AWS Documentation MCP: "Bedrock Agent InvokeAgent errors"

## Completion Checklist

Before marking Task 11 complete, verify:

- [ ] All sub-tasks (11.0 - 11.8) are complete
- [ ] All spec documents have been read for each sub-task
- [ ] Existing code has been audited
- [ ] All code has been written
- [ ] getDiagnostics shows NO errors or warnings
- [ ] All tests pass
- [ ] Deployment succeeds
- [ ] CloudWatch logs show NO errors
- [ ] DynamoDB records are correct
- [ ] S3 artifacts are saved
- [ ] End-to-end testing succeeds

## Resources

- [AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- [AgentCore Starter Toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-toolkit.html)
- [Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)
- [InvokeAgentRuntime API](https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_InvokeAgentRuntime.html)

## Remember

**Quality over speed.** Take time to fix errors properly. Use AWS Documentation MCP for complex errors. Never skip verification.
