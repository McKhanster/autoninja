#!/usr/bin/env python3
"""
Requirements Analyst Agent Demonstration

This script demonstrates the Requirements Analyst Agent making real inference
calls to Amazon Bedrock models, with full request/response logging.

Usage:
    python examples/demo_requirements_analyst.py

Requirements:
    - AWS credentials configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    - Access to Amazon Bedrock in us-east-2 region
    - Claude models enabled in Bedrock
"""

import json
import logging
import sys
import time
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, '.')

from autoninja.agents.requirements_analyst import create_requirements_analyst_agent
from autoninja.core.bedrock_client import BedrockClientManager

# Configure detailed logging to see raw requests/responses
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('requirements_analyst_demo.log')
    ]
)

logger = logging.getLogger(__name__)


def demo_simple_chatbot_request():
    """Demonstrate analysis of a simple chatbot request"""
    
    print("\n" + "="*80)
    print("DEMO 1: Simple Customer Service Chatbot")
    print("="*80)
    
    # Create the Requirements Analyst Agent
    print("Creating Requirements Analyst Agent...")
    agent = create_requirements_analyst_agent()
    
    # Simple user request
    user_request = """
    I need a customer service chatbot for my small online bookstore. 
    The bot should help customers find books, check order status, and answer 
    basic questions about shipping and returns. It should be friendly and 
    easy to use, and I want to keep costs reasonable since I'm a small business.
    """
    
    print(f"\nUser Request:")
    print(f"{user_request}")
    
    print(f"\nMaking inference call to Bedrock...")
    start_time = time.time()
    
    # Make the analysis call - this will make real Bedrock inference
    result = agent.analyze_requirements(user_request, "demo-simple-chatbot")
    
    end_time = time.time()
    
    print(f"\n✅ Analysis completed in {end_time - start_time:.2f} seconds")
    print(f"Confidence Score: {result.output.confidence_score:.2f}")
    
    # Display results
    print(f"\n📋 EXTRACTED REQUIREMENTS:")
    extracted_reqs = result.output.result.get("extracted_requirements", {})
    
    functional_reqs = extracted_reqs.get("functional_requirements", [])
    print(f"Functional Requirements ({len(functional_reqs)}):")
    for i, req in enumerate(functional_reqs[:5], 1):  # Show first 5
        print(f"  {i}. {req}")
    
    non_functional_reqs = extracted_reqs.get("non_functional_requirements", {})
    if non_functional_reqs:
        print(f"\nNon-Functional Requirements:")
        for category, reqs in non_functional_reqs.items():
            print(f"  {category.title()}: {reqs}")
    
    # Display compliance frameworks
    compliance = result.output.result.get("compliance_frameworks", [])
    if compliance:
        print(f"\n🔒 COMPLIANCE FRAMEWORKS: {compliance}")
    
    # Display recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    for i, rec in enumerate(result.output.recommendations, 1):
        print(f"  {i}. {rec}")
    
    return result


def demo_complex_healthcare_request():
    """Demonstrate analysis of a complex healthcare system request"""
    
    print("\n" + "="*80)
    print("DEMO 2: Complex Healthcare AI System")
    print("="*80)
    
    # Create the Requirements Analyst Agent
    agent = create_requirements_analyst_agent()
    
    # Complex healthcare request
    user_request = """
    Our hospital network needs a comprehensive AI agent system that can:
    
    1. Patient Communication:
       - Handle appointment scheduling and rescheduling
       - Send medication reminders and follow-up care instructions
       - Answer basic health questions (non-diagnostic)
       - Provide hospital navigation and department information
    
    2. Staff Support:
       - Assist nurses with patient data lookup
       - Help with inventory management for medical supplies
       - Generate shift reports and patient status summaries
       - Coordinate between departments for patient transfers
    
    3. Administrative Functions:
       - Process insurance verification requests
       - Handle billing inquiries and payment processing
       - Manage patient records and documentation
       - Generate compliance reports for regulatory bodies
    
    4. Integration Requirements:
       - Must integrate with Epic EHR system
       - Connect to our existing patient portal
       - Interface with pharmacy systems for prescription management
       - Link to laboratory systems for test results
    
    5. Compliance and Security:
       - Full HIPAA compliance with audit trails
       - HITECH Act compliance for electronic health records
       - SOC 2 Type II certification requirements
       - End-to-end encryption for all patient data
       - Role-based access controls for different user types
    
    6. Performance Requirements:
       - Handle 50,000+ daily interactions across all hospitals
       - 99.9% uptime with disaster recovery capabilities
       - Response time under 2 seconds for patient queries
       - Support for 10+ languages including Spanish, Mandarin, Arabic
    
    The system must be scalable, secure, and ready for regulatory audits.
    We have a budget of $2M for the first year implementation.
    """
    
    additional_context = {
        "industry": "healthcare",
        "organization_size": "large_hospital_network",
        "compliance_requirements": ["HIPAA", "HITECH", "SOC2"],
        "integration_systems": ["Epic EHR", "Patient Portal", "Pharmacy Systems", "Lab Systems"],
        "languages": ["English", "Spanish", "Mandarin", "Arabic"],
        "budget": "$2M",
        "timeline": "1 year",
        "scale": "50000_daily_interactions"
    }
    
    print(f"User Request: [Complex healthcare system - see full details in log]")
    print(f"Additional Context: {json.dumps(additional_context, indent=2)}")
    
    print(f"\nMaking inference call to Bedrock for complex analysis...")
    start_time = time.time()
    
    # Make the analysis call with additional context
    result = agent.analyze_requirements(user_request, "demo-healthcare-complex", additional_context)
    
    end_time = time.time()
    
    print(f"\n✅ Complex analysis completed in {end_time - start_time:.2f} seconds")
    print(f"Confidence Score: {result.output.confidence_score:.2f}")
    
    # Display comprehensive results
    output_data = result.output.result
    
    print(f"\n📋 ANALYSIS SUMMARY:")
    
    # Functional requirements
    functional_reqs = output_data.get("extracted_requirements", {}).get("functional_requirements", [])
    print(f"Functional Requirements Identified: {len(functional_reqs)}")
    
    # Non-functional requirements
    non_functional_reqs = output_data.get("extracted_requirements", {}).get("non_functional_requirements", {})
    print(f"Non-Functional Requirement Categories: {len(non_functional_reqs)}")
    for category in non_functional_reqs.keys():
        print(f"  - {category.title()}")
    
    # Compliance frameworks
    compliance = output_data.get("compliance_frameworks", [])
    print(f"\n🔒 COMPLIANCE FRAMEWORKS DETECTED: {len(compliance)}")
    for framework in compliance:
        print(f"  - {framework}")
    
    # Complexity assessment
    complexity = output_data.get("complexity_assessment", {})
    if complexity:
        print(f"\n📊 COMPLEXITY ASSESSMENT:")
        for key, value in complexity.items():
            print(f"  {key}: {value}")
    
    # Recommendations
    print(f"\n💡 KEY RECOMMENDATIONS ({len(result.output.recommendations)}):")
    for i, rec in enumerate(result.output.recommendations[:8], 1):  # Show first 8
        print(f"  {i}. {rec}")
    
    # Execution metadata
    metadata = result.execution_metadata
    print(f"\n⚡ EXECUTION METADATA:")
    print(f"  Duration: {metadata.duration_seconds:.2f} seconds")
    print(f"  Model Invocations: {metadata.model_invocations}")
    print(f"  Start Time: {metadata.start_time}")
    
    return result


