#!/usr/bin/env python3
"""
Escape JSON prompt files for embedding in CloudFormation YAML templates.
Removes problematic characters like emojis and ensures proper formatting.
"""

import json
import sys
from pathlib import Path


def clean_text(text: str) -> str:
    """Remove emoji and other problematic Unicode characters."""
    # Remove warning emoji
    text = text.replace("⚠️", "[WARNING]")
    text = text.replace("✅", "[OK]")
    text = text.replace("❌", "[ERROR]")
    
    # Remove other potential problematic characters
    # Keep only ASCII printable + common whitespace
    cleaned = ""
    for char in text:
        if ord(char) < 128 or char in ['\n', '\t']:
            cleaned += char
        elif char == '—':  # em dash
            cleaned += '--'
        elif char == '–':  # en dash
            cleaned += '-'
    
    return cleaned


def process_json_file(input_path: Path, output_path: Path = None):
    """Process a JSON file to make it YAML-safe."""
    if output_path is None:
        output_path = input_path
    
    # Read the JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Clean all string values recursively
    def clean_dict(obj):
        if isinstance(obj, dict):
            return {k: clean_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_dict(item) for item in obj]
        elif isinstance(obj, str):
            return clean_text(obj)
        else:
            return obj
    
    cleaned_data = clean_dict(data)
    
    # Write back
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=True)
    
    print(f"Processed: {input_path} -> {output_path}")


def main():
    prompts_dir = Path("infrastructure/cloudformation/prompts")
    
    # Process all JSON files
    for json_file in prompts_dir.glob("*.json"):
        if not json_file.name.endswith('-nova.json'):  # Skip nova files for now
            process_json_file(json_file)
    
    print("\nAll prompt files have been cleaned and are YAML-safe!")


if __name__ == "__main__":
    main()
