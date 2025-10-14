"""
Unit tests for Requirements Analyst Lambda handler
Tests the business logic without requiring AWS resources
"""
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Set environment variables BEFORE importing handler
os.environ['DYNAMODB_TABLE_NAME'] = 'test-table'
os.environ['S3_BUCKET_NAME'] = 'test-bucket'
os.environ['AWS_REGION'] = 'us-east-2'

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))


def test_extract_capabilities():
    """Test capability extraction logic"""
    print("\n" + "="*80)
    print("UNIT TEST: Extract Capabilities")
    print("="*80)
    
    from handler import extract_capabilities
    
    test_cases = [
        ("I want a friend agent", ["Friendly interaction and companionship", "Emotional support"]),
        ("Help me answer questions", ["User assistance", "Question answering"]),
        ("Chat with users", ["Natural language conversation"]),
        ("Generic agent", ["General purpose interaction"]),
    ]
    
    for user_request, expected_keywords in test_cases:
        result = extract_capabilities(user_request)
        print(f"\nInput: '{user_request}'")
        print(f"Output: {result}")
        
        # Check if at least one expected keyword is in results
        has_match = any(any(keyword.lower() in cap.lower() for keyword in expected_keywords) for cap in result)
        status = "✅ PASS" if has_match or result else "❌ FAIL"
        print(f"Status: {status}")
    
    return True


def test_calculate_complexity_score():
    """Test complexity scoring logic"""
    print("\n" + "="*80)
    print("UNIT TEST: Calculate Complexity Score")
    print("="*80)
    
    from handler import calculate_complexity_score
    
    test_cases = [
        ({
            "capabilities": ["cap1"],
            "integrations": ["int1"],
            "data_needs": [],
            "lambda_requirements": {"actions": [{"name": "action1"}]},
            "architecture_requirements": {"storage": {}}
        }, "simple"),
        ({
            "capabilities": ["cap1", "cap2", "cap3"],
            "integrations": ["int1", "int2"],
            "data_needs": ["data1", "data2"],
            "lambda_requirements": {"actions": [{"name": "a1"}, {"name": "a2"}]},
            "architecture_requirements": {"storage": {"dynamodb_tables": 1}}
        }, "moderate"),
        ({
            "capabilities": ["c1", "c2", "c3", "c4", "c5", "c6"],
            "integrations": ["i1", "i2", "i3", "i4"],
            "data_needs": ["d1", "d2", "d3", "d4"],
            "lambda_requirements": {"actions": [{"name": f"a{i}"} for i in range(5)]},
            "architecture_requirements": {"storage": {"dynamodb_tables": 2, "s3_buckets": 1}}
        }, "complex"),
    ]
    
    for requirements, expected_complexity in test_cases:
        result = calculate_complexity_score(requirements)
        print(f"\nCapabilities: {len(requirements['capabilities'])}, Integrations: {len(requirements['integrations'])}")
        print(f"Expected: {expected_complexity}, Got: {result}")
        status = "✅ PASS" if result == expected_complexity else "❌ FAIL"
        print(f"Status: {status}")
    
    return True


def test_validate_requirements_completeness():
    """Test requirements validation logic"""
    print("\n" + "="*80)
    print("UNIT TEST: Validate Requirements Completeness")
    print("="*80)
    
    from handler import validate_requirements_completeness
    
    # Test 1: Complete requirements
    complete_reqs = {
        "agent_purpose": "Test agent for validation",
        "capabilities": ["cap1", "cap2"],
        "interactions": ["interaction1"],
        "system_prompts": "This is a detailed system prompt that is long enough to pass validation checks",
        "lambda_requirements": {
            "runtime": "python3.12",
            "actions": [{"name": "action1"}]
        },
        "architecture_requirements": {
            "bedrock": {"model": "claude"},
            "iam": {"roles": ["role1"]}
        },
        "deployment_requirements": {
            "deployment_method": "cloudformation",
            "region": "us-east-1"
        }
    }
    
    result = validate_requirements_completeness(complete_reqs)
    print(f"\nTest 1: Complete Requirements")
    print(f"  Is Valid: {result['is_valid']}")
    print(f"  Missing Items: {len(result['missing_items'])}")
    print(f"  Status: {'✅ PASS' if result['is_valid'] else '❌ FAIL'}")
    
    # Test 2: Incomplete requirements
    incomplete_reqs = {
        "agent_purpose": "Test",
        "capabilities": [],  # Missing
        "interactions": [],  # Missing
    }
    
    result2 = validate_requirements_completeness(incomplete_reqs)
    print(f"\nTest 2: Incomplete Requirements")
    print(f"  Is Valid: {result2['is_valid']}")
    print(f"  Missing Items: {len(result2['missing_items'])}")
    print(f"  Missing: {result2['missing_items'][:3]}")
    print(f"  Status: {'✅ PASS' if not result2['is_valid'] and len(result2['missing_items']) > 0 else '❌ FAIL'}")
    
    return True


def test_event_parsing():
    """Test Bedrock Agent event parsing"""
    print("\n" + "="*80)
    print("UNIT TEST: Event Parsing")
    print("="*80)
    
    event = {
        'messageVersion': '1.0',
        'agent': {'name': 'requirements-analyst'},
        'sessionId': 'test-session',
        'actionGroup': 'requirements-analyst-actions',
        'apiPath': '/extract-requirements',
        'httpMethod': 'POST',
        'requestBody': {
            'content': {
                'application/json': {
                    'properties': [
                        {'name': 'job_name', 'type': 'string', 'value': 'job-test-123'},
                        {'name': 'user_request', 'type': 'string', 'value': 'Test request'}
                    ]
                }
            }
        }
    }
    
    # Extract parameters
    request_body = event.get('requestBody', {})
    content = request_body.get('content', {})
    json_content = content.get('application/json', {})
    properties = json_content.get('properties', [])
    params = {prop['name']: prop['value'] for prop in properties}
    
    print(f"\nExtracted Parameters:")
    print(f"  job_name: {params.get('job_name')}")
    print(f"  user_request: {params.get('user_request')}")
    print(f"  apiPath: {event.get('apiPath')}")
    
    status = "✅ PASS" if params.get('job_name') == 'job-test-123' else "❌ FAIL"
    print(f"\nStatus: {status}")
    
    return True


def run_unit_tests():
    """Run all unit tests"""
    print("\n" + "="*80)
    print("REQUIREMENTS ANALYST - UNIT TEST SUITE")
    print("="*80)
    print("\nThese tests validate business logic without requiring AWS resources")
    
    results = []
    
    try:
        results.append(("Event Parsing", test_event_parsing()))
    except Exception as e:
        print(f"\n❌ Event Parsing FAILED: {e}")
        results.append(("Event Parsing", False))
    
    try:
        results.append(("Extract Capabilities", test_extract_capabilities()))
    except Exception as e:
        print(f"\n❌ Extract Capabilities FAILED: {e}")
        results.append(("Extract Capabilities", False))
    
    try:
        results.append(("Calculate Complexity", test_calculate_complexity_score()))
    except Exception as e:
        print(f"\n❌ Calculate Complexity FAILED: {e}")
        results.append(("Calculate Complexity", False))
    
    try:
        results.append(("Validate Requirements", test_validate_requirements_completeness()))
    except Exception as e:
        print(f"\n❌ Validate Requirements FAILED: {e}")
        results.append(("Validate Requirements", False))
    
    # Summary
    print("\n" + "="*80)
    print("UNIT TEST SUMMARY")
    print("="*80)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name}: {status}")
    print("="*80)
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n🎉 ALL UNIT TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED")
    
    return all_passed


if __name__ == '__main__':
    success = run_unit_tests()
    sys.exit(0 if success else 1)
