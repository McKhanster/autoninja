"""
DynamoDB State Persistence Layer

This module provides DynamoDB-based persistence for AutoNinja session state,
including table schemas, CRUD operations, error handling, and retry logic.
"""

import json
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from boto3.dynamodb.conditions import Key, Attr

from autoninja.models.state import SessionState, GenerationStage, SessionStatus
from autoninja.utils.retry import exponential_backoff_retry
from autoninja.utils.serialization import serialize_for_dynamodb, deserialize_from_dynamodb


logger = logging.getLogger(__name__)


class DynamoDBStateStore:
    """
    DynamoDB-based state persistence for AutoNinja sessions.
    
    Provides CRUD operations for session state with error handling,
    retry logic, and optimistic locking for concurrent access.
    """
    
    def __init__(
        self,
        table_name: str = "autoninja-sessions",
        region_name: str = "us-east-2",
        endpoint_url: Optional[str] = None
    ):
        """
        Initialize DynamoDB state store.
        
        Args:
            table_name: Name of the DynamoDB table
            region_name: AWS region for DynamoDB
            endpoint_url: Optional endpoint URL for local testing
        """
        self.table_name = table_name
        self.region_name = region_name
        
        # Initialize DynamoDB client and resource
        session = boto3.Session()
        self.dynamodb = session.resource(
            'dynamodb',
            region_name=region_name,
            endpoint_url=endpoint_url
        )
        self.client = session.client(
            'dynamodb',
            region_name=region_name,
            endpoint_url=endpoint_url
        )
        
        self.table = self.dynamodb.Table(table_name)
        
        # Ensure table exists
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Ensure the DynamoDB table exists, create if not"""
        try:
            self.table.load()
            logger.info(f"DynamoDB table {self.table_name} exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Creating DynamoDB table {self.table_name}")
                self._create_table()
            else:
                raise
    
    def _create_table(self):
        """Create the DynamoDB table with proper schema"""
        try:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'session_id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'session_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'status',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'created_at',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'status-created-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'status',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'created_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                BillingMode='PAY_PER_REQUEST',
                Tags=[
                    {
                        'Key': 'Application',
                        'Value': 'AutoNinja'
                    },
                    {
                        'Key': 'Component',
                        'Value': 'StateStore'
                    }
                ]
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            logger.info(f"Successfully created DynamoDB table {self.table_name}")
            
        except ClientError as e:
            logger.error(f"Failed to create DynamoDB table: {e}")
            raise
    
    @exponential_backoff_retry(max_retries=3)
    async def create_session(self, session_state: SessionState) -> bool:
        """
        Create a new session in DynamoDB.
        
        Args:
            session_state: SessionState object to persist
            
        Returns:
            bool: True if successful
            
        Raises:
            ValueError: If session already exists
            ClientError: If DynamoDB operation fails
        """
        try:
            # Serialize the session state for DynamoDB
            item = serialize_for_dynamodb(session_state.dict())
            
            # Add DynamoDB-specific fields
            item['ttl'] = int((datetime.utcnow().timestamp() + 86400 * 30))  # 30 days TTL
            item['version'] = 1
            
            # Use condition expression to prevent overwriting existing sessions
            response = self.table.put_item(
                Item=item,
                ConditionExpression=Attr('session_id').not_exists()
            )
            
            logger.info(f"Created session {session_state.session_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise ValueError(f"Session {session_state.session_id} already exists")
            else:
                logger.error(f"Failed to create session {session_state.session_id}: {e}")
                raise
    
    @exponential_backoff_retry(max_retries=3)
    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieve a session from DynamoDB.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            SessionState object if found, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={'session_id': session_id}
            )
            
            if 'Item' not in response:
                logger.warning(f"Session {session_id} not found")
                return None
            
            # Deserialize from DynamoDB format
            item_data = deserialize_from_dynamodb(response['Item'])
            
            # Remove DynamoDB-specific fields
            item_data.pop('ttl', None)
            item_data.pop('version', None)
            
            session_state = SessionState(**item_data)
            logger.debug(f"Retrieved session {session_id}")
            return session_state
            
        except ClientError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise
    
    @exponential_backoff_retry(max_retries=3)
    async def update_session(
        self,
        session_state: SessionState,
        expected_version: Optional[int] = None
    ) -> bool:
        """
        Update an existing session with optimistic locking.
        
        Args:
            session_state: Updated SessionState object
            expected_version: Expected version for optimistic locking
            
        Returns:
            bool: True if successful
            
        Raises:
            ValueError: If version mismatch (concurrent modification)
            ClientError: If DynamoDB operation fails
        """
        try:
            # Update timestamp
            session_state.update_timestamp()
            
            # Serialize for DynamoDB
            item = serialize_for_dynamodb(session_state.dict())
            
            # Increment version for optimistic locking
            new_version = (expected_version or 1) + 1
            item['version'] = new_version
            item['ttl'] = int((datetime.utcnow().timestamp() + 86400 * 30))  # Refresh TTL
            
            # Build condition expression for optimistic locking
            condition_expression = Attr('session_id').exists()
            if expected_version is not None:
                condition_expression = condition_expression & Attr('version').eq(expected_version)
            
            response = self.table.put_item(
                Item=item,
                ConditionExpression=condition_expression
            )
            
            logger.info(f"Updated session {session_state.session_id} to version {new_version}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise ValueError(f"Version mismatch for session {session_state.session_id}")
            else:
                logger.error(f"Failed to update session {session_state.session_id}: {e}")
                raise
    
    @exponential_backoff_retry(max_retries=3)
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from DynamoDB.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bool: True if successful
        """
        try:
            response = self.table.delete_item(
                Key={'session_id': session_id},
                ConditionExpression=Attr('session_id').exists()
            )
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Session {session_id} not found for deletion")
                return False
            else:
                logger.error(f"Failed to delete session {session_id}: {e}")
                raise
    
    @exponential_backoff_retry(max_retries=3)
    async def list_sessions_by_status(
        self,
        status: SessionStatus,
        limit: int = 50,
        last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        List sessions by status using GSI.
        
        Args:
            status: Session status to filter by
            limit: Maximum number of sessions to return
            last_evaluated_key: Pagination token
            
        Returns:
            Dict containing sessions and pagination info
        """
        try:
            query_params = {
                'IndexName': 'status-created-index',
                'KeyConditionExpression': Key('status').eq(status.value),
                'Limit': limit,
                'ScanIndexForward': False  # Most recent first
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = self.table.query(**query_params)
            
            # Deserialize sessions
            sessions = []
            for item in response.get('Items', []):
                item_data = deserialize_from_dynamodb(item)
                item_data.pop('ttl', None)
                item_data.pop('version', None)
                sessions.append(SessionState(**item_data))
            
            result = {
                'sessions': sessions,
                'count': len(sessions),
                'last_evaluated_key': response.get('LastEvaluatedKey')
            }
            
            logger.debug(f"Listed {len(sessions)} sessions with status {status.value}")
            return result
            
        except ClientError as e:
            logger.error(f"Failed to list sessions by status {status.value}: {e}")
            raise
    
    @exponential_backoff_retry(max_retries=3)
    async def get_session_count_by_status(self, status: SessionStatus) -> int:
        """
        Get count of sessions by status.
        
        Args:
            status: Session status to count
            
        Returns:
            int: Number of sessions with the given status
        """
        try:
            response = self.table.query(
                IndexName='status-created-index',
                KeyConditionExpression=Key('status').eq(status.value),
                Select='COUNT'
            )
            
            count = response.get('Count', 0)
            logger.debug(f"Found {count} sessions with status {status.value}")
            return count
            
        except ClientError as e:
            logger.error(f"Failed to count sessions by status {status.value}: {e}")
            raise
    
    async def cleanup_expired_sessions(self, days_old: int = 30) -> int:
        """
        Clean up sessions older than specified days.
        
        Args:
            days_old: Number of days after which sessions are considered expired
            
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_timestamp = cutoff_date.isoformat()
            
            # Scan for old sessions (this could be expensive for large tables)
            response = self.table.scan(
                FilterExpression=Attr('created_at').lt(cutoff_timestamp),
                ProjectionExpression='session_id'
            )
            
            deleted_count = 0
            for item in response.get('Items', []):
                try:
                    await self.delete_session(item['session_id'])
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete expired session {item['session_id']}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} expired sessions")
            return deleted_count
            
        except ClientError as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on DynamoDB connection.
        
        Returns:
            Dict with health status information
        """
        try:
            # Simple table description to test connectivity
            start_time = time.time()
            self.table.load()
            response_time = time.time() - start_time
            
            # Get table status
            table_status = self.table.table_status
            
            return {
                'status': 'healthy',
                'table_name': self.table_name,
                'table_status': table_status,
                'response_time_ms': round(response_time * 1000, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Factory function for creating state store instances
def create_state_store(
    table_name: Optional[str] = None,
    region_name: Optional[str] = None,
    endpoint_url: Optional[str] = None
) -> DynamoDBStateStore:
    """
    Factory function to create DynamoDB state store instance.
    
    Args:
        table_name: DynamoDB table name (defaults to autoninja-sessions)
        region_name: AWS region (defaults to us-east-2)
        endpoint_url: Optional endpoint URL for local testing
        
    Returns:
        DynamoDBStateStore instance
    """
    return DynamoDBStateStore(
        table_name=table_name or "autoninja-sessions",
        region_name=region_name or "us-east-2",
        endpoint_url=endpoint_url
    )