def demo_model_selection_and_logging():
    """Demonstrate model selection and request/response logging"""
    
    print("\n" + "="*80)
    print("DEMO 3: Model Selection and Logging Verification")
    print("="*80)
    
    # Show Bedrock client manager status
    bedrock_manager = BedrockClientManager()
    
    print("Bedrock Client Manager Status:")
    status = bedrock_manager.get_client_status()
    for model_id, model_status in status.items():
        print(f"  {model_id}:")
        print(f"    Available: {model_status['available']}")
        print(f"    Circuit Breaker: {model_status['circuit_breaker_state']}")
    
    available_models = bedrock_manager.get_available_models()
    print(f"\nAvailable Models: {[model.value for model in available_models]}")
    
    # Create agent and show model selection
    agent = create_requirements_analyst_agent()
    
    print(f"\nAgent Configuration:")
    agent_info = agent.get_agent_info()
    print(f"  Agent Name: {agent_info['agent_name']}")
    print(f"  Model Complexity: {agent_info['model_complexity']}")
    print(f"  Available Tools: {agent_info['tools']}")
    
    # Test with a request that will generate detailed logs
    user_request = "Create an AI agent for automated invoice processing and approval workflows"
    
    print(f"\nTest Request: {user_request}")
    print(f"Making inference call with detailed logging...")
    
    # This will log raw request and response
    result = agent.analyze_requirements(user_request, "demo-logging-test")
    
    print(f"\n✅ Inference completed successfully")
    print(f"Check the log file 'requirements_analyst_demo.log' for raw request/response details")
    
    return result


def main():
    """Run all demonstrations"""
    
    print("🚀 Requirements Analyst Agent - Bedrock Inference Demonstration")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Log file: requirements_analyst_demo.log")
    
    try:
        # Demo 1: Simple request
        result1 = demo_simple_chatbot_request()
        
        # Demo 2: Complex request
        result2 = demo_complex_healthcare_request()
        
        # Demo 3: Model selection and logging
        result3 = demo_model_selection_and_logging()
        
        print("\n" + "="*80)
        print("🎉 ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
        print("="*80)
        
        print(f"\nSummary:")
        print(f"  Demo 1 Confidence: {result1.output.confidence_score:.2f}")
        print(f"  Demo 2 Confidence: {result2.output.confidence_score:.2f}")
        print(f"  Demo 3 Confidence: {result3.output.confidence_score:.2f}")
        
        print(f"\nTotal Execution Time:")
        total_time = (
            result1.execution_metadata.duration_seconds +
            result2.execution_metadata.duration_seconds +
            result3.execution_metadata.duration_seconds
        )
        print(f"  {total_time:.2f} seconds")
        
        print(f"\n📝 Check 'requirements_analyst_demo.log' for detailed logs including:")
        print(f"  - Raw Bedrock requests and responses")
        print(f"  - Model selection decisions")
        print(f"  - Tool execution details")
        print(f"  - Error handling (if any)")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {str(e)}")
        print(f"\n❌ Demonstration failed: {str(e)}")
        print(f"Please check:")
        print(f"  1. AWS credentials are configured")
        print(f"  2. Bedrock access is enabled in us-east-2")
        print(f"  3. Claude models are available")
        sys.exit(1)


if __name__ == "__main__":
    main()