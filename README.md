# Hybrid Memory Integration Solution

A production-ready hybrid real-time memory integration solution using FastAPI that integrates with Supabase and Notion databases. Features comprehensive anti-hallucination mechanisms, confidence scoring, source tracking, and data validation.

## 🌟 Features

### Core Capabilities
- **Multi-Source Integration**: Seamlessly query both Supabase and Notion databases
- **Source Tracking**: Every response includes source IDs, metadata, and data hashes
- **Confidence Scoring**: Automatic confidence calculation (0.0-1.0) with configurable thresholds
- **Anti-Hallucination Mechanisms**: LLM prompt templates that enforce "I don't know" responses
- **Data Validation**: Comprehensive validation ensuring data comes from actual databases
- **Real-Time Webhooks**: Endpoints for Supabase and Notion real-time updates
- **Production-Ready**: Full error handling, logging, and monitoring

### Key Components

1. **JSON Response Formatter**
   - Standardized response format with source IDs
   - Confidence scores with reasoning
   - `information_not_found` flags
   - Source metadata and timestamps

2. **Data Validator**
   - Verifies data comes from actual databases
   - Enforces confidence threshold (default: 0.85)
   - Validates response integrity with data hashes
   - Aggregates confidence across multiple sources

3. **LLM Prompt Templates**
   - Strict anti-hallucination system prompts
   - Enforces citation requirements
   - Automatic "I don't know" responses for low confidence
   - Source-aware prompt generation

4. **Webhook Endpoints**
   - Real-time integration with Supabase
   - Real-time integration with Notion
   - Background task processing
   - Event validation and logging

## 📋 Requirements

- Python 3.8+
- Supabase account and API credentials
- Notion integration and database access

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Dpdpdpdp0987/hybrid-memory-integration.git
cd hybrid-memory-integration

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Notion Configuration
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id

# API Configuration
API_SECRET_KEY=your-secret-key-here
CONFIDENCE_THRESHOLD=0.85
ENVIRONMENT=development
```

### 3. Run the Application

```bash
python main.py
```

The API will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## 📚 API Endpoints

### Query Endpoints

#### Multi-Source Query
```http
POST /api/v1/query
Content-Type: application/json

{
  "query": "Find user information",
  "sources": ["supabase", "notion"],
  "require_verification": true,
  "confidence_threshold": 0.85,
  "additional_context": {
    "user_id": "123"
  }
}
```

**Response:**
```json
{
  "query": "Find user information",
  "sources": [
    {
      "data": {"id": "123", "name": "John Doe"},
      "source_metadata": {
        "source_type": "supabase",
        "source_id": "123",
        "table_name": "users",
        "retrieved_at": "2026-01-01T15:09:00Z",
        "raw_data_hash": "abc123..."
      },
      "confidence": {
        "score": 0.92,
        "reasoning": "Data from verified Supabase source with 100% completeness",
        "factors": {
          "completeness": 1.0,
          "filter_match": 1.0,
          "source_reliability": 0.95
        }
      },
      "information_not_found": false,
      "verified": true,
      "timestamp": "2026-01-01T15:09:00Z"
    }
  ],
  "aggregated_confidence": 0.92,
  "meets_threshold": true,
  "information_not_found": false,
  "timestamp": "2026-01-01T15:09:00Z"
}
```

#### Query Supabase
```http
POST /api/v1/query/supabase
Content-Type: application/json

{
  "table": "users",
  "filters": {"id": "123"}
}
```

#### Query Notion
```http
POST /api/v1/query/notion
Content-Type: application/json

{
  "filters": {"Name": "Project Alpha"}
}
```

### Webhook Endpoints

#### Supabase Webhook
```http
POST /api/v1/webhooks/supabase
Content-Type: application/json

{
  "event_type": "insert",
  "source": "supabase",
  "table_name": "users",
  "record_id": "123",
  "data": {"id": "123", "name": "John Doe"},
  "timestamp": "2026-01-01T15:09:00Z"
}
```

#### Notion Webhook
```http
POST /api/v1/webhooks/notion
Content-Type: application/json

