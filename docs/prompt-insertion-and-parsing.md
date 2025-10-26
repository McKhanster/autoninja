# Prompt Insertion and Response Parsing

## How Prompts Work with Bedrock Agents

### 1. Prompt Template Structure

The markdown prompt files (e.g., `ra-nova.md`) contain placeholders that get replaced when the Bedrock Agent is invoked:

```markdown
## User Query

The user has requested:

$question$

Analyze this request and produce a complete requirements analysis document.
```

### 2. Placeholder Replacement

When the supervisor calls the Requirements Analyst:

```python
bedrock_response = invoke_bedrock_agent(
    agent_id=agent_id,
    alias_id=agent_alias_id,
    session_id=session_id,
    input_text=user_request  # This replaces $question$
)
```

The Bedrock Agent runtime automatically replaces `$question$` with the actual user request.

### 3. Response Format

The agent returns a markdown document like:

```markdown
# Requirements Analysis

## Executive Summary

- **Agent Name**: CustomerServiceBot
- **Purpose**: Handle customer inquiries
- **Business Value**: Reduce response time by 40%
- **Complexity Level**: medium
- **Estimated Effort**: 3-4 months

## For Solution Architect

### Performance Requirements

- **Response Time**: 1500ms
- **Throughput**: 1200 requests per minute
- **Availability**: 99.9%
- **Scalability Needs**: Auto-scale during peak hours

### Integration Requirements

**External APIs:**
- PaymentGatewayAPI
- ShippingProviderAPI

**Data Sources:**
- InventoryDB
- CRM_System

**AWS Services:**
- Lambda
- DynamoDB
- S3

**Networking:** VPC with private subnets

## For Code Generator

### Functional Specifications

**Core Capabilities:**
- Track orders
- Process returns

...
```

## Parsing the Response

### Step 1: Receive Markdown

```python
bedrock_response = invoke_bedrock_agent(...)
# Returns full markdown document
```

### Step 2: Parse to Dictionary

```python
from shared.utils.markdown_parser import markdown_to_dict

requirements = markdown_to_dict(bedrock_response)
```

This converts the markdown to:

```python
{
    "executive_summary": {
        "Agent Name": "CustomerServiceBot",
        "Purpose": "Handle customer inquiries",
        "Business Value": "Reduce response time by 40%",
        "Complexity Level": "medium",
        "Estimated Effort": "3-4 months"
    },
    "for_solution_architect": {
        "performance_requirements": {
            "Response Time": "1500ms",
            "Throughput": "1200 requests per minute",
            "Availability": "99.9%",
            "Scalability Needs": "Auto-scale during peak hours"
        },
        "integration_requirements": {
            "external_apis": ["PaymentGatewayAPI", "ShippingProviderAPI"],
            "data_sources": ["InventoryDB", "CRM_System"],
            "aws_services": ["Lambda", "DynamoDB", "S3"],
            "networking": "VPC with private subnets"
        }
    },
    "for_code_generator": {
        "functional_specifications": {
            "core_capabilities": ["Track orders", "Process returns"],
            ...
        },
        ...
    },
    ...
}
```

### Step 3: Extract Sections

The supervisor then extracts specific sections for each agent:

```python
# For Solution Architect
sa_requirements = requirements.get('for_solution_architect', requirements)

# For Code Generator
cg_requirements = requirements.get('for_code_generator', requirements)
```

## Parsing Utilities

The `markdown_parser.py` module provides several utilities:

### Extract a Section

```python
from shared.utils.markdown_parser import extract_section

# Get everything under "## For Solution Architect"
sa_section = extract_section(markdown, "For Solution Architect", level=2)
```

### Extract Code Blocks

```python
from shared.utils.markdown_parser import extract_code_block

# Get Python code from first code block
python_code = extract_code_block(markdown, language='python', index=0)

# Get YAML from second code block
yaml_config = extract_code_block(markdown, language='yaml', index=1)
```

### Extract Bullet Lists

```python
from shared.utils.markdown_parser import extract_bullet_list

# Get list of capabilities
capabilities = extract_bullet_list(markdown, "Core Capabilities")
# Returns: ["Track orders", "Process returns", ...]
```

### Extract Key-Value Pairs

```python
from shared.utils.markdown_parser import extract_key_value_pairs

# Get executive summary as dict
summary = extract_key_value_pairs(markdown, "Executive Summary")
# Returns: {"Agent Name": "...", "Purpose": "...", ...}
```

### Full Conversion

```python
from shared.utils.markdown_parser import markdown_to_dict

# Convert entire RA response to nested dict
requirements = markdown_to_dict(markdown)
```

## Example Flow

### 1. User Request

```
"Build a customer service agent for order tracking"
```

### 2. Supervisor Calls RA

```python
requirements_result = orchestrate_requirements_analyst(job_name, user_request)
```

### 3. RA Bedrock Agent Receives

The prompt template with `$question$` replaced:

```markdown
## User Query

The user has requested:

Build a customer service agent for order tracking

Analyze this request and produce a complete requirements analysis document.
```

### 4. RA Returns Markdown

```markdown
# Requirements Analysis

## Executive Summary
- **Agent Name**: OrderTrackingAgent
...

## For Solution Architect
### Performance Requirements
- **Response Time**: 1000ms
...
```

### 5. Parse to Dictionary

```python
requirements = parse_markdown_response(bedrock_response)
```

### 6. Extract for SA

```python
sa_requirements = requirements.get('for_solution_architect')
```

### 7. SA Receives Only Its Section

```python
{
    "performance_requirements": {...},
    "integration_requirements": {...}
}
```

## Benefits

1. **Clean Separation**: Each agent gets only what it needs
2. **Easy Debugging**: Can read the markdown directly
3. **Flexible Format**: Can mix text, lists, code blocks
4. **Less Error-Prone**: No JSON bracket tracking
5. **Human Readable**: Easy to understand what went wrong

## Migration Path

1. ✅ Created markdown prompt templates
2. ✅ Created markdown parser utility
3. ✅ Updated Requirements Analyst to use markdown parser
4. ⏳ Update Solution Architect to use markdown parser
5. ⏳ Update Code Generator to use markdown parser
6. ⏳ Update Deployment Manager to use markdown parser
7. ⏳ Update CloudFormation stacks to reference .md files
8. ⏳ Test end-to-end flow
