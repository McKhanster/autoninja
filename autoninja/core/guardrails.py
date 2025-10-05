"""
Bedrock Guardrails integration for content filtering and safety controls.

This module provides functionality for integrating Bedrock Guardrails into
agent response processing and compliance validation for generated content.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


class GuardrailAction(Enum):
    """Actions that can be taken by guardrails."""
    BLOCKED = "BLOCKED"
    ALLOWED = "ALLOWED"
    FILTERED = "FILTERED"


class ContentFilterType(Enum):
    """Types of content filters available in Bedrock Guardrails."""
    HATE = "HATE"
    INSULTS = "INSULTS"
    SEXUAL = "SEXUAL"
    VIOLENCE = "VIOLENCE"
    MISCONDUCT = "MISCONDUCT"
    PROMPT_ATTACK = "PROMPT_ATTACK"


class FilterStrength(Enum):
    """Strength levels for content filters."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PIIEntityType(Enum):
    """Types of PII entities that can be detected and filtered."""
    ADDRESS = "ADDRESS"
    AGE = "AGE"
    AWS_ACCESS_KEY = "AWS_ACCESS_KEY"
    AWS_SECRET_KEY = "AWS_SECRET_KEY"
    CA_HEALTH_NUMBER = "CA_HEALTH_NUMBER"
    CA_SOCIAL_INSURANCE_NUMBER = "CA_SOCIAL_INSURANCE_NUMBER"
    CREDIT_DEBIT_CARD_CVV = "CREDIT_DEBIT_CARD_CVV"
    CREDIT_DEBIT_CARD_EXPIRY = "CREDIT_DEBIT_CARD_EXPIRY"
    CREDIT_DEBIT_CARD_NUMBER = "CREDIT_DEBIT_CARD_NUMBER"
    DRIVER_ID = "DRIVER_ID"
    EMAIL = "EMAIL"
    INTERNATIONAL_BANK_ACCOUNT_NUMBER = "INTERNATIONAL_BANK_ACCOUNT_NUMBER"
    IP_ADDRESS = "IP_ADDRESS"
    LICENSE_PLATE = "LICENSE_PLATE"
    MAC_ADDRESS = "MAC_ADDRESS"
    NAME = "NAME"
    PASSWORD = "PASSWORD"
    PHONE = "PHONE"
    PIN = "PIN"
    ROUTING_NUMBER = "ROUTING_NUMBER"
    SSN = "SSN"
    SWIFT_CODE = "SWIFT_CODE"
    UK_NATIONAL_HEALTH_SERVICE_NUMBER = "UK_NATIONAL_HEALTH_SERVICE_NUMBER"
    UK_NATIONAL_INSURANCE_NUMBER = "UK_NATIONAL_INSURANCE_NUMBER"
    UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER = "UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER"
    URL = "URL"
    USERNAME = "USERNAME"
    US_BANK_ACCOUNT_NUMBER = "US_BANK_ACCOUNT_NUMBER"
    US_BANK_ROUTING_NUMBER = "US_BANK_ROUTING_NUMBER"
    US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER = "US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER"
    US_PASSPORT_NUMBER = "US_PASSPORT_NUMBER"
    VEHICLE_IDENTIFICATION_NUMBER = "VEHICLE_IDENTIFICATION_NUMBER"


@dataclass
class ContentFilter:
    """Configuration for a content filter."""
    filter_type: ContentFilterType
    strength: FilterStrength


@dataclass
class PIIFilter:
    """Configuration for PII filtering."""
    entity_types: List[PIIEntityType]
    action: str = "BLOCK"  # BLOCK or ANONYMIZE


@dataclass
class TopicFilter:
    """Configuration for topic-based filtering."""
    name: str
    definition: str
    examples: List[str]
    action: str = "BLOCK"  # BLOCK or ALLOW


@dataclass
class WordFilter:
    """Configuration for word-based filtering."""
    words: List[str]
    action: str = "BLOCK"  # BLOCK or ALLOW


@dataclass
class GuardrailConfig:
    """Configuration for Bedrock Guardrails."""
    guardrail_id: str
    guardrail_version: str = "DRAFT"
    region_name: str = "us-east-2"
    content_filters: List[ContentFilter] = None
    pii_filters: List[PIIFilter] = None
    topic_filters: List[TopicFilter] = None
    word_filters: List[WordFilter] = None
    
    def __post_init__(self):
        if self.content_filters is None:
            self.content_filters = []
        if self.pii_filters is None:
            self.pii_filters = []
        if self.topic_filters is None:
            self.topic_filters = []
        if self.word_filters is None:
            self.word_filters = []


