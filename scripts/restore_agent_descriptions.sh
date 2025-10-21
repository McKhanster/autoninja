#!/bin/bash
set -e

###############################################################################
# Restore Agent Descriptions
# This script restores the descriptions for all collaborator agents
###############################################################################

REGION=${AWS_REGION:-us-east-2}
PROFILE=${AWS_PROFILE:-AdministratorAccess-784327326356}

echo "=========================================="
echo "Restoring Agent Descriptions"
echo "=========================================="

# Agent configurations with descriptions from CloudFormation templates
declare -A AGENT_DESCRIPTIONS=(
    ["COIRVWOLUP"]="Requirements Analyst agent - extracts and validates requirements from user requests"
    ["WPEDLIJE2K"]="Code Generator agent - generates Lambda code, agent configs, and OpenAPI schemas"
    ["8BSQ59K3RO"]="Solution Architect agent - designs AWS architecture and generates infrastructure as code"
    ["I0E1LEIHEE"]="Quality Validator agent - validates code quality, security, and compliance"
    ["NVPH3RIYGD"]="Deployment Manager agent - deploys CloudFormation stacks and configures agents"
)

for AGENT_ID in "${!AGENT_DESCRIPTIONS[@]}"; do
    DESCRIPTION="${AGENT_DESCRIPTIONS[$AGENT_ID]}"

    echo "Restoring description for $AGENT_ID..."
    echo "  Description: $DESCRIPTION"

    # Get current agent configuration
    CURRENT_CONFIG=$(aws bedrock-agent get-agent \
        --agent-id "$AGENT_ID" \
        --region "$REGION" \
        --profile "$PROFILE")

    AGENT_NAME=$(echo "$CURRENT_CONFIG" | jq -r '.agent.agentName')
    ROLE_ARN=$(echo "$CURRENT_CONFIG" | jq -r '.agent.agentResourceRoleArn')
    INSTRUCTION=$(echo "$CURRENT_CONFIG" | jq -r '.agent.instruction')
    FOUNDATION_MODEL=$(echo "$CURRENT_CONFIG" | jq -r '.agent.foundationModel')
    IDLE_TTL=$(echo "$CURRENT_CONFIG" | jq -r '.agent.idleSessionTTLInSeconds // 1800')

    # Update with description
    aws bedrock-agent update-agent \
        --agent-id "$AGENT_ID" \
        --agent-name "$AGENT_NAME" \
        --description "$DESCRIPTION" \
        --foundation-model "$FOUNDATION_MODEL" \
        --agent-resource-role-arn "$ROLE_ARN" \
        --instruction "$INSTRUCTION" \
        --idle-session-ttl-in-seconds $IDLE_TTL \
        --region "$REGION" \
        --profile "$PROFILE" \
        > /dev/null

    echo "  ✓ Description restored"
done

echo ""
echo "=========================================="
echo "✓ All descriptions restored!"
echo "=========================================="
echo ""
echo "You need to prepare the agents again for the descriptions to take effect in version 2:"
echo "./scripts/update_collaborator_models.sh"
