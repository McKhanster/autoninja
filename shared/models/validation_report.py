"""ValidationReport data model for quality validation results."""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json


@dataclass
class ValidationReport:
    """Model for quality validation results."""
    
    is_valid: bool
    quality_score: float
    issues: List[Dict[str, Any]]
    vulnerabilities: List[Dict[str, Any]]
    compliance_violations: List[Dict[str, Any]]
    risk_level: str  # "low" | "medium" | "high" | "critical"
    recommendations: Optional[List[str]] = None
    validation_timestamp: Optional[str] = None

    def to_json(self) -> str:
        """
        Serialize ValidationReport to JSON string.
        
        Returns:
            str: JSON representation of validation report
        """
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'ValidationReport':
        """
        Deserialize ValidationReport from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            ValidationReport: Deserialized instance
        """
        data = json.loads(json_str)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ValidationReport to dictionary.
        
        Returns:
            dict: Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationReport':
        """
        Create ValidationReport from dictionary.
        
        Args:
            data: Dictionary with validation report data
            
        Returns:
            ValidationReport: New instance
        """
        return cls(**data)
