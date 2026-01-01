# Technical Specification: Hybrid Memory Integration Solution

## 1. Overview

### 1.1 Purpose
This system provides a production-grade hybrid memory integration solution that queries multiple databases (Supabase and Notion) while ensuring data integrity, source verification, and anti-hallucination mechanisms for LLM integrations.

### 1.2 Key Requirements
- Multi-source data integration (Supabase + Notion)
- Source tracking with unique IDs
- Confidence scoring (0.0-1.0 scale)
- Data validation and verification
- Anti-hallucination LLM prompt templates
- Real-time webhook support
- Production-ready error handling

### 1.3 Architecture Style
- RESTful API using FastAPI
- Async/await for concurrent operations
- Modular, testable design
- Configuration via environment variables

## 2. System Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       Client Layer                          │
│  (HTTP Clients, LLMs, Webhook Senders)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Query      │  │   Webhook    │  │   Prompt Gen    │  │
│  │  Endpoints   │  │  Endpoints   │  │   Endpoints     │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Data         │  │   Prompt     │  │   Validator     │  │
│  │ Validator    │  │  Templates   │  │                 │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Access Layer                         │
│  ┌──────────────────┐           ┌───────────────────────┐  │
│  │ Supabase Client  │           │  Notion Client        │  │
│  └──────────────────┘           └───────────────────────┘  │
└──────────┬───────────────────────────────┬──────────────────┘
           │                               │
           ▼                               ▼
   ┌──────────────┐               ┌──────────────┐
   │   Supabase   │               │    Notion    │
   │   Database   │               │   Database   │
   └──────────────┘               └──────────────┘
```

### 2.2 Data Flow

#### Query Flow
```
1. Client Request → FastAPI Endpoint
2. Parse and validate QueryRequest
3. Execute parallel queries to data sources
4. Calculate confidence scores for each result
5. Aggregate confidence across sources
6. Validate against threshold
7. Format MultiSourceResponse
8. Return to client
```

#### Webhook Flow
```
1. External system → Webhook endpoint
2. Validate WebhookPayload
3. Queue background task
4. Return 202 Accepted
5. Background: Process webhook data
6. Background: Update caches/indexes
```

## 3. Data Models

### 3.1 Core Models

#### SourceMetadata
```python
class SourceMetadata:
    source_type: SourceType      # supabase | notion | unknown
    source_id: str               # Unique ID from source
    table_name: Optional[str]    # Table/database name
    retrieved_at: datetime       # Retrieval timestamp
    query_params: Optional[Dict] # Query parameters used
    raw_data_hash: Optional[str] # SHA256 hash for verification
```

#### ConfidenceScore
```python
class ConfidenceScore:
    score: float                 # 0.0-1.0
    reasoning: str               # Human-readable explanation
    factors: Dict[str, float]    # Individual confidence factors
```

**Confidence Factors:**
- `completeness`: Percentage of non-null fields (0.0-1.0)
- `filter_match`: How well data matches filters (0.0-1.0)
- `source_reliability`: Fixed per source (Supabase: 0.95, Notion: 0.90)

**Calculation:**
```
confidence = (completeness * 0.3) + 
             (filter_match * 0.4) + 
             (source_reliability * 0.3)
```

#### DataResponse
```python
class DataResponse:
    data: Any                          # Actual retrieved data
    source_metadata: SourceMetadata    # Source tracking info
    confidence: ConfidenceScore        # Confidence details
    information_not_found: bool        # True if no data found
    verified: bool                     # True if verified against source
    timestamp: datetime                # Response timestamp
    additional_context: Optional[str]  # Extra info (e.g., errors)
```

#### MultiSourceResponse
```python
class MultiSourceResponse:
    query: str                    # Original query string
    sources: List[DataResponse]   # Results from all sources
    aggregated_confidence: float  # Weighted average confidence
    meets_threshold: bool         # True if >= threshold
    information_not_found: bool   # True if all sources empty
    timestamp: datetime           # Response timestamp
```

### 3.2 Request Models

#### QueryRequest
```python
class QueryRequest:
    query: str                           # Query string
    sources: List[SourceType]            # Which sources to query
    require_verification: bool = True    # Enforce validation
    confidence_threshold: Optional[float] # Override default
    additional_context: Optional[Dict]   # Extra query params
```

#### WebhookPayload
```python
class WebhookPayload:
    event_type: Literal["insert", "update", "delete"]
    source: SourceType
    table_name: str
    record_id: str
    data: Dict[str, Any]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]]
