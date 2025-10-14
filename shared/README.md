# AutoNinja Shared Libraries

This directory contains shared code used across all AutoNinja Lambda functions, packaged as a Lambda Layer.

## Structure

```
shared/
├── persistence/          # DynamoDB and S3 client wrappers
│   ├── dynamodb_client.py
│   └── s3_client.py
├── utils/               # Utility modules
│   ├── job_generator.py
│   └── logger.py
├── requirements.txt     # Python dependencies
└── README.md
```

## Modules

### Persistence Layer

#### DynamoDBClient

Provides methods for logging inference records to DynamoDB:

```python
from shared.persistence import DynamoDBClient

client = DynamoDBClient()

# Log inference input
client.log_inference_input(
    job_name="job-friend-20251013-143022",
    session_id="session-123",
    agent_name="requirements-analyst",
    action_name="extract_requirements",
    prompt="Full raw prompt..."
)

# Log inference output
client.log_inference_output(
    job_name="job-friend-20251013-143022",
    timestamp="2025-10-13T14:30:22.123Z",
    response="Full raw response...",
    tokens_used=4532,
    cost_estimate=0.0226,
    duration_seconds=3.24
)

# Query records
records = client.query_by_job_name("job-friend-20251013-143022")
```

#### S3Client

Provides methods for saving and retrieving artifacts from S3:

```python
from shared.persistence import S3Client

client = S3Client()

# Save raw response
s3_uri = client.save_raw_response(
    job_name="job-friend-20251013-143022",
    phase="requirements",
    agent_name="requirements-analyst",
    response={"requirements": [...]}
)

# Save converted artifact
s3_uri = client.save_converted_artifact(
    job_name="job-friend-20251013-143022",
    phase="requirements",
    agent_name="requirements-analyst",
    artifact=requirements_dict,
    filename="requirements.json"
)

# Get artifact
artifact = client.get_artifact(
    job_name="job-friend-20251013-143022",
    phase="requirements",
    agent_name="requirements-analyst",
    filename="requirements.json"
)
```

### Utilities

#### Job Generator

Generates unique job identifiers:

```python
from shared.utils import generate_job_name

job_name = generate_job_name("I would like a friend agent")
# Returns: "job-friend-20251013-143022"
```

#### Structured Logger

Provides JSON-formatted logging with consistent fields:

```python
from shared.utils import get_logger

logger = get_logger(
    __name__,
    job_name="job-friend-20251013-143022",
    agent_name="requirements-analyst",
    action_name="extract_requirements"
)

logger.info("Processing request", user_id="user-123")
# Outputs JSON: {"timestamp": "...", "level": "INFO", "message": "Processing request", 
#                "job_name": "job-friend-20251013-143022", "user_id": "user-123"}
```

## Packaging as Lambda Layer

To package the shared libraries as a Lambda Layer:

```bash
# Package the layer
./scripts/package_lambda_layer.sh

# Upload to S3 (optional)
S3_BUCKET=your-bucket-name ./scripts/package_lambda_layer.sh
```

This creates a ZIP file at `build/autoninja-shared-layer.zip` that can be deployed as a Lambda Layer.

## Usage in Lambda Functions

Lambda functions can import from the shared libraries:

```python
# In Lambda function code
from shared.persistence import DynamoDBClient, S3Client
from shared.utils import get_logger, generate_job_name

def lambda_handler(event, context):
    logger = get_logger(__name__)
    db_client = DynamoDBClient()
    s3_client = S3Client()
    
    # Use the clients...
```

## Environment Variables

The shared libraries expect these environment variables:

- `DYNAMODB_TABLE_NAME`: DynamoDB table name for inference records
- `S3_BUCKET_NAME`: S3 bucket name for artifacts
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Dependencies

- boto3 >= 1.34.0
- botocore >= 1.34.0

These are included in the Lambda Layer package.
