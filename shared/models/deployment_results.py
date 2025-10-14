"""DeploymentResults data model for deployment outcomes."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import json


@dataclass
class DeploymentResults:
    """Model for deployment outcomes."""
    
    stack_id: str
    agent_id: str
    agent_arn: str
    alias_id: str
    test_results: Dict[str, Any]
    is_successful: bool
    deployment_timestamp: Optional[str] = None
    stack_outputs: Optional[Dict[str, str]] = None
    error_details: Optional[str] = None

    def to_json(self) -> str:
        """
        Serialize DeploymentResults to JSON string.
        
        Returns:
            str: JSON representation of deployment results
        """
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'DeploymentResults':
        """
        Deserialize DeploymentResults from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            DeploymentResults: Deserialized instance
        """
        data = json.loads(json_str)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert DeploymentResults to dictionary.
        
        Returns:
            dict: Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentResults':
        """
        Create DeploymentResults from dictionary.
        
        Args:
            data: Dictionary with deployment results data
            
        Returns:
            DeploymentResults: New instance
        """
        return cls(**data)
