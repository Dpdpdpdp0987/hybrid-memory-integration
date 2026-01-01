"""
Anti-Hallucination Prompt Usage Examples
==========================================

This script demonstrates how to use the enhanced anti-hallucination prompt system
with different strictness levels and confidence thresholds.
"""

import asyncio
from typing import List
from datetime import datetime

# Mock imports - in production, use actual imports
from models import DataResponse, SourceMetadata, ConfidenceScore, SourceType
from prompt_integration import PromptGenerator, generate_strict_prompt, generate_adaptive_prompt
from validators import DataValidator


def create_mock_data_response(
    source_type: str,
    source_id: str,
    data: dict,
    confidence_score: float,
    information_not_found: bool = False
) -> DataResponse:
    """Create a mock DataResponse for testing."""
    return DataResponse(
        data=data if not information_not_found else None,
        source_metadata=SourceMetadata(
            source_type=SourceType(source_type),
            source_id=source_id,
            table_name=f"{source_type}_table",
            retrieved_at=datetime.utcnow(),
            query_params={"filter": "test"},
            raw_data_hash="abc123def456"
        ),
        confidence=ConfidenceScore(
            score=confidence_score,
            reasoning=f"Confidence based on data quality: {confidence_score:.2f}",
            factors={
                "completeness": 0.9,
                "filter_match": 0.85,
                "source_reliability": 0.95 if source_type == "supabase" else 0.90
            }
        ),
        information_not_found=information_not_found,
        verified=True,
        timestamp=datetime.utcnow(),
        additional_context=None
    )


# ============================================================================
# Example 1: Basic Strict Prompt Generation
# ============================================================================

def example_1_strict_prompt():
    """
    Example 1: Generate a strict anti-hallucination prompt
    Use case: Medical, legal, or financial queries requiring maximum accuracy
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Strict Anti-Hallucination Prompt")
    print("="*80)
    
    query = "What is the patient's current medication dosage?"
    
    # Simulate retrieved data
    retrieved_data = [
        create_mock_data_response(
            source_type="supabase",
            source_id="patient-123",
            data={
                "medication": "Metformin",
                "dosage": "500mg",
                "frequency": "twice daily",
                "last_updated": "2026-01-01"
            },
            confidence_score=0.95
        ),
        create_mock_data_response(
            source_type="notion",
            source_id="med-record-456",
            data={
                "medication": "Metformin",
                "dosage": "500mg",
                "notes": "Patient tolerating well"
            },
            confidence_score=0.92
        )
    ]
    
    # Generate strict prompt
    result = generate_strict_prompt(
        query=query,
        retrieved_data=retrieved_data,
        confidence_threshold=0.90
    )
    
    print(f"\nQuery: {query}")
    print(f"Strictness Level: {result.strictness_level}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.3f}")
    print(f"Should Use 'I Don't Know': {result.should_use_dont_know}")
    
    print("\n--- SYSTEM PROMPT (First 500 chars) ---")
    print(result.prompt_template.system_prompt[:500] + "...")
    
    print("\n--- USER PROMPT (First 800 chars) ---")
    print(result.prompt_template.user_prompt[:800] + "...")


# ============================================================================
# Example 2: Adaptive Prompt with Auto-Detection
# ============================================================================

def example_2_adaptive_prompt():
    """
    Example 2: Adaptive prompt with automatic strictness detection
    Use case: General queries where optimal strictness should be determined by data quality
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Adaptive Prompt with Auto-Detection")
    print("="*80)
    
    query = "What are the latest project updates?"
    
    # High quality data - should select lenient mode
    retrieved_data = [
        create_mock_data_response(
            source_type="supabase",
            source_id="project-789",
            data={
                "project_name": "Website Redesign",
                "status": "In Progress",
                "completion": "75%",
                "last_update": "2026-01-01"
            },
            confidence_score=0.93
        ),
        create_mock_data_response(
            source_type="notion",
            source_id="task-list-101",
            data={
                "project_name": "Website Redesign",
                "tasks_completed": 15,
                "tasks_remaining": 5,
                "next_milestone": "Launch"
            },
            confidence_score=0.91
        )
    ]
    
    # Generate adaptive prompt
    result = generate_adaptive_prompt(
        query=query,
        retrieved_data=retrieved_data,
        confidence_threshold=0.85
    )
    
    print(f"\nQuery: {query}")
    print(f"Auto-Detected Strictness: {result.strictness_level}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.3f}")
    print(f"Should Use 'I Don't Know': {result.should_use_dont_know}")
    
    print("\n--- METADATA ---")
    for key, value in result.metadata.items():
        print(f"{key}: {value}")


