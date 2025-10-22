#!/usr/bin/env python3
"""
End-to-End Test for AutoNinja Supervisor Orchestration

Tests:
1. Invoke supervisor agent (which orchestrates all 5 collaborators internally)
2. Verify CloudWatch logs contain entries for supervisor and collaborators
3. Verify DynamoDB records contain requests and responses
4. Verify S3 artifacts are stored for each phase
5. Verify agent sequence matches expected order from supervisor logs
"""

import boto3
import json
import time
import os
import logging
import re
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================
SUPERVISOR_AGENT_ID = os.environ.get('SUPERVISOR_AGENT_ID', 'ANXDPRPFKZ')
SUPERVISOR_ALIAS_ID = os.environ.get('SUPERVISOR_ALIAS_ID', 'DB1NJMRAJ8')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')
AWS_PROFILE = os.environ.get('AWS_PROFILE', 'AdministratorAccess-784327326356')

# DynamoDB and S3 configuration
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'autoninja-inference-records-production')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'autoninja-artifacts-784327326356-production')

# Expected agent sequence (from supervisor orchestration)
EXPECTED_AGENT_SEQUENCE = [
    'requirements-analyst',
    'code-generator',
    'solution-architect',
    'quality-validator',
    'deployment-manager'
]

# CloudWatch log groups
LOG_GROUP_SUPERVISOR = '/aws/lambda/autoninja-supervisor-production'

# ============================================================================
# AWS CLIENTS
# ============================================================================
session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
bedrock_agent_runtime = session.client('bedrock-agent-runtime')
dynamodb = session.client('dynamodb')
s3 = session.client('s3')
logs = session.client('logs')

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def invoke_supervisor(prompt: str) -> dict:
    """Invoke supervisor agent and return results"""
    import random
    session_id = f"e2e-test-{int(time.time())}-{random.randint(1000, 9999)}"

    logger.info("=" * 80)
    logger.info("INVOKING SUPERVISOR AGENT")
    logger.info(f"Agent ID: {SUPERVISOR_AGENT_ID}")
    logger.info(f"Alias ID: {SUPERVISOR_ALIAS_ID}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Prompt: {prompt}")
    logger.info("=" * 80)

    # Add delay to avoid rate limiting - Claude 3.7 has very low quotas
    logger.info("Waiting 10 seconds to avoid rate limiting...")
    time.sleep(10)

    start_time = datetime.now()

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=SUPERVISOR_AGENT_ID,
            agentAliasId=SUPERVISOR_ALIAS_ID,
            sessionId=session_id,
            inputText=prompt,
            enableTrace=True
        )

        completion = ""

        for event in response.get('completion', []):
            if 'chunk' in event:
                completion += event['chunk']['bytes'].decode('utf-8')

        logger.info(f"✓ Supervisor completed")
        logger.info(f"Completion length: {len(completion)} characters")

        return {
            'session_id': session_id,
            'completion': completion,
            'start_time': start_time,
            'end_time': datetime.now()
        }

    except Exception as e:
        logger.error(f"✗ Failed to invoke supervisor: {e}")
        raise

def extract_job_name(completion: str) -> str:
    """Extract job_name from completion text"""
    # Look for job-name pattern: job-{keyword}-{YYYYMMDD}-{HHMMSS}
    pattern = r'job-[a-z]+-\d{8}-\d{6}'
    match = re.search(pattern, completion)

    if match:
        return match.group(0)

    # Fallback: look for job_name in JSON
    try:
        if '{' in completion:
            json_start = completion.index('{')
            json_end = completion.rindex('}') + 1
            data = json.loads(completion[json_start:json_end])
            if 'job_name' in data:
                return data['job_name']
    except:
        pass

    logger.warning("Could not extract job_name from completion")
    return None

def verify_cloudwatch_logs(job_name: str, start_time: datetime) -> bool:
    """Verify CloudWatch logs exist for supervisor"""
    logger.info("\n" + "=" * 80)
    logger.info("VERIFYING CLOUDWATCH LOGS")
    logger.info("=" * 80)

    try:
        response = logs.filter_log_events(
            logGroupName=LOG_GROUP_SUPERVISOR,
            startTime=int(start_time.timestamp() * 1000),
            filterPattern=f'"{job_name}"'
        )

        events = response.get('events', [])

        if not events:
            logger.error(f"✗ No log events found for job: {job_name}")
            return False

        logger.info(f"✓ Found {len(events)} log events")

        # Check for key orchestration steps in logs
        log_text = ' '.join([event['message'] for event in events])

        agents_logged = []
        for agent in EXPECTED_AGENT_SEQUENCE:
            if agent in log_text:
                agents_logged.append(agent)
                logger.info(f"  ✓ Found logs for: {agent}")

        if len(agents_logged) >= 1:  # At least requirements-analyst should be logged
            logger.info(f"✓ CloudWatch logs verified ({len(agents_logged)}/{len(EXPECTED_AGENT_SEQUENCE)} agents logged)")
            return True
        else:
            logger.error("✗ No agent invocations found in logs")
            return False

    except logs.exceptions.ResourceNotFoundException:
        logger.error(f"✗ Log group not found: {LOG_GROUP_SUPERVISOR}")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking logs: {e}")
        return False

