#!/bin/bash
set -e

###############################################################################
# Update Bedrock Agent Foundation Models
#
# This script updates all collaborator agents to use the correct inference
# profile ID (us.anthropic.claude-3-7-sonnet-20250219-v1:0) instead of the
# foundation model ID (anthropic.claude-3-7-sonnet-20250219-v1:0).
#
# Process:
# 1. Get current agent configuration (to preserve instructions, action groups)
# 2. Update each agent with new foundation model
# 3. Prepare agents (creates version 2)
# 4. Update aliases to point to version 2
###############################################################################

REGION=${AWS_REGION:-us-east-2}
PROFILE=${AWS_PROFILE:-AdministratorAccess-784327326356}
NEW_MODEL="us.anthropic.claude-3-7-sonnet-20250219-v1:0"

echo "=========================================="
echo "Updating Collaborator Agent Models"
echo "=========================================="
echo "Region: $REGION"
echo "Profile: $PROFILE"
echo "New Model: $NEW_MODEL"
echo ""

# Agent configurations
declare -A AGENTS=(
    ["COIRVWOLUP"]="requirements-analyst:4DQZMU4IJ4"
    ["WPEDLIJE2K"]="code-generator:NLKOI3URQC"
    ["8BSQ59K3RO"]="solution-architect:BVTCJTDYRK"
    ["I0E1LEIHEE"]="quality-validator:X8IWGQ9NLC"
    ["NVPH3RIYGD"]="deployment-manager:DL7YM7QETY"
)

# Step 1: Get current configurations
echo "Step 1: Backing up current agent configurations..."
mkdir -p /tmp/agent-backups
for AGENT_ID in "${!AGENTS[@]}"; do
    IFS=':' read -r NAME ALIAS_ID <<< "${AGENTS[$AGENT_ID]}"
    echo "  - Backing up $NAME ($AGENT_ID)..."
    aws bedrock-agent get-agent \
        --agent-id "$AGENT_ID" \
        --region "$REGION" \
        --profile "$PROFILE" \
        > "/tmp/agent-backups/${NAME}-config.json"
done
echo "✓ Backups saved to /tmp/agent-backups/"
echo ""

# Step 2: Update each agent with new foundation model
echo "Step 2: Updating agents with new foundation model..."
for AGENT_ID in "${!AGENTS[@]}"; do
    IFS=':' read -r NAME ALIAS_ID <<< "${AGENTS[$AGENT_ID]}"
    echo "  - Updating $NAME ($AGENT_ID)..."

    # Get current agent properties from backup
    ROLE_ARN=$(jq -r '.agent.agentResourceRoleArn' "/tmp/agent-backups/${NAME}-config.json")
    INSTRUCTION=$(jq -r '.agent.instruction' "/tmp/agent-backups/${NAME}-config.json")
    DESCRIPTION=$(jq -r '.agent.description // ""' "/tmp/agent-backups/${NAME}-config.json")
    AGENT_NAME=$(jq -r '.agent.agentName' "/tmp/agent-backups/${NAME}-config.json")
    IDLE_TTL=$(jq -r '.agent.idleSessionTTLInSeconds // 1800' "/tmp/agent-backups/${NAME}-config.json")

    # Build update command with all preserved properties
    UPDATE_CMD="aws bedrock-agent update-agent \
        --agent-id \"$AGENT_ID\" \
        --agent-name \"$AGENT_NAME\" \
        --foundation-model \"$NEW_MODEL\" \
        --agent-resource-role-arn \"$ROLE_ARN\" \
        --instruction \"$INSTRUCTION\" \
        --idle-session-ttl-in-seconds $IDLE_TTL \
        --region \"$REGION\" \
        --profile \"$PROFILE\""

    # Add description if it exists
    if [ -n "$DESCRIPTION" ] && [ "$DESCRIPTION" != "null" ]; then
        UPDATE_CMD="$UPDATE_CMD --description \"$DESCRIPTION\""
    fi

    # Execute the update
    eval "$UPDATE_CMD > /dev/null"

    echo "    ✓ Updated (preserved description, TTL, and all settings)"
done
echo ""

