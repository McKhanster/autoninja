export AWS_REGION=us-east-2 && export AWS_PROFILE=AdministratorAccess-784327326356 && python3 tests/requirements-analyst/test_requirements_analyst_agent.py

================================================================================
BEDROCK AGENT TEST SUITE - Requirements Analyst
================================================================================

Note: Bedrock on-demand models have strict rate limits (~1 RPM for Claude Sonnet 4.5)
Maintaining 60-second intervals between tests to avoid throttling...
This test will take approximately 3 minutes to complete.


⏳ Running Test 1...

================================================================================
TEST 1: Extract Requirements
================================================================================

================================================================================
INVOKING BEDROCK AGENT
================================================================================
Agent ID: LPDQZRQAZM
Alias ID: TSTALIASID
Session ID: test-session-20251016174108
Region: us-east-2

Prompt: Please extract requirements for a friend agent.

Job Name: job-test-extract-20251016-001122
User Request: I would like a friend agent that can have conversations and provide emotional support

Extract comprehensive requirements for all sub-agents.
================================================================================

Agent Response:
--------------------------------------------------------------------------------
Requirements successfully extracted for job **job-test-extract-20251016-001122**.

**Agent Purpose:** Friend agent for conversations and emotional support

**Key Requirements:**
- **Complexity:** Low
- **Capabilities:** Process user requests for conversational and emotional support
- **Interactions:** API-based communication
- **Foundation Model:** Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)

**Technical Specifications:**
- **Lambda Runtime:** Python 3.12, 512 MB memory, 60s timeout
- **Action Groups:** 1 primary action
- **Infrastructure:** 1 Bedrock agent, 1 Lambda function
- **Deployment:** CloudFormation in us-east-2 region

The requirements have been structured for all downstream sub-agents (Code Generator, Solution Architect, Quality Validator, and Deployment Manager) and are ready for the next stage of the pipeline.
--------------------------------------------------------------------------------

✅ Agent invocation completed successfully!
Total response length: 855 characters

⏳ Running Test 2...

================================================================================
TEST 2: Analyze Complexity
================================================================================

================================================================================
INVOKING BEDROCK AGENT
================================================================================
Agent ID: LPDQZRQAZM
Alias ID: TSTALIASID
Session ID: test-session-20251016174208
Region: us-east-2

Prompt: Please analyze the complexity of these requirements.

Job Name: job-test-complexity-20251016-001122
Requirements: {
  "agent_purpose": "Friend agent for companionship",
  "capabilities": [
    "Natural language conversation",
    "Emotional support"
  ],
  "system_prompts": "Be friendly and supportive"
}

Provide complexity assessment.
================================================================================

Agent Response:
--------------------------------------------------------------------------------
**Complexity Assessment: LOW**

The requirements for job-test-complexity-20251016-001122 have been analyzed and determined to be **low complexity** based on:

**Key Factors:**
- **Simple Purpose**: Basic companionship agent with conversational capabilities
- **Limited Capabilities**: Only natural language conversation and emotional support
- **Minimal Infrastructure**: 
  - 1 Lambda function (512MB, 60s timeout)
  - 1 Bedrock agent with 1 action group
  - No database or storage requirements
- **Straightforward Interactions**: API-based communication only
- **Basic Data Needs**: Session state only
- **Standard Deployment**: CloudFormation in single region (us-east-2)

This is a simple, single-purpose conversational agent without complex integrations, external APIs, or data persistence requirements.
--------------------------------------------------------------------------------

✅ Agent invocation completed successfully!
Total response length: 808 characters

⏳ Running Test 3...

================================================================================
TEST 3: Validate Requirements
================================================================================

================================================================================
INVOKING BEDROCK AGENT
================================================================================
Agent ID: LPDQZRQAZM
Alias ID: TSTALIASID
Session ID: test-session-20251016174308
Region: us-east-2

Prompt: Please validate these requirements for completeness.

Job Name: job-test-validate-20251016-001122
Requirements: {
  "agent_purpose": "Friend agent for companionship",
  "capabilities": [
    "Natural language conversation"
  ],
  "system_prompts": "Be friendly"
}

Check if all required fields are present.
================================================================================

Agent Response:
--------------------------------------------------------------------------------
**Requirements Validation Results:**

❌ **INCOMPLETE** - The provided requirements are missing several critical fields:

**Missing Required Fields:**
1. **interactions** - No interaction patterns defined (API-based, real-time, etc.)
2. **data_needs** - No data storage or state management requirements
3. **integrations** - No integration requirements specified
4. **lambda_requirements** - Missing Lambda configuration (runtime, memory, timeout, actions)
5. **architecture_requirements** - No compute, storage, or Bedrock specifications
6. **deployment_requirements** - No deployment method or region specified
7. **complexity** - No complexity assessment (low/moderate/high)

**Present Fields:**
✓ agent_purpose
✓ capabilities (minimal - only 1 capability)
✓ system_prompts (very basic)

**Recommendation:** The requirements need significant expansion to include Lambda configuration, architecture specifications, deployment details, and more detailed capabilities for all downstream agents (Code Generator, Solution Architect, Quality Validator, Deployment Manager) to function properly.
--------------------------------------------------------------------------------

