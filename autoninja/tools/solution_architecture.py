"""
Solution Architecture Tools for AutoNinja

LangChain tools for AWS service selection, architecture design,
CloudFormation template generation, and cost estimation.
"""

import json
import re
from typing import Dict, List, Any, Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient, KnowledgeBaseType


class ServiceSelectionInput(BaseModel):
    """Input schema for AWS service selection tool."""
    requirements: Dict[str, Any] = Field(description="Structured requirements for service selection")
    constraints: Optional[Dict[str, Any]] = Field(default=None, description="Budget and technical constraints")


class ServiceSelectionTool(BaseTool):
    """Tool for selecting optimal AWS services based on requirements."""
    
    name: str = "aws_service_selection"
    description: str = """Select optimal AWS services based on functional and non-functional requirements.
    Considers performance, cost, scalability, and compliance requirements."""
    
    args_schema: Type[BaseModel] = ServiceSelectionInput
    kb_client: Optional[BedrockKnowledgeBaseClient] = Field(default=None, exclude=True)
    
    def __init__(self, knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None, **kwargs):
        super().__init__(kb_client=knowledge_base_client, **kwargs)
        
    def _run(self, requirements: Dict[str, Any], constraints: Optional[Dict[str, Any]] = None) -> str:
        """Select AWS services based on requirements."""
        try:
            # Analyze requirements to determine service needs
            service_recommendations = self._analyze_service_needs(requirements)
            
            # Apply constraints to filter services
            if constraints:
                service_recommendations = self._apply_constraints(service_recommendations, constraints)
            
            # Get architecture patterns from knowledge base
            architecture_patterns = []
            if self.kb_client:
                architecture_patterns = self._get_architecture_patterns(requirements)
            
            # Generate service configuration
            service_config = self._generate_service_configuration(service_recommendations, requirements)
            
            result = {
                "recommended_services": service_recommendations,
                "service_configuration": service_config,
                "architecture_patterns": architecture_patterns,
                "cost_estimate": self._estimate_costs(service_recommendations),
                "deployment_complexity": self._assess_deployment_complexity(service_recommendations)
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Error selecting AWS services: {str(e)}"
    
    def _analyze_service_needs(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze requirements to determine needed AWS services."""
        services = []
        
        functional_reqs = requirements.get("functional_requirements", [])
        nfr = requirements.get("non_functional_requirements", {})
        agent_type = requirements.get("agent_type_detected", "custom")
        
        # Core Bedrock services for AI agents
        services.append({
            "service": "Amazon Bedrock",
            "purpose": "Foundation model access and agent orchestration",
            "configuration": {
                "models": ["anthropic.claude-3-sonnet-20240229-v1:0"],
                "agent_runtime": True,
                "knowledge_bases": True
            },
            "priority": "high",
            "cost_tier": "variable"
        })
        
        # API Gateway for external access
        if any("api" in req.lower() or "endpoint" in req.lower() for req in functional_reqs):
            services.append({
                "service": "Amazon API Gateway",
                "purpose": "REST API endpoints for agent access",
                "configuration": {
                    "type": "REST",
                    "authentication": "API_KEY",
                    "throttling": True
                },
                "priority": "high",
                "cost_tier": "low"
            })
        
        # Lambda for serverless compute
        services.append({
            "service": "AWS Lambda",
            "purpose": "Serverless compute for agent logic",
            "configuration": {
                "runtime": "python3.12",
                "memory": 1024,
                "timeout": 300
            },
            "priority": "high",
            "cost_tier": "low"
        })
        
        # Data storage services
        if any("data" in req.lower() or "store" in req.lower() for req in functional_reqs):
            services.append({
                "service": "Amazon DynamoDB",
                "purpose": "NoSQL database for session state and metadata",
                "configuration": {
                    "billing_mode": "PAY_PER_REQUEST",
                    "encryption": True,
                    "point_in_time_recovery": True
                },
                "priority": "medium",
                "cost_tier": "low"
            })
        
        # File storage
        if any("file" in req.lower() or "document" in req.lower() for req in functional_reqs):
            services.append({
                "service": "Amazon S3",
                "purpose": "Object storage for documents and artifacts",
                "configuration": {
                    "storage_class": "STANDARD",
                    "versioning": True,
                    "encryption": "AES256"
                },
                "priority": "medium",
                "cost_tier": "low"
            })
        
        # Monitoring and observability
        services.extend([
            {
                "service": "Amazon CloudWatch",
                "purpose": "Monitoring, logging, and alerting",
                "configuration": {
                    "log_retention": 30,
                    "metrics": True,
                    "alarms": True
                },
                "priority": "medium",
                "cost_tier": "low"
            },
            {
                "service": "AWS X-Ray",
                "purpose": "Distributed tracing and performance analysis",
                "configuration": {
                    "sampling_rate": 0.1,
                    "trace_segments": True
                },
                "priority": "low",
                "cost_tier": "low"
            }
        ])
        
        # Security services
        services.extend([
            {
                "service": "AWS IAM",
                "purpose": "Identity and access management",
                "configuration": {
                    "least_privilege": True,
                    "role_based": True
                },
                "priority": "high",
                "cost_tier": "free"
            },
            {
                "service": "AWS Secrets Manager",
                "purpose": "Secure credential storage",
                "configuration": {
                    "rotation": True,
                    "encryption": True
                },
                "priority": "medium",
                "cost_tier": "low"
            }
        ])
        
        # Performance-specific services
        if nfr.get("performance"):
            services.append({
                "service": "Amazon ElastiCache",
                "purpose": "In-memory caching for performance",
                "configuration": {
                    "engine": "redis",
                    "node_type": "cache.t3.micro"
                },
                "priority": "low",
                "cost_tier": "medium"
            })
        
        # High availability services
        if nfr.get("availability"):
            services.append({
                "service": "Application Load Balancer",
                "purpose": "Load balancing and high availability",
                "configuration": {
                    "scheme": "internet-facing",
                    "health_checks": True
                },
                "priority": "medium",
                "cost_tier": "medium"
            })
        
        return services
    
    def _apply_constraints(self, services: List[Dict[str, Any]], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply budget and technical constraints to service selection."""
        filtered_services = []
        
        budget_constraint = constraints.get("budget", "standard")
        
        for service in services:
            # Apply budget constraints
            if budget_constraint == "minimal" and service["cost_tier"] in ["high", "medium"]:
                if service["priority"] != "high":
                    continue  # Skip non-essential expensive services
            
            # Apply technical constraints
            tech_constraints = constraints.get("technology", [])
            if "serverless_only" in tech_constraints:
                if service["service"] in ["Amazon EC2", "Amazon ECS"]:
                    continue  # Skip non-serverless services
            
            filtered_services.append(service)
        
        return filtered_services
    
    def _get_architecture_patterns(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant architecture patterns from knowledge base."""
        if not self.kb_client:
            return []
        
        try:
            # Build query from requirements
            agent_type = requirements.get("agent_type_detected", "custom")
            complexity = requirements.get("complexity", "medium")
            
            query = f"architecture pattern for {agent_type} agent with {complexity} complexity"
            
            results = self.kb_client.search_knowledge_base(
                kb_type=KnowledgeBaseType.ARCHITECTURE_PATTERNS,
                query=query,
                max_results=3
            )
            
            patterns = []
            for result in results:
                patterns.append({
                    "pattern_name": result.title,
                    "description": result.excerpt,
                    "relevance_score": result.relevance_score,
                    "content": result.content[:500] + "..." if len(result.content) > 500 else result.content
                })
            
            return patterns
            
        except Exception:
            return []
    
    def _generate_service_configuration(self, services: List[Dict[str, Any]], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed service configuration."""
        config = {
            "deployment_model": "serverless",
            "region": "us-east-2",
            "environment": "production",
            "services": {}
        }
        
        for service in services:
            service_name = service["service"].replace(" ", "").replace("Amazon", "").replace("AWS", "")
            config["services"][service_name] = {
                "enabled": True,
                "configuration": service.get("configuration", {}),
                "purpose": service["purpose"],
                "priority": service["priority"]
            }
        
        # Add integration configuration
        config["integrations"] = self._generate_integration_config(services)
        
        return config
    
    def _generate_integration_config(self, services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate service integration configuration."""
        integrations = {
            "api_gateway_lambda": {
                "enabled": any(s["service"] == "Amazon API Gateway" for s in services) and 
                          any(s["service"] == "AWS Lambda" for s in services),
                "configuration": {
                    "proxy_integration": True,
                    "cors_enabled": True
                }
            },
            "lambda_bedrock": {
                "enabled": True,
                "configuration": {
                    "invoke_model": True,
                    "agent_runtime": True
                }
            },
            "lambda_dynamodb": {
                "enabled": any(s["service"] == "Amazon DynamoDB" for s in services),
                "configuration": {
                    "read_write_access": True,
                    "stream_processing": False
                }
            }
        }
        
        return integrations
    
    def _estimate_costs(self, services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate monthly costs for selected services."""
        cost_estimates = {
            "monthly_estimate": 0.0,
            "service_breakdown": {},
            "cost_factors": []
        }
        
        # Basic cost estimates (simplified)
        service_costs = {
            "Amazon Bedrock": {"base": 50, "variable": "per_request"},
            "Amazon API Gateway": {"base": 5, "variable": "per_million_requests"},
            "AWS Lambda": {"base": 0, "variable": "per_gb_second"},
            "Amazon DynamoDB": {"base": 0, "variable": "per_read_write"},
            "Amazon S3": {"base": 5, "variable": "per_gb_storage"},
            "Amazon CloudWatch": {"base": 10, "variable": "per_metric"},
            "AWS X-Ray": {"base": 0, "variable": "per_trace"},
            "Amazon ElastiCache": {"base": 50, "variable": "per_hour"},
            "Application Load Balancer": {"base": 25, "variable": "per_hour"}
        }
        
        total_cost = 0
        for service in services:
            service_name = service["service"]
            if service_name in service_costs:
                base_cost = service_costs[service_name]["base"]
                cost_estimates["service_breakdown"][service_name] = {
                    "estimated_monthly": base_cost,
                    "pricing_model": service_costs[service_name]["variable"]
                }
                total_cost += base_cost
        
        cost_estimates["monthly_estimate"] = total_cost
        cost_estimates["cost_factors"] = [
            "Costs vary based on usage patterns",
            "Bedrock costs depend on model usage and requests",
            "Lambda costs scale with execution time and memory",
            "Storage costs depend on data volume"
        ]
        
        return cost_estimates
    
    def _assess_deployment_complexity(self, services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess deployment complexity based on selected services."""
        complexity_score = 0
        complexity_factors = []
        
        # Base complexity for each service
        service_complexity = {
            "Amazon Bedrock": 3,
            "Amazon API Gateway": 2,
            "AWS Lambda": 1,
            "Amazon DynamoDB": 2,
            "Amazon S3": 1,
            "Amazon CloudWatch": 1,
            "AWS X-Ray": 2,
            "Amazon ElastiCache": 3,
            "Application Load Balancer": 3
        }
        
        for service in services:
            service_name = service["service"]
            if service_name in service_complexity:
                complexity_score += service_complexity[service_name]
        
        # Determine complexity level
        if complexity_score <= 10:
            complexity_level = "low"
            complexity_factors.append("Simple serverless architecture")
        elif complexity_score <= 20:
            complexity_level = "medium"
            complexity_factors.append("Moderate complexity with multiple services")
        else:
            complexity_level = "high"
            complexity_factors.append("Complex architecture requiring careful orchestration")
        
        return {
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "factors": complexity_factors,
            "estimated_deployment_time": "1-2 weeks" if complexity_level == "low" else 
                                       "2-4 weeks" if complexity_level == "medium" else "4+ weeks"
        }


class CloudFormationGeneratorInput(BaseModel):
    """Input schema for CloudFormation template generation tool."""
    service_architecture: Dict[str, Any] = Field(description="Service architecture specification")
    deployment_config: Optional[Dict[str, Any]] = Field(default=None, description="Deployment configuration")


class CloudFormationGeneratorTool(BaseTool):
    """Tool for generating CloudFormation templates from architecture specifications."""
    
    name: str = "cloudformation_generator"
    description: str = """Generate CloudFormation templates from service architecture specifications.
    Creates infrastructure as code with proper resource dependencies and configurations."""
    
    args_schema: Type[BaseModel] = CloudFormationGeneratorInput
    kb_client: Optional[BedrockKnowledgeBaseClient] = Field(default=None, exclude=True)
    
    def __init__(self, knowledge_base_client: Optional[BedrockKnowledgeBaseClient] = None, **kwargs):
        super().__init__(kb_client=knowledge_base_client, **kwargs)
    
    def _run(self, service_architecture: Dict[str, Any], deployment_config: Optional[Dict[str, Any]] = None) -> str:
        """Generate CloudFormation template from architecture."""
        try:
            # Generate CloudFormation template structure
            template = self._generate_template_structure()
            
            # Add parameters
            template["Parameters"] = self._generate_parameters(service_architecture, deployment_config)
            
            # Add resources
            template["Resources"] = self._generate_resources(service_architecture, deployment_config)
            
            # Add outputs
            template["Outputs"] = self._generate_outputs(service_architecture)
            
            # Get template patterns from knowledge base
            template_patterns = []
            if self.kb_client:
                template_patterns = self._get_template_patterns(service_architecture)
            
            result = {
                "cloudformation_template": template,
                "template_patterns": template_patterns,
                "deployment_instructions": self._generate_deployment_instructions(template),
                "validation_commands": self._generate_validation_commands()
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Error generating CloudFormation template: {str(e)}"
    
    def _generate_template_structure(self) -> Dict[str, Any]:
        """Generate basic CloudFormation template structure."""
        return {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "AutoNinja AI Agent Infrastructure",
            "Metadata": {
                "AWS::CloudFormation::Interface": {
                    "ParameterGroups": [
                        {
                            "Label": {"default": "Agent Configuration"},
                            "Parameters": ["AgentName", "Environment"]
                        },
                        {
                            "Label": {"default": "Security Configuration"},
                            "Parameters": ["KMSKeyId"]
                        }
                    ]
                }
            }
        }
    
    def _generate_parameters(self, architecture: Dict[str, Any], config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate CloudFormation parameters."""
        parameters = {
            "AgentName": {
                "Type": "String",
                "Description": "Name of the AI agent",
                "Default": "AutoNinjaAgent",
                "AllowedPattern": "^[a-zA-Z][a-zA-Z0-9-]*$"
            },
            "Environment": {
                "Type": "String",
                "Description": "Deployment environment",
                "Default": "prod",
                "AllowedValues": ["dev", "staging", "prod"]
            },
            "KMSKeyId": {
                "Type": "String",
                "Description": "KMS Key ID for encryption",
                "Default": "alias/aws/s3"
            }
        }
        
        # Add service-specific parameters
        services = architecture.get("services", {})
        
        if "Lambda" in services:
            parameters["LambdaMemorySize"] = {
                "Type": "Number",
                "Description": "Lambda function memory size in MB",
                "Default": 1024,
                "MinValue": 128,
                "MaxValue": 10240
            }
        
        if "DynamoDB" in services:
            parameters["DynamoDBBillingMode"] = {
                "Type": "String",
                "Description": "DynamoDB billing mode",
                "Default": "PAY_PER_REQUEST",
                "AllowedValues": ["PAY_PER_REQUEST", "PROVISIONED"]
            }
        
        return parameters
    
    def _generate_resources(self, architecture: Dict[str, Any], config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate CloudFormation resources."""
        resources = {}
        services = architecture.get("services", {})
        
        # IAM Role for Lambda
        if "Lambda" in services:
            resources["LambdaExecutionRole"] = {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "lambda.amazonaws.com"},
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    },
                    "ManagedPolicyArns": [
                        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                    ],
                    "Policies": [
                        {
                            "PolicyName": "BedrockAccess",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "bedrock:InvokeModel",
                                            "bedrock:InvokeAgent",
                                            "bedrock:Retrieve"
                                        ],
                                        "Resource": "*"
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
            
            # Lambda Function
            resources["AgentLambdaFunction"] = {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "FunctionName": {"Fn::Sub": "${AgentName}-handler"},
                    "Runtime": "python3.12",
                    "Handler": "index.handler",
                    "Role": {"Fn::GetAtt": ["LambdaExecutionRole", "Arn"]},
                    "MemorySize": {"Ref": "LambdaMemorySize"},
                    "Timeout": 300,
                    "Environment": {
                        "Variables": {
                            "AGENT_NAME": {"Ref": "AgentName"},
                            "ENVIRONMENT": {"Ref": "Environment"}
                        }
                    },
                    "Code": {
                        "ZipFile": """
import json
import boto3

def handler(event, context):
    # Placeholder Lambda function
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Agent handler ready'})
    }
"""
                    }
                }
            }
        
        # API Gateway
        if "APIGateway" in services:
            resources["AgentRestApi"] = {
                "Type": "AWS::ApiGateway::RestApi",
                "Properties": {
                    "Name": {"Fn::Sub": "${AgentName}-api"},
                    "Description": "REST API for AI Agent",
                    "EndpointConfiguration": {
                        "Types": ["REGIONAL"]
                    }
                }
            }
            
            resources["AgentApiResource"] = {
                "Type": "AWS::ApiGateway::Resource",
                "Properties": {
                    "RestApiId": {"Ref": "AgentRestApi"},
                    "ParentId": {"Fn::GetAtt": ["AgentRestApi", "RootResourceId"]},
                    "PathPart": "agent"
                }
            }
            
            resources["AgentApiMethod"] = {
                "Type": "AWS::ApiGateway::Method",
                "Properties": {
                    "RestApiId": {"Ref": "AgentRestApi"},
                    "ResourceId": {"Ref": "AgentApiResource"},
                    "HttpMethod": "POST",
                    "AuthorizationType": "AWS_IAM",
                    "Integration": {
                        "Type": "AWS_PROXY",
                        "IntegrationHttpMethod": "POST",
                        "Uri": {
                            "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${AgentLambdaFunction.Arn}/invocations"
                        }
                    }
                }
            }
            
            resources["AgentApiDeployment"] = {
                "Type": "AWS::ApiGateway::Deployment",
                "DependsOn": ["AgentApiMethod"],
                "Properties": {
                    "RestApiId": {"Ref": "AgentRestApi"},
                    "StageName": {"Ref": "Environment"}
                }
            }
            
            resources["LambdaApiPermission"] = {
                "Type": "AWS::Lambda::Permission",
                "Properties": {
                    "FunctionName": {"Ref": "AgentLambdaFunction"},
                    "Action": "lambda:InvokeFunction",
                    "Principal": "apigateway.amazonaws.com",
                    "SourceArn": {
                        "Fn::Sub": "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${AgentRestApi}/*/*"
                    }
                }
            }
        
        # DynamoDB Table
        if "DynamoDB" in services:
            resources["AgentStateTable"] = {
                "Type": "AWS::DynamoDB::Table",
                "Properties": {
                    "TableName": {"Fn::Sub": "${AgentName}-state"},
                    "BillingMode": {"Ref": "DynamoDBBillingMode"},
                    "AttributeDefinitions": [
                        {
                            "AttributeName": "session_id",
                            "AttributeType": "S"
                        }
                    ],
                    "KeySchema": [
                        {
                            "AttributeName": "session_id",
                            "KeyType": "HASH"
                        }
                    ],
                    "PointInTimeRecoverySpecification": {
                        "PointInTimeRecoveryEnabled": True
                    },
                    "SSESpecification": {
                        "SSEEnabled": True,
                        "KMSMasterKeyId": {"Ref": "KMSKeyId"}
                    }
                }
            }
        
        # S3 Bucket
        if "S3" in services:
            resources["AgentArtifactsBucket"] = {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": {"Fn::Sub": "${AgentName}-artifacts-${AWS::AccountId}"},
                    "VersioningConfiguration": {
                        "Status": "Enabled"
                    },
                    "BucketEncryption": {
                        "ServerSideEncryptionConfiguration": [
                            {
                                "ServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "aws:kms",
                                    "KMSMasterKeyID": {"Ref": "KMSKeyId"}
                                }
                            }
                        ]
                    },
                    "PublicAccessBlockConfiguration": {
                        "BlockPublicAcls": True,
                        "BlockPublicPolicy": True,
                        "IgnorePublicAcls": True,
                        "RestrictPublicBuckets": True
                    }
                }
            }
        
        return resources
    
    def _generate_outputs(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Generate CloudFormation outputs."""
        outputs = {}
        services = architecture.get("services", {})
        
        if "APIGateway" in services:
            outputs["ApiEndpoint"] = {
                "Description": "API Gateway endpoint URL",
                "Value": {
                    "Fn::Sub": "https://${AgentRestApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}/agent"
                },
                "Export": {
                    "Name": {"Fn::Sub": "${AWS::StackName}-ApiEndpoint"}
                }
            }
        
        if "Lambda" in services:
            outputs["LambdaFunctionArn"] = {
                "Description": "Lambda function ARN",
                "Value": {"Fn::GetAtt": ["AgentLambdaFunction", "Arn"]},
                "Export": {
                    "Name": {"Fn::Sub": "${AWS::StackName}-LambdaArn"}
                }
            }
        
        if "DynamoDB" in services:
            outputs["DynamoDBTableName"] = {
                "Description": "DynamoDB table name",
                "Value": {"Ref": "AgentStateTable"},
                "Export": {
                    "Name": {"Fn::Sub": "${AWS::StackName}-TableName"}
                }
            }
        
        if "S3" in services:
            outputs["S3BucketName"] = {
                "Description": "S3 bucket name",
                "Value": {"Ref": "AgentArtifactsBucket"},
                "Export": {
                    "Name": {"Fn::Sub": "${AWS::StackName}-BucketName"}
                }
            }
        
        return outputs
    
    def _get_template_patterns(self, architecture: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get CloudFormation template patterns from knowledge base."""
        if not self.kb_client:
            return []
        
        try:
            query = "CloudFormation template patterns for AI agent infrastructure"
            
            results = self.kb_client.search_knowledge_base(
                kb_type=KnowledgeBaseType.CODE_TEMPLATES,
                query=query,
                max_results=3
            )
            
            patterns = []
            for result in results:
                patterns.append({
                    "pattern_name": result.title,
                    "description": result.excerpt,
                    "relevance_score": result.relevance_score
                })
            
            return patterns
            
        except Exception:
            return []
    
    def _generate_deployment_instructions(self, template: Dict[str, Any]) -> List[str]:
        """Generate deployment instructions for the CloudFormation template."""
        instructions = [
            "1. Save the CloudFormation template to a file (e.g., agent-infrastructure.yaml)",
            "2. Validate the template: aws cloudformation validate-template --template-body file://agent-infrastructure.yaml",
            "3. Deploy the stack: aws cloudformation create-stack --stack-name my-agent-stack --template-body file://agent-infrastructure.yaml --capabilities CAPABILITY_IAM",
            "4. Monitor deployment: aws cloudformation describe-stacks --stack-name my-agent-stack",
            "5. Get outputs: aws cloudformation describe-stacks --stack-name my-agent-stack --query 'Stacks[0].Outputs'"
        ]
        
        return instructions
    
    def _generate_validation_commands(self) -> List[str]:
        """Generate validation commands for the infrastructure."""
        commands = [
            "aws cloudformation validate-template --template-body file://template.yaml",
            "cfn-lint template.yaml",
            "aws cloudformation estimate-template-cost --template-body file://template.yaml"
        ]
        
        return commands


class CostEstimationInput(BaseModel):
    """Input schema for cost estimation tool."""
    service_architecture: Dict[str, Any] = Field(description="Service architecture for cost estimation")
    usage_patterns: Optional[Dict[str, Any]] = Field(default=None, description="Expected usage patterns")


class CostEstimationTool(BaseTool):
    """Tool for estimating AWS costs based on service architecture."""
    
    name: str = "aws_cost_estimation"
    description: str = """Estimate AWS costs based on service architecture and usage patterns.
    Provides detailed cost breakdown and optimization recommendations."""
    
    args_schema: Type[BaseModel] = CostEstimationInput
    
    def _run(self, service_architecture: Dict[str, Any], usage_patterns: Optional[Dict[str, Any]] = None) -> str:
        """Estimate costs for the service architecture."""
        try:
            # Default usage patterns if not provided
            if not usage_patterns:
                usage_patterns = self._get_default_usage_patterns()
            
            # Calculate costs for each service
            service_costs = self._calculate_service_costs(service_architecture, usage_patterns)
            
            # Generate cost optimization recommendations
            optimizations = self._generate_cost_optimizations(service_architecture, service_costs)
            
            # Calculate total costs
            total_costs = self._calculate_total_costs(service_costs)
            
            result = {
                "cost_breakdown": service_costs,
                "total_monthly_cost": total_costs,
                "cost_optimizations": optimizations,
                "usage_assumptions": usage_patterns,
                "cost_factors": self._identify_cost_factors(service_architecture)
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Error estimating costs: {str(e)}"
    
    def _get_default_usage_patterns(self) -> Dict[str, Any]:
        """Get default usage patterns for cost estimation."""
        return {
            "monthly_requests": 100000,
            "average_request_duration": 2.0,  # seconds
            "lambda_memory": 1024,  # MB
            "storage_gb": 10,
            "data_transfer_gb": 50,
            "concurrent_users": 100,
            "peak_usage_factor": 2.0
        }
    
    def _calculate_service_costs(self, architecture: Dict[str, Any], usage: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate costs for each service in the architecture."""
        costs = {}
        services = architecture.get("services", {})
        
        # Bedrock costs
        if "Bedrock" in services:
            # Simplified Bedrock pricing (varies by model)
            input_tokens = usage["monthly_requests"] * 1000  # Assume 1k tokens per request
            output_tokens = usage["monthly_requests"] * 500   # Assume 500 tokens per response
            
            costs["Bedrock"] = {
                "input_token_cost": input_tokens * 0.003 / 1000,  # $3 per 1M input tokens
                "output_token_cost": output_tokens * 0.015 / 1000,  # $15 per 1M output tokens
                "monthly_total": (input_tokens * 0.003 + output_tokens * 0.015) / 1000,
                "usage_details": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens
                }
            }
        
        # Lambda costs
        if "Lambda" in services:
            gb_seconds = (usage["lambda_memory"] / 1024) * usage["average_request_duration"] * usage["monthly_requests"]
            
            costs["Lambda"] = {
                "request_cost": usage["monthly_requests"] * 0.0000002,  # $0.20 per 1M requests
                "compute_cost": gb_seconds * 0.0000166667,  # $0.0000166667 per GB-second
                "monthly_total": (usage["monthly_requests"] * 0.0000002) + (gb_seconds * 0.0000166667),
                "usage_details": {
                    "requests": usage["monthly_requests"],
                    "gb_seconds": gb_seconds
                }
            }
        
        # API Gateway costs
        if "APIGateway" in services:
            costs["APIGateway"] = {
                "request_cost": usage["monthly_requests"] * 0.0000035,  # $3.50 per million requests
                "monthly_total": usage["monthly_requests"] * 0.0000035,
                "usage_details": {
                    "requests": usage["monthly_requests"]
                }
            }
        
        # DynamoDB costs
        if "DynamoDB" in services:
            # Assume read/write ratio of 3:1
            read_requests = usage["monthly_requests"] * 3
            write_requests = usage["monthly_requests"]
            
            costs["DynamoDB"] = {
                "read_cost": read_requests * 0.00000025,  # $0.25 per million read requests
                "write_cost": write_requests * 0.00000125,  # $1.25 per million write requests
                "storage_cost": usage["storage_gb"] * 0.25,  # $0.25 per GB per month
                "monthly_total": (read_requests * 0.00000025) + (write_requests * 0.00000125) + (usage["storage_gb"] * 0.25),
                "usage_details": {
                    "read_requests": read_requests,
                    "write_requests": write_requests,
                    "storage_gb": usage["storage_gb"]
                }
            }
        
        # S3 costs
        if "S3" in services:
            costs["S3"] = {
                "storage_cost": usage["storage_gb"] * 0.023,  # $0.023 per GB per month
                "request_cost": usage["monthly_requests"] * 0.0000004,  # $0.40 per million requests
                "data_transfer_cost": usage["data_transfer_gb"] * 0.09,  # $0.09 per GB
                "monthly_total": (usage["storage_gb"] * 0.023) + (usage["monthly_requests"] * 0.0000004) + (usage["data_transfer_gb"] * 0.09),
                "usage_details": {
                    "storage_gb": usage["storage_gb"],
                    "requests": usage["monthly_requests"],
                    "data_transfer_gb": usage["data_transfer_gb"]
                }
            }
        
        # CloudWatch costs
        if "CloudWatch" in services:
            costs["CloudWatch"] = {
                "metrics_cost": 10 * 0.30,  # $0.30 per metric per month (assume 10 custom metrics)
                "logs_cost": 5 * 0.50,  # $0.50 per GB ingested (assume 5 GB)
                "monthly_total": (10 * 0.30) + (5 * 0.50),
                "usage_details": {
                    "custom_metrics": 10,
                    "log_ingestion_gb": 5
                }
            }
        
        return costs
    
    def _calculate_total_costs(self, service_costs: Dict[str, Any]) -> Dict[str, float]:
        """Calculate total costs across all services."""
        monthly_total = sum(service["monthly_total"] for service in service_costs.values())
        
        return {
            "monthly": monthly_total,
            "annual": monthly_total * 12,
            "daily": monthly_total / 30
        }
    
    def _generate_cost_optimizations(self, architecture: Dict[str, Any], costs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cost optimization recommendations."""
        optimizations = []
        
        # Bedrock optimization
        if "Bedrock" in costs and costs["Bedrock"]["monthly_total"] > 100:
            optimizations.append({
                "service": "Bedrock",
                "recommendation": "Consider using smaller models for simple tasks",
                "potential_savings": "20-40%",
                "implementation": "Implement model selection logic based on request complexity"
            })
        
        # Lambda optimization
        if "Lambda" in costs:
            optimizations.append({
                "service": "Lambda",
                "recommendation": "Optimize memory allocation based on actual usage",
                "potential_savings": "10-30%",
                "implementation": "Use AWS Lambda Power Tuning to find optimal memory setting"
            })
        
        # DynamoDB optimization
        if "DynamoDB" in costs and costs["DynamoDB"]["monthly_total"] > 50:
            optimizations.append({
                "service": "DynamoDB",
                "recommendation": "Consider using DynamoDB On-Demand for variable workloads",
                "potential_savings": "15-25%",
                "implementation": "Switch to on-demand billing if usage is unpredictable"
            })
        
        # General optimizations
        optimizations.extend([
            {
                "service": "General",
                "recommendation": "Implement caching to reduce API calls",
                "potential_savings": "20-50%",
                "implementation": "Add ElastiCache or application-level caching"
            },
            {
                "service": "General",
                "recommendation": "Use Reserved Instances for predictable workloads",
                "potential_savings": "30-60%",
                "implementation": "Purchase Reserved Instances for consistent usage patterns"
            }
        ])
        
        return optimizations
    
    def _identify_cost_factors(self, architecture: Dict[str, Any]) -> List[str]:
        """Identify key factors that affect costs."""
        factors = [
            "Request volume is the primary cost driver for Bedrock and API Gateway",
            "Lambda costs scale with execution time and memory allocation",
            "Storage costs depend on data retention policies",
            "Data transfer costs can be significant for high-traffic applications"
        ]
        
        services = architecture.get("services", {})
        
        if "Bedrock" in services:
            factors.append("Bedrock model selection significantly impacts token costs")
        
        if "DynamoDB" in services:
            factors.append("DynamoDB read/write patterns affect cost efficiency")
        
        if "S3" in services:
            factors.append("S3 storage class selection can optimize long-term costs")
        
        return factors