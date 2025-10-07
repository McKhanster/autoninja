#!/usr/bin/env python3
"""
Test Logging Setup

This script demonstrates the new structured logging configuration
and shows where logs are saved.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, '.')

from autoninja.core.logging_config import setup_logging, get_session_logger
from autoninja.agents.requirements_analyst import create_requirements_analyst_agent

def test_logging_configuration():
    """Test the logging configuration and show log file locations."""
    
    print("🔧 Setting up AutoNinja Logging Configuration")
    print("=" * 60)
    
    # Setup logging with custom configuration
    setup_logging(
        log_level="INFO",
        enable_file_logging=True,
        enable_console_logging=True
    )
    
    # Show log file locations
    logs_dir = Path.cwd() / "logs"
    print(f"📁 Log files will be saved to: {logs_dir.absolute()}")
    print(f"   - Main application log: {logs_dir / 'autoninja.log'}")
    print(f"   - Requirements Analyst log: {logs_dir / 'requirements_analyst.log'}")
    print(f"   - Bedrock inference log: {logs_dir / 'bedrock_inference.log'}")
    print(f"   - Error log: {logs_dir / 'errors.log'}")
    
    # Test session logging
    print(f"\n🧪 Testing session-based logging...")
    session_logger = get_session_logger("test-session-123", "test-execution-456")
    session_logger.info("This is a test log message with session context")
    
    # Test Requirements Analyst Agent logging
    print(f"\n🤖 Testing Requirements Analyst Agent logging...")
    try:
        agent = create_requirements_analyst_agent()
        
        # This will create logs in the requirements_analyst.log file
        print(f"✅ Agent created successfully - check logs for initialization messages")
        
        # Test a simple analysis (will fail due to credentials, but will log the attempt)
        print(f"\n📝 Testing analysis logging (will fail due to credentials, but logs will be created)...")
        result = agent.analyze_requirements(
            "Create a simple test chatbot for customer support",
            "logging-test-session"
        )
        
        print(f"✅ Analysis completed (with errors expected) - check logs for detailed request/response")
        
    except Exception as e:
        print(f"⚠️  Expected error occurred: {str(e)}")
        print(f"   This is normal - check the error.log file for details")
    
    # Show log file contents
    print(f"\n📋 Log File Contents:")
    print("=" * 60)
    
    log_files = [
        ("Main Log", logs_dir / "autoninja.log"),
        ("Requirements Analyst Log", logs_dir / "requirements_analyst.log"),
        ("Bedrock Inference Log", logs_dir / "bedrock_inference.log"),
        ("Error Log", logs_dir / "errors.log")
    ]
    
    for name, log_file in log_files:
        if log_file.exists():
            print(f"\n📄 {name} ({log_file}):")
            print("-" * 40)
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # Show last 5 lines
                    for line in lines[-5:]:
                        print(f"   {line.strip()}")
            except Exception as e:
                print(f"   Error reading file: {e}")
        else:
            print(f"\n📄 {name}: File not created yet")
    
    print(f"\n🎉 Logging test completed!")
    print(f"📁 All logs are saved in: {logs_dir.absolute()}")
    print(f"💡 You can monitor logs in real-time with: tail -f {logs_dir}/autoninja.log")

if __name__ == "__main__":
    test_logging_configuration()