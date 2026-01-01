# Webhook Implementation - FastAPI

## Übersicht

Diese Implementation bietet eine vollständige, produktionsreife Webhook-Lösung für das Hybrid Memory Integration System mit Unterstützung für Supabase und Notion.

## 🚀 Features

### Core Features
- ✅ **Real-time Webhooks** für Supabase und Notion
- ✅ **Background Task Processing** mit FastAPI BackgroundTasks
- ✅ **Automatic Retry Logic** mit exponentieller Backoff-Strategie
- ✅ **HMAC Signature Verification** für Sicherheit
- ✅ **Comprehensive Error Handling** mit detailliertem Logging
- ✅ **Metrics & Monitoring** mit eingebautem Stats-Endpoint
- ✅ **Data Verification** gegen Quell-Datenbanken
- ✅ **Cache Invalidation** bei Datenänderungen

### Event Types
- `INSERT` - Neue Datensätze erstellt
- `UPDATE` - Bestehende Datensätze geändert
- `DELETE` - Datensätze gelöscht

## 📚 Dateienübersicht

### Neue Dateien

1. **`webhook_handlers.py`**
   - `WebhookProcessor`: Haupt-Klasse für Webhook-Verarbeitung
   - `WebhookSecurity`: Signature-Verifikation
   - `WebhookMetrics`: Performance-Metriken
   - Retry-Logik mit exponentieller Backoff
   - Data verification gegen Quell-Datenbanken

2. **`webhook_router.py`**
   - FastAPI Router mit allen Webhook-Endpoints
   - `/api/v1/webhooks/supabase` - Supabase Events
   - `/api/v1/webhooks/notion` - Notion Events
   - `/api/v1/webhooks/stats` - Statistiken
   - `/api/v1/webhooks/test` - Test-Endpoint

3. **`docs/WEBHOOK_GUIDE.md`**
   - Vollständige Dokumentation
   - Setup-Anleitungen für Supabase und Notion
   - API-Referenz mit Beispielen
   - Troubleshooting-Guide

4. **`examples/webhook_examples/`**
   - JSON-Payload-Beispiele
   - Test-Skripte
   - Integration-Code-Snippets

### Aktualisierte Dateien

1. **`main.py`**
   - Webhook-Router Integration
   - Enhanced Logging
   - Startup/Shutdown Events
   - Verbesserte Fehlerbehandlung

## 🔧 Installation & Setup

### 1. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 2. Umgebungsvariablen konfigurieren

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Notion
NOTION_API_KEY=secret_your-notion-integration-key
NOTION_DATABASE_ID=your-database-id

# API
API_SECRET_KEY=your-secret-key
CONFIDENCE_THRESHOLD=0.85
ENVIRONMENT=development

# Webhook Security (optional)
VERIFY_WEBHOOK_SIGNATURES=true

# Server
HOST=0.0.0.0
PORT=8000
```

### 3. Server starten

```bash
python main.py
```

Oder mit uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### Supabase Webhook

```bash
POST /api/v1/webhooks/supabase
Content-Type: application/json

{
  "event_type": "insert",
  "source": "supabase",
  "table_name": "users",
  "record_id": "123",
  "data": {...},
  "timestamp": "2026-01-01T15:00:00Z"
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
    "record_id": "123",
    "table_name": "users",
    "timestamp": "2026-01-01T15:00:00Z"
  }
}
```

### Notion Webhook

```bash
POST /api/v1/webhooks/notion
Content-Type: application/json