```

## 4. API Endpoints

### 4.1 Query Endpoints

#### POST /api/v1/query
Multi-source query with confidence validation.

**Request:**
```json
{
  "query": "string",
  "sources": ["supabase", "notion"],
  "require_verification": true,
  "confidence_threshold": 0.85,
  "additional_context": {}
}
```

**Response:** `MultiSourceResponse`

**Status Codes:**
- 200: Success
- 422: Validation failed
- 500: Server error

#### POST /api/v1/query/supabase
Direct Supabase query.

**Request:**
```json
{
  "table": "string",
  "filters": {"key": "value"}
}
```

**Response:** `List[DataResponse]`

#### POST /api/v1/query/notion
Direct Notion query.

**Request:**
```json
{
  "filters": {"Property": "value"}
}
```

**Response:** `List[DataResponse]`

### 4.2 Webhook Endpoints

#### POST /api/v1/webhooks/supabase
Receive Supabase real-time updates.

**Request:** `WebhookPayload` with `source: "supabase"`

**Response:**
```json
{
  "status": "accepted",
  "message": "string",
  "event_type": "string",
  "record_id": "string"
}
```

#### POST /api/v1/webhooks/notion
Receive Notion updates.

**Request:** `WebhookPayload` with `source: "notion"`

### 4.3 Utility Endpoints

#### POST /api/v1/prompt/generate
Generate anti-hallucination LLM prompt.

**Request:** `QueryRequest`

**Response:**
```json
{
  "prompt": {
    "system_prompt": "string",
    "user_prompt": "string",
    "retrieved_data": [...],
    "strict_mode": true,
    "confidence_threshold": 0.85
  },
  "should_use_dont_know": false,
  "aggregated_confidence": 0.92,
  "dont_know_response": "string (optional)"
}
```

#### GET /health
Health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-01T15:09:00Z",
  "environment": "development"
}
```

## 5. Anti-Hallucination Mechanisms

### 5.1 Source Verification

**Mechanism:**
- Every response includes `source_id` from the database
- `raw_data_hash` for data integrity verification
- `verified` flag indicating successful source verification

**Implementation:**
```python
# SHA256 hash of retrieved data
data_hash = hashlib.sha256(
    json.dumps(data, sort_keys=True).encode()
).hexdigest()
```

### 5.2 Confidence Threshold Enforcement

**Rules:**
1. Default threshold: 0.85 (configurable)
2. If `aggregated_confidence < threshold`: Return "I don't know"
3. If `information_not_found == True`: Return "I don't know"
4. If no sources are `verified`: Return "I don't know"

**Validator Logic:**
```python
def should_return_dont_know(response):
    if all(r.information_not_found for r in response.sources):
        return True
    if response.aggregated_confidence < threshold:
        return True
    if not any(r.verified for r in response.sources):
        return True
    return False
```

### 5.3 LLM Prompt Engineering

**System Prompt Rules:**
1. ONLY use information from provided sources
2. NEVER infer or assume information
3. ALWAYS cite source IDs
4. Respond "I don't know" if confidence < threshold
5. Acknowledge data conflicts with source citations

**Prompt Template Structure:**
```
SYSTEM PROMPT:
- Anti-hallucination rules
- Citation requirements
- Confidence threshold policy

USER PROMPT:
- Original query
- Retrieved data with metadata
- Confidence scores and reasoning
- Explicit instructions
```

### 5.4 Information Not Found Handling

**When to set `information_not_found = True`:**
- Database query returns empty result
- Query error occurs
- No matching records found

**Response Format:**
```json
{
  "data": null,
  "source_metadata": {...},
  "confidence": {
    "score": 0.0,
    "reasoning": "No data found in Supabase",
    "factors": {"data_found": 0.0}
  },
  "information_not_found": true,
  "verified": true
}
```

## 6. Database Clients

### 6.1 SupabaseClient

**Responsibilities:**
- Execute Supabase queries
- Calculate confidence scores
- Generate source metadata
- Handle errors gracefully

**Key Methods:**
```python
async def query(table: str, filters: Dict) -> List[DataResponse]
    # Execute query, calculate confidence, format response

def _calculate_confidence(data, filters) -> ConfidenceScore
    # Compute confidence based on completeness and match quality

def _calculate_data_hash(data) -> str
    # Generate SHA256 hash for verification
```

### 6.2 NotionDatabaseClient

**Responsibilities:**
- Query Notion databases
- Extract properties from Notion objects
- Calculate confidence scores
- Convert filters to Notion API format

**Key Methods:**
```python
async def query(filters: Dict) -> List[DataResponse]
    # Query Notion, extract properties, format response

def _extract_properties(properties: Dict) -> Dict
    # Convert Notion property objects to simple dict

def _build_notion_filter(filters: Dict) -> Dict
    # Convert simple filters to Notion API format
```

## 7. Data Validation

### 7.1 Single Response Validation

**Checks:**
1. Response is verified (`verified == True`)
2. Confidence >= threshold
3. Not marked as not found OR is properly flagged
4. Valid source ID (not "none", "error", "unknown")
5. Data consistency (if found, data should not be None)

### 7.2 Multi-Source Validation

**Checks:**
1. Each source passes single response validation
2. Aggregated confidence >= threshold
3. `meets_threshold` flag is correct
4. At least one source is verified

