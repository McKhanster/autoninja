"""
Dynamic Template Generation System for AutoNinja AWS Bedrock

This module implements template synthesis from multiple patterns,
context-aware template customization, and template validation with quality scoring.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
import re
import hashlib

from autoninja.core.pattern_learning import Pattern, SimilarityDetector
from autoninja.core.knowledge_base import BedrockKnowledgeBaseClient, KnowledgeBaseType
from autoninja.utils.serialization import safe_json_dumps, safe_json_loads

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Types of templates that can be generated"""
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    CODE = "code"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


@dataclass
class TemplateComponent:
    """Represents a component within a template"""
    component_id: str
    component_type: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    weight: float  # Importance weight in the template
    source_patterns: List[str]  # Pattern IDs that contributed to this component


@dataclass
class GeneratedTemplate:
    """Represents a dynamically generated template"""
    template_id: str
    template_type: TemplateType
    title: str
    description: str
    components: List[TemplateComponent]
    context: Dict[str, Any]
    quality_score: float
    confidence_score: float
    created_at: datetime
    source_patterns: List[str]
    customization_parameters: Dict[str, Any]


@dataclass
class TemplateRequest:
    """Represents a request for template generation"""
    template_type: TemplateType
    context: Dict[str, Any]
    requirements: List[str]
    constraints: Dict[str, Any]
    customization_preferences: Dict[str, Any]