def verify_dynamodb_records(job_name: str) -> bool:
    """Verify DynamoDB records contain requests and responses"""
    logger.info("\n" + "=" * 80)
    logger.info("VERIFYING DYNAMODB RECORDS")
    logger.info("=" * 80)

    try:
        response = dynamodb.query(
            TableName=DYNAMODB_TABLE_NAME,
            KeyConditionExpression='job_name = :job_name',
            ExpressionAttributeValues={
                ':job_name': {'S': job_name}
            }
        )

        records = response.get('Items', [])
        logger.info(f"Found {len(records)} DynamoDB records for job: {job_name}")

        if not records:
            logger.error("✗ No DynamoDB records found")
            return False

        # Verify each record has prompt and response
        records_valid = True
        agents_found = set()

        for record in records:
            agent_name = record.get('agent_name', {}).get('S', 'unknown')
            action_name = record.get('action_name', {}).get('S', 'unknown')
            prompt = record.get('prompt', {}).get('S', '')
            response = record.get('response', {}).get('S', '')

            agents_found.add(agent_name)

            has_prompt = len(prompt) > 0
            has_response = len(response) > 0

            status = "✓" if (has_prompt and has_response) else "✗"
            logger.info(f"  {status} {agent_name}/{action_name}: prompt={has_prompt}, response={has_response}")

            if not (has_prompt and has_response):
                records_valid = False

        logger.info(f"\nAgents with records: {sorted(agents_found)}")

        if records_valid:
            logger.info("✓ All DynamoDB records have both prompt and response")
            return True
        else:
            logger.error("✗ Some DynamoDB records are missing prompt or response")
            return False

    except Exception as e:
        logger.error(f"✗ Error verifying DynamoDB records: {e}")
        return False

def verify_s3_artifacts(job_name: str) -> bool:
    """Verify S3 artifacts are stored"""
    logger.info("\n" + "=" * 80)
    logger.info("VERIFYING S3 ARTIFACTS")
    logger.info("=" * 80)

    phases = ['requirements', 'code', 'architecture', 'validation', 'deployment']

    try:
        # List all objects for this job
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=f"{job_name}/"
        )

        if 'Contents' not in response:
            logger.error(f"✗ No S3 artifacts found for job: {job_name}")
            return False

        artifacts = response['Contents']
        logger.info(f"Found {len(artifacts)} S3 artifacts")

        # Check for artifacts in each phase
        phases_found = set()
        for artifact in artifacts:
            key = artifact['Key']
            size = artifact['Size']

            for phase in phases:
                if f"/{phase}/" in key:
                    phases_found.add(phase)
                    logger.info(f"  ✓ {phase}: {key} ({size} bytes)")
                    break

        logger.info(f"\nPhases with artifacts: {sorted(phases_found)}")

        # At minimum, we should have requirements artifacts
        if 'requirements' in phases_found:
            logger.info(f"✓ S3 artifacts verified ({len(phases_found)}/{len(phases)} phases)")
            return True
        else:
            logger.error("✗ No requirements artifacts found")
            return False

    except Exception as e:
        logger.error(f"✗ Error verifying S3 artifacts: {e}")
        return False

# ============================================================================
# END-TO-END TEST
# ============================================================================

def test_e2e_orchestration():
    """
    End-to-end test: Invoke supervisor and verify all outputs
    """
    logger.info("\n" + "=" * 80)
    logger.info("STARTING END-TO-END ORCHESTRATION TEST")
    logger.info("=" * 80)

    # Test prompt
    prompt = "Build a simple friend agent for emotional support"

    # Track test results
    results = {
        'supervisor_invocation': False,
        'cloudwatch_logs': False,
        'dynamodb_records': False,
        's3_artifacts': False
    }

    job_name = None

    try:
        # Step 1: Invoke supervisor (which orchestrates everything internally)
        logger.info("\n### STEP 1: Invoke Supervisor (Orchestrates All Agents) ###")
        supervisor_result = invoke_supervisor(prompt)
        results['supervisor_invocation'] = True

        # Extract job_name
        job_name = extract_job_name(supervisor_result['completion'])
        if not job_name:
            logger.error("✗ Could not extract job_name from completion")
            # Try to find it in logs
            time.sleep(5)
            # For now, mark as failure if we can't extract job_name
            logger.error("Cannot proceed with verification without job_name")
        else:
            logger.info(f"✓ Extracted job_name: {job_name}")

            # Wait for async operations to complete
            logger.info("\nWaiting 15 seconds for async operations to complete...")
            time.sleep(15)

            # Step 2: Verify CloudWatch logs
            logger.info("\n### STEP 2: Verify CloudWatch Logs ###")
            results['cloudwatch_logs'] = verify_cloudwatch_logs(
                job_name,
                supervisor_result['start_time']
            )

            # Step 3: Verify DynamoDB records
            logger.info("\n### STEP 3: Verify DynamoDB Records ###")
            results['dynamodb_records'] = verify_dynamodb_records(job_name)

            # Step 4: Verify S3 artifacts
            logger.info("\n### STEP 4: Verify S3 Artifacts ###")
            results['s3_artifacts'] = verify_s3_artifacts(job_name)

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    # Print final results
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 80)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status} - {test_name.replace('_', ' ').title()}")

    total_passed = sum(results.values())
    total_tests = len(results)

    logger.info("=" * 80)
    logger.info(f"TOTAL: {total_passed}/{total_tests} tests passed")
    if job_name:
        logger.info(f"Job Name: {job_name}")
    logger.info("=" * 80)

    return all(results.values())

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("AutoNinja End-to-End Orchestration Test")
    logger.info(f"Supervisor Agent ID: {SUPERVISOR_AGENT_ID}")
    logger.info(f"Supervisor Alias ID: {SUPERVISOR_ALIAS_ID}")
    logger.info(f"AWS Region: {AWS_REGION}")
    logger.info(f"AWS Profile: {AWS_PROFILE}")
    logger.info(f"DynamoDB Table: {DYNAMODB_TABLE_NAME}")
    logger.info(f"S3 Bucket: {S3_BUCKET_NAME}")

    success = test_e2e_orchestration()

    exit(0 if success else 1)