{
  "event_type": "update",
  "source": "notion",
  "table_name": "database-id",
  "record_id": "page-id",
  "data": {...},
  "timestamp": "2026-01-01T15:00:00Z"
}
```

### Webhook Statistiken

```bash
GET /api/v1/webhooks/stats
```

**Response:**
```json
{
  "total_processed": 1523,
  "total_failed": 12,
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

### Test Webhook

```bash
POST /api/v1/webhooks/test
Content-Type: application/json

{
  "event_type": "insert",
  "source": "supabase",
  "table_name": "test",
  "record_id": "123",
  "data": {}
}
```

## 🛠️ Architektur

### Request Flow

```
1. Webhook Received
   │
   │  - Validate payload structure
   │  - Verify signature (optional)
   │  - Check source type
   │
   v
2. Immediate Response (202 Accepted)
   │
   v
3. Background Task Queued
   │
   │  - Attempt 1: Process immediately
   │  - Attempt 2: Retry after 2s (if failed)
   │  - Attempt 3: Retry after 4s (if failed)
   │
   v
4. Background Processing
   │
   ├─▶ Validate payload details
   ├─▶ Verify data against source
   ├─▶ Invalidate cache
   ├─▶ Update indexes
   ├─▶ Record metrics
   └─▶ Log results
```

### Komponenten

```
┌───────────────────────────────────┐
│        webhook_router.py           │
│  (FastAPI Endpoints)              │
│                                   │
│  - /webhooks/supabase             │
│  - /webhooks/notion               │
│  - /webhooks/stats                │
│  - /webhooks/test                 │
└─────────────┬─────────────────────┘
               │
               v
┌───────────────────────────────────┐
│      webhook_handlers.py          │
│  (Business Logic)                 │
│                                   │
│  • WebhookProcessor              │
│    - process_webhook()            │
│    - retry logic                  │
│    - error handling               │
│                                   │
│  • WebhookSecurity               │
│    - verify_signature()           │
│                                   │
│  • WebhookMetrics                │
│    - record_success()             │
│    - record_failure()             │
└─────────────┬─────────────────────┘
               │
               v
┌───────────────────────────────────┐
│     database_clients.py          │
│  (Data Access)                    │
│                                   │
│  • SupabaseClient                │
│  • NotionDatabaseClient         │
└───────────────────────────────────┘
```

## 🔒 Sicherheit

### Signature Verification

Die Implementation unterstützt HMAC-SHA256 Signature Verification:

```python
import hmac
import hashlib
import json

# Generate signature (sender side)
payload = {...}
payload_bytes = json.dumps(payload).encode()

signature = hmac.new(
    settings.supabase_key.encode(),
    payload_bytes,
    hashlib.sha256
).hexdigest()

# Include in request header:
headers = {"X-Webhook-Signature": signature}
```

### Best Practices

- ✅ HTTPS für alle Webhook-Endpoints
- ✅ Signature Verification aktivieren
- ✅ Rate Limiting implementieren
- ✅ IP Whitelisting (optional)
- ✅ Payload Size Limits (< 100KB)
- ✅ Timeout-Einstellungen

## 📋 Logging

### Log Levels

```python
# INFO - Normale Operationen
logger.info("Webhook processed successfully")

# WARNING - Nicht-kritische Probleme
logger.warning("All results below confidence threshold")

# ERROR - Fehler mit Stack Trace
logger.error("Webhook processing failed", exc_info=True)
```

### Log Format

```
2026-01-01 15:00:00 - webhook_handlers - INFO - Starting webhook processing: supabase/insert for record abc-123
2026-01-01 15:00:00 - webhook_handlers - INFO - Processing Supabase insert event
2026-01-01 15:00:00 - webhook_handlers - INFO - Webhook processed successfully in 0.23s (attempt 1/3)
```

## 📊 Monitoring

### Key Metrics

1. **Success Rate** - Prozentsatz erfolgreicher Verarbeitungen
2. **Average Processing Time** - Durchschnittliche Verarbeitungszeit
3. **Total Retries** - Anzahl der Wiederholungsversuche
4. **Events by Type** - Verteilung nach Event-Typ
5. **Events by Source** - Verteilung nach Datenquelle

### Abrufen der Metriken

```bash
curl -X GET http://localhost:8000/api/v1/webhooks/stats
```

## 🧪 Testing

### Unit Tests

```bash
python examples/webhook_examples/test_webhook.py
```

### Manual Testing

```bash
# Test Supabase webhook
curl -X POST http://localhost:8000/api/v1/webhooks/supabase \
  -H "Content-Type: application/json" \
  -d @examples/webhook_examples/supabase_webhook_payload.json

# Test Notion webhook
curl -X POST http://localhost:8000/api/v1/webhooks/notion \
  -H "Content-Type: application/json" \
  -d @examples/webhook_examples/notion_webhook_payload.json

# Check statistics
curl -X GET http://localhost:8000/api/v1/webhooks/stats
```

## ⚙️ Konfiguration

### Retry-Einstellungen

```python
# In webhook_handlers.py
WebhookProcessor(
    max_retries=3,      # Maximale Anzahl Versuche
    retry_delay=2       # Basis-Verzögerung in Sekunden
)
```

### Exponential Backoff

```
Attempt 1: Sofort
Attempt 2: Nach 2 Sekunden
Attempt 3: Nach 4 Sekunden
Attempt N: Nach 2^(N-1) Sekunden
```

## 🐛 Troubleshooting

### Problem: Webhook wird nicht empfangen

**Lösungen:**
1. Firewall-Einstellungen prüfen
2. API-URL verifizieren
3. Öffentliche Erreichbarkeit testen
4. Webhook-Logs in Supabase prüfen

### Problem: Signature Verification schlägt fehl

**Lösungen:**
1. Secret Key überprüfen
2. Algorithmus verifizieren (HMAC-SHA256)
3. Payload-Modifikation ausschließen

### Problem: Hohe Fehlerrate

**Lösungen:**
1. Stats-Endpoint prüfen
2. Logs analysieren
3. Datenbank-Verbindung testen
4. Rate Limits prüfen

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - NOTION_API_KEY=${NOTION_API_KEY}
      - NOTION_DATABASE_ID=${NOTION_DATABASE_ID}
      - API_SECRET_KEY=${API_SECRET_KEY}
    restart: unless-stopped
```

### Production Checklist

- [ ] HTTPS aktiviert
- [ ] Environment Variables gesetzt
- [ ] Signature Verification aktiviert
- [ ] Logging konfiguriert
- [ ] Monitoring eingerichtet
- [ ] Rate Limiting implementiert
- [ ] Backup-Strategie definiert
- [ ] Error Tracking (Sentry, etc.)
- [ ] Health Checks konfiguriert

## 📚 Weitere Ressourcen

- **API Dokumentation:** http://localhost:8000/docs
- **Webhook Guide:** [docs/WEBHOOK_GUIDE.md](docs/WEBHOOK_GUIDE.md)
- **Beispiele:** [examples/webhook_examples/](examples/webhook_examples/)
- **Technische Spezifikation:** [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md)

## 👥 Support

Bei Fragen oder Problemen:
1. Logs prüfen
2. Stats-Endpoint konsultieren
3. Test-Endpoint nutzen
4. Dokumentation durchsuchen

---

**Version:** 1.0.0  
**Erstellt:** 2026-01-01  
**Autor:** Hybrid Memory Integration Team