"""Architecture data model for architecture design."""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json


@dataclass
class Architecture:
    """Model for architecture design specifications."""
    
    services: List[str]
    resources: Dict[str, Any]
    iam_policies: Dict[str, Any]
    integration_points: List[Dict[str, Any]]
    architecture_diagram: Optional[str] = None
    service_rationale: Optional[Dict[str, str]] = None
    cost_estimate: Optional[str] = None
    scalability_notes: Optional[str] = None

    def to_json(self) -> str:
        """
        Serialize Architecture to JSON string.
        
        Returns:
            str: JSON representation of architecture
        """
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Architecture':
        """
        Deserialize Architecture from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            Architecture: Deserialized instance
        """
        data = json.loads(json_str)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Architecture to dictionary.
        
        Returns:
            dict: Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Architecture':
        """
        Create Architecture from dictionary.
        
        Args:
            data: Dictionary with architecture data
            
        Returns:
            Architecture: New instance
        """
        return cls(**data)
