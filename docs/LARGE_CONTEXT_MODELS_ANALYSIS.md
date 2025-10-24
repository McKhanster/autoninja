# Large Context Window Models on AWS Bedrock

## Summary of Available Models with Large Context Windows

Based on AWS Bedrock documentation research, here are the models with the largest context windows:

### 🏆 Top Models by Context Window Size:

| Model | Context Window | Model ID | Regions | Notes |
|-------|---------------|----------|---------|-------|
| **Amazon Nova Premier** | **1M tokens** | amazon.nova-premier-v1:0 | us-east-1*, us-east-2*, us-west-2* | Most capable, best for teacher/distillation |
| **Amazon Nova Pro** | 300k tokens | amazon.nova-pro-v1:0 | Multiple regions | Best balance accuracy/speed/cost |
| **Amazon Nova Lite** | 300k tokens | amazon.nova-lite-v1:0 | Multiple regions | Very low cost, lightning fast |
| **Claude 3.5 Haiku** | 200k tokens | anthropic.claude-3-5-haiku-20241022-v1:0 | us-east-1*, us-east-2*, us-west-2 | Current choice, fast & cheap |
| **Claude 3.5 Sonnet** | 200k tokens | anthropic.claude-3-5-sonnet-20241022-v2:0 | Multiple regions | Higher quality |
| **Amazon Nova Micro** | 128k tokens | amazon.nova-micro-v1:0 | Multiple regions | Text-only, lowest latency |

### Qwen Models Available on Bedrock:

✅ **Qwen models ARE available** on AWS Bedrock:

| Model | Model ID | Regions |
|-------|----------|---------|
| **Qwen3 235B A22B 2507** | qwen.qwen3-235b-a22b-2507-v1:0 | us-east-2, us-west-2, ap-northeast-1, ap-south-1, ap-southeast-3, eu-central-1, eu-north-1, eu-south-1, eu-west-2 |
| **Qwen3 32B (dense)** | qwen.qwen3-32b-v1:0 | us-east-1, us-east-2, us-west-2, ap-northeast-1, ap-south-1, ap-southeast-3, eu-central-1, eu-north-1, eu-south-1, eu-west-1, eu-west-2, sa-east-1 |
| **Qwen3 Coder 480B A35B** | qwen.qwen3-coder-480b-a35b-v1:0 | us-east-2, us-west-2, ap-northeast-1, ap-south-1, ap-southeast-3, eu-north-1, eu-west-2 |
| **Qwen3-Coder-30B-A3B** | qwen.qwen3-coder-30b-a3b-v1:0 | us-east-1, us-east-2, us-west-2, ap-northeast-1, ap-south-1, ap-southeast-3, eu-central-1, eu-north-1, eu-south-1, eu-west-1, eu-west-2, sa-east-1 |

**Note:** AWS documentation doesn't specify Qwen's exact context window size, but Qwen models typically support **128k-1M tokens** depending on the variant.

## Recommendations for Your Multi-Agent System

### Current Situation:
- You need **super large context windows** for data accumulation across agents
- Currently using **Claude 3.5 Haiku** (200k context)

### Best Options:

#### Option 1: Amazon Nova Premier (1M context) 🏆
**Pros:**
- Largest context window available (1M tokens = 5x larger than Haiku)
- Most capable model for complex reasoning
- Multimodal (text, image, video)
- Available in US regions

**Cons:**
- ⚠️ Most expensive model
- Only US East (N. Virginia), US East (Ohio), US West (Oregon)
- No Provisioned Throughput
- No fine-tuning (distillation only)

**Best for:** Code Generator agent that needs to handle massive accumulated context

#### Option 2: Amazon Nova Pro (300k context)
**Pros:**
- 50% larger context than Haiku (300k vs 200k)
- Best balance of accuracy, speed, and cost
- Widely available across regions
- Supports Provisioned Throughput
- Supports fine-tuning

**Cons:**
- More expensive than Haiku (but cheaper than Premier)
- Not as fast as Lite

**Best for:** Solution Architect and Code Generator agents

#### Option 3: Amazon Nova Lite (300k context)
**Pros:**
- 50% larger context than Haiku (300k vs 200k)
- Very low cost
- Lightning fast
- Widely available

**Cons:**
- Lower quality than Pro/Premier
- May not be sufficient for complex code generation

**Best for:** Requirements Analyst, Quality Validator, Deployment Manager

#### Option 4: Qwen3 Models
**Pros:**
- Large models (235B, 480B parameters)
- Likely large context windows (128k-1M)
- Good for code generation (Coder variants)

**Cons:**
- ⚠️ AWS docs don't specify exact context window size
- Limited documentation on Bedrock
- Need to test performance

**Best for:** Code Generator if context window is confirmed to be large

### Recommended Configuration:

```yaml
# For maximum context window capacity:

Requirements Analyst: amazon.nova-lite-v1:0      # 300k context, fast, cheap
Solution Architect:   amazon.nova-pro-v1:0       # 300k context, balanced
Code Generator:       amazon.nova-premier-v1:0   # 1M context, most capable
Quality Validator:    amazon.nova-lite-v1:0      # 300k context, fast, cheap
Deployment Manager:   amazon.nova-lite-v1:0      # 300k context, fast, cheap
Supervisor:           amazon.nova-pro-v1:0       # 300k context, orchestration
```

### Alternative (Cost-Optimized):

```yaml
# Balance context window and cost:

Requirements Analyst: amazon.nova-lite-v1:0      # 300k context
Solution Architect:   amazon.nova-pro-v1:0       # 300k context
Code Generator:       amazon.nova-pro-v1:0       # 300k context (cheaper than Premier)
Quality Validator:    amazon.nova-lite-v1:0      # 300k context
Deployment Manager:   amazon.nova-lite-v1:0      # 300k context
Supervisor:           amazon.nova-pro-v1:0       # 300k context
```

## Next Steps:

1. **Test Qwen models** - Verify actual context window size and performance
2. **Benchmark Nova Premier** - Test if 1M context justifies the cost for Code Generator
3. **Try Nova Pro/Lite** - Get 50% more context (300k) at reasonable cost
4. **Monitor token usage** - Check if you're actually hitting 200k limits with current setup

## Key Insight:

If you're hitting context window limits with Claude 3.5 Haiku (200k), switching to **Nova Pro or Nova Lite (300k)** gives you 50% more capacity, while **Nova Premier (1M)** gives you 5x more capacity for the most demanding agents.

Would you like me to update your CloudFormation templates to use Nova models?