{
  "event_type": "update",
  "source": "notion",
  "table_name": "database_id",
  "record_id": "page_id",
  "data": {"Name": "Updated Project"},
  "timestamp": "2026-01-01T15:09:00Z"
}
```

### LLM Prompt Generation

```http
POST /api/v1/prompt/generate
Content-Type: application/json

{
  "query": "What are the project details?",
  "sources": ["supabase", "notion"],
  "confidence_threshold": 0.85
}
```

**Response:**
```json
{
  "prompt": {
    "system_prompt": "You are a precise information retrieval assistant...",
    "user_prompt": "Query: What are the project details?\n\nRETRIEVED DATA SOURCES:\n...",
    "retrieved_data": [...],
    "strict_mode": true,
    "confidence_threshold": 0.85
  },
  "should_use_dont_know": false,
  "aggregated_confidence": 0.91
}
```

## 🔧 Architecture

### Data Flow

```
Client Request
     |
     v
FastAPI Endpoint
     |
     v
Database Clients (Supabase/Notion)
     |
     v
Data Retrieval + Metadata Generation
     |
     v
Confidence Scoring
     |
     v
Data Validation
     |
     v
Response Formatting
     |
     v
Client Response
```

### Key Classes

- **`SupabaseClient`**: Manages Supabase connections and queries with source tracking
- **`NotionDatabaseClient`**: Manages Notion API interactions with property extraction
- **`DataValidator`**: Validates responses and enforces confidence thresholds
- **`AntiHallucinationPrompts`**: Generates LLM prompts with anti-hallucination rules

## 🛡️ Anti-Hallucination Mechanisms

### 1. Source Verification
- Every response includes verifiable source IDs
- Data hashes for integrity checking
- `verified` flag indicating source confirmation

### 2. Confidence Scoring
- Multi-factor confidence calculation:
  - Data completeness (30%)
  - Filter match quality (40%)
  - Source reliability (30%)
- Configurable thresholds
- Automatic "I don't know" for low confidence

### 3. LLM Prompt Engineering
- Strict system prompts forbidding inference
- Mandatory source citations
- Explicit "I don't know" instructions
- Data quality context in prompts

### 4. Information Not Found Flags
- Explicit flags when data is missing
- Differentiation between "no data" and "low confidence"
- Proper handling of empty results

## 📊 Confidence Score Calculation

```python
# Example confidence calculation
factors = {
    'completeness': 0.95,      # 95% of fields have data
    'filter_match': 1.0,       # All filters matched
    'source_reliability': 0.95 # Supabase reliability
}

# Weighted average
score = (
    factors['completeness'] * 0.3 +
    factors['filter_match'] * 0.4 +
    factors['source_reliability'] * 0.3
) # = 0.965
```

## 🔐 Security Considerations

- Environment variables for sensitive credentials
- API key authentication (implement as needed)
- CORS middleware configured
- Input validation on all endpoints
- Background task processing for webhooks

## 🧪 Testing

Create test files to verify functionality:

```bash
# Test configuration
python -c "from config import settings; print(settings.supabase_url)"

# Test Supabase connection
curl -X POST http://localhost:8000/api/v1/query/supabase \
  -H "Content-Type: application/json" \
  -d '{"table": "your_table", "filters": {}}'

# Test health endpoint
curl http://localhost:8000/health
```

## 📝 Customization

### Adjusting Confidence Threshold

Edit `.env`:
```env
CONFIDENCE_THRESHOLD=0.90
```

Or per-request:
```json
{
  "query": "...",
  "confidence_threshold": 0.90
}
```

### Adding Custom Confidence Factors

Edit `database_clients.py` in the `_calculate_confidence` method:

```python
def _calculate_confidence(self, data, filters):
    factors = {
        'completeness': ...,
        'filter_match': ...,
        'source_reliability': ...,
        'custom_factor': ...  # Add your factor
    }
    # Adjust weights accordingly
```

## 🚀 Production Deployment

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Gunicorn
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
- [Notion API Documentation](https://developers.notion.com/)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - feel free to use this in your projects.

## 💡 Examples

See the `examples/` directory for:
- Integration examples
- Custom validators
- Extended confidence scoring
- Webhook processing patterns

---

Built with ❤️ for reliable, verifiable AI systems