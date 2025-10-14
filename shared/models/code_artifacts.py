"""CodeArtifacts data model for generated code."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import json


@dataclass
class CodeArtifacts:
    """Model for generated code artifacts."""
    
    lambda_code: Dict[str, str]  # filename -> code content
    agent_config: Dict[str, Any]
    openapi_schemas: Dict[str, str]  # action_group_name -> schema yaml/json
    system_prompts: str
    requirements_txt: str
    additional_files: Optional[Dict[str, str]] = None

    def to_json(self) -> str:
        """
        Serialize CodeArtifacts to JSON string.
        
        Returns:
            str: JSON representation of code artifacts
        """
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'CodeArtifacts':
        """
        Deserialize CodeArtifacts from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            CodeArtifacts: Deserialized instance
        """
        data = json.loads(json_str)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert CodeArtifacts to dictionary.
        
        Returns:
            dict: Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeArtifacts':
        """
        Create CodeArtifacts from dictionary.
        
        Args:
            data: Dictionary with code artifacts data
            
        Returns:
            CodeArtifacts: New instance
        """
        return cls(**data)
