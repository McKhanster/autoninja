"""
S3 client wrapper for AutoNinja artifact storage.

This module provides functions to save and retrieve artifacts from S3,
including raw responses and converted/processed data. All operations are
real (no mocking) and persist data immediately.
"""

import os
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import boto3
from botocore.exceptions import ClientError


class S3Client:
    """Client for persisting artifacts to S3."""
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize S3 client.
        
        Args:
            bucket_name: S3 bucket name. If not provided, reads from
                        S3_BUCKET_NAME environment variable.
        """
        self.bucket_name = bucket_name or os.environ.get('S3_BUCKET_NAME')
        if not self.bucket_name:
            raise ValueError("S3 bucket name must be provided or set in S3_BUCKET_NAME env var")
        
        self.s3_client = boto3.client('s3')
    
    def _build_s3_key(
        self,
        job_name: str,
        phase: str,
        agent_name: str,
        filename: str
    ) -> str:
        """
        Build S3 key following the standard structure.
        
        Structure: {job_name}/{phase}/{agent_name}/{filename}
        Example: job-friend-20251013-143022/requirements/requirements-analyst/requirements.json
        
        Args:
            job_name: Unique job identifier
            phase: Phase name (requirements, code, architecture, validation, deployment)
            agent_name: Agent name
            filename: File name
            
        Returns:
            Complete S3 key
        """
        return f"{job_name}/{phase}/{agent_name}/{filename}"
    
    def save_raw_response(
        self,
        job_name: str,
        phase: str,
        agent_name: str,
        response: Union[str, Dict, List],
        filename: str = 'raw_response.json'
    ) -> str:
        """
        Save raw agent response to S3.
        
        This function saves the complete unprocessed response from an agent
        for audit and debugging purposes.
        
        Args:
            job_name: Unique job identifier
            phase: Phase name (requirements, code, architecture, validation, deployment)
            agent_name: Agent name
            response: Raw response (string or JSON-serializable object)
            filename: Optional custom filename (default: raw_response.json)
            
        Returns:
            S3 URI of the saved object
        """
        s3_key = self._build_s3_key(job_name, phase, agent_name, filename)
        
        # Convert response to string if it's not already
        if isinstance(response, (dict, list)):
            content = json.dumps(response, indent=2, default=str)
        else:
            content = str(response)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType='application/json'
            )
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            return s3_uri
        except ClientError as e:
            raise Exception(f"Failed to save raw response to S3: {e}")
    
    def save_converted_artifact(
        self,
        job_name: str,
        phase: str,
        agent_name: str,
        artifact: Union[str, Dict, List],
        filename: str,
        content_type: str = 'application/json'
    ) -> str:
        """
        Save converted/processed artifact to S3.
        
        This function saves processed data (requirements, code, architecture, etc.)
        that has been extracted and converted from raw responses.
        
        Args:
            job_name: Unique job identifier
            phase: Phase name (requirements, code, architecture, validation, deployment)
            agent_name: Agent name
            artifact: Processed artifact (can be string, dict, or list)
            filename: File name for the artifact
            content_type: MIME type (default: application/json)
            
        Returns:
            S3 URI of the saved object
        """
        s3_key = self._build_s3_key(job_name, phase, agent_name, filename)
        
        # Convert artifact to appropriate format
        if content_type == 'application/json' and isinstance(artifact, (dict, list)):
            content = json.dumps(artifact, indent=2, default=str)
        else:
            content = str(artifact)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType=content_type
            )
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            return s3_uri
        except ClientError as e:
            raise Exception(f"Failed to save converted artifact to S3: {e}")
    
    def get_artifact(
        self,
        job_name: str,
        phase: str,
        agent_name: str,
        filename: str,
        parse_json: bool = True
    ) -> Union[str, Dict, List]:
        """
        Retrieve an artifact from S3.
        
        Args:
            job_name: Unique job identifier
            phase: Phase name
            agent_name: Agent name
            filename: File name
            parse_json: If True, parse JSON content (default: True)
            
        Returns:
            Artifact content (parsed JSON or raw string)
        """
        s3_key = self._build_s3_key(job_name, phase, agent_name, filename)
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            content = response['Body'].read().decode('utf-8')
            
            if parse_json:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return content
            else:
                return content
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"Artifact not found: s3://{self.bucket_name}/{s3_key}")
            raise Exception(f"Failed to get artifact from S3: {e}")
    
    def list_artifacts(
        self,
        job_name: str,
        phase: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all artifacts for a job, optionally filtered by phase and agent.
        
        Args:
            job_name: Unique job identifier
            phase: Optional phase filter
            agent_name: Optional agent name filter
            
        Returns:
            List of artifact metadata (key, size, last_modified)
        """
        # Build prefix based on filters
        if agent_name and phase:
            prefix = f"{job_name}/{phase}/{agent_name}/"
        elif phase:
            prefix = f"{job_name}/{phase}/"
        else:
            prefix = f"{job_name}/"
        
        try:
            artifacts = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        artifacts.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            's3_uri': f"s3://{self.bucket_name}/{obj['Key']}"
                        })
            
            return artifacts
        except ClientError as e:
            raise Exception(f"Failed to list artifacts from S3: {e}")
    
    def get_artifact_by_uri(
        self,
        s3_uri: str,
        parse_json: bool = True
    ) -> Union[str, Dict, List]:
        """
        Retrieve an artifact using its full S3 URI.
        
        Args:
            s3_uri: Full S3 URI (e.g., s3://bucket/key)
            parse_json: If True, parse JSON content (default: True)
            
        Returns:
            Artifact content (parsed JSON or raw string)
        """
        # Parse S3 URI
        if not s3_uri.startswith('s3://'):
            raise ValueError(f"Invalid S3 URI: {s3_uri}")
        
        parts = s3_uri[5:].split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URI format: {s3_uri}")
        
        bucket, key = parts
        
        try:
            response = self.s3_client.get_object(
                Bucket=bucket,
                Key=key
            )
            
            content = response['Body'].read().decode('utf-8')
            
            if parse_json:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return content
            else:
                return content
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"Artifact not found: {s3_uri}")
            raise Exception(f"Failed to get artifact from S3: {e}")
    
    def delete_job_artifacts(
        self,
        job_name: str
    ) -> int:
        """
        Delete all artifacts for a specific job.
        
        Args:
            job_name: Unique job identifier
            
        Returns:
            Number of objects deleted
        """
        prefix = f"{job_name}/"
        
        try:
            # List all objects with the prefix
            objects_to_delete = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])
            
            if not objects_to_delete:
                return 0
            
            # Delete objects in batches of 1000 (S3 limit)
            deleted_count = 0
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': batch}
                )
                deleted_count += len(response.get('Deleted', []))
            
            return deleted_count
        except ClientError as e:
            raise Exception(f"Failed to delete job artifacts from S3: {e}")
    
    def get_s3_uri(
        self,
        job_name: str,
        phase: str,
        agent_name: str,
        filename: str
    ) -> str:
        """
        Get the S3 URI for an artifact without checking if it exists.
        
        Args:
            job_name: Unique job identifier
            phase: Phase name
            agent_name: Agent name
            filename: File name
            
        Returns:
            S3 URI
        """
        s3_key = self._build_s3_key(job_name, phase, agent_name, filename)
        return f"s3://{self.bucket_name}/{s3_key}"
