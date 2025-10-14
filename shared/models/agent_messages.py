"""Agent communication models for supervisor-collaborator messaging."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import json


@dataclass
class SupervisorMessage:
    """Message format for supervisor-to-collaborator communication."""
    
    job_name: str
    message_id: str
    target_agent: str
    action: str
    parameters: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

    def to_json(self) -> str:
        """
        Serialize SupervisorMessage to JSON string.
        
        Returns:
            str: JSON representation of message
        """
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'SupervisorMessage':
        """
        Deserialize SupervisorMessage from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            SupervisorMessage: Deserialized instance
        """
        data = json.loads(json_str)
        return cls(**data)

    def validate(self) -> bool:
        """
        Validate message structure.
        
        Returns:
            bool: True if message is valid
        """
        if not self.job_name or not self.message_id:
            return False
        if not self.target_agent or not self.action:
            return False
        if not isinstance(self.parameters, dict):
            return False
        return True


@dataclass
class CollaboratorResponse:
    """Message format for collaborator-to-supervisor responses."""
    
    job_name: str
    message_id: str
    source_agent: str
    action: str
    status: str  # "success" | "error" | "pending"
    result: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: Optional[str] = None

    def to_json(self) -> str:
        """
        Serialize CollaboratorResponse to JSON string.
        
        Returns:
            str: JSON representation of response
        """
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'CollaboratorResponse':
        """
        Deserialize CollaboratorResponse from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            CollaboratorResponse: Deserialized instance
        """
        data = json.loads(json_str)
        return cls(**data)

    def validate(self) -> bool:
        """
        Validate response structure.
        
        Returns:
            bool: True if response is valid
        """
        if not self.job_name or not self.message_id:
            return False
        if not self.source_agent or not self.action:
            return False
        if self.status not in ["success", "error", "pending"]:
            return False
        if not isinstance(self.result, dict):
            return False
        return True
