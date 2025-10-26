# Using Markdown Prompts in CloudFormation

## Current Setup (JSON Embedded)

Currently, the JSON prompt is embedded directly in the CloudFormation template:

```yaml
BasePromptTemplate: |
  {
    "schemaVersion": "messages-v1",
    "system": [
      {
        "text": "You are a Senior Business Analyst..."
      }
    ],
    "messages": [...],
    "inferenceConfig": {...}
  }
```

## Option 1: Embed Markdown in CloudFormation (Simple)

Replace the JSON with the markdown content:

```yaml
BasePromptTemplate: |
  # Requirements Analyst Prompt (Markdown Format)
  
  ## System Message
  
  You are a Senior Business Analyst and Requirements Engineer...
  
  ### Your Role
  
  Analyze user requests and extract comprehensive requirements...
  
  ### Output Format
  
  Your response MUST follow this exact markdown structure:
  
  ```markdown
  # Requirements Analysis
  
  ## Executive Summary
  
  - **Agent Name**: [descriptive name]
  - **Purpose**: [what the agent does]
  ...
  ```
  
  ## User Query
  
  The user has requested:
  
  $question$
  
  ## Assistant Response
  
  Begin your response with:
  
  ```markdown
  # Requirements Analysis
  ```
```

**Pros:**
- Simple, everything in one place
- No external dependencies

**Cons:**
- Hard to read/edit in YAML
- Must redeploy CloudFormation to update prompts
- YAML escaping can be tricky

## Option 2: Load from S3 (Recommended)

Store the `.md` file in S3 and load it at deployment time.

### Step 1: Upload Prompts to S3

```bash
aws s3 cp infrastructure/cloudformation/prompts/ra-nova.md \
  s3://your-deployment-bucket/prompts/ra-nova.md
```

### Step 2: Update CloudFormation Template

Use a custom resource or Lambda to read the file:

```yaml
# Custom Resource to Read Prompt from S3
PromptReader:
  Type: AWS::Lambda::Function
  Properties:
    Runtime: python3.12
    Handler: index.handler
    Code:
      ZipFile: |
        import boto3
        import cfnresponse
        
        s3 = boto3.client('s3')
        
        def handler(event, context):
            try:
                bucket = event['ResourceProperties']['Bucket']
                key = event['ResourceProperties']['Key']
                
                response = s3.get_object(Bucket=bucket, Key=key)
                prompt = response['Body'].read().decode('utf-8')
                
                cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                    'Prompt': prompt
                })
            except Exception as e:
                cfnresponse.send(event, context, cfnresponse.FAILED, {
                    'Error': str(e)
                })

ReadRAPrompt:
  Type: Custom::PromptReader
  Properties:
    ServiceToken: !GetAtt PromptReader.Arn
    Bucket: !Ref DeploymentBucket
    Key: prompts/ra-nova.md

# Use the prompt
Agent:
  Type: AWS::Bedrock::Agent
  Properties:
    PromptOverrideConfiguration:
      PromptConfigurations:
        - BasePromptTemplate: !GetAtt ReadRAPrompt.Prompt
```

**Pros:**
- Easy to update prompts without redeploying CloudFormation
- Clean separation of concerns
- Easy to version control prompts

**Cons:**
- More complex setup
- Requires custom resource Lambda

## Option 3: Hybrid Approach (Practical)

Keep the structure but simplify the content:

### Step 1: Create a Simpler Embedded Prompt

```yaml
BasePromptTemplate: |
  You are a Senior Business Analyst. Analyze the user request and return a markdown document.
  
  ## Output Format
  
  Return your response as markdown starting with:
  
  # Requirements Analysis
  
  ## Executive Summary
  - **Agent Name**: [name]
  - **Purpose**: [purpose]
  
  ## For Solution Architect
  ### Performance Requirements
  - **Response Time**: [X]ms
  
  ## For Code Generator
  ### Functional Specifications
  **Core Capabilities:**
  - [capability 1]
  
  ## User Request
  
  $question$
  
  Begin your response with: # Requirements Analysis
```

### Step 2: Store Detailed Template in S3

Keep the full detailed template in S3 for reference and testing, but use a simplified version in CloudFormation.

## Recommended Approach

For your use case, I recommend **Option 1 (Embed Markdown)** because:

1. You already embed JSON prompts
2. Markdown is more readable than JSON even when embedded
3. No additional infrastructure needed
4. Consistent with current architecture

## How to Update

### 1. Read the Markdown File

```bash
cat infrastructure/cloudformation/prompts/ra-nova.md
```

### 2. Copy the Content

Copy everything from the `.md` file.

### 3. Paste into CloudFormation

Replace the `BasePromptTemplate` content:

```yaml
BasePromptTemplate: |
  [PASTE ENTIRE MARKDOWN CONTENT HERE]
```

### 4. Handle Special Characters

YAML requires proper escaping:
- Keep the `|` for multi-line strings
- Indent consistently (usually 2 spaces per level)
- No need to escape most markdown characters

### 5. Replace Placeholders

Make sure `$question$` and `$prompt_session_attributes$` are preserved.

## Example Conversion

**Before (JSON):**
```yaml
BasePromptTemplate: |
  {
    "schemaVersion": "messages-v1",
    "system": [{"text": "You are..."}],
    "messages": [{"role": "user", "content": [{"text": "$question$"}]}]
  }
```

**After (Markdown):**
```yaml
BasePromptTemplate: |
  # Requirements Analyst Prompt
  
  ## System Message
  
  You are a Senior Business Analyst...
  
  ## User Query
  
  $question$
  
  ## Assistant Response
  
  Begin with: # Requirements Analysis
```

## Testing

After updating:

1. Deploy the CloudFormation stack
2. Invoke the agent with a test request
3. Check the response format
4. Verify markdown parsing works

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id <AGENT_ID> \
  --agent-alias-id <ALIAS_ID> \
  --session-id test-$(date +%s) \
  --input-text "Build a customer service agent" \
  output.json
```
