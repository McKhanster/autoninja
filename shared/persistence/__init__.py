"""
Persistence layer for AutoNinja.

This module provides client wrappers for DynamoDB and S3 operations.
"""

from .dynamodb_client import DynamoDBClient
from .s3_client import S3Client

__all__ = ['DynamoDBClient', 'S3Client']
