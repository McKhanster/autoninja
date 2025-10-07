#!/usr/bin/env python3
"""
Pipeline Manual Injection Utility

This utility allows you to manually inject inference results into the agent pipeline
for debugging, testing, and bypassing model calls when needed.

Usage:
    python examples/pipeline_manual_injection.py <session_id> <stage> <execution_id>
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, UTC

# Add the project root to the path
sys.path.insert(0, '.')

from autoninja.core.pipeline_logging import get_pipeline_reader, PipelineStage


def list_sessions():
    """List all available pipeline sessions."""
    log_dir = Path.cwd() / "logs" / "pipeline"
    if not log_dir.exists():
        print("❌ No pipeline logs directory found")
        return
    
    session_files = list(log_dir.glob("session_*.jsonl"))
    if not session_files:
        print("❌ No pipeline sessions found")
        return
    
    print("📋 Available Pipeline Sessions:")
    print("=" * 50)
    
    for session_file in session_files:
        session_id = session_file.stem.replace("session_", "")
        state_file = log_dir / f"state_{session_id}.json"
        
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            print(f"🔍 Session: {session_id}")
            print(f"   Created: {state.get('created_at', 'Unknown')}")
            print(f"   Current Stage: {state.get('current_stage', 'Unknown')}")
            print(f"   Completed Stages: {', '.join(state.get('completed_stages', []))}")
            print(f"   Agent Outputs: {len(state.get('agent_outputs', {}))}")
            print()


def show_session_details(session_id: str):
    """Show detailed information about a pipeline session."""
    reader = get_pipeline_reader(session_id)
    
    print(f"📊 Pipeline Session Details: {session_id}")
    print("=" * 60)
    
    # Show pipeline state
    state = reader.get_pipeline_state()
    if state:
        print(f"📈 Pipeline State:")
        print(f"   Created: {state.get('created_at')}")
        print(f"   Updated: {state.get('updated_at')}")
        print(f"   Current Stage: {state.get('current_stage')}")
        print(f"   Completed Stages: {', '.join(state.get('completed_stages', []))}")
        print()
    
    # Show agent inputs/outputs
    for stage in PipelineStage:
        inputs = reader.get_agent_inputs(stage)
        outputs = reader.get_agent_outputs(stage)
        requests = reader.get_inference_requests(stage)
        responses = reader.get_inference_responses(stage)
        
        if inputs or outputs or requests or responses:
            print(f"🔧 Stage: {stage.value}")
            print(f"   Inputs: {len(inputs)}")
            print(f"   Outputs: {len(outputs)}")
            print(f"   Inference Requests: {len(requests)}")
            print(f"   Inference Responses: {len(responses)}")
            
            # Show execution IDs for manual injection
            if requests:
                print(f"   Available for injection:")
                for req in requests:
                    print(f"     - {req['execution_id']} ({req['agent_name']})")
            print()


def show_inference_requests(session_id: str, stage: str):
    """Show inference requests for a specific stage."""
    try:
        pipeline_stage = PipelineStage(stage)
    except ValueError:
        print(f"❌ Invalid stage: {stage}")
        print(f"   Valid stages: {', '.join([s.value for s in PipelineStage])}")
        return
    
    reader = get_pipeline_reader(session_id)
    requests = reader.get_inference_requests(pipeline_stage)
    
    if not requests:
        print(f"❌ No inference requests found for stage {stage}")
        return
    
    print(f"🔍 Inference Requests for {stage}:")
    print("=" * 50)
    
    for i, req in enumerate(requests, 1):
        print(f"📤 Request {i}:")
        print(f"   Execution ID: {req['execution_id']}")
        print(f"   Agent: {req['agent_name']}")
        print(f"   Model: {req['model_id']}")
        print(f"   Timestamp: {req['timestamp']}")
        print(f"   Messages: {len(req['request_data'].get('messages', []))}")
        print()


def create_injection_template(session_id: str, stage: str, execution_id: str):
    """Create a manual injection template."""
    try:
        pipeline_stage = PipelineStage(stage)
    except ValueError:
        print(f"❌ Invalid stage: {stage}")
        return
    
    reader = get_pipeline_reader(session_id)
    
    try:
        template = reader.create_manual_injection_template(pipeline_stage, execution_id)
        
        # Save template to file
        template_file = Path.cwd() / "logs" / "pipeline" / f"injection_template_{session_id}_{stage}_{execution_id}.json"
        with open(template_file, 'w') as f:
            json.dump(template, f, indent=2)
        
        print(f"✅ Injection template created: {template_file}")
        print()
        print("📝 Instructions:")
        print("1. Edit the template file")
        print("2. Replace 'REPLACE_WITH_MANUAL_RESPONSE' with your desired model output")
        print("3. Use the inject_response() function to apply the injection")
        print()
        print("🔧 Template structure:")
        print(f"   Session: {template['injection_metadata']['session_id']}")
        print(f"   Stage: {template['injection_metadata']['stage']}")
        print(f"   Execution ID: {template['injection_metadata']['execution_id']}")
        print(f"   Original Model: {template['manual_response']['model_id']}")
        
    except Exception as e:
        print(f"❌ Error creating injection template: {e}")


def inject_response(template_file: str):
    """Inject a manual response using a template file."""
    template_path = Path(template_file)
    if not template_path.exists():
        print(f"❌ Template file not found: {template_file}")
        return
    
    with open(template_path, 'r') as f:
        template = json.load(f)
    
    # Validate template
    if template['manual_response']['response_content'] == "REPLACE_WITH_MANUAL_RESPONSE":
        print("❌ Template not completed - please replace 'REPLACE_WITH_MANUAL_RESPONSE' with actual content")
        return
    
    # Create injection log entry
    session_id = template['injection_metadata']['session_id']
    execution_id = template['injection_metadata']['execution_id']
    stage = template['injection_metadata']['stage']
    
    injection_log = Path.cwd() / "logs" / "pipeline" / f"manual_injection_{session_id}_{stage}_{execution_id}.json"
    
    injection_data = {
        "injection_metadata": template['injection_metadata'],
        "injected_response": template['manual_response'],
        "injection_applied_at": datetime.now(UTC).isoformat(),
        "status": "injected"
    }
    
    with open(injection_log, 'w') as f:
        json.dump(injection_data, f, indent=2)
    
    print(f"✅ Manual injection applied: {injection_log}")
    print(f"🔧 Injected response for execution {execution_id} in stage {stage}")
    print()
    print("💡 The injected response can now be used by downstream agents")
    print("   Check the pipeline logs to see the injection in action")


def main():
    parser = argparse.ArgumentParser(description="Pipeline Manual Injection Utility")
    parser.add_argument("command", choices=["list", "show", "requests", "template", "inject"], 
                       help="Command to execute")
    parser.add_argument("--session-id", help="Pipeline session ID")
    parser.add_argument("--stage", help="Pipeline stage")
    parser.add_argument("--execution-id", help="Execution ID for injection")
    parser.add_argument("--template-file", help="Template file for injection")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_sessions()
    
    elif args.command == "show":
        if not args.session_id:
            print("❌ --session-id required for show command")
            return
        show_session_details(args.session_id)
    
    elif args.command == "requests":
        if not args.session_id or not args.stage:
            print("❌ --session-id and --stage required for requests command")
            return
        show_inference_requests(args.session_id, args.stage)
    
    elif args.command == "template":
        if not args.session_id or not args.stage or not args.execution_id:
            print("❌ --session-id, --stage, and --execution-id required for template command")
            return
        create_injection_template(args.session_id, args.stage, args.execution_id)
    
    elif args.command == "inject":
        if not args.template_file:
            print("❌ --template-file required for inject command")
            return
        inject_response(args.template_file)


if __name__ == "__main__":
    main()