"""
Unit tests for Bedrock Knowledge Base integration.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from autoninja.core.knowledge_base import (
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


class TestBedrockKnowledgeBaseClient:
    """Test cases for BedrockKnowledgeBaseClient."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_knowledge_base_client()
        self.config = KnowledgeBaseConfig(region_name="us-east-2")
    
    @patch('boto3.client')
    def test_client_initialization(self, mock_boto_client):
        """Test client initialization."""
        mock_bedrock_agent = Mock()
        mock_bedrock_runtime = Mock()
        mock_boto_client.side_effect = [mock_bedrock_agent, mock_bedrock_runtime]
        
        client = BedrockKnowledgeBaseClient(self.config)
        
        assert client.config == self.config
        assert mock_boto_client.call_count == 2
    
    def test_get_knowledge_base_id(self):
        """Test getting knowledge base ID."""
        with patch('boto3.client'):
            client = BedrockKnowledgeBaseClient(self.config)
            
            # Test valid knowledge base type
            kb_id = client.get_knowledge_base_id(KnowledgeBaseType.REQUIREMENTS_PATTERNS)
            assert kb_id == "requirements-patterns-kb-id"
            
            # Test that all KB types are mapped
            for kb_type in KnowledgeBaseType:
                kb_id = client.get_knowledge_base_id(kb_type)
                assert kb_id is not None
    
    @patch('boto3.client')
    def test_search_knowledge_base(self, mock_boto_client):
        """Test knowledge base search functionality."""
        mock_runtime_client = Mock()
        mock_boto_client.side_effect = [Mock(), mock_runtime_client]
        
        # Mock the retrieve response
        mock_response = {
            'retrievalResults': [
                {
                    'score': 0.85,
                    'content': {'text': 'Test pattern content'},
                    'metadata': {
                        'document_id': 'test-doc-1',
                        'title': 'Test Pattern',
                        'pattern_type': 'requirements'
                    }
                },
                {
                    'score': 0.6,  # Below threshold
                    'content': {'text': 'Low relevance content'},
                    'metadata': {
                        'document_id': 'test-doc-2',
                        'title': 'Low Relevance'
                    }
                }
            ]
        }
        mock_runtime_client.retrieve.return_value = mock_response
        
        client = BedrockKnowledgeBaseClient(self.config)
        
        results = client.search_knowledge_base(
            kb_type=KnowledgeBaseType.REQUIREMENTS_PATTERNS,
            query="test query",
            similarity_threshold=0.7
        )
        
        # Should only return results above threshold
        assert len(results) == 1
        assert results[0].document_id == 'test-doc-1'
        assert results[0].relevance_score == 0.85
        assert results[0].title == 'Test Pattern'
        
        # Verify API call
        mock_runtime_client.retrieve.assert_called_once()
    
    @patch('boto3.client')
    def test_retrieve_and_generate(self, mock_boto_client):
        """Test retrieve and generate functionality."""
        mock_runtime_client = Mock()
        mock_boto_client.side_effect = [Mock(), mock_runtime_client]
        
        # Mock the retrieve_and_generate response
        mock_response = {
            'output': {'text': 'Generated response based on knowledge base'},
            'sessionId': 'test-session-123',
            'citations': [
                {
                    'retrievedReferences': [
                        {
                            'content': {'text': 'Source document content'},
                            'metadata': {'source': 'kb-document'},
                            'location': {'s3Location': {'uri': 's3://bucket/doc'}},
                            'score': 0.9
                        }
                    ]
                }
            ]
        }
        mock_runtime_client.retrieve_and_generate.return_value = mock_response
        
        client = BedrockKnowledgeBaseClient(self.config)
        
        result = client.retrieve_and_generate(
            kb_type=KnowledgeBaseType.ARCHITECTURE_PATTERNS,
            query="design microservices architecture"
        )
        
        assert result['generated_text'] == 'Generated response based on knowledge base'
        assert result['session_id'] == 'test-session-123'
        assert len(result['source_documents']) == 1
        assert result['source_documents'][0]['score'] == 0.9
        
        # Verify API call
        mock_runtime_client.retrieve_and_generate.assert_called_once()
    
    @patch('boto3.client')
    def test_find_similar_patterns(self, mock_boto_client):
        """Test finding similar patterns."""
        mock_runtime_client = Mock()
        mock_boto_client.side_effect = [Mock(), mock_runtime_client]
        
        mock_response = {
            'retrievalResults': [
                {
                    'score': 0.9,
                    'content': {'text': 'Similar pattern'},
                    'metadata': {'document_id': 'similar-1', 'title': 'Similar Pattern'}
                }
            ]
        }
        mock_runtime_client.retrieve.return_value = mock_response
        
        client = BedrockKnowledgeBaseClient(self.config)
        
        results = client.find_similar_patterns(
            kb_type=KnowledgeBaseType.CODE_TEMPLATES,
            pattern_content="lambda function template",
            similarity_threshold=0.8
        )
        
        assert len(results) == 1
        assert results[0].relevance_score == 0.9
    
    @patch('boto3.client')
    def test_get_pattern_recommendations(self, mock_boto_client):
        """Test getting pattern recommendations."""
        mock_runtime_client = Mock()
        mock_boto_client.side_effect = [Mock(), mock_runtime_client]
        
        mock_response = {
            'retrievalResults': [
                {
                    'score': 0.85,
                    'content': {'text': 'Recommended pattern'},
                    'metadata': {'document_id': 'rec-1', 'title': 'Recommendation'}
                }
            ]
        }
        mock_runtime_client.retrieve.return_value = mock_response
        
        client = BedrockKnowledgeBaseClient(self.config)
        
        context = {
            'agent_type': 'conversational',
            'requirements': ['natural language processing', 'customer support'],
            'domain': 'customer service',
            'complexity': 'medium'
        }
        
        results = client.get_pattern_recommendations(
            kb_type=KnowledgeBaseType.REQUIREMENTS_PATTERNS,
            context=context,
            max_recommendations=3
        )
        
        assert len(results) == 1
        assert results[0].title == 'Recommendation'


