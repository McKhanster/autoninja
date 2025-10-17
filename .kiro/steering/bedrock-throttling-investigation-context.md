---
inclusion: fileMatch
fileMatchPattern: '.kiro/specs/bedrock-throttling-investigation/**'
---

# Bedrock Throttling Investigation - Required Context

When working on tasks for the bedrock-throttling-investigation spec, you MUST read the following documents before starting any task implementation:

## Required Reading (ALWAYS read these first)

1. **Requirements Document**: #[[file:.kiro/specs/bedrock-throttling-investigation/requirements.md]]
   - Contains the problem statement and acceptance criteria
   - Defines what needs to be fixed and validated

2. **Design Document**: #[[file:.kiro/specs/bedrock-throttling-investigation/design.md]]
   - Outlines the solution architecture
   - Explains how Advanced Prompts will be implemented
   - Details the CloudFormation changes needed

3. **Root Cause Analysis**: #[[file:.kiro/specs/bedrock-throttling-investigation/root-cause-analysis.md]]
   - Documents the investigation findings
   - Explains why throttling occurs (AWS default orchestration prompt)
   - Provides evidence from logs and AWS documentation
   - Recommends the solution approach

## Critical Context

**The Problem**: AWS Bedrock Agents use a default orchestration prompt that includes "ALWAYS optimize the plan by using multiple function calls at the same time whenever possible." This causes parallel tool calls that trigger multiple simultaneous Converse API calls, exceeding Claude Sonnet 4.5's ~1 RPM rate limit.

**The Solution**: Use AWS Bedrock's Advanced Prompts feature to override the default orchestration template and enforce sequential tool execution.

**Key Insight**: The problematic instruction is NOT in our codebase—it's part of AWS's managed service. We must override it using CloudFormation configuration.

## Implementation Guidelines

- All changes must be made to CloudFormation templates in `infrastructure/cloudformation/`
- Focus on the `PromptOverrideConfiguration` property for Bedrock Agents
- Test changes must update rate limiting intervals to account for sequential execution
- Verify changes by checking CloudWatch logs for sequential tool calls

## DO NOT proceed with any task until you have read all three required documents above.
