"""
Configuration management for AutoNinja AWS Bedrock.

This module handles environment-specific configuration settings for the AutoNinja system.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BedrockSettings(BaseSettings):
    """Bedrock-specific configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="BEDROCK_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # AWS Configuration
    region_name: str = Field(default="us-east-2", description="AWS region for Bedrock services")
    
    # Model Configuration
    default_max_tokens: int = Field(default=4096, description="Default maximum tokens for model responses")
    default_temperature: float = Field(default=0.1, description="Default temperature for model responses")
    default_top_p: float = Field(default=0.9, description="Default top_p for model responses")
    
    # Timeout and Retry Configuration
    default_timeout: int = Field(default=300, description="Default timeout for model invocations in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries for failed requests")
    
    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = Field(
        default=5, 
        description="Number of failures before opening circuit breaker"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60, 
        description="Time in seconds before attempting to close circuit breaker"
    )
    
    # Model Selection Configuration
    enable_model_fallback: bool = Field(
        default=True, 
        description="Enable fallback to alternative models on failure"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    enable_debug_logging: bool = Field(default=False, description="Enable debug logging for Bedrock calls")


class AutoNinjaSettings(BaseSettings):
    """Main AutoNinja configuration settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application Configuration
    app_name: str = Field(default="AutoNinja AWS Bedrock", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Enable API auto-reload in development")
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-2", description="Default AWS region")
    
    # DynamoDB Configuration
    dynamodb_table_prefix: str = Field(default="autoninja", description="Prefix for DynamoDB table names")
    
    # S3 Configuration
    s3_bucket_prefix: str = Field(default="autoninja", description="Prefix for S3 bucket names")
    
    # Bedrock Configuration
    bedrock: BedrockSettings = Field(default_factory=BedrockSettings)
    
    # Security Configuration
    enable_api_key_auth: bool = Field(default=True, description="Enable API key authentication")
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    
    # Monitoring Configuration
    enable_xray_tracing: bool = Field(default=True, description="Enable AWS X-Ray tracing")
    enable_cloudwatch_metrics: bool = Field(default=True, description="Enable CloudWatch metrics")
    
    # Development Configuration
    enable_cors: bool = Field(default=True, description="Enable CORS for development")
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")


def get_settings() -> AutoNinjaSettings:
    """
    Get the application settings.
    
    Returns:
        AutoNinjaSettings: The configured application settings
    """
    return AutoNinjaSettings()


# Global settings instance
settings = get_settings()