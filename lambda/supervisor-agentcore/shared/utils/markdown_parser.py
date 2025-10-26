"""
Markdown Parser Utility
Extracts sections and code blocks from markdown documents
"""
import re
from typing import Dict, Any, Optional, List


def extract_section(markdown: str, section_header: str, level: int = 2) -> str:
    """
    Extract a section from markdown by header.
    
    Args:
        markdown: Full markdown document
        section_header: Header text to find (without # symbols)
        level: Header level (2 for ##, 3 for ###, etc.)
    
    Returns:
        The section content including subsections
    
    Example:
        extract_section(doc, "For Solution Architect", level=2)
        Returns everything under "## For Solution Architect" until next ## header
    """
    # Build the header pattern
    header_prefix = "#" * level
    pattern = f"^{header_prefix} {re.escape(section_header)}$"
    
    lines = markdown.split('\n')
    start_idx = None
    
    # Find the section start
    for i, line in enumerate(lines):
        if re.match(pattern, line.strip()):
            start_idx = i
            break
    
    if start_idx is None:
        return ""
    
    # Find the section end (next header of same or higher level)
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        # Check if this is a header of same or higher level
        if re.match(f"^#{{{1,{level}}}} ", lines[i].strip()):
            end_idx = i
            break
    
    # Return the section content
    return '\n'.join(lines[start_idx:end_idx]).strip()


def extract_all_sections(markdown: str, level: int = 2) -> Dict[str, str]:
    """
    Extract all sections at a given level.
    
    Args:
        markdown: Full markdown document
        level: Header level to extract (2 for ##, 3 for ###)
    
    Returns:
        Dict mapping section names to their content
    
    Example:
        {
            "Executive Summary": "...",
            "For Solution Architect": "...",
            "For Code Generator": "..."
        }
    """
    sections = {}
    header_prefix = "#" * level
    pattern = f"^{header_prefix} (.+)$"
    
    lines = markdown.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = match.group(1)
            current_content = [line]
        elif current_section:
            current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def extract_code_block(markdown: str, language: Optional[str] = None, index: int = 0) -> str:
    """
    Extract code from markdown code blocks.
    
    Args:
        markdown: Markdown text containing code blocks
        language: Optional language filter (e.g., 'python', 'yaml', 'json')
        index: Which code block to extract (0 for first, 1 for second, etc.)
    
    Returns:
        The code content without the ``` markers
    
    Example:
        extract_code_block(text, language='python', index=0)
        Returns the first Python code block
    """
    if language:
        pattern = f"```{re.escape(language)}\\s*\\n(.*?)\\n```"
    else:
        pattern = r"```[a-zA-Z]*\s*\n(.*?)\n```"
    
    matches = re.findall(pattern, markdown, re.DOTALL | re.IGNORECASE)
    
    if index < len(matches):
        return matches[index].strip()
    
    return ""


def extract_all_code_blocks(markdown: str) -> List[Dict[str, str]]:
    """
    Extract all code blocks with their languages.
    
    Args:
        markdown: Markdown text
    
    Returns:
        List of dicts with 'language' and 'code' keys
    
    Example:
        [
            {'language': 'python', 'code': 'def foo(): pass'},
            {'language': 'yaml', 'code': 'key: value'}
        ]
    """
    pattern = r"```([a-zA-Z]*)\s*\n(.*?)\n```"
    matches = re.findall(pattern, markdown, re.DOTALL | re.IGNORECASE)
    
    return [
        {
            'language': lang.lower() if lang else 'text',
            'code': code.strip()
        }
        for lang, code in matches
    ]


def extract_bullet_list(markdown: str, section_header: Optional[str] = None) -> List[str]:
    """
    Extract bullet points from a section.
    
    Args:
        markdown: Markdown text
        section_header: Optional section to extract from first
    
    Returns:
        List of bullet point texts (without the - or * markers)
    
    Example:
        extract_bullet_list(text, "Core Capabilities")
        Returns: ["Capability 1", "Capability 2", ...]
    """
    if section_header:
        markdown = extract_section(markdown, section_header, level=3)
    
    pattern = r"^[\-\*]\s+(.+)$"
    lines = markdown.split('\n')
    
    bullets = []
    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            # Remove bold markers if present
            text = match.group(1)
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            bullets.append(text.strip())
    
    return bullets


def extract_key_value_pairs(markdown: str, section_header: Optional[str] = None) -> Dict[str, str]:
    """
    Extract key-value pairs from markdown (e.g., "- **Key**: value").
    
    Args:
        markdown: Markdown text
        section_header: Optional section to extract from first
    
    Returns:
        Dict of key-value pairs
    
    Example:
        extract_key_value_pairs(text, "Executive Summary")
        Returns: {"Agent Name": "MyAgent", "Purpose": "...", ...}
    """
    if section_header:
        markdown = extract_section(markdown, section_header, level=2)
    
    pattern = r"[\-\*]\s+\*\*(.+?)\*\*:\s*(.+)$"
    lines = markdown.split('\n')
    
    pairs = {}
    for line in lines:
        match = re.match(pattern, line.strip())
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            pairs[key] = value
    
    return pairs


def markdown_to_dict(markdown: str) -> Dict[str, Any]:
    """
    Convert a structured markdown document to a nested dictionary.
    Specifically designed for Requirements Analyst output.
    
    Args:
        markdown: Full markdown document
    
    Returns:
        Nested dictionary matching the expected structure
    
    Example:
        {
            "executive_summary": {...},
            "for_solution_architect": {...},
            "for_code_generator": {...},
            ...
        }
    """
    result = {}
    
    # Extract Executive Summary
    exec_summary = extract_section(markdown, "Executive Summary", level=2)
    if exec_summary:
        result['executive_summary'] = extract_key_value_pairs(exec_summary)
    
    # Extract For Solution Architect
    sa_section = extract_section(markdown, "For Solution Architect", level=2)
    if sa_section:
        result['for_solution_architect'] = {
            'performance_requirements': extract_key_value_pairs(
                extract_section(sa_section, "Performance Requirements", level=3)
            ),
            'integration_requirements': {
                'external_apis': extract_bullet_list(sa_section, "External APIs"),
                'data_sources': extract_bullet_list(sa_section, "Data Sources"),
                'aws_services': extract_bullet_list(sa_section, "AWS Services"),
                'networking': extract_section(sa_section, "Networking", level=4)
            }
        }
    
    # Extract For Code Generator
    cg_section = extract_section(markdown, "For Code Generator", level=2)
    if cg_section:
        result['for_code_generator'] = {
            'functional_specifications': {
                'core_capabilities': extract_bullet_list(cg_section, "Core Capabilities"),
                'user_interaction_patterns': extract_bullet_list(cg_section, "User Interaction Patterns"),
                'input_validation': extract_bullet_list(cg_section, "Input Validation"),
                'output_formats': extract_bullet_list(cg_section, "Output Formats"),
                'error_scenarios': extract_bullet_list(cg_section, "Error Scenarios")
            },
            'business_logic': {
                'decision_rules': extract_bullet_list(cg_section, "Decision Rules"),
                'calculations': extract_bullet_list(cg_section, "Calculations"),
                'workflows': extract_bullet_list(cg_section, "Workflows"),
                'data_transformations': extract_bullet_list(cg_section, "Data Transformations")
            },
            'agent_personality': extract_key_value_pairs(
                extract_section(cg_section, "Agent Personality", level=3)
            )
        }
    
    # Extract For Quality Validator
    qv_section = extract_section(markdown, "For Quality Validator", level=2)
    if qv_section:
        result['for_quality_validator'] = {
            'security_requirements': extract_key_value_pairs(
                extract_section(qv_section, "Security Requirements", level=3)
            ),
            'compliance_framework': {
                'regulations': extract_bullet_list(qv_section, "Regulations"),
                'industry_standards': extract_bullet_list(qv_section, "Industry Standards"),
                'data_classification': extract_section(qv_section, "Data Classification", level=4)
            },
            'quality_gates': {
                'performance_benchmarks': extract_bullet_list(qv_section, "Performance Benchmarks"),
                'reliability_targets': extract_section(qv_section, "Reliability Targets", level=4),
                'security_controls': extract_bullet_list(qv_section, "Security Controls")
            }
        }
    
    # Extract For Deployment Manager
    dm_section = extract_section(markdown, "For Deployment Manager", level=2)
    if dm_section:
        result['for_deployment_manager'] = {
            'infrastructure_specifications': {
                'compute_requirements': extract_key_value_pairs(
                    extract_section(dm_section, "Compute Requirements", level=4)
                ),
                'storage_requirements': {
                    's3_buckets': extract_bullet_list(dm_section, "S3 Buckets"),
                    'dynamodb_tables': extract_bullet_list(dm_section, "DynamoDB Tables")
                },
                'networking_requirements': extract_key_value_pairs(
                    extract_section(dm_section, "Networking Requirements", level=4)
                )
            },
            'operational_requirements': {
                'monitoring_needs': extract_bullet_list(dm_section, "Monitoring Needs"),
                'logging_requirements': extract_section(dm_section, "Logging Requirements", level=4),
                'backup_strategy': extract_section(dm_section, "Backup Strategy", level=4)
            }
        }
    
    # Extract Validation Criteria
    vc_section = extract_section(markdown, "Validation Criteria", level=2)
    if vc_section:
        result['validation_criteria'] = {
            'success_metrics': extract_bullet_list(vc_section, "Success Metrics"),
            'acceptance_tests': extract_bullet_list(vc_section, "Acceptance Tests"),
            'performance_tests': extract_bullet_list(vc_section, "Performance Tests")
        }
    
    return result
