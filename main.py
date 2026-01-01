from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import uvicorn
import logging

from config import settings
from models import (
    QueryRequest,
    MultiSourceResponse,
    DataResponse,
    WebhookPayload,
    SourceType,
    ConfidenceScore
)
from database_clients import SupabaseClient, NotionDatabaseClient
from validators import DataValidator
from prompt_templates import AntiHallucinationPrompts
from prompt_integration import (
    PromptGenerator, 
    PromptStrictnessLevel,
    generate_strict_prompt,
    generate_adaptive_prompt,
    validate_response
)
from datetime import datetime
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Hybrid Memory Integration API",
    description="Real-time memory integration with Supabase and Notion with enhanced anti-hallucination mechanisms",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
supabase_client = SupabaseClient()
notion_client = NotionDatabaseClient()
validator = DataValidator()
prompt_generator = PromptGenerator(validator=validator, default_strictness="strict")


class PromptGenerationRequest(BaseModel):
    """Request model for prompt generation with strictness control."""
    query: str
    sources: List[SourceType] = [SourceType.SUPABASE, SourceType.NOTION]
    confidence_threshold: Optional[float] = None
    strictness_level: Optional[str] = None
    auto_detect_strictness: bool = True
    use_cache: bool = False
    additional_context: Optional[Dict[str, Any]] = None


class ValidationRequest(BaseModel):
    """Request model for LLM response validation."""
    query: str
    llm_response: str
    sources: List[SourceType] = [SourceType.SUPABASE, SourceType.NOTION]
    strict_validation: bool = True
    additional_context: Optional[Dict[str, Any]] = None


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Hybrid Memory Integration API",
        "version": "2.0.0",
        "status": "operational",
        "confidence_threshold": settings.confidence_threshold,
        "supported_sources": ["supabase", "notion"],
        "new_features": [
            "Enhanced anti-hallucination prompts",
            "Multi-level strictness (strict/moderate/lenient)",
            "Automatic strictness detection",
            "Response validation",
            "Conflict detection",
            "Prompt caching",
            "Metrics tracking"
        ],
        "endpoints": {
            "query": "/api/v1/query",
            "query_supabase": "/api/v1/query/supabase",
            "query_notion": "/api/v1/query/notion",
            "prompt_generate": "/api/v1/prompt/generate",
            "prompt_generate_adaptive": "/api/v1/prompt/generate/adaptive",
            "prompt_validate": "/api/v1/prompt/validate",
            "prompt_compare": "/api/v1/prompt/compare",
            "prompt_metrics": "/api/v1/prompt/metrics",
            "webhooks": "/api/v1/webhooks",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
        "prompt_generator": {
            "cache_size": len(prompt_generator.prompt_cache),
            "prompts_generated": prompt_generator._metrics["prompts_generated"]
        }
    }


@app.post("/api/v1/query", response_model=MultiSourceResponse)
async def query_multi_source(request: QueryRequest) -> MultiSourceResponse:
    """Query multiple data sources with confidence validation."""
    logger.info(f"Multi-source query received: {request.query[:100]}")
    
    all_responses: List[DataResponse] = []
    
    # Query requested sources
    if SourceType.SUPABASE in request.sources:
        try:
            filters = request.additional_context or {}
            supabase_results = await supabase_client.query("your_table_name", filters)
            all_responses.extend(supabase_results)
            logger.info(f"Supabase returned {len(supabase_results)} results")
        except Exception as e:
            logger.error(f"Supabase query failed: {str(e)}")
    
    if SourceType.NOTION in request.sources:
        try:
            filters = request.additional_context or {}
            notion_results = await notion_client.query(filters)
            all_responses.extend(notion_results)
            logger.info(f"Notion returned {len(notion_results)} results")
        except Exception as e:
            logger.error(f"Notion query failed: {str(e)}")
    
    # Calculate aggregated confidence
    aggregated_confidence = validator.calculate_aggregated_confidence(all_responses)
    
    # Determine threshold
    threshold = request.confidence_threshold or settings.confidence_threshold
    meets_threshold = aggregated_confidence >= threshold
    
    # Check if all sources returned no information
    information_not_found = all(r.information_not_found for r in all_responses)
    
    response = MultiSourceResponse(
        query=request.query,
        sources=all_responses,
        aggregated_confidence=aggregated_confidence,
        meets_threshold=meets_threshold,
        information_not_found=information_not_found
    )
    
    # Validate response
    if request.require_verification:
        is_valid, issues = validator.validate_multi_source(response)
        if not is_valid:
            logger.warning(f"Validation failed: {issues}")
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Data validation failed",
                    "issues": issues,
                    "response": response.dict()
                }
            )
    
    logger.info(f"Query completed with confidence {aggregated_confidence:.3f}")
    return response


