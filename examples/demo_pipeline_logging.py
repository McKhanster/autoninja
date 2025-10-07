#!/usr/bin/env python3
"""
Pipeline Logging Demonstration

This script demonstrates the comprehensive pipeline logging system that captures
all agent inputs, outputs, and inference calls for manual injection capability.
"""

import sys
import json
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, '.')

from autoninja.agents.requirements_analyst import create_requirements_analyst_agent
from autoninja.core.pipeline_logging import get_pipeline_logger, get_pipeline_reader, PipelineStage


def demonstrate_pipeline_logging():
    """Demonstrate the complete pipeline logging system."""
    
    print("🚀 Pipeline Logging Demonstration")
    print("=" * 60)
    
    session_id = "demo-pipeline-logging"
    
    # Show log directory structure
    log_dir = Path.cwd() / "logs" / "pipeline"
    print(f"📁 Pipeline logs will be saved to: {log_dir.absolute()}")
    print(f"   Session log: session_{session_id}.jsonl")
    print(f"   Inference log: inference_{session_id}.jsonl")
    print(f"   Pipeline state: state_{session_id}.json")
    print()
    
    # Create Requirements Analyst Agent
    print("🤖 Creating Requirements Analyst Agent...")
    agent = create_requirements_analyst_agent()
    
    # Test user request
    user_request = """
    I need an AI agent for my e-commerce platform that can:
    1. Handle customer inquiries about products and orders
    2. Process return requests and refunds
    3. Integrate with our inventory management system
    4. Support multiple languages (English, Spanish, French)
    5. Comply with GDPR and CCPA regulations
    6. Handle 10,000+ daily interactions
    
    The system should be scalable, secure, and provide detailed analytics.
    Budget: $100,000 for initial implementation.
    """
    
    additional_context = {
        "industry": "e-commerce",
        "platform": "Shopify",
        "languages": ["English", "Spanish", "French"],
        "compliance": ["GDPR", "CCPA"],
        "scale": "10000_daily_interactions",
        "budget": "$100,000"
    }
    
    print(f"📝 Test Request: E-commerce customer service agent")
    print(f"💰 Budget: $100,000")
    print(f"🌍 Languages: English, Spanish, French")
    print(f"📊 Scale: 10,000+ daily interactions")
    print()
    
    # Execute the agent (this will create comprehensive logs)
    print("⚡ Executing Requirements Analyst Agent...")
    print("   (This will log all inputs, outputs, and inference calls)")
    
    try:
        result = agent.analyze_requirements(user_request, session_id, additional_context)
        
        print(f"✅ Analysis completed successfully!")
        print(f"   Confidence Score: {result.output.confidence_score:.2f}")
        print(f"   Execution Time: {result.execution_metadata.duration_seconds:.2f}s")
        print(f"   Recommendations: {len(result.output.recommendations)}")
        
    except Exception as e:
        print(f"⚠️  Analysis completed with errors (expected): {str(e)}")
        print(f"   Error details logged for debugging")
    
    print()
    
    # Show what was logged
    print("📋 Pipeline Logging Results:")
    print("=" * 40)
    
    reader = get_pipeline_reader(session_id)
    
    # Show pipeline state
    state = reader.get_pipeline_state()
    if state:
        print(f"📊 Pipeline State:")
        print(f"   Session ID: {state['session_id']}")
        print(f"   Current Stage: {state.get('current_stage', 'None')}")
        print(f"   Completed Stages: {', '.join(state.get('completed_stages', []))}")
        print(f"   Agent Outputs: {len(state.get('agent_outputs', {}))}")
        print()
    
    # Show logged data
    inputs = reader.get_agent_inputs(PipelineStage.REQUIREMENTS_ANALYSIS)
    outputs = reader.get_agent_outputs(PipelineStage.REQUIREMENTS_ANALYSIS)
    requests = reader.get_inference_requests(PipelineStage.REQUIREMENTS_ANALYSIS)
    responses = reader.get_inference_responses(PipelineStage.REQUIREMENTS_ANALYSIS)
    
    print(f"📥 Agent Inputs Logged: {len(inputs)}")
    if inputs:
        for inp in inputs:
            print(f"   - {inp['execution_id']} ({inp['agent_name']})")
    
    print(f"📤 Agent Outputs Logged: {len(outputs)}")
    if outputs:
        for out in outputs:
            print(f"   - {out['execution_id']} ({out['agent_name']})")
    
    print(f"🔍 Inference Requests Logged: {len(requests)}")
    if requests:
        for req in requests:
            print(f"   - {req['execution_id']} -> {req['model_id']}")
    
    print(f"📨 Inference Responses Logged: {len(responses)}")
    if responses:
        for resp in responses:
            print(f"   - {resp['execution_id']} <- {resp['model_id']} ({resp.get('processing_time_seconds', 0):.2f}s)")
    
    print()
    
    # Show manual injection capabilities
    print("🔧 Manual Injection Capabilities:")
    print("=" * 40)
    
    if requests:
        execution_id = requests[0]['execution_id']
        print(f"💉 You can manually inject responses for:")
        print(f"   Session: {session_id}")
        print(f"   Stage: requirements_analysis")
        print(f"   Execution ID: {execution_id}")
        print()
        print(f"🛠️  Commands to use:")
        print(f"   1. Create injection template:")
        print(f"      python examples/pipeline_manual_injection.py template \\")
        print(f"        --session-id {session_id} \\")
        print(f"        --stage requirements_analysis \\")
        print(f"        --execution-id {execution_id}")
        print()
        print(f"   2. List all sessions:")
        print(f"      python examples/pipeline_manual_injection.py list")
        print()
        print(f"   3. Show session details:")
        print(f"      python examples/pipeline_manual_injection.py show --session-id {session_id}")
    
    # Show log file contents
    print()
    print("📄 Log File Locations:")
    print("=" * 40)
    
    log_files = [
        ("Session Log", log_dir / f"session_{session_id}.jsonl"),
        ("Inference Log", log_dir / f"inference_{session_id}.jsonl"),
        ("Pipeline State", log_dir / f"state_{session_id}.json")
    ]
    
    for name, log_file in log_files:
        if log_file.exists():
            size = log_file.stat().st_size
            print(f"✅ {name}: {log_file} ({size} bytes)")
        else:
            print(f"❌ {name}: Not created")
    
    print()
    print("🎯 Key Benefits of Pipeline Logging:")
    print("=" * 40)
    print("✅ Complete agent input/output capture for debugging")
    print("✅ Raw inference request/response logging")
    print("✅ Manual injection capability for testing")
    print("✅ Pipeline state reconstruction")
    print("✅ Agent performance analysis")
    print("✅ Error debugging and troubleshooting")
    print("✅ Agent handoff data validation")
    
    print()
    print("💡 Use Cases:")
    print("- Debug agent pipeline failures")
    print("- Test agents with known good/bad inputs")
    print("- Bypass expensive model calls during development")
    print("- Validate agent handoff data")
    print("- Analyze agent performance and bottlenecks")
    print("- Create test fixtures from real pipeline runs")


if __name__ == "__main__":
    demonstrate_pipeline_logging()