class TestDynamicPatternManager:
    """Test cases for DynamicPatternManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('boto3.client'):
            self.kb_client = BedrockKnowledgeBaseClient()
            self.pattern_manager = DynamicPatternManager(self.kb_client)
    
    def test_extract_patterns_from_generation(self):
        """Test pattern extraction from generation results."""
        generation_result = {
            'requirements': {
                'agent_type': 'conversational',
                'functional': ['handle customer queries', 'provide support'],
                'non_functional': {'performance': {'response_time': '< 2s'}},
                'compliance': ['GDPR'],
                'success_criteria': ['95% accuracy']
            },
            'architecture': {
                'pattern_name': 'customer-support-bot',
                'services': ['bedrock', 'lambda', 'dynamodb'],
                'configuration': {'memory': '512MB'},
                'security': {'encryption': 'AES-256'},
                'integrations': ['api-gateway'],
                'cost_optimization': {'reserved_capacity': True}
            },
            'generated_code': {
                'lambda_handler': {
                    'content': 'def lambda_handler(event, context): pass',
                    'language': 'python',
                    'framework': 'boto3',
                    'dependencies': ['boto3', 'json']
                }
            }
        }
        
        patterns = self.pattern_manager.extract_patterns_from_generation(generation_result)
        
        # Should extract requirements, architecture, and code patterns
        assert len(patterns) >= 3
        
        # Check requirements pattern
        req_pattern = next((p for p in patterns if 'requirements' in p.title.lower()), None)
        assert req_pattern is not None
        assert req_pattern.document_type == DocumentType.PATTERN
        assert 'requirements' in req_pattern.tags
        
        # Check architecture pattern
        arch_pattern = next((p for p in patterns if 'architecture' in p.title.lower()), None)
        assert arch_pattern is not None
        assert arch_pattern.document_type == DocumentType.PATTERN
        assert 'architecture' in arch_pattern.tags
        
        # Check code template
        code_template = next((p for p in patterns if 'lambda_handler' in p.title.lower()), None)
        assert code_template is not None
        assert code_template.document_type == DocumentType.TEMPLATE
        assert 'code' in code_template.tags
    
    @patch('boto3.client')
    def test_store_pattern_in_s3(self, mock_boto_client):
        """Test storing patterns in S3."""
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        
        # Create the pattern manager with mocked S3 client
        self.pattern_manager._s3_client = mock_s3_client
        
        document = KnowledgeBaseDocument(
            document_id="test-doc-123",
            title="Test Pattern",
            content="Test pattern content",
            document_type=DocumentType.PATTERN,
            metadata={'pattern_type': 'test'},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=['test', 'pattern'],
            confidence_score=0.8
        )
        
        s3_uri = self.pattern_manager.store_pattern_in_s3(document)
        
        # Verify S3 put_object was called
        mock_s3_client.put_object.assert_called_once()
        
        # Verify S3 URI format
        assert s3_uri.startswith('s3://autoninja-dynamic-patterns/patterns/')
        assert 'test-doc-123.json' in s3_uri
    
    def test_update_pattern_usage(self):
        """Test updating pattern usage statistics."""
        # This is a simple test since the method currently just logs
        self.pattern_manager.update_pattern_usage(
            "test-doc-123",
            KnowledgeBaseType.REQUIREMENTS_PATTERNS
        )
        
        # No assertion needed as this method currently just logs
        # In a full implementation, this would test database updates


class TestGlobalFunctions:
    """Test cases for global functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_knowledge_base_client()
    
    @patch('boto3.client')
    def test_get_knowledge_base_client_singleton(self, mock_boto_client):
        """Test that get_knowledge_base_client returns singleton."""
        mock_boto_client.return_value = Mock()
        
        client1 = get_knowledge_base_client()
        client2 = get_knowledge_base_client()
        
        assert client1 is client2
    
    @patch('boto3.client')
    def test_reset_knowledge_base_client(self, mock_boto_client):
        """Test resetting the global client."""
        mock_boto_client.return_value = Mock()
        
        client1 = get_knowledge_base_client()
        reset_knowledge_base_client()
        client2 = get_knowledge_base_client()
        
        assert client1 is not client2


if __name__ == '__main__':
    pytest.main([__file__])