from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
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
from datetime import datetime

# Import webhook router
from webhook_router import router as webhook_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.environment == "production" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Hybrid Memory Integration API",
    description="Real-time memory integration with Supabase and Notion with anti-hallucination mechanisms",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include webhook router
app.include_router(webhook_router)

# Initialize clients
supabase_client = SupabaseClient()
notion_client = NotionDatabaseClient()
validator = DataValidator()


@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    logger.info("="*60)
    logger.info("Hybrid Memory Integration API Starting")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Confidence Threshold: {settings.confidence_threshold}")
    logger.info(f"Host: {settings.host}:{settings.port}")
    logger.info("="*60)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler."""
    logger.info("Hybrid Memory Integration API Shutting Down")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Hybrid Memory Integration API",
        "version": "1.0.0",
        "status": "operational",
        "confidence_threshold": settings.confidence_threshold,
        "supported_sources": ["supabase", "notion"],
        "endpoints": {
            "query": "/api/v1/query",
            "query_supabase": "/api/v1/query/supabase",
            "query_notion": "/api/v1/query/notion",
            "webhooks": {
                "supabase": "/api/v1/webhooks/supabase",
                "notion": "/api/v1/webhooks/notion",
                "stats": "/api/v1/webhooks/stats",
                "test": "/api/v1/webhooks/test"
            },
            "prompt_generation": "/api/v1/prompt/generate",
            "health": "/health",
            "docs": "/docs"
        },
        "features": [
            "Multi-source data integration",
            "Confidence scoring",
            "Anti-hallucination mechanisms",
            "Real-time webhook support",
            "Background task processing",
            "Automatic retry logic",
            "Signature verification"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Could add database connectivity checks here
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.environment,
            "services": {
                "api": "operational",
                "supabase": "configured",
                "notion": "configured"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.post("/api/v1/query", response_model=MultiSourceResponse)
async def query_multi_source(request: QueryRequest) -> MultiSourceResponse:
    """
    Query multiple data sources with confidence validation.
    
    This endpoint queries Supabase and/or Notion databases based on the
    provided query string and returns results with confidence scores and
    source metadata.
    
    Features:
    - Parallel querying of multiple sources
    - Confidence score calculation
    - Source verification
    - Anti-hallucination validation
    
    Args:
        request: QueryRequest containing query string and sources
        
    Returns:
        MultiSourceResponse with aggregated results
    """
    logger.info(f"Multi-source query received: '{request.query}'")
    logger.debug(f"Query sources: {[s.value for s in request.sources]}")
    
    all_responses: List[DataResponse] = []
    
    # Query requested sources
    if SourceType.SUPABASE in request.sources:
        try:
            # Parse query to extract potential filters
            # In production, use more sophisticated query parsing
            filters = request.additional_context or {}
            table_name = filters.pop("table", "your_table_name")
            
            logger.debug(f"Querying Supabase table '{table_name}' with filters: {filters}")
            supabase_results = await supabase_client.query(table_name, filters)
            all_responses.extend(supabase_results)
            logger.info(f"Supabase returned {len(supabase_results)} results")
        except Exception as e:
            logger.error(f"Supabase query failed: {str(e)}", exc_info=True)
    
    if SourceType.NOTION in request.sources:
        try:
            filters = request.additional_context or {}
            logger.debug(f"Querying Notion with filters: {filters}")
            notion_results = await notion_client.query(filters)
            all_responses.extend(notion_results)
            logger.info(f"Notion returned {len(notion_results)} results")
        except Exception as e:
            logger.error(f"Notion query failed: {str(e)}", exc_info=True)
    
    # Calculate aggregated confidence
    aggregated_confidence = validator.calculate_aggregated_confidence(all_responses)
    logger.debug(f"Aggregated confidence: {aggregated_confidence}")
    
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
    
    logger.info(f"Query completed successfully. Meets threshold: {meets_threshold}")
    return response


@app.post("/api/v1/query/supabase", response_model=List[DataResponse])
async def query_supabase(
    table: str,
    filters: Optional[Dict[str, Any]] = None
) -> List[DataResponse]:
    """
    Query Supabase database directly.
    
    Direct access to Supabase without multi-source aggregation.
    
    Args:
        table: Table name to query
        filters: Optional filters as key-value pairs
        
    Returns:
        List of DataResponse objects
    """
    logger.info(f"Direct Supabase query: table={table}, filters={filters}")
    
    try:
        results = await supabase_client.query(table, filters)
        
        # Enforce confidence threshold
        valid_results = validator.enforce_confidence_threshold(results)
        
        if not valid_results and results:
            logger.warning("All results below confidence threshold")
            # All results failed threshold
            raise HTTPException(
                status_code=200,
                detail={
                    "message": "Data found but below confidence threshold",
                    "results": [r.dict() for r in results]
                }
            )
        
        logger.info(f"Supabase query returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Supabase query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query/notion", response_model=List[DataResponse])
async def query_notion(
    filters: Optional[Dict[str, Any]] = None
) -> List[DataResponse]:
    """
    Query Notion database directly.
    
    Direct access to Notion without multi-source aggregation.
    
    Args:
        filters: Optional filters for Notion query
        
    Returns:
        List of DataResponse objects
    """
    logger.info(f"Direct Notion query: filters={filters}")
    
    try:
        results = await notion_client.query(filters)
        
        # Enforce confidence threshold
        valid_results = validator.enforce_confidence_threshold(results)
        
        if not valid_results and results:
            logger.warning("All results below confidence threshold")
            raise HTTPException(
                status_code=200,
                detail={
                    "message": "Data found but below confidence threshold",
                    "results": [r.dict() for r in results]
                }
            )
        
        logger.info(f"Notion query returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Notion query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/prompt/generate")
async def generate_llm_prompt(request: QueryRequest):
    """
    Generate anti-hallucination LLM prompt from query.
    
    Creates a specialized prompt template with retrieved data and
    strict anti-hallucination instructions for LLM consumption.
    
    Features:
    - Retrieves data from specified sources
    - Calculates confidence scores
    - Generates system and user prompts
    - Provides "I don't know" response when appropriate
    
    Args:
        request: QueryRequest with query and sources
        
    Returns:
        Prompt template with metadata and confidence information
    """
    logger.info(f"Generating LLM prompt for query: '{request.query}'")
    
    # Query data sources
    all_responses: List[DataResponse] = []
    
    if SourceType.SUPABASE in request.sources:
        filters = request.additional_context or {}
        table_name = filters.pop("table", "your_table_name")
        supabase_results = await supabase_client.query(table_name, filters)
        all_responses.extend(supabase_results)
    
    if SourceType.NOTION in request.sources:
        filters = request.additional_context or {}
        notion_results = await notion_client.query(filters)
        all_responses.extend(notion_results)
    
    # Generate prompt template
    threshold = request.confidence_threshold or settings.confidence_threshold
    prompt_template = AntiHallucinationPrompts.create_template(
        request.query,
        all_responses,
        threshold
    )
    
    # Check if we should return "I don't know"
    aggregated_confidence = validator.calculate_aggregated_confidence(all_responses)
    
    if aggregated_confidence < threshold or all(r.information_not_found for r in all_responses):
        reason = "Insufficient data or confidence below threshold"
        dont_know_response = AntiHallucinationPrompts.format_dont_know_response(
            reason,
            all_responses
        )
        
        logger.info(f"Low confidence ({aggregated_confidence}), recommending 'I don't know' response")
        
        return {
            "prompt": prompt_template.dict(),
            "should_use_dont_know": True,
            "dont_know_response": dont_know_response,
            "aggregated_confidence": aggregated_confidence,
            "threshold": threshold,
            "reason": reason
        }
    
    logger.info(f"Prompt generated successfully. Confidence: {aggregated_confidence}")
    return {
        "prompt": prompt_template.dict(),
        "should_use_dont_know": False,
        "aggregated_confidence": aggregated_confidence,
        "threshold": threshold
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level="info" if settings.environment == "production" else "debug"
    )