# ============================================================================
# Example 3: Low Confidence - "I Don't Know" Response
# ============================================================================

def example_3_low_confidence():
    """
    Example 3: Handling low confidence data
    Use case: When data quality is poor or below threshold
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Low Confidence - 'I Don't Know' Response")
    print("="*80)
    
    query = "What is the user's email address?"
    
    # Low confidence data
    retrieved_data = [
        create_mock_data_response(
            source_type="supabase",
            source_id="user-999",
            data={
                "user_id": "999",
                "email": "unknown@example.com"
            },
            confidence_score=0.60  # Below threshold
        )
    ]
    
    generator = PromptGenerator()
    result = generator.generate_prompt(
        query=query,
        retrieved_data=retrieved_data,
        confidence_threshold=0.85,
        auto_detect_strictness=True
    )
    
    print(f"\nQuery: {query}")
    print(f"Strictness Level: {result.strictness_level}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.3f}")
    print(f"Should Use 'I Don't Know': {result.should_use_dont_know}")
    
    if result.dont_know_response:
        print("\n--- 'I DON'T KNOW' RESPONSE ---")
        print(result.dont_know_response)


# ============================================================================
# Example 4: Data Conflicts Between Sources
# ============================================================================

def example_4_data_conflicts():
    """
    Example 4: Detecting and handling data conflicts
    Use case: When different sources provide conflicting information
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Data Conflicts Between Sources")
    print("="*80)
    
    query = "What is the product price?"
    
    # Conflicting data between sources
    retrieved_data = [
        create_mock_data_response(
            source_type="supabase",
            source_id="product-001",
            data={
                "product_name": "Widget Pro",
                "price": 99.99,
                "currency": "USD"
            },
            confidence_score=0.90
        ),
        create_mock_data_response(
            source_type="notion",
            source_id="catalog-002",
            data={
                "product_name": "Widget Pro",
                "price": 89.99,  # Different price!
                "currency": "USD"
            },
            confidence_score=0.88
        )
    ]
    
    generator = PromptGenerator()
    
    # Detect conflicts
    conflicts = generator.detect_conflicts(retrieved_data, field_name="price")
    
    print(f"\nQuery: {query}")
    print(f"Has Conflicts: {conflicts['has_conflicts']}")
    print(f"Conflicting Fields: {conflicts['conflicting_fields']}")
    
    if conflicts['has_conflicts']:
        print("\n--- CONFLICT DETAILS ---")
        for conflict in conflicts['conflict_details']:
            print(f"\nField: {conflict['field']}")
            print(f"  Source 1 ({conflict['source1']['type']}): {conflict['source1']['value']}")
            print(f"    Confidence: {conflict['source1']['confidence']:.3f}")
            print(f"  Source 2 ({conflict['source2']['type']}): {conflict['source2']['value']}")
            print(f"    Confidence: {conflict['source2']['confidence']:.3f}")


# ============================================================================
# Example 5: Response Validation
# ============================================================================

