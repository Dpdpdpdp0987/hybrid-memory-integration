from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import uvicorn

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

# Initialize FastAPI app
app = FastAPI(
    title="Hybrid Memory Integration API",
    description="Real-time memory integration with Supabase and Notion with anti-hallucination mechanisms",
    version="1.0.0"
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
        "environment": settings.environment
    }


@app.post("/api/v1/query", response_model=MultiSourceResponse)
async def query_multi_source(request: QueryRequest) -> MultiSourceResponse:
    """Query multiple data sources with confidence validation."""
    all_responses: List[DataResponse] = []
    
    # Query requested sources
    if SourceType.SUPABASE in request.sources:
        try:
            # Parse query to extract potential filters
            # In production, use more sophisticated query parsing
            filters = request.additional_context or {}
            supabase_results = await supabase_client.query("your_table_name", filters)
            all_responses.extend(supabase_results)
        except Exception as e:
            print(f"Supabase query failed: {str(e)}")
    
    if SourceType.NOTION in request.sources:
        try:
            filters = request.additional_context or {}
            notion_results = await notion_client.query(filters)
            all_responses.extend(notion_results)
        except Exception as e:
            print(f"Notion query failed: {str(e)}")
    
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
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Data validation failed",
                    "issues": issues,
                    "response": response.dict()
                }
            )
    
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
            # All results failed threshold
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


@app.post("/api/v1/webhooks/supabase")
async def supabase_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks
):
    """Webhook endpoint for Supabase real-time updates."""
    # Validate webhook payload
    if payload.source != SourceType.SUPABASE:
        raise HTTPException(
            status_code=400,
            detail="Invalid source type for Supabase webhook"
        )
    
    # Process webhook in background
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


@app.post("/api/v1/prompt/generate")
async def generate_llm_prompt(request: QueryRequest):
    """Generate anti-hallucination LLM prompt from query."""
    # Query data sources
    all_responses: List[DataResponse] = []
    
    if SourceType.SUPABASE in request.sources:
        filters = request.additional_context or {}
        supabase_results = await supabase_client.query("your_table_name", filters)
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
        
        return {
            "prompt": prompt_template.dict(),
            "should_use_dont_know": True,
            "dont_know_response": dont_know_response,
            "aggregated_confidence": aggregated_confidence
        }
    
    return {
        "prompt": prompt_template.dict(),
        "should_use_dont_know": False,
        "aggregated_confidence": aggregated_confidence
    }


async def process_webhook(payload: WebhookPayload):
    """Process webhook payload in background."""
    print(f"Processing webhook: {payload.event_type} for {payload.source} - {payload.record_id}")
    
    # Here you would implement your webhook processing logic:
    # - Update local cache
    # - Trigger re-indexing
    # - Send notifications
    # - Update confidence scores
    # etc.
    
    # Example: Log the event
    print(f"Webhook data: {payload.data}")
    print(f"Timestamp: {payload.timestamp}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development"
    )