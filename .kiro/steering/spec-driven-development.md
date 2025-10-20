---
inclusion: always
---

# Spec-Driven Development Standards

This steering file ensures all agents follow proper spec-driven development practices in the AutoNinja project.

## Critical Workflow Rules

### 1. MANDATORY: Read Specification Documents First

**Before executing ANY task, agents MUST read these documents in order:**

1. **requirements.md** - Understanding what needs to be built
2. **design.md** - Understanding how it should be built  
3. **tasks.md** - Understanding the implementation plan

**Verification:** Agent must demonstrate understanding by referencing specific requirements and design decisions in their implementation.

### 2. Spec Document Reading Pattern

**Always use this exact pattern when starting work:**

```
STEP 1: Read .kiro/specs/{feature_name}/requirements.md
STEP 2: Read .kiro/specs/{feature_name}/design.md  
STEP 3: Read .kiro/specs/{feature_name}/tasks.md
STEP 4: Identify the specific task being executed
STEP 5: Reference relevant requirements and design decisions
STEP 6: Execute the task implementation
```

### 3. Task Execution Rules

**One Task at a Time:**
- Execute ONLY the requested task
- Do NOT automatically proceed to next tasks
- Stop and let user review after each task completion
- Reference specific requirements the task addresses

**Task Context Requirements:**
- Always cite which requirements the task fulfills
- Reference relevant design decisions from design.md
- Explain how the implementation aligns with the overall architecture

### 4. Implementation Verification

**Before marking any task complete, verify:**

- [ ] Implementation addresses all requirements cited in the task
- [ ] Code follows design patterns specified in design.md
- [ ] Implementation integrates properly with existing architecture
- [ ] All tests pass (if tests are part of the task)
- [ ] getDiagnostics shows no errors or warnings

### 5. AgentCore Integration Requirements

**For AgentCore-related tasks, ensure:**

- [ ] AgentCore Memory is used for distributed state management
- [ ] AgentCore Runtime is properly configured
- [ ] Rate limiting follows the 30-second universal pattern
- [ ] CloudFormation resources are enhanced, not replaced
- [ ] Hackathon requirements are met (minimum 1 AgentCore primitive)

### 6. Error Handling and Recovery

**If specification documents are missing or incomplete:**

1. Stop execution immediately
2. Request user to provide missing specifications
3. Do NOT proceed with implementation without proper specs
4. Suggest creating or updating specification documents

**If task requirements are unclear:**

1. Reference the requirements.md for clarification
2. Check design.md for implementation guidance
3. Ask user for clarification if specs don't provide enough detail
4. Do NOT make assumptions about requirements

### 7. Communication Standards

**When starting a task:**
- State which task you're executing
- Reference the specific requirements it addresses
- Mention relevant design decisions that guide implementation

**When completing a task:**
- Summarize what was implemented
- Confirm which requirements were satisfied
- Note any design decisions that were applied
- Stop and wait for user review

### 8. Forbidden Practices

**NEVER do these things:**

❌ Start implementation without reading specs
❌ Execute multiple tasks in sequence without user approval
❌ Make assumptions about requirements not documented in specs
❌ Ignore design patterns specified in design.md
❌ Proceed when specification documents are missing
❌ Implement features not covered by requirements
❌ Skip verification steps before marking tasks complete

### 9. Spec Document Quality Standards

**Requirements documents must have:**
- Clear user stories with acceptance criteria
- EARS-compliant requirements syntax
- Defined glossary of terms
- Measurable success criteria

**Design documents must have:**
- Architecture overview
- Component interfaces
- Data models
- Error handling strategy
- Testing approach

**Task documents must have:**
- Numbered, actionable tasks
- Clear requirement references
- Implementation order dependencies
- Optional vs required task distinctions

### 10. AgentCore-Specific Patterns

**When working with AgentCore features:**

```python
# AgentCore Memory usage pattern
from agentcore import Memory

memory = Memory(namespace="autoninja-rate-limiting")
last_invocation = memory.get("last_model_call")
current_time = time.time()

if last_invocation and (current_time - last_invocation) < 30:
    wait_time = 30 - (current_time - last_invocation)
    time.sleep(wait_time)

memory.set("last_model_call", current_time)
```

**CloudFormation AgentCore Resources:**
- Use AWS::AgentCore::Memory for distributed state
- Use AWS::AgentCore::Runtime for agent execution
- Enhance existing resources, don't replace them

### 11. Quick Reference Checklist

**Before starting any task:**
- [ ] Read requirements.md completely
- [ ] Read design.md completely  
- [ ] Read tasks.md to understand context
- [ ] Identify specific task to execute
- [ ] Understand which requirements the task addresses

**During task execution:**
- [ ] Reference requirements being implemented
- [ ] Follow design patterns from design.md
- [ ] Implement only what the task specifies
- [ ] Test implementation thoroughly

**After task completion:**
- [ ] Verify all requirements are met
- [ ] Run diagnostics to check for errors
- [ ] Summarize what was accomplished
- [ ] Stop and wait for user review

## When in Doubt

**Always refer back to the specification documents.** They are the source of truth for what needs to be built and how to build it.

If specifications are unclear or missing, stop and request clarification rather than making assumptions.