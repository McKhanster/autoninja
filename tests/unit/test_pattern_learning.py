"""
Unit tests for the pattern learning system
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from dataclasses import asdict
import json

from autoninja.core.pattern_learning import (
    Pattern, GenerationResult, PatternExtractor, SimilarityDetector,
    PatternRefiner, PatternLearningSystem, DynamoDBPatternStorage
)


class TestPatternExtractor:
    """Test pattern extraction functionality"""
    
    def setup_method(self):
        self.extractor = PatternExtractor()
        self.sample_generation = GenerationResult(
            generation_id="test-gen-001",
            agent_type="conversational",
            user_request={
                "description": "Create a customer support chatbot",
                "agent_type": "conversational"
            },
            requirements={
                "functional_requirements": {
                    "chat_interface": True,
                    "knowledge_base": True,
                    "escalation": True
                },
                "non_functional_requirements": {
                    "response_time": "< 2 seconds",
                    "availability": "99.9%"
                },
                "compliance_requirements": {
                    "gdpr": True,
                    "data_retention": "30 days"
                }
            },
            architecture={
                "aws_services": {
                    "services": ["bedrock", "lambda", "api_gateway", "dynamodb"],
                    "bedrock_models": ["claude-3-sonnet"]
                },
                "security_architecture": {
                    "encryption": "AES-256",
                    "authentication": "API_KEY",
                    "security_features": ["encryption", "authentication", "logging"]
                },
                "integrations": {
                    "external_apis": ["crm_system"],
                    "internal_services": ["user_management"]
                }
            },
            generated_code={
                "lambda_functions": {
                    "chat_handler": {
                        "runtime": "python3.9",
                        "code": "import boto3\ndef lambda_handler(event, context):\n    return {'statusCode': 200}"
                    }
                },
                "api_gateway": {
                    "endpoints": ["/chat", "/health"],
                    "methods": ["POST", "GET"]
                },
                "cloudformation": {
                    "template": "AWSTemplateFormatVersion: '2010-09-09'"
                }
            },
            validation_results={
                "overall_score": 0.95,
                "code_quality": 0.9,
                "security_score": 0.98
            },
            deployment_config={
                "environment": "production",
                "region": "us-east-1"
            },
            success_metrics={
                "deployment_success": True,
                "performance_score": 0.92
            },
            timestamp=datetime.now(timezone.utc)
        )
    
    def test_extract_requirements_patterns(self):
        """Test extraction of requirements patterns"""
        patterns = self.extractor.extract_requirements_patterns(self.sample_generation)
        
        assert len(patterns) == 3  # functional, non-functional, compliance
        
        # Check functional requirements pattern
        functional_pattern = next(p for p in patterns 
                                if p.metadata['pattern_subtype'] == 'functional_requirements')
        assert functional_pattern.pattern_type == 'requirements'
        assert 'chat_interface' in functional_pattern.content['requirements_structure']
        assert functional_pattern.content['context']['domain'] == 'customer_service'
        
        # Check compliance pattern
        compliance_pattern = next(p for p in patterns 
                                if p.metadata['pattern_subtype'] == 'compliance_requirements')
        assert compliance_pattern.pattern_type == 'requirements'
        assert 'gdpr' in compliance_pattern.content['requirements_structure']
    
    def test_extract_architecture_patterns(self):
        """Test extraction of architecture patterns"""
        patterns = self.extractor.extract_architecture_patterns(self.sample_generation)
        
        assert len(patterns) == 3  # service_composition, security_architecture, integration_patterns
        
        # Check service composition pattern
        service_pattern = next(p for p in patterns 
                             if p.metadata['pattern_subtype'] == 'service_composition')
        assert service_pattern.pattern_type == 'architecture'
        assert 'bedrock' in service_pattern.content['architecture_components']['services']
        assert service_pattern.content['context']['scale'] == 'small'
    
    def test_extract_code_patterns(self):
        """Test extraction of code patterns"""
        patterns = self.extractor.extract_code_patterns(self.sample_generation)
        
        assert len(patterns) == 3  # lambda_function, api_gateway, cloudformation_template
        
        # Check Lambda function pattern
        lambda_pattern = next(p for p in patterns 
                            if p.metadata['pattern_subtype'] == 'lambda_function')
        assert lambda_pattern.pattern_type == 'code'
        assert lambda_pattern.content['component_name'] == 'chat_handler'
        assert lambda_pattern.content['context']['language'] == 'python'
    
    def test_domain_extraction(self):
        """Test domain extraction from user requests"""
        # Customer service domain
        domain = self.extractor._extract_domain({
            'description': 'Create a customer support chatbot'
        })
        assert domain == 'customer_service'
        
        # Data analytics domain
        domain = self.extractor._extract_domain({
            'description': 'Build a data analysis dashboard'
        })
        assert domain == 'data_analytics'
        
        # Automation domain
        domain = self.extractor._extract_domain({
            'description': 'Automate workflow processes'
        })
        assert domain == 'automation'
        
        # General domain
        domain = self.extractor._extract_domain({
            'description': 'Some other type of agent'
        })
        assert domain == 'general'
    
    def test_complexity_assessment(self):
        """Test complexity assessment"""
        # Low complexity
        complexity = self.extractor._assess_complexity({'simple': 'requirement'})
        assert complexity == 'low'
        
        # High complexity (large content)
        large_content = {'requirements': 'x' * 3000}
        complexity = self.extractor._assess_complexity(large_content)
        assert complexity == 'high'
    
    def test_aws_services_extraction(self):
        """Test AWS services extraction from code"""
        code_content = {
            'code': 'import boto3\nclient = boto3.client("dynamodb")\ns3_bucket = "my-bucket"'
        }
        services = self.extractor._extract_aws_services(code_content)
        assert 'dynamodb' in services
        assert 's3' in services


class TestSimilarityDetector:
    """Test similarity detection functionality"""
    
    def setup_method(self):
        self.detector = SimilarityDetector(similarity_threshold=0.7)
        
        # Create sample patterns
        self.pattern1 = Pattern(
            pattern_id="pattern1",
            pattern_type="requirements",
            content={
                "pattern_subtype": "functional_requirements",
                "requirements_structure": {
                    "chat_interface": True,
                    "knowledge_base": True
                }
            },
            metadata={
                "pattern_subtype": "functional_requirements",
                "source_agent_type": "conversational"
            },
            confidence_score=0.9,
            usage_count=5,
            success_rate=0.95,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            last_refined=datetime.now(timezone.utc),
            source_generations=["gen1", "gen2"]
        )
        
        self.pattern2 = Pattern(
            pattern_id="pattern2",
            pattern_type="requirements",
            content={
                "pattern_subtype": "functional_requirements",
                "requirements_structure": {
                    "chat_interface": True,
                    "knowledge_base": True,
                    "escalation": True
                }
            },
            metadata={
                "pattern_subtype": "functional_requirements",
                "source_agent_type": "conversational"
            },
            confidence_score=0.85,
            usage_count=3,
            success_rate=0.9,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            last_refined=datetime.now(timezone.utc),
            source_generations=["gen3"]
        )
        
        self.pattern3 = Pattern(
            pattern_id="pattern3",
            pattern_type="architecture",  # Different type
            content={
                "pattern_subtype": "service_composition",
                "architecture_components": {
                    "services": ["bedrock", "lambda"]
                }
            },
            metadata={
                "pattern_subtype": "service_composition",
                "source_agent_type": "conversational"
            },
            confidence_score=0.8,
            usage_count=2,
            success_rate=0.85,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            last_refined=datetime.now(timezone.utc),
            source_generations=["gen4"]
        )
    
    def test_find_similar_patterns(self):
        """Test finding similar patterns"""
        existing_patterns = [self.pattern2, self.pattern3]
        similar_patterns = self.detector.find_similar_patterns(self.pattern1, existing_patterns)
        
        # Should find pattern2 as similar (same type and similar content)
        assert len(similar_patterns) == 1
        assert similar_patterns[0][0].pattern_id == "pattern2"
        assert similar_patterns[0][1] > 0.7  # High similarity score
    
    def test_content_similarity(self):
        """Test content similarity calculation"""
        similarity = self.detector._calculate_content_similarity(
            self.pattern1.content, self.pattern2.content
        )
        assert similarity > 0.7  # Should be similar
        
        similarity = self.detector._calculate_content_similarity(
            self.pattern1.content, self.pattern3.content
        )
        assert similarity < 0.5  # Should be different
    
    def test_metadata_similarity(self):
        """Test metadata similarity calculation"""
        similarity = self.detector._calculate_metadata_similarity(
            self.pattern1.metadata, self.pattern2.metadata
        )
        assert similarity > 0.8  # Should be very similar
        
        similarity = self.detector._calculate_metadata_similarity(
            self.pattern1.metadata, self.pattern3.metadata
        )
        assert similarity < 0.7  # Different subtypes


class TestPatternRefiner:
    """Test pattern refinement functionality"""
    
    def setup_method(self):
        self.refiner = PatternRefiner()
        self.sample_pattern = Pattern(
            pattern_id="test_pattern",
            pattern_type="requirements",
            content={
                "pattern_subtype": "functional_requirements",
                "requirements_structure": {"chat_interface": True}
            },
            metadata={
                "pattern_subtype": "functional_requirements",
                "source_agent_type": "conversational"
            },
            confidence_score=0.8,
            usage_count=2,
            success_rate=0.9,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            last_refined=datetime.now(timezone.utc),
            source_generations=["gen1"]
        )
    
    def test_refine_pattern_success(self):
        """Test pattern refinement with successful usage"""
        usage_feedback = {
            'success': True,
            'improvements': {
                'add_components': ['new_feature']
            }
        }
        
        original_usage_count = self.sample_pattern.usage_count
        original_success_rate = self.sample_pattern.success_rate
        
        refined_pattern = self.refiner.refine_pattern(self.sample_pattern, usage_feedback)
        
        # Check updated statistics
        assert refined_pattern.usage_count == original_usage_count + 1
        assert refined_pattern.success_rate >= original_success_rate
        assert refined_pattern.confidence_score > 0
    
    def test_refine_pattern_failure(self):
        """Test pattern refinement with failed usage"""
        usage_feedback = {
            'success': False
        }
        
        original_success_rate = self.sample_pattern.success_rate
        
        refined_pattern = self.refiner.refine_pattern(self.sample_pattern, usage_feedback)
        
        # Success rate should decrease
        assert refined_pattern.success_rate < original_success_rate
    
    def test_merge_similar_patterns(self):
        """Test merging of similar patterns"""
        pattern2 = Pattern(
            pattern_id="pattern2",
            pattern_type="requirements",
            content={"pattern_subtype": "functional_requirements"},
            metadata={"pattern_subtype": "functional_requirements"},
            confidence_score=0.7,
            usage_count=3,
            success_rate=0.8,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            last_refined=datetime.now(timezone.utc),
            source_generations=["gen2", "gen3"]
        )
        
        merged_pattern = self.refiner.merge_similar_patterns(self.sample_pattern, pattern2)
        
        # Check merged statistics
        assert merged_pattern.usage_count == 5  # 2 + 3
        assert merged_pattern.pattern_id == self.sample_pattern.pattern_id
        assert len(merged_pattern.source_generations) == 3  # gen1, gen2, gen3
        assert merged_pattern.confidence_score == max(0.8, 0.7)
    
    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        # High usage, high success
        self.sample_pattern.usage_count = 10
        self.sample_pattern.success_rate = 0.95
        confidence = self.refiner._calculate_confidence_score(self.sample_pattern)
        assert confidence > 0.8
        
        # Low usage, low success
        self.sample_pattern.usage_count = 1
        self.sample_pattern.success_rate = 0.5
        confidence = self.refiner._calculate_confidence_score(self.sample_pattern)
        assert confidence < 0.6


class TestPatternLearningSystem:
    """Test the complete pattern learning system"""
    
    def setup_method(self):
        self.mock_storage = Mock()
        self.mock_kb_client = Mock()
        self.system = PatternLearningSystem(self.mock_storage, self.mock_kb_client)
        
        self.sample_generation = GenerationResult(
            generation_id="test-gen-001",
            agent_type="conversational",
            user_request={"description": "Create a chatbot"},
            requirements={"functional_requirements": {"chat": True}},
            architecture={"aws_services": {"services": ["bedrock"]}},
            generated_code={"lambda_functions": {"handler": {"code": "test"}}},
            validation_results={"overall_score": 0.9},
            deployment_config={},
            success_metrics={"deployment_success": True},
            timestamp=datetime.now(timezone.utc)
        )
    
    @patch('autoninja.core.pattern_learning.PatternLearningSystem._get_existing_patterns')
    @patch('autoninja.core.pattern_learning.PatternLearningSystem._store_pattern')
    def test_learn_from_generation_new_patterns(self, mock_store, mock_get_existing):
        """Test learning from generation with new patterns"""
        mock_get_existing.return_value = []  # No existing patterns
        
        patterns = self.system.learn_from_generation(self.sample_generation)
        
        # Should extract and store multiple patterns
        assert len(patterns) > 0
        assert mock_store.call_count > 0
    
    @patch('autoninja.core.pattern_learning.PatternLearningSystem._get_existing_patterns')
    @patch('autoninja.core.pattern_learning.PatternLearningSystem._store_pattern')
    @patch('autoninja.core.pattern_learning.PatternLearningSystem._remove_pattern')
    def test_learn_from_generation_similar_patterns(self, mock_remove, mock_store, mock_get_existing):
        """Test learning from generation with similar existing patterns"""
        # Mock existing similar pattern
        existing_pattern = Pattern(
            pattern_id="existing",
            pattern_type="requirements",
            content={"pattern_subtype": "functional_requirements"},
            metadata={"pattern_subtype": "functional_requirements"},
            confidence_score=0.8,
            usage_count=1,
            success_rate=0.9,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            last_refined=datetime.now(timezone.utc),
            source_generations=["gen1"]
        )
        mock_get_existing.return_value = [existing_pattern]
        
        patterns = self.system.learn_from_generation(self.sample_generation)
        
        # Should merge patterns and remove old one
        assert len(patterns) > 0
        assert mock_store.call_count > 0
        assert mock_remove.call_count > 0
    
    def test_get_relevant_patterns(self):
        """Test getting relevant patterns for a context"""
        # Mock storage response
        mock_pattern_data = {
            'pattern_id': 'test',
            'pattern_type': 'requirements',
            'content': {},
            'metadata': {'source_agent_type': 'conversational'},
            'confidence_score': 0.8,
            'usage_count': 1,
            'success_rate': 0.9,
            'created_at': datetime.now(timezone.utc),
            'last_used': datetime.now(timezone.utc),
            'last_refined': datetime.now(timezone.utc),
            'source_generations': []
        }
        
        self.mock_storage.query_items.return_value = [
            {'pattern_data': json.dumps(mock_pattern_data, default=str)}
        ]
        
        context = {
            'pattern_type': 'requirements',
            'agent_type': 'conversational',
            'min_confidence': 0.7
        }
        
        patterns = self.system.get_relevant_patterns(context)
        
        assert len(patterns) == 1
        assert patterns[0].pattern_id == 'test'
    
    def test_update_pattern_feedback(self):
        """Test updating pattern with feedback"""
        # Mock pattern retrieval
        mock_pattern_data = {
            'pattern_id': 'test',
            'pattern_type': 'requirements',
            'content': {},
            'metadata': {},
            'confidence_score': 0.8,
            'usage_count': 1,
            'success_rate': 0.9,
            'created_at': datetime.now(timezone.utc),
            'last_used': datetime.now(timezone.utc),
            'last_refined': datetime.now(timezone.utc),
            'source_generations': []
        }
        
        self.mock_storage.get_item.return_value = {
            'pattern_data': json.dumps(mock_pattern_data, default=str)
        }
        
        feedback = {'success': True}
        updated_pattern = self.system.update_pattern_feedback('test', feedback)
        
        assert updated_pattern is not None
        assert updated_pattern.usage_count == 2  # Should increment
        assert self.mock_storage.put_item.called


if __name__ == '__main__':
    pytest.main([__file__])


class TestTemplateGeneration:
    """Test template generation functionality"""
    
    def setup_method(self):
        from autoninja.core.template_generation import (
            PatternSynthesizer, ContextAwareCustomizer, TemplateValidator,
            TemplateRequest, TemplateType, GeneratedTemplate, TemplateComponent
        )
        
        # Store classes as instance variables for use in tests
        self.GeneratedTemplate = GeneratedTemplate
        self.TemplateComponent = TemplateComponent
        self.TemplateRequest = TemplateRequest
        self.TemplateType = TemplateType
        
        self.synthesizer = PatternSynthesizer()
        self.customizer = ContextAwareCustomizer()
        self.validator = TemplateValidator()
        
        # Create sample template request
        self.template_request = self.TemplateRequest(
            template_type=self.TemplateType.REQUIREMENTS,
            context={
                'agent_type': 'conversational',
                'domain': 'customer_service',
                'complexity': 'medium'
            },
            requirements=['chat_interface', 'knowledge_base', 'escalation'],
            constraints={'budget': 'medium'},
            customization_preferences={'security_level': 'high'}
        )
        
        # Create sample patterns
        self.sample_patterns = [
            Pattern(
                pattern_id="req_pattern_1",
                pattern_type="requirements",
                content={
                    "pattern_subtype": "functional_requirements",
                    "requirements_structure": {
                        "chat_interface": True,
                        "knowledge_base": True,
                        "escalation": True
                    },
                    "context": {
                        "agent_type": "conversational",
                        "domain": "customer_service",
                        "complexity": "medium"
                    }
                },
                metadata={
                    "pattern_subtype": "functional_requirements",
                    "source_agent_type": "conversational"
                },
                confidence_score=0.9,
                usage_count=5,
                success_rate=0.95,
                created_at=datetime.now(timezone.utc),
                last_used=datetime.now(timezone.utc),
                last_refined=datetime.now(timezone.utc),
                source_generations=["gen1", "gen2"]
            ),
            Pattern(
                pattern_id="req_pattern_2",
                pattern_type="requirements",
                content={
                    "pattern_subtype": "functional_requirements",
                    "requirements_structure": {
                        "chat_interface": True,
                        "user_authentication": True
                    },
                    "context": {
                        "agent_type": "conversational",
                        "domain": "general",
                        "complexity": "low"
                    }
                },
                metadata={
                    "pattern_subtype": "functional_requirements",
                    "source_agent_type": "conversational"
                },
                confidence_score=0.8,
                usage_count=3,
                success_rate=0.9,
                created_at=datetime.now(timezone.utc),
                last_used=datetime.now(timezone.utc),
                last_refined=datetime.now(timezone.utc),
                source_generations=["gen3"]
            )
        ]
    
    def test_pattern_synthesizer_filter_relevant_patterns(self):
        """Test filtering of relevant patterns"""
        relevant_patterns = self.synthesizer._filter_relevant_patterns(
            self.sample_patterns, self.template_request
        )
        
        # Should include both patterns (both are requirements type and meet confidence threshold)
        assert len(relevant_patterns) == 2
        
        # Test with higher confidence threshold
        self.synthesizer.min_pattern_confidence = 0.85
        relevant_patterns = self.synthesizer._filter_relevant_patterns(
            self.sample_patterns, self.template_request
        )
        
        # Should only include the first pattern (higher confidence)
        assert len(relevant_patterns) == 1
        assert relevant_patterns[0].pattern_id == "req_pattern_1"
    
    def test_pattern_synthesizer_rank_patterns(self):
        """Test pattern ranking by relevance"""
        ranked_patterns = self.synthesizer._rank_patterns_by_relevance(
            self.sample_patterns, self.template_request
        )
        
        # First pattern should rank higher (better context match)
        assert ranked_patterns[0].pattern_id == "req_pattern_1"
        assert ranked_patterns[1].pattern_id == "req_pattern_2"
    
    def test_synthesize_template(self):
        """Test template synthesis from patterns"""
        template = self.synthesizer.synthesize_template(
            self.sample_patterns, self.template_request
        )
        
        assert isinstance(template, self.GeneratedTemplate)
        assert template.template_type == self.TemplateType.REQUIREMENTS
        assert len(template.components) > 0
        assert template.quality_score > 0
        assert template.confidence_score > 0
        assert len(template.source_patterns) > 0
    
    def test_context_aware_customizer(self):
        """Test context-aware template customization"""
        # Create a basic template
        template = self.GeneratedTemplate(
            template_id="test_template",
            template_type=self.TemplateType.ARCHITECTURE,
            title="Test Template",
            description="Test description",
            components=[
                self.TemplateComponent(
                    component_id="test_component",
                    component_type="service_composition",
                    content={"services": ["lambda", "api_gateway"]},
                    metadata={},
                    weight=0.8,
                    source_patterns=["pattern1"]
                )
            ],
            context={},
            quality_score=0.8,
            confidence_score=0.7,
            created_at=datetime.now(timezone.utc),
            source_patterns=["pattern1"],
            customization_parameters={}
        )
        
        # Test customization
        customization_context = {
            'scale': 'large',
            'environment': 'production',
            'preferences': {
                'security_level': 'high',
                'performance_priority': 'high'
            }
        }
        
        customized_template = self.customizer.customize_template(template, customization_context)
        
        assert customized_template.template_id != template.template_id
        assert 'auto_scaling' in customized_template.components[0].content
        assert 'monitoring' in customized_template.components[0].content
        assert 'security' in customized_template.components[0].content
    
    def test_template_validator(self):
        """Test template validation"""
        # Create a valid template
        template = self.GeneratedTemplate(
            template_id="test_template",
            template_type=self.TemplateType.REQUIREMENTS,
            title="Test Template",
            description="Test description",
            components=[
                self.TemplateComponent(
                    component_id="test_component",
                    component_type="functional_requirements",
                    content={"chat_interface": True},
                    metadata={},
                    weight=0.8,
                    source_patterns=["pattern1"]
                )
            ],
            context={},
            quality_score=0.8,
            confidence_score=0.7,
            created_at=datetime.now(timezone.utc),
            source_patterns=["pattern1"],
            customization_parameters={}
        )
        
        validation_results = self.validator.validate_template(template)
        
        assert 'overall_score' in validation_results
        assert 'component_scores' in validation_results
        assert 'validation_errors' in validation_results
        assert 'validation_warnings' in validation_results
        assert 'recommendations' in validation_results
        
        # Should have a reasonable score for a valid template
        assert validation_results['overall_score'] > 0.5
    
    def test_template_validator_empty_template(self):
        """Test validation of empty template"""
        empty_template = self.GeneratedTemplate(
            template_id="empty_template",
            template_type=self.TemplateType.REQUIREMENTS,
            title="",
            description="",
            components=[],
            context={},
            quality_score=0.0,
            confidence_score=0.0,
            created_at=datetime.now(timezone.utc),
            source_patterns=[],
            customization_parameters={}
        )
        
        validation_results = self.validator.validate_template(empty_template)
        
        # Should have low score and errors
        assert validation_results['overall_score'] < 0.5
        assert len(validation_results['validation_errors']) > 0
        assert len(validation_results['validation_warnings']) > 0


if __name__ == '__main__':
    pytest.main([__file__])


class TestKnowledgeBaseUpdater:
    """Test knowledge base auto-update functionality"""
    
    def setup_method(self):
        from autoninja.core.knowledge_base_updater import (
            PatternVersionManager, KnowledgeBaseOptimizer, KnowledgeBaseUpdateQueue,
            KnowledgeBaseAutoUpdater, KnowledgeBaseUpdate, UpdateType, UpdatePriority
        )
        from autoninja.core.knowledge_base import KnowledgeBaseType
        
        # Store classes as instance variables
        self.PatternVersionManager = PatternVersionManager
        self.KnowledgeBaseOptimizer = KnowledgeBaseOptimizer
        self.KnowledgeBaseUpdateQueue = KnowledgeBaseUpdateQueue
        self.KnowledgeBaseAutoUpdater = KnowledgeBaseAutoUpdater
        self.KnowledgeBaseUpdate = KnowledgeBaseUpdate
        self.UpdateType = UpdateType
        self.UpdatePriority = UpdatePriority
        self.KnowledgeBaseType = KnowledgeBaseType
        
        # Create mock dependencies
        self.mock_storage = Mock()
        self.mock_kb_client = Mock()
        self.mock_kb_client.config.region_name = "us-east-2"
        self.mock_pattern_learning_system = Mock()
        
        # Create instances with proper mocking
        self.version_manager = self.PatternVersionManager(self.mock_storage)
        self.optimizer = self.KnowledgeBaseOptimizer(self.mock_kb_client, self.mock_storage)
        self.update_queue = self.KnowledgeBaseUpdateQueue(self.mock_storage)
        
        # Mock the DynamicPatternManager to avoid AWS client creation
        with patch('autoninja.core.knowledge_base_updater.DynamicPatternManager'):
            self.auto_updater = self.KnowledgeBaseAutoUpdater(
                self.mock_kb_client, self.mock_pattern_learning_system, self.mock_storage
            )
        
        # Create sample pattern
        self.sample_pattern = Pattern(
            pattern_id="test_pattern_kb",
            pattern_type="requirements",
            content={
                "pattern_subtype": "functional_requirements",
                "requirements_structure": {"chat_interface": True}
            },
            metadata={"source_agent_type": "conversational"},
            confidence_score=0.9,
            usage_count=5,
            success_rate=0.95,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            last_refined=datetime.now(timezone.utc),
            source_generations=["gen1"]
        )
    
    @pytest.mark.asyncio
    async def test_pattern_version_manager_create_version(self):
        """Test creating a pattern version"""
        # Mock the async methods
        async def mock_get_version(pattern_id):
            return 0
        
        async def mock_store_version(version):
            return None
        
        async def mock_cleanup(pattern_id):
            return None
        
        self.version_manager._get_latest_version_number = mock_get_version
        self.version_manager._store_pattern_version = mock_store_version
        self.version_manager._cleanup_old_versions = mock_cleanup
        
        pattern_version = await self.version_manager.create_pattern_version(self.sample_pattern)
        
        assert pattern_version.pattern_id == self.sample_pattern.pattern_id
        assert pattern_version.version == 1
        assert pattern_version.content == self.sample_pattern.content
    
    @pytest.mark.asyncio
    async def test_knowledge_base_optimizer_collect_metrics(self):
        """Test collecting knowledge base metrics"""
        kb_type = self.KnowledgeBaseType.REQUIREMENTS_PATTERNS
        
        metrics = await self.optimizer._collect_kb_metrics(kb_type)
        
        # Should return placeholder metrics
        assert 'total_documents' in metrics
        assert 'active_patterns' in metrics
        assert 'avg_confidence' in metrics
        assert metrics['total_documents'] > 0
    
    @pytest.mark.asyncio
    async def test_knowledge_base_optimizer_optimize(self):
        """Test knowledge base optimization"""
        kb_type = self.KnowledgeBaseType.REQUIREMENTS_PATTERNS
        
        optimization_results = await self.optimizer.optimize_knowledge_base(kb_type)
        
        assert 'kb_type' in optimization_results
        assert 'actions_taken' in optimization_results
        assert 'metrics_before' in optimization_results
        assert 'metrics_after' in optimization_results
        assert optimization_results['kb_type'] == kb_type.value
        assert len(optimization_results['actions_taken']) > 0
    
    @pytest.mark.asyncio
    async def test_update_queue_queue_update(self):
        """Test queuing an update"""
        update = self.KnowledgeBaseUpdate(
            update_id="test_update",
            update_type=self.UpdateType.NEW_PATTERN,
            priority=self.UpdatePriority.MEDIUM,
            kb_type=self.KnowledgeBaseType.REQUIREMENTS_PATTERNS,
            content={"pattern": asdict(self.sample_pattern)},
            metadata={"source": "test"},
            created_at=datetime.now(timezone.utc)
        )
        
        # Mock the async storage method
        async def mock_store_update(update):
            return None
        
        self.update_queue._store_queued_update = mock_store_update
        
        success = await self.update_queue.queue_update(update)
        
        assert success is True
        self.update_queue._store_queued_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_queue_process_queue(self):
        """Test processing the update queue"""
        # Mock the async method
        async def mock_get_pending():
            return []
        
        self.update_queue._get_pending_updates = mock_get_pending
        
        results = await self.update_queue.process_update_queue()
        
        assert 'start_time' in results
        assert 'end_time' in results
        assert 'updates_processed' in results
        assert 'updates_failed' in results
        assert results['updates_processed'] >= 0
    
    @pytest.mark.asyncio
    async def test_auto_updater_process_generation_result(self):
        """Test processing a generation result"""
        generation_result = GenerationResult(
            generation_id="test_gen_kb",
            agent_type="conversational",
            user_request={"description": "test"},
            requirements={"functional": {"chat": True}},
            architecture={"services": ["bedrock"]},
            generated_code={"lambda": {"code": "test"}},
            validation_results={"score": 0.9},
            deployment_config={},
            success_metrics={"success": True},
            timestamp=datetime.now(timezone.utc)
        )
        
        # Mock the pattern learning system
        self.mock_pattern_learning_system.learn_from_generation.return_value = [self.sample_pattern]
        
        # Mock the async queue update method
        async def mock_queue_update(pattern, results):
            return None
        
        self.auto_updater._queue_pattern_update = mock_queue_update
        
        results = await self.auto_updater.process_generation_result(generation_result)
        
        assert 'generation_id' in results
        assert 'patterns_learned' in results
        assert 'kb_updates_queued' in results
        assert results['generation_id'] == generation_result.generation_id
        assert results['patterns_learned'] > 0
    
    @pytest.mark.asyncio
    async def test_auto_updater_get_kb_health_status(self):
        """Test getting knowledge base health status"""
        health_status = await self.auto_updater.get_kb_health_status()
        
        assert 'timestamp' in health_status
        assert 'knowledge_bases' in health_status
        assert 'overall_health' in health_status
        
        # Should have entries for all KB types
        for kb_type in self.KnowledgeBaseType:
            assert kb_type.value in health_status['knowledge_bases']
    
    def test_get_kb_type_for_pattern(self):
        """Test determining KB type for patterns"""
        # Requirements pattern
        req_pattern = Pattern(
            pattern_id="req_test",
            pattern_type="requirements",
            content={}, metadata={}, confidence_score=0.8, usage_count=1,
            success_rate=0.9, created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc), last_refined=datetime.now(timezone.utc),
            source_generations=[]
        )
        
        kb_type = self.auto_updater._get_kb_type_for_pattern(req_pattern)
        assert kb_type == self.KnowledgeBaseType.REQUIREMENTS_PATTERNS
        
        # Architecture pattern
        arch_pattern = Pattern(
            pattern_id="arch_test",
            pattern_type="architecture",
            content={}, metadata={}, confidence_score=0.8, usage_count=1,
            success_rate=0.9, created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc), last_refined=datetime.now(timezone.utc),
            source_generations=[]
        )
        
        kb_type = self.auto_updater._get_kb_type_for_pattern(arch_pattern)
        assert kb_type == self.KnowledgeBaseType.ARCHITECTURE_PATTERNS
        
        # Code pattern
        code_pattern = Pattern(
            pattern_id="code_test",
            pattern_type="code",
            content={}, metadata={}, confidence_score=0.8, usage_count=1,
            success_rate=0.9, created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc), last_refined=datetime.now(timezone.utc),
            source_generations=[]
        )
        
        kb_type = self.auto_updater._get_kb_type_for_pattern(code_pattern)
        assert kb_type == self.KnowledgeBaseType.CODE_TEMPLATES


if __name__ == '__main__':
    pytest.main([__file__])