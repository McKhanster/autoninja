# Nova Premier Migration Plan

## Model Information

**Model ID to Use:** `us.amazon.nova-premier-v1:0` (Inference Profile)
**Context Window:** 1,000,000 tokens (1M)
**Regions:** us-east-1, us-east-2, us-west-2

## Key Benefits

1. **5x Larger Context Window** - 1M tokens vs 200k for Claude 3.5 Haiku
2. **Most Capable Model** - Best for complex reasoning and large data accumulation
3. **Multimodal Support** - Text, image, and video inputs
4. **AWS Native** - Optimized for AWS infrastructure

## Changes Required

### 1. CloudFormation Template Updates

Update the `BedrockModel` parameter default in:

- ✅ `infrastructure/cloudformation/autoninja-collaborators.yaml` - Parent template
- ✅ `infrastructure/cloudformation/stacks/supervisor.yaml` - Supervisor agent
- ⏳ `infrastructure/cloudformation/stacks/requirements-analyst.yaml`
- ⏳ `infrastructure/cloudformation/stacks/solution-architect.yaml`
- ⏳ `infrastructure/cloudformation/stacks/code-generator.yaml`
- ⏳ `infrastructure/cloudformation/stacks/quality-validator.yaml`
- ⏳ `infrastructure/cloudformation/stacks/deployment-manager.yaml`

**Change from:**
```yaml
Default: anthropic.claude-3-5-haiku-20241022-v1:0
# or
Default:  us.amazon.nova-premier-v1:0
```

**Change to:**
```yaml
Default: us.amazon.nova-premier-v1:0
```

### 2. Prompt Files - NO CHANGES NEEDED

The prompt files in `infrastructure/cloudformation/prompts/` use the Invoke API format which Nova Premier supports:

- `ra.json` - Requirements Analyst
- `sa.json` - Solution Architect  
- `cg.json` - Code Generator
- `qv.json` - Quality Validator
- `dm.json` - Deployment Manager
- `sup.json` - Supervisor

**Why no changes needed:**
- Nova models support both Converse API and Invoke API
- The `anthropic_version: bedrock-2023-05-31` format works with Nova
- Prompts will function correctly with Nova Premier

### 3. Token Limit Configurations

Current token limits are already generous:
- Requirements Analyst: 16,000 tokens
- Solution Architect: 16,000 tokens
- Code Generator: 32,000 tokens
- Quality Validator: 8,000 tokens
- Deployment Manager: 16,000 tokens

With Nova Premier's 1M context window, these limits are well within capacity.

### 4. Important Considerations

**Timeout Settings:**
- Nova models have a 60-minute timeout for inference
- Ensure SDK read timeout is set to at least 3600 seconds
- Current Lambda timeouts should be reviewed

**Cost:**
- Nova Premier is the most expensive Nova model
- Justified by 1M context window and superior capabilities
- Monitor costs after deployment

**Availability:**
- Only available in us-east-1, us-east-2, us-west-2
- Ensure your deployment region is supported

## Deployment Steps

1. **Update CloudFormation Templates**
   ```bash
   # Update all stack defaults to us.amazon.nova-premier-v1:0
   ```

2. **Deploy Updated Stacks**
   ```bash
   ./scripts/deploy_collaborators.sh
   ./scripts/deploy_supervisor.sh
   ```

3. **Test with Sample Request**
   ```bash
   # Test with a complex request that benefits from large context
   ```

4. **Monitor Performance**
   - Check CloudWatch logs for any errors
   - Monitor token usage and costs
   - Validate response quality

## Rollback Plan

If issues occur:
1. Revert `BedrockModel` parameter to previous value
2. Redeploy stacks
3. Test functionality

## Success Criteria

- ✅ All agents deploy successfully with Nova Premier
- ✅ Multi-agent workflow completes end-to-end
- ✅ Large context requests handled without truncation
- ✅ Response quality meets or exceeds previous model
- ✅ No critical errors in CloudWatch logs

## Next Steps

1. Complete CloudFormation template updates
2. Deploy to development environment first
3. Run comprehensive tests
4. Deploy to production after validation
