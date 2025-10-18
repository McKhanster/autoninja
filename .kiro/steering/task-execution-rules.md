---
inclusion: always
---

# Task Execution Rules for AutoNinja Spec

## Critical Execution Rules

These rules MUST be followed for EVERY task in the AutoNinja spec:

### 1. Always Read Spec Documents First

**BEFORE starting ANY task, you MUST:**
- Read `.kiro/specs/autoninja-bedrock-agents/requirements.md` completely
- Read `.kiro/specs/autoninja-bedrock-agents/design.md` completely
- Read `.kiro/specs/autoninja-bedrock-agents/tasks.md` completely

**Why:** Understanding the full context prevents mistakes and ensures consistency.

### 2. Audit Existing Code for Compatibility

**BEFORE making changes, you MUST:**
- Review existing code in the relevant files
- Identify what needs to be removed, updated, or preserved
- Document compatibility issues
- Plan the changes before implementing

**Example:** For task 11, audit `infrastructure/cloudformation/autoninja-complete.yaml` to understand the existing supervisor agent definition before integrating AgentCore.

### 3. Use AWS Documentation MCP for Non-Simple Errors

**IF an error occurs that is NOT simple (syntax error, typo, etc.), you MUST:**
- Use the AWS Documentation MCP to search for solutions
- Read relevant AWS documentation pages
- Apply the documented solution
- Document what you learned

**Example Errors Requiring MCP:**
- CloudFormation validation errors
- AWS API errors (throttling, permissions, etc.)
- AgentCore deployment failures
- Bedrock Agent configuration issues

**Simple Errors (don't need MCP):**
- Python syntax errors
- Missing imports
- Typos in variable names

### 4. Never Mark Tasks Complete with Errors

**A task can ONLY be marked complete when:**
- ✅ All code has been written
- ✅ All tests pass
- ✅ getDiagnostics shows NO errors or warnings
- ✅ Deployment succeeds (if applicable)
- ✅ Validation passes (if applicable)
- ✅ End-to-end testing succeeds (if applicable)

**If ANY errors exist:**
- ❌ DO NOT mark the task as complete
- ❌ DO NOT move to the next task
- ✅ Fix the errors first
- ✅ Use AWS Documentation MCP if needed
- ✅ Re-test until all errors are resolved

### 5. Verification Steps

**After implementing code, you MUST:**
1. Run `getDiagnostics` on all modified files
2. Fix any errors or warnings
3. Run tests (if applicable)
4. Verify deployment (if applicable)
5. Check CloudWatch logs for errors
6. Verify DynamoDB records (if applicable)
7. Verify S3 artifacts (if applicable)

### 6. Error Handling Pattern

**When an error occurs:**

```
1. Identify the error type
   - Simple (syntax, typo) → Fix directly
   - Complex (AWS API, config) → Use AWS Documentation MCP

2. If using MCP:
   - Search for relevant documentation
   - Read the documentation page
   - Apply the solution
   - Document the fix

3. Verify the fix:
   - Re-run the failing operation
   - Check for new errors
   - Repeat until resolved

4. Only then mark task complete
```

## Task 11 Specific Rules

For task 11 (Supervisor Agent with AgentCore Runtime):

### Mandatory First Step (11.0)
- Read ALL spec documents
- Audit `infrastructure/cloudformation/autoninja-complete.yaml`
- Identify existing supervisor agent resources
- Document what needs to change

### Implementation (11.1-11.2)
- Follow the design in design.md exactly
- Use the code examples provided
- Implement error handling
- Run getDiagnostics before marking complete

### Testing (11.4)
- Test locally first
- Fix all errors before deploying
- Use AWS Documentation MCP for complex errors

### Deployment (11.5)
- Check CloudWatch logs for errors
- Use AWS Documentation MCP if deployment fails
- Verify deployment in AWS Console

### CloudFormation Update (11.6)
- Audit existing template first
- Remove old supervisor resources
- Validate with cfn-lint
- Fix validation errors before marking complete

### End-to-End Testing (11.8)
- Test complete workflow
- Verify all collaborators are invoked
- Check DynamoDB and S3
- Fix any errors before marking complete

## Completion Checklist

Before marking ANY task complete, verify:

- [ ] All spec documents have been read
- [ ] Existing code has been audited (if applicable)
- [ ] All code has been written
- [ ] getDiagnostics shows NO errors or warnings
- [ ] All tests pass (if applicable)
- [ ] Deployment succeeds (if applicable)
- [ ] CloudWatch logs show NO errors
- [ ] DynamoDB records are correct (if applicable)
- [ ] S3 artifacts are saved (if applicable)
- [ ] End-to-end testing succeeds (if applicable)

## Remember

**Quality over speed.** It's better to take time to fix errors properly than to mark tasks complete with unresolved issues.

**Use AWS Documentation MCP.** It's there to help you find solutions to complex AWS-related errors.

**Never skip verification.** Always verify your work before marking a task complete.
