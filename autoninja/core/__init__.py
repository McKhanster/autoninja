"""
AutoNinja Core Module

This module provides core functionality for the AutoNinja AWS Bedrock system,
including Bedrock client management, configuration, and utilities.
"""

from .bedrock_client import (
    BedrockClientManager,
    BedrockClientConfig,
    BedrockCircuitBreaker,
    TaskComplexity,
    BedrockModelId,
    get_bedrock_client_manager,
    reset_client_manager
)

from .config import (
    BedrockSettings,
    AutoNinjaSettings,
    get_settings,
    settings
)

from .knowledge_base import (
    BedrockKnowledgeBaseClient,
    DynamicPatternManager,
    KnowledgeBaseType,
    DocumentType,
    KnowledgeBaseDocument,
    SearchResult,
    KnowledgeBaseConfig,
    get_knowledge_base_client,
    reset_knowledge_base_client
)

from .guardrails import (
    BedrockGuardrailsClient,
    GuardrailsManager,
    GuardrailConfig,
    GuardrailAssessment,
    GuardrailAction,
    ContentFilter,
    ContentFilterType,
    FilterStrength,
    PIIFilter,
    PIIEntityType,
    TopicFilter,
    WordFilter,
    get_guardrails_manager,
    reset_guardrails_manager,
    validate_input,
    validate_output,
    filter_content,
    get_compliance_report
)

__all__ = [
    # Bedrock client classes and functions
    "BedrockClientManager",
    "BedrockClientConfig", 
    "BedrockCircuitBreaker",
    "TaskComplexity",
    "BedrockModelId",
    "get_bedrock_client_manager",
    "reset_client_manager",
    
    # Configuration classes and functions
    "BedrockSettings",
    "AutoNinjaSettings", 
    "get_settings",
    "settings",
    
    # Knowledge Base classes and functions
    "BedrockKnowledgeBaseClient",
    "DynamicPatternManager",
    "KnowledgeBaseType",
    "DocumentType",
    "KnowledgeBaseDocument",
    "SearchResult",
    "KnowledgeBaseConfig",
    "get_knowledge_base_client",
    "reset_knowledge_base_client",
    
    # Guardrails classes and functions
    "BedrockGuardrailsClient",
    "GuardrailsManager",
    "GuardrailConfig",
    "GuardrailAssessment",
    "GuardrailAction",
    "ContentFilter",
    "ContentFilterType",
    "FilterStrength",
    "PIIFilter",
    "PIIEntityType",
    "TopicFilter",
    "WordFilter",
    "get_guardrails_manager",
    "reset_guardrails_manager",
    "validate_input",
    "validate_output",
    "filter_content",
    "get_compliance_report"
]