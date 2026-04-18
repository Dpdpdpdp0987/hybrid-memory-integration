# Webhook Implementation Guide

## Overview

This guide explains how to set up and use webhooks with the Hybrid Memory Integration API. Webhooks enable real-time synchronization between your databases (Supabase and Notion) and the API.

## Features

✅ **Real-time updates** - Process database changes instantly
✅ **Automatic retry logic** - Failed webhook processing retries with exponential backoff
✅ **Signature verification** - Optional HMAC signature verification for security
✅ **Background processing** - Non-blocking webhook handling
✅ **Comprehensive logging** - Track all webhook events and errors
✅ **Metrics & monitoring** - Built-in statistics endpoint

## Architecture

```
┌──────────────┐          ┌──────────────┐
│   Supabase   │─────────▶│   Webhook    │
│   Database   │  HTTP    │   Endpoint   │
└──────────────┘  POST    └──────┬───────┘
                                 │
                                 ▼
┌──────────────┐          ┌──────────────┐
│    Notion    │─────────▶│  Background  │
│   Database   │          │  Processing  │
└──────────────┘          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │  - Cache     │
                          │  - Verify    │
                          │  - Index     │
                          └──────────────┘
```

## Endpoints

### 1. Supabase Webhook

**POST** `/api/v1/webhooks/supabase`

Receives real-time updates from Supabase database.

**Headers:**
- `Content-Type: application/json`
- `X-Webhook-Signature: <signature>` (optional, for verification)

**Request Body:**
```json
{
  "event_type": "insert",
  "source": "supabase",
  "table_name": "users",
  "record_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "John Doe",
    "email": "john@example.com",
    "created_at": "2026-01-01T15:00:00Z"
  },
  "timestamp": "2026-01-01T15:00:00Z",
  "metadata": {
    "schema": "public"
  }
}
```

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "message": "Webhook payload received and queued for processing",
  "details": {
    "event_type": "insert",
    "source": "supabase",
    "record_id": "123e4567-e89b-12d3-a456-426614174000",
    "table_name": "users",
    "timestamp": "2026-01-01T15:00:00Z"
  }
}
```

### 2. Notion Webhook

**POST** `/api/v1/webhooks/notion`

Receives updates from Notion database.

**Headers:**
- `Content-Type: application/json`

**Request Body:**
```json
{
  "event_type": "update",
  "source": "notion",
  "table_name": "e8d4b0a1c7f24a9e8f2d5c3b1a6e9f4d",
  "record_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "data": {
    "properties": {
      "Name": {
        "type": "title",
        "title": [{"plain_text": "Project Alpha"}]
      },
      "Status": {
        "type": "select",
        "select": {"name": "In Progress"}
      }
    }
  },
  "timestamp": "2026-01-01T15:00:00Z"
}
```

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "message": "Webhook payload received and queued for processing",
  "details": {
    "event_type": "update",
    "source": "notion",
    "record_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "database_id": "e8d4b0a1c7f24a9e8f2d5c3b1a6e9f4d",
    "timestamp": "2026-01-01T15:00:00Z"
  }
}
```

### 3. Webhook Statistics

**GET** `/api/v1/webhooks/stats`

Retrieve processing metrics.

**Response (200 OK):**
```json
{
  "total_processed": 1523,
  "total_failed": 12,
  "total_retries": 8,
  "success_rate": 0.992,
  "average_processing_time_seconds": 0.234,
  "events_by_type": {
    "insert": 456,
    "update": 892,
    "delete": 187
  },
  "events_by_source": {
    "supabase": 789,
    "notion": 746
  }
}
```

### 4. Test Webhook

**POST** `/api/v1/webhooks/test`

Test your webhook payload format.

**Request Body:**
```json
{
  "event_type": "insert",
  "source": "supabase",
  "table_name": "test_table",
  "record_id": "test-123",
  "data": {"test": "data"}
}
```

**Response:**
```json
{
  "status": "valid",
  "message": "Webhook payload is valid",
  "parsed_payload": { ... },
  "would_be_processed": true
}
```

## Setup Instructions

### Supabase Setup

1. **Create a Database Webhook in Supabase:**

   Go to your Supabase project → Database → Webhooks → Create a new webhook

2. **Configure the webhook:**
   - **Name:** Hybrid Memory Integration
   - **Table:** Select your table (e.g., `users`)
   - **Events:** Insert, Update, Delete
   - **Type:** HTTP Request
   - **Method:** POST
   - **URL:** `https://your-api.com/api/v1/webhooks/supabase`
   - **Headers:** 
     - `Content-Type: application/json`
     - `X-Webhook-Signature: <your-secret>` (optional)

3. **Example Supabase SQL trigger:**

```sql
CREATE OR REPLACE FUNCTION notify_webhook()
RETURNS TRIGGER AS $$
DECLARE
  payload JSON;
BEGIN
  payload := json_build_object(
    'event_type', TG_OP::text,
    'source', 'supabase',
    'table_name', TG_TABLE_NAME,
    'record_id', NEW.id,
    'data', row_to_json(NEW),
    'timestamp', NOW()
  );
  
  PERFORM net.http_post(
    url := 'https://your-api.com/api/v1/webhooks/supabase',
    body := payload::text,
    headers := '{"Content-Type": "application/json"}'::jsonb
  );
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_webhook_trigger
AFTER INSERT OR UPDATE OR DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION notify_webhook();
```

### Notion Setup

Notion doesn't have native webhook support. You'll need to:

1. **Use a third-party service** like Zapier or Make (formerly Integromat)
2. **Poll Notion API** and send updates
3. **Use Notion's API** with custom integration

**Example with a custom poller:**

```python
import httpx
import asyncio
from notion_client import Client

async def notion_webhook_poller():
    notion = Client(auth="your-notion-key")
    last_edited = None
    
    while True:
        # Query recently edited pages
        response = notion.databases.query(
            database_id="your-database-id",
            sorts=[{"timestamp": "last_edited_time", "direction": "descending"}]
        )
        
        for page in response['results']:
            if last_edited and page['last_edited_time'] <= last_edited:
                continue
                
            # Send webhook
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://your-api.com/api/v1/webhooks/notion",
                    json={
                        "event_type": "update",
                        "source": "notion",
                        "table_name": "your-database-id",
                        "record_id": page['id'],
                        "data": page,
                        "timestamp": page['last_edited_time']
                    }
                )
        
        if response['results']:
            last_edited = response['results'][0]['last_edited_time']
        
        await asyncio.sleep(60)  # Poll every 60 seconds
```

## Security

### Signature Verification

Enable signature verification in your `.env`:

```env
VERIFY_WEBHOOK_SIGNATURES=true
```

**Generate signature:**

```python
import hmac
import hashlib
import json

payload = {"event_type": "insert", ...}
payload_bytes = json.dumps(payload).encode()

signature = hmac.new(
    b"your-secret-key",
    payload_bytes,
    hashlib.sha256
).hexdigest()

# Include in request header:
# X-Webhook-Signature: <signature>
```

## Error Handling

### Automatic Retries

The webhook processor automatically retries failed operations:

- **Max retries:** 3 (configurable)
- **Retry delay:** 2 seconds with exponential backoff
- **Backoff multiplier:** 2x per attempt

**Example retry timeline:**
- Attempt 1: Immediate
- Attempt 2: After 2 seconds
- Attempt 3: After 4 seconds

### Error Responses

**400 Bad Request:**
```json
{
  "error": "invalid_source",
  "message": "Invalid source type for Supabase webhook",
  "expected": "supabase",
  "received": "notion"
}
```

**401 Unauthorized:**
```json
{
  "error": "invalid_signature",
  "message": "Webhook signature verification failed"
}
```

**422 Unprocessable Entity:**
```json
{
  "detail": [
    {
      "loc": ["body", "record_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Background Processing

### What Happens in the Background?

1. **Validation** - Validates payload structure and data
2. **Verification** - Verifies data against source database
3. **Cache Invalidation** - Removes stale cache entries
4. **Index Update** - Updates search indexes (if implemented)
5. **Metrics Recording** - Records processing metrics
6. **Logging** - Logs event details for monitoring

### Processing Flow

```
Webhook Received
      │
      ▼
[Immediate Response: 202 Accepted]
      │
      ▼
Background Task Queued
      │
      ├─▶ Attempt 1
      │   ├─▶ Success ✓
      │   └─▶ Failure ✗ → Wait 2s
      │
      ├─▶ Attempt 2 (if failed)
      │   ├─▶ Success ✓
      │   └─▶ Failure ✗ → Wait 4s
      │
      └─▶ Attempt 3 (if failed)
          ├─▶ Success ✓
          └─▶ Failure ✗ → Log Error
```

## Monitoring

### Check Webhook Stats

```bash
curl -X GET https://your-api.com/api/v1/webhooks/stats
```

### Logs

Webhook processing logs include:

```
2026-01-01 15:00:00 - webhook_handlers - INFO - Starting webhook processing: supabase/insert for record abc-123
2026-01-01 15:00:00 - webhook_handlers - INFO - Processing Supabase insert event
2026-01-01 15:00:00 - webhook_handlers - INFO - Supabase webhook processed: ['data_verification', 'index_update_queued']
2026-01-01 15:00:00 - webhook_handlers - INFO - Webhook processed successfully in 0.23s (attempt 1/3)
```

## Testing

### Test with cURL

**Supabase Webhook:**
```bash
curl -X POST https://your-api.com/api/v1/webhooks/supabase \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "insert",
    "source": "supabase",
    "table_name": "users",
    "record_id": "test-123",
    "data": {"name": "Test User"},
    "timestamp": "2026-01-01T15:00:00Z"
  }'
```

**Notion Webhook:**
```bash
curl -X POST https://your-api.com/api/v1/webhooks/notion \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "update",
    "source": "notion",
    "table_name": "database-id",
    "record_id": "page-id",
    "data": {"properties": {}},
    "timestamp": "2026-01-01T15:00:00Z"
  }'
```

### Test Payload Validation

```bash
curl -X POST https://your-api.com/api/v1/webhooks/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "insert",
    "source": "supabase",
    "table_name": "test",
    "record_id": "123",
    "data": {}
  }'
```

## Best Practices

✅ **Always use HTTPS** for webhook endpoints in production
✅ **Enable signature verification** for security
✅ **Monitor webhook stats** regularly
✅ **Set up alerting** for high failure rates
✅ **Keep webhook payloads small** (< 100KB recommended)
✅ **Use idempotency** - Handle duplicate webhooks gracefully
✅ **Log everything** - Debug issues with comprehensive logs
✅ **Test thoroughly** - Use the test endpoint before production

## Troubleshooting

### Webhook not being received

1. Check your firewall settings
2. Verify the webhook URL is correct
3. Ensure your API is publicly accessible
4. Check Supabase webhook logs

### Signature verification failing

1. Verify the secret key matches
2. Check the signature algorithm (HMAC-SHA256)
3. Ensure payload hasn't been modified in transit

### High failure rate

1. Check the stats endpoint: `GET /api/v1/webhooks/stats`
2. Review application logs
3. Verify database connectivity
4. Check for rate limiting issues

### Processing too slow

1. Monitor average processing time in stats
2. Consider optimizing database queries
3. Implement caching strategies
4. Scale horizontally if needed

## Examples

See the `/examples/webhook_examples/` directory for:
- Complete webhook payload examples
- Integration code snippets
- Testing scripts
- Monitoring dashboards

## Support

For issues or questions:
- Check the logs: Application logs contain detailed error information
- Review stats: `GET /api/v1/webhooks/stats`
- Test endpoint: Use `/api/v1/webhooks/test` to validate payloads
- Documentation: `/docs` for interactive API documentation

---

**Last Updated:** 2026-01-01  
**Version:** 1.0.0