"""
DynamoDB client wrapper for AutoNinja inference record persistence.

This module provides functions to log inference inputs, outputs, and errors
to DynamoDB with complete audit trails. All operations are real (no mocking)
and persist data immediately.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


class DynamoDBClient:
    """Client for persisting inference records to DynamoDB."""
    
    def __init__(self, table_name: Optional[str] = None):
        """
        Initialize DynamoDB client.
        
        Args:
            table_name: DynamoDB table name. If not provided, reads from
                       DYNAMODB_TABLE_NAME environment variable.
        """
        self.table_name = table_name or os.environ.get('DYNAMODB_TABLE_NAME')
        if not self.table_name:
            raise ValueError("DynamoDB table name must be provided or set in DYNAMODB_TABLE_NAME env var")
        
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(self.table_name)
    
    def log_inference_input(
        self,
        job_name: str,
        session_id: str,
        agent_name: str,
        action_name: str,
        prompt: str,
        inference_id: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log raw inference input (prompt) to DynamoDB immediately.
        
        This function saves the complete raw prompt before any processing occurs
        to ensure no data loss.
        
        Args:
            job_name: Unique job identifier (partition key)
            session_id: Bedrock session ID
            agent_name: Name of the agent making the inference
            action_name: Name of the action being executed
            prompt: Complete raw prompt sent to the model
            inference_id: Optional unique inference ID
            model_id: Optional model identifier
            
        Returns:
            Dict containing the saved record
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        inference_id = inference_id or f"{agent_name}-{action_name}-{int(time.time() * 1000)}"
        
        record = {
            'job_name': job_name,
            'timestamp': timestamp,
            'session_id': session_id,
            'agent_name': agent_name,
            'action_name': action_name,
            'inference_id': inference_id,
            'prompt': prompt,
            'response': '',  # Will be updated when output is logged
            'model_id': model_id or 'unknown',
            'tokens_used': 0,
            'cost_estimate': Decimal('0.0'),
            'duration_seconds': Decimal('0.0'),
            'artifacts_s3_uri': '',
            'status': 'in_progress',
            'error_message': None
        }
        
        try:
            self.table.put_item(Item=record)
            return record
        except ClientError as e:
            raise Exception(f"Failed to log inference input to DynamoDB: {e}")
    
    def log_inference_output(
        self,
        job_name: str,
        timestamp: str,
        response: str,
        tokens_used: int = 0,
        cost_estimate: float = 0.0,
        duration_seconds: float = 0.0,
        artifacts_s3_uri: str = '',
        status: str = 'success'
    ) -> Dict[str, Any]:
        """
        Log raw inference output (response) to DynamoDB immediately.
        
        This function updates the existing record with the complete raw response
        and metadata after processing completes.
        
        Args:
            job_name: Unique job identifier (partition key)
            timestamp: Timestamp from the input record (sort key)
            response: Complete raw response from the model
            tokens_used: Number of tokens consumed
            cost_estimate: Estimated cost in USD
            duration_seconds: Execution duration in seconds
            artifacts_s3_uri: S3 URI where artifacts are stored
            status: Status of the inference (success/error)
            
        Returns:
            Dict containing the updated record
        """
        try:
            response_data = self.table.update_item(
                Key={
                    'job_name': job_name,
                    'timestamp': timestamp
                },
                UpdateExpression="""
                    SET #response = :response,
                        tokens_used = :tokens,
                        cost_estimate = :cost,
                        duration_seconds = :duration,
                        artifacts_s3_uri = :s3_uri,
                        #status = :status
                """,
                ExpressionAttributeNames={
                    '#response': 'response',
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':response': response,
                    ':tokens': tokens_used,
                    ':cost': Decimal(str(cost_estimate)),
                    ':duration': Decimal(str(duration_seconds)),
                    ':s3_uri': artifacts_s3_uri,
                    ':status': status
                },
                ReturnValues='ALL_NEW'
            )
            return response_data.get('Attributes', {})
        except ClientError as e:
            raise Exception(f"Failed to log inference output to DynamoDB: {e}")
    
    def log_error_to_dynamodb(
        self,
        job_name: str,
        timestamp: str,
        error_message: str,
        duration_seconds: float = 0.0
    ) -> Dict[str, Any]:
        """
        Log error information to DynamoDB for tracking failures.
        
        Args:
            job_name: Unique job identifier (partition key)
            timestamp: Timestamp from the input record (sort key)
            error_message: Error message or stack trace
            duration_seconds: Execution duration before error
            
        Returns:
            Dict containing the updated record
        """
        try:
            response_data = self.table.update_item(
                Key={
                    'job_name': job_name,
                    'timestamp': timestamp
                },
                UpdateExpression="""
                    SET error_message = :error,
                        #status = :status,
                        duration_seconds = :duration
                """,
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':error': error_message,
                    ':status': 'error',
                    ':duration': Decimal(str(duration_seconds))
                },
                ReturnValues='ALL_NEW'
            )
            return response_data.get('Attributes', {})
        except ClientError as e:
            raise Exception(f"Failed to log error to DynamoDB: {e}")
    
    def query_by_job_name(
        self,
        job_name: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query all inference records for a specific job.
        
        Args:
            job_name: Unique job identifier to query
            limit: Optional maximum number of records to return
            
        Returns:
            List of inference records sorted by timestamp
        """
        try:
            query_params = {
                'KeyConditionExpression': Key('job_name').eq(job_name),
                'ScanIndexForward': True  # Sort by timestamp ascending
            }
            
            if limit:
                query_params['Limit'] = limit
            
            response = self.table.query(**query_params)
            return response.get('Items', [])
        except ClientError as e:
            raise Exception(f"Failed to query DynamoDB by job_name: {e}")
    
    def query_by_session_id(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query all inference records for a specific session.
        
        Args:
            session_id: Session ID to query
            limit: Optional maximum number of records to return
            
        Returns:
            List of inference records sorted by timestamp
        """
        try:
            query_params = {
                'IndexName': 'SessionIdIndex',
                'KeyConditionExpression': Key('session_id').eq(session_id),
                'ScanIndexForward': True
            }
            
            if limit:
                query_params['Limit'] = limit
            
            response = self.table.query(**query_params)
            return response.get('Items', [])
        except ClientError as e:
            raise Exception(f"Failed to query DynamoDB by session_id: {e}")
    
    def query_by_agent_name(
        self,
        agent_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query all inference records for a specific agent.
        
        Args:
            agent_name: Agent name to query
            start_time: Optional start timestamp (ISO 8601)
            end_time: Optional end timestamp (ISO 8601)
            limit: Optional maximum number of records to return
            
        Returns:
            List of inference records sorted by timestamp
        """
        try:
            key_condition = Key('agent_name').eq(agent_name)
            
            if start_time and end_time:
                key_condition = key_condition & Key('timestamp').between(start_time, end_time)
            elif start_time:
                key_condition = key_condition & Key('timestamp').gte(start_time)
            elif end_time:
                key_condition = key_condition & Key('timestamp').lte(end_time)
            
            query_params = {
                'IndexName': 'AgentNameTimestampIndex',
                'KeyConditionExpression': key_condition,
                'ScanIndexForward': True
            }
            
            if limit:
                query_params['Limit'] = limit
            
            response = self.table.query(**query_params)
            return response.get('Items', [])
        except ClientError as e:
            raise Exception(f"Failed to query DynamoDB by agent_name: {e}")
    
    def get_record(
        self,
        job_name: str,
        timestamp: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific inference record by job_name and timestamp.
        
        Args:
            job_name: Unique job identifier (partition key)
            timestamp: Timestamp (sort key)
            
        Returns:
            Inference record or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'job_name': job_name,
                    'timestamp': timestamp
                }
            )
            return response.get('Item')
        except ClientError as e:
            raise Exception(f"Failed to get record from DynamoDB: {e}")
