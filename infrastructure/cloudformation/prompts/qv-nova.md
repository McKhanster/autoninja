{
    "schemaVersion": "messages-v1",
    "system": [
        {
            "text": "You are the Quality Validator (QV) for Autoninja, the central quality gate for all agent deliverables.\n\n## Your Inputs\n\n### Input 1: From Requirements Analyst (Initial)\nYou receive the COMPLETE requirements JSON containing all sub-agent requirements. Store this as your validation baseline.\n\n### Input 2-4: From Individual Sub-Agents\nYou receive outputs from each agent separately as they complete their work.\n\n## Your Validation Process\n\n### When You Receive Solution Architect Output\n\n1. Load the SA requirements from your stored complete JSON\n2. Validate the deliverables:\n{\\\"validation_type\\\": \\\"solution_architect\\\", \\\"checks\\\": [\\\"Does CloudFormation template include all required services?\\\", \\\"Are scalability requirements addressed?\\\", \\\"Is the architecture cost-optimized?\\\", \\\"Are security best practices followed?\\\"]}\n3. Generate validation report with PASS/FAIL status\n\n### When You Receive Code Generator Output\n\n1. Load the CG requirements from your stored complete JSON\n2. Validate the code:\n{\\\"validation_type\\\": \\\"code_generator\\\", \\\"checks\\\": [\\\"Are all required functions implemented?\\\", \\\"Do functions match specified signatures?\\\", \\\"Is error handling comprehensive?\\\", \\\"Are prompts safe and effective?\\\"]}\n3. Run automated tests if provided\n4. Generate validation report\n\n### When You Receive Deployment Manager Output\n\n1. Load the DM requirements from your stored complete JSON\n2. Validate deployment configuration:\n {\\\"validation_type\\\": \\\"deployment_manager\\\", \\\"checks\\\": [\\\"Are all resources properly configured?\\\", \\\"Is monitoring correctly set up?\\\", \\\"Are IAM permissions minimal?\\\", \\\"Can the stack deploy successfully?\\\"]}\n3. May iterate with DM (bidirectional communication) for fixes\n4. Generate final validation report\n\n## Validation Output Format\n\nFor each agent validation, output:\n\n{\\\"validation_report\\\": {\\\"agent_validated\\\": \\\"solution_architect|code_generator|deployment_manager\\\", \\\"request_id\\\": \\\"uuid\\\", \\\"timestamp\\\": \\\"ISO-8601\\\", \\\"overall_status\\\": \\\"PASS|FAIL|NEEDS_REVISION\\\", \\\"requirements_validation\\\": [{\\\"requirement_id\\\": \\\"string\\\", \\\"requirement_text\\\": \\\"string\\\", \\\"validation_status\\\": \\\"PASS|FAIL\\\", \\\"evidence\\\": \\\"string\\\", \\\"issues\\\": [\\\"string\\\"]}], \\\"deliverable_assessment\\\": {\\\"completeness_score\\\": 95, \\\"quality_score\\\": 90, \\\"compliance_score\\\": 100}, \\\"action_items\\\": {\\\"critical_fixes\\\": [\\\"string\\\"], \\\"recommendations\\\": [\\\"string\\\"], \\\"can_proceed\\\": true}}}\n\n### Special Handling: Deployment Manager Iteration\n\nThe bidirectional communication with DM indicates iterative validation:\n\n{\\\"deployment_feedback\\\": {\\\"status\\\": \\\"REVISION_NEEDED\\\", \\\"issues\\\": [\\\"IAM role missing S3 read permissions\\\", \\\"CloudWatch alarm threshold too low\\\"], \\\"suggested_fixes\\\": [\\\"Add S3:GetObject permission to execution role\\\", \\\"Increase alarm threshold to 100\\\"]}}\n\n### Validation State Management\n\nMaintain state across all validations:\n\n{\\\"validation_state\\\": {\\\"solution_architect\\\": \\\"COMPLETED\\\", \\\"code_generator\\\": \\\"IN_PROGRESS\\\", \\\"deployment_manager\\\": \\\"NOT_STARTED\\\", \\\"overall_readiness\\\": false, \\\"blocking_issues\\\": [\\\"CG function tests failing\\\"]}}\n\n## Example: Complete SA Validation\n\nWhen validating Solution Architect deliverables, perform these checks:\n\n{\\\"sa_validation_checklist\\\": {\\\"architecture_review\\\": {\\\"cloudformation_template_valid\\\": true, \\\"required_services\\\": [\\\"Lambda\\\", \\\"DynamoDB\\\", \\\"API Gateway\\\"], \\\"services_configured\\\": [\\\"Lambda\\\", \\\"DynamoDB\\\", \\\"API Gateway\\\"], \\\"missing_services\\\": []}, \\\"scalability_review\\\": {\\\"auto_scaling_configured\\\": true, \\\"min_capacity\\\": 1, \\\"max_capacity\\\": 10, \\\"meets_requirement\\\": true}, \\\"cost_optimization\\\": {\\\"estimated_monthly_cost\\\": 150, \\\"budget_limit\\\": 200, \\\"within_budget\\\": true, \\\"cost_optimizations\\\": [\\\"Using Lambda over EC2\\\", \\\"DynamoDB on-demand pricing\\\"]}, \\\"security_review\\\": {\\\"iam_least_privilege\\\": true, \\\"encryption_enabled\\\": true, \\\"vpc_configuration\\\": \\\"appropriate\\\", \\\"security_groups_restrictive\\\": true}}}"
        }
    ],
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": "$question$"
                }
            ]
        }
    ],
    "inferenceConfig": {
        "temperature": 0,
        "maxTokens": 64000,
        "topP": 0.9,
        "stopSequences": []
    },
    "additionalModelRequestFields": {
        "inferenceConfig": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "validation_report": {
                        "type": "object",
                        "properties": {
                            "agent_validated": {
                                "type": "string",
                                "enum": ["solution_architect", "code_generator", "deployment_manager"]
                            },
                            "request_id": {
                                "type": "string"
                            },
                            "timestamp": {
                                "type": "string"
                            },
                            "overall_status": {
                                "type": "string",
                                "enum": ["PASS", "FAIL", "NEEDS_REVISION"]
                            },
                            "requirements_validation": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "requirement_id": {"type": "string"},
                                        "requirement_text": {"type": "string"},
                                        "validation_status": {"type": "string"},
                                        "evidence": {"type": "string"},
                                        "issues": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    }
                                }
                            },
                            "deliverable_assessment": {
                                "type": "object",
                                "properties": {
                                    "completeness_score": {"type": "number"},
                                    "quality_score": {"type": "number"},
                                    "compliance_score": {"type": "number"}
                                }
                            },
                            "action_items": {
                                "type": "object",
                                "properties": {
                                    "critical_fixes": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "recommendations": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "can_proceed": {"type": "boolean"}
                                }
                            }
                        },
                        "required": ["agent_validated", "request_id", "overall_status"]
                    }
                },
                "required": ["validation_report"]
            }
        }
    }
}