### 7.3 Aggregated Confidence Calculation

**Algorithm:**
```python
# Filter out responses with no data
valid = [r for r in responses if not r.information_not_found]

# Weighted average by source reliability
weights = {'supabase': 0.55, 'notion': 0.45}

total_score = sum(
    r.confidence.score * weights[r.source_type] 
    for r in valid
)
total_weight = sum(weights[r.source_type] for r in valid)

aggregated = total_score / total_weight if total_weight > 0 else 0.0
```

## 8. Configuration

### 8.1 Environment Variables

```env
# Supabase
SUPABASE_URL=string (required)
SUPABASE_KEY=string (required)

# Notion
NOTION_API_KEY=string (required)
NOTION_DATABASE_ID=string (required)

# API
API_SECRET_KEY=string (required)
CONFIDENCE_THRESHOLD=float (default: 0.85)
ENVIRONMENT=string (default: "development")

# Server
HOST=string (default: "0.0.0.0")
PORT=int (default: 8000)
```

### 8.2 Settings Class

Uses `pydantic-settings` for type-safe configuration:

```python
class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    notion_api_key: str
    notion_database_id: str
    api_secret_key: str
    confidence_threshold: float = 0.85
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
```

## 9. Error Handling

### 9.1 Database Query Errors

**Strategy:** Return error response instead of raising exception

```python
try:
    results = await client.query(...)
except Exception as e:
    return [create_error_response(error=str(e))]
```

**Error Response:**
```json
{
  "data": null,
  "confidence": {"score": 0.0, "reasoning": "Query error: ..."},
  "information_not_found": true,
  "verified": false,
  "additional_context": "error details"
}
```

### 9.2 Validation Errors

**Strategy:** Raise HTTP 422 with detailed issues

```python
if not is_valid:
    raise HTTPException(
        status_code=422,
        detail={
            "message": "Data validation failed",
            "issues": ["issue1", "issue2"],
            "response": response.dict()
        }
    )
```

### 9.3 Webhook Processing Errors

**Strategy:** Log and continue (background tasks)

```python
async def process_webhook(payload):
    try:
        # Process webhook
        pass
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        # Don't raise - webhook already accepted
```

## 10. Performance Considerations

### 10.1 Concurrent Queries

Use async/await for parallel database queries:

```python
# Execute in parallel
supabase_task = supabase_client.query(...)
notion_task = notion_client.query(...)

results = await asyncio.gather(supabase_task, notion_task)
```

### 10.2 Caching Strategy

**Recommendations:**
- Cache frequently accessed data
- Invalidate cache on webhook events
- Use Redis for distributed caching
- TTL based on data volatility

### 10.3 Rate Limiting

**Implementation (not included, recommended):**
```python
from fastapi_limiter import FastAPILimiter

@app.post("/api/v1/query")
@limiter.limit("10/minute")
async def query_multi_source(...):
    ...
```

## 11. Security

### 11.1 Authentication

**Recommendations:**
- Implement API key authentication
- Use JWT tokens for user sessions
- OAuth2 for third-party integrations

**Example:**
```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.api_secret_key:
        raise HTTPException(status_code=403)
```

### 11.2 Input Validation

- All inputs validated with Pydantic models
- SQL injection prevention (parameterized queries)
- XSS prevention (no HTML rendering)

### 11.3 Secrets Management

- Use environment variables
- Never commit `.env` files
- Use secret management services (AWS Secrets Manager, etc.)

## 12. Deployment

### 12.1 Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 12.2 Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Use secure `API_SECRET_KEY`
- [ ] Enable HTTPS
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Configure rate limiting
- [ ] Implement authentication
- [ ] Set up CI/CD pipeline
- [ ] Configure backup strategy
- [ ] Set up error tracking (Sentry, etc.)

## 13. Monitoring & Observability

### 13.1 Metrics to Track

- Request latency
- Database query times
- Confidence score distribution
- Validation failure rate
- Webhook processing time
- Error rates by endpoint

### 13.2 Logging

**Structured logging example:**
```python
import logging
import json

logger = logging.getLogger(__name__)

logger.info(json.dumps({
    "event": "query_executed",
    "query": query,
    "sources": sources,
    "confidence": aggregated_confidence,
    "duration_ms": duration
}))
```

## 14. Future Enhancements

### 14.1 Additional Features
- [ ] Elasticsearch integration
- [ ] Redis caching layer
- [ ] GraphQL API
- [ ] WebSocket support for real-time updates
- [ ] Machine learning confidence scoring
- [ ] Multi-tenant support
- [ ] Advanced query language
- [ ] Data versioning

### 14.2 Scalability
- [ ] Horizontal scaling with load balancer
- [ ] Database connection pooling
- [ ] Message queue for webhooks (RabbitMQ/Kafka)
- [ ] Microservices architecture

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-01-01  
**Author:** Technical Team