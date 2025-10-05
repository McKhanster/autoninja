"""
Unit tests for Bedrock Guardrails integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from autoninja.core.guardrails import (
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


class TestGuardrailConfig:
    """Test cases for GuardrailConfig."""
    
    def test_config_initialization(self):
        """Test guardrail configuration initialization."""
        config = GuardrailConfig(
            guardrail_id="test-guardrail",
            guardrail_version="1"
        )
        
        assert config.guardrail_id == "test-guardrail"
        assert config.guardrail_version == "1"
        assert config.region_name == "us-east-2"
        assert config.content_filters == []
        assert config.pii_filters == []
        assert config.topic_filters == []
        assert config.word_filters == []
    
    def test_config_with_filters(self):
        """Test configuration with various filters."""
        content_filters = [
            ContentFilter(ContentFilterType.HATE, FilterStrength.HIGH),
            ContentFilter(ContentFilterType.VIOLENCE, FilterStrength.MEDIUM)
        ]
        
        pii_filters = [
            PIIFilter([PIIEntityType.SSN, PIIEntityType.EMAIL], action="BLOCK")
        ]
        
        topic_filters = [
            TopicFilter(
                name="malicious_code",
                definition="Harmful code",
                examples=["malware"],
                action="BLOCK"
            )
        ]
        
        config = GuardrailConfig(
            guardrail_id="test-guardrail",
            content_filters=content_filters,
            pii_filters=pii_filters,
            topic_filters=topic_filters
        )
        
        assert len(config.content_filters) == 2
        assert len(config.pii_filters) == 1
        assert len(config.topic_filters) == 1
        assert config.content_filters[0].filter_type == ContentFilterType.HATE
        assert config.pii_filters[0].entity_types == [PIIEntityType.SSN, PIIEntityType.EMAIL]


class TestBedrockGuardrailsClient:
    """Test cases for BedrockGuardrailsClient."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = GuardrailConfig(
            guardrail_id="test-guardrail",
            guardrail_version="1"
        )
    
    @patch('boto3.client')
    def test_client_initialization(self, mock_boto_client):
        """Test client initialization."""
        mock_bedrock_runtime = Mock()
        mock_bedrock = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, mock_bedrock]
        
        client = BedrockGuardrailsClient(self.config)
        
        assert client.config == self.config
        assert mock_boto_client.call_count == 2
    
    @patch('boto3.client')
    def test_apply_guardrail_allowed(self, mock_boto_client):
        """Test applying guardrail with allowed content."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        # Mock allowed response
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [{'text': 'Clean content'}],
            'assessments': [],
            'usage': {'topicPolicyUnits': 1, 'contentPolicyUnits': 1}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        client = BedrockGuardrailsClient(self.config)
        assessment = client.apply_guardrail("This is clean content", "INPUT")
        
        assert assessment.action == GuardrailAction.ALLOWED
        assert assessment.filtered_content == 'Clean content'
        assert assessment.usage['topicPolicyUnits'] == 1
        
        # Verify API call
        mock_bedrock_runtime.apply_guardrail.assert_called_once_with(
            guardrailIdentifier="test-guardrail",
            guardrailVersion="1",
            source="INPUT",
            content=[{'text': {'text': 'This is clean content'}}]
        )
    
    @patch('boto3.client')
    def test_apply_guardrail_blocked(self, mock_boto_client):
        """Test applying guardrail with blocked content."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        # Mock blocked response
        mock_response = {
            'action': 'BLOCKED',
            'outputs': [],
            'assessments': [
                {
                    'contentPolicy': {
                        'filters': [
                            {
                                'type': 'HATE',
                                'confidence': 'HIGH',
                                'action': 'BLOCKED'
                            }
                        ]
                    }
                }
            ],
            'usage': {'topicPolicyUnits': 1, 'contentPolicyUnits': 1}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        client = BedrockGuardrailsClient(self.config)
        assessment = client.apply_guardrail("Harmful content", "INPUT")
        
        assert assessment.action == GuardrailAction.BLOCKED
        assert assessment.filtered_content is None
        assert len(assessment.assessments) == 1
    
    @patch('boto3.client')
    def test_validate_input_content(self, mock_boto_client):
        """Test input content validation."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        client = BedrockGuardrailsClient(self.config)
        assessment = client.validate_input_content("Test input")
        
        assert assessment.action == GuardrailAction.ALLOWED
        
        # Verify correct source parameter
        call_args = mock_bedrock_runtime.apply_guardrail.call_args
        assert call_args[1]['source'] == 'INPUT'
    
    @patch('boto3.client')
    def test_validate_output_content(self, mock_boto_client):
        """Test output content validation."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        client = BedrockGuardrailsClient(self.config)
        assessment = client.validate_output_content("Test output")
        
        assert assessment.action == GuardrailAction.ALLOWED
        
        # Verify correct source parameter
        call_args = mock_bedrock_runtime.apply_guardrail.call_args
        assert call_args[1]['source'] == 'OUTPUT'
    
    @patch('boto3.client')
    def test_is_content_safe(self, mock_boto_client):
        """Test content safety check."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        # Test safe content
        mock_response = {'action': 'ALLOWED', 'outputs': [], 'assessments': [], 'usage': {}}
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        client = BedrockGuardrailsClient(self.config)
        assert client.is_content_safe("Safe content") is True
        
        # Test unsafe content
        mock_response = {'action': 'BLOCKED', 'outputs': [], 'assessments': [], 'usage': {}}
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        assert client.is_content_safe("Unsafe content") is False
    
    @patch('boto3.client')
    def test_get_filtered_content(self, mock_boto_client):
        """Test getting filtered content."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        client = BedrockGuardrailsClient(self.config)
        
        # Test allowed content
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [{'text': 'Original content'}],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        result = client.get_filtered_content("Original content")
        assert result == "Original content"
        
        # Test filtered content
        mock_response = {
            'action': 'FILTERED',
            'outputs': [{'text': 'Filtered content'}],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        result = client.get_filtered_content("Content to filter")
        assert result == "Filtered content"
        
        # Test blocked content
        mock_response = {
            'action': 'BLOCKED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        result = client.get_filtered_content("Blocked content")
        assert result == "[CONTENT BLOCKED BY GUARDRAILS]"
    
    @patch('boto3.client')
    def test_get_assessment_details(self, mock_boto_client):
        """Test extracting assessment details."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        client = BedrockGuardrailsClient(self.config)
        
        # Create mock assessment
        assessment = GuardrailAssessment(
            action=GuardrailAction.BLOCKED,
            filtered_content=None,
            assessments=[
                {
                    'contentPolicy': {
                        'filters': [
                            {
                                'type': 'HATE',
                                'confidence': 'HIGH',
                                'action': 'BLOCKED'
                            }
                        ]
                    }
                },
                {
                    'sensitiveInformationPolicy': {
                        'piiEntities': [
                            {
                                'type': 'EMAIL',
                                'match': 'test@example.com',
                                'action': 'BLOCKED'
                            }
                        ]
                    }
                }
            ],
            usage={'contentPolicyUnits': 1}
        )
        
        details = client.get_assessment_details(assessment)
        
        assert details['action'] == 'BLOCKED'
        assert len(details['content_filters']) == 1
        assert details['content_filters'][0]['type'] == 'HATE'
        assert len(details['pii_filters']) == 1
        assert details['pii_filters'][0]['type'] == 'EMAIL'
        assert details['usage']['contentPolicyUnits'] == 1


class TestGuardrailsManager:
    """Test cases for GuardrailsManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_guardrails_manager()
    
    @patch('boto3.client')
    def test_manager_initialization(self, mock_boto_client):
        """Test manager initialization with default guardrails."""
        mock_boto_client.return_value = Mock()
        
        manager = GuardrailsManager()
        
        # Should have default guardrail registered
        assert "autoninja-default" in manager._guardrail_configs
        assert "autoninja-default" in manager._clients
        
        # Check default configuration
        default_config = manager._guardrail_configs["autoninja-default"]
        assert default_config.guardrail_id == "autoninja-content-filter"
        assert len(default_config.content_filters) > 0
        assert len(default_config.pii_filters) > 0
        assert len(default_config.topic_filters) > 0
    
    @patch('boto3.client')
    def test_register_guardrail(self, mock_boto_client):
        """Test registering a new guardrail configuration."""
        mock_boto_client.return_value = Mock()
        
        manager = GuardrailsManager()
        
        custom_config = GuardrailConfig(
            guardrail_id="custom-guardrail",
            guardrail_version="2"
        )
        
        manager.register_guardrail("custom", custom_config)
        
        assert "custom" in manager._guardrail_configs
        assert "custom" in manager._clients
        assert manager._guardrail_configs["custom"] == custom_config
    
    @patch('boto3.client')
    def test_get_guardrail_client(self, mock_boto_client):
        """Test getting guardrail client."""
        mock_boto_client.return_value = Mock()
        
        manager = GuardrailsManager()
        
        # Test getting default client
        client = manager.get_guardrail_client()
        assert client is not None
        
        # Test getting specific client
        client = manager.get_guardrail_client("autoninja-default")
        assert client is not None
        
        # Test getting non-existent client
        with pytest.raises(ValueError, match="Guardrail configuration not found"):
            manager.get_guardrail_client("non-existent")
    
    @patch('boto3.client')
    def test_validate_agent_input(self, mock_boto_client):
        """Test validating agent input."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        manager = GuardrailsManager()
        assessment = manager.validate_agent_input("Test input")
        
        assert assessment.action == GuardrailAction.ALLOWED
    
    @patch('boto3.client')
    def test_validate_agent_output(self, mock_boto_client):
        """Test validating agent output."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        manager = GuardrailsManager()
        assessment = manager.validate_agent_output("Test output")
        
        assert assessment.action == GuardrailAction.ALLOWED
    
    @patch('boto3.client')
    def test_filter_content_safely(self, mock_boto_client):
        """Test filtering content safely."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'FILTERED',
            'outputs': [{'text': 'Filtered content'}],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        manager = GuardrailsManager()
        result = manager.filter_content_safely("Content to filter")
        
        assert result == "Filtered content"
    
    @patch('boto3.client')
    def test_is_content_compliant(self, mock_boto_client):
        """Test checking content compliance."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        manager = GuardrailsManager()
        result = manager.is_content_compliant("Compliant content")
        
        assert result is True
    
    @patch('boto3.client')
    def test_get_compliance_report(self, mock_boto_client):
        """Test getting compliance report."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {'contentPolicyUnits': 1}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        manager = GuardrailsManager()
        report = manager.get_compliance_report("Test content")
        
        assert report['compliant'] is True
        assert report['action_taken'] == 'ALLOWED'
        assert 'assessment_details' in report
        assert 'usage_metrics' in report
        assert 'timestamp' in report


class TestGlobalFunctions:
    """Test cases for global convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_guardrails_manager()
    
    @patch('boto3.client')
    def test_validate_input(self, mock_boto_client):
        """Test global validate_input function."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        result = validate_input("Test input")
        assert result is True
    
    @patch('boto3.client')
    def test_validate_output(self, mock_boto_client):
        """Test global validate_output function."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        result = validate_output("Test output")
        assert result is True
    
    @patch('boto3.client')
    def test_filter_content(self, mock_boto_client):
        """Test global filter_content function."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [{'text': 'Clean content'}],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        result = filter_content("Clean content")
        assert result == "Clean content"
    
    @patch('boto3.client')
    def test_get_compliance_report_global(self, mock_boto_client):
        """Test global get_compliance_report function."""
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_runtime, Mock()]
        
        mock_response = {
            'action': 'ALLOWED',
            'outputs': [],
            'assessments': [],
            'usage': {}
        }
        mock_bedrock_runtime.apply_guardrail.return_value = mock_response
        
        report = get_compliance_report("Test content")
        assert report['compliant'] is True
    
    @patch('boto3.client')
    def test_get_guardrails_manager_singleton(self, mock_boto_client):
        """Test that get_guardrails_manager returns singleton."""
        mock_boto_client.return_value = Mock()
        
        manager1 = get_guardrails_manager()
        manager2 = get_guardrails_manager()
        
        assert manager1 is manager2
    
    @patch('boto3.client')
    def test_reset_guardrails_manager(self, mock_boto_client):
        """Test resetting the global manager."""
        mock_boto_client.return_value = Mock()
        
        manager1 = get_guardrails_manager()
        reset_guardrails_manager()
        manager2 = get_guardrails_manager()
        
        assert manager1 is not manager2


if __name__ == '__main__':
    pytest.main([__file__])