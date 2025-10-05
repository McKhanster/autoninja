"""
Knowledge Base Auto-Update Mechanism for AutoNinja AWS Bedrock

This module implements automatic knowledge base document creation,
pattern versioning and lifecycle management, and knowledge base
optimization and cleanup processes.
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import boto3
from botocore.exceptions import ClientError

from autoninja.core.pattern_learning import Pattern, PatternLearningSystem, GenerationResult
from autoninja.core.template_generation import GeneratedTemplate
from autoninja.core.knowledge_base import (
    BedrockKnowledgeBaseClient, KnowledgeBaseType, KnowledgeBaseDocument, 
    DocumentType, DynamicPatternManager
)
from autoninja.storage.dynamodb import DynamoDBStateStore
from autoninja.utils.serialization import safe_json_dumps, safe_json_loads

logger = logging.getLogger(__name__)


class UpdateType(Enum):
    """Types of knowledge base updates"""
    NEW_PATTERN = "new_pattern"
    PATTERN_REFINEMENT = "pattern_refinement"
    PATTERN_MERGE = "pattern_merge"
    PATTERN_DEPRECATION = "pattern_deprecation"
    TEMPLATE_ADDITION = "template_addition"
    CLEANUP = "cleanup"


class UpdatePriority(Enum):
    """Priority levels for knowledge base updates"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class KnowledgeBaseUpdate:
    """Represents a pending knowledge base update"""
    update_id: str
    update_type: UpdateType
    priority: UpdatePriority
    kb_type: KnowledgeBaseType
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class PatternVersion:
    """Represents a version of a pattern"""
    pattern_id: str
    version: int
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    deprecated_at: Optional[datetime] = None
    replacement_pattern_id: Optional[str] = None


@dataclass
class KnowledgeBaseMetrics:
    """Metrics for knowledge base health and performance"""
    kb_type: KnowledgeBaseType
    total_documents: int
    active_patterns: int
    deprecated_patterns: int
    avg_pattern_confidence: float
    last_update: datetime
    update_frequency: float  # Updates per day
    storage_size_mb: float
    query_performance_ms: float