@dataclass
class GuardrailAssessment:
    """Result of guardrail assessment."""
    action: GuardrailAction
    filtered_content: Optional[str]
    assessments: List[Dict[str, Any]]
    usage: Dict[str, Any]
    trace_id: Optional[str] = None


class BedrockGuardrailsClient:
    """Client for interacting with Bedrock Guardrails."""
    
    def __init__(self, config: GuardrailConfig):
        self.config = config
        self._bedrock_runtime_client = boto3.client(
            'bedrock-runtime',
            region_name=self.config.region_name
        )
        self._bedrock_client = boto3.client(
            'bedrock',
            region_name=self.config.region_name
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def apply_guardrail(
        self,
        content: str,
        source: str = "INPUT"
    ) -> GuardrailAssessment:
        """
        Apply guardrail filtering to content.
        
        Args:
            content: The content to filter
            source: The source of the content (INPUT or OUTPUT)
            
        Returns:
            GuardrailAssessment: The assessment result
            
        Raises:
            ClientError: If the Bedrock API call fails
        """
        try:
            response = self._bedrock_runtime_client.apply_guardrail(
                guardrailIdentifier=self.config.guardrail_id,
                guardrailVersion=self.config.guardrail_version,
                source=source,
                content=[
                    {
                        'text': {
                            'text': content
                        }
                    }
                ]
            )
            
            # Parse the response
            action = GuardrailAction(response.get('action', 'ALLOWED'))
            
            # Extract filtered content if available
            filtered_content = None
            outputs = response.get('outputs', [])
            if outputs and 'text' in outputs[0]:
                filtered_content = outputs[0]['text']
            
            # Extract assessments
            assessments = response.get('assessments', [])
            
            # Extract usage information
            usage = response.get('usage', {})
            
            assessment = GuardrailAssessment(
                action=action,
                filtered_content=filtered_content,
                assessments=assessments,
                usage=usage,
                trace_id=response.get('trace_id')
            )
            
            logger.info(f"Guardrail assessment completed: {action.value}")
            return assessment
            
        except ClientError as e:
            logger.error(f"Failed to apply guardrail: {str(e)}")
            raise
    
    def validate_input_content(self, content: str) -> GuardrailAssessment:
        """
        Validate input content against guardrails.
        
        Args:
            content: The input content to validate
            
        Returns:
            GuardrailAssessment: The validation result
        """
        return self.apply_guardrail(content, source="INPUT")
    
    def validate_output_content(self, content: str) -> GuardrailAssessment:
        """
        Validate output content against guardrails.
        
        Args:
            content: The output content to validate
            
        Returns:
            GuardrailAssessment: The validation result
        """
        return self.apply_guardrail(content, source="OUTPUT")
    
    def is_content_safe(self, content: str, source: str = "INPUT") -> bool:
        """
        Check if content is safe according to guardrails.
        
        Args:
            content: The content to check
            source: The source of the content
            
        Returns:
            bool: True if content is safe, False otherwise
        """
        try:
            assessment = self.apply_guardrail(content, source)
            return assessment.action == GuardrailAction.ALLOWED
        except Exception as e:
            logger.error(f"Error checking content safety: {str(e)}")
            return False
    
    def get_filtered_content(self, content: str, source: str = "INPUT") -> str:
        """
        Get filtered version of content.
        
        Args:
            content: The content to filter
            source: The source of the content
            
        Returns:
            str: The filtered content, or original if no filtering applied
        """
        try:
            assessment = self.apply_guardrail(content, source)
            
            if assessment.action == GuardrailAction.FILTERED and assessment.filtered_content:
                return assessment.filtered_content
            elif assessment.action == GuardrailAction.BLOCKED:
                return "[CONTENT BLOCKED BY GUARDRAILS]"
            else:
                return content
                
        except Exception as e:
            logger.error(f"Error filtering content: {str(e)}")
            return content
    
    def get_assessment_details(self, assessment: GuardrailAssessment) -> Dict[str, Any]:
        """
        Extract detailed information from a guardrail assessment.
        
        Args:
            assessment: The guardrail assessment
            
        Returns:
            Dict containing detailed assessment information
        """
        details = {
            'action': assessment.action.value,
            'content_filters': [],
            'pii_filters': [],
            'topic_filters': [],
            'word_filters': [],
            'usage': assessment.usage
        }
        
        for assessment_item in assessment.assessments:
            # Content filter assessments
            if 'contentPolicy' in assessment_item:
                content_policy = assessment_item['contentPolicy']
                for filter_item in content_policy.get('filters', []):
                    details['content_filters'].append({
                        'type': filter_item.get('type'),
                        'confidence': filter_item.get('confidence'),
                        'action': filter_item.get('action')
                    })
            
            # PII filter assessments
            if 'sensitiveInformationPolicy' in assessment_item:
                pii_policy = assessment_item['sensitiveInformationPolicy']
                for pii_item in pii_policy.get('piiEntities', []):
                    details['pii_filters'].append({
                        'type': pii_item.get('type'),
                        'match': pii_item.get('match'),
                        'action': pii_item.get('action')
                    })
            
            # Topic filter assessments
            if 'topicPolicy' in assessment_item:
                topic_policy = assessment_item['topicPolicy']
                for topic_item in topic_policy.get('topics', []):
                    details['topic_filters'].append({
                        'name': topic_item.get('name'),
                        'type': topic_item.get('type'),
                        'action': topic_item.get('action')
                    })
            
            # Word filter assessments
            if 'wordPolicy' in assessment_item:
                word_policy = assessment_item['wordPolicy']
                for word_item in word_policy.get('customWords', []):
                    details['word_filters'].append({
                        'match': word_item.get('match'),
                        'action': word_item.get('action')
                    })
        
        return details


class GuardrailsManager:
    """High-level manager for Bedrock Guardrails integration."""
    
    def __init__(self):
        self._guardrail_configs: Dict[str, GuardrailConfig] = {}
        self._clients: Dict[str, BedrockGuardrailsClient] = {}
        self._initialize_default_guardrails()
    
    def _initialize_default_guardrails(self):
        """Initialize default guardrail configurations."""
        # AutoNinja content filter guardrail
        autoninja_config = GuardrailConfig(
            guardrail_id="autoninja-content-filter",
            guardrail_version="1",
            content_filters=[
                ContentFilter(ContentFilterType.HATE, FilterStrength.HIGH),
                ContentFilter(ContentFilterType.INSULTS, FilterStrength.HIGH),
                ContentFilter(ContentFilterType.SEXUAL, FilterStrength.HIGH),
                ContentFilter(ContentFilterType.VIOLENCE, FilterStrength.MEDIUM),
                ContentFilter(ContentFilterType.MISCONDUCT, FilterStrength.HIGH),
                ContentFilter(ContentFilterType.PROMPT_ATTACK, FilterStrength.HIGH)
            ],
            pii_filters=[
                PIIFilter([
                    PIIEntityType.SSN,
                    PIIEntityType.CREDIT_DEBIT_CARD_NUMBER,
                    PIIEntityType.AWS_ACCESS_KEY,
                    PIIEntityType.AWS_SECRET_KEY,
                    PIIEntityType.PASSWORD
                ], action="BLOCK")
            ],
            topic_filters=[
                TopicFilter(
                    name="malicious_code",
                    definition="Code or instructions intended to cause harm, damage systems, or perform unauthorized actions",
                    examples=[
                        "malware creation",
                        "system exploitation",
                        "unauthorized access methods"
                    ],
                    action="BLOCK"
                ),
                TopicFilter(
                    name="illegal_activities",
                    definition="Instructions or guidance for illegal activities",
                    examples=[
                        "illegal hacking",
                        "fraud schemes",
                        "illegal surveillance"
                    ],
                    action="BLOCK"
                )
            ]
        )
        
        self.register_guardrail("autoninja-default", autoninja_config)
    
    def register_guardrail(self, name: str, config: GuardrailConfig):
        """
        Register a guardrail configuration.
        
        Args:
            name: The name for the guardrail configuration
            config: The guardrail configuration
        """
        self._guardrail_configs[name] = config
        self._clients[name] = BedrockGuardrailsClient(config)
        logger.info(f"Registered guardrail configuration: {name}")
    
    def get_guardrail_client(self, name: str = "autoninja-default") -> BedrockGuardrailsClient:
        """
        Get a guardrail client by name.
        
        Args:
            name: The name of the guardrail configuration
            
        Returns:
            BedrockGuardrailsClient: The guardrail client
            
        Raises:
            ValueError: If the guardrail configuration is not found
        """
        if name not in self._clients:
            raise ValueError(f"Guardrail configuration not found: {name}")
        
        return self._clients[name]
    
    def validate_agent_input(
        self,
        content: str,
        guardrail_name: str = "autoninja-default"
    ) -> GuardrailAssessment:
        """
        Validate agent input content.
        
        Args:
            content: The input content to validate
            guardrail_name: The name of the guardrail to use
            
        Returns:
            GuardrailAssessment: The validation result
        """
        client = self.get_guardrail_client(guardrail_name)
        return client.validate_input_content(content)
    
    def validate_agent_output(
        self,
        content: str,
        guardrail_name: str = "autoninja-default"
    ) -> GuardrailAssessment:
        """
        Validate agent output content.
        
        Args:
            content: The output content to validate
            guardrail_name: The name of the guardrail to use
            
        Returns:
            GuardrailAssessment: The validation result
        """
        client = self.get_guardrail_client(guardrail_name)
        return client.validate_output_content(content)
    
    def filter_content_safely(
        self,
        content: str,
        source: str = "INPUT",
        guardrail_name: str = "autoninja-default"
    ) -> str:
        """
        Filter content safely, returning filtered version or blocking message.
        
        Args:
            content: The content to filter
            source: The source of the content (INPUT or OUTPUT)
            guardrail_name: The name of the guardrail to use
            
        Returns:
            str: The filtered content
        """
        client = self.get_guardrail_client(guardrail_name)
        return client.get_filtered_content(content, source)
    
    def is_content_compliant(
        self,
        content: str,
        source: str = "INPUT",
        guardrail_name: str = "autoninja-default"
    ) -> bool:
        """
        Check if content is compliant with guardrails.
        
        Args:
            content: The content to check
            source: The source of the content
            guardrail_name: The name of the guardrail to use
            
        Returns:
            bool: True if content is compliant, False otherwise
        """
        client = self.get_guardrail_client(guardrail_name)
        return client.is_content_safe(content, source)
    
    def get_compliance_report(
        self,
        content: str,
        source: str = "INPUT",
        guardrail_name: str = "autoninja-default"
    ) -> Dict[str, Any]:
        """
        Get a detailed compliance report for content.
        
        Args:
            content: The content to analyze
            source: The source of the content
            guardrail_name: The name of the guardrail to use
            
        Returns:
            Dict containing detailed compliance information
        """
        client = self.get_guardrail_client(guardrail_name)
        assessment = client.apply_guardrail(content, source)
        
        report = {
            'compliant': assessment.action == GuardrailAction.ALLOWED,
            'action_taken': assessment.action.value,
            'assessment_details': client.get_assessment_details(assessment),
            'filtered_content_available': assessment.filtered_content is not None,
            'usage_metrics': assessment.usage,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return report


# Global guardrails manager instance
_guardrails_manager: Optional[GuardrailsManager] = None


def get_guardrails_manager() -> GuardrailsManager:
    """
    Get the global guardrails manager instance.
    
    Returns:
        GuardrailsManager: The global manager instance
    """
    global _guardrails_manager
    
    if _guardrails_manager is None:
        _guardrails_manager = GuardrailsManager()
    
    return _guardrails_manager


def reset_guardrails_manager():
    """Reset the global guardrails manager instance (mainly for testing)."""
    global _guardrails_manager
    _guardrails_manager = None


# Convenience functions for common operations
def validate_input(content: str) -> bool:
    """Validate input content using default guardrails."""
    manager = get_guardrails_manager()
    return manager.is_content_compliant(content, source="INPUT")


def validate_output(content: str) -> bool:
    """Validate output content using default guardrails."""
    manager = get_guardrails_manager()
    return manager.is_content_compliant(content, source="OUTPUT")


def filter_content(content: str, source: str = "INPUT") -> str:
    """Filter content using default guardrails."""
    manager = get_guardrails_manager()
    return manager.filter_content_safely(content, source)


def get_compliance_report(content: str, source: str = "INPUT") -> Dict[str, Any]:
    """Get compliance report using default guardrails."""
    manager = get_guardrails_manager()
    return manager.get_compliance_report(content, source)