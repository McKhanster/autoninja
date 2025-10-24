#!/usr/bin/env python3
"""Check if Nova Premier is accessible in Bedrock."""

import boto3
import json

def check_nova_access():
    bedrock = boto3.client('bedrock', region_name='us-east-1')
    
    try:
        # List all foundation models
        response = bedrock.list_foundation_models()
        
        # Filter for Nova models
        nova_models = [
            model for model in response['modelSummaries']
            if 'nova' in model['modelId'].lower()
        ]
        
        print("Available Nova Models:")
        print("=" * 80)
        for model in nova_models:
            print(f"\nModel ID: {model['modelId']}")
            print(f"  Name: {model.get('modelName', 'N/A')}")
            print(f"  Provider: {model.get('providerName', 'N/A')}")
            print(f"  Input Modalities: {', '.join(model.get('inputModalities', []))}")
            print(f"  Output Modalities: {', '.join(model.get('outputModalities', []))}")
            
        # Check inference profiles
        print("\n" + "=" * 80)
        print("Checking Inference Profiles...")
        print("=" * 80)
        
        # Try to get model info for Nova Premier
        try:
            model_info = bedrock.get_foundation_model(
                modelIdentifier='us.amazon.nova-premier-v1:0'
            )
            print("\n✓ Nova Premier inference profile is accessible!")
            print(f"  Model ARN: {model_info['modelDetails'].get('modelArn', 'N/A')}")
        except Exception as e:
            print(f"\n✗ Nova Premier inference profile error: {e}")
            
    except Exception as e:
        print(f"Error checking models: {e}")

if __name__ == "__main__":
    check_nova_access()