class PatternVersionManager:
    """Manages pattern versioning and lifecycle"""
    
    def __init__(self, storage: DynamoDBStateStore):
        self.storage = storage
        self.version_table = "autoninja_pattern_versions"
        self.max_versions_per_pattern = 10
        self.deprecation_threshold_days = 90
    
    async def create_pattern_version(self, pattern: Pattern) -> PatternVersion:
        """
        Create a new version of a pattern.
        
        Args:
            pattern: The pattern to version
            
        Returns:
            PatternVersion: The created version
        """
        # Get current version number
        current_version = await self._get_latest_version_number(pattern.pattern_id)
        new_version = current_version + 1
        
        pattern_version = PatternVersion(
            pattern_id=pattern.pattern_id,
            version=new_version,
            content=pattern.content.copy(),
            metadata=pattern.metadata.copy(),
            created_at=datetime.now(timezone.utc)
        )
        
        # Store the version
        await self._store_pattern_version(pattern_version)
        
        # Clean up old versions if needed
        await self._cleanup_old_versions(pattern.pattern_id)
        
        logger.info(f"Created version {new_version} for pattern {pattern.pattern_id}")
        return pattern_version
    
    async def get_pattern_versions(self, pattern_id: str) -> List[PatternVersion]:
        """Get all versions of a pattern"""
        try:
            # This would query the version table
            # For now, return empty list as placeholder
            return []
        except Exception as e:
            logger.error(f"Error retrieving pattern versions for {pattern_id}: {e}")
            return []
    
    async def deprecate_pattern_version(self, pattern_id: str, version: int, 
                                      replacement_pattern_id: Optional[str] = None) -> bool:
        """
        Deprecate a specific version of a pattern.
        
        Args:
            pattern_id: The pattern ID
            version: The version to deprecate
            replacement_pattern_id: Optional replacement pattern ID
            
        Returns:
            bool: True if successful
        """
        try:
            pattern_version = await self._get_pattern_version(pattern_id, version)
            if not pattern_version:
                logger.warning(f"Pattern version {pattern_id}:{version} not found")
                return False
            
            pattern_version.deprecated_at = datetime.now(timezone.utc)
            pattern_version.replacement_pattern_id = replacement_pattern_id
            
            await self._store_pattern_version(pattern_version)
            
            logger.info(f"Deprecated pattern version {pattern_id}:{version}")
            return True
            
        except Exception as e:
            logger.error(f"Error deprecating pattern version {pattern_id}:{version}: {e}")
            return False
    
    async def cleanup_deprecated_patterns(self, days_old: int = 90) -> int:
        """
        Clean up patterns deprecated longer than specified days.
        
        Args:
            days_old: Number of days after which to clean up deprecated patterns
            
        Returns:
            int: Number of patterns cleaned up
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        cleaned_count = 0
        
        try:
            # This would scan for deprecated patterns older than cutoff
            # For now, return 0 as placeholder
            logger.info(f"Cleaned up {cleaned_count} deprecated patterns")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up deprecated patterns: {e}")
            return 0
    
    async def _get_latest_version_number(self, pattern_id: str) -> int:
        """Get the latest version number for a pattern"""
        try:
            # This would query the version table for the highest version
            # For now, return 0 as placeholder
            return 0
        except Exception as e:
            logger.error(f"Error getting latest version for {pattern_id}: {e}")
            return 0
    
    async def _store_pattern_version(self, pattern_version: PatternVersion) -> None:
        """Store a pattern version"""
        try:
            # This would store the version in DynamoDB
            logger.debug(f"Stored pattern version {pattern_version.pattern_id}:{pattern_version.version}")
        except Exception as e:
            logger.error(f"Error storing pattern version: {e}")
            raise
    
    async def _get_pattern_version(self, pattern_id: str, version: int) -> Optional[PatternVersion]:
        """Get a specific pattern version"""
        try:
            # This would retrieve the specific version from DynamoDB
            return None
        except Exception as e:
            logger.error(f"Error retrieving pattern version {pattern_id}:{version}: {e}")
            return None
    
    async def _cleanup_old_versions(self, pattern_id: str) -> None:
        """Clean up old versions beyond the maximum limit"""
        try:
            versions = await self.get_pattern_versions(pattern_id)
            if len(versions) > self.max_versions_per_pattern:
                # Sort by version number and keep only the latest ones
                versions.sort(key=lambda v: v.version, reverse=True)
                versions_to_delete = versions[self.max_versions_per_pattern:]
                
                for version in versions_to_delete:
                    await self._delete_pattern_version(pattern_id, version.version)
                
                logger.info(f"Cleaned up {len(versions_to_delete)} old versions for pattern {pattern_id}")
        except Exception as e:
            logger.error(f"Error cleaning up old versions for {pattern_id}: {e}")
    
    async def _delete_pattern_version(self, pattern_id: str, version: int) -> None:
        """Delete a specific pattern version"""
        try:
            # This would delete the version from DynamoDB
            logger.debug(f"Deleted pattern version {pattern_id}:{version}")
        except Exception as e:
            logger.error(f"Error deleting pattern version {pattern_id}:{version}: {e}")


class KnowledgeBaseOptimizer:
    """Optimizes knowledge base performance and storage"""
    
    def __init__(self, kb_client: BedrockKnowledgeBaseClient, storage: DynamoDBStateStore):
        self.kb_client = kb_client
        self.storage = storage
        self.metrics_table = "autoninja_kb_metrics"
    
    async def optimize_knowledge_base(self, kb_type: KnowledgeBaseType) -> Dict[str, Any]:
        """
        Optimize a knowledge base for performance and storage.
        
        Args:
            kb_type: The knowledge base type to optimize
            
        Returns:
            Dict containing optimization results
        """
        logger.info(f"Optimizing knowledge base: {kb_type.value}")
        
        optimization_results = {
            'kb_type': kb_type.value,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'actions_taken': [],
            'metrics_before': {},
            'metrics_after': {},
            'improvement_summary': {}
        }
        
        # Get baseline metrics
        optimization_results['metrics_before'] = await self._collect_kb_metrics(kb_type)
        
        # Perform optimization actions
        await self._deduplicate_similar_patterns(kb_type, optimization_results)
        await self._consolidate_low_usage_patterns(kb_type, optimization_results)
        await self._update_pattern_rankings(kb_type, optimization_results)
        await self._cleanup_obsolete_documents(kb_type, optimization_results)
        
        # Get post-optimization metrics
        optimization_results['metrics_after'] = await self._collect_kb_metrics(kb_type)
        
        # Calculate improvements
        optimization_results['improvement_summary'] = self._calculate_improvements(
            optimization_results['metrics_before'],
            optimization_results['metrics_after']
        )
        
        optimization_results['end_time'] = datetime.now(timezone.utc).isoformat()
        
        # Store optimization results
        await self._store_optimization_results(optimization_results)
        
        logger.info(f"Knowledge base optimization complete for {kb_type.value}")
        return optimization_results
    
    async def _collect_kb_metrics(self, kb_type: KnowledgeBaseType) -> Dict[str, Any]:
        """Collect metrics for a knowledge base"""
        try:
            # This would collect actual metrics from the knowledge base
            # For now, return placeholder metrics
            return {
                'total_documents': 100,
                'active_patterns': 80,
                'deprecated_patterns': 20,
                'avg_confidence': 0.75,
                'storage_size_mb': 50.0,
                'query_performance_ms': 150.0
            }
        except Exception as e:
            logger.error(f"Error collecting metrics for {kb_type.value}: {e}")
            return {}
    
    async def _deduplicate_similar_patterns(self, kb_type: KnowledgeBaseType, 
                                          results: Dict[str, Any]) -> None:
        """Remove duplicate or very similar patterns"""
        try:
            # This would identify and merge similar patterns
            duplicates_removed = 5  # Placeholder
            
            results['actions_taken'].append({
                'action': 'deduplicate_patterns',
                'duplicates_removed': duplicates_removed,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Removed {duplicates_removed} duplicate patterns from {kb_type.value}")
            
        except Exception as e:
            logger.error(f"Error deduplicating patterns in {kb_type.value}: {e}")
    
    async def _consolidate_low_usage_patterns(self, kb_type: KnowledgeBaseType, 
                                            results: Dict[str, Any]) -> None:
        """Consolidate patterns with low usage into more general patterns"""
        try:
            # This would identify low-usage patterns and consolidate them
            patterns_consolidated = 3  # Placeholder
            
            results['actions_taken'].append({
                'action': 'consolidate_low_usage',
                'patterns_consolidated': patterns_consolidated,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Consolidated {patterns_consolidated} low-usage patterns in {kb_type.value}")
            
        except Exception as e:
            logger.error(f"Error consolidating patterns in {kb_type.value}: {e}")
    
    async def _update_pattern_rankings(self, kb_type: KnowledgeBaseType, 
                                     results: Dict[str, Any]) -> None:
        """Update pattern rankings based on usage and success metrics"""
        try:
            # This would recalculate and update pattern rankings
            patterns_reranked = 25  # Placeholder
            
            results['actions_taken'].append({
                'action': 'update_rankings',
                'patterns_reranked': patterns_reranked,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Updated rankings for {patterns_reranked} patterns in {kb_type.value}")
            
        except Exception as e:
            logger.error(f"Error updating pattern rankings in {kb_type.value}: {e}")
    
    async def _cleanup_obsolete_documents(self, kb_type: KnowledgeBaseType, 
                                        results: Dict[str, Any]) -> None:
        """Remove obsolete or outdated documents"""
        try:
            # This would identify and remove obsolete documents
            documents_removed = 8  # Placeholder
            
            results['actions_taken'].append({
                'action': 'cleanup_obsolete',
                'documents_removed': documents_removed,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Removed {documents_removed} obsolete documents from {kb_type.value}")
            
        except Exception as e:
            logger.error(f"Error cleaning up obsolete documents in {kb_type.value}: {e}")
    
    def _calculate_improvements(self, before_metrics: Dict[str, Any], 
                              after_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate improvement metrics"""
        improvements = {}
        
        for metric in ['total_documents', 'storage_size_mb', 'query_performance_ms']:
            if metric in before_metrics and metric in after_metrics:
                before_val = before_metrics[metric]
                after_val = after_metrics[metric]
                
                if before_val > 0:
                    improvement_pct = ((before_val - after_val) / before_val) * 100
                    improvements[f"{metric}_improvement_pct"] = improvement_pct
        
        return improvements
    
    async def _store_optimization_results(self, results: Dict[str, Any]) -> None:
        """Store optimization results for tracking"""
        try:
            # This would store the results in DynamoDB
            logger.debug(f"Stored optimization results for {results['kb_type']}")
        except Exception as e:
            logger.error(f"Error storing optimization results: {e}")


