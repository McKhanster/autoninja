"""
Serialization Utilities

This module provides utilities for serializing and deserializing data
for storage in DynamoDB and other AWS services.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


def serialize_for_dynamodb(data: Any) -> Any:
    """
    Serialize Python objects for DynamoDB storage.
    
    DynamoDB has specific requirements for data types:
    - Numbers must be Decimal for precision
    - Sets must be converted to lists
    - datetime objects must be ISO strings
    - None values must be removed
    
    Args:
        data: Python object to serialize
        
    Returns:
        Serialized object suitable for DynamoDB
    """
    if data is None:
        return None
    elif isinstance(data, bool):
        return data
    elif isinstance(data, (int, float)):
        return Decimal(str(data))
    elif isinstance(data, str):
        return data
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return data
    elif isinstance(data, (list, tuple)):
        return [serialize_for_dynamodb(item) for item in data if item is not None]
    elif isinstance(data, set):
        return [serialize_for_dynamodb(item) for item in data if item is not None]
    elif isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if value is not None:  # DynamoDB doesn't support None values
                serialized_value = serialize_for_dynamodb(value)
                if serialized_value is not None:
                    result[key] = serialized_value
        return result
    else:
        # For other objects, try to convert to dict first
        try:
            if hasattr(data, 'dict'):
                # Pydantic models
                return serialize_for_dynamodb(data.dict())
            elif hasattr(data, '__dict__'):
                # Regular Python objects
                return serialize_for_dynamodb(data.__dict__)
            else:
                # Convert to string as fallback
                return str(data)
        except Exception as e:
            logger.warning(f"Failed to serialize object {type(data)}: {e}")
            return str(data)


def deserialize_from_dynamodb(data: Any) -> Any:
    """
    Deserialize data from DynamoDB format back to Python objects.
    
    Args:
        data: DynamoDB item data
        
    Returns:
        Deserialized Python object
    """
    if data is None:
        return None
    elif isinstance(data, bool):
        return data
    elif isinstance(data, Decimal):
        # Convert Decimal back to appropriate numeric type
        if data % 1 == 0:
            return int(data)
        else:
            return float(data)
    elif isinstance(data, str):
        # Try to parse as datetime if it looks like ISO format
        if _is_iso_datetime(data):
            try:
                return datetime.fromisoformat(data.replace('Z', '+00:00'))
            except ValueError:
                return data
        return data
    elif isinstance(data, list):
        return [deserialize_from_dynamodb(item) for item in data]
    elif isinstance(data, dict):
        result = {}
        for key, value in data.items():
            result[key] = deserialize_from_dynamodb(value)
        return result
    else:
        return data


def _is_iso_datetime(value: str) -> bool:
    """
    Check if a string looks like an ISO datetime format.
    
    Args:
        value: String to check
        
    Returns:
        bool: True if it looks like ISO datetime
    """
    if not isinstance(value, str) or len(value) < 19:
        return False
    
    # Basic check for ISO format patterns
    iso_patterns = [
        'T',  # ISO datetime separator
        '-',  # Date separators
        ':'   # Time separators
    ]
    
    return all(pattern in value for pattern in iso_patterns)


def serialize_for_json(data: Any) -> Any:
    """
    Serialize Python objects for JSON storage/transmission.
    
    Args:
        data: Python object to serialize
        
    Returns:
        JSON-serializable object
    """
    if data is None:
        return None
    elif isinstance(data, (bool, int, float, str)):
        return data
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, (list, tuple)):
        return [serialize_for_json(item) for item in data]
    elif isinstance(data, set):
        return [serialize_for_json(item) for item in data]
    elif isinstance(data, dict):
        return {key: serialize_for_json(value) for key, value in data.items()}
    else:
        # For other objects, try to convert to dict first
        try:
            if hasattr(data, 'dict'):
                # Pydantic models
                return serialize_for_json(data.dict())
            elif hasattr(data, '__dict__'):
                # Regular Python objects
                return serialize_for_json(data.__dict__)
            else:
                # Convert to string as fallback
                return str(data)
        except Exception as e:
            logger.warning(f"Failed to serialize object {type(data)} for JSON: {e}")
            return str(data)


def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Safely serialize data to JSON string with proper error handling.
    
    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string
    """
    try:
        serialized_data = serialize_for_json(data)
        return json.dumps(serialized_data, **kwargs)
    except Exception as e:
        logger.error(f"Failed to serialize data to JSON: {e}")
        # Return a safe fallback
        return json.dumps({"error": "serialization_failed", "type": str(type(data))})


def safe_json_loads(json_str: str) -> Any:
    """
    Safely deserialize JSON string with proper error handling.
    
    Args:
        json_str: JSON string to deserialize
        
    Returns:
        Deserialized Python object
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to deserialize JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error deserializing JSON: {e}")
        return None


class DynamoDBEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for DynamoDB-compatible serialization.
    """
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)


def compress_large_attributes(data: Dict[str, Any], max_size: int = 400000) -> Dict[str, Any]:
    """
    Compress large attributes that might exceed DynamoDB limits.
    
    DynamoDB has a 400KB limit per item. This function identifies large
    attributes and compresses them if needed.
    
    Args:
        data: Dictionary to check and compress
        max_size: Maximum size in bytes before compression
        
    Returns:
        Dictionary with compressed large attributes
    """
    import gzip
    import base64
    
    result = data.copy()
    
    for key, value in data.items():
        if isinstance(value, (str, dict, list)):
            # Estimate size
            serialized = safe_json_dumps(value)
            size_bytes = len(serialized.encode('utf-8'))
            
            if size_bytes > max_size:
                try:
                    # Compress the data
                    compressed = gzip.compress(serialized.encode('utf-8'))
                    encoded = base64.b64encode(compressed).decode('utf-8')
                    
                    # Store compressed data with metadata
                    result[key] = {
                        '_compressed': True,
                        '_original_size': size_bytes,
                        '_compressed_size': len(encoded),
                        'data': encoded
                    }
                    
                    logger.info(
                        f"Compressed attribute {key}: {size_bytes} -> {len(encoded)} bytes "
                        f"({(1 - len(encoded)/size_bytes)*100:.1f}% reduction)"
                    )
                    
                except Exception as e:
                    logger.warning(f"Failed to compress attribute {key}: {e}")
    
    return result


def decompress_attributes(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decompress attributes that were compressed by compress_large_attributes.
    
    Args:
        data: Dictionary potentially containing compressed attributes
        
    Returns:
        Dictionary with decompressed attributes
    """
    import gzip
    import base64
    
    result = data.copy()
    
    for key, value in data.items():
        if isinstance(value, dict) and value.get('_compressed'):
            try:
                # Decompress the data
                encoded_data = value['data']
                compressed = base64.b64decode(encoded_data.encode('utf-8'))
                decompressed = gzip.decompress(compressed).decode('utf-8')
                
                # Parse back to original format
                result[key] = safe_json_loads(decompressed)
                
                logger.debug(f"Decompressed attribute {key}")
                
            except Exception as e:
                logger.error(f"Failed to decompress attribute {key}: {e}")
                # Keep the compressed version if decompression fails
                result[key] = value
    
    return result