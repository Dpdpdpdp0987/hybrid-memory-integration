"""
Unit Tests for Anti-Hallucination Prompt System
"""

import pytest
from datetime import datetime
from typing import List

from models import (
    DataResponse, 
    SourceMetadata, 
    ConfidenceScore, 
    SourceType,
    MultiSourceResponse
)
from prompt_templates import AntiHallucinationPrompts
from prompt_integration import PromptGenerator, PromptStrictnessLevel
from validators import DataValidator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_data_response() -> DataResponse:
    """Create a sample DataResponse for testing."""
    return DataResponse(
        data={"test_field": "test_value", "amount": 100},
        source_metadata=SourceMetadata(
            source_type=SourceType.SUPABASE,
            source_id="test-123",
            table_name="test_table",
            retrieved_at=datetime.utcnow(),
            query_params={"filter": "test"},
            raw_data_hash="abc123"
        ),
        confidence=ConfidenceScore(
            score=0.90,
            reasoning="High confidence test data",
            factors={"completeness": 0.9, "filter_match": 0.85}
        ),
        information_not_found=False,
        verified=True,
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def low_confidence_response() -> DataResponse:
    """Create a low confidence DataResponse."""
    return DataResponse(
        data={"test_field": "uncertain_value"},
        source_metadata=SourceMetadata(
            source_type=SourceType.NOTION,
            source_id="test-456",
            table_name="test_table"
        ),
        confidence=ConfidenceScore(
            score=0.60,
            reasoning="Low confidence due to incomplete data",
            factors={"completeness": 0.5, "filter_match": 0.7}
        ),
        information_not_found=False,
        verified=True,
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def no_data_response() -> DataResponse:
    """Create a response with no data found."""
    return DataResponse(
        data=None,
        source_metadata=SourceMetadata(
            source_type=SourceType.SUPABASE,
            source_id="none",
            table_name="test_table"
        ),
        confidence=ConfidenceScore(
            score=0.0,
            reasoning="No data found",
            factors={"data_found": 0.0}
        ),
        information_not_found=True,
        verified=True,
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def validator() -> DataValidator:
    """Create a DataValidator instance."""
    return DataValidator(confidence_threshold=0.85)


@pytest.fixture
def prompt_generator(validator) -> PromptGenerator:
    """Create a PromptGenerator instance."""
    return PromptGenerator(validator=validator)


# ============================================================================
# Test AntiHallucinationPrompts
# ============================================================================

class TestAntiHallucinationPrompts:
    """Test suite for AntiHallucinationPrompts class."""
    
    def test_create_strict_system_prompt(self):
        """Test strict system prompt creation."""
        prompt = AntiHallucinationPrompts.create_strict_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "CRITICAL RULES" in prompt
        assert "NEVER" in prompt
        assert "ALWAYS" in prompt
        assert "Source:" in prompt
        
    def test_create_moderate_system_prompt(self):
        """Test moderate system prompt creation."""
        prompt = AntiHallucinationPrompts.create_moderate_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "IMPORTANT RULES" in prompt
        assert "primarily use" in prompt.lower()
        
    def test_create_lenient_system_prompt(self):
        """Test lenient system prompt creation."""
        prompt = AntiHallucinationPrompts.create_lenient_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "GUIDELINES" in prompt
        assert "helpful" in prompt.lower()
    
    def test_create_user_prompt(self, sample_data_response):
        """Test user prompt creation with data."""
        query = "What is the test value?"
        retrieved_data = [sample_data_response]
        
        prompt = AntiHallucinationPrompts.create_user_prompt(
            query=query,
            retrieved_data=retrieved_data,
            confidence_threshold=0.85
        )
        
        assert query in prompt
        assert "0.85" in prompt or "0.850" in prompt
        assert "test-123" in prompt
        assert "0.90" in prompt or "0.900" in prompt
    
    def test_create_template_strict(self, sample_data_response):
        """Test template creation with strict mode."""
        template = AntiHallucinationPrompts.create_template(
            query="Test query",
            retrieved_data=[sample_data_response],
            confidence_threshold=0.85,
            strictness_level="strict"
        )
        
        assert template.strict_mode is True
        assert template.confidence_threshold == 0.85
        assert len(template.system_prompt) > 0
        assert len(template.user_prompt) > 0
        assert len(template.retrieved_data) == 1
    
    def test_create_template_invalid_strictness(self, sample_data_response):
        """Test template creation with invalid strictness level."""
        with pytest.raises(ValueError):
            AntiHallucinationPrompts.create_template(
                query="Test",
                retrieved_data=[sample_data_response],
                strictness_level="invalid"
            )
    
    def test_format_dont_know_response(self, sample_data_response):
        """Test 'I don't know' response formatting."""
        response = AntiHallucinationPrompts.format_dont_know_response(
            reason="Test reason",
            sources=[sample_data_response],
            query="Test query",
            confidence_threshold=0.85
        )
        
        assert "I don't know" in response
        assert "Test reason" in response
        assert "0.85" in response or "0.850" in response
        assert "test-123" in response
    
    def test_detect_data_conflicts_no_conflict(self, sample_data_response):
        """Test conflict detection with matching data."""
        data1 = sample_data_response
        data2 = DataResponse(
            data={"test_field": "test_value", "amount": 100},  # Same values
            source_metadata=SourceMetadata(
                source_type=SourceType.NOTION,
                source_id="test-456"
            ),
            confidence=ConfidenceScore(score=0.88, reasoning="Test"),
            information_not_found=False,
            verified=True
        )
        
        conflicts = AntiHallucinationPrompts.detect_data_conflicts([data1, data2])
        
        assert conflicts['has_conflicts'] is False
        assert len(conflicts['conflicting_fields']) == 0
    
    def test_detect_data_conflicts_with_conflict(self, sample_data_response):
        """Test conflict detection with conflicting data."""
        data1 = sample_data_response
        data2 = DataResponse(
            data={"test_field": "different_value", "amount": 100},  # Different value
            source_metadata=SourceMetadata(
                source_type=SourceType.NOTION,
                source_id="test-456"
            ),
            confidence=ConfidenceScore(score=0.88, reasoning="Test"),
            information_not_found=False,
            verified=True
        )
        
        conflicts = AntiHallucinationPrompts.detect_data_conflicts([data1, data2])
        
        assert conflicts['has_conflicts'] is True
        assert 'test_field' in conflicts['conflicting_fields']
        assert len(conflicts['conflict_details']) > 0
    
    def test_format_citation(self, sample_data_response):
        """Test citation formatting."""
        citation = AntiHallucinationPrompts.format_citation(
            sample_data_response.source_metadata
        )
        
        assert citation == "[Source: supabase-test-123]"
    
    def test_format_citation_with_timestamp(self, sample_data_response):
        """Test citation formatting with timestamp."""
        citation = AntiHallucinationPrompts.format_citation(
            sample_data_response.source_metadata,
            include_timestamp=True
        )
        
        assert "[Source: supabase-test-123" in citation
        assert "Retrieved:" in citation


# ============================================================================
# Test PromptGenerator
# ============================================================================

class TestPromptGenerator:
    """Test suite for PromptGenerator class."""
    
    def test_initialization(self, validator):
        """Test PromptGenerator initialization."""
        generator = PromptGenerator(validator=validator, default_strictness="strict")
        
        assert generator.validator == validator
        assert generator.default_strictness == "strict"
        assert len(generator.prompt_cache) == 0
    
    def test_generate_prompt_basic(self, prompt_generator, sample_data_response):
        """Test basic prompt generation."""
        result = prompt_generator.generate_prompt(
            query="Test query",
            retrieved_data=[sample_data_response],
            confidence_threshold=0.85
        )
        
        assert result.prompt_template is not None
        assert result.aggregated_confidence > 0
        assert result.strictness_level in ["strict", "moderate", "lenient"]
        assert isinstance(result.should_use_dont_know, bool)
    
    def test_generate_prompt_with_low_confidence(self, prompt_generator, low_confidence_response):
        """Test prompt generation with low confidence data."""
        result = prompt_generator.generate_prompt(
            query="Test query",
            retrieved_data=[low_confidence_response],
            confidence_threshold=0.85
        )
        
        assert result.should_use_dont_know is True
        assert result.dont_know_response is not None
        assert "I don't know" in result.dont_know_response
    
    def test_generate_prompt_no_data(self, prompt_generator, no_data_response):
        """Test prompt generation with no data found."""
        result = prompt_generator.generate_prompt(
            query="Test query",
            retrieved_data=[no_data_response],
            confidence_threshold=0.85
        )
        
        assert result.should_use_dont_know is True
        assert result.dont_know_response is not None
    
    def test_auto_detect_strictness_high_quality(self, prompt_generator, sample_data_response):
        """Test auto-detection with high quality data."""
        # High confidence should select lenient mode
        result = prompt_generator.generate_prompt(
            query="Test query",
            retrieved_data=[sample_data_response],
            confidence_threshold=0.80,  # Lower threshold
            auto_detect_strictness=True
        )
        
        # With good data, should be lenient or moderate
        assert result.strictness_level in ["lenient", "moderate"]
    
    def test_auto_detect_strictness_low_quality(self, prompt_generator, low_confidence_response):
        """Test auto-detection with low quality data."""
        result = prompt_generator.generate_prompt(
            query="Test query",
            retrieved_data=[low_confidence_response],
            confidence_threshold=0.85,
            auto_detect_strictness=True
        )
        
        # With low quality data, should be strict
        assert result.strictness_level == "strict"
    
    def test_prompt_caching(self, prompt_generator, sample_data_response):
        """Test prompt caching functionality."""
        # First generation
        result1 = prompt_generator.generate_prompt(
            query="Test query",
            retrieved_data=[sample_data_response],
            use_cache=True
        )
        
        # Second generation with cache
        result2 = prompt_generator.generate_prompt(
            query="Test query",
            retrieved_data=[sample_data_response],
            use_cache=True
        )
        
        # Should hit cache
        metrics = prompt_generator.get_metrics()
        assert metrics['cache_hits'] > 0
    
    def test_validate_llm_response_valid(self, prompt_generator, sample_data_response):
        """Test validation of valid LLM response."""
        validation = prompt_generator.validate_llm_response(
            query="Test query",
            llm_response="The value is test_value [Source: supabase-test-123]",
            retrieved_data=[sample_data_response]
        )
        
        assert validation['has_citations'] is True
        assert validation['confidence_check_passed'] is True
    
    def test_validate_llm_response_invalid(self, prompt_generator, sample_data_response):
        """Test validation of invalid LLM response."""
        validation = prompt_generator.validate_llm_response(
            query="Test query",
            llm_response="The value is something I made up without sources",
            retrieved_data=[sample_data_response],
            strict_validation=True
        )
        
        assert validation['has_citations'] is False
        assert len(validation['issues']) > 0
    
    def test_detect_conflicts(self, prompt_generator):
        """Test conflict detection through PromptGenerator."""
        data1 = DataResponse(
            data={"price": 99.99},
            source_metadata=SourceMetadata(
                source_type=SourceType.SUPABASE,
                source_id="prod-1"
            ),
            confidence=ConfidenceScore(score=0.90, reasoning="Test"),
            information_not_found=False,
            verified=True
        )
        
        data2 = DataResponse(
            data={"price": 89.99},  # Different price
            source_metadata=SourceMetadata(
                source_type=SourceType.NOTION,
                source_id="prod-2"
            ),
            confidence=ConfidenceScore(score=0.88, reasoning="Test"),
            information_not_found=False,
            verified=True
        )
        
        conflicts = prompt_generator.detect_conflicts([data1, data2])
        
        assert conflicts['has_conflicts'] is True
        assert 'price' in conflicts['conflicting_fields']
    
    def test_get_metrics(self, prompt_generator, sample_data_response):
        """Test metrics retrieval."""
        # Generate some prompts
        prompt_generator.generate_prompt(
            query="Test 1",
            retrieved_data=[sample_data_response]
        )
        prompt_generator.generate_prompt(
            query="Test 2",
            retrieved_data=[sample_data_response]
        )
        
        metrics = prompt_generator.get_metrics()
        
        assert metrics['prompts_generated'] >= 2
        assert 'cache_hit_rate' in metrics
        assert 'dont_know_rate' in metrics
        assert 'strictness_distribution' in metrics
    
    def test_clear_cache(self, prompt_generator, sample_data_response):
        """Test cache clearing."""
        # Generate with cache
        prompt_generator.generate_prompt(
            query="Test",
            retrieved_data=[sample_data_response],
            use_cache=True
        )
        
        assert len(prompt_generator.prompt_cache) > 0
        
        prompt_generator.clear_cache()
        
        assert len(prompt_generator.prompt_cache) == 0
    
    def test_reset_metrics(self, prompt_generator, sample_data_response):
        """Test metrics reset."""
        # Generate some prompts
        prompt_generator.generate_prompt(
            query="Test",
            retrieved_data=[sample_data_response]
        )
        
        metrics_before = prompt_generator.get_metrics()
        assert metrics_before['prompts_generated'] > 0
        
        prompt_generator.reset_metrics()
        
        metrics_after = prompt_generator.get_metrics()
        assert metrics_after['prompts_generated'] == 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the complete system."""
    
    def test_full_workflow_high_confidence(self, prompt_generator, sample_data_response):
        """Test complete workflow with high confidence data."""
        # 1. Generate prompt
        result = prompt_generator.generate_prompt(
            query="What is the amount?",
            retrieved_data=[sample_data_response],
            auto_detect_strictness=True
        )
        
        # 2. Should not require "I don't know"
        assert result.should_use_dont_know is False
        
        # 3. Simulate LLM response
        llm_response = "The amount is 100 [Source: supabase-test-123]"
        
        # 4. Validate response
        validation = prompt_generator.validate_llm_response(
            query="What is the amount?",
            llm_response=llm_response,
            retrieved_data=[sample_data_response]
        )
        
        # 5. Should pass validation
        assert validation['is_valid'] is True
        assert validation['has_citations'] is True
    
    def test_full_workflow_low_confidence(self, prompt_generator, low_confidence_response):
        """Test complete workflow with low confidence data."""
        # 1. Generate prompt
        result = prompt_generator.generate_prompt(
            query="What is the value?",
            retrieved_data=[low_confidence_response],
            confidence_threshold=0.85
        )
        
        # 2. Should require "I don't know"
        assert result.should_use_dont_know is True
        assert result.dont_know_response is not None
        
        # 3. Use don't know response directly
        final_response = result.dont_know_response
        
        assert "I don't know" in final_response
        assert "confidence" in final_response.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
