#!/bin/bash
# Quick script to update the BedrockModel parameter in deployed stacks

set -e

REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-default}"
ENVIRONMENT="${ENVIRONMENT:-production}"
NEW_MODEL="us.amazon.nova-premier-v1:0"

echo "Updating BedrockModel parameter to: $NEW_MODEL"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Update collaborators stack
COLLAB_STACK="autoninja-collaborators-${ENVIRONMENT}"
echo "Updating $COLLAB_STACK..."
aws cloudformation update-stack \
    --stack-name "$COLLAB_STACK" \
    --use-previous-template \
    --parameters ParameterKey=BedrockModel,ParameterValue="$NEW_MODEL" \
                 ParameterKey=Environment,UsePreviousValue=true \
                 ParameterKey=DeploymentBucket,UsePreviousValue=true \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --profile "$PROFILE" 2>&1 || echo "No changes needed for $COLLAB_STACK"

echo ""
echo "Stack update initiated. Monitor progress:"
echo "  aws cloudformation wait stack-update-complete --stack-name $COLLAB_STACK --region $REGION --profile $PROFILE"
