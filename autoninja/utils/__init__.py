"""
AutoNinja Utilities Package

This package contains utility functions and helpers for retry logic,
serialization, and other common operations.
"""

from .retry import exponential_backoff_retry, CircuitBreaker, with_timeout
from .serialization import (
    serialize_for_dynamodb,
    deserialize_from_dynamodb,
    serialize_for_json,
    safe_json_dumps,
    safe_json_loads,
    DynamoDBEncoder,
    compress_large_attributes,
    decompress_attributes,
)

__all__ = [
    # Retry utilities
    "exponential_backoff_retry",
    "CircuitBreaker", 
    "with_timeout",
    
    # Serialization utilities
    "serialize_for_dynamodb",
    "deserialize_from_dynamodb",
    "serialize_for_json",
    "safe_json_dumps",
    "safe_json_loads",
    "DynamoDBEncoder",
    "compress_large_attributes",
    "decompress_attributes",
]