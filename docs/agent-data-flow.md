# AutoNinja Agent Data Flow

## The Big Picture

**INPUT**: User types "Build me a customer service agent"  
**OUTPUT**: A deployed, working Bedrock Agent with Lambda functions, ready to use

## The Pipeline

1. **Requirements Analyst** - Understands what the user wants
2. **Solution Architect** - Designs the AWS infrastructure  
3. **Code Generator** - Writes all the code
4. **Deployment Manager** - Deploys everything to AWS

---

## 1. Requirements Analyst (RA)

### What It Receives
A natural language request from the user (e.g., "Build a customer service chatbot")

### What It Does
Analyzes the request and creates a structured document with different sections for different audiences.

### What It Produces

**For Solution Architect:**
- How fast should responses be? (e.g., under 2 seconds)
- How many requests per minute? (e.g., 1000 RPM)
- What external systems to connect to? (e.g., payment API, inventory database)
- What AWS services are needed? (e.g., Lambda, DynamoDB, S3)

**For Code Generator:**
- What should the agent actually do? (e.g., track orders, process returns)
- What kind of conversations will it have? (e.g., multi-turn dialogues)
- What inputs need validation? (e.g., order IDs must match pattern ORD-123456)
- How should it talk? (e.g., friendly and professional tone)
- What business rules? (e.g., escalate to human after 3 failed attempts)

**For Quality Validator:** (currently skipped)
- Security requirements
- Compliance needs

**For Deployment Manager:** (currently unused)
- Infrastructure specs
- Monitoring needs

### Example
"The agent needs to respond in under 1.5 seconds, handle 1200 requests per minute, connect to a payment gateway and inventory database, use Lambda and DynamoDB, track orders and process returns, validate product IDs, maintain a friendly tone, and escalate after 3 failures."

---

## 2. Solution Architect (SA)

### What It Receives
ONLY the "For Solution Architect" section from RA - the performance and integration requirements.

### What It Does
Designs the AWS architecture - which services, how they connect, how much they cost.

### What It Produces

**For Code Generator:**
- Lambda settings: Python 3.12, 512MB memory, 30 second timeout
- Which Bedrock model to use: amazon.titan-text-express-v1
- How to structure the agent's instructions
- How to connect Lambda to DynamoDB, S3, etc.
- Environment variables needed

**For Quality Validator:** (currently skipped)
- Security controls to implement
- Compliance mappings

**For Deployment Manager:** (currently unused)
- CloudFormation resources list
- Deployment order

**Cost Estimate:**
- Monthly cost projection

### Example
"Use Lambda with 512MB memory and 30s timeout, use Titan Express model, connect to DynamoDB for session storage, use S3 for logs, set environment variable ORDER_TABLE=customer-orders, estimated cost $45/month."

---

## 3. Code Generator (CG)

### What It Receives
TWO things:
1. From RA: What the agent should do (capabilities, business logic, personality)
2. From SA: How to build it (Lambda specs, Bedrock config, integrations)

### What It Does
Writes all the actual code files, configurations, tests, and documentation.

### What It Produces

**Lambda Code Files:**
- handler.py - Main entry point
- business_logic.py - Core functionality
- utils.py - Helper functions (database queries, etc.)
- validators.py - Input validation
- exceptions.py - Error handling
- config.py - Configuration management
- requirements.txt - Python dependencies

**Bedrock Agent Configuration:**
- Agent name
- Description
- Instructions (how the agent should behave)
- Which model to use
- Action groups (what functions the agent can call)

**OpenAPI Schema:**
- API definitions for all the agent's actions
- Request/response formats
- Validation rules

**Tests:**
- Unit tests for individual functions
- Integration tests for full workflows
- Test data examples

**Documentation:**
- README with setup instructions
- API documentation
- Deployment guide

### Example
Complete Python code for tracking orders, processing returns, validating inputs, handling errors, plus Bedrock Agent config that says "You are a helpful customer service agent", plus OpenAPI schema defining the /track-order and /process-return endpoints, plus tests and docs.

---

## 4. Deployment Manager (DM)

### What It Receives
The COMPLETE package from Code Generator - nothing added, nothing removed.

