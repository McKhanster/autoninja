"""
S3 Artifact Storage System

This module provides S3-based storage for AutoNinja generated artifacts,
including code files, documentation, infrastructure templates, and deployment
packages with versioning and metadata management.
"""

import asyncio
import hashlib
import json
import logging
import mimetypes
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, BinaryIO, TextIO
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError, BotoCoreError
import aiofiles

from autoninja.utils.retry import exponential_backoff_retry
from autoninja.utils.serialization import safe_json_dumps, safe_json_loads


logger = logging.getLogger(__name__)


class ArtifactMetadata:
    """Metadata for stored artifacts"""
    
    def __init__(
        self,
        artifact_type: str,
        session_id: str,
        agent_name: str,
        file_name: str,
        content_type: str = None,
        size_bytes: int = None,
        checksum: str = None,
        version: int = 1,
        tags: Dict[str, str] = None,
        custom_metadata: Dict[str, Any] = None
    ):
        self.artifact_type = artifact_type
        self.session_id = session_id
        self.agent_name = agent_name
        self.file_name = file_name
        self.content_type = content_type or self._guess_content_type(file_name)
        self.size_bytes = size_bytes
        self.checksum = checksum
        self.version = version
        self.tags = tags or {}
        self.custom_metadata = custom_metadata or {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def _guess_content_type(self, file_name: str) -> str:
        """Guess content type from file extension"""
        content_type, _ = mimetypes.guess_type(file_name)
        return content_type or 'application/octet-stream'
    
    def to_s3_metadata(self) -> Dict[str, str]:
        """Convert to S3 metadata format (string values only)"""
        metadata = {
            'artifact-type': self.artifact_type,
            'session-id': self.session_id,
            'agent-name': self.agent_name,
            'file-name': self.file_name,
            'version': str(self.version),
            'created-at': self.created_at.isoformat(),
            'updated-at': self.updated_at.isoformat()
        }
        
        if self.size_bytes is not None:
            metadata['size-bytes'] = str(self.size_bytes)
        
        if self.checksum:
            metadata['checksum'] = self.checksum
        
        # Add custom metadata with prefix
        for key, value in self.custom_metadata.items():
            metadata[f'custom-{key}'] = str(value)
        
        return metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'artifact_type': self.artifact_type,
            'session_id': self.session_id,
            'agent_name': self.agent_name,
            'file_name': self.file_name,
            'content_type': self.content_type,
            'size_bytes': self.size_bytes,
            'checksum': self.checksum,
            'version': self.version,
            'tags': self.tags,
            'custom_metadata': self.custom_metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_s3_metadata(cls, s3_metadata: Dict[str, str], s3_tags: Dict[str, str] = None):
        """Create from S3 metadata"""
        custom_metadata = {}
        for key, value in s3_metadata.items():
            if key.startswith('custom-'):
                custom_key = key[7:]  # Remove 'custom-' prefix
                custom_metadata[custom_key] = value
        
        metadata = cls(
            artifact_type=s3_metadata.get('artifact-type', 'unknown'),
            session_id=s3_metadata.get('session-id', ''),
            agent_name=s3_metadata.get('agent-name', ''),
            file_name=s3_metadata.get('file-name', ''),
            version=int(s3_metadata.get('version', '1')),
            tags=s3_tags or {},
            custom_metadata=custom_metadata
        )
        
        # Parse timestamps
        if 'created-at' in s3_metadata:
            metadata.created_at = datetime.fromisoformat(s3_metadata['created-at'])
        if 'updated-at' in s3_metadata:
            metadata.updated_at = datetime.fromisoformat(s3_metadata['updated-at'])
        
        # Parse optional fields
        if 'size-bytes' in s3_metadata:
            metadata.size_bytes = int(s3_metadata['size-bytes'])
        if 'checksum' in s3_metadata:
            metadata.checksum = s3_metadata['checksum']
        
        return metadata


class S3ArtifactStore:
    """
    S3-based artifact storage for AutoNinja generated content.
    
    Provides versioned storage of code files, documentation, infrastructure
    templates, and deployment packages with comprehensive metadata management.
    """
    
    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-2",
        endpoint_url: Optional[str] = None,
        prefix: str = "autoninja-artifacts"
    ):
        """
        Initialize S3 artifact store.
        
        Args:
            bucket_name: S3 bucket name for artifact storage
            region_name: AWS region for S3 bucket
            endpoint_url: Optional endpoint URL for local testing
            prefix: Key prefix for all artifacts
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.prefix = prefix.rstrip('/')
        
        # Initialize S3 client
        session = boto3.Session()
        self.s3_client = session.client(
            's3',
            region_name=region_name,
            endpoint_url=endpoint_url
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if not"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.info(f"Creating S3 bucket {self.bucket_name}")
                self._create_bucket()
            else:
                logger.error(f"Error checking bucket {self.bucket_name}: {e}")
                raise
    
    def _create_bucket(self):
        """Create the S3 bucket with proper configuration"""
        try:
            create_params = {'Bucket': self.bucket_name}
            
            # Add location constraint for regions other than us-east-2
            if self.region_name != 'us-east-2':
                create_params['CreateBucketConfiguration'] = {
                    'LocationConstraint': self.region_name
                }
            
            self.s3_client.create_bucket(**create_params)
            
            # Enable versioning
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Set up lifecycle policy for old versions
            lifecycle_policy = {
                'Rules': [
                    {
                        'ID': 'AutoNinjaArtifactLifecycle',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': f'{self.prefix}/'},
                        'NoncurrentVersionExpiration': {'NoncurrentDays': 90},
                        'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 7}
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_policy
            )
            
            # Add bucket tags
            self.s3_client.put_bucket_tagging(
                Bucket=self.bucket_name,
                Tagging={
                    'TagSet': [
                        {'Key': 'Application', 'Value': 'AutoNinja'},
                        {'Key': 'Component', 'Value': 'ArtifactStore'},
                        {'Key': 'Environment', 'Value': 'production'}
                    ]
                }
            )
            
            logger.info(f"Successfully created S3 bucket {self.bucket_name}")
            
        except ClientError as e:
            logger.error(f"Failed to create S3 bucket {self.bucket_name}: {e}")
            raise
    
    def _generate_key(
        self,
        session_id: str,
        artifact_type: str,
        file_name: str,
        agent_name: Optional[str] = None
    ) -> str:
        """Generate S3 key for artifact"""
        key_parts = [self.prefix, session_id, artifact_type]
        
        if agent_name:
            key_parts.append(agent_name)
        
        key_parts.append(file_name)
        
        return '/'.join(key_parts)
    
    def _calculate_checksum(self, content: Union[str, bytes]) -> str:
        """Calculate MD5 checksum for content"""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        return hashlib.md5(content).hexdigest()
    
    @exponential_backoff_retry(max_retries=3)
    async def upload_artifact(
        self,
        session_id: str,
        artifact_type: str,
        file_name: str,
        content: Union[str, bytes, BinaryIO, TextIO],
        agent_name: Optional[str] = None,
        metadata: Optional[ArtifactMetadata] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload an artifact to S3.
        
        Args:
            session_id: Unique session identifier
            artifact_type: Type of artifact (source_code, infrastructure, documentation, etc.)
            file_name: Name of the file
            content: File content (string, bytes, or file-like object)
            agent_name: Name of the agent that generated this artifact
            metadata: Optional artifact metadata
            tags: Optional S3 tags
            
        Returns:
            str: S3 URI of the uploaded artifact
        """
        try:
            # Generate S3 key
            s3_key = self._generate_key(session_id, artifact_type, file_name, agent_name)
            
            # Prepare content
            if hasattr(content, 'read'):
                # File-like object
                content_bytes = content.read()
                if isinstance(content_bytes, str):
                    content_bytes = content_bytes.encode('utf-8')
            elif isinstance(content, str):
                content_bytes = content.encode('utf-8')
            else:
                content_bytes = content
            
            # Create metadata if not provided
            if metadata is None:
                metadata = ArtifactMetadata(
                    artifact_type=artifact_type,
                    session_id=session_id,
                    agent_name=agent_name or 'unknown',
                    file_name=file_name,
                    size_bytes=len(content_bytes),
                    checksum=self._calculate_checksum(content_bytes)
                )
            
            # Prepare S3 upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'Body': content_bytes,
                'ContentType': metadata.content_type,
                'Metadata': metadata.to_s3_metadata()
            }
            
            # Add tags if provided
            if tags or metadata.tags:
                all_tags = {**(tags or {}), **metadata.tags}
                tag_set = [{'Key': k, 'Value': v} for k, v in all_tags.items()]
                upload_params['Tagging'] = '&'.join([f"{tag['Key']}={tag['Value']}" for tag in tag_set])
            
            # Upload to S3
            response = self.s3_client.put_object(**upload_params)
            
            # Generate S3 URI
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            
            logger.info(
                f"Uploaded artifact {file_name} for session {session_id} "
                f"({len(content_bytes)} bytes) to {s3_uri}"
            )
            
            return s3_uri
            
        except ClientError as e:
            logger.error(f"Failed to upload artifact {file_name}: {e}")
            raise
    
    @exponential_backoff_retry(max_retries=3)
    async def download_artifact(
        self,
        s3_uri: str,
        local_path: Optional[str] = None
    ) -> Union[bytes, str]:
        """
        Download an artifact from S3.
        
        Args:
            s3_uri: S3 URI of the artifact
            local_path: Optional local file path to save the artifact
            
        Returns:
            Artifact content as bytes, or local file path if saved locally
        """
        try:
            # Parse S3 URI
            parsed = urlparse(s3_uri)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            # Download from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            if local_path:
                # Save to local file
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                async with aiofiles.open(local_path, 'wb') as f:
                    await f.write(content)
                
                logger.info(f"Downloaded artifact from {s3_uri} to {local_path}")
                return local_path
            else:
                logger.info(f"Downloaded artifact from {s3_uri} ({len(content)} bytes)")
                return content
                
        except ClientError as e:
            logger.error(f"Failed to download artifact from {s3_uri}: {e}")
            raise
    
    @exponential_backoff_retry(max_retries=3)
    async def get_artifact_metadata(self, s3_uri: str) -> Optional[ArtifactMetadata]:
        """
        Get metadata for an artifact.
        
        Args:
            s3_uri: S3 URI of the artifact
            
        Returns:
            ArtifactMetadata object if found, None otherwise
        """
        try:
            # Parse S3 URI
            parsed = urlparse(s3_uri)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            # Get object metadata
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            
            # Get object tags
            try:
                tags_response = self.s3_client.get_object_tagging(Bucket=bucket, Key=key)
                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
            except ClientError:
                tags = {}
            
            # Create metadata object
            metadata = ArtifactMetadata.from_s3_metadata(
                response.get('Metadata', {}),
                tags
            )
            
            # Set additional fields from S3 response
            metadata.size_bytes = response.get('ContentLength')
            metadata.content_type = response.get('ContentType')
            
            return metadata
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Artifact not found: {s3_uri}")
                return None
            else:
                logger.error(f"Failed to get metadata for {s3_uri}: {e}")
                raise
    
    @exponential_backoff_retry(max_retries=3)
    async def list_session_artifacts(
        self,
        session_id: str,
        artifact_type: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all artifacts for a session.
        
        Args:
            session_id: Session identifier
            artifact_type: Optional filter by artifact type
            agent_name: Optional filter by agent name
            
        Returns:
            List of artifact information dictionaries
        """
        try:
            # Build prefix for listing
            prefix_parts = [self.prefix, session_id]
            if artifact_type:
                prefix_parts.append(artifact_type)
                if agent_name:
                    prefix_parts.append(agent_name)
            
            list_prefix = '/'.join(prefix_parts) + '/'
            
            # List objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            artifacts = []
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=list_prefix):
                for obj in page.get('Contents', []):
                    # Get metadata for each object
                    s3_uri = f"s3://{self.bucket_name}/{obj['Key']}"
                    metadata = await self.get_artifact_metadata(s3_uri)
                    
                    artifact_info = {
                        's3_uri': s3_uri,
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"'),
                        'metadata': metadata.to_dict() if metadata else None
                    }
                    
                    artifacts.append(artifact_info)
            
            logger.info(f"Found {len(artifacts)} artifacts for session {session_id}")
            return artifacts
            
        except ClientError as e:
            logger.error(f"Failed to list artifacts for session {session_id}: {e}")
            raise
    
    @exponential_backoff_retry(max_retries=3)
    async def delete_artifact(self, s3_uri: str) -> bool:
        """
        Delete an artifact from S3.
        
        Args:
            s3_uri: S3 URI of the artifact to delete
            
        Returns:
            bool: True if successful
        """
        try:
            # Parse S3 URI
            parsed = urlparse(s3_uri)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            # Delete object
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            
            logger.info(f"Deleted artifact {s3_uri}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete artifact {s3_uri}: {e}")
            raise
    
    @exponential_backoff_retry(max_retries=3)
    async def create_deployment_package(
        self,
        session_id: str,
        package_name: str,
        artifacts: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a deployment package containing multiple artifacts.
        
        Args:
            session_id: Session identifier
            package_name: Name of the deployment package
            artifacts: List of S3 URIs to include in the package
            metadata: Optional package metadata
            
        Returns:
            str: S3 URI of the deployment package
        """
        import zipfile
        import tempfile
        
        try:
            # Create temporary zip file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Create zip package
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for artifact_uri in artifacts:
                    # Download artifact
                    content = await self.download_artifact(artifact_uri)
                    
                    # Extract file name from URI
                    parsed = urlparse(artifact_uri)
                    file_name = os.path.basename(parsed.path)
                    
                    # Add to zip
                    zip_file.writestr(file_name, content)
                
                # Add metadata file if provided
                if metadata:
                    metadata_json = safe_json_dumps(metadata, indent=2)
                    zip_file.writestr('package_metadata.json', metadata_json)
            
            # Upload package to S3
            with open(temp_path, 'rb') as package_file:
                package_uri = await self.upload_artifact(
                    session_id=session_id,
                    artifact_type='deployment_package',
                    file_name=package_name,
                    content=package_file,
                    metadata=ArtifactMetadata(
                        artifact_type='deployment_package',
                        session_id=session_id,
                        agent_name='deployment_manager',
                        file_name=package_name,
                        custom_metadata=metadata or {}
                    )
                )
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            logger.info(f"Created deployment package {package_name} with {len(artifacts)} artifacts")
            return package_uri
            
        except Exception as e:
            logger.error(f"Failed to create deployment package {package_name}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on S3 connection.
        
        Returns:
            Dict with health status information
        """
        try:
            # Test bucket access
            start_time = datetime.utcnow()
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'bucket_name': self.bucket_name,
                'region': self.region_name,
                'response_time_ms': round(response_time * 1000, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Factory function for creating artifact store instances
def create_artifact_store(
    bucket_name: Optional[str] = None,
    region_name: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    prefix: Optional[str] = None
) -> S3ArtifactStore:
    """
    Factory function to create S3 artifact store instance.
    
    Args:
        bucket_name: S3 bucket name (defaults to autoninja-artifacts)
        region_name: AWS region (defaults to us-east-2)
        endpoint_url: Optional endpoint URL for local testing
        prefix: Key prefix for artifacts (defaults to autoninja-artifacts)
        
    Returns:
        S3ArtifactStore instance
    """
    return S3ArtifactStore(
        bucket_name=bucket_name or "autoninja-artifacts",
        region_name=region_name or "us-east-2",
        endpoint_url=endpoint_url,
        prefix=prefix or "autoninja-artifacts"
    )