@app.post("/api/v1/query/supabase", response_model=List[DataResponse])
async def query_supabase(
    table: str,
    filters: Optional[Dict[str, Any]] = None
) -> List[DataResponse]:
    """Query Supabase database directly."""
    try:
        results = await supabase_client.query(table, filters)
        
        # Enforce confidence threshold
        valid_results = validator.enforce_confidence_threshold(results)
        
        if not valid_results and results:
            raise HTTPException(
                status_code=200,
                detail={
                    "message": "Data found but below confidence threshold",
                    "results": [r.dict() for r in results]
                }
            )
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query/notion", response_model=List[DataResponse])
async def query_notion(
    filters: Optional[Dict[str, Any]] = None
) -> List[DataResponse]:
    """Query Notion database directly."""
    try:
        results = await notion_client.query(filters)
        
        # Enforce confidence threshold
        valid_results = validator.enforce_confidence_threshold(results)
        
        if not valid_results and results:
            raise HTTPException(
                status_code=200,
                detail={
                    "message": "Data found but below confidence threshold",
                    "results": [r.dict() for r in results]
                }
            )
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/prompt/generate")
async def generate_llm_prompt(request: PromptGenerationRequest):
    """
    Generate anti-hallucination LLM prompt with specified or auto-detected strictness.
    
    Supports three strictness levels:
    - strict: Maximum anti-hallucination enforcement (medical, legal, financial)
    - moderate: Balanced approach (general use)
    - lenient: Flexible but accurate (exploratory, creative)
    """
    logger.info(f"Prompt generation requested: {request.query[:100]}")
    
    # Query data sources
    all_responses: List[DataResponse] = []
    
    if SourceType.SUPABASE in request.sources:
        try:
            filters = request.additional_context or {}
            supabase_results = await supabase_client.query("your_table_name", filters)
            all_responses.extend(supabase_results)
        except Exception as e:
            logger.error(f"Supabase query failed: {str(e)}")
    
    if SourceType.NOTION in request.sources:
        try:
            filters = request.additional_context or {}
            notion_results = await notion_client.query(filters)
            all_responses.extend(notion_results)
        except Exception as e:
            logger.error(f"Notion query failed: {str(e)}")
    
    # Generate prompt using PromptGenerator
    result = prompt_generator.generate_prompt(
        query=request.query,
        retrieved_data=all_responses,
        confidence_threshold=request.confidence_threshold,
        strictness_level=request.strictness_level,
        auto_detect_strictness=request.auto_detect_strictness,
        use_cache=request.use_cache
    )
    
    logger.info(
        f"Generated {result.strictness_level} prompt with confidence {result.aggregated_confidence:.3f}, "
        f"should_use_dont_know={result.should_use_dont_know}"
    )
    
    return result.to_dict()


@app.post("/api/v1/prompt/generate/adaptive")
async def generate_adaptive_llm_prompt(request: QueryRequest):
    """
    Generate adaptive anti-hallucination prompt with automatic strictness detection.
    
    This endpoint automatically selects the optimal strictness level based on:
    - Data quality and confidence scores
    - Number of verified sources
    - Presence of data conflicts
    """
    logger.info(f"Adaptive prompt generation: {request.query[:100]}")
    
    # Query data sources
    all_responses: List[DataResponse] = []
    
    if SourceType.SUPABASE in request.sources:
        try:
            filters = request.additional_context or {}
            supabase_results = await supabase_client.query("your_table_name", filters)
            all_responses.extend(supabase_results)
        except Exception as e:
            logger.error(f"Supabase query failed: {str(e)}")
    
    if SourceType.NOTION in request.sources:
        try:
            filters = request.additional_context or {}
            notion_results = await notion_client.query(filters)
            all_responses.extend(notion_results)
        except Exception as e:
            logger.error(f"Notion query failed: {str(e)}")
    
    # Use convenience function for adaptive generation
    result = generate_adaptive_prompt(
        query=request.query,
        retrieved_data=all_responses,
        confidence_threshold=request.confidence_threshold
    )
    
    logger.info(f"Auto-selected strictness: {result.strictness_level}")
    
    return result.to_dict()


@app.post("/api/v1/prompt/validate")
async def validate_llm_response(request: ValidationRequest):
    """
    Validate an LLM response for hallucinations and accuracy.
    
    Checks:
    - Source citation compliance
    - Confidence threshold respect
    - "I don't know" usage when required
    - Data presence verification
    - Hallucination detection
    """
    logger.info(f"Response validation requested for query: {request.query[:100]}")
    
    # Query data sources to get what was available
    all_responses: List[DataResponse] = []
    
    if SourceType.SUPABASE in request.sources:
        try:
            filters = request.additional_context or {}
            supabase_results = await supabase_client.query("your_table_name", filters)
            all_responses.extend(supabase_results)
        except Exception as e:
            logger.error(f"Supabase query failed: {str(e)}")
    
    if SourceType.NOTION in request.sources:
        try:
            filters = request.additional_context or {}
            notion_results = await notion_client.query(filters)
            all_responses.extend(notion_results)
        except Exception as e:
            logger.error(f"Notion query failed: {str(e)}")
    
    # Validate response
    validation_result = prompt_generator.validate_llm_response(
        query=request.query,
        llm_response=request.llm_response,
        retrieved_data=all_responses,
        strict_validation=request.strict_validation
    )
    
    logger.info(f"Validation result: {'PASS' if validation_result['is_valid'] else 'FAIL'}")
    
    return {
        **validation_result,
        "query": request.query,
        "sources_checked": len(all_responses),
        "strictness": "strict" if request.strict_validation else "lenient"
    }