✅ Agent invocation completed successfully!
Total response length: 1090 characters

================================================================================
TEST SUMMARY
================================================================================
  Extract Requirements: ✅ PASSED
  Analyze Complexity: ✅ PASSED
  Validate Requirements: ✅ PASSED
================================================================================

🎉 ALL TESTS PASSED!

==================================

 export AWS_REGION=us-east-2 && export AWS_PROFILE=AdministratorAccess-784327326356 && python3 tests/code-generator/test_code_generator_agent.py 

================================================================================
BEDROCK AGENT TEST SUITE - Code Generator
================================================================================

Note: Bedrock on-demand models have strict rate limits (~1 RPM for Claude Sonnet 4.5)
Maintaining 60-second intervals between tests to avoid throttling...
This test will take approximately 3 minutes to complete.


⏳ Running Test 1...

================================================================================
TEST 1: Generate Lambda Code
================================================================================

================================================================================
INVOKING BEDROCK AGENT
================================================================================
Agent ID: ENFYY6GZGF
Alias ID: TSTALIASID
Session ID: test-session-20251016175913
Region: us-east-2

Prompt: Please generate Lambda function code for a friend agent.

Job Name: job-test-lambda-20251016-001122
Requirements: {
  "agent_purpose": "Friend agent for companionship",
  "capabilities": [
    "Natural language conversation",
    "Emotional support"
  ],
  "lambda_requirements": {
    "runtime": "python3.12",
    "memory": 512,
    "timeout": 60,
    "actions": [
      {
        "name": "chat",
        "description": "Handle chat interactions"
      }
    ]
  }
}

Generate production-ready Python code with error handling and logging.
================================================================================

Agent Response:
--------------------------------------------------------------------------------
Lambda function code has been successfully generated for job-test-lambda-20251016-001122!

**Generated Files:**

1. **handler.py** - Production-ready Python Lambda function with:
   - Bedrock Agent event parsing and routing
   - Error handling and logging
   - Chat action handler for natural language conversation
   - Session management support
   - Response formatting for Bedrock Agent
   - Configurable logging levels
   - Performance timing

2. **requirements.txt** - Dependencies:
   - boto3>=1.28.0
   - botocore>=1.31.0

**Configuration:**
- Runtime: Python 3.12
- Memory: 512 MB
- Timeout: 60 seconds
- Purpose: Friend agent for companionship with emotional support capabilities

The code includes comprehensive error handling, structured logging, and follows AWS Lambda best practices for Bedrock Agent integration.
--------------------------------------------------------------------------------

✅ Agent invocation completed successfully!
Total response length: 826 characters

⏳ Running Test 2...

================================================================================
TEST 2: Generate Agent Config
================================================================================

================================================================================
INVOKING BEDROCK AGENT
================================================================================
Agent ID: ENFYY6GZGF
Alias ID: TSTALIASID
Session ID: test-session-20251016180013
Region: us-east-2

Prompt: Please generate Bedrock Agent configuration.

Job Name: job-test-config-20251016-001122
Requirements: {
  "agent_purpose": "Friend agent for companionship",
  "system_prompts": "You are a friendly AI companion. Be supportive and engaging.",
  "architecture_requirements": {
    "bedrock": {
      "foundation_model": "anthropic.claude-sonnet-4-5-20250929-v1:0",
      "action_groups": 1
    }
  }
}

Include agent name, instructions, foundation model, and action groups.
================================================================================

Agent Response:
--------------------------------------------------------------------------------
I cannot generate Bedrock Agent configuration because the generate-agent-config function is not available. I can only generate Lambda function code using the available <REDACTED> function. Please ensure the generate-agent-config action is properly configured and available.
--------------------------------------------------------------------------------

✅ Agent invocation completed successfully!
Total response length: 273 characters

⏳ Running Test 3...

================================================================================
TEST 3: Generate OpenAPI Schema
================================================================================

================================================================================
INVOKING BEDROCK AGENT
================================================================================
Agent ID: ENFYY6GZGF
Alias ID: TSTALIASID
Session ID: test-session-20251016180113
Region: us-east-2

Prompt: Please generate OpenAPI schema for action groups.

Job Name: job-test-schema-20251016-001122
Action Group Spec: {
  "agent_name": "friend-agent",
  "actions": [
    {
      "name": "chat",
      "description": "Handle chat interactions",
      "parameters": [
        "user_input",
        "session_id"
      ]
    }
  ]
}

Generate OpenAPI 3.0 schema.
================================================================================

Agent Response:
--------------------------------------------------------------------------------
I cannot generate the OpenAPI schema as the required function for OpenAPI schema generation is not available in my current toolset. Please ensure the generate-openapi-schema action is properly configured and available.
--------------------------------------------------------------------------------

✅ Agent invocation completed successfully!
Total response length: 218 characters

================================================================================
TEST SUMMARY
================================================================================
  Generate Lambda Code: ✅ PASSED
  Generate Agent Config: ✅ PASSED
  Generate OpenAPI Schema: ✅ PASSED
================================================================================

🎉 ALL TESTS PASSED!
