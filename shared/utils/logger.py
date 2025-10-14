"""
Structured logging utilities for AutoNinja.

This module provides structured logging in JSON format with consistent
fields for job_name, agent_name, and action_name for easy querying
and analysis.
"""

import os
import json
import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs with consistent fields.
    """
    
    def __init__(
        self,
        name: str,
        job_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        action_name: Optional[str] = None,
        level: Optional[str] = None
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically __name__)
            job_name: Optional job identifier
            agent_name: Optional agent name
            action_name: Optional action name
            level: Optional log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        
        # Set log level from parameter or environment variable
        log_level = level or os.environ.get('LOG_LEVEL', 'INFO')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []
        
        # Create console handler with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        
        # Store context fields
        self.context = {
            'job_name': job_name,
            'agent_name': agent_name,
            'action_name': action_name
        }
    
    def _log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Internal logging method that adds context fields.
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            extra: Additional fields to include
            **kwargs: Additional keyword arguments
        """
        # Merge context with extra fields
        log_extra = {**self.context}
        if extra:
            log_extra.update(extra)
        if kwargs:
            log_extra.update(kwargs)
        
        # Get the logging method
        log_method = getattr(self.logger, level)
        
        # Log with extra fields
        log_method(message, extra={'custom_fields': log_extra})
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log('critical', message, **kwargs)
    
    def set_context(
        self,
        job_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        action_name: Optional[str] = None
    ):
        """
        Update context fields for subsequent log messages.
        
        Args:
            job_name: Job identifier
            agent_name: Agent name
            action_name: Action name
        """
        if job_name is not None:
            self.context['job_name'] = job_name
        if agent_name is not None:
            self.context['agent_name'] = agent_name
        if action_name is not None:
            self.context['action_name'] = action_name


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add custom fields if present
        if hasattr(record, 'custom_fields'):
            log_data.update(record.custom_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


def get_logger(
    name: str,
    job_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    action_name: Optional[str] = None
) -> StructuredLogger:
    """
    Get or create a structured logger.
    
    Args:
        name: Logger name (typically __name__)
        job_name: Optional job identifier
        agent_name: Optional agent name
        action_name: Optional action name
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(
        name=name,
        job_name=job_name,
        agent_name=agent_name,
        action_name=action_name
    )


def log_lambda_event(
    logger: StructuredLogger,
    event: Dict[str, Any],
    context: Any
):
    """
    Log Lambda invocation event details.
    
    Args:
        logger: StructuredLogger instance
        event: Lambda event
        context: Lambda context
    """
    logger.info(
        "Lambda invocation started",
        request_id=context.request_id,
        function_name=context.function_name,
        function_version=context.function_version,
        memory_limit_mb=context.memory_limit_in_mb,
        remaining_time_ms=context.get_remaining_time_in_millis()
    )


def log_lambda_response(
    logger: StructuredLogger,
    response: Dict[str, Any],
    duration_ms: float
):
    """
    Log Lambda response details.
    
    Args:
        logger: StructuredLogger instance
        response: Lambda response
        duration_ms: Execution duration in milliseconds
    """
    logger.info(
        "Lambda invocation completed",
        duration_ms=duration_ms,
        status_code=response.get('response', {}).get('httpStatusCode', 'unknown')
    )


def log_error(
    logger: StructuredLogger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
):
    """
    Log error with context.
    
    Args:
        logger: StructuredLogger instance
        error: Exception object
        context: Optional additional context
    """
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error)
    }
    
    if context:
        error_data.update(context)
    
    logger.error(
        f"Error occurred: {str(error)}",
        **error_data
    )
