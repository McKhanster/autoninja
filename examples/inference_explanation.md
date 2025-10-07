# Requirements Analyst Agent - Direct LLM Inference Implementation

## Overview

The Requirements Analyst Agent now makes **direct inference calls** to Amazon Bedrock models with comprehensive request/response logging. Here's exactly where and how the LLM inference happens:

## 🔍 Where the LLM Inference Occurs

### 1. Main Analysis Method
**File:** `autoninja/agents/requirements_analyst.py`  
**Method:** `analyze_requirements()` (lines ~160-200)

```python
# Make direct Bedrock inference call
result = self._make_bedrock_inference(agent_input, execution_id)

# Log raw response
logger.info(f"Raw response for {execution_id}: {json.dumps(result, indent=2, default=str)}")
```

### 2. Direct Bedrock Inference Method
**File:** `autoninja/agents/requirements_analyst.py`  
**Method:** `_make_bedrock_inference()` (lines ~380-460)

This method performs the actual LLM inference:

```python
def _make_bedrock_inference(self, agent_input: str, execution_id: str) -> Dict[str, Any]:
    """Make direct inference call to Bedrock model with full request/response logging."""
    
    # Get the appropriate Bedrock model
    model_id = self.bedrock_client_manager.select_model_by_complexity(TaskComplexity.MEDIUM)
    
    # Prepare the messages for the model
    messages = [
        SystemMessage(content="""You are a Requirements Analyst specializing in extracting and structuring 
requirements from natural language descriptions..."""),
        HumanMessage(content=agent_input)
    ]
    
    # Log the raw request being sent to Bedrock
    raw_request = {
        "model_id": model_id.value,
        "messages": [{"role": msg.type, "content": msg.content} for msg in messages],
        "execution_id": execution_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(f"Raw Bedrock request for {execution_id}: {json.dumps(raw_request, indent=2)}")
    
    # Make the inference call using the Bedrock client manager
    response = self.bedrock_client_manager.invoke_with_retry(
        model_id=model_id,
        messages=messages
    )
    
    # Log the raw response from Bedrock
    raw_response = {
        "model_id": model_id.value,
        "response_content": response.content if hasattr(response, 'content') else str(response),
        "execution_id": execution_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(f"Raw Bedrock response for {execution_id}: {json.dumps(raw_response, indent=2)}")
```

## 📝 Raw Request/Response Logging

### Raw Request Logging
The system logs the complete request structure including:
- **Model ID**: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Messages**: System prompt + user input
- **Execution ID**: Unique identifier for tracking
- **Timestamp**: When the request was made

**Example Log Output:**
```json
{
  "model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "messages": [
    {
      "role": "system",
      "content": "You are a Requirements Analyst specializing in extracting and structuring requirements..."
    },
    {
      "role": "human", 
      "content": "I need a simple chatbot for customer support..."
    }
  ],
  "execution_id": "direct-inference-test_requirements_analyst_1759804024",
  "timestamp": "2025-10-06T22:27:04.997848"
}
```

### Raw Response Logging
The system logs the complete response from Bedrock:
- **Model ID**: Which model generated the response
- **Response Content**: The actual LLM output
- **Execution ID**: For correlation with the request
- **Timestamp**: When the response was received

**Example Log Output:**
```json
{
  "model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "response_content": "{\"extracted_requirements\": {...}, \"compliance_frameworks\": [...]}",
  "execution_id": "direct-inference-test_requirements_analyst_1759804024", 
  "timestamp": "2025-10-06T22:27:07.123456"
}
```

## 🔧 Model Selection and Configuration

### Model Selection Logic
**File:** `autoninja/core/bedrock_client.py`  
**Method:** `select_model_by_complexity()`

The agent automatically selects the appropriate Claude model:
- **TaskComplexity.MEDIUM** → **Claude Sonnet 4.5** (for requirements analysis)
- Includes retry logic and circuit breaker patterns
- Handles model availability and failover

### Bedrock Client Integration
**File:** `autoninja/core/bedrock_client.py`  
**Method:** `invoke_with_retry()`

Direct integration with Amazon Bedrock:
- Uses `ChatBedrock` from LangChain AWS
- Implements exponential backoff retry
- Circuit breaker for fault tolerance
- Comprehensive error handling

## 🧪 Testing and Verification

### Unit Tests
**File:** `tests/unit/test_direct_inference.py`

Tests verify:
- ✅ Direct Bedrock inference calls are made
- ✅ Raw requests are properly logged
- ✅ Raw responses are properly logged  
- ✅ Model selection works correctly
- ✅ Error handling is robust

### Integration Tests
**File:** `tests/integration/test_requirements_analyst_integration.py`

Real Bedrock API tests (with AWS credentials):
- ✅ End-to-end inference with real models
- ✅ Complex scenario handling
- ✅ Performance and reliability testing

### Demo Scripts
**File:** `examples/test_direct_inference.py`

Live demonstration showing:
- ✅ Real Bedrock API calls
- ✅ Complete request/response logging
- ✅ Model inference in action

## 🚀 How to Run and See the Inference

### 1. Run the Direct Inference Test
```bash
python examples/test_direct_inference.py
```

### 2. Run Integration Tests (requires AWS credentials)
```bash
python -m pytest tests/integration/test_requirements_analyst_integration.py -v
```

### 3. Run Unit Tests
```bash
python -m pytest tests/unit/test_direct_inference.py -v
```

## 📊 Key Features Implemented

✅ **Direct Bedrock Model Calls**: No abstraction layers, direct API calls  
✅ **Raw Request Logging**: Complete request structure with metadata  
✅ **Raw Response Logging**: Full model output with timestamps  
✅ **Model Selection**: Automatic Claude model selection based on complexity  
✅ **Retry Logic**: Exponential backoff with circuit breaker  
✅ **Error Handling**: Graceful degradation on API failures  
✅ **Tool Enhancement**: LLM output enhanced with specialized tools  
✅ **Comprehensive Testing**: Unit, integration, and demo tests  

## 🔍 Log Analysis

When you run the agent, look for these log entries:

1. **`Raw request for {execution_id}:`** - Shows the complete request sent to Bedrock
2. **`Raw Bedrock request for {execution_id}:`** - Shows the structured request with model details
3. **`Raw Bedrock response for {execution_id}:`** - Shows the complete response from the model
4. **`Raw response for {execution_id}:`** - Shows the processed response structure

The agent now provides complete transparency into the LLM inference process with full request/response logging as required by the task specifications.