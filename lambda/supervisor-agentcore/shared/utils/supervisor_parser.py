"""
Supervisor Requirements Parser
Extracts JSON from supervisor's markdown response and splits it for different agents
"""
import json
import re
from typing import Dict, Any, Optional
from shared.utils.logger import get_logger

logger = get_logger(__name__)


def extract_json_from_supervisor_response(response_text: str) -> Dict[str, Any]:
    """
    Extract JSON from supervisor's response that contains ```json ... ``` blocks.
    
    Args:
        response_text: Full response from supervisor (markdown with embedded JSON)
        
    Returns:
        Parsed JSON object with requirements for all agents
        
    Raises:
        ValueError: If no valid JSON found or parsing fails
    """
    try:
        # Pattern to match ```json ... ``` blocks
        json_pattern = r'```json\s*\n(.*?)\n```'
        matches = re.findall(json_pattern, response_text, re.DOTALL | re.IGNORECASE)
        
        if not matches:
            # Try without language specifier
            json_pattern = r'```\s*\n(\{.*?\})\s*\n```'
            matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        if not matches:
            # Try to find JSON object directly (fallback)
            json_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
            matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        if not matches:
            raise ValueError("No JSON code blocks found in supervisor response")
        
        # Take the first (and should be only) JSON block
        json_text = matches[0].strip()
        
        # Parse JSON
        requirements = json.loads(json_text)
        
        logger.info(f"Successfully extracted JSON with {len(requirements)} top-level keys")
        return requirements
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        logger.error(f"Problematic JSON (first 500 chars): {json_text[:500] if 'json_text' in locals() else 'N/A'}")
        raise ValueError(f"Invalid JSON in supervisor response: {e}")
    except Exception as e:
        logger.error(f"Failed to extract JSON from supervisor response: {e}")
        logger.error(f"Response preview (first 500 chars): {response_text[:500]}")
        raise ValueError(f"Failed to parse supervisor response: {e}")


def split_requirements_for_agents(requirements: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Split the comprehensive requirements JSON into sections for each agent.
    Matches the structure defined in schemas/supervisor-schema.yaml
    
    Args:
        requirements: Complete requirements object from supervisor
        
    Returns:
        Dict mapping agent names to their specific requirements
    """
    try:
        agent_requirements = {}
        
        # Extract Solution Architect requirements
        agent_requirements['solution_architect'] = requirements.get('solution_architect_requirements', {})
        
        # Extract Code Generator requirements  
        agent_requirements['code_generator'] = requirements.get('code_generator_requirements', {})
        
        # Extract Deployment Manager requirements
        agent_requirements['deployment_manager'] = requirements.get('deployment_manager_requirements', {})
        
        # Extract Quality Validator requirements
        agent_requirements['quality_validator'] = {
            'validation_framework': requirements.get('validation_framework', {}),
            'metadata': requirements.get('metadata', {}),
            'risk_assessment': requirements.get('risk_assessment', {})
        }
        
        logger.info(f"Split requirements for {len(agent_requirements)} agents")
        return agent_requirements
        
    except Exception as e:
        logger.error(f"Failed to split requirements for agents: {e}")
        raise ValueError(f"Requirements splitting failed: {e}")


def get_agent_requirements(supervisor_response: str, agent_name: str) -> Dict[str, Any]:
    """
    Convenience function to extract requirements for a specific agent.
    
    Args:
        supervisor_response: Full markdown response from supervisor
        agent_name: Name of agent ('solution_architect', 'code_generator', etc.)
        
    Returns:
        Requirements dict for the specified agent
    """
    try:
        # Extract JSON from supervisor response
        requirements = extract_json_from_supervisor_response(supervisor_response)
        
        # Split for all agents
        agent_requirements = split_requirements_for_agents(requirements)
        
        # Return specific agent's requirements
        if agent_name in agent_requirements:
            return agent_requirements[agent_name]
        else:
            logger.warning(f"No requirements found for agent: {agent_name}")
            return {}
            
    except Exception as e:
        logger.error(f"Failed to get requirements for {agent_name}: {e}")
        raise


def validate_requirements_structure(requirements: Dict[str, Any]) -> bool:
    """
    Validate that the requirements object has the expected structure.
    
    Args:
        requirements: Requirements object to validate
        
    Returns:
        True if structure is valid, False otherwise
    """
    try:
        required_sections = [
            'solution_architect_requirements',
            'code_generator_requirements', 
            'deployment_manager_requirements',
            'validation_framework'
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in requirements:
                missing_sections.append(section)
        
        if missing_sections:
            logger.warning(f"Missing required sections: {missing_sections}")
            return False
        
        # Validate metadata if present
        if 'metadata' in requirements:
            metadata = requirements['metadata']
            required_metadata = ['agent_name', 'agent_type', 'complexity_level']
            for field in required_metadata:
                if field not in metadata:
                    logger.warning(f"Missing metadata field: {field}")
        
        logger.info("✓ Requirements structure validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Requirements validation failed: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    # Test with sample supervisor response
    sample_response = """
    # Requirements Analysis
    
    Based on your request, here are the comprehensive requirements:
    
    ```json
    {
        "metadata": {
            "agent_name": "CustomerServiceBot",
            "agent_type": "conversational",
            "complexity_level": "moderate"
        },
        "solution_architect_requirements": {
            "agent_overview": {
                "name": "CustomerServiceBot",
                "type": "conversational",
                "business_purpose": "Handle customer inquiries"
            }
        },
        "code_generator_requirements": {
            "agent_configuration": {
                "name": "CustomerServiceBot",
                "primary_model": "amazon.nova-premier-v1:0"
            }
        },
        "deployment_manager_requirements": {
            "deployment_configuration": {
                "agent_name": "CustomerServiceBot",
                "environment": "production"
            }
        },
        "validation_framework": {
            "acceptance_criteria": {
                "functional_requirements": []
            }
        }
    }
    ```
    
    This provides a complete specification for building the agent.
    """
    
    try:
        # Test extraction
        requirements = extract_json_from_supervisor_response(sample_response)
        print("✓ JSON extraction successful")
        
        # Test splitting
        agent_reqs = split_requirements_for_agents(requirements)
        print("✓ Requirements splitting successful")
        
        # Test validation
        is_valid = validate_requirements_structure(requirements)
        print(f"✓ Validation result: {is_valid}")
        
        # Test agent-specific extraction
        sa_reqs = get_agent_requirements(sample_response, 'solution_architect')
        print(f"✓ SA requirements extracted: {len(sa_reqs)} keys")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")