@app.post("/api/v1/prompt/compare")
async def compare_multi_source(request: QueryRequest):
    """
    Generate comparison prompt for multi-source data with conflict detection.
    
    Useful when:
    - Data conflicts exist between sources
    - Synthesizing information from multiple sources
    - Need explicit conflict acknowledgment
    """
    logger.info(f"Multi-source comparison requested: {request.query[:100]}")
    
    # Query all sources
    all_responses: List[DataResponse] = []
    
    if SourceType.SUPABASE in request.sources:
        try:
            filters = request.additional_context or {}
            supabase_results = await supabase_client.query("your_table_name", filters)
            all_responses.extend(supabase_results)
        except Exception as e:
            logger.error(f"Supabase query failed: {str(e)}")
    
    if SourceType.NOTION in request.sources:
        try:
            filters = request.additional_context or {}
            notion_results = await notion_client.query(filters)
            all_responses.extend(notion_results)
        except Exception as e:
            logger.error(f"Notion query failed: {str(e)}")
    
    # Create multi-source response
    aggregated_confidence = validator.calculate_aggregated_confidence(all_responses)
    threshold = request.confidence_threshold or settings.confidence_threshold
    
    multi_response = MultiSourceResponse(
        query=request.query,
        sources=all_responses,
        aggregated_confidence=aggregated_confidence,
        meets_threshold=aggregated_confidence >= threshold,
        information_not_found=all(r.information_not_found for r in all_responses)
    )
    
    # Detect conflicts
    conflicts = prompt_generator.detect_conflicts(all_responses)
    
    # Generate comparison prompt
    comparison_prompt = prompt_generator.create_multi_source_comparison(
        query=request.query,
        multi_response=multi_response,
        confidence_threshold=threshold
    )
    
    logger.info(
        f"Comparison generated: {len(all_responses)} sources, "
        f"conflicts={'YES' if conflicts['has_conflicts'] else 'NO'}"
    )
    
    return {
        "comparison_prompt": comparison_prompt,
        "conflict_analysis": conflicts,
        "multi_source_response": multi_response.dict(),
        "aggregated_confidence": aggregated_confidence,
        "meets_threshold": multi_response.meets_threshold
    }


@app.get("/api/v1/prompt/metrics")
async def get_prompt_metrics():
    """
    Get prompt generation metrics and statistics.
    
    Provides insights into:
    - Total prompts generated
    - Strictness level distribution
    - Cache performance
    - "I don't know" response rate
    """
    metrics = prompt_generator.get_metrics()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "configuration": {
            "default_strictness": prompt_generator.default_strictness,
            "confidence_threshold": validator.confidence_threshold
        }
    }


@app.post("/api/v1/prompt/metrics/reset")
async def reset_prompt_metrics():
    """Reset prompt generation metrics."""
    prompt_generator.reset_metrics()
    
    return {
        "status": "success",
        "message": "Metrics reset successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.delete("/api/v1/prompt/cache")
async def clear_prompt_cache():
    """Clear the prompt cache."""
    prompt_generator.clear_cache()
    
    return {
        "status": "success",
        "message": "Prompt cache cleared",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/webhooks/supabase")
async def supabase_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks
):
    """Webhook endpoint for Supabase real-time updates."""
    if payload.source != SourceType.SUPABASE:
        raise HTTPException(
            status_code=400,
            detail="Invalid source type for Supabase webhook"
        )
    
    background_tasks.add_task(process_webhook, payload)
    
    return {
        "status": "accepted",
        "message": "Webhook payload received and queued for processing",
        "event_type": payload.event_type,
        "record_id": payload.record_id
    }


@app.post("/api/v1/webhooks/notion")
async def notion_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks
):
    """Webhook endpoint for Notion real-time updates."""
    if payload.source != SourceType.NOTION:
        raise HTTPException(
            status_code=400,
            detail="Invalid source type for Notion webhook"
        )
    
    background_tasks.add_task(process_webhook, payload)
    
    return {
        "status": "accepted",
        "message": "Webhook payload received and queued for processing",
        "event_type": payload.event_type,
        "record_id": payload.record_id
    }


async def process_webhook(payload: WebhookPayload):
    """Process webhook payload in background."""
    logger.info(f"Processing webhook: {payload.event_type} for {payload.source} - {payload.record_id}")
    
    # Clear cache on data updates to ensure fresh prompts
    if payload.event_type in ["insert", "update", "delete"]:
        prompt_generator.clear_cache()
        logger.info("Prompt cache cleared due to data update")
    
    # Additional webhook processing logic here
    logger.info(f"Webhook processed: {payload.record_id}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development"
    )
