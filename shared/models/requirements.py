"""Requirements data model for structured requirements."""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json


@dataclass
class Requirements:
    """Model for structured requirements extracted from user requests."""
    
    agent_purpose: str
    capabilities: List[str]
    interactions: List[str]
    data_needs: List[str]
    integrations: List[str]
    system_prompts: str
    lambda_requirements: Dict[str, Any]
    architecture_requirements: Dict[str, Any]
    deployment_requirements: Dict[str, Any]
    complexity: Optional[str] = None
    additional_notes: Optional[str] = None

    def to_json(self) -> str:
        """
        Serialize Requirements to JSON string.
        
        Returns:
            str: JSON representation of requirements
        """
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Requirements':
        """
        Deserialize Requirements from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            Requirements: Deserialized instance
        """
        data = json.loads(json_str)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Requirements to dictionary.
        
        Returns:
            dict: Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Requirements':
        """
        Create Requirements from dictionary.
        
        Args:
            data: Dictionary with requirements data
            
        Returns:
            Requirements: New instance
        """
        return cls(**data)
