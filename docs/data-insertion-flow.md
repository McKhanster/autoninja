# Data Insertion Flow

## How Data Flows Between Agents

### 1. Requirements Analyst (RA)

**Input:**
```python
# Supervisor calls RA
user_request = "Build a customer service agent"

bedrock_response = invoke_bedrock_agent(
    agent_id=ra_agent_id,
    alias_id=ra_alias_id,
    session_id=session_id,
    input_text=user_request  # ← This replaces $question$ in ra-nova.md
)
```

**Prompt Template (ra-nova.md):**
```markdown
## User Query

The user has requested:

$question$  ← Replaced with: "Build a customer service agent"

Analyze this request...
```

**Output:**
```markdown
# Requirements Analysis

## Executive Summary
- **Agent Name**: CustomerServiceAgent
...

## For Solution Architect
### Performance Requirements
- **Response Time**: 1500ms
...

## For Code Generator
### Functional Specifications
**Core Capabilities:**
- Track orders
...
```

**Parsed to:**
```python
{
    "executive_summary": {...},
    "for_solution_architect": {...},
    "for_code_generator": {...},
    ...
}
```

---

### 2. Solution Architect (SA)

**Input:**
```python
# Supervisor extracts SA's section
sa_requirements = requirements.get('for_solution_architect')
# = {
#     "performance_requirements": {...},
#     "integration_requirements": {...}
# }

# Supervisor calls SA
bedrock_response = invoke_bedrock_agent(
    agent_id=sa_agent_id,
    alias_id=sa_alias_id,
    session_id=session_id,
    input_text=json.dumps(sa_requirements)  # ← This replaces $question$
)
```

**Prompt Template (sa-nova.md):**
```markdown
## Input from Requirements Analyst

You will receive the requirements analysis from the Requirements Analyst in JSON format:

$question$  ← Replaced with: {"performance_requirements": {...}, "integration_requirements": {...}}

This contains:
- Performance requirements
- Integration requirements

Parse this input and design architecture...
```

**Output:**
```markdown
# Architecture Design

## Executive Summary
- **Architecture Name**: ServerlessCustomerService
...

## For Code Generator
### Service Specifications
#### Primary Compute
- **Service**: AWS Lambda
...
```

**Parsed to:**
```python
{
    "executive_summary": {...},
    "for_code_generator": {...},
    "for_quality_validator": {...},
    ...
}
```

---

### 3. Code Generator (CG)

**Input:**
```python
# Supervisor extracts CG's sections from both RA and SA
cg_requirements = requirements.get('for_code_generator')
cg_architecture = architecture.get('for_code_generator')

# Combine them
cg_input = {
    "requirements": cg_requirements,
    "architecture": cg_architecture
}

# Supervisor calls CG
bedrock_response = invoke_bedrock_agent(
    agent_id=cg_agent_id,
    alias_id=cg_alias_id,
    session_id=session_id,
    input_text=json.dumps(cg_input)  # ← This replaces $question$
)
```

**Prompt Template (cg-nova.md):**
```markdown
## Input from Requirements Analyst and Solution Architect

You will receive a JSON object containing:

$question$  ← Replaced with: {"requirements": {...}, "architecture": {...}}

This includes:
1. From Requirements Analyst: functional specs, business logic, personality
2. From Solution Architect: Lambda specs, Bedrock config, integrations

Generate complete code...
```

**Output:**
```markdown
# Generated Code Package

## Lambda Code

### handler.py

```python
import json
def lambda_handler(event, context):
    return {"statusCode": 200}
```

## Agent Configuration

```yaml
name: CustomerServiceAgent
model: amazon.titan-text-express-v1
```

## OpenAPI Schema

```yaml
openapi: 3.0.1
paths:
  /track-order:
    post: ...
```
```

**Parsed to:**
```python
{
    "lambda_code": {
        "handler.py": "import json\ndef lambda_handler...",
        "business_logic.py": "...",
        ...
    },
    "agent_configuration": {
        "name": "CustomerServiceAgent",
        ...
    },
    "openapi_schema": {
        "openapi": "3.0.1",
        ...
    },
    ...
}
```

---

