# AgentCore Throttling Fix Hooks

## Hook Descriptions

1. **Spec Review Before Tasks**: When starting any task, the agent should read requirements.md, design.md, and tasks.md to understand specifications before implementation.

2. **AgentCore Compliance Check**: When Python or YAML files are edited, the agent should verify AgentCore Memory usage, rate limiting patterns, and CloudFormation resource enhancements.

3. **Rate Limiting Verification**: When Lambda Python files are modified, the agent should check that all model invocations implement the 30-second rate limiting pattern with AgentCore Memory.

4. **Task Completion Check**: When marking a task complete, the agent should verify all requirements are met, run diagnostics, and confirm AgentCore integration before allowing completion.