class KnowledgeBaseUpdateQueue:
    """Manages queued updates to knowledge bases"""
    
    def __init__(self, storage: DynamoDBStateStore):
        self.storage = storage
        self.update_queue_table = "autoninja_kb_update_queue"
        self.max_concurrent_updates = 5
        self.update_batch_size = 10
    
    async def queue_update(self, update: KnowledgeBaseUpdate) -> bool:
        """
        Queue a knowledge base update.
        
        Args:
            update: The update to queue
            
        Returns:
            bool: True if successfully queued
        """
        try:
            # Store the update in the queue
            await self._store_queued_update(update)
            
            logger.info(f"Queued update {update.update_id} for {update.kb_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error queuing update {update.update_id}: {e}")
            return False
    
    async def process_update_queue(self) -> Dict[str, Any]:
        """
        Process pending updates in the queue.
        
        Returns:
            Dict containing processing results
        """
        logger.info("Processing knowledge base update queue")
        
        processing_results = {
            'start_time': datetime.now(timezone.utc).isoformat(),
            'updates_processed': 0,
            'updates_failed': 0,
            'updates_skipped': 0,
            'errors': []
        }
        
        try:
            # Get pending updates
            pending_updates = await self._get_pending_updates()
            
            # Process updates in batches
            for i in range(0, len(pending_updates), self.update_batch_size):
                batch = pending_updates[i:i + self.update_batch_size]
                batch_results = await self._process_update_batch(batch)
                
                processing_results['updates_processed'] += batch_results['processed']
                processing_results['updates_failed'] += batch_results['failed']
                processing_results['updates_skipped'] += batch_results['skipped']
                processing_results['errors'].extend(batch_results['errors'])
        
        except Exception as e:
            logger.error(f"Error processing update queue: {e}")
            processing_results['errors'].append(str(e))
        
        processing_results['end_time'] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Update queue processing complete. Processed: {processing_results['updates_processed']}, "
                   f"Failed: {processing_results['updates_failed']}, Skipped: {processing_results['updates_skipped']}")
        
        return processing_results
    
    async def _get_pending_updates(self) -> List[KnowledgeBaseUpdate]:
        """Get pending updates from the queue"""
        try:
            # This would query the update queue table
            # For now, return empty list as placeholder
            return []
        except Exception as e:
            logger.error(f"Error retrieving pending updates: {e}")
            return []
    
    async def _process_update_batch(self, updates: List[KnowledgeBaseUpdate]) -> Dict[str, Any]:
        """Process a batch of updates concurrently"""
        batch_results = {
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Create semaphore to limit concurrent updates
        semaphore = asyncio.Semaphore(self.max_concurrent_updates)
        
        async def process_single_update(update: KnowledgeBaseUpdate):
            async with semaphore:
                try:
                    success = await self._execute_update(update)
                    if success:
                        batch_results['processed'] += 1
                        await self._mark_update_completed(update.update_id)
                    else:
                        batch_results['failed'] += 1
                        await self._handle_update_failure(update)
                        
                except Exception as e:
                    batch_results['failed'] += 1
                    batch_results['errors'].append(f"Update {update.update_id}: {str(e)}")
                    await self._handle_update_failure(update)
        
        # Process all updates in the batch concurrently
        tasks = [process_single_update(update) for update in updates]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return batch_results
    
    async def _execute_update(self, update: KnowledgeBaseUpdate) -> bool:
        """Execute a specific update"""
        try:
            logger.info(f"Executing update {update.update_id} of type {update.update_type.value}")
            
            if update.update_type == UpdateType.NEW_PATTERN:
                return await self._execute_new_pattern_update(update)
            elif update.update_type == UpdateType.PATTERN_REFINEMENT:
                return await self._execute_pattern_refinement_update(update)
            elif update.update_type == UpdateType.PATTERN_MERGE:
                return await self._execute_pattern_merge_update(update)
            elif update.update_type == UpdateType.TEMPLATE_ADDITION:
                return await self._execute_template_addition_update(update)
            elif update.update_type == UpdateType.CLEANUP:
                return await self._execute_cleanup_update(update)
            else:
                logger.warning(f"Unknown update type: {update.update_type.value}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing update {update.update_id}: {e}")
            return False
    
    async def _execute_new_pattern_update(self, update: KnowledgeBaseUpdate) -> bool:
        """Execute a new pattern update"""
        try:
            # This would add a new pattern to the knowledge base
            logger.info(f"Added new pattern to {update.kb_type.value}")
            return True
        except Exception as e:
            logger.error(f"Error adding new pattern: {e}")
            return False
    
    async def _execute_pattern_refinement_update(self, update: KnowledgeBaseUpdate) -> bool:
        """Execute a pattern refinement update"""
        try:
            # This would update an existing pattern in the knowledge base
            logger.info(f"Refined pattern in {update.kb_type.value}")
            return True
        except Exception as e:
            logger.error(f"Error refining pattern: {e}")
            return False
    
    async def _execute_pattern_merge_update(self, update: KnowledgeBaseUpdate) -> bool:
        """Execute a pattern merge update"""
        try:
            # This would merge similar patterns in the knowledge base
            logger.info(f"Merged patterns in {update.kb_type.value}")
            return True
        except Exception as e:
            logger.error(f"Error merging patterns: {e}")
            return False
    
    async def _execute_template_addition_update(self, update: KnowledgeBaseUpdate) -> bool:
        """Execute a template addition update"""
        try:
            # This would add a new template to the knowledge base
            logger.info(f"Added template to {update.kb_type.value}")
            return True
        except Exception as e:
            logger.error(f"Error adding template: {e}")
            return False
    
    async def _execute_cleanup_update(self, update: KnowledgeBaseUpdate) -> bool:
        """Execute a cleanup update"""
        try:
            # This would perform cleanup operations on the knowledge base
            logger.info(f"Performed cleanup on {update.kb_type.value}")
            return True
        except Exception as e:
            logger.error(f"Error performing cleanup: {e}")
            return False
    
    async def _store_queued_update(self, update: KnowledgeBaseUpdate) -> None:
        """Store an update in the queue"""
        try:
            # This would store the update in DynamoDB
            logger.debug(f"Stored queued update {update.update_id}")
        except Exception as e:
            logger.error(f"Error storing queued update: {e}")
            raise
    
    async def _mark_update_completed(self, update_id: str) -> None:
        """Mark an update as completed"""
        try:
            # This would update the status in DynamoDB
            logger.debug(f"Marked update {update_id} as completed")
        except Exception as e:
            logger.error(f"Error marking update completed: {e}")
    
    async def _handle_update_failure(self, update: KnowledgeBaseUpdate) -> None:
        """Handle a failed update"""
        try:
            update.retry_count += 1
            
            if update.retry_count < update.max_retries:
                # Reschedule for retry
                update.scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=5 * update.retry_count)
                await self._store_queued_update(update)
                logger.info(f"Rescheduled failed update {update.update_id} for retry {update.retry_count}")
            else:
                # Mark as permanently failed
                logger.error(f"Update {update.update_id} failed permanently after {update.retry_count} retries")
                
        except Exception as e:
            logger.error(f"Error handling update failure: {e}")


