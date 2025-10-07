"""
Logging Configuration for AutoNinja

Centralized logging configuration with file rotation, structured logging,
and separate log files for different components.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class AutoNinjaFormatter(logging.Formatter):
    """Custom formatter for AutoNinja logs with structured output."""
    
    def format(self, record):
        # Add execution context if available
        if hasattr(record, 'session_id'):
            record.session_info = f"[{record.session_id}]"
        else:
            record.session_info = ""
        
        if hasattr(record, 'execution_id'):
            record.exec_info = f"[{record.execution_id}]"
        else:
            record.exec_info = ""
        
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup comprehensive logging configuration for AutoNinja.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (defaults to ./logs)
        enable_file_logging: Whether to enable file logging
        enable_console_logging: Whether to enable console logging
        max_file_size: Maximum size per log file before rotation
        backup_count: Number of backup files to keep
    """
    
    # Create logs directory
    if log_dir is None:
        log_dir = Path.cwd() / "logs"
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(exist_ok=True)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Create formatters
    detailed_formatter = AutoNinjaFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(session_info)s%(exec_info)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
    
    if enable_file_logging:
        # Main application log
        main_log_file = log_dir / "autoninja.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        main_handler.setLevel(numeric_level)
        main_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(main_handler)
        
        # Requirements Analyst specific log
        requirements_log_file = log_dir / "requirements_analyst.log"
        requirements_handler = logging.handlers.RotatingFileHandler(
            requirements_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        requirements_handler.setLevel(numeric_level)
        requirements_handler.setFormatter(detailed_formatter)
        
        # Add filter for requirements analyst logs
        requirements_handler.addFilter(
            lambda record: 'requirements_analyst' in record.name
        )
        root_logger.addHandler(requirements_handler)
        
        # Solution Architect specific log
        solution_architect_log_file = log_dir / "solution_architect.log"
        solution_architect_handler = logging.handlers.RotatingFileHandler(
            solution_architect_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        solution_architect_handler.setLevel(numeric_level)
        solution_architect_handler.setFormatter(detailed_formatter)
        
        # Add filter for solution architect logs
        solution_architect_handler.addFilter(
            lambda record: 'solution_architect' in record.name
        )
        root_logger.addHandler(solution_architect_handler)
        
        # Bedrock inference log (for raw requests/responses)
        bedrock_log_file = log_dir / "bedrock_inference.log"
        bedrock_handler = logging.handlers.RotatingFileHandler(
            bedrock_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        bedrock_handler.setLevel(logging.DEBUG)  # Capture all Bedrock logs
        bedrock_handler.setFormatter(detailed_formatter)
        
        # Add filter for Bedrock logs
        bedrock_handler.addFilter(
            lambda record: any(keyword in record.name for keyword in 
                             ['bedrock', 'langchain_aws']) or 
                             'Raw Bedrock' in record.getMessage()
        )
        root_logger.addHandler(bedrock_handler)
        
        # Error log (errors only)
        error_log_file = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File logging: {enable_file_logging}")
    if enable_file_logging:
        logger.info(f"Log files location: {log_dir.absolute()}")


def get_session_logger(session_id: str, execution_id: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with session context for structured logging.
    
    Args:
        session_id: Session identifier
        execution_id: Optional execution identifier
        
    Returns:
        Logger with session context
    """
    logger = logging.getLogger("autoninja.session")
    
    # Create a custom adapter to add session context
    class SessionLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return f"[{self.extra['session_id']}] {msg}", kwargs
    
    extra = {"session_id": session_id}
    if execution_id:
        extra["execution_id"] = execution_id
    
    return SessionLoggerAdapter(logger, extra)


def log_bedrock_request(execution_id: str, request_data: dict) -> None:
    """Log Bedrock request with structured format."""
    logger = logging.getLogger("autoninja.bedrock.request")
    logger.info(f"BEDROCK_REQUEST [{execution_id}]: {request_data}")


def log_bedrock_response(execution_id: str, response_data: dict) -> None:
    """Log Bedrock response with structured format."""
    logger = logging.getLogger("autoninja.bedrock.response")
    logger.info(f"BEDROCK_RESPONSE [{execution_id}]: {response_data}")


# Default configuration
def configure_default_logging():
    """Configure default logging for AutoNinja."""
    setup_logging(
        log_level="INFO",
        enable_file_logging=True,
        enable_console_logging=True
    )


# Auto-configure when imported
if not logging.getLogger().handlers:
    configure_default_logging()