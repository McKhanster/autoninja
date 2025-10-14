"""
Utility modules for AutoNinja.

This module provides job name generation and structured logging utilities.
"""

from .job_generator import (
    generate_job_name,
    extract_keyword,
    normalize_keyword,
    parse_job_name,
    is_valid_job_name
)
from .logger import (
    StructuredLogger,
    JSONFormatter,
    get_logger,
    log_lambda_event,
    log_lambda_response,
    log_error
)

__all__ = [
    'generate_job_name',
    'extract_keyword',
    'normalize_keyword',
    'parse_job_name',
    'is_valid_job_name',
    'StructuredLogger',
    'JSONFormatter',
    'get_logger',
    'log_lambda_event',
    'log_lambda_response',
    'log_error'
]