### 4. Deployment Manager (DM)

**Input:**
```python
# Supervisor passes complete code package (unchanged)
code = code_generator_result.get('code')

# Supervisor calls DM
bedrock_response = invoke_bedrock_agent(
    agent_id=dm_agent_id,
    alias_id=dm_alias_id,
    session_id=session_id,
    input_text=json.dumps(code)  # ← This replaces $question$
)
```

**Prompt Template (dm-nova.md):**
```markdown
## Input from Code Generator

You will receive a JSON object containing the complete code package:

$question$  ← Replaced with: {"lambda_code": {...}, "agent_configuration": {...}, ...}

This includes:
- lambda_code: Dictionary of Python files
- agent_configuration: Bedrock Agent settings
- openapi_schema: API definitions

Generate CloudFormation template...
```

**Output:**
```markdown
# CloudFormation Template

## CloudFormation Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  LambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: CustomerServiceAgent
      ...
  
  BedrockAgent:
    Type: AWS::Bedrock::Agent
    Properties:
      AgentName: CustomerServiceAgent
      ...
```
```

**Parsed to:**
```python
{
    "cloudformation_template": "AWSTemplateFormatVersion: '2010-09-09'...",
    "stack_name": "customer-service-agent-stack",
    ...
}
```

---

## Summary

### Data Flow Diagram

```
User Request
    ↓
    ↓ (input_text = "Build a customer service agent")
    ↓
[RA Bedrock Agent]
    ↓ ($question$ replaced with user request)
    ↓
RA Markdown Output
    ↓
    ↓ (parsed to dict)
    ↓
requirements = {for_solution_architect: {...}, for_code_generator: {...}, ...}
    ↓
    ↓ (extract for_solution_architect)
    ↓ (input_text = json.dumps(requirements['for_solution_architect']))
    ↓
[SA Bedrock Agent]
    ↓ ($question$ replaced with RA's for_solution_architect section)
    ↓
SA Markdown Output
    ↓
    ↓ (parsed to dict)
    ↓
architecture = {for_code_generator: {...}, for_quality_validator: {...}, ...}
    ↓
    ↓ (extract for_code_generator from both RA and SA)
    ↓ (input_text = json.dumps({requirements: ..., architecture: ...}))
    ↓
[CG Bedrock Agent]
    ↓ ($question$ replaced with combined RA+SA sections)
    ↓
CG Markdown Output
    ↓
    ↓ (parsed to dict)
    ↓
code = {lambda_code: {...}, agent_configuration: {...}, openapi_schema: {...}, ...}
    ↓
    ↓ (pass complete code package)
    ↓ (input_text = json.dumps(code))
    ↓
[DM Bedrock Agent]
    ↓ ($question$ replaced with complete code package)
    ↓
DM Markdown Output
    ↓
    ↓ (extract CloudFormation template)
    ↓
Deployed Agent
```

### Key Points

1. **$question$ is the insertion point** - It gets replaced with `input_text` parameter
2. **Supervisor extracts sections** - Uses `.get('for_agent_name')` to extract relevant data
3. **Data is JSON-serialized** - Even though prompts are markdown, data is passed as JSON strings
4. **Agents return markdown** - Responses are markdown documents with embedded code blocks
5. **Parsing extracts structure** - Markdown parser converts responses back to Python dicts

### Code References

**Supervisor orchestration:**
```python
# handler.py lines 387-402
requirements = orchestrate_requirements_analyst(job_name, user_request)
sa_requirements = requirements.get('for_solution_architect', requirements)
architecture = orchestrate_solution_architect(job_name, sa_requirements)
cg_requirements = requirements.get('for_code_generator', requirements)
cg_architecture = architecture.get('for_code_generator', architecture)
code = orchestrate_code_generator(job_name, cg_requirements, cg_architecture)
deployment = orchestrate_deployment_manager(job_name, code)
```

**Agent invocation:**
```python
# solution_architect.py line 163
bedrock_response = invoke_bedrock_agent(
    agent_id=agent_id,
    alias_id=agent_alias_id,
    session_id=session_id,
    input_text=json.dumps(requirements)  # ← Data insertion here
)
```
