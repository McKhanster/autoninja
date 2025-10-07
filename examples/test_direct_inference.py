#!/usr/bin/env python3
"""
Test Direct Bedrock Inference

This script tests the Requirements Analyst Agent making direct inference
calls to Amazon Bedrock models with full request/response logging.
"""

import sys
import logging
import json

# Add the project root to the path
sys.path.insert(0, '.')

from autoninja.agents.requirements_analyst import create_requirements_analyst_agent

# Configure logging to see the raw requests/responses
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_direct_inference():
    """Test direct Bedrock inference with raw request/response logging"""
    
    print("🧪 Testing Direct Bedrock Inference")
    print("="*50)
    
    # Create the agent
    agent = create_requirements_analyst_agent()
    
    # Simple test request
    user_request = "I need a simple chatbot for customer support that can answer basic questions about our products."
    
    print(f"User Request: {user_request}")
    print("\nMaking direct Bedrock inference call...")
    
    try:
        # This should now make a direct Bedrock call and log raw request/response
        result = agent.analyze_requirements(user_request, "direct-inference-test")
        
        print(f"\n✅ Direct inference completed successfully!")
        print(f"Confidence Score: {result.output.confidence_score}")
        print(f"Execution Time: {result.execution_metadata.duration_seconds:.2f}s")
        
        # Show some results
        output_data = result.output.result
        functional_reqs = output_data.get("extracted_requirements", {}).get("functional_requirements", [])
        print(f"\nExtracted {len(functional_reqs)} functional requirements:")
        for i, req in enumerate(functional_reqs[:3], 1):
            print(f"  {i}. {req}")
        
        print(f"\nRecommendations:")
        for i, rec in enumerate(result.output.recommendations[:3], 1):
            print(f"  {i}. {rec}")
            
        print(f"\n📝 Check the logs above for:")
        print(f"  - Raw Bedrock request with model_id, messages, and metadata")
        print(f"  - Raw Bedrock response with model output")
        print(f"  - Tool enhancement details")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        logger.error(f"Direct inference test failed: {str(e)}")

if __name__ == "__main__":
    test_direct_inference()