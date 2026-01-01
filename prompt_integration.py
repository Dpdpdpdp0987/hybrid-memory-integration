"""
Prompt Integration Utilities
Provides seamless integration between anti-hallucination prompts and the hybrid memory system.
"""

from typing import List, Dict, Any, Optional, Tuple
from models import (
    QueryRequest, 
    DataResponse, 
    MultiSourceResponse, 
    LLMPromptTemplate,
    SourceType
)
from prompt_templates import AntiHallucinationPrompts
from validators import DataValidator
from config import settings
import logging
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class PromptStrictnessLevel(str, Enum):
    """Enumeration of prompt strictness levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


class PromptGenerationResult:
    """Result of prompt generation with metadata."""
    
    def __init__(
        self,
        prompt_template: LLMPromptTemplate,
        should_use_dont_know: bool,
        dont_know_response: Optional[str],
        aggregated_confidence: float,
        strictness_level: str,
        metadata: Dict[str, Any]
    ):
        self.prompt_template = prompt_template
        self.should_use_dont_know = should_use_dont_know
        self.dont_know_response = dont_know_response
        self.aggregated_confidence = aggregated_confidence
        self.strictness_level = strictness_level
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "prompt": self.prompt_template.dict(),
            "should_use_dont_know": self.should_use_dont_know,
            "dont_know_response": self.dont_know_response,
            "aggregated_confidence": self.aggregated_confidence,
            "strictness_level": self.strictness_level,
            "metadata": self.metadata
        }


class PromptGenerator:
    """
    Centralized prompt generator with confidence-aware selection and validation.
    """
    
    def __init__(
        self, 
        validator: Optional[DataValidator] = None,
        default_strictness: str = "strict"
    ):
        """
        Initialize PromptGenerator.
        
        Args:
            validator: DataValidator instance for confidence checks
            default_strictness: Default strictness level ("strict", "moderate", "lenient")
        """
        self.validator = validator or DataValidator()
        self.default_strictness = default_strictness
        self.prompt_cache: Dict[str, PromptGenerationResult] = {}
        self._metrics = {
            "prompts_generated": 0,
            "dont_know_responses": 0,
            "cache_hits": 0,
            "strictness_distribution": {
                "strict": 0,
                "moderate": 0,
                "lenient": 0
            }
        }
    
    def generate_prompt(
        self,
        query: str,
        retrieved_data: List[DataResponse],
        confidence_threshold: Optional[float] = None,
        strictness_level: Optional[str] = None,
        auto_detect_strictness: bool = True,
        use_cache: bool = False
    ) -> PromptGenerationResult:
        """
        Generate anti-hallucination prompt with optimal configuration.
        
        Args:
            query: User query string
            retrieved_data: List of data responses from sources
            confidence_threshold: Confidence threshold (uses config default if None)
            strictness_level: Force specific strictness level
            auto_detect_strictness: Automatically detect optimal strictness
            use_cache: Use cached prompts if available
            
        Returns:
            PromptGenerationResult with prompt and metadata
        """
        # Use configured threshold if not provided
        threshold = confidence_threshold or self.validator.confidence_threshold
        
        # Generate cache key
        cache_key = self._generate_cache_key(query, retrieved_data, threshold)
        
        # Check cache
        if use_cache and cache_key in self.prompt_cache:
            self._metrics["cache_hits"] += 1
            logger.info(f"Prompt cache hit for query: {query[:50]}...")
            return self.prompt_cache[cache_key]
        
        # Determine strictness level
        if strictness_level:
            selected_strictness = strictness_level
        elif auto_detect_strictness:
            selected_strictness = self._detect_optimal_strictness(
                retrieved_data, 
                threshold
            )
        else:
            selected_strictness = self.default_strictness
        
        # Calculate aggregated confidence
        aggregated_confidence = self.validator.calculate_aggregated_confidence(
            retrieved_data
        )
        
        # Check if should return "I don't know"
        multi_response = self._create_temp_multi_response(
            query, 
            retrieved_data, 
            aggregated_confidence, 
            threshold
        )
        
        should_use_dont_know = self.validator.should_return_dont_know(multi_response)
        
        # Generate prompt template
        prompt_template = AntiHallucinationPrompts.create_template(
            query=query,
            retrieved_data=retrieved_data,
            confidence_threshold=threshold,
            strictness_level=selected_strictness
        )
        
        # Generate "I don't know" response if needed
        dont_know_response = None
        if should_use_dont_know:
            reason = self._determine_dont_know_reason(
                retrieved_data, 
                aggregated_confidence, 
                threshold
            )
            dont_know_response = AntiHallucinationPrompts.format_dont_know_response(
                reason=reason,
                sources=retrieved_data,
                query=query,
                confidence_threshold=threshold,
                include_suggestions=True
            )
            self._metrics["dont_know_responses"] += 1
        
        # Create result with metadata
        result = PromptGenerationResult(
            prompt_template=prompt_template,
            should_use_dont_know=should_use_dont_know,
            dont_know_response=dont_know_response,
            aggregated_confidence=aggregated_confidence,
            strictness_level=selected_strictness,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "query": query,
                "sources_count": len(retrieved_data),
                "sources_with_data": sum(1 for s in retrieved_data if not s.information_not_found),
                "verified_sources": sum(1 for s in retrieved_data if s.verified),
                "threshold": threshold,
                "auto_detected_strictness": auto_detect_strictness,
                "cache_used": use_cache
            }
        )
        
        # Update metrics
        self._metrics["prompts_generated"] += 1
        self._metrics["strictness_distribution"][selected_strictness] += 1
        
        # Cache result
        if use_cache:
            self.prompt_cache[cache_key] = result
        
        logger.info(
            f"Generated {selected_strictness} prompt for query '{query[:50]}...' "
            f"with confidence {aggregated_confidence:.3f}"
        )
        
        return result
    
    def _detect_optimal_strictness(
        self,
        retrieved_data: List[DataResponse],
        threshold: float
    ) -> str:
        """
        Automatically detect optimal strictness level based on data quality.
        
        Returns:
            "strict", "moderate", or "lenient"
        """
        if not retrieved_data:
            return PromptStrictnessLevel.STRICT.value
        
        # Calculate quality metrics
        sources_with_data = [s for s in retrieved_data if not s.information_not_found]
        verified_sources = [s for s in retrieved_data if s.verified]
        avg_confidence = sum(s.confidence.score for s in retrieved_data) / len(retrieved_data)
        
        # Decision logic
        if len(verified_sources) == 0:
            # No verified sources - use strict
            return PromptStrictnessLevel.STRICT.value
        
        if avg_confidence < threshold - 0.10:
            # Well below threshold - use strict
            return PromptStrictnessLevel.STRICT.value
        
        if avg_confidence >= threshold + 0.05 and len(sources_with_data) >= 2:
            # Good confidence and multiple sources - can use lenient
            return PromptStrictnessLevel.LENIENT.value
        
        if avg_confidence >= threshold:
            # Meets threshold - use moderate
            return PromptStrictnessLevel.MODERATE.value
        
        # Default to strict
        return PromptStrictnessLevel.STRICT.value
    
    def _determine_dont_know_reason(
        self,
        retrieved_data: List[DataResponse],
        aggregated_confidence: float,
        threshold: float
    ) -> str:
        """Determine specific reason for "I don't know" response."""
        
        if all(s.information_not_found for s in retrieved_data):
            return "No information found in any data source."
        
        if not any(s.verified for s in retrieved_data):
            return "No data sources could be verified."
        
        if aggregated_confidence < threshold:
            return f"Data confidence ({aggregated_confidence:.3f}) is below the required threshold ({threshold:.3f})."
        
        sources_with_data = [s for s in retrieved_data if not s.information_not_found]
        if not sources_with_data:
            return "All data sources returned empty results."
        
        return "Data quality checks failed."
    
    def _create_temp_multi_response(
        self,
        query: str,
        retrieved_data: List[DataResponse],
        aggregated_confidence: float,
        threshold: float
    ) -> MultiSourceResponse:
        """Create temporary MultiSourceResponse for validation."""
        return MultiSourceResponse(
            query=query,
            sources=retrieved_data,
            aggregated_confidence=aggregated_confidence,
            meets_threshold=aggregated_confidence >= threshold,
            information_not_found=all(s.information_not_found for s in retrieved_data)
        )
    
    def _generate_cache_key(
        self,
        query: str,
        retrieved_data: List[DataResponse],
        threshold: float
    ) -> str:
        """Generate cache key for prompt."""
        import hashlib
        
        # Create deterministic key from query and data
        key_data = f"{query}:{threshold}:{len(retrieved_data)}"
        for data in retrieved_data:
            key_data += f":{data.source_metadata.source_id}:{data.confidence.score}"
        
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def validate_llm_response(
        self,
        query: str,
        llm_response: str,
        retrieved_data: List[DataResponse],
        strict_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Validate LLM response for hallucinations and accuracy.
        
        Args:
            query: Original query
            llm_response: LLM's response to validate
            retrieved_data: Data that was provided to LLM
            strict_validation: Use strict validation rules
            
        Returns:
            Dictionary with validation results
        """
        validation_prompt = AntiHallucinationPrompts.create_validation_prompt(
            query=query,
            llm_response=llm_response,
            retrieved_data=retrieved_data
        )
        
        # Basic validation checks
        issues = []
        
        # Check for source citations
        has_citations = "[Source:" in llm_response
        if not has_citations and retrieved_data:
            issues.append("Missing source citations")
        
        # Check for "I don't know" when required
        aggregated_confidence = self.validator.calculate_aggregated_confidence(retrieved_data)
        threshold = self.validator.confidence_threshold
        
        if aggregated_confidence < threshold:
            if "I don't know" not in llm_response.lower():
                issues.append(f"Should respond 'I don't know' (confidence {aggregated_confidence:.3f} < {threshold})")
        
        # Check for data presence
        if all(s.information_not_found for s in retrieved_data):
            if "I don't know" not in llm_response.lower():
                issues.append("Should respond 'I don't know' (no data found)")
        
        is_valid = len(issues) == 0 if strict_validation else len(issues) < 2
        
        return {
            "is_valid": is_valid,
            "issues": issues,
            "validation_prompt": validation_prompt,
            "has_citations": has_citations,
            "confidence_check_passed": aggregated_confidence >= threshold,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def detect_conflicts(
        self,
        retrieved_data: List[DataResponse],
        field_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect conflicts between data sources.
        
        Args:
            retrieved_data: List of data responses
            field_name: Specific field to check (optional)
            
        Returns:
            Conflict analysis dictionary
        """
        return AntiHallucinationPrompts.detect_data_conflicts(
            retrieved_data=retrieved_data,
            field_name=field_name
        )
    
    def create_multi_source_comparison(
        self,
        query: str,
        multi_response: MultiSourceResponse,
        confidence_threshold: Optional[float] = None
    ) -> str:
        """
        Create prompt for multi-source comparison and synthesis.
        
        Args:
            query: Original query
            multi_response: Multi-source response to compare
            confidence_threshold: Confidence threshold
            
        Returns:
            Comparison prompt string
        """
        threshold = confidence_threshold or self.validator.confidence_threshold
        
        return AntiHallucinationPrompts.create_multi_source_comparison_prompt(
            query=query,
            multi_response=multi_response,
            confidence_threshold=threshold
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get prompt generation metrics."""
        return {
            **self._metrics,
            "cache_size": len(self.prompt_cache),
            "cache_hit_rate": (
                self._metrics["cache_hits"] / self._metrics["prompts_generated"]
                if self._metrics["prompts_generated"] > 0 else 0.0
            ),
            "dont_know_rate": (
                self._metrics["dont_know_responses"] / self._metrics["prompts_generated"]
                if self._metrics["prompts_generated"] > 0 else 0.0
            )
        }
    
    def clear_cache(self):
        """Clear prompt cache."""
        self.prompt_cache.clear()
        logger.info("Prompt cache cleared")
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self._metrics = {
            "prompts_generated": 0,
            "dont_know_responses": 0,
            "cache_hits": 0,
            "strictness_distribution": {
                "strict": 0,
                "moderate": 0,
                "lenient": 0
            }
        }
        logger.info("Metrics reset")


# Convenience functions for quick usage

def generate_strict_prompt(
    query: str,
    retrieved_data: List[DataResponse],
    confidence_threshold: Optional[float] = None
) -> PromptGenerationResult:
    """Quick function to generate strict anti-hallucination prompt."""
    generator = PromptGenerator(default_strictness="strict")
    return generator.generate_prompt(
        query=query,
        retrieved_data=retrieved_data,
        confidence_threshold=confidence_threshold,
        strictness_level="strict",
        auto_detect_strictness=False
    )


def generate_adaptive_prompt(
    query: str,
    retrieved_data: List[DataResponse],
    confidence_threshold: Optional[float] = None
) -> PromptGenerationResult:
    """Quick function to generate adaptive prompt with auto-detected strictness."""
    generator = PromptGenerator()
    return generator.generate_prompt(
        query=query,
        retrieved_data=retrieved_data,
        confidence_threshold=confidence_threshold,
        auto_detect_strictness=True
    )


def validate_response(
    query: str,
    llm_response: str,
    retrieved_data: List[DataResponse]
) -> Dict[str, Any]:
    """Quick function to validate LLM response."""
    generator = PromptGenerator()
    return generator.validate_llm_response(
        query=query,
        llm_response=llm_response,
        retrieved_data=retrieved_data
    )