# Step 3: Prepare agents (creates version 2)
echo "Step 3: Preparing agents (creating version 2)..."
for AGENT_ID in "${!AGENTS[@]}"; do
    IFS=':' read -r NAME ALIAS_ID <<< "${AGENTS[$AGENT_ID]}"
    echo "  - Preparing $NAME ($AGENT_ID)..."

    PREPARE_OUTPUT=$(aws bedrock-agent prepare-agent \
        --agent-id "$AGENT_ID" \
        --region "$REGION" \
        --profile "$PROFILE" 2>&1)

    # Extract agent status
    STATUS=$(echo "$PREPARE_OUTPUT" | grep -o '"agentStatus": "[^"]*"' | cut -d'"' -f4 || echo "UNKNOWN")
    echo "    ✓ Prepared (Status: $STATUS)"

    # Wait for preparation to complete
    echo "    Waiting for preparation to complete..."
    for i in {1..30}; do
        AGENT_STATUS=$(aws bedrock-agent get-agent \
            --agent-id "$AGENT_ID" \
            --region "$REGION" \
            --profile "$PROFILE" \
            --query 'agent.agentStatus' \
            --output text)

        if [ "$AGENT_STATUS" = "PREPARED" ] || [ "$AGENT_STATUS" = "NOT_PREPARED" ]; then
            echo "    ✓ Preparation complete (Status: $AGENT_STATUS)"
            break
        fi

        echo "    Waiting... (Status: $AGENT_STATUS)"
        sleep 2
    done
done
echo ""

# Step 4: Get the latest version number and update aliases
echo "Step 4: Updating aliases to point to latest version..."
for AGENT_ID in "${!AGENTS[@]}"; do
    IFS=':' read -r NAME ALIAS_ID <<< "${AGENTS[$AGENT_ID]}"
    echo "  - Updating $NAME alias ($ALIAS_ID)..."

    # Get the latest prepared version
    LATEST_VERSION=$(aws bedrock-agent list-agent-versions \
        --agent-id "$AGENT_ID" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'agentVersionSummaries[?agentStatus==`PREPARED`] | [0].agentVersion' \
        --output text)

    if [ "$LATEST_VERSION" = "None" ] || [ -z "$LATEST_VERSION" ]; then
        echo "    ✗ No PREPARED version found, skipping alias update"
        continue
    fi

    echo "    Latest PREPARED version: $LATEST_VERSION"

    aws bedrock-agent update-agent-alias \
        --agent-id "$AGENT_ID" \
        --agent-alias-id "$ALIAS_ID" \
        --agent-alias-name production \
        --routing-configuration "agentVersion=$LATEST_VERSION" \
        --region "$REGION" \
        --profile "$PROFILE" \
        > /dev/null

    echo "    ✓ Alias updated to version $LATEST_VERSION"
done
echo ""

# Step 5: Verify updates
echo "=========================================="
echo "Verification"
echo "=========================================="
for AGENT_ID in "${!AGENTS[@]}"; do
    IFS=':' read -r NAME ALIAS_ID <<< "${AGENTS[$AGENT_ID]}"

    echo "$NAME ($AGENT_ID):"

    # Get agent details
    AGENT_MODEL=$(aws bedrock-agent get-agent \
        --agent-id "$AGENT_ID" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'agent.foundationModel' \
        --output text)

    # Get alias details
    ALIAS_VERSION=$(aws bedrock-agent get-agent-alias \
        --agent-id "$AGENT_ID" \
        --agent-alias-id "$ALIAS_ID" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --query 'agentAlias.routingConfiguration[0].agentVersion' \
        --output text)

    echo "  Model: $AGENT_MODEL"
    echo "  Alias Version: $ALIAS_VERSION"

    if [ "$AGENT_MODEL" = "$NEW_MODEL" ]; then
        echo "  ✓ Model updated correctly"
    else
        echo "  ✗ Model NOT updated (expected: $NEW_MODEL)"
    fi
    echo ""
done

echo "=========================================="
echo "✓ All agents updated successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test the supervisor agent: python tests/supervisor/test_supervisor.py"
echo "2. Check CloudWatch logs for any errors"
echo ""
