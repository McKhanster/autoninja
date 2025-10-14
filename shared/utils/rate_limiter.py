"""
Rate limiter utility for managing API call timing to avoid throttling.

This module provides utilities to ensure proper spacing between API calls
to respect rate limits, particularly for AWS Bedrock on-demand models.

The rate limiter ensures a 30-second TOTAL interval per invocation:
- If call takes 15 seconds, wait another 15 seconds
- If call takes 29 seconds, wait 1 second
- If call takes 35 seconds, don't wait
"""
import time
from typing import Optional


class RateLimiter:
    """
    Rate limiter that ensures minimum total time per operation.
    
    Usage:
        limiter = RateLimiter(min_interval_seconds=30)
        
        start = time.time()
        # ... do work that takes variable time ...
        limiter.wait_if_needed(start)  # Waits remaining time to reach 30s total
    """
    
    def __init__(self, min_interval_seconds: float = 30.0):
        """
        Initialize rate limiter.
        
        Args:
            min_interval_seconds: Minimum total time per operation (default: 30 seconds)
        """
        self.min_interval_seconds = min_interval_seconds
        self.last_operation_time: Optional[float] = None
    
    def wait_if_needed(self, operation_start_time: Optional[float] = None) -> float:
        """
        Wait if needed to ensure minimum total time since operation start.
        
        This ensures the TOTAL time (operation + wait) equals min_interval_seconds.
        
        Args:
            operation_start_time: When the current operation started (from time.time()).
                                 If provided, calculates remaining time from operation start.
                                 If None, uses time since last operation.
        
        Returns:
            Actual wait time in seconds (0 if no wait needed)
            
        Examples:
            - Operation takes 15s: waits 15s (total 30s)
            - Operation takes 29s: waits 1s (total 30s)
            - Operation takes 35s: waits 0s (total 35s)
        """
        current_time = time.time()
        
        # If operation_start_time provided, calculate elapsed time from operation start
        if operation_start_time is not None:
            elapsed = current_time - operation_start_time
            remaining = self.min_interval_seconds - elapsed
        elif self.last_operation_time is not None:
            # Calculate time since last operation completed
            elapsed = current_time - self.last_operation_time
            remaining = self.min_interval_seconds - elapsed
        else:
            # First operation, no wait needed
            remaining = 0
        
        # Wait if needed
        if remaining > 0:
            time.sleep(remaining)
            wait_time = remaining
        else:
            wait_time = 0
        
        # Update last operation time to now (after wait)
        self.last_operation_time = time.time()
        
        return wait_time
    
    def reset(self):
        """Reset the rate limiter (useful for testing)."""
        self.last_operation_time = None


def wait_for_rate_limit(
    operation_start_time: float,
    min_interval_seconds: float = 30.0
) -> float:
    """
    Convenience function to wait for rate limit without maintaining state.
    
    Ensures that at least min_interval_seconds have passed since operation_start_time.
    This guarantees a TOTAL time (operation + wait) of at least min_interval_seconds.
    
    Args:
        operation_start_time: When the operation started (from time.time())
        min_interval_seconds: Minimum total time for the operation (default: 30 seconds)
    
    Returns:
        Actual wait time in seconds (0 if no wait needed)
    
    Examples:
        start = time.time()
        result = do_api_call()  # Takes 15 seconds
        wait_for_rate_limit(start, 30)  # Waits 15 seconds (total 30s)
        
        start = time.time()
        result = do_api_call()  # Takes 29 seconds
        wait_for_rate_limit(start, 30)  # Waits 1 second (total 30s)
        
        start = time.time()
        result = do_api_call()  # Takes 35 seconds
        wait_for_rate_limit(start, 30)  # Waits 0 seconds (total 35s)
    """
    current_time = time.time()
    elapsed = current_time - operation_start_time
    remaining = min_interval_seconds - elapsed
    
    if remaining > 0:
        time.sleep(remaining)
        return remaining
    
    return 0.0


# Alias for backward compatibility
BedrockRateLimiter = RateLimiter
