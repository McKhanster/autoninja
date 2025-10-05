"""
Example usage of Bedrock client configuration.

This module provides examples of how to use the BedrockClientManager
for different scenarios and task complexities.
"""

import asyncio
import logging
from typing import List, Dict, Any

from autoninja.core.bedrock_client import (
    BedrockClientManager,
    BedrockClientConfig,
    TaskComplexity,
    BedrockModelId,
    get_bedrock_client_manager
)
from autoninja.core.config import settings

logger = logging.getLogger(__name__)


async def example_simple_invocation():
    """Example of simple model invocation with automatic model selection."""
    try:
        # Get the global client manager
        manager = get_bedrock_client_manager()
        
        # Select model based on task complexity
        model_id = manager.select_model_by_complexity(TaskComplexity.MEDIUM)
        
        # Prepare messages
        messages = [
            {"role": "user", "content": "Explain the benefits of serverless architecture in 3 bullet points."}
        ]
        
        # Invoke with retry logic
        response = manager.invoke_with_retry(model_id, messages)
        
        logger.info(f"Model response: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to invoke model: {str(e)}")
        raise


async def example_complex_task_invocation():
    """Example of complex task invocation using high-performance model."""
    try:
        # Get the client manager with custom configuration
        config = BedrockClientConfig(
            region_name="us-east-2",
            max_tokens=8192,
            temperature=0.2,
            timeout=600  # Longer timeout for complex tasks
        )
        manager = BedrockClientManager(config)
        
        # Use high-performance model for complex task
        model_id = manager.select_model_by_complexity(TaskComplexity.HIGH)
        
        # Complex architectural analysis prompt
        messages = [
            {
                "role": "user", 
                "content": """
                Design a comprehensive AWS architecture for a multi-tenant SaaS application 
                that needs to handle 100,000+ concurrent users, process real-time data streams, 
                maintain GDPR compliance, and provide 99.99% availability. Include:
                
                1. Compute and container orchestration strategy
                2. Database design with read replicas and caching
                3. Security architecture with zero-trust principles
                4. Monitoring and observability setup
                5. Disaster recovery and backup strategies
                6. Cost optimization recommendations
                
                Provide detailed CloudFormation template snippets for key components.
                """
            }
        ]
        
        # Invoke with retry logic
        response = manager.invoke_with_retry(model_id, messages)
        
        logger.info(f"Complex task completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Failed to complete complex task: {str(e)}")
        raise


async def example_model_fallback():
    """Example of handling model failures with fallback strategy."""
    try:
        manager = get_bedrock_client_manager()
        
        # List of models to try in order of preference
        preferred_models = [
            BedrockModelId.CLAUDE_OPUS_4_1,      # First choice for high quality
            BedrockModelId.CLAUDE_SONNET_4_5,    # Fallback for good performance
            BedrockModelId.CLAUDE_HAIKU_3        # Last resort for basic functionality
        ]
        
        messages = [
            {"role": "user", "content": "Generate a Python function to validate email addresses using regex."}
        ]
        
        response = None
        last_error = None
        
        for model_id in preferred_models:
            try:
                # Check if model is available
                available_models = manager.get_available_models()
                if model_id not in available_models:
                    logger.warning(f"Model {model_id.value} not available, trying next option")
                    continue
                
                # Try to invoke the model
                response = manager.invoke_with_retry(model_id, messages)
                logger.info(f"Successfully used model: {model_id.value}")
                break
                
            except Exception as e:
                last_error = e
                logger.warning(f"Model {model_id.value} failed: {str(e)}, trying next option")
                continue
        
        if response is None:
            raise RuntimeError(f"All models failed. Last error: {str(last_error)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Model fallback strategy failed: {str(e)}")
        raise


