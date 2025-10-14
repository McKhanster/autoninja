# AWS Bedrock Agent OpenAPI Schema Constraints

**Quick Reference Guide** - Last Updated: 2025-10-14

## TL;DR

- ✅ Use `ApiSchema.Payload` with inline YAML in CloudFormation
- ❌ Don't use `ApiSchema.S3` - it doesn't work reliably
- ❌ Don't use `additionalProperties`, `$ref`, `enum` arrays, or `components`
- ✅ Keep schemas simple, flat, and use JSON strings for complex data

## The Problem

AWS Bedrock Agents have undocumented limitations on OpenAPI schema format that cause cryptic "Failed to create OpenAPI 3 model" errors during deployment. Standard OpenAPI 3.0 features don't work.

## Unsupported Features

### ❌ S3 Schema References

**Don't use:**
```yaml
ApiSchema:
  S3:
    S3BucketName: !Ref MyBucket
    S3ObjectKey: schemas/my-schema.yaml
```

**Error:** "Failed to create OpenAPI 3 model from the JSON/YAML object"

**Use instead:**
```yaml
ApiSchema:
  Payload: |
    openapi: 3.0.0
    info:
      title: My API
      version: 1.0.0
    paths:
      /my-action:
        post:
          operationId: myAction
          # ... inline schema
```

### ❌ additionalProperties

**Don't use:**
```yaml
properties:
  metadata:
    type: object
    additionalProperties:
      type: string
```

**Use instead:**
```yaml
properties:
  metadata:
    type: string
    description: JSON string containing metadata key-value pairs
```

### ❌ $ref and components

**Don't use:**
```yaml
responses:
  '400':
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/Error'

components:
  schemas:
    Error:
      type: object
      properties:
        message:
          type: string
```

**Use instead:**
```yaml
responses:
  '400':
    description: Invalid request
  '500':
    description: Internal error
```

### ❌ enum arrays

**Don't use:**
```yaml
properties:
  status:
    type: string
    enum: [success, error, pending]
```

**Use instead:**
```yaml
properties:
  status:
    type: string
    description: Status of operation (success, error, or pending)
```

## Minimal Working Template

```yaml
openapi: 3.0.0
info:
  title: Example API
  version: 1.0.0

paths:
  /process-data:
    post:
      summary: Process data
      description: Processes input and returns result
      operationId: processData
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_name
                - input
              properties:
                job_name:
                  type: string
                  description: Unique job identifier
                input:
                  type: string
                  description: Input data as JSON string
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_name:
                    type: string
                  result:
                    type: string
                  status:
                    type: string
        '400':
          description: Invalid request
        '500':
          description: Internal error
```

## Testing Workflow

### 1. Validate Locally
```bash
pip install openapi-spec-validator
python3 << 'EOF'
from openapi_spec_validator import validate_spec
import yaml

with open('schema.yaml', 'r') as f:
    spec = yaml.safe_load(f)
    validate_spec(spec)
    print("✅ Valid OpenAPI 3.0")
EOF
```

### 2. Test with AWS CLI
```bash
# Faster than CloudFormation for iteration
aws bedrock-agent create-agent-action-group \
  --agent-id <AGENT_ID> \
  --agent-version DRAFT \
  --action-group-name test-actions \
  --action-group-executor lambda=<LAMBDA_ARN> \
  --api-schema payload="$(cat schema.yaml)" \
  --region us-east-2
```

### 3. Check for Errors
```bash
# If it fails, check CloudWatch Logs
aws logs tail /aws/bedrock/agents/<agent-name> --follow
```

### 4. Deploy via CloudFormation
```yaml
ActionGroups:
  - ActionGroupName: my-actions
    ActionGroupState: ENABLED
    ActionGroupExecutor:
      Lambda: !GetAtt MyFunction.Arn
    Description: My action group
    ApiSchema:
      Payload: |
        openapi: 3.0.0
        # ... your validated schema
```

## Common Patterns

### Pattern: Dynamic Key-Value Data
```yaml
# Instead of additionalProperties, use JSON string
properties:
  config:
    type: string
    description: JSON string containing configuration key-value pairs
```

**Lambda Response:**
```python
return {
    "config": json.dumps({"key1": "value1", "key2": "value2"})
}
```

### Pattern: Multiple Actions
```yaml
paths:
  /action-one:
    post:
      operationId: actionOne
      # ... schema
  
  /action-two:
    post:
      operationId: actionTwo
      # ... schema
  
  /action-three:
    post:
      operationId: actionThree
      # ... schema
```

### Pattern: Optional Parameters
```yaml
properties:
  required_param:
    type: string
    description: This parameter is required
  optional_param:
    type: string
    description: This parameter is optional

required:
  - required_param
```

## Troubleshooting

### Error: "Failed to create OpenAPI 3 model"

**Causes:**
1. Using S3 reference instead of inline Payload
2. Using `additionalProperties`
3. Using `$ref` or `components`
4. Using `enum` arrays
5. Complex nested objects

**Solution:**
- Simplify schema to minimal working template
- Add features one at a time
- Test after each addition

### Error: "ActionGroup cannot be deleted when Enabled"

**Solution:**
```bash
# Disable first, then delete
aws bedrock-agent update-agent-action-group \
  --agent-id <ID> \
  --agent-version DRAFT \
  --action-group-id <ACTION_GROUP_ID> \
  --action-group-name <NAME> \
  --action-group-state DISABLED \
  --region us-east-2

aws bedrock-agent delete-agent-action-group \
  --agent-id <ID> \
  --agent-version DRAFT \
  --action-group-id <ACTION_GROUP_ID> \
  --region us-east-2
```

## Best Practices

1. **Start minimal** - Single endpoint, basic types
2. **Test incrementally** - Add one feature at a time
3. **Use JSON strings** - For any complex or dynamic data
4. **Inline everything** - No external references
5. **Keep it flat** - Avoid deep nesting
6. **Document thoroughly** - Descriptions help the agent understand

## References

- [AWS Bedrock Agent OpenAPI Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-api-schema.html)
- [CloudFormation APISchema Property](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-bedrock-agent-apischema.html)
- [OpenAPI 3.0 Specification](https://swagger.io/specification/)

## Version History

- **2025-10-14**: Initial documentation based on Task 5 implementation
  - Discovered S3 references don't work
  - Documented all unsupported features
  - Created minimal working templates