### What It Does
1. Zips up all the Lambda code files
2. Uploads the ZIP to S3
3. Uploads the OpenAPI schema to S3
4. Generates a CloudFormation template (asks its own Bedrock Agent to create this)
5. Deploys the CloudFormation stack
6. Waits for everything to be created
7. Returns the deployed agent's ID and ARN

### What It Produces
- Stack name and ID
- Agent ID (to invoke the agent)
- Agent Alias ID (production version)
- Lambda ARN
- S3 locations of uploaded files
- Status: success or error

### Example
"Stack job-customer-20251025-stack created successfully. Agent ID: ABC123, Alias ID: XYZ789, Lambda ARN: arn:aws:lambda:us-east-2:123456789012:function:CustomerServiceAgent. Ready to use."

---

## How The Supervisor Orchestrates

```
1. Call RA with user's request
   → Get back structured requirements

2. Extract the "for_solution_architect" section
   Call SA with just that section
   → Get back architecture design

3. Extract "for_code_generator" from both RA and SA outputs
   Call CG with both sections
   → Get back complete code package

4. Pass the complete code package to DM (unchanged)
   → Get back deployed agent info
```

## Critical Rules

1. **Each agent gets ONLY what it needs**
   - SA doesn't need to know about agent personality
   - CG doesn't need to know about monthly costs
   - DM doesn't need to know about business requirements

2. **No modifications between agents**
   - What CG produces is exactly what DM deploys
   - Don't add extra fields
   - Don't remove anything

3. **Data flows one direction**
   - RA → SA → CG → DM
   - No going backwards
   - No skipping steps

4. **Use the specialized sections**
   - RA produces `for_solution_architect`, `for_code_generator`, etc.
   - Supervisor extracts these sections
   - Each agent receives only its section

---

## What Can Go Wrong

**Problem**: SA receives the entire requirements document instead of just its section  
**Why**: Supervisor didn't extract `requirements['for_solution_architect']`  
**Fix**: Extract the section before calling SA

**Problem**: DM can't find the agent configuration  
**Why**: Looking for `agent_config` but CG produces `agent_configuration`  
**Fix**: Check both names: `code.get('agent_configuration', code.get('agent_config', {}))`

**Problem**: DM receives a messy code object with extra fields  
**Why**: Something added fields to the code object between CG and DM  
**Fix**: Pass code object unchanged from CG to DM

**Problem**: All agents receive identical data  
**Why**: Not extracting the specialized sections  
**Fix**: Use `requirements.get('for_agent_name')` pattern consistently


---

## Output Format: Markdown vs JSON

### Why Markdown?

1. **LLMs are trained on markdown** - More natural output format
2. **Less bracket tracking** - No need to balance `{}` and `[]`
3. **Flexible embedding** - Can contain JSON, YAML, code, tables, all in one document
4. **Human readable** - Easy to debug and understand
5. **Fewer parsing errors** - Missing commas and brackets are common JSON issues

### Proposed Format

Each agent produces a markdown document with embedded code blocks:

```markdown
# Requirements Analysis

## Executive Summary
- Agent Name: CustomerServiceBot
- Purpose: Handle customer inquiries
- Complexity: Medium

## For Solution Architect

### Performance Requirements
- Response time: < 1500ms
- Throughput: 1200 RPM
- Availability: 99.9%

### Integration Requirements
```yaml
external_apis:
  - PaymentGatewayAPI
  - ShippingProviderAPI
data_sources:
  - InventoryDB
  - CRM_System
aws_services:
  - Lambda
  - DynamoDB
  - S3
```

## For Code Generator

### Functional Specifications
- Track orders
- Process returns
- Multi-turn dialogues

### Business Logic
```python
# Decision rules
if failed_attempts >= 3:
    escalate_to_human()
```
```

### Parsing Strategy

1. **Extract sections by headers** - Use `## For Solution Architect` to find sections
2. **Parse embedded code blocks** - Extract YAML/JSON/Python from ``` blocks
3. **Fallback to full document** - If section not found, pass entire markdown

### Benefits

- **Fewer JSON parsing errors** - No more "Expecting value: line 68 column 35"
- **Better context** - Explanations alongside data
- **Easier debugging** - Can read the markdown directly
- **More flexible** - Mix formats as needed

### Implementation

Each agent module needs:
1. Update prompt to request markdown output
2. Parse markdown to extract sections
3. Convert embedded code blocks to Python objects when needed
