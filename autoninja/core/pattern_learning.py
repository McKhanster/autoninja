"""
Dynamic Pattern Learning System for AutoNinja AWS Bedrock

This module implements pattern extraction, similarity detection, and refinement
logic for learning from successful agent generations.
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
import re
import boto3

from autoninja.storage.dynamodb import DynamoDBStateStore
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient
from autoninja.utils.serialization import serialize_for_json, safe_json_loads, safe_json_dumps

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents a learned pattern from successful generations"""
    pattern_id: str
    pattern_type: str  # requirements, architecture, code, testing, deployment
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    confidence_score: float
    usage_count: int
    success_rate: float
    created_at: datetime
    last_used: datetime
    last_refined: datetime
    source_generations: List[str]


@dataclass
class GenerationResult:
    """Represents a successful agent generation result"""
    generation_id: str
    agent_type: str
    user_request: Dict[str, Any]
    requirements: Dict[str, Any]
    architecture: Dict[str, Any]
    generated_code: Dict[str, Any]
    validation_results: Dict[str, Any]
    deployment_config: Dict[str, Any]
    success_metrics: Dict[str, Any]
    timestamp: datetime


class PatternExtractor:
    """Extracts reusable patterns from successful generations"""
    
    def __init__(self):
        self.similarity_threshold = 0.7
        self.min_pattern_occurrences = 2
        
    def extract_requirements_patterns(self, generation_result: GenerationResult) -> List[Pattern]:
        """Extract reusable requirements patterns"""
        patterns = []
        requirements = generation_result.requirements
        
        # Extract functional requirement patterns
        if 'functional_requirements' in requirements:
            pattern = self._create_requirements_pattern(
                requirements['functional_requirements'],
                generation_result,
                'functional_requirements'
            )
            patterns.append(pattern)
        
        # Extract non-functional requirement patterns
        if 'non_functional_requirements' in requirements:
            pattern = self._create_requirements_pattern(
                requirements['non_functional_requirements'],
                generation_result,
                'non_functional_requirements'
            )
            patterns.append(pattern)
        
        # Extract compliance patterns
        if 'compliance_requirements' in requirements:
            pattern = self._create_requirements_pattern(
                requirements['compliance_requirements'],
                generation_result,
                'compliance_requirements'
            )
            patterns.append(pattern)
            
        return patterns
    
    def extract_architecture_patterns(self, generation_result: GenerationResult) -> List[Pattern]:
        """Extract reusable architecture patterns"""
        patterns = []
        architecture = generation_result.architecture
        
        # Extract service composition patterns
        if 'aws_services' in architecture:
            pattern = self._create_architecture_pattern(
                architecture['aws_services'],
                generation_result,
                'service_composition'
            )
            patterns.append(pattern)
        
        # Extract security architecture patterns
        if 'security_architecture' in architecture:
            pattern = self._create_architecture_pattern(
                architecture['security_architecture'],
                generation_result,
                'security_architecture'
            )
            patterns.append(pattern)
        
        # Extract integration patterns
        if 'integrations' in architecture:
            pattern = self._create_architecture_pattern(
                architecture['integrations'],
                generation_result,
                'integration_patterns'
            )
            patterns.append(pattern)
            
        return patterns
    
    def extract_code_patterns(self, generation_result: GenerationResult) -> List[Pattern]:
        """Extract reusable code patterns"""
        patterns = []
        code = generation_result.generated_code
        
        # Extract Lambda function patterns
        if 'lambda_functions' in code:
            for func_name, func_code in code['lambda_functions'].items():
                pattern = self._create_code_pattern(
                    func_code,
                    generation_result,
                    'lambda_function',
                    func_name
                )
                patterns.append(pattern)
        
        # Extract API Gateway patterns
        if 'api_gateway' in code:
            pattern = self._create_code_pattern(
                code['api_gateway'],
                generation_result,
                'api_gateway'
            )
            patterns.append(pattern)
        
        # Extract CloudFormation patterns
        if 'cloudformation' in code:
            pattern = self._create_code_pattern(
                code['cloudformation'],
                generation_result,
                'cloudformation_template'
            )
            patterns.append(pattern)
            
        return patterns
    
    def _create_requirements_pattern(self, content: Dict[str, Any], 
                                   generation_result: GenerationResult,
                                   pattern_subtype: str) -> Pattern:
        """Create a requirements pattern"""
        pattern_content = {
            'pattern_subtype': pattern_subtype,
            'requirements_structure': content,
            'context': {
                'agent_type': generation_result.agent_type,
                'domain': self._extract_domain(generation_result.user_request),
                'complexity': self._assess_complexity(content)
            }
        }
        
        return self._create_pattern(
            pattern_content,
            generation_result,
            'requirements',
            pattern_subtype
        )
    
    def _create_architecture_pattern(self, content: Dict[str, Any],
                                   generation_result: GenerationResult,
                                   pattern_subtype: str) -> Pattern:
        """Create an architecture pattern"""
        pattern_content = {
            'pattern_subtype': pattern_subtype,
            'architecture_components': content,
            'context': {
                'agent_type': generation_result.agent_type,
                'scale': self._assess_scale(content),
                'security_level': self._assess_security_level(content)
            }
        }
        
        return self._create_pattern(
            pattern_content,
            generation_result,
            'architecture',
            pattern_subtype
        )
    
    def _create_code_pattern(self, content: Dict[str, Any],
                           generation_result: GenerationResult,
                           pattern_subtype: str,
                           component_name: str = None) -> Pattern:
        """Create a code pattern"""
        pattern_content = {
            'pattern_subtype': pattern_subtype,
            'code_structure': content,
            'component_name': component_name,
            'context': {
                'language': self._detect_language(content),
                'framework': self._detect_framework(content),
                'aws_services': self._extract_aws_services(content)
            }
        }
        
        return self._create_pattern(
            pattern_content,
            generation_result,
            'code',
            pattern_subtype
        )
    
    def _create_pattern(self, content: Dict[str, Any],
                       generation_result: GenerationResult,
                       pattern_type: str,
                       pattern_subtype: str) -> Pattern:
        """Create a pattern with metadata"""
        pattern_id = self._generate_pattern_id(content, pattern_type, pattern_subtype)
        
        metadata = {
            'pattern_subtype': pattern_subtype,
            'source_agent_type': generation_result.agent_type,
            'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
            'success_metrics': generation_result.success_metrics,
            'validation_score': generation_result.validation_results.get('overall_score', 0.0)
        }
        
        return Pattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            content=content,
            metadata=metadata,
            confidence_score=1.0,  # Initial confidence
            usage_count=1,
            success_rate=1.0,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            last_refined=datetime.now(timezone.utc),
            source_generations=[generation_result.generation_id]
        )
    
    def _generate_pattern_id(self, content: Dict[str, Any], 
                           pattern_type: str, pattern_subtype: str) -> str:
        """Generate a unique pattern ID based on content hash"""
        content_str = json.dumps(content, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        return f"{pattern_type}_{pattern_subtype}_{content_hash}"
    
    def _extract_domain(self, user_request: Dict[str, Any]) -> str:
        """Extract domain from user request"""
        description = user_request.get('description', '').lower()
        
        # Simple domain detection based on keywords
        if any(word in description for word in ['customer', 'support', 'chat', 'conversation']):
            return 'customer_service'
        elif any(word in description for word in ['data', 'analysis', 'analytics', 'report']):
            return 'data_analytics'
        elif any(word in description for word in ['automation', 'workflow', 'process']):
            return 'automation'
        else:
            return 'general'
    
    def _assess_complexity(self, content: Dict[str, Any]) -> str:
        """Assess complexity of requirements"""
        requirement_count = len(str(content))
        
        if requirement_count > 2000:
            return 'high'
        elif requirement_count > 1000:
            return 'medium'
        else:
            return 'low'
    
    def _assess_scale(self, content: Dict[str, Any]) -> str:
        """Assess scale of architecture"""
        service_count = len(content.get('services', []))
        
        if service_count > 10:
            return 'large'
        elif service_count > 5:
            return 'medium'
        else:
            return 'small'
    
    def _assess_security_level(self, content: Dict[str, Any]) -> str:
        """Assess security level of architecture"""
        security_features = content.get('security_features', [])
        
        if len(security_features) > 5:
            return 'high'
        elif len(security_features) > 2:
            return 'medium'
        else:
            return 'basic'
    
    def _detect_language(self, content: Dict[str, Any]) -> str:
        """Detect programming language from code content"""
        code_str = str(content).lower()
        
        if 'import boto3' in code_str or 'def lambda_handler' in code_str:
            return 'python'
        elif 'const aws' in code_str or 'exports.handler' in code_str:
            return 'nodejs'
        elif 'import com.amazonaws' in code_str:
            return 'java'
        else:
            return 'unknown'
    
    def _detect_framework(self, content: Dict[str, Any]) -> str:
        """Detect framework from code content"""
        code_str = str(content).lower()
        
        if 'fastapi' in code_str:
            return 'fastapi'
        elif 'flask' in code_str:
            return 'flask'
        elif 'express' in code_str:
            return 'express'
        else:
            return 'none'
    
    def _extract_aws_services(self, content: Dict[str, Any]) -> List[str]:
        """Extract AWS services used in code"""
        code_str = str(content).lower()
        services = []
        
        service_patterns = {
            'lambda': r'lambda|aws_lambda',
            'dynamodb': r'dynamodb',
            'api_gateway': r'api.gateway|apigateway',
            's3': r's3|bucket',
            'bedrock': r'bedrock',
            'step_functions': r'stepfunctions|step.functions'
        }
        
        for service, pattern in service_patterns.items():
            if re.search(pattern, code_str):
                services.append(service)
        
        return services


class SimilarityDetector:
    """Detects similarity between patterns for deduplication and refinement"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
    
    def find_similar_patterns(self, new_pattern: Pattern, 
                            existing_patterns: List[Pattern]) -> List[Tuple[Pattern, float]]:
        """Find existing patterns similar to the new pattern"""
        similar_patterns = []
        
        for existing_pattern in existing_patterns:
            if existing_pattern.pattern_type != new_pattern.pattern_type:
                continue
                
            similarity_score = self._calculate_similarity(new_pattern, existing_pattern)
            
            if similarity_score >= self.similarity_threshold:
                similar_patterns.append((existing_pattern, similarity_score))
        
        # Sort by similarity score (highest first)
        similar_patterns.sort(key=lambda x: x[1], reverse=True)
        return similar_patterns
    
    def _calculate_similarity(self, pattern1: Pattern, pattern2: Pattern) -> float:
        """Calculate similarity score between two patterns"""
        # Content similarity
        content_similarity = self._calculate_content_similarity(
            pattern1.content, pattern2.content
        )
        
        # Metadata similarity
        metadata_similarity = self._calculate_metadata_similarity(
            pattern1.metadata, pattern2.metadata
        )
        
        # Weighted average
        return 0.7 * content_similarity + 0.3 * metadata_similarity
    
    def _calculate_content_similarity(self, content1: Dict[str, Any], 
                                    content2: Dict[str, Any]) -> float:
        """Calculate similarity between pattern contents"""
        content1_str = json.dumps(content1, sort_keys=True)
        content2_str = json.dumps(content2, sort_keys=True)
        
        return SequenceMatcher(None, content1_str, content2_str).ratio()
    
    def _calculate_metadata_similarity(self, metadata1: Dict[str, Any],
                                     metadata2: Dict[str, Any]) -> float:
        """Calculate similarity between pattern metadata"""
        # Compare key metadata fields
        similarity_scores = []
        
        # Pattern subtype
        if metadata1.get('pattern_subtype') == metadata2.get('pattern_subtype'):
            similarity_scores.append(1.0)
        else:
            similarity_scores.append(0.0)
        
        # Source agent type
        if metadata1.get('source_agent_type') == metadata2.get('source_agent_type'):
            similarity_scores.append(1.0)
        else:
            similarity_scores.append(0.0)
        
        # Validation score similarity
        score1 = metadata1.get('validation_score', 0.0)
        score2 = metadata2.get('validation_score', 0.0)
        score_similarity = 1.0 - abs(score1 - score2)
        similarity_scores.append(score_similarity)
        
        return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0


class PatternRefiner:
    """Refines patterns based on usage feedback and success metrics"""
    
    def __init__(self):
        self.min_usage_for_refinement = 3
        self.confidence_decay_factor = 0.95
        self.success_weight = 0.6
        self.usage_weight = 0.4
    
    def refine_pattern(self, pattern: Pattern, usage_feedback: Dict[str, Any]) -> Pattern:
        """Refine a pattern based on usage feedback"""
        # Update usage statistics
        pattern.usage_count += 1
        pattern.last_used = datetime.now(timezone.utc)
        
        # Update success rate
        if 'success' in usage_feedback:
            success_count = pattern.usage_count * pattern.success_rate
            if usage_feedback['success']:
                success_count += 1
            pattern.success_rate = success_count / pattern.usage_count
        
        # Update confidence score
        pattern.confidence_score = self._calculate_confidence_score(pattern)
        
        # Refine content if enough usage data
        if pattern.usage_count >= self.min_usage_for_refinement:
            pattern = self._refine_pattern_content(pattern, usage_feedback)
        
        pattern.last_refined = datetime.now(timezone.utc)
        return pattern
    
    def merge_similar_patterns(self, primary_pattern: Pattern, 
                             similar_pattern: Pattern) -> Pattern:
        """Merge two similar patterns into one refined pattern"""
        # Combine usage statistics
        total_usage = primary_pattern.usage_count + similar_pattern.usage_count
        combined_success_rate = (
            (primary_pattern.success_rate * primary_pattern.usage_count +
             similar_pattern.success_rate * similar_pattern.usage_count) / total_usage
        )
        
        # Merge content (prefer higher confidence pattern)
        if primary_pattern.confidence_score >= similar_pattern.confidence_score:
            merged_content = primary_pattern.content.copy()
            base_metadata = primary_pattern.metadata.copy()
        else:
            merged_content = similar_pattern.content.copy()
            base_metadata = similar_pattern.metadata.copy()
        
        # Combine source generations
        combined_sources = list(set(
            primary_pattern.source_generations + similar_pattern.source_generations
        ))
        
        # Create merged pattern
        merged_pattern = Pattern(
            pattern_id=primary_pattern.pattern_id,  # Keep primary ID
            pattern_type=primary_pattern.pattern_type,
            content=merged_content,
            metadata=base_metadata,
            confidence_score=max(primary_pattern.confidence_score, 
                               similar_pattern.confidence_score),
            usage_count=total_usage,
            success_rate=combined_success_rate,
            created_at=min(primary_pattern.created_at, similar_pattern.created_at),
            last_used=max(primary_pattern.last_used, similar_pattern.last_used),
            last_refined=datetime.now(timezone.utc),
            source_generations=combined_sources
        )
        
        return merged_pattern
    
    def _calculate_confidence_score(self, pattern: Pattern) -> float:
        """Calculate confidence score based on usage and success metrics"""
        # Base confidence from success rate
        success_confidence = pattern.success_rate
        
        # Usage confidence (more usage = higher confidence, with diminishing returns)
        usage_confidence = min(1.0, pattern.usage_count / 10.0)
        
        # Time decay (patterns get less confident over time without use)
        days_since_last_use = (datetime.now(timezone.utc) - pattern.last_used).days
        time_decay = self.confidence_decay_factor ** (days_since_last_use / 30.0)
        
        # Weighted combination
        confidence = (
            self.success_weight * success_confidence +
            self.usage_weight * usage_confidence
        ) * time_decay
        
        return min(1.0, max(0.0, confidence))
    
    def _refine_pattern_content(self, pattern: Pattern, 
                              usage_feedback: Dict[str, Any]) -> Pattern:
        """Refine pattern content based on usage feedback"""
        # This is a simplified refinement - in practice, this would use
        # more sophisticated ML techniques to improve patterns
        
        if 'improvements' in usage_feedback:
            improvements = usage_feedback['improvements']
            
            # Apply improvements to pattern content
            if 'add_components' in improvements:
                for component in improvements['add_components']:
                    if 'components' not in pattern.content:
                        pattern.content['components'] = []
                    if component not in pattern.content['components']:
                        pattern.content['components'].append(component)
            
            if 'remove_components' in improvements:
                for component in improvements['remove_components']:
                    if 'components' in pattern.content:
                        pattern.content['components'] = [
                            c for c in pattern.content['components'] if c != component
                        ]
        
        return pattern


class DynamoDBPatternStorage:
    """Generic DynamoDB storage for patterns"""
    
    def __init__(self, table_name: str = "autoninja-patterns", region_name: str = "us-east-2"):
        self.table_name = table_name
        self.region_name = region_name
        
        # Initialize DynamoDB client and resource
        session = boto3.Session()
        self.dynamodb = session.resource('dynamodb', region_name=region_name)
        self.table = self.dynamodb.Table(table_name)
    
    def put_item(self, table_name: str, item: Dict[str, Any]) -> None:
        """Put an item into the table"""
        self.table.put_item(Item=item)
    
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get an item from the table"""
        response = self.table.get_item(Key=key)
        return response.get('Item')
    
    def delete_item(self, table_name: str, key: Dict[str, Any]) -> None:
        """Delete an item from the table"""
        self.table.delete_item(Key=key)
    
    def query_items(self, table_name: str, key_condition_expression: str, 
                   expression_attribute_values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query items from the table"""
        from boto3.dynamodb.conditions import Key
        
        # Simple implementation - in practice would need more sophisticated parsing
        if "pattern_type = :pattern_type" in key_condition_expression:
            pattern_type = expression_attribute_values[":pattern_type"]
            response = self.table.query(
                KeyConditionExpression=Key('pattern_type').eq(pattern_type)
            )
            return response.get('Items', [])
        return []


class PatternLearningSystem:
    """Main system for pattern learning from successful generations"""
    
    def __init__(self, dynamodb_storage: DynamoDBPatternStorage, 
                 knowledge_base_client: BedrockKnowledgeBaseClient):
        self.storage = dynamodb_storage
        self.knowledge_base = knowledge_base_client
        self.extractor = PatternExtractor()
        self.similarity_detector = SimilarityDetector()
        self.refiner = PatternRefiner()
        
        # Initialize pattern storage table
        self.pattern_table = "autoninja_patterns"
        
    def learn_from_generation(self, generation_result: GenerationResult) -> List[Pattern]:
        """Learn patterns from a successful generation"""
        logger.info(f"Learning patterns from generation {generation_result.generation_id}")
        
        # Extract patterns from the generation
        all_patterns = []
        all_patterns.extend(self.extractor.extract_requirements_patterns(generation_result))
        all_patterns.extend(self.extractor.extract_architecture_patterns(generation_result))
        all_patterns.extend(self.extractor.extract_code_patterns(generation_result))
        
        # Process each extracted pattern
        processed_patterns = []
        for pattern in all_patterns:
            processed_pattern = self._process_new_pattern(pattern)
            if processed_pattern:
                processed_patterns.append(processed_pattern)
        
        logger.info(f"Processed {len(processed_patterns)} patterns from generation")
        return processed_patterns
    
    def _process_new_pattern(self, new_pattern: Pattern) -> Optional[Pattern]:
        """Process a new pattern by checking for similarities and merging if needed"""
        # Get existing patterns of the same type
        existing_patterns = self._get_existing_patterns(new_pattern.pattern_type)
        
        # Find similar patterns
        similar_patterns = self.similarity_detector.find_similar_patterns(
            new_pattern, existing_patterns
        )
        
        if similar_patterns:
            # Merge with the most similar pattern
            most_similar_pattern, similarity_score = similar_patterns[0]
            logger.info(f"Found similar pattern with score {similarity_score}")
            
            # Merge patterns
            merged_pattern = self.refiner.merge_similar_patterns(
                most_similar_pattern, new_pattern
            )
            
            # Update in storage
            self._store_pattern(merged_pattern)
            
            # Remove the old similar pattern
            self._remove_pattern(most_similar_pattern.pattern_id)
            
            return merged_pattern
        else:
            # Store as new pattern
            self._store_pattern(new_pattern)
            return new_pattern
    
    def update_pattern_feedback(self, pattern_id: str, 
                              usage_feedback: Dict[str, Any]) -> Optional[Pattern]:
        """Update a pattern based on usage feedback"""
        pattern = self._get_pattern(pattern_id)
        if not pattern:
            logger.warning(f"Pattern {pattern_id} not found for feedback update")
            return None
        
        # Refine the pattern
        refined_pattern = self.refiner.refine_pattern(pattern, usage_feedback)
        
        # Store updated pattern
        self._store_pattern(refined_pattern)
        
        return refined_pattern
    
    def get_relevant_patterns(self, context: Dict[str, Any]) -> List[Pattern]:
        """Get patterns relevant to a given context"""
        # This would implement more sophisticated pattern matching
        # For now, return patterns based on type and metadata
        
        pattern_type = context.get('pattern_type')
        if not pattern_type:
            return []
        
        patterns = self._get_existing_patterns(pattern_type)
        
        # Filter by context
        relevant_patterns = []
        for pattern in patterns:
            if self._is_pattern_relevant(pattern, context):
                relevant_patterns.append(pattern)
        
        # Sort by confidence score
        relevant_patterns.sort(key=lambda p: p.confidence_score, reverse=True)
        
        return relevant_patterns
    
    def _get_existing_patterns(self, pattern_type: str) -> List[Pattern]:
        """Get existing patterns of a specific type from storage"""
        try:
            items = self.storage.query_items(
                table_name=self.pattern_table,
                key_condition_expression="pattern_type = :pattern_type",
                expression_attribute_values={":pattern_type": pattern_type}
            )
            
            patterns = []
            for item in items:
                pattern_data = safe_json_loads(item['pattern_data'])
                pattern = Pattern(**pattern_data)
                patterns.append(pattern)
            
            return patterns
        except Exception as e:
            logger.error(f"Error retrieving patterns: {e}")
            return []
    
    def _get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """Get a specific pattern by ID"""
        try:
            item = self.storage.get_item(
                table_name=self.pattern_table,
                key={"pattern_id": pattern_id}
            )
            
            if item:
                pattern_data = safe_json_loads(item['pattern_data'])
                return Pattern(**pattern_data)
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving pattern {pattern_id}: {e}")
            return None
    
    def _store_pattern(self, pattern: Pattern) -> None:
        """Store a pattern in the database"""
        try:
            item = {
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type,
                "pattern_data": safe_json_dumps(asdict(pattern)),
                "confidence_score": pattern.confidence_score,
                "usage_count": pattern.usage_count,
                "last_used": pattern.last_used.isoformat(),
                "created_at": pattern.created_at.isoformat()
            }
            
            self.storage.put_item(table_name=self.pattern_table, item=item)
            logger.info(f"Stored pattern {pattern.pattern_id}")
        except Exception as e:
            logger.error(f"Error storing pattern {pattern.pattern_id}: {e}")
    
    def _remove_pattern(self, pattern_id: str) -> None:
        """Remove a pattern from storage"""
        try:
            self.storage.delete_item(
                table_name=self.pattern_table,
                key={"pattern_id": pattern_id}
            )
            logger.info(f"Removed pattern {pattern_id}")
        except Exception as e:
            logger.error(f"Error removing pattern {pattern_id}: {e}")
    
    def _is_pattern_relevant(self, pattern: Pattern, context: Dict[str, Any]) -> bool:
        """Check if a pattern is relevant to the given context"""
        # Simple relevance check based on metadata
        pattern_metadata = pattern.metadata
        
        # Check agent type
        if 'agent_type' in context:
            if pattern_metadata.get('source_agent_type') != context['agent_type']:
                return False
        
        # Check domain
        if 'domain' in context:
            pattern_context = pattern.content.get('context', {})
            if pattern_context.get('domain') != context['domain']:
                return False
        
        # Check minimum confidence
        min_confidence = context.get('min_confidence', 0.5)
        if pattern.confidence_score < min_confidence:
            return False
        
        return True