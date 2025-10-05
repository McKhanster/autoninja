"""
Bedrock Knowledge Base integration for dynamic pattern storage and retrieval.

This module provides functionality for managing Bedrock Knowledge Bases,
including vector search, pattern matching, and document management.
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
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


class KnowledgeBaseType(Enum):
    """Types of knowledge bases for different pattern categories."""
    REQUIREMENTS_PATTERNS = "requirements-patterns"
    ARCHITECTURE_PATTERNS = "architecture-patterns"
    CODE_TEMPLATES = "code-templates"
    TESTING_STANDARDS = "testing-standards"
    DEPLOYMENT_PRACTICES = "deployment-practices"


class DocumentType(Enum):
    """Types of documents stored in knowledge bases."""
    PATTERN = "pattern"
    TEMPLATE = "template"
    STANDARD = "standard"
    EXAMPLE = "example"
    GUIDELINE = "guideline"


@dataclass
class KnowledgeBaseDocument:
    """Represents a document in a Bedrock Knowledge Base."""
    document_id: str
    title: str
    content: str
    document_type: DocumentType
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    confidence_score: float = 0.0
    usage_count: int = 0


@dataclass
class SearchResult:
    """Represents a search result from knowledge base query."""
    document_id: str
    title: str
    content: str
    relevance_score: float
    metadata: Dict[str, Any]
    excerpt: str


@dataclass
class KnowledgeBaseConfig:
    """Configuration for Bedrock Knowledge Base."""
    region_name: str = "us-east-2"
    embedding_model_arn: str = "arn:aws:bedrock:us-east-2::foundation-model/amazon.titan-embed-text-v1"
    max_results: int = 10
    similarity_threshold: float = 0.7
    timeout: int = 30


class BedrockKnowledgeBaseClient:
    """Client for interacting with Bedrock Knowledge Bases."""
    
    def __init__(self, config: Optional[KnowledgeBaseConfig] = None):
        self.config = config or KnowledgeBaseConfig()
        self._bedrock_agent_client = boto3.client(
            'bedrock-agent',
            region_name=self.config.region_name
        )
        self._bedrock_agent_runtime_client = boto3.client(
            'bedrock-agent-runtime',
            region_name=self.config.region_name
        )
        self._knowledge_bases: Dict[KnowledgeBaseType, str] = {}
        self._initialize_knowledge_bases()
    
    def _initialize_knowledge_bases(self):
        """Initialize knowledge base mappings."""
        # In a real implementation, these would be created during deployment
        # For now, we'll store the mapping of KB types to KB IDs
        kb_mapping = {
            KnowledgeBaseType.REQUIREMENTS_PATTERNS: "requirements-patterns-kb-id",
            KnowledgeBaseType.ARCHITECTURE_PATTERNS: "architecture-patterns-kb-id",
            KnowledgeBaseType.CODE_TEMPLATES: "code-templates-kb-id",
            KnowledgeBaseType.TESTING_STANDARDS: "testing-standards-kb-id",
            KnowledgeBaseType.DEPLOYMENT_PRACTICES: "deployment-practices-kb-id"
        }
        
        # Validate knowledge bases exist (in production)
        for kb_type, kb_id in kb_mapping.items():
            try:
                # This would validate the KB exists in production
                self._knowledge_bases[kb_type] = kb_id
                logger.info(f"Initialized knowledge base: {kb_type.value} -> {kb_id}")
            except Exception as e:
                logger.warning(f"Knowledge base {kb_type.value} not available: {str(e)}")
    
    def get_knowledge_base_id(self, kb_type: KnowledgeBaseType) -> str:
        """
        Get the knowledge base ID for a given type.
        
        Args:
            kb_type: The type of knowledge base
            
        Returns:
            str: The knowledge base ID
            
        Raises:
            ValueError: If the knowledge base is not available
        """
        if kb_type not in self._knowledge_bases:
            raise ValueError(f"Knowledge base not available: {kb_type.value}")
        
        return self._knowledge_bases[kb_type]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def search_knowledge_base(
        self,
        kb_type: KnowledgeBaseType,
        query: str,
        max_results: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Search a knowledge base using vector similarity.
        
        Args:
            kb_type: The type of knowledge base to search
            query: The search query
            max_results: Maximum number of results to return
            similarity_threshold: Minimum similarity score for results
            
        Returns:
            List[SearchResult]: List of search results
            
        Raises:
            ValueError: If the knowledge base is not available
            ClientError: If the Bedrock API call fails
        """
        kb_id = self.get_knowledge_base_id(kb_type)
        max_results = max_results or self.config.max_results
        similarity_threshold = similarity_threshold or self.config.similarity_threshold
        
        try:
            response = self._bedrock_agent_runtime_client.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        'overrideSearchType': 'HYBRID'
                    }
                }
            )
            
            results = []
            for item in response.get('retrievalResults', []):
                # Extract relevance score
                score = item.get('score', 0.0)
                
                # Filter by similarity threshold
                if score < similarity_threshold:
                    continue
                
                # Extract content and metadata
                content = item.get('content', {}).get('text', '')
                metadata = item.get('metadata', {})
                
                result = SearchResult(
                    document_id=metadata.get('document_id', str(uuid.uuid4())),
                    title=metadata.get('title', 'Untitled'),
                    content=content,
                    relevance_score=score,
                    metadata=metadata,
                    excerpt=content[:200] + "..." if len(content) > 200 else content
                )
                
                results.append(result)
            
            logger.info(f"Found {len(results)} results for query in {kb_type.value}")
            return results
            
        except ClientError as e:
            logger.error(f"Failed to search knowledge base {kb_type.value}: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def retrieve_and_generate(
        self,
        kb_type: KnowledgeBaseType,
        query: str,
        model_arn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant documents and generate a response using RAG.
        
        Args:
            kb_type: The type of knowledge base to query
            query: The query for retrieval and generation
            model_arn: Optional model ARN for generation
            
        Returns:
            Dict containing the generated response and source documents
            
        Raises:
            ValueError: If the knowledge base is not available
            ClientError: If the Bedrock API call fails
        """
        kb_id = self.get_knowledge_base_id(kb_type)
        
        # Default to Claude Sonnet if no model specified
        if not model_arn:
            model_arn = "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
        
        try:
            response = self._bedrock_agent_runtime_client.retrieve_and_generate(
                input={
                    'text': query
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': kb_id,
                        'modelArn': model_arn,
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': self.config.max_results
                            }
                        }
                    }
                }
            )
            
            result = {
                'generated_text': response.get('output', {}).get('text', ''),
                'source_documents': [],
                'session_id': response.get('sessionId', ''),
                'citations': response.get('citations', [])
            }
            
            # Extract source documents from citations
            for citation in response.get('citations', []):
                for reference in citation.get('retrievedReferences', []):
                    content = reference.get('content', {}).get('text', '')
                    metadata = reference.get('metadata', {})
                    
                    source_doc = {
                        'content': content,
                        'metadata': metadata,
                        'location': reference.get('location', {}),
                        'score': reference.get('score', 0.0)
                    }
                    
                    result['source_documents'].append(source_doc)
            
            logger.info(f"Generated response using knowledge base {kb_type.value}")
            return result
            
        except ClientError as e:
            logger.error(f"Failed to retrieve and generate from {kb_type.value}: {str(e)}")
            raise
    
    def find_similar_patterns(
        self,
        kb_type: KnowledgeBaseType,
        pattern_content: str,
        similarity_threshold: float = 0.8
    ) -> List[SearchResult]:
        """
        Find patterns similar to the given content.
        
        Args:
            kb_type: The type of knowledge base to search
            pattern_content: The pattern content to find similarities for
            similarity_threshold: Minimum similarity score
            
        Returns:
            List[SearchResult]: Similar patterns found
        """
        return self.search_knowledge_base(
            kb_type=kb_type,
            query=pattern_content,
            similarity_threshold=similarity_threshold
        )
    
    def get_pattern_recommendations(
        self,
        kb_type: KnowledgeBaseType,
        context: Dict[str, Any],
        max_recommendations: int = 5
    ) -> List[SearchResult]:
        """
        Get pattern recommendations based on context.
        
        Args:
            kb_type: The type of knowledge base to search
            context: Context information for recommendations
            max_recommendations: Maximum number of recommendations
            
        Returns:
            List[SearchResult]: Recommended patterns
        """
        # Build query from context
        query_parts = []
        
        if 'agent_type' in context:
            query_parts.append(f"agent type: {context['agent_type']}")
        
        if 'requirements' in context:
            query_parts.append(f"requirements: {' '.join(context['requirements'])}")
        
        if 'domain' in context:
            query_parts.append(f"domain: {context['domain']}")
        
        if 'complexity' in context:
            query_parts.append(f"complexity: {context['complexity']}")
        
        query = " ".join(query_parts)
        
        return self.search_knowledge_base(
            kb_type=kb_type,
            query=query,
            max_results=max_recommendations
        )


class DynamicPatternManager:
    """Manages dynamic pattern learning and knowledge base updates."""
    
    def __init__(self, kb_client: BedrockKnowledgeBaseClient):
        self.kb_client = kb_client
        self._s3_client = boto3.client('s3', region_name=kb_client.config.region_name)
        self._pattern_bucket = "autoninja-dynamic-patterns"  # Would be configured
    
    def extract_patterns_from_generation(
        self,
        generation_result: Dict[str, Any]
    ) -> List[KnowledgeBaseDocument]:
        """
        Extract reusable patterns from successful agent generations.
        
        Args:
            generation_result: The result of a successful agent generation
            
        Returns:
            List[KnowledgeBaseDocument]: Extracted patterns
        """
        patterns = []
        
        # Extract requirements patterns
        if 'requirements' in generation_result:
            req_pattern = self._create_requirements_pattern(generation_result['requirements'])
            if req_pattern:
                patterns.append(req_pattern)
        
        # Extract architecture patterns
        if 'architecture' in generation_result:
            arch_pattern = self._create_architecture_pattern(generation_result['architecture'])
            if arch_pattern:
                patterns.append(arch_pattern)
        
        # Extract code templates
        if 'generated_code' in generation_result:
            code_templates = self._create_code_templates(generation_result['generated_code'])
            patterns.extend(code_templates)
        
        return patterns
    
    def _create_requirements_pattern(self, requirements: Dict[str, Any]) -> Optional[KnowledgeBaseDocument]:
        """Create a requirements pattern from successful requirements analysis."""
        if not requirements or 'functional' not in requirements:
            return None
        
        pattern_content = {
            'pattern_type': 'requirements',
            'functional_requirements': requirements.get('functional', []),
            'non_functional_requirements': requirements.get('non_functional', {}),
            'compliance_frameworks': requirements.get('compliance', []),
            'success_criteria': requirements.get('success_criteria', [])
        }
        
        return KnowledgeBaseDocument(
            document_id=str(uuid.uuid4()),
            title=f"Requirements Pattern - {requirements.get('agent_type', 'Generic')}",
            content=json.dumps(pattern_content, indent=2),
            document_type=DocumentType.PATTERN,
            metadata={
                'pattern_type': 'requirements',
                'agent_type': requirements.get('agent_type', 'unknown'),
                'complexity': requirements.get('complexity', 'medium'),
                'domain': requirements.get('domain', 'general')
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=['requirements', 'pattern', 'auto-generated'],
            confidence_score=0.8
        )
    
    def _create_architecture_pattern(self, architecture: Dict[str, Any]) -> Optional[KnowledgeBaseDocument]:
        """Create an architecture pattern from successful architecture design."""
        if not architecture or 'services' not in architecture:
            return None
        
        pattern_content = {
            'pattern_type': 'architecture',
            'aws_services': architecture.get('services', []),
            'service_configuration': architecture.get('configuration', {}),
            'security_architecture': architecture.get('security', {}),
            'integration_patterns': architecture.get('integrations', []),
            'cost_optimization': architecture.get('cost_optimization', {})
        }
        
        return KnowledgeBaseDocument(
            document_id=str(uuid.uuid4()),
            title=f"Architecture Pattern - {architecture.get('pattern_name', 'Generic')}",
            content=json.dumps(pattern_content, indent=2),
            document_type=DocumentType.PATTERN,
            metadata={
                'pattern_type': 'architecture',
                'services': architecture.get('services', []),
                'complexity': architecture.get('complexity', 'medium'),
                'cost_tier': architecture.get('cost_tier', 'standard')
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=['architecture', 'pattern', 'aws', 'auto-generated'],
            confidence_score=0.8
        )
    
    def _create_code_templates(self, generated_code: Dict[str, Any]) -> List[KnowledgeBaseDocument]:
        """Create code templates from successful code generation."""
        templates = []
        
        for component_name, code_data in generated_code.items():
            if not isinstance(code_data, dict) or 'content' not in code_data:
                continue
            
            template_content = {
                'template_type': 'code',
                'component_name': component_name,
                'language': code_data.get('language', 'python'),
                'framework': code_data.get('framework', ''),
                'code_template': code_data.get('content', ''),
                'dependencies': code_data.get('dependencies', []),
                'configuration': code_data.get('configuration', {})
            }
            
            template = KnowledgeBaseDocument(
                document_id=str(uuid.uuid4()),
                title=f"Code Template - {component_name}",
                content=json.dumps(template_content, indent=2),
                document_type=DocumentType.TEMPLATE,
                metadata={
                    'template_type': 'code',
                    'component_name': component_name,
                    'language': code_data.get('language', 'python'),
                    'framework': code_data.get('framework', ''),
                    'complexity': code_data.get('complexity', 'medium')
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                tags=['code', 'template', 'auto-generated'],
                confidence_score=0.7
            )
            
            templates.append(template)
        
        return templates
    
    def store_pattern_in_s3(self, document: KnowledgeBaseDocument) -> str:
        """
        Store a pattern document in S3 for knowledge base ingestion.
        
        Args:
            document: The document to store
            
        Returns:
            str: The S3 URI of the stored document
        """
        try:
            # Create S3 key
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            s3_key = f"patterns/{document.document_type.value}/{timestamp}_{document.document_id}.json"
            
            # Prepare document for storage
            document_data = {
                'document_id': document.document_id,
                'title': document.title,
                'content': document.content,
                'document_type': document.document_type.value,
                'metadata': document.metadata,
                'created_at': document.created_at.isoformat(),
                'updated_at': document.updated_at.isoformat(),
                'tags': document.tags,
                'confidence_score': document.confidence_score,
                'usage_count': document.usage_count
            }
            
            # Store in S3
            self._s3_client.put_object(
                Bucket=self._pattern_bucket,
                Key=s3_key,
                Body=json.dumps(document_data, indent=2),
                ContentType='application/json',
                Metadata={
                    'document-type': document.document_type.value,
                    'pattern-type': document.metadata.get('pattern_type', 'unknown'),
                    'auto-generated': 'true'
                }
            )
            
            s3_uri = f"s3://{self._pattern_bucket}/{s3_key}"
            logger.info(f"Stored pattern document: {s3_uri}")
            
            return s3_uri
            
        except ClientError as e:
            logger.error(f"Failed to store pattern in S3: {str(e)}")
            raise
    
    def update_pattern_usage(self, document_id: str, kb_type: KnowledgeBaseType):
        """
        Update usage statistics for a pattern.
        
        Args:
            document_id: The document ID to update
            kb_type: The knowledge base type
        """
        # In a full implementation, this would update usage statistics
        # in a database and potentially trigger pattern refinement
        logger.info(f"Updated usage for pattern {document_id} in {kb_type.value}")


# Global knowledge base client instance
_kb_client: Optional[BedrockKnowledgeBaseClient] = None


def get_knowledge_base_client(config: Optional[KnowledgeBaseConfig] = None) -> BedrockKnowledgeBaseClient:
    """
    Get the global knowledge base client instance.
    
    Args:
        config: Optional configuration for the client
        
    Returns:
        BedrockKnowledgeBaseClient: The global client instance
    """
    global _kb_client
    
    if _kb_client is None:
        _kb_client = BedrockKnowledgeBaseClient(config)
    
    return _kb_client


def reset_knowledge_base_client():
    """Reset the global knowledge base client instance (mainly for testing)."""
    global _kb_client
    _kb_client = None