class PatternSynthesizer:
    """Synthesizes templates from multiple patterns"""
    
    def __init__(self):
        self.similarity_detector = SimilarityDetector()
        self.min_pattern_confidence = 0.6
        self.max_patterns_per_template = 10
    
    def synthesize_template(self, patterns: List[Pattern], 
                          template_request: TemplateRequest) -> GeneratedTemplate:
        """
        Synthesize a template from multiple patterns based on the request.
        
        Args:
            patterns: List of relevant patterns to synthesize from
            template_request: The template generation request
            
        Returns:
            GeneratedTemplate: The synthesized template
        """
        logger.info(f"Synthesizing {template_request.template_type.value} template from {len(patterns)} patterns")
        
        # Filter and rank patterns by relevance
        relevant_patterns = self._filter_relevant_patterns(patterns, template_request)
        ranked_patterns = self._rank_patterns_by_relevance(relevant_patterns, template_request)
        
        # Limit to top patterns
        top_patterns = ranked_patterns[:self.max_patterns_per_template]
        
        # Extract and merge components from patterns
        components = self._extract_and_merge_components(top_patterns, template_request)
        
        # Generate template metadata
        template_id = self._generate_template_id(template_request, top_patterns)
        quality_score = self._calculate_template_quality(components, template_request)
        confidence_score = self._calculate_confidence_score(top_patterns, components)
        
        template = GeneratedTemplate(
            template_id=template_id,
            template_type=template_request.template_type,
            title=self._generate_template_title(template_request),
            description=self._generate_template_description(template_request, components),
            components=components,
            context=template_request.context.copy(),
            quality_score=quality_score,
            confidence_score=confidence_score,
            created_at=datetime.now(timezone.utc),
            source_patterns=[p.pattern_id for p in top_patterns],
            customization_parameters=template_request.customization_preferences.copy()
        )
        
        logger.info(f"Generated template {template_id} with quality score {quality_score:.2f}")
        return template
    
    def _filter_relevant_patterns(self, patterns: List[Pattern], 
                                 template_request: TemplateRequest) -> List[Pattern]:
        """Filter patterns based on relevance to the template request"""
        relevant_patterns = []
        
        for pattern in patterns:
            # Check pattern type matches
            if pattern.pattern_type != template_request.template_type.value:
                continue
            
            # Check minimum confidence
            if pattern.confidence_score < self.min_pattern_confidence:
                continue
            
            # Check context compatibility
            if self._is_context_compatible(pattern, template_request.context):
                relevant_patterns.append(pattern)
        
        return relevant_patterns
    
    def _is_context_compatible(self, pattern: Pattern, context: Dict[str, Any]) -> bool:
        """Check if a pattern is compatible with the given context"""
        pattern_context = pattern.content.get('context', {})
        
        # Check agent type compatibility
        if 'agent_type' in context and 'agent_type' in pattern_context:
            if pattern_context['agent_type'] != context['agent_type']:
                return False
        
        # Check domain compatibility
        if 'domain' in context and 'domain' in pattern_context:
            if pattern_context['domain'] != context['domain']:
                # Allow general domain patterns to match any domain
                if pattern_context['domain'] != 'general':
                    return False
        
        # Check complexity compatibility
        if 'complexity' in context and 'complexity' in pattern_context:
            context_complexity = context['complexity']
            pattern_complexity = pattern_context['complexity']
            
            # Allow patterns of same or lower complexity
            complexity_order = {'low': 1, 'medium': 2, 'high': 3}
            if complexity_order.get(pattern_complexity, 2) > complexity_order.get(context_complexity, 2):
                return False
        
        return True
    
    def _rank_patterns_by_relevance(self, patterns: List[Pattern], 
                                   template_request: TemplateRequest) -> List[Pattern]:
        """Rank patterns by relevance to the template request"""
        scored_patterns = []
        
        for pattern in patterns:
            relevance_score = self._calculate_pattern_relevance(pattern, template_request)
            scored_patterns.append((pattern, relevance_score))
        
        # Sort by relevance score (highest first)
        scored_patterns.sort(key=lambda x: x[1], reverse=True)
        
        return [pattern for pattern, score in scored_patterns]
    
    def _calculate_pattern_relevance(self, pattern: Pattern, 
                                   template_request: TemplateRequest) -> float:
        """Calculate relevance score for a pattern"""
        score = 0.0
        
        # Base score from pattern confidence and usage
        score += pattern.confidence_score * 0.4
        score += min(pattern.usage_count / 10.0, 1.0) * 0.2
        score += pattern.success_rate * 0.2
        
        # Context matching bonus
        pattern_context = pattern.content.get('context', {})
        request_context = template_request.context
        
        context_matches = 0
        context_total = 0
        
        for key in ['agent_type', 'domain', 'complexity']:
            if key in request_context:
                context_total += 1
                if pattern_context.get(key) == request_context[key]:
                    context_matches += 1
                elif pattern_context.get(key) == 'general':
                    context_matches += 0.5  # Partial match for general patterns
        
        if context_total > 0:
            context_score = context_matches / context_total
            score += context_score * 0.2
        
        return min(score, 1.0)
    
    def _extract_and_merge_components(self, patterns: List[Pattern], 
                                    template_request: TemplateRequest) -> List[TemplateComponent]:
        """Extract and merge components from patterns"""
        components = []
        component_groups = {}  # Group similar components
        
        for pattern in patterns:
            pattern_components = self._extract_components_from_pattern(pattern)
            
            for component in pattern_components:
                # Group similar components for merging
                component_key = self._get_component_key(component)
                
                if component_key not in component_groups:
                    component_groups[component_key] = []
                
                component_groups[component_key].append((component, pattern))
        
        # Merge grouped components
        for component_key, component_list in component_groups.items():
            merged_component = self._merge_similar_components(component_list, template_request)
            if merged_component:
                components.append(merged_component)
        
        # Sort components by weight (importance)
        components.sort(key=lambda c: c.weight, reverse=True)
        
        return components
    
    def _extract_components_from_pattern(self, pattern: Pattern) -> List[TemplateComponent]:
        """Extract reusable components from a pattern"""
        components = []
        pattern_content = pattern.content
        
        if pattern.pattern_type == 'requirements':
            components.extend(self._extract_requirements_components(pattern))
        elif pattern.pattern_type == 'architecture':
            components.extend(self._extract_architecture_components(pattern))
        elif pattern.pattern_type == 'code':
            components.extend(self._extract_code_components(pattern))
        
        return components
    
    def _extract_requirements_components(self, pattern: Pattern) -> List[TemplateComponent]:
        """Extract components from requirements patterns"""
        components = []
        content = pattern.content
        
        # Extract functional requirements component
        if 'requirements_structure' in content:
            req_structure = content['requirements_structure']
            
            component = TemplateComponent(
                component_id=f"{pattern.pattern_id}_functional_req",
                component_type="functional_requirements",
                content=req_structure,
                metadata={
                    "source_pattern": pattern.pattern_id,
                    "pattern_confidence": pattern.confidence_score,
                    "usage_count": pattern.usage_count
                },
                weight=0.8,  # High importance for functional requirements
                source_patterns=[pattern.pattern_id]
            )
            components.append(component)
        
        return components
    
    def _extract_architecture_components(self, pattern: Pattern) -> List[TemplateComponent]:
        """Extract components from architecture patterns"""
        components = []
        content = pattern.content
        
        # Extract service composition component
        if 'architecture_components' in content:
            arch_components = content['architecture_components']
            
            component = TemplateComponent(
                component_id=f"{pattern.pattern_id}_services",
                component_type="service_composition",
                content=arch_components,
                metadata={
                    "source_pattern": pattern.pattern_id,
                    "pattern_confidence": pattern.confidence_score,
                    "services": arch_components.get('services', [])
                },
                weight=0.9,  # Very high importance for service composition
                source_patterns=[pattern.pattern_id]
            )
            components.append(component)
        
        return components
    
    def _extract_code_components(self, pattern: Pattern) -> List[TemplateComponent]:
        """Extract components from code patterns"""
        components = []
        content = pattern.content
        
        # Extract code structure component
        if 'code_structure' in content:
            code_structure = content['code_structure']
            
            component = TemplateComponent(
                component_id=f"{pattern.pattern_id}_code",
                component_type="code_structure",
                content=code_structure,
                metadata={
                    "source_pattern": pattern.pattern_id,
                    "language": content.get('context', {}).get('language', 'unknown'),
                    "framework": content.get('context', {}).get('framework', 'none')
                },
                weight=0.7,  # Moderate importance for code structure
                source_patterns=[pattern.pattern_id]
            )
            components.append(component)
        
        return components
    
    def _get_component_key(self, component: TemplateComponent) -> str:
        """Generate a key for grouping similar components"""
        return f"{component.component_type}_{hashlib.md5(str(component.content).encode()).hexdigest()[:8]}"
    
    def _merge_similar_components(self, component_list: List[Tuple[TemplateComponent, Pattern]], 
                                template_request: TemplateRequest) -> Optional[TemplateComponent]:
        """Merge similar components from different patterns"""
        if not component_list:
            return None
        
        if len(component_list) == 1:
            return component_list[0][0]
        
        # Use the component with highest pattern confidence as base
        component_list.sort(key=lambda x: x[1].confidence_score, reverse=True)
        base_component, base_pattern = component_list[0]
        
        # Merge content from other components
        merged_content = base_component.content.copy()
        merged_metadata = base_component.metadata.copy()
        source_patterns = [base_pattern.pattern_id]
        
        total_weight = base_pattern.confidence_score
        weighted_content = {}
        
        for component, pattern in component_list[1:]:
            source_patterns.append(pattern.pattern_id)
            weight = pattern.confidence_score
            total_weight += weight
            
            # Merge content with weighting
            for key, value in component.content.items():
                if key not in weighted_content:
                    weighted_content[key] = []
                weighted_content[key].append((value, weight))
        
        # Apply weighted merging for conflicting values
        for key, value_weights in weighted_content.items():
            if key in merged_content:
                # Resolve conflicts using weighted voting
                merged_content[key] = self._resolve_content_conflict(
                    merged_content[key], value_weights, base_pattern.confidence_score
                )
        
        # Calculate merged weight
        avg_confidence = total_weight / len(component_list)
        merged_weight = base_component.weight * (avg_confidence / base_pattern.confidence_score)
        
        return TemplateComponent(
            component_id=f"merged_{base_component.component_id}",
            component_type=base_component.component_type,
            content=merged_content,
            metadata=merged_metadata,
            weight=merged_weight,
            source_patterns=source_patterns
        )
    
    def _resolve_content_conflict(self, base_value: Any, 
                                 conflicting_values: List[Tuple[Any, float]], 
                                 base_weight: float) -> Any:
        """Resolve conflicts between content values using weighted voting"""
        if not conflicting_values:
            return base_value
        
        # For simple values, use the highest weighted value
        if isinstance(base_value, (str, int, float, bool)):
            best_value = base_value
            best_weight = base_weight
            
            for value, weight in conflicting_values:
                if weight > best_weight:
                    best_value = value
                    best_weight = weight
            
            return best_value
        
        # For lists, merge unique items
        elif isinstance(base_value, list):
            merged_list = base_value.copy()
            
            for value, weight in conflicting_values:
                if isinstance(value, list):
                    for item in value:
                        if item not in merged_list:
                            merged_list.append(item)
            
            return merged_list
        
        # For dicts, merge recursively
        elif isinstance(base_value, dict):
            merged_dict = base_value.copy()
            
            for value, weight in conflicting_values:
                if isinstance(value, dict):
                    for key, val in value.items():
                        if key not in merged_dict:
                            merged_dict[key] = val
                        elif weight > base_weight:
                            merged_dict[key] = val
            
            return merged_dict
        
        # Default: return base value
        return base_value
    
    def _calculate_template_quality(self, components: List[TemplateComponent], 
                                  template_request: TemplateRequest) -> float:
        """Calculate quality score for the generated template"""
        if not components:
            return 0.0
        
        # Component quality score
        component_scores = [c.weight for c in components]
        avg_component_quality = sum(component_scores) / len(component_scores)
        
        # Coverage score (how well the template covers the requirements)
        coverage_score = self._calculate_coverage_score(components, template_request)
        
        # Consistency score (how well components work together)
        consistency_score = self._calculate_consistency_score(components)
        
        # Weighted combination
        quality_score = (
            0.4 * avg_component_quality +
            0.4 * coverage_score +
            0.2 * consistency_score
        )
        
        return min(1.0, max(0.0, quality_score))
    
    def _calculate_coverage_score(self, components: List[TemplateComponent], 
                                template_request: TemplateRequest) -> float:
        """Calculate how well the template covers the requirements"""
        requirements = template_request.requirements
        if not requirements:
            return 1.0
        
        covered_requirements = 0
        
        for requirement in requirements:
            requirement_lower = requirement.lower()
            
            # Check if any component addresses this requirement
            for component in components:
                component_content = str(component.content).lower()
                if any(word in component_content for word in requirement_lower.split()):
                    covered_requirements += 1
                    break
        
        return covered_requirements / len(requirements) if requirements else 1.0
    
    def _calculate_consistency_score(self, components: List[TemplateComponent]) -> float:
        """Calculate consistency score between components"""
        if len(components) < 2:
            return 1.0
        
        consistency_scores = []
        
        for i, comp1 in enumerate(components):
            for comp2 in components[i+1:]:
                # Check for consistency between components
                consistency = self._check_component_consistency(comp1, comp2)
                consistency_scores.append(consistency)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0
    
    def _check_component_consistency(self, comp1: TemplateComponent, 
                                   comp2: TemplateComponent) -> float:
        """Check consistency between two components"""
        # Simple consistency check based on metadata compatibility
        meta1 = comp1.metadata
        meta2 = comp2.metadata
        
        consistency_score = 1.0
        
        # Check language consistency for code components
        if (comp1.component_type == 'code_structure' and 
            comp2.component_type == 'code_structure'):
            lang1 = meta1.get('language', 'unknown')
            lang2 = meta2.get('language', 'unknown')
            
            if lang1 != 'unknown' and lang2 != 'unknown' and lang1 != lang2:
                consistency_score *= 0.5  # Penalty for language mismatch
        
        # Check framework consistency
        if 'framework' in meta1 and 'framework' in meta2:
            if meta1['framework'] != meta2['framework']:
                consistency_score *= 0.8  # Small penalty for framework mismatch
        
        return consistency_score
    
    def _calculate_confidence_score(self, patterns: List[Pattern], 
                                  components: List[TemplateComponent]) -> float:
        """Calculate confidence score for the template"""
        if not patterns:
            return 0.0
        
        # Average pattern confidence
        pattern_confidences = [p.confidence_score for p in patterns]
        avg_pattern_confidence = sum(pattern_confidences) / len(pattern_confidences)
        
        # Pattern usage score
        total_usage = sum(p.usage_count for p in patterns)
        usage_score = min(total_usage / 50.0, 1.0)  # Normalize to 0-1
        
        # Component count score (more components = higher confidence up to a point)
        component_score = min(len(components) / 5.0, 1.0)
        
        # Weighted combination
        confidence = (
            0.5 * avg_pattern_confidence +
            0.3 * usage_score +
            0.2 * component_score
        )
        
        return min(1.0, max(0.0, confidence))
    
    def _generate_template_id(self, template_request: TemplateRequest, 
                            patterns: List[Pattern]) -> str:
        """Generate unique template ID"""
        content_str = f"{template_request.template_type.value}_{template_request.context}_{[p.pattern_id for p in patterns]}"
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"template_{template_request.template_type.value}_{timestamp}_{content_hash}"
    
    def _generate_template_title(self, template_request: TemplateRequest) -> str:
        """Generate a descriptive title for the template"""
        template_type = template_request.template_type.value.title()
        context = template_request.context
        
        agent_type = context.get('agent_type', 'Generic')
        domain = context.get('domain', 'General')
        
        return f"{template_type} Template for {agent_type.title()} Agent ({domain.title()} Domain)"
    
    def _generate_template_description(self, template_request: TemplateRequest, 
                                     components: List[TemplateComponent]) -> str:
        """Generate a description for the template"""
        template_type = template_request.template_type.value
        component_count = len(components)
        
        description = f"Dynamically generated {template_type} template with {component_count} components. "
        
        if template_request.requirements:
            description += f"Addresses {len(template_request.requirements)} specific requirements. "
        
        if components:
            component_types = list(set(c.component_type for c in components))
            description += f"Includes: {', '.join(component_types)}."
        
        return description


class ContextAwareCustomizer:
    """Customizes templates based on specific context and preferences"""
    
    def __init__(self):
        self.customization_rules = self._load_customization_rules()
    
    def customize_template(self, template: GeneratedTemplate, 
                         customization_context: Dict[str, Any]) -> GeneratedTemplate:
        """
        Customize a template based on specific context and preferences.
        
        Args:
            template: The base template to customize
            customization_context: Context-specific customization parameters
            
        Returns:
            GeneratedTemplate: Customized template
        """
        logger.info(f"Customizing template {template.template_id}")
        
        # Create a copy of the template for customization
        customized_template = self._copy_template(template)
        
        # Apply context-specific customizations
        customized_template = self._apply_context_customizations(customized_template, customization_context)
        
        # Apply preference-based customizations
        customized_template = self._apply_preference_customizations(customized_template, customization_context)
        
        # Update template metadata
        customized_template.template_id = f"{template.template_id}_customized"
        customized_template.customization_parameters.update(customization_context)
        
        # Recalculate quality score after customization
        customized_template.quality_score = self._recalculate_quality_after_customization(
            customized_template, template.quality_score
        )
        
        logger.info(f"Customized template with quality score {customized_template.quality_score:.2f}")
        return customized_template
    
    def _copy_template(self, template: GeneratedTemplate) -> GeneratedTemplate:
        """Create a deep copy of the template"""
        return GeneratedTemplate(
            template_id=template.template_id,
            template_type=template.template_type,
            title=template.title,
            description=template.description,
            components=[self._copy_component(c) for c in template.components],
            context=template.context.copy(),
            quality_score=template.quality_score,
            confidence_score=template.confidence_score,
            created_at=template.created_at,
            source_patterns=template.source_patterns.copy(),
            customization_parameters=template.customization_parameters.copy()
        )
    
    def _copy_component(self, component: TemplateComponent) -> TemplateComponent:
        """Create a deep copy of a template component"""
        return TemplateComponent(
            component_id=component.component_id,
            component_type=component.component_type,
            content=json.loads(json.dumps(component.content)),  # Deep copy
            metadata=component.metadata.copy(),
            weight=component.weight,
            source_patterns=component.source_patterns.copy()
        )
    
    def _apply_context_customizations(self, template: GeneratedTemplate, 
                                    context: Dict[str, Any]) -> GeneratedTemplate:
        """Apply context-specific customizations"""
        # Scale-based customizations
        if 'scale' in context:
            template = self._apply_scale_customizations(template, context['scale'])
        
        # Environment-based customizations
        if 'environment' in context:
            template = self._apply_environment_customizations(template, context['environment'])
        
        # Budget-based customizations
        if 'budget_tier' in context:
            template = self._apply_budget_customizations(template, context['budget_tier'])
        
        return template
    
    def _apply_preference_customizations(self, template: GeneratedTemplate, 
                                       context: Dict[str, Any]) -> GeneratedTemplate:
        """Apply preference-based customizations"""
        preferences = context.get('preferences', {})
        
        # Security preference customizations
        if 'security_level' in preferences:
            template = self._apply_security_customizations(template, preferences['security_level'])
        
        # Performance preference customizations
        if 'performance_priority' in preferences:
            template = self._apply_performance_customizations(template, preferences['performance_priority'])
        
        # Technology preference customizations
        if 'preferred_technologies' in preferences:
            template = self._apply_technology_customizations(template, preferences['preferred_technologies'])
        
        return template
    
    def _apply_scale_customizations(self, template: GeneratedTemplate, scale: str) -> GeneratedTemplate:
        """Apply customizations based on scale requirements"""
        for component in template.components:
            if component.component_type == 'service_composition':
                if scale == 'large':
                    # Add auto-scaling and load balancing for large scale
                    if 'auto_scaling' not in component.content:
                        component.content['auto_scaling'] = {
                            'enabled': True,
                            'min_capacity': 2,
                            'max_capacity': 100
                        }
                elif scale == 'small':
                    # Optimize for cost in small scale
                    if 'cost_optimization' not in component.content:
                        component.content['cost_optimization'] = {
                            'use_spot_instances': True,
                            'reserved_capacity': False
                        }
        
        return template
    
    def _apply_environment_customizations(self, template: GeneratedTemplate, environment: str) -> GeneratedTemplate:
        """Apply customizations based on environment (dev/staging/prod)"""
        for component in template.components:
            if environment == 'production':
                # Add production-specific configurations
                component.content['monitoring'] = {
                    'detailed_monitoring': True,
                    'alerting': True,
                    'backup_enabled': True
                }
            elif environment == 'development':
                # Add development-specific configurations
                component.content['development'] = {
                    'debug_mode': True,
                    'cost_optimization': True,
                    'simplified_setup': True
                }
        
        return template
    
    def _apply_budget_customizations(self, template: GeneratedTemplate, budget_tier: str) -> GeneratedTemplate:
        """Apply customizations based on budget constraints"""
        for component in template.components:
            if budget_tier == 'low':
                # Optimize for cost
                component.content['cost_optimization'] = {
                    'use_free_tier': True,
                    'minimal_resources': True,
                    'spot_instances': True
                }
            elif budget_tier == 'high':
                # Optimize for performance
                component.content['performance_optimization'] = {
                    'provisioned_capacity': True,
                    'premium_services': True,
                    'multi_az': True
                }
        
        return template
    
    def _apply_security_customizations(self, template: GeneratedTemplate, security_level: str) -> GeneratedTemplate:
        """Apply security-based customizations"""
        for component in template.components:
            if security_level == 'high':
                component.content['security'] = {
                    'encryption_at_rest': True,
                    'encryption_in_transit': True,
                    'vpc_isolation': True,
                    'audit_logging': True,
                    'mfa_required': True
                }
            elif security_level == 'basic':
                component.content['security'] = {
                    'encryption_at_rest': True,
                    'basic_authentication': True
                }
        
        return template
    
    def _apply_performance_customizations(self, template: GeneratedTemplate, performance_priority: str) -> GeneratedTemplate:
        """Apply performance-based customizations"""
        for component in template.components:
            if performance_priority == 'high':
                component.content['performance'] = {
                    'provisioned_concurrency': True,
                    'caching_enabled': True,
                    'optimized_instance_types': True
                }
            elif performance_priority == 'balanced':
                component.content['performance'] = {
                    'auto_scaling': True,
                    'basic_caching': True
                }
        
        return template
    
    def _apply_technology_customizations(self, template: GeneratedTemplate, preferred_technologies: List[str]) -> GeneratedTemplate:
        """Apply technology preference customizations"""
        for component in template.components:
            if component.component_type == 'code_structure':
                # Update language preferences
                if 'python' in preferred_technologies:
                    component.metadata['language'] = 'python'
                elif 'nodejs' in preferred_technologies:
                    component.metadata['language'] = 'nodejs'
                
                # Update framework preferences
                if 'fastapi' in preferred_technologies:
                    component.metadata['framework'] = 'fastapi'
                elif 'express' in preferred_technologies:
                    component.metadata['framework'] = 'express'
        
        return template
    
    def _recalculate_quality_after_customization(self, customized_template: GeneratedTemplate, 
                                               original_quality: float) -> float:
        """Recalculate quality score after customization"""
        # Customization generally improves quality by making it more specific
        customization_bonus = 0.1
        
        # Check if customizations are consistent
        consistency_penalty = 0.0
        
        # Simple consistency check - in practice this would be more sophisticated
        for component in customized_template.components:
            if 'security' in component.content and 'cost_optimization' in component.content:
                # High security and aggressive cost optimization might conflict
                if (component.content['security'].get('encryption_at_rest') and 
                    component.content['cost_optimization'].get('use_free_tier')):
                    consistency_penalty += 0.05
        
        new_quality = original_quality + customization_bonus - consistency_penalty
        return min(1.0, max(0.0, new_quality))
    
    def _load_customization_rules(self) -> Dict[str, Any]:
        """Load customization rules (placeholder for future rule-based system)"""
        return {
            'scale_rules': {},
            'environment_rules': {},
            'security_rules': {},
            'performance_rules': {}
        }