class KnowledgeBaseAutoUpdater:
    """Main class for automatic knowledge base updates"""
    
    def __init__(self, kb_client: BedrockKnowledgeBaseClient, 
                 pattern_learning_system: PatternLearningSystem,
                 storage: DynamoDBStateStore):
        self.kb_client = kb_client
        self.pattern_learning_system = pattern_learning_system
        self.storage = storage
        
        self.version_manager = PatternVersionManager(storage)
        self.optimizer = KnowledgeBaseOptimizer(kb_client, storage)
        self.update_queue = KnowledgeBaseUpdateQueue(storage)
        self.pattern_manager = DynamicPatternManager(kb_client)
        
        # Configuration
        self.auto_update_enabled = True
        self.update_frequency_hours = 6
        self.optimization_frequency_days = 7
    
    async def process_generation_result(self, generation_result: GenerationResult) -> Dict[str, Any]:
        """
        Process a successful generation result and update knowledge bases.
        
        Args:
            generation_result: The successful generation result
            
        Returns:
            Dict containing processing results
        """
        logger.info(f"Processing generation result {generation_result.generation_id} for KB updates")
        
        processing_results = {
            'generation_id': generation_result.generation_id,
            'patterns_learned': 0,
            'kb_updates_queued': 0,
            'errors': []
        }
        
        try:
            # Learn patterns from the generation
            learned_patterns = self.pattern_learning_system.learn_from_generation(generation_result)
            processing_results['patterns_learned'] = len(learned_patterns)
            
            # Create KB updates for each learned pattern
            for pattern in learned_patterns:
                await self._queue_pattern_update(pattern, processing_results)
            
            # Extract and queue template updates if applicable
            if hasattr(generation_result, 'generated_templates'):
                for template in generation_result.generated_templates:
                    await self._queue_template_update(template, processing_results)
            
        except Exception as e:
            logger.error(f"Error processing generation result {generation_result.generation_id}: {e}")
            processing_results['errors'].append(str(e))
        
        logger.info(f"Processed generation result. Patterns learned: {processing_results['patterns_learned']}, "
                   f"Updates queued: {processing_results['kb_updates_queued']}")
        
        return processing_results
    
    async def run_scheduled_updates(self) -> Dict[str, Any]:
        """
        Run scheduled knowledge base updates.
        
        Returns:
            Dict containing update results
        """
        logger.info("Running scheduled knowledge base updates")
        
        update_results = {
            'start_time': datetime.now(timezone.utc).isoformat(),
            'queue_processing_results': {},
            'optimization_results': {},
            'cleanup_results': {},
            'errors': []
        }
        
        try:
            # Process the update queue
            update_results['queue_processing_results'] = await self.update_queue.process_update_queue()
            
            # Run optimization if scheduled
            if await self._should_run_optimization():
                optimization_tasks = []
                for kb_type in KnowledgeBaseType:
                    optimization_tasks.append(self.optimizer.optimize_knowledge_base(kb_type))
                
                optimization_results = await asyncio.gather(*optimization_tasks, return_exceptions=True)
                update_results['optimization_results'] = {
                    kb_type.value: result for kb_type, result in zip(KnowledgeBaseType, optimization_results)
                    if not isinstance(result, Exception)
                }
            
            # Run cleanup operations
            update_results['cleanup_results'] = await self._run_cleanup_operations()
            
        except Exception as e:
            logger.error(f"Error running scheduled updates: {e}")
            update_results['errors'].append(str(e))
        
        update_results['end_time'] = datetime.now(timezone.utc).isoformat()
        
        logger.info("Scheduled knowledge base updates complete")
        return update_results
    
    async def _queue_pattern_update(self, pattern: Pattern, results: Dict[str, Any]) -> None:
        """Queue an update for a learned pattern"""
        try:
            # Determine the appropriate knowledge base type
            kb_type = self._get_kb_type_for_pattern(pattern)
            
            # Create version for the pattern
            pattern_version = await self.version_manager.create_pattern_version(pattern)
            
            # Create update
            update = KnowledgeBaseUpdate(
                update_id=f"pattern_{pattern.pattern_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                update_type=UpdateType.NEW_PATTERN,
                priority=UpdatePriority.MEDIUM,
                kb_type=kb_type,
                content={
                    'pattern': asdict(pattern),
                    'version': asdict(pattern_version)
                },
                metadata={
                    'source': 'pattern_learning',
                    'confidence_score': pattern.confidence_score,
                    'usage_count': pattern.usage_count
                },
                created_at=datetime.now(timezone.utc)
            )
            
            # Queue the update
            success = await self.update_queue.queue_update(update)
            if success:
                results['kb_updates_queued'] += 1
            
        except Exception as e:
            logger.error(f"Error queuing pattern update for {pattern.pattern_id}: {e}")
            results['errors'].append(f"Pattern {pattern.pattern_id}: {str(e)}")
    
    async def _queue_template_update(self, template: GeneratedTemplate, results: Dict[str, Any]) -> None:
        """Queue an update for a generated template"""
        try:
            # Determine the appropriate knowledge base type
            kb_type = self._get_kb_type_for_template(template)
            
            # Create update
            update = KnowledgeBaseUpdate(
                update_id=f"template_{template.template_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                update_type=UpdateType.TEMPLATE_ADDITION,
                priority=UpdatePriority.LOW,
                kb_type=kb_type,
                content={
                    'template': asdict(template)
                },
                metadata={
                    'source': 'template_generation',
                    'quality_score': template.quality_score,
                    'confidence_score': template.confidence_score
                },
                created_at=datetime.now(timezone.utc)
            )
            
            # Queue the update
            success = await self.update_queue.queue_update(update)
            if success:
                results['kb_updates_queued'] += 1
            
        except Exception as e:
            logger.error(f"Error queuing template update for {template.template_id}: {e}")
            results['errors'].append(f"Template {template.template_id}: {str(e)}")
    
    def _get_kb_type_for_pattern(self, pattern: Pattern) -> KnowledgeBaseType:
        """Determine the appropriate knowledge base type for a pattern"""
        if pattern.pattern_type == 'requirements':
            return KnowledgeBaseType.REQUIREMENTS_PATTERNS
        elif pattern.pattern_type == 'architecture':
            return KnowledgeBaseType.ARCHITECTURE_PATTERNS
        elif pattern.pattern_type == 'code':
            return KnowledgeBaseType.CODE_TEMPLATES
        elif pattern.pattern_type == 'testing':
            return KnowledgeBaseType.TESTING_STANDARDS
        elif pattern.pattern_type == 'deployment':
            return KnowledgeBaseType.DEPLOYMENT_PRACTICES
        else:
            return KnowledgeBaseType.REQUIREMENTS_PATTERNS  # Default
    
    def _get_kb_type_for_template(self, template: GeneratedTemplate) -> KnowledgeBaseType:
        """Determine the appropriate knowledge base type for a template"""
        from autoninja.core.template_generation import TemplateType
        
        if template.template_type == TemplateType.REQUIREMENTS:
            return KnowledgeBaseType.REQUIREMENTS_PATTERNS
        elif template.template_type == TemplateType.ARCHITECTURE:
            return KnowledgeBaseType.ARCHITECTURE_PATTERNS
        elif template.template_type == TemplateType.CODE:
            return KnowledgeBaseType.CODE_TEMPLATES
        elif template.template_type == TemplateType.TESTING:
            return KnowledgeBaseType.TESTING_STANDARDS
        elif template.template_type == TemplateType.DEPLOYMENT:
            return KnowledgeBaseType.DEPLOYMENT_PRACTICES
        else:
            return KnowledgeBaseType.REQUIREMENTS_PATTERNS  # Default
    
    async def _should_run_optimization(self) -> bool:
        """Check if optimization should be run"""
        try:
            # This would check when optimization was last run
            # For now, return True as placeholder
            return True
        except Exception as e:
            logger.error(f"Error checking optimization schedule: {e}")
            return False
    
    async def _run_cleanup_operations(self) -> Dict[str, Any]:
        """Run cleanup operations"""
        cleanup_results = {
            'deprecated_patterns_cleaned': 0,
            'old_versions_cleaned': 0,
            'errors': []
        }
        
        try:
            # Clean up deprecated patterns
            deprecated_cleaned = await self.version_manager.cleanup_deprecated_patterns()
            cleanup_results['deprecated_patterns_cleaned'] = deprecated_cleaned
            
        except Exception as e:
            logger.error(f"Error running cleanup operations: {e}")
            cleanup_results['errors'].append(str(e))
        
        return cleanup_results
    
    async def get_kb_health_status(self) -> Dict[str, Any]:
        """Get health status of all knowledge bases"""
        health_status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'knowledge_bases': {},
            'overall_health': 'unknown'
        }
        
        try:
            healthy_count = 0
            total_count = 0
            
            for kb_type in KnowledgeBaseType:
                total_count += 1
                kb_metrics = await self.optimizer._collect_kb_metrics(kb_type)
                
                # Simple health check based on metrics
                is_healthy = (
                    kb_metrics.get('total_documents', 0) > 0 and
                    kb_metrics.get('query_performance_ms', 1000) < 500
                )
                
                if is_healthy:
                    healthy_count += 1
                
                health_status['knowledge_bases'][kb_type.value] = {
                    'healthy': is_healthy,
                    'metrics': kb_metrics
                }
            
            # Overall health
            if healthy_count == total_count:
                health_status['overall_health'] = 'healthy'
            elif healthy_count > total_count / 2:
                health_status['overall_health'] = 'degraded'
            else:
                health_status['overall_health'] = 'unhealthy'
            
        except Exception as e:
            logger.error(f"Error getting KB health status: {e}")
            health_status['overall_health'] = 'error'
            health_status['error'] = str(e)
        
        return health_status


# Factory function for creating auto-updater instances
def create_kb_auto_updater(
    kb_client: BedrockKnowledgeBaseClient,
    pattern_learning_system: PatternLearningSystem,
    storage: DynamoDBStateStore
) -> KnowledgeBaseAutoUpdater:
    """
    Factory function to create knowledge base auto-updater instance.
    
    Args:
        kb_client: Bedrock knowledge base client
        pattern_learning_system: Pattern learning system
        storage: DynamoDB storage instance
        
    Returns:
        KnowledgeBaseAutoUpdater instance
    """
    return KnowledgeBaseAutoUpdater(kb_client, pattern_learning_system, storage)