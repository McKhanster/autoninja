"""
Pipeline Logging for AutoNinja Agent Chain

Comprehensive logging system for agent pipelines that captures:
- Agent inputs and outputs for manual injection
- Pipeline state at each step
- Inference requests and responses
- Agent handoff data
- Pipeline recovery points
"""

import json
import logging
import pickle
import base64
from datetime import datetime
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

from autoninja.models.state import AgentOutput


class PipelineStage(str, Enum):
    """Pipeline stages for agent execution"""
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    SOLUTION_ARCHITECTURE = "solution_architecture"
    CODE_GENERATION = "code_generation"
    QUALITY_VALIDATION = "quality_validation"
    DEPLOYMENT_MANAGEMENT = "deployment_management"


@dataclass
class PipelineLogEntry:
    """Structured log entry for pipeline execution"""
    session_id: str
    execution_id: str
    stage: PipelineStage
    agent_name: str
    timestamp: str
    log_type: str  # 'input', 'output', 'inference_request', 'inference_response', 'error'
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class PipelineLogger:
    """
    Specialized logger for agent pipeline execution with manual injection support.
    
    This logger creates structured logs that allow for:
    1. Complete pipeline state reconstruction
    2. Manual injection of agent outputs
    3. Pipeline debugging and troubleshooting
    4. Agent performance analysis
    """
    
    def __init__(self, session_id: str, log_dir: Optional[Path] = None):
        self.session_id = session_id
        self.log_dir = log_dir or Path.cwd() / "logs" / "pipeline"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create session-specific log files
        self.session_log_file = self.log_dir / f"session_{session_id}.jsonl"
        self.inference_log_file = self.log_dir / f"inference_{session_id}.jsonl"
        self.pipeline_state_file = self.log_dir / f"state_{session_id}.json"
        
        # Initialize pipeline state
        self.pipeline_state = {
            "session_id": session_id,
            "created_at": datetime.now(UTC).isoformat(),
            "current_stage": None,
            "completed_stages": [],
            "agent_outputs": {},
            "pipeline_metadata": {}
        }
        
        self.logger = logging.getLogger(f"pipeline.{session_id}")
    
    def log_agent_input(
        self, 
        stage: PipelineStage, 
        agent_name: str, 
        execution_id: str,
        input_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log agent input data for pipeline debugging."""
        
        log_entry = PipelineLogEntry(
            session_id=self.session_id,
            execution_id=execution_id,
            stage=stage,
            agent_name=agent_name,
            timestamp=datetime.now(UTC).isoformat(),
            log_type="input",
            data=input_data,
            metadata=metadata or {}
        )
        
        self._write_log_entry(log_entry)
        self.logger.info(f"AGENT_INPUT [{stage}] {agent_name}: {execution_id}")
    
    def log_agent_output(
        self, 
        stage: PipelineStage, 
        agent_name: str, 
        execution_id: str,
        output_data: Union[AgentOutput, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log agent output data for pipeline handoff."""
        
        # Convert AgentOutput to dict if needed
        if isinstance(output_data, AgentOutput):
            output_dict = self._serialize_agent_output(output_data)
        else:
            output_dict = output_data
        
        log_entry = PipelineLogEntry(
            session_id=self.session_id,
            execution_id=execution_id,
            stage=stage,
            agent_name=agent_name,
            timestamp=datetime.now(UTC).isoformat(),
            log_type="output",
            data=output_dict,
            metadata=metadata or {}
        )
        
        self._write_log_entry(log_entry)
        
        # Update pipeline state
        self.pipeline_state["agent_outputs"][stage.value] = {
            "execution_id": execution_id,
            "agent_name": agent_name,
            "output": output_dict,
            "timestamp": log_entry.timestamp
        }
        self.pipeline_state["current_stage"] = stage.value
        if stage.value not in self.pipeline_state["completed_stages"]:
            self.pipeline_state["completed_stages"].append(stage.value)
        
        self._save_pipeline_state()
        
        self.logger.info(f"AGENT_OUTPUT [{stage}] {agent_name}: {execution_id}")
    
    def _serialize_agent_output(self, agent_output: AgentOutput) -> Dict[str, Any]:
        """Serialize AgentOutput with proper datetime handling."""
        import json
        
        def datetime_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        # Convert to dict and then serialize/deserialize to handle datetime objects
        output_dict = agent_output.model_dump()
        json_str = json.dumps(output_dict, default=datetime_serializer)
        return json.loads(json_str)
    
    def log_inference_request(
        self, 
        execution_id: str, 
        model_id: str,
        request_data: Dict[str, Any],
        agent_name: str,
        stage: PipelineStage
    ) -> None:
        """Log raw inference request for manual injection capability."""
        
        inference_entry = {
            "session_id": self.session_id,
            "execution_id": execution_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "inference_request",
            "stage": stage.value,
            "agent_name": agent_name,
            "model_id": model_id,
            "request_data": request_data
        }
        
        self._write_inference_log(inference_entry)
        self.logger.info(f"INFERENCE_REQUEST [{stage}] {agent_name} -> {model_id}: {execution_id}")
    
    def log_inference_response(
        self, 
        execution_id: str, 
        model_id: str,
        response_data: Dict[str, Any],
        agent_name: str,
        stage: PipelineStage,
        processing_time: Optional[float] = None
    ) -> None:
        """Log raw inference response for manual injection capability."""
        
        inference_entry = {
            "session_id": self.session_id,
            "execution_id": execution_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "inference_response",
            "stage": stage.value,
            "agent_name": agent_name,
            "model_id": model_id,
            "response_data": response_data,
            "processing_time_seconds": processing_time
        }
        
        self._write_inference_log(inference_entry)
        self.logger.info(f"INFERENCE_RESPONSE [{stage}] {agent_name} <- {model_id}: {execution_id}")
    
    def log_pipeline_error(
        self, 
        stage: PipelineStage, 
        agent_name: str, 
        execution_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log pipeline errors for debugging."""
        
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        
        log_entry = PipelineLogEntry(
            session_id=self.session_id,
            execution_id=execution_id,
            stage=stage,
            agent_name=agent_name,
            timestamp=datetime.now(UTC).isoformat(),
            log_type="error",
            data=error_data,
            metadata={}
        )
        
        self._write_log_entry(log_entry)
        self.logger.error(f"PIPELINE_ERROR [{stage}] {agent_name}: {error}")
    
    def create_injection_point(
        self, 
        stage: PipelineStage, 
        agent_name: str,
        description: str = ""
    ) -> str:
        """Create a manual injection point for pipeline debugging."""
        
        injection_id = f"inject_{stage.value}_{int(datetime.now(UTC).timestamp())}"
        
        injection_data = {
            "injection_id": injection_id,
            "session_id": self.session_id,
            "stage": stage.value,
            "agent_name": agent_name,
            "description": description,
            "timestamp": datetime.now(UTC).isoformat(),
            "pipeline_state_snapshot": self.pipeline_state.copy()
        }
        
        injection_file = self.log_dir / f"injection_point_{injection_id}.json"
        with open(injection_file, 'w') as f:
            json.dump(injection_data, f, indent=2)
        
        self.logger.info(f"INJECTION_POINT [{stage}] {agent_name}: {injection_id}")
        return injection_id
    
    def get_agent_output(self, stage: PipelineStage) -> Optional[Dict[str, Any]]:
        """Get the output from a specific pipeline stage."""
        return self.pipeline_state["agent_outputs"].get(stage.value)
    
    def get_pipeline_state(self) -> Dict[str, Any]:
        """Get the current pipeline state."""
        return self.pipeline_state.copy()
    
    def _write_log_entry(self, entry: PipelineLogEntry) -> None:
        """Write a log entry to the session log file."""
        with open(self.session_log_file, 'a') as f:
            f.write(json.dumps(asdict(entry), default=self._json_serializer) + '\n')
    
    def _json_serializer(self, obj):
        """JSON serializer for datetime and other non-serializable objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)
    
    def _write_inference_log(self, entry: Dict[str, Any]) -> None:
        """Write an inference log entry."""
        with open(self.inference_log_file, 'a') as f:
            f.write(json.dumps(entry, default=self._json_serializer) + '\n')
    
    def _save_pipeline_state(self) -> None:
        """Save the current pipeline state."""
        self.pipeline_state["updated_at"] = datetime.now(UTC).isoformat()
        with open(self.pipeline_state_file, 'w') as f:
            json.dump(self.pipeline_state, f, indent=2)


class PipelineLogReader:
    """
    Reader for pipeline logs that supports manual injection and debugging.
    """
    
    def __init__(self, session_id: str, log_dir: Optional[Path] = None):
        self.session_id = session_id
        self.log_dir = log_dir or Path.cwd() / "logs" / "pipeline"
        
        self.session_log_file = self.log_dir / f"session_{session_id}.jsonl"
        self.inference_log_file = self.log_dir / f"inference_{session_id}.jsonl"
        self.pipeline_state_file = self.log_dir / f"state_{session_id}.json"
    
    def get_agent_inputs(self, stage: Optional[PipelineStage] = None) -> List[Dict[str, Any]]:
        """Get all agent inputs, optionally filtered by stage."""
        return self._read_log_entries("input", stage)
    
    def get_agent_outputs(self, stage: Optional[PipelineStage] = None) -> List[Dict[str, Any]]:
        """Get all agent outputs, optionally filtered by stage."""
        return self._read_log_entries("output", stage)
    
    def get_inference_requests(self, stage: Optional[PipelineStage] = None) -> List[Dict[str, Any]]:
        """Get all inference requests for manual injection."""
        return self._read_inference_logs("inference_request", stage)
    
    def get_inference_responses(self, stage: Optional[PipelineStage] = None) -> List[Dict[str, Any]]:
        """Get all inference responses for analysis."""
        return self._read_inference_logs("inference_response", stage)
    
    def get_pipeline_state(self) -> Optional[Dict[str, Any]]:
        """Get the current pipeline state."""
        if self.pipeline_state_file.exists():
            with open(self.pipeline_state_file, 'r') as f:
                return json.load(f)
        return None
    
    def create_manual_injection_template(
        self, 
        stage: PipelineStage, 
        execution_id: str
    ) -> Dict[str, Any]:
        """Create a template for manual injection at a specific stage."""
        
        # Get the last inference request for this stage
        requests = self.get_inference_requests(stage)
        if not requests:
            raise ValueError(f"No inference requests found for stage {stage}")
        
        # Find the specific request
        target_request = None
        for req in requests:
            if req["execution_id"] == execution_id:
                target_request = req
                break
        
        if not target_request:
            raise ValueError(f"No inference request found for execution_id {execution_id}")
        
        # Create injection template
        template = {
            "injection_metadata": {
                "session_id": self.session_id,
                "stage": stage.value,
                "execution_id": execution_id,
                "original_request": target_request,
                "injection_timestamp": datetime.now(UTC).isoformat(),
                "instructions": "Replace 'manual_response_content' with your desired model output"
            },
            "manual_response": {
                "model_id": target_request["model_id"],
                "response_content": "REPLACE_WITH_MANUAL_RESPONSE",
                "execution_id": execution_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "injected": True
            }
        }
        
        return template
    
    def _read_log_entries(self, log_type: str, stage: Optional[PipelineStage] = None) -> List[Dict[str, Any]]:
        """Read log entries of a specific type."""
        entries = []
        
        if not self.session_log_file.exists():
            return entries
        
        with open(self.session_log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry["log_type"] == log_type:
                        if stage is None or entry["stage"] == stage.value:
                            entries.append(entry)
                except json.JSONDecodeError:
                    continue
        
        return entries
    
    def _read_inference_logs(self, log_type: str, stage: Optional[PipelineStage] = None) -> List[Dict[str, Any]]:
        """Read inference logs of a specific type."""
        entries = []
        
        if not self.inference_log_file.exists():
            return entries
        
        with open(self.inference_log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry["type"] == log_type:
                        if stage is None or entry["stage"] == stage.value:
                            entries.append(entry)
                except json.JSONDecodeError:
                    continue
        
        return entries


# Global pipeline logger registry
_pipeline_loggers: Dict[str, PipelineLogger] = {}


def get_pipeline_logger(session_id: str) -> PipelineLogger:
    """Get or create a pipeline logger for a session."""
    if session_id not in _pipeline_loggers:
        _pipeline_loggers[session_id] = PipelineLogger(session_id)
    return _pipeline_loggers[session_id]


def get_pipeline_reader(session_id: str) -> PipelineLogReader:
    """Get a pipeline log reader for a session."""
    return PipelineLogReader(session_id)