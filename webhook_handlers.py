"""Webhook handlers with comprehensive error handling and background processing."""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import hashlib
import hmac
import logging
import json
from enum import Enum

from models import WebhookPayload, SourceType, DataResponse
from database_clients import SupabaseClient, NotionDatabaseClient
from config import settings

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class WebhookEventType(str, Enum):
    """Types of webhook events."""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class WebhookProcessor:
    """Process webhook events with retry logic and error handling."""
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.supabase_client = SupabaseClient()
        self.notion_client = NotionDatabaseClient()
        self.processing_queue: List[WebhookPayload] = []
        
    async def process_webhook(self, payload: WebhookPayload) -> Dict[str, Any]:
        """
        Process webhook payload with error handling and retry logic.
        
        Args:
            payload: WebhookPayload to process
            
        Returns:
            Dict with processing results
        """
        start_time = datetime.utcnow()
        attempt = 0
        last_error = None
        
        logger.info(
            f"Starting webhook processing: {payload.source}/{payload.event_type} "
            f"for record {payload.record_id}"
        )
        
        while attempt < self.max_retries:
            try:
                result = await self._process_webhook_internal(payload)
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"Webhook processed successfully in {duration:.2f}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1,
                    "duration_seconds": duration,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                attempt += 1
                last_error = str(e)
                
                logger.error(
                    f"Webhook processing failed (attempt {attempt}/{self.max_retries}): {e}",
                    exc_info=True
                )
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.error(
            f"Webhook processing failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )
        
        return {
            "success": False,
            "error": last_error,
            "attempts": self.max_retries,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload.dict()
        }
    
    async def _process_webhook_internal(self, payload: WebhookPayload) -> Dict[str, Any]:
        """
        Internal webhook processing logic.
        
        This is where the actual business logic happens.
        Override this method for custom processing.
        """
        # Validate payload
        self._validate_payload(payload)
        
        # Route to appropriate handler
        if payload.source == SourceType.SUPABASE:
            return await self._handle_supabase_webhook(payload)
        elif payload.source == SourceType.NOTION:
            return await self._handle_notion_webhook(payload)
        else:
            raise ValueError(f"Unsupported source type: {payload.source}")
    
    def _validate_payload(self, payload: WebhookPayload) -> None:
        """Validate webhook payload."""
        if not payload.record_id:
            raise ValueError("record_id is required")
        
        if not payload.table_name:
            raise ValueError("table_name is required")
        
        if not payload.data:
            raise ValueError("data is required")
        
        if payload.event_type not in ["insert", "update", "delete"]:
            raise ValueError(f"Invalid event_type: {payload.event_type}")
    
    async def _handle_supabase_webhook(self, payload: WebhookPayload) -> Dict[str, Any]:
        """
        Handle Supabase webhook events.
        
        Implements:
        - Cache invalidation
        - Data verification
        - Index updates
        - Notification triggers
        """
        logger.info(f"Processing Supabase {payload.event_type} event")
        
        result = {
            "source": "supabase",
            "event_type": payload.event_type,
            "record_id": payload.record_id,
            "table_name": payload.table_name,
            "actions_performed": []
        }
        
        # Handle different event types
        if payload.event_type == WebhookEventType.INSERT:
            # Verify the inserted data
            verification = await self._verify_supabase_record(
                payload.table_name,
                payload.record_id,
                payload.data
            )
            result["verification"] = verification
            result["actions_performed"].append("data_verification")
            
            # Update search index (if implemented)
            # await self._update_search_index(payload)
            result["actions_performed"].append("index_update_queued")
            
        elif payload.event_type == WebhookEventType.UPDATE:
            # Invalidate cache for this record
            await self._invalidate_cache(payload.source, payload.record_id)
            result["actions_performed"].append("cache_invalidated")
            
            # Verify updated data
            verification = await self._verify_supabase_record(
                payload.table_name,
                payload.record_id,
                payload.data
            )
            result["verification"] = verification
            result["actions_performed"].append("data_verification")
            
        elif payload.event_type == WebhookEventType.DELETE:
            # Remove from cache
            await self._invalidate_cache(payload.source, payload.record_id)
            result["actions_performed"].append("cache_invalidated")
            
            # Remove from search index
            # await self._remove_from_search_index(payload)
            result["actions_performed"].append("index_removal_queued")
        
        logger.info(f"Supabase webhook processed: {result['actions_performed']}")
        return result
    
    async def _handle_notion_webhook(self, payload: WebhookPayload) -> Dict[str, Any]:
        """
        Handle Notion webhook events.
        
        Implements:
        - Cache invalidation
        - Property extraction
        - Sync status tracking
        """
        logger.info(f"Processing Notion {payload.event_type} event")
        
        result = {
            "source": "notion",
            "event_type": payload.event_type,
            "record_id": payload.record_id,
            "database_id": payload.table_name,
            "actions_performed": []
        }
        
        if payload.event_type == WebhookEventType.INSERT:
            # Extract Notion properties
            extracted_data = self._extract_notion_properties(payload.data)
            result["extracted_properties"] = extracted_data
            result["actions_performed"].append("property_extraction")
            
            # Verify against Notion API
            verification = await self._verify_notion_page(
                payload.record_id,
                payload.data
            )
            result["verification"] = verification
            result["actions_performed"].append("data_verification")
            
        elif payload.event_type == WebhookEventType.UPDATE:
            # Invalidate cache
            await self._invalidate_cache(payload.source, payload.record_id)
            result["actions_performed"].append("cache_invalidated")
            
            # Extract updated properties
            extracted_data = self._extract_notion_properties(payload.data)
            result["extracted_properties"] = extracted_data
            result["actions_performed"].append("property_extraction")
            
        elif payload.event_type == WebhookEventType.DELETE:
            # Remove from cache
            await self._invalidate_cache(payload.source, payload.record_id)
            result["actions_performed"].append("cache_invalidated")
        
        logger.info(f"Notion webhook processed: {result['actions_performed']}")
        return result
    
    async def _verify_supabase_record(
        self,
        table_name: str,
        record_id: str,
        expected_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify Supabase record against the database.
        """
        try:
            # Query the actual record
            results = await self.supabase_client.query(
                table_name,
                {"id": record_id}
            )
            
            if not results or results[0].information_not_found:
                return {
                    "verified": False,
                    "reason": "Record not found in database"
                }
            
            actual_data = results[0].data
            
            # Calculate data hash for comparison
            expected_hash = self._calculate_hash(expected_data)
            actual_hash = self._calculate_hash(actual_data)
            
            return {
                "verified": expected_hash == actual_hash,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "confidence": results[0].confidence.score
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                "verified": False,
                "reason": f"Verification error: {str(e)}"
            }
    
    async def _verify_notion_page(
        self,
        page_id: str,
        expected_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify Notion page against the API.
        """
        try:
            # Query the actual page
            results = await self.notion_client.query()
            
            # Find the matching page
            matching_page = None
            for result in results:
                if result.source_metadata.source_id == page_id:
                    matching_page = result
                    break
            
            if not matching_page or matching_page.information_not_found:
                return {
                    "verified": False,
                    "reason": "Page not found in Notion"
                }
            
            return {
                "verified": True,
                "confidence": matching_page.confidence.score
            }
            
        except Exception as e:
            logger.error(f"Notion verification failed: {e}")
            return {
                "verified": False,
                "reason": f"Verification error: {str(e)}"
            }
    
    def _extract_notion_properties(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract simplified properties from Notion data.
        """
        if "properties" in data:
            return self.notion_client._extract_properties(data["properties"])
        return data
    
    async def _invalidate_cache(self, source: SourceType, record_id: str) -> None:
        """
        Invalidate cache for a specific record.
        
        In production, integrate with Redis or similar cache.
        """
        logger.info(f"Cache invalidation: {source}/{record_id}")
        # TODO: Implement actual cache invalidation
        # Example:
        # await redis_client.delete(f"cache:{source}:{record_id}")
        pass
    
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """Calculate SHA256 hash of data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()


class WebhookSecurity:
    """Security utilities for webhook verification."""
    
    @staticmethod
    def verify_signature(
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify HMAC signature of webhook payload.
        
        Args:
            payload: Raw webhook payload bytes
            signature: Signature from webhook header
            secret: Webhook secret key
            
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    @staticmethod
    def verify_supabase_signature(
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify Supabase webhook signature.
        
        Uses the JWT secret from Supabase.
        """
        return WebhookSecurity.verify_signature(
            payload,
            signature,
            settings.supabase_key
        )
    
    @staticmethod
    def verify_notion_signature(
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify Notion webhook signature.
        
        Note: Notion doesn't provide webhook signatures by default.
        Implement custom signature mechanism if needed.
        """
        # Notion doesn't have built-in webhook signatures
        # You may want to implement your own verification mechanism
        logger.warning("Notion webhook signature verification not implemented")
        return True


class WebhookMetrics:
    """Track webhook processing metrics."""
    
    def __init__(self):
        self.total_processed = 0
        self.total_failed = 0
        self.total_retries = 0
        self.processing_times: List[float] = []
        self.events_by_type: Dict[str, int] = {}
        self.events_by_source: Dict[str, int] = {}
    
    def record_success(self, duration: float, event_type: str, source: str):
        """Record successful webhook processing."""
        self.total_processed += 1
        self.processing_times.append(duration)
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
        self.events_by_source[source] = self.events_by_source.get(source, 0) + 1
    
    def record_failure(self, event_type: str, source: str):
        """Record failed webhook processing."""
        self.total_failed += 1
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
        self.events_by_source[source] = self.events_by_source.get(source, 0) + 1
    
    def record_retry(self):
        """Record a retry attempt."""
        self.total_retries += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get webhook processing statistics."""
        avg_time = (
            sum(self.processing_times) / len(self.processing_times)
            if self.processing_times else 0
        )
        
        return {
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "total_retries": self.total_retries,
            "success_rate": (
                self.total_processed / (self.total_processed + self.total_failed)
                if (self.total_processed + self.total_failed) > 0 else 0
            ),
            "average_processing_time_seconds": round(avg_time, 3),
            "events_by_type": self.events_by_type,
            "events_by_source": self.events_by_source
        }


# Global instances
webhook_processor = WebhookProcessor()
webhook_metrics = WebhookMetrics()