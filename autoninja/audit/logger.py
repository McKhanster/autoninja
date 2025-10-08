"""
Audit-specific logging for the multi-agent pipeline system.

Extends the core logging system with audit-specific functionality for
pipeline execution tracking, validation logging, and audit trail generation.
"""

import logging
import logging.handlers
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict

from ..core.logging_config import get_session_logger, AutoNinjaFormatter
from .config import AuditConfig, ExecutionStatus, AgentStatus


@dataclass
class AuditEvent:
    """Represents a single audit event in the pipeline."""
    timestamp: datetime
    event_type: str
    session_id: str
    execution_id: Optional[str]
    agent_name: Optional[str]
    event_data: Dict[str, Any]
    severity: str = "INFO"


@dataclass
class ValidationEvent:
    """Represents a validation event."""
    timestamp: datetime
    session_id: str
    agent_name: str
    validation_type: str
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    compatibility_score: Optional[float] = None


@dataclass
class PerformanceEvent:
    """Represents a performance monitoring event."""
    timestamp: datetime
    session_id: str
    agent_name: str
    execution_time_seconds: float
    memory_usage_mb: Optional[float]
    bedrock_calls: int
    bedrock_response_time_seconds: float
    tokens_used: int


class PipelineAuditLogger:
    """
    Comprehensive audit logging for the multi-agent pipeline.
    
    Provides structured logging for pipeline execution, validation results,
    performance metrics, and audit trail generation.
    """
    
    def __init__(self, config: AuditConfig):
        """Initialize the audit logger with configuration."""
        self.config = config
        self.audit_events: List[AuditEvent] = []
        self.validation_events: List[ValidationEvent] = []
        self.performance_events: List[PerformanceEvent] = []
        
        # Set up audit-specific loggers
        self._setup_audit_loggers()
    
    def _setup_audit_loggers(self) -> None:
        """Set up audit-specific logging handlers."""
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Audit logger for structured audit events
        self.audit_logger = logging.getLogger("autoninja.audit")
        if not self.audit_logger.handlers:
            audit_handler = logging.handlers.RotatingFileHandler(
                log_dir / "audit.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            audit_formatter = AutoNinjaFormatter(
                fmt='%(asctime)s - AUDIT - %(levelname)s - %(session_info)s%(exec_info)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            audit_handler.setFormatter(audit_formatter)
            self.audit_logger.addHandler(audit_handler)
            self.audit_logger.setLevel(getattr(logging, self.config.log_level.value))
    
    def log_pipeline_start(self, session_id: str, user_request: str) -> None:
        """Log the start of a pipeline execution."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="PIPELINE_START",
            session_id=session_id,
            execution_id=None,
            agent_name=None,
            event_data={
                "user_request": user_request,
                "config": asdict(self.config)
            }
        )
        self.audit_events.append(event)
        
        session_logger = get_session_logger(session_id)
        session_logger.info(f"Pipeline started with request: {user_request}")
        self.audit_logger.info(f"PIPELINE_START [{session_id}]: {user_request}")
    
    def log_pipeline_completion(self, session_id: str, status: ExecutionStatus, 
                              execution_time_seconds: float, final_output: Optional[Dict] = None) -> None:
        """Log the completion of a pipeline execution."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="PIPELINE_COMPLETE",
            session_id=session_id,
            execution_id=None,
            agent_name=None,
            event_data={
                "status": status.value,
                "execution_time_seconds": execution_time_seconds,
                "has_output": final_output is not None
            }
        )
        self.audit_events.append(event)
        
        session_logger = get_session_logger(session_id)
        session_logger.info(f"Pipeline completed with status: {status.value} in {execution_time_seconds:.2f}s")
        self.audit_logger.info(f"PIPELINE_COMPLETE [{session_id}]: {status.value} ({execution_time_seconds:.2f}s)")
    
    def log_agent_execution_start(self, session_id: str, execution_id: str, 
                                agent_name: str, input_data: Dict[str, Any]) -> None:
        """Log the start of an agent execution."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="AGENT_START",
            session_id=session_id,
            execution_id=execution_id,
            agent_name=agent_name,
            event_data={
                "input_keys": list(input_data.keys()),
                "input_size": len(str(input_data))
            }
        )
        self.audit_events.append(event)
        
        session_logger = get_session_logger(session_id, execution_id)
        session_logger.info(f"Agent {agent_name} started execution")
        self.audit_logger.info(f"AGENT_START [{session_id}][{execution_id}] {agent_name}")
    
    def log_agent_execution_complete(self, session_id: str, execution_id: str,
                                   agent_name: str, status: AgentStatus, 
                                   output_data: Optional[Dict[str, Any]] = None,
                                   execution_time_seconds: Optional[float] = None) -> None:
        """Log the completion of an agent execution."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="AGENT_COMPLETE",
            session_id=session_id,
            execution_id=execution_id,
            agent_name=agent_name,
            event_data={
                "status": status.value,
                "has_output": output_data is not None,
                "output_keys": list(output_data.keys()) if output_data else [],
                "execution_time_seconds": execution_time_seconds
            }
        )
        self.audit_events.append(event)
        
        session_logger = get_session_logger(session_id, execution_id)
        session_logger.info(f"Agent {agent_name} completed with status: {status.value}")
        self.audit_logger.info(f"AGENT_COMPLETE [{session_id}][{execution_id}] {agent_name}: {status.value}")
    
    def log_validation_result(self, session_id: str, agent_name: str, 
                            validation_type: str, is_valid: bool,
                            errors: List[str], warnings: List[str],
                            compatibility_score: Optional[float] = None) -> None:
        """Log validation results."""
        event = ValidationEvent(
            timestamp=datetime.now(),
            session_id=session_id,
            agent_name=agent_name,
            validation_type=validation_type,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            compatibility_score=compatibility_score
        )
        self.validation_events.append(event)
        
        session_logger = get_session_logger(session_id)
        status = "PASSED" if is_valid else "FAILED"
        session_logger.info(f"Validation {validation_type} for {agent_name}: {status}")
        
        if errors:
            session_logger.warning(f"Validation errors for {agent_name}: {errors}")
        if warnings:
            session_logger.info(f"Validation warnings for {agent_name}: {warnings}")
        
        self.audit_logger.info(
            f"VALIDATION [{session_id}] {agent_name} {validation_type}: {status} "
            f"(errors: {len(errors)}, warnings: {len(warnings)})"
        )
    
    def log_error(self, session_id: str, error_type: str, error_message: str,
                  agent_name: Optional[str] = None, execution_id: Optional[str] = None,
                  error_context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error event."""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="ERROR",
            session_id=session_id,
            execution_id=execution_id,
            agent_name=agent_name,
            event_data={
                "error_type": error_type,
                "error_message": error_message,
                "error_context": error_context or {}
            },
            severity="ERROR"
        )
        self.audit_events.append(event)
        
        session_logger = get_session_logger(session_id, execution_id)
        session_logger.error(f"ERROR in {agent_name or 'pipeline'}: {error_type} - {error_message}")
        self.audit_logger.error(f"ERROR [{session_id}] {agent_name or 'PIPELINE'}: {error_type} - {error_message}")
    
    def generate_execution_report(self, session_id: str) -> Dict[str, Any]:
        """Generate a comprehensive execution report for a session."""
        session_events = [e for e in self.audit_events if e.session_id == session_id]
        session_validations = [v for v in self.validation_events if v.session_id == session_id]
        session_performance = [p for p in self.performance_events if p.session_id == session_id]
        
        # Calculate summary statistics
        total_execution_time = 0.0
        agent_executions = {}
        validation_summary = {"passed": 0, "failed": 0, "warnings": 0}
        
        for event in session_events:
            if event.event_type == "AGENT_COMPLETE" and "execution_time_seconds" in event.event_data:
                total_execution_time += event.event_data.get("execution_time_seconds", 0.0)
                agent_executions[event.agent_name] = event.event_data
        
        for validation in session_validations:
            if validation.is_valid:
                validation_summary["passed"] += 1
            else:
                validation_summary["failed"] += 1
            validation_summary["warnings"] += len(validation.warnings)
        
        report = {
            "session_id": session_id,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_execution_time_seconds": total_execution_time,
                "total_events": len(session_events),
                "agent_executions": len(agent_executions),
                "validation_summary": validation_summary
            },
            "events": [asdict(e) for e in session_events],
            "validations": [asdict(v) for v in session_validations],
            "performance": [asdict(p) for p in session_performance],
            "agent_summary": agent_executions
        }
        
        return report
    
    def save_execution_report(self, session_id: str, output_file: Optional[str] = None) -> str:
        """Save execution report to a JSON file."""
        report = self.generate_execution_report(session_id)
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"logs/audit_report_{session_id}_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.audit_logger.info(f"Execution report saved: {output_path}")
        return str(output_path)


def get_audit_logger(config: AuditConfig) -> PipelineAuditLogger:
    """Get a configured audit logger instance."""
    return PipelineAuditLogger(config)