# Markdown Prompts Migration

## Overview

Converted all agent prompts from JSON format to Markdown format based on AWS Nova best practices.

## Why Markdown?

1. **LLMs are trained on markdown** - More natural output format
2. **Less error-prone** - No bracket tracking, fewer parsing errors
3. **Flexible embedding** - Can contain JSON, YAML, Python, any format
4. **Human readable** - Easy to debug and understand
5. **AWS Nova recommendation** - Explicitly supported in Nova documentation

## Files Created

### Prompt Files

| Agent | JSON Prompt (old) | Markdown Prompt (new) |
|-------|-------------------|----------------------|
| Requirements Analyst | `ra-nova.json` | `ra-nova.md` |
| Solution Architect | `sa-nova.json` | `sa-nova.md` |
| Code Generator | `cg-nova.json` | `cg-nova.md` |
| Quality Validator | `qv-nova.json` | `qv-nova.md` |
| Deployment Manager | `dm-nova.json` | `dm-nova.md` |

### Documentation

- `docs/agent-data-flow.md` - Complete data flow specification
- `docs/markdown-prompts-migration.md` - This file

## Key Changes

### 1. Output Format

**Before (JSON):**
```json
{
  "executive_summary": {
    "agent_name": "string",
    "purpose": "string"
  }
}
```

**After (Markdown):**
```markdown
# Requirements Analysis

## Executive Summary

- **Agent Name**: CustomerServiceBot
- **Purpose**: Handle customer inquiries
```

### 2. Embedded Code

Markdown allows embedding multiple formats:

```markdown
## Lambda Code

### handler.py

```python
def lambda_handler(event, context):
    return {"statusCode": 200}
```

## Configuration

```yaml
name: MyAgent
model: amazon.titan-text-express-v1
```
```

### 3. Prefilling

Following Nova best practices, prompts now include prefilling:

```markdown
## Assistant Response

Begin your response with:

```markdown
# Requirements Analysis
```
```

This guides the model to start with the correct format.

## Next Steps

### 1. Update Agent Modules

Each agent module needs to:
- Parse markdown instead of JSON
- Extract sections by headers (e.g., `## For Solution Architect`)
- Extract embedded code blocks
- Convert to Python objects as needed

### 2. Update Parsing Functions

Replace `json.loads()` with markdown parsing:

```python
def extract_section_from_markdown(markdown: str, section_header: str) -> str:
    """Extract a section from markdown by header"""
    # Find section start
    pattern = f"## {section_header}"
    start = markdown.find(pattern)
    if start == -1:
        return ""
    
    # Find next section or end
    next_section = markdown.find("\n## ", start + len(pattern))
    if next_section == -1:
        return markdown[start:]
    
    return markdown[start:next_section]

def extract_code_block(markdown: str, language: str = None) -> str:
    """Extract code from markdown code blocks"""
    import re
    if language:
        pattern = f"```{language}\\n(.*?)\\n```"
    else:
        pattern = r"```.*?\n(.*?)\n```"
    
    matches = re.findall(pattern, markdown, re.DOTALL)
    return matches[0] if matches else ""
```

### 3. Update CloudFormation Templates

Update the prompt configuration in CloudFormation stacks to use `.md` files instead of `.json` files.

### 4. Test Each Agent

Test each agent individually:
1. Verify markdown output is generated
2. Verify sections can be extracted
3. Verify embedded code can be parsed
4. Verify downstream agents receive correct data

## Benefits

### Immediate

- Fewer JSON parsing errors
- More natural LLM output
- Easier debugging

### Long-term

- More maintainable prompts
- Easier to add new sections
- Better human readability
- Flexible format mixing

## Rollback Plan

If markdown approach has issues:
1. Keep JSON prompts (not deleted)
2. Switch back to JSON in CloudFormation
3. Revert parsing logic

## References

- [AWS Nova Prompting Best Practices](https://docs.aws.amazon.com/nova/latest/userguide/prompting.html)
- [Structured Output Documentation](https://docs.aws.amazon.com/nova/latest/userguide/prompting-structured-output.html)
- [Agent Data Flow Specification](./agent-data-flow.md)
