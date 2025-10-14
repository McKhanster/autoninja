"""InferenceRecord data model for DynamoDB persistence."""

from dataclasses import dataclass, asdict
from typing import Optional
from decimal import Decimal


@dataclass
class InferenceRecord:
    """Model for storing inference records in DynamoDB."""
    
    job_name: str
    timestamp: str
    session_id: str
    agent_name: str
    action_name: str
    inference_id: str
    prompt: str  # Raw prompt
    response: str  # Raw response
    model_id: str
    tokens_used: int
    cost_estimate: float
    duration_seconds: float
    artifacts_s3_uri: str
    status: str  # "success" | "error"
    error_message: Optional[str] = None

    def to_dynamodb(self) -> dict:
        """
        Convert InferenceRecord to DynamoDB item format.
        
        Returns:
            dict: DynamoDB item with proper type conversions
        """
        item = asdict(self)
        
        # Convert float to Decimal for DynamoDB
        item['cost_estimate'] = Decimal(str(self.cost_estimate))
        item['duration_seconds'] = Decimal(str(self.duration_seconds))
        
        # Remove None values
        if item['error_message'] is None:
            del item['error_message']
        
        return item

    @classmethod
    def from_dynamodb(cls, item: dict) -> 'InferenceRecord':
        """
        Create InferenceRecord from DynamoDB item.
        
        Args:
            item: DynamoDB item dictionary
            
        Returns:
            InferenceRecord: Deserialized instance
        """
        # Convert Decimal back to float
        if 'cost_estimate' in item:
            item['cost_estimate'] = float(item['cost_estimate'])
        if 'duration_seconds' in item:
            item['duration_seconds'] = float(item['duration_seconds'])
        
        # Handle optional error_message
        if 'error_message' not in item:
            item['error_message'] = None
        
        return cls(**item)