def example_5_response_validation():
    """
    Example 5: Validating LLM responses for hallucinations
    Use case: Verify that LLM responses comply with anti-hallucination rules
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: LLM Response Validation")
    print("="*80)
    
    query = "What is the account balance?"
    
    retrieved_data = [
        create_mock_data_response(
            source_type="supabase",
            source_id="account-555",
            data={
                "account_id": "555",
                "balance": 1500.00,
                "currency": "USD"
            },
            confidence_score=0.94
        )
    ]
    
    # Good response with citation
    good_llm_response = """
    Based on the retrieved data, the account balance is $1,500.00 USD 
    [Source: supabase-account-555].
    """
    
    # Bad response with hallucination
    bad_llm_response = """
    The account balance is $1,500.00 USD. The account was opened in 2020 
    and has an excellent credit rating.
    """
    
    generator = PromptGenerator()
    
    # Validate good response
    print("\n--- Validating GOOD Response ---")
    good_validation = generator.validate_llm_response(
        query=query,
        llm_response=good_llm_response,
        retrieved_data=retrieved_data
    )
    print(f"Valid: {good_validation['is_valid']}")
    print(f"Issues: {good_validation['issues']}")
    print(f"Has Citations: {good_validation['has_citations']}")
    
    # Validate bad response
    print("\n--- Validating BAD Response ---")
    bad_validation = generator.validate_llm_response(
        query=query,
        llm_response=bad_llm_response,
        retrieved_data=retrieved_data
    )
    print(f"Valid: {bad_validation['is_valid']}")
    print(f"Issues: {bad_validation['issues']}")
    print(f"Has Citations: {bad_validation['has_citations']}")


# ============================================================================
# Example 6: Different Strictness Levels Comparison
# ============================================================================

def example_6_strictness_comparison():
    """
    Example 6: Compare different strictness levels
    Use case: Understanding when to use each strictness level
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Strictness Levels Comparison")
    print("="*80)
    
    query = "What are the company's quarterly results?"
    
    retrieved_data = [
        create_mock_data_response(
            source_type="supabase",
            source_id="financials-q4",
            data={
                "quarter": "Q4 2025",
                "revenue": 5000000,
                "profit": 1000000
            },
            confidence_score=0.88
        )
    ]
    
    generator = PromptGenerator()
    
    for strictness in ["strict", "moderate", "lenient"]:
        result = generator.generate_prompt(
            query=query,
            retrieved_data=retrieved_data,
            confidence_threshold=0.85,
            strictness_level=strictness,
            auto_detect_strictness=False
        )
        
        print(f"\n--- {strictness.upper()} MODE ---")
        print(f"System Prompt Length: {len(result.prompt_template.system_prompt)} chars")
        print(f"Key Rules: ", end="")
        
        # Extract key characteristics
        if strictness == "strict":
            print("ZERO tolerance, ALWAYS cite, reject speculation")
        elif strictness == "moderate":
            print("Careful approach, cite main claims, qualified inferences")
        else:  # lenient
            print("Helpful focus, cite key facts, reasonable context allowed")


# ============================================================================
# Example 7: Metrics Tracking
# ============================================================================

def example_7_metrics_tracking():
    """
    Example 7: Track prompt generation metrics
    Use case: Monitor prompt usage and effectiveness
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Metrics Tracking")
    print("="*80)
    
    generator = PromptGenerator()
    
    # Generate several prompts
    queries = [
        "What is the user status?",
        "Show me recent orders",
        "What are the system metrics?"
    ]
    
    for query in queries:
        retrieved_data = [
            create_mock_data_response(
                source_type="supabase",
                source_id=f"data-{hash(query)}",
                data={"query": query, "result": "sample"},
                confidence_score=0.85 + (hash(query) % 10) * 0.01
            )
        ]
        
        generator.generate_prompt(
            query=query,
            retrieved_data=retrieved_data,
            auto_detect_strictness=True
        )
    
    # Get metrics
    metrics = generator.get_metrics()
    
    print("\n--- METRICS ---")
    print(f"Total Prompts Generated: {metrics['prompts_generated']}")
    print(f"'I Don't Know' Responses: {metrics['dont_know_responses']}")
    print(f"Don't Know Rate: {metrics['dont_know_rate']:.2%}")
    print(f"Cache Hits: {metrics['cache_hits']}")
    print(f"Cache Hit Rate: {metrics['cache_hit_rate']:.2%}")
    
    print("\n--- STRICTNESS DISTRIBUTION ---")
    for level, count in metrics['strictness_distribution'].items():
        print(f"{level.capitalize()}: {count}")


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("ANTI-HALLUCINATION PROMPT SYSTEM - USAGE EXAMPLES")
    print("="*80)
    
    examples = [
        ("Basic Strict Prompt", example_1_strict_prompt),
        ("Adaptive Auto-Detection", example_2_adaptive_prompt),
        ("Low Confidence Handling", example_3_low_confidence),
        ("Data Conflict Detection", example_4_data_conflicts),
        ("Response Validation", example_5_response_validation),
        ("Strictness Comparison", example_6_strictness_comparison),
        ("Metrics Tracking", example_7_metrics_tracking)
    ]
    
    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Example '{name}' failed: {str(e)}")
    
    print("\n" + "="*80)
    print("ALL EXAMPLES COMPLETED")
    print("="*80)


if __name__ == "__main__":
    main()