async def example_batch_processing():
    """Example of processing multiple requests with optimal model selection."""
    try:
        manager = get_bedrock_client_manager()
        
        # Different types of tasks with varying complexity
        tasks = [
            {
                "complexity": TaskComplexity.LOW,
                "prompt": "What is the capital of France?"
            },
            {
                "complexity": TaskComplexity.MEDIUM,
                "prompt": "Explain the differences between REST and GraphQL APIs."
            },
            {
                "complexity": TaskComplexity.HIGH,
                "prompt": "Design a microservices architecture for an e-commerce platform with detailed service boundaries and communication patterns."
            },
            {
                "complexity": TaskComplexity.LOW,
                "prompt": "Convert 100 USD to EUR (approximate)."
            },
            {
                "complexity": TaskComplexity.CRITICAL,
                "prompt": "Analyze the security implications of implementing OAuth 2.0 with PKCE in a mobile application and provide a comprehensive implementation guide."
            }
        ]
        
        results = []
        
        for i, task in enumerate(tasks):
            try:
                # Select appropriate model for task complexity
                model_id = manager.select_model_by_complexity(task["complexity"])
                
                messages = [{"role": "user", "content": task["prompt"]}]
                
                # Process the task
                response = manager.invoke_with_retry(model_id, messages)
                
                results.append({
                    "task_id": i,
                    "complexity": task["complexity"].value,
                    "model_used": model_id.value,
                    "response": response,
                    "status": "success"
                })
                
                logger.info(f"Completed task {i} with complexity {task['complexity'].value}")
                
            except Exception as e:
                results.append({
                    "task_id": i,
                    "complexity": task["complexity"].value,
                    "error": str(e),
                    "status": "failed"
                })
                
                logger.error(f"Failed task {i}: {str(e)}")
        
        # Summary statistics
        successful_tasks = [r for r in results if r["status"] == "success"]
        failed_tasks = [r for r in results if r["status"] == "failed"]
        
        logger.info(f"Batch processing completed: {len(successful_tasks)} successful, {len(failed_tasks)} failed")
        
        return {
            "results": results,
            "summary": {
                "total_tasks": len(tasks),
                "successful": len(successful_tasks),
                "failed": len(failed_tasks),
                "success_rate": len(successful_tasks) / len(tasks) * 100
            }
        }
        
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        raise


async def example_monitoring_and_status():
    """Example of monitoring client status and health."""
    try:
        manager = get_bedrock_client_manager()
        
        # Get overall client status
        status = manager.get_client_status()
        
        logger.info("=== Bedrock Client Status ===")
        for model_id, model_status in status.items():
            logger.info(f"Model: {model_id}")
            logger.info(f"  Available: {model_status['available']}")
            logger.info(f"  Circuit Breaker: {model_status['circuit_breaker_state']}")
            logger.info(f"  Failure Count: {model_status['failure_count']}")
            logger.info(f"  Last Failure: {model_status['last_failure_time']}")
            logger.info("---")
        
        # Get available models
        available_models = manager.get_available_models()
        logger.info(f"Available models: {[m.value for m in available_models]}")
        
        # Health check - try a simple invocation on each available model
        health_results = {}
        
        for model_id in available_models:
            try:
                messages = [{"role": "user", "content": "Hello, are you working?"}]
                response = manager.invoke_with_retry(model_id, messages)
                health_results[model_id.value] = "healthy"
                logger.info(f"Health check passed for {model_id.value}")
                
            except Exception as e:
                health_results[model_id.value] = f"unhealthy: {str(e)}"
                logger.warning(f"Health check failed for {model_id.value}: {str(e)}")
        
        return {
            "client_status": status,
            "available_models": [m.value for m in available_models],
            "health_check": health_results
        }
        
    except Exception as e:
        logger.error(f"Status monitoring failed: {str(e)}")
        raise


async def main():
    """Run all examples."""
    logger.info("Starting Bedrock client examples...")
    
    try:
        # Simple invocation
        logger.info("\n=== Example 1: Simple Invocation ===")
        await example_simple_invocation()
        
        # Complex task
        logger.info("\n=== Example 2: Complex Task ===")
        await example_complex_task_invocation()
        
        # Model fallback
        logger.info("\n=== Example 3: Model Fallback ===")
        await example_model_fallback()
        
        # Batch processing
        logger.info("\n=== Example 4: Batch Processing ===")
        batch_results = await example_batch_processing()
        logger.info(f"Batch processing summary: {batch_results['summary']}")
        
        # Monitoring and status
        logger.info("\n=== Example 5: Monitoring and Status ===")
        await example_monitoring_and_status()
        
        logger.info("\nAll examples completed successfully!")
        
    except Exception as e:
        logger.error(f"Examples failed: {str(e)}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run examples
    asyncio.run(main())