"""
Job name generator for AutoNinja.

This module provides utilities to generate unique job identifiers
in the format: job-{keyword}-{YYYYMMDD-HHMMSS}
"""

import re
from datetime import datetime
from typing import Optional


def generate_job_name(user_request: str, keyword: Optional[str] = None) -> str:
    """
    Generate a unique job name from a user request.
    
    Format: job-{keyword}-{YYYYMMDD-HHMMSS}
    Example: job-friend-20251013-143022
    
    Args:
        user_request: The user's natural language request
        keyword: Optional explicit keyword. If not provided, extracts from user_request
        
    Returns:
        Unique job name string
    """
    # Extract keyword if not provided
    if not keyword:
        keyword = extract_keyword(user_request)
    
    # Clean and normalize keyword
    keyword = normalize_keyword(keyword)
    
    # Generate timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    
    return f"job-{keyword}-{timestamp}"


def extract_keyword(user_request: str, max_length: int = 20) -> str:
    """
    Extract a meaningful keyword from the user request.
    
    This function attempts to find the most relevant noun or key concept
    from the user's request to use as the job identifier.
    
    Args:
        user_request: The user's natural language request
        max_length: Maximum length for the keyword (default: 20)
        
    Returns:
        Extracted keyword
    """
    # Common words to skip
    skip_words = {
        'i', 'want', 'need', 'would', 'like', 'create', 'build', 'make',
        'generate', 'develop', 'design', 'implement', 'a', 'an', 'the',
        'to', 'for', 'with', 'that', 'can', 'could', 'should', 'will',
        'agent', 'system', 'application', 'app', 'service', 'tool'
    }
    
    # Clean and tokenize the request
    words = re.findall(r'\b[a-zA-Z]+\b', user_request.lower())
    
    # Find the first meaningful word
    for word in words:
        if word not in skip_words and len(word) >= 3:
            return word[:max_length]
    
    # Fallback: use first word or 'agent'
    if words:
        return words[0][:max_length]
    
    return 'agent'


def normalize_keyword(keyword: str) -> str:
    """
    Normalize a keyword for use in job names.
    
    - Convert to lowercase
    - Replace spaces and underscores with hyphens
    - Remove special characters
    - Limit length
    
    Args:
        keyword: Raw keyword string
        
    Returns:
        Normalized keyword
    """
    # Convert to lowercase
    keyword = keyword.lower()
    
    # Replace spaces and underscores with hyphens
    keyword = re.sub(r'[\s_]+', '-', keyword)
    
    # Remove special characters (keep only alphanumeric and hyphens)
    keyword = re.sub(r'[^a-z0-9-]', '', keyword)
    
    # Remove leading/trailing hyphens
    keyword = keyword.strip('-')
    
    # Collapse multiple hyphens
    keyword = re.sub(r'-+', '-', keyword)
    
    # Limit length to 20 characters
    if len(keyword) > 20:
        keyword = keyword[:20].rstrip('-')
    
    # Ensure we have at least something
    if not keyword:
        keyword = 'agent'
    
    return keyword


def parse_job_name(job_name: str) -> dict:
    """
    Parse a job name into its components.
    
    Args:
        job_name: Job name in format job-{keyword}-{YYYYMMDD-HHMMSS}
        
    Returns:
        Dict with 'keyword', 'date', 'time', and 'timestamp' keys
        
    Raises:
        ValueError: If job_name format is invalid
    """
    pattern = r'^job-([a-z0-9-]+)-(\d{8})-(\d{6})$'
    match = re.match(pattern, job_name)
    
    if not match:
        raise ValueError(f"Invalid job name format: {job_name}")
    
    keyword, date_str, time_str = match.groups()
    
    return {
        'keyword': keyword,
        'date': date_str,
        'time': time_str,
        'timestamp': f"{date_str}-{time_str}"
    }


def is_valid_job_name(job_name: str) -> bool:
    """
    Check if a string is a valid job name.
    
    Args:
        job_name: String to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^job-[a-z0-9-]+-\d{8}-\d{6}$'
    return bool(re.match(pattern, job_name))