class TemplateValidator:
    """Validates generated templates and calculates quality scores"""
    
    def __init__(self):
        self.validation_rules = self._load_validation_rules()
    
    def validate_template(self, template: GeneratedTemplate) -> Dict[str, Any]:
        """
        Validate a generated template and return validation results.
        
        Args:
            template: The template to validate
            
        Returns:
            Dict containing validation results and scores
        """
        logger.info(f"Validating template {template.template_id}")
        
        validation_results = {
            'template_id': template.template_id,
            'overall_score': 0.0,
            'component_scores': {},
            'validation_errors': [],
            'validation_warnings': [],
            'recommendations': []
        }
        
        # Validate individual components
        component_scores = []
        for component in template.components:
            component_result = self._validate_component(component)
            validation_results['component_scores'][component.component_id] = component_result
            component_scores.append(component_result['score'])
            
            validation_results['validation_errors'].extend(component_result.get('errors', []))
            validation_results['validation_warnings'].extend(component_result.get('warnings', []))
        
        # Validate template structure
        structure_result = self._validate_template_structure(template)
        validation_results['validation_errors'].extend(structure_result.get('errors', []))
        validation_results['validation_warnings'].extend(structure_result.get('warnings', []))
        
        # Validate template consistency
        consistency_result = self._validate_template_consistency(template)
        validation_results['validation_errors'].extend(consistency_result.get('errors', []))
        validation_results['validation_warnings'].extend(consistency_result.get('warnings', []))
        
        # Calculate overall score
        if component_scores:
            avg_component_score = sum(component_scores) / len(component_scores)
            structure_score = structure_result.get('score', 1.0)
            consistency_score = consistency_result.get('score', 1.0)
            
            validation_results['overall_score'] = (
                0.6 * avg_component_score +
                0.2 * structure_score +
                0.2 * consistency_score
            )
        
        # Generate recommendations
        validation_results['recommendations'] = self._generate_recommendations(template, validation_results)
        
        logger.info(f"Template validation complete. Score: {validation_results['overall_score']:.2f}")
        return validation_results
    
    def _validate_component(self, component: TemplateComponent) -> Dict[str, Any]:
        """Validate an individual template component"""
        result = {
            'component_id': component.component_id,
            'score': 1.0,
            'errors': [],
            'warnings': []
        }
        
        # Check component structure
        if not component.content:
            result['errors'].append("Component has no content")
            result['score'] *= 0.5
        
        if not component.component_type:
            result['errors'].append("Component has no type specified")
            result['score'] *= 0.7
        
        # Validate component-specific content
        if component.component_type == 'service_composition':
            result = self._validate_service_composition(component, result)
        elif component.component_type == 'functional_requirements':
            result = self._validate_functional_requirements(component, result)
        elif component.component_type == 'code_structure':
            result = self._validate_code_structure(component, result)
        
        return result
    
    def _validate_service_composition(self, component: TemplateComponent, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate service composition component"""
        content = component.content
        
        if 'services' not in content:
            result['errors'].append("Service composition missing services list")
            result['score'] *= 0.5
        else:
            services = content['services']
            if not isinstance(services, list) or not services:
                result['warnings'].append("Services list is empty or invalid")
                result['score'] *= 0.8
        
        return result
    
    def _validate_functional_requirements(self, component: TemplateComponent, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate functional requirements component"""
        content = component.content
        
        if not content or not isinstance(content, dict):
            result['errors'].append("Functional requirements content is invalid")
            result['score'] *= 0.5
        
        return result
    
    def _validate_code_structure(self, component: TemplateComponent, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate code structure component"""
        metadata = component.metadata
        
        if 'language' not in metadata:
            result['warnings'].append("Code structure missing language specification")
            result['score'] *= 0.9
        
        return result
    
    def _validate_template_structure(self, template: GeneratedTemplate) -> Dict[str, Any]:
        """Validate overall template structure"""
        result = {
            'score': 1.0,
            'errors': [],
            'warnings': []
        }
        
        # Check required fields
        if not template.components:
            result['errors'].append("Template has no components")
            result['score'] *= 0.3
        
        if not template.title:
            result['warnings'].append("Template has no title")
            result['score'] *= 0.9
        
        if not template.description:
            result['warnings'].append("Template has no description")
            result['score'] *= 0.9
        
        # Check component diversity
        component_types = set(c.component_type for c in template.components)
        if len(component_types) < 2:
            result['warnings'].append("Template has limited component diversity")
            result['score'] *= 0.8
        
        return result
    
    def _validate_template_consistency(self, template: GeneratedTemplate) -> Dict[str, Any]:
        """Validate template consistency"""
        result = {
            'score': 1.0,
            'errors': [],
            'warnings': []
        }
        
        # Check for conflicting configurations
        security_configs = []
        performance_configs = []
        
        for component in template.components:
            if 'security' in component.content:
                security_configs.append(component.content['security'])
            if 'performance' in component.content:
                performance_configs.append(component.content['performance'])
        
        # Check security consistency
        if len(security_configs) > 1:
            # Simple consistency check
            encryption_settings = [config.get('encryption_at_rest', False) for config in security_configs]
            if not all(encryption_settings) and any(encryption_settings):
                result['warnings'].append("Inconsistent encryption settings across components")
                result['score'] *= 0.9
        
        return result
    
    def _generate_recommendations(self, template: GeneratedTemplate, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations for template improvement"""
        recommendations = []
        
        # Recommendations based on validation errors
        if validation_results['validation_errors']:
            recommendations.append("Fix validation errors to improve template quality")
        
        # Recommendations based on component diversity
        component_types = set(c.component_type for c in template.components)
        if len(component_types) < 3:
            recommendations.append("Consider adding more diverse component types")
        
        # Recommendations based on quality score
        if validation_results['overall_score'] < 0.7:
            recommendations.append("Template quality is below recommended threshold")
        
        # Recommendations based on template type
        if template.template_type == TemplateType.ARCHITECTURE:
            has_security = any('security' in c.content for c in template.components)
            if not has_security:
                recommendations.append("Consider adding security components for architecture template")
        
        return recommendations
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules (placeholder for future rule-based system)"""
        return {
            'component_rules': {},
            'structure_rules': {},
            'consistency_rules': {}
        }


class DynamicTemplateGenerator:
    """Main class for dynamic template generation system"""
    
    def __init__(self, knowledge_base_client: BedrockKnowledgeBaseClient):
        self.kb_client = knowledge_base_client
        self.synthesizer = PatternSynthesizer()
        self.customizer = ContextAwareCustomizer()
        self.validator = TemplateValidator()
    
    def generate_template(self, template_request: TemplateRequest) -> GeneratedTemplate:
        """
        Generate a template based on the request.
        
        Args:
            template_request: The template generation request
            
        Returns:
            GeneratedTemplate: The generated template
        """
        logger.info(f"Generating {template_request.template_type.value} template")
        
        # Get relevant patterns from knowledge base
        patterns = self._get_relevant_patterns(template_request)
        
        if not patterns:
            logger.warning("No relevant patterns found for template generation")
            return self._create_fallback_template(template_request)
        
        # Synthesize template from patterns
        template = self.synthesizer.synthesize_template(patterns, template_request)
        
        # Apply context-aware customizations
        if template_request.customization_preferences:
            customization_context = {
                'preferences': template_request.customization_preferences,
                **template_request.context
            }
            template = self.customizer.customize_template(template, customization_context)
        
        # Validate the generated template
        validation_results = self.validator.validate_template(template)
        
        # Update template quality score based on validation
        template.quality_score = validation_results['overall_score']
        
        logger.info(f"Generated template {template.template_id} with quality score {template.quality_score:.2f}")
        return template
    
    def _get_relevant_patterns(self, template_request: TemplateRequest) -> List[Pattern]:
        """Get relevant patterns from knowledge base"""
        # This would integrate with the pattern learning system
        # For now, return empty list as placeholder
        return []
    
    def _create_fallback_template(self, template_request: TemplateRequest) -> GeneratedTemplate:
        """Create a basic fallback template when no patterns are available"""
        logger.info("Creating fallback template")
        
        # Create basic components based on template type
        components = []
        
        if template_request.template_type == TemplateType.REQUIREMENTS:
            components.append(TemplateComponent(
                component_id="fallback_functional_req",
                component_type="functional_requirements",
                content={"basic_functionality": True},
                metadata={"fallback": True},
                weight=0.5,
                source_patterns=[]
            ))
        elif template_request.template_type == TemplateType.ARCHITECTURE:
            components.append(TemplateComponent(
                component_id="fallback_services",
                component_type="service_composition",
                content={"services": ["lambda", "api_gateway"]},
                metadata={"fallback": True},
                weight=0.5,
                source_patterns=[]
            ))
        
        return GeneratedTemplate(
            template_id=f"fallback_{template_request.template_type.value}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            template_type=template_request.template_type,
            title=f"Basic {template_request.template_type.value.title()} Template",
            description="Fallback template generated when no patterns were available",
            components=components,
            context=template_request.context.copy(),
            quality_score=0.3,  # Low quality for fallback
            confidence_score=0.2,  # Low confidence for fallback
            created_at=datetime.now(timezone.utc),
            source_patterns=[],
            customization_parameters={}
        )