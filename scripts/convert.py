import json
import os
from typing import Any

def markdown_to_json_escaped(file_path: str = None, markdown_text: str = None) -> str:
    """
    Convert markdown text or a markdown file to a JSON-escaped string.
    
    Args:
        file_path (str, optional): Path to the markdown file
        markdown_text (str, optional): Direct markdown text input
        
    Returns:
        str: JSON-escaped string
        
    Raises:
        FileNotFoundError: If file_path is provided but file doesn't exist
        ValueError: If neither file_path nor markdown_text is provided
    """
    if file_path and markdown_text:
        raise ValueError("Provide either file_path or markdown_text, not both")
    if not file_path and not markdown_text:
        raise ValueError("Either file_path or markdown_text must be provided")
    
    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Markdown file not found: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
    
    if not markdown_text:
        return ""
    
    # Escape special characters for JSON
    escaped = json.dumps(markdown_text, ensure_ascii=False)
    # Remove the surrounding quotes added by json.dumps
    return escaped[1:-1]

def json_to_yaml_escaped(json_data: Any) -> str:
    """
    Convert JSON data to a compressed, YAML-escaped string suitable for CloudFormation.
    
    Args:
        json_data: Python object (dict, list, etc.) to be converted
        
    Returns:
        str: YAML-escaped JSON string
        
    Raises:
        json.JSONDecodeError: If the JSON data is invalid
    """
    # Validate JSON data
    try:
        json.dumps(json_data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise json.JSONDecodeError(f"Invalid JSON data: {e}", str(json_data), 0)
    
    # Convert to compact JSON string (no indentation, minimal whitespace)
    compact_json = json.dumps(json_data, separators=(',', ':'), ensure_ascii=False)
    
    # Escape special characters for YAML/CloudFormation compatibility
    escaped = compact_json.replace('"', '\\"')  # Escape double quotes
    escaped = escaped.replace('\n', '\\n')     # Escape newlines
    escaped = escaped.replace('\t', '\\t')     # Escape tabs
    escaped = escaped.replace(':', '\\:')      # Escape colons
    escaped = escaped.replace('!', '\\!')      # Escape exclamation marks
    
    return escaped

def insert_markdown_into_json(markdown_file: str = None, markdown_text: str = None, 
                            json_file: str = None, json_data: Any = None, 
                            target_field: list = None) -> dict:
    """
    Convert Markdown to JSON-escaped string and insert it into a JSON object.
    
    Args:
        markdown_file (str, optional): Path to the markdown file
        markdown_text (str, optional): Direct markdown text input
        json_file (str, optional): Path to the JSON file
        json_data: Python object (dict, list, etc.) to insert into
        target_field (list): List of keys to navigate to the target field (e.g., ['system', 0, 'text'])
        
    Returns:
        dict: Modified JSON data with the escaped markdown inserted
        
    Raises:
        FileNotFoundError: If file_path is provided but file doesn't exist
        ValueError: If inputs are invalid or target_field is unreachable
        json.JSONDecodeError: If the JSON file or data is invalid
    """
    if (markdown_file and markdown_text) or (not markdown_file and not markdown_text):
        raise ValueError("Provide either markdown_file or markdown_text, not both or neither")
    if (json_file and json_data) or (not json_file and json_data is None):
        raise ValueError("Provide either json_file or json_data, not both or neither")
    if not target_field:
        raise ValueError("target_field must be provided to specify where to insert the markdown")
    
    # Convert Markdown to JSON-escaped string
    escaped_markdown = markdown_to_json_escaped(file_path=markdown_file, markdown_text=markdown_text)
    
    # Load or use JSON data
    if json_file:
        if not os.path.exists(json_file):
            raise FileNotFoundError(f"JSON file not found: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                json_data = json.load(f)
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(f"Invalid JSON in file {json_file}: {e}", e.doc, e.pos)
    
    # Navigate to the target field and insert the escaped markdown
    current = json_data
    try:
        for i, key in enumerate(target_field[:-1]):
            if isinstance(key, int):
                while len(current) <= key:
                    current.append({})
            current = current[key]
        current[target_field[-1]] = escaped_markdown
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Could not insert markdown into JSON at {target_field}: {e}")
    
    return json_data

# Example usage
if __name__ == "__main__":
    # Sample Markdown text
    sample_markdown = """
# Heading
This is *markdown* with "quotes" and
multiple lines.
- List item 1
- List item 2
"""
    
    # Sample JSON structure (simplified version of your provided JSON)
    sample_json = {
        "schemaVersion": "messages-v1",
        "system": [
            {
                "text": "Placeholder"
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": "Design a conversational AI agent architecture."
                    }
                ]
            }
        ]
    }
    
    try:
        # Step 1: Convert Markdown and insert into JSON
        modified_json = insert_markdown_into_json(
            markdown_text=sample_markdown,
            json_data=sample_json,
            target_field=["system", 0, "text"]
        )
        print("\nModified JSON with inserted Markdown:")
        print(json.dumps(modified_json, indent=2))
        
        # Step 2: Convert the modified JSON to YAML-escaped string
        yaml_escaped = json_to_yaml_escaped(modified_json)
        print("\nJSON to YAML escaped (after Markdown insertion):")
        print(yaml_escaped)
        print("\nYAML output example for CloudFormation:")
        print(f"Data: \"{yaml_escaped}\"")
        
        # Example with file input
        # Assuming you have a markdown file named 'sample.md' and a JSON file named 'sample.json'
        markdown_file = "/home/mcesel/Documents/proj/autoninja2/infrastructure/cloudformation/prompts/sa-nova.md"
        json_file = "/home/mcesel/Documents/proj/autoninja2/infrastructure/cloudformation/prompts/test.json"
        modified_json_file = insert_markdown_into_json(
            markdown_file=markdown_file,
            json_file=json_file,
            target_field=["system", 0, "text"]
        )
        print("\nModified JSON from file input:")
        print(json.dumps(modified_json_file, indent=2))
        
        yaml_escaped_file = json_to_yaml_escaped(modified_json_file)
        print("\nJSON to YAML escaped (from file):")
        print(yaml_escaped_file)
        
    except FileNotFoundError as e:
        print(f"\nFile error: {e}")
    except json.JSONDecodeError as e:
        print(f"\nJSON error: {e}")
    except ValueError as e:
        print(f"\nValue error: {e}")