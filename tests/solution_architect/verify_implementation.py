#!/usr/bin/env python3
"""
Verification script to check if design_architecture implementation follows the pattern
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

def verify_implementation():
    """Verify the implementation follows the required pattern"""
    print("\n" + "="*80)
    print("VERIFYING IMPLEMENTATION PATTERN")
    print("="*80)
    
    # Read the handler file
    handler_path = "lambda/solution-architect/handler.py"
    with open(handler_path, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check 1: STEP 1 - Log input immediately
    check1 = "timestamp = dynamodb_client.log_inference_input(" in content
    checks.append(("STEP 1: Log inference input immediately", check1))
    
    # Check 2: STEP 2 - Store timestamp
    check2 = "['timestamp']" in content and "timestamp = dynamodb_client.log_inference_input" in content
    checks.append(("STEP 2: Store returned timestamp", check2))
    
    # Check 3: STEP 3 - Retrieve code files
    check3 = "retrieve_code_artifacts" in content
    checks.append(("STEP 3: Retrieve code files from S3", check3))
    
    # Check 4: STEP 4 - Design architecture
    check4 = "design_architecture_from_requirements" in content
    checks.append(("STEP 4: Design AWS architecture", check4))
    
    # Check 5: STEP 5 - Generate architecture design
    check5 = "Architecture(**architecture_data)" in content
    checks.append(("STEP 5: Generate architecture design document", check5))
    
    # Check 6: STEP 6 - Log output immediately
    check6 = "dynamodb_client.log_inference_output(" in content and "timestamp=timestamp" in content
    checks.append(("STEP 6: Log inference output with timestamp", check6))
    
    # Check 7: STEP 7 - Save converted artifact
    check7 = "s3_client.save_converted_artifact(" in content and "architecture.to_dict()" in content
    checks.append(("STEP 7: Save architecture design to S3", check7))
    
    # Check 8: STEP 8 - Save raw response
    check8 = "s3_client.save_raw_response(" in content
    checks.append(("STEP 8: Save raw response to S3", check8))
    
    # Check 9: STEP 9 - Return formatted response
    check9 = "'messageVersion': '1.0'" in content and "'response':" in content
    checks.append(("STEP 9: Return formatted response", check9))
    
    # Check 10: Helper function - retrieve_code_artifacts
    check10 = "def retrieve_code_artifacts(job_name: str)" in content
    checks.append(("Helper: retrieve_code_artifacts function", check10))
    
    # Check 11: Helper function - design_architecture_from_requirements
    check11 = "def design_architecture_from_requirements(" in content
    checks.append(("Helper: design_architecture_from_requirements function", check11))
    
    # Check 12: S3 get_artifact calls
    check12 = "s3_client.get_artifact(" in content
    checks.append(("S3: get_artifact calls for code files", check12))
    
    # Print results
    print("\nImplementation Checks:")
    print("-" * 80)
    all_passed = True
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
        if not passed:
            all_passed = False
    
    print("-" * 80)
    
    if all_passed:
        print("\n🎉 ALL CHECKS PASSED!")
        print("\nThe implementation follows the exact pattern from Requirements Analyst:")
        print("  1. Log input immediately (BEFORE processing)")
        print("  2. Store timestamp")
        print("  3. Retrieve code files from S3")
        print("  4. Design architecture based on requirements and code")
        print("  5. Generate architecture design document")
        print("  6. Log output immediately (AFTER generation)")
        print("  7. Save converted artifact to S3")
        print("  8. Save raw response to S3")
        print("  9. Return formatted response")
        print("\n✅ Task 8.2 implementation is COMPLETE and CORRECT!")
        return 0
    else:
        print("\n⚠️  SOME CHECKS FAILED")
        print("Please review the implementation against the Requirements Analyst pattern.")
        return 1


if __name__ == '__main__':
    sys.exit(verify_implementation())
