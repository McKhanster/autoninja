#!/bin/bash
# Configure Custom Orchestration for all 5 sub-agents
# Run this after CloudFormation deployment completes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-AdministratorAccess-784327326356}"
ENVIRONMENT="${ENVIRONMENT:-production}"
STACK_NAME="autoninja-${ENVIRONMENT}"

echo -e "${YELLOW}Configuring Custom Orchestration for Bedrock Agents${NC}"
echo ""

# Get Custom Orchestration Lambda ARN
CUSTOM_ORCH_ARN=$(aws lambda get-function \
    --function-name "autoninja-custom-orchestration-${ENVIRONMENT}" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Configuration.FunctionArn' \
    --output text)

echo "Custom Orchestration Lambda ARN: $CUSTOM_ORCH_ARN"
echo ""

# Get agent IDs from stack outputs
echo "Retrieving agent IDs from CloudFormation stack..."
REQ_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`RequirementsAnalystAgentId`].OutputValue' \
    --output text)

CODE_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`CodeGeneratorAgentId`].OutputValue' \
    --output text)

ARCH_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`SolutionArchitectAgentId`].OutputValue' \
    --output text)

QV_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`QualityValidatorAgentId`].OutputValue' \
    --output text)

DM_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --query 'Stacks[0].Outputs[?OutputKey==`DeploymentManagerAgentId`].OutputValue' \
    --output text)

echo "Agent IDs retrieved"
echo ""

# Configure each agent with custom orchestration using AWS Bedrock API
AGENTS_TO_CONFIGURE=(
    "requirements-analyst:$REQ_AGENT_ID"
    "code-generator:$CODE_AGENT_ID"
    "solution-architect:$ARCH_AGENT_ID"
    "quality-validator:$QV_AGENT_ID"
    "deployment-manager:$DM_AGENT_ID"
)

for agent_info in "${AGENTS_TO_CONFIGURE[@]}"; do
    agent_name="${agent_info%%:*}"
    agent_id="${agent_info##*:}"

    echo -e "${YELLOW}Configuring $agent_name (ID: $agent_id)...${NC}"

    # Get current agent configuration
    agent_config=$(aws bedrock-agent get-agent \
        --agent-id "$agent_id" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --output json)

    # Extract required fields
    agent_full_name=$(echo "$agent_config" | jq -r '.agent.agentName')
    agent_role_arn=$(echo "$agent_config" | jq -r '.agent.agentResourceRoleArn')
    foundation_model=$(echo "$agent_config" | jq -r '.agent.foundationModel')

    # Update agent with custom orchestration (using correct AWS CLI syntax)
    update_result=$(aws bedrock-agent update-agent \
        --agent-id "$agent_id" \
        --agent-name "$agent_full_name" \
        --agent-resource-role-arn "$agent_role_arn" \
        --foundation-model "$foundation_model" \
        --orchestration-type CUSTOM_ORCHESTRATION \
        --custom-orchestration "executor={lambda=${CUSTOM_ORCH_ARN}}" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --output json 2>&1)

    if [ $? -eq 0 ]; then
        echo "  Preparing agent..."
        # Prepare agent to apply changes
        aws bedrock-agent prepare-agent \
            --agent-id "$agent_id" \
            --region "$REGION" \
            --profile "$PROFILE" \
            --output json > /dev/null 2>&1

        echo -e "  ${GREEN}✓${NC} $agent_name configured successfully"
    else
        echo -e "  ${RED}✗${NC} Failed to configure $agent_name"
        echo "  Error: $update_result"
    fi
    echo ""
done

echo -e "${GREEN}Configuration complete!${NC}"
echo ""
echo "Verifying configuration..."
echo ""

# Verify each agent
for agent_info in "${AGENTS_TO_CONFIGURE[@]}"; do
    agent_name="${agent_info%%:*}"
    agent_id="${agent_info##*:}"

    orch_type=$(aws bedrock-agent get-agent \
        --agent-id "$agent_id" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'agent.orchestrationType' \
        --output text)

    if [ "$orch_type" == "CUSTOM_ORCHESTRATION" ]; then
        echo -e "  ${GREEN}✓${NC} $agent_name: CUSTOM_ORCHESTRATION"
    else
        echo -e "  ${RED}✗${NC} $agent_name: $orch_type (expected CUSTOM_ORCHESTRATION)"
    fi
done

echo ""
echo -e "${GREEN}Done!${NC}"
