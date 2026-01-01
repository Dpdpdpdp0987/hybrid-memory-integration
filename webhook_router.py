"""FastAPI router for webhook endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, Request, status
from typing import Optional, Dict, Any
import logging
import json

from models import WebhookPayload, SourceType
from webhook_handlers import (
    webhook_processor,
    webhook_metrics,
    WebhookSecurity
)
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["webhooks"]
)


@router.post(
    "/supabase",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Supabase Webhook Endpoint",
    description="Receive and process Supabase real-time database events"
)
async def supabase_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None, description="Webhook signature for verification")
) -> Dict[str, Any]:
    """
    Webhook endpoint for Supabase real-time updates.
    
    Supports:
    - INSERT events: New records created
    - UPDATE events: Existing records modified
    - DELETE events: Records removed
    
    Features:
    - Signature verification (if configured)
    - Background processing with retry logic
    - Automatic cache invalidation
    - Data verification
    
    Args:
        payload: WebhookPayload containing event data
        background_tasks: FastAPI background tasks
        request: Raw HTTP request for signature verification
        x_webhook_signature: Optional webhook signature header
    
    Returns:
        Immediate acknowledgment with processing status
    """
    logger.info(
        f"Received Supabase webhook: {payload.event_type} "
        f"for table {payload.table_name}, record {payload.record_id}"
    )
    
    # Validate source type
    if payload.source != SourceType.SUPABASE:
        logger.error(f"Invalid source type: {payload.source}, expected: supabase")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_source",
                "message": "Invalid source type for Supabase webhook",
                "expected": "supabase",
                "received": payload.source
            }
        )
    
    # Verify webhook signature (if provided and verification is enabled)
    if x_webhook_signature and hasattr(settings, 'verify_webhook_signatures'):
        if settings.verify_webhook_signatures:
            body = await request.body()
            is_valid = WebhookSecurity.verify_supabase_signature(
                body,
                x_webhook_signature
            )
            
            if not is_valid:
                logger.error("Supabase webhook signature verification failed")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "invalid_signature",
                        "message": "Webhook signature verification failed"
                    }
                )
            
            logger.info("Supabase webhook signature verified successfully")
    
    # Queue background processing
    background_tasks.add_task(
        process_webhook_with_metrics,
        payload
    )
    
    return {
        "status": "accepted",
        "message": "Webhook payload received and queued for processing",
        "details": {
            "event_type": payload.event_type,
            "source": payload.source,
            "record_id": payload.record_id,
            "table_name": payload.table_name,
            "timestamp": payload.timestamp.isoformat()
        }
    }


@router.post(
    "/notion",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Notion Webhook Endpoint",
    description="Receive and process Notion database events"
)
async def notion_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None, description="Webhook signature for verification")
) -> Dict[str, Any]:
    """
    Webhook endpoint for Notion database updates.
    
    Supports:
    - INSERT events: New pages created
    - UPDATE events: Existing pages modified
    - DELETE events: Pages archived/deleted
    
    Features:
    - Background processing with retry logic
    - Property extraction and normalization
    - Cache management
    - Sync status tracking
    
    Args:
        payload: WebhookPayload containing event data
        background_tasks: FastAPI background tasks
        request: Raw HTTP request
        x_webhook_signature: Optional webhook signature header
    
    Returns:
        Immediate acknowledgment with processing status
    """
    logger.info(
        f"Received Notion webhook: {payload.event_type} "
        f"for database {payload.table_name}, page {payload.record_id}"
    )
    
    # Validate source type
    if payload.source != SourceType.NOTION:
        logger.error(f"Invalid source type: {payload.source}, expected: notion")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_source",
                "message": "Invalid source type for Notion webhook",
                "expected": "notion",
                "received": payload.source
            }
        )
    
    # Note: Notion doesn't provide built-in webhook signatures
    # Consider implementing custom authentication if needed
    
    # Queue background processing
    background_tasks.add_task(
        process_webhook_with_metrics,
        payload
    )
    
    return {
        "status": "accepted",
        "message": "Webhook payload received and queued for processing",
        "details": {
            "event_type": payload.event_type,
            "source": payload.source,
            "record_id": payload.record_id,
            "database_id": payload.table_name,
            "timestamp": payload.timestamp.isoformat()
        }
    }


@router.get(
    "/stats",
    summary="Webhook Processing Statistics",
    description="Get metrics about webhook processing performance"
)
async def webhook_stats() -> Dict[str, Any]:
    """
    Get webhook processing statistics and metrics.
    
    Returns:
        Dictionary containing:
        - total_processed: Total successful webhooks
        - total_failed: Total failed webhooks
        - success_rate: Percentage of successful processing
        - average_processing_time: Average time to process webhooks
        - events_by_type: Breakdown by event type (insert/update/delete)
        - events_by_source: Breakdown by source (supabase/notion)
    """
    return webhook_metrics.get_stats()


@router.post(
    "/test",
    summary="Test Webhook Endpoint",
    description="Test endpoint for webhook integration testing"
)
async def test_webhook(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Test endpoint for webhook functionality.
    
    Use this endpoint to test your webhook integration without
    affecting production data.
    
    Args:
        payload: Test webhook payload
        background_tasks: FastAPI background tasks
    
    Returns:
        Test results and validation feedback
    """
    logger.info(f"Test webhook received: {payload}")
    
    # Validate payload structure
    required_fields = ["event_type", "source", "table_name", "record_id", "data"]
    missing_fields = [f for f in required_fields if f not in payload]
    
    if missing_fields:
        return {
            "status": "validation_failed",
            "missing_fields": missing_fields,
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }
    
    # Try to create a WebhookPayload
    try:
        webhook_payload = WebhookPayload(**payload)
        
        return {
            "status": "valid",
            "message": "Webhook payload is valid",
            "parsed_payload": webhook_payload.dict(),
            "would_be_processed": True
        }
    except Exception as e:
        return {
            "status": "invalid",
            "message": "Webhook payload validation failed",
            "error": str(e),
            "would_be_processed": False
        }


async def process_webhook_with_metrics(payload: WebhookPayload):
    """
    Process webhook and record metrics.
    
    This wrapper function ensures metrics are captured even if
    processing fails.
    """
    try:
        result = await webhook_processor.process_webhook(payload)
        
        if result["success"]:
            webhook_metrics.record_success(
                duration=result["duration_seconds"],
                event_type=payload.event_type,
                source=payload.source
            )
            logger.info(f"Webhook processing succeeded: {result}")
        else:
            webhook_metrics.record_failure(
                event_type=payload.event_type,
                source=payload.source
            )
            logger.error(f"Webhook processing failed: {result}")
        
        # Record retries
        if result.get("attempts", 1) > 1:
            webhook_metrics.record_retry()
        
    except Exception as e:
        logger.error(f"Unexpected error in webhook processing: {e}", exc_info=True)
        webhook_metrics.record_failure(
            event_type=payload.event_type,
            source=payload.source
        )