# Amazon Nova Premier Prompting Guide for Structured JSON Output

## Key Findings from AWS Documentation

### 1. Structured Output Best Practices

**For JSON Output:**
- Explicitly state: "Please generate only the JSON output. DO NOT provide any preamble."
- Provide an **Output Schema** in the prompt
- Use **prefilling** to guide the model's response
- Set `temperature=0` for greedy decoding (deterministic output)

### 2. Prefilling Technique (RECOMMENDED)

**Method 1: Prefill with opening brace**
```json
{
  "role": "assistant",
  "content": [{"text": "{"}]
}
```
This nudges the model to start with JSON immediately.

**Method 2: Prefill with JSON code block**
```json
{
  "role": "assistant",
  "content": [{"text": "```json"}]
}
```
Add stop sequence on ` ``` ` to ensure clean JSON extraction.

### 3. System Role Structure

Amazon Nova uses three roles:
- **system** (optional) - Establishes behavioral parameters
- **user** - Conveys context and specifies outcome
- **assistant** - Aids in guiding toward intended response

### 4. Temperature Setting

**For structured output:** Always use `temperature=0`
- Ensures greedy decoding
- Produces deterministic, consistent output
- Critical for JSON generation

## Current Prompt Analysis

### Issues with Current Prompts:

1. **Using Anthropic-specific format:**
   ```json
   {"anthropic_version": "bedrock-2023-05-31", "system": "..."}
   ```

2. **No prefilling in assistant role**
   - Missing the critical prefilling technique

3. **Temperature varies:**
   - RA: 0.1
   - SA: 0.2
   - CG: 0.1
   - QV: 0.0 ✓ (correct)
   - DM: 0.1

## Recommended Prompt Structure for Nova Premier

### For Requirements Analyst, Solution Architect (JSON Output):

```json
{
  "schemaVersion": "messages-v1",
  "system": [
    {
      "text": "You are a Senior Business Analyst... [full instructions]
      
      ## CRITICAL OUTPUT RULES
      - Generate ONLY valid JSON
      - NO markdown code blocks
      - NO preamble or postamble
      - First character MUST be {
      - Last character MUST be }
      
      ## Output Schema:
      {
        \"executive_summary\": {...},
        \"for_solution_architect\": {...}
      }"
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": [{"text": "$question$"}]
    },
    {
      "role": "assistant",
      "content": [{"text": "{"}]
    }
  ],
  "inferenceConfig": {
    "temperature": 0,
    "stopSequences": []
  }
}
```

### Key Changes Needed:

1. **Update schema version:**
   - From: `"anthropic_version": "bedrock-2023-05-31"`
   - To: `"schemaVersion": "messages-v1"`

2. **Add prefilling:**
   - Add assistant message with `"{"` to start JSON immediately

3. **Set temperature to 0:**
   - All agents generating JSON should use `temperature: 0`

4. **Remove stop sequences:**
   - Current stop sequences like `["</answer>"]` are for Claude's XML format
   - Nova doesn't need them for JSON output

## Implementation Priority

### High Priority (JSON Output Agents):
1. **Requirements Analyst** - Generates JSON requirements
2. **Solution Architect** - Generates JSON architecture
3. **Quality Validator** - Generates JSON validation results

### Medium Priority:
4. **Code Generator** - Generates code + JSON config
5. **Deployment Manager** - Generates CloudFormation + JSON

### Low Priority:
6. **Supervisor** - Uses action groups, different pattern

## Temperature Settings by Agent

| Agent | Current | Recommended | Reason |
|-------|---------|-------------|--------|
| Requirements Analyst | 0.1 | **0.0** | JSON output needs determinism |
| Solution Architect | 0.2 | **0.0** | JSON output needs determinism |
| Code Generator | 0.1 | **0.0** | Code + JSON needs consistency |
| Quality Validator | 0.0 | **0.0** | ✓ Already correct |
| Deployment Manager | 0.1 | **0.0** | CloudFormation needs precision |
| Supervisor | 0.0 | **0.0** | ✓ Already correct |

## Example: Updated Requirements Analyst Prompt

### Before (Anthropic format):
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "system": "You are a Senior Business Analyst...",
  "messages": [
    {"role": "user", "content": [{"text": "$question$"}]},
    {"role": "assistant", "content": [{"text": "{$agent_scratchpad$"}]}
  ]
}
```

### After (Nova format with prefilling):
```json
{
  "schemaVersion": "messages-v1",
  "system": [{"text": "You are a Senior Business Analyst..."}],
  "messages": [
    {"role": "user", "content": [{"text": "$question$"}]},
    {"role": "assistant", "content": [{"text": "{"}]}
  ]
}
```

## Benefits of These Changes

1. **Better JSON Compliance** - Prefilling ensures JSON starts immediately
2. **Deterministic Output** - Temperature=0 produces consistent results
3. **Cleaner Parsing** - No markdown wrappers to strip
4. **Nova-Optimized** - Uses Nova's native message format
5. **Reduced Errors** - Less chance of malformed JSON

## Testing Recommendations

1. Test each agent individually with sample inputs
2. Verify JSON parsing works without errors
3. Compare output quality vs. previous Claude models
4. Monitor token usage (Nova Premier has 1M context)
5. Check response times and costs

## Next Steps

1. Update prompt files to use Nova message format
2. Add prefilling to assistant messages
3. Set all temperatures to 0 for JSON output
4. Remove Anthropic-specific stop sequences
5. Test thoroughly before production deployment
