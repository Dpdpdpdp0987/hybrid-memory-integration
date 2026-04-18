# Anti-Hallucination Prompt System Guide

## Überblick

Dieses Dokument beschreibt das erweiterte Anti-Halluzination Prompt-System, das in das Hybrid Memory Integration System integriert wurde. Das System bietet mehrstufige Schutzmechanismen gegen LLM-Halluzinationen durch intelligente Prompt-Generierung und Confidence-Threshold-Integration.

## 🎯 Hauptfunktionen

### 1. **Multi-Level Strictness Control**
- **Strict Mode**: Maximaler Schutz (medizinische, rechtliche, finanzielle Anwendungen)
- **Moderate Mode**: Ausgewogener Ansatz (allgemeine Verwendung)
- **Lenient Mode**: Flexibel aber akkurat (explorativ, kreativ)

### 2. **Automatische Strictness-Erkennung**
Das System wählt automatisch den optimalen Strictness-Level basierend auf:
- Datenqualität und Confidence-Scores
- Anzahl verifizierter Quellen
- Vorhandensein von Datenkonflikten

### 3. **Confidence-Threshold-Integration**
- Nahtlose Integration mit dem bestehenden Confidence-System
- Automatisches "I don't know" bei unzureichender Confidence
- Detaillierte Confidence-Analyse pro Quelle

### 4. **Data Conflict Detection**
- Automatische Erkennung von Widersprüchen zwischen Quellen
- Detaillierte Konfliktanalyse
- Intelligente Konfliktlösungsstrategien

### 5. **Response Validation**
- Automatische Validierung von LLM-Antworten
- Halluzinations-Erkennung
- Citation-Compliance-Prüfung

## 📚 API-Endpunkte

### 1. `/api/v1/prompt/generate`
Generiert Anti-Halluzination-Prompts mit konfigurierbarem Strictness-Level.

**Request:**
```json
{
  "query": "What is the patient's medication?",
  "sources": ["supabase", "notion"],
  "confidence_threshold": 0.85,
  "strictness_level": "strict",
  "auto_detect_strictness": false,
  "use_cache": true
}
```

**Response:**
```json
{
  "prompt": {
    "system_prompt": "...",
    "user_prompt": "...",
    "retrieved_data": [...],
    "strict_mode": true,
    "confidence_threshold": 0.85
  },
  "should_use_dont_know": false,
  "dont_know_response": null,
  "aggregated_confidence": 0.92,
  "strictness_level": "strict",
  "metadata": {...}
}
```

### 2. `/api/v1/prompt/generate/adaptive`
Automatische Strictness-Erkennung basierend auf Datenqualität.

**Request:**
```json
{
  "query": "What are the project updates?",
  "sources": ["supabase", "notion"],
  "confidence_threshold": 0.85
}
```

**Response:** Wie `/api/v1/prompt/generate`, aber mit automatisch gewähltem Strictness-Level.

### 3. `/api/v1/prompt/validate`
Validiert LLM-Antworten auf Halluzinationen.

**Request:**
```json
{
  "query": "What is the balance?",
  "llm_response": "The balance is $1000 [Source: supabase-acc-123]",
  "sources": ["supabase"],
  "strict_validation": true
}
```

**Response:**
```json
{
  "is_valid": true,
  "issues": [],
  "validation_prompt": "...",
  "has_citations": true,
  "confidence_check_passed": true,
  "timestamp": "2026-01-01T15:00:00Z"
}
```

### 4. `/api/v1/prompt/compare`
Multi-Source-Vergleich mit Konflikt-Erkennung.

**Request:**
```json
{
  "query": "What is the product price?",
  "sources": ["supabase", "notion"]
}
```

**Response:**
```json
{
  "comparison_prompt": "...",
  "conflict_analysis": {
    "has_conflicts": true,
    "conflicting_fields": ["price"],
    "conflict_details": [...]
  },
  "multi_source_response": {...},
  "aggregated_confidence": 0.89
}
```

### 5. `/api/v1/prompt/metrics`
Abrufen von Prompt-Generierungs-Metriken.

**Response:**
```json
{
  "timestamp": "2026-01-01T15:00:00Z",
  "metrics": {
    "prompts_generated": 150,
    "dont_know_responses": 12,
    "cache_hits": 45,
    "strictness_distribution": {
      "strict": 50,
      "moderate": 70,
      "lenient": 30
    },
    "cache_hit_rate": 0.30,
    "dont_know_rate": 0.08
  }
}
```

## 🔧 Programmatische Verwendung

### Beispiel 1: Strict Prompt Generation

```python
from prompt_integration import generate_strict_prompt

result = generate_strict_prompt(
    query="What is the medication dosage?",
    retrieved_data=data_responses,
    confidence_threshold=0.90
)

print(f"Should use 'I don't know': {result.should_use_dont_know}")
print(f"Confidence: {result.aggregated_confidence}")

if result.should_use_dont_know:
    print(result.dont_know_response)
else:
    # Use prompt with LLM
    llm_response = call_llm(
        system=result.prompt_template.system_prompt,
        user=result.prompt_template.user_prompt
    )
```

### Beispiel 2: Adaptive Prompt mit Auto-Detection

```python
from prompt_integration import generate_adaptive_prompt

result = generate_adaptive_prompt(
    query="What are the project updates?",
    retrieved_data=data_responses,
    confidence_threshold=0.85
)

print(f"Auto-detected strictness: {result.strictness_level}")
```

### Beispiel 3: Response Validation

```python
from prompt_integration import validate_response

validation = validate_response(
    query="What is the balance?",
    llm_response=response_text,
    retrieved_data=data_responses
)

if not validation['is_valid']:
    print(f"Validation failed: {validation['issues']}")
```

### Beispiel 4: PromptGenerator Class

```python
from prompt_integration import PromptGenerator
from validators import DataValidator

validator = DataValidator(confidence_threshold=0.85)
generator = PromptGenerator(validator=validator)

# Generate prompt
result = generator.generate_prompt(
    query="What is the status?",
    retrieved_data=data_responses,
    auto_detect_strictness=True,
    use_cache=True
)

# Detect conflicts
conflicts = generator.detect_conflicts(data_responses)

if conflicts['has_conflicts']:
    print(f"Conflicts found in: {conflicts['conflicting_fields']}")

# Get metrics
metrics = generator.get_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")
```

## 🎚️ Strictness Levels im Detail

### Strict Mode (`strictness_level="strict"`)

**Verwendung:**
- Medizinische Anwendungen
- Rechtliche Dokumente
- Finanzielle Daten
- Kritische Systeme

**Eigenschaften:**
- ❌ ZERO Tolerance für Halluzinationen
- ✅ MUSS jede Information zitieren
- ✅ MUSS "I don't know" bei < Threshold verwenden
- ❌ KEINE Inferenzen oder Annahmen
- ✅ Vollständige Transparenz über Datenlücken

**System Prompt Regeln:**
```
1. ONLY use information from provided sources
2. NEVER infer or assume
3. ALWAYS cite with [Source: type-id]
4. Respond "I don't know" if confidence < threshold
5. Acknowledge ALL data conflicts
6. Report data quality issues
7. PROHIBITED: Fabrication, speculation, uncited info
```

### Moderate Mode (`strictness_level="moderate"`)

**Verwendung:**
- Allgemeine Informationsabfragen
- Standardoperationen
- Kundenservice
- Reporting

**Eigenschaften:**
- ✅ Primär Quelldaten verwenden
- ⚠️ Kleine begründete Inferenzen erlaubt (markiert)
- ✅ Hauptaussagen müssen zitiert werden
- ⚠️ Externe Kontextinformationen erlaubt (markiert)
- ✅ Qualifizierte Antworten bei marginaler Confidence

**System Prompt Regeln:**
```
1. Primarily use provided sources
2. NEVER fabricate information
3. Minor inferences allowed if marked as [Inference]
4. MUST cite factual claims
5. Acknowledge conflicts, may resolve by confidence
6. Use qualifiers when confidence not high
7. PROHIBITED: Complete fabrication, ignoring low confidence
```

### Lenient Mode (`strictness_level="lenient"`)

**Verwendung:**
- Explorative Abfragen
- Brainstorming
- Kreative Anwendungen
- Kontextuelle Hilfe

**Eigenschaften:**
- ✅ Quelldaten als primäre Basis
- ✅ Kann mit Allgemeinwissen ergänzen (markiert)
- ✅ Begründete Inferenzen erlaubt
- ⚠️ Zitate für Schlüsselfakten erforderlich
- ✅ Balanciert Genauigkeit mit Nützlichkeit

**System Prompt Regeln:**
```
1. Use provided data as primary source
2. May supplement with general knowledge (marked)
3. Reasonable inferences allowed with qualifiers
4. Cite key facts and specific data
5. Provide warnings for low-confidence info
6. Be helpful while maintaining accuracy
7. STILL PROHIBITED: Deliberate fabrication
```

## 📊 Confidence-Threshold-Integration

### Confidence Berechnung

Das System verwendet einen mehrschichtigen Confidence-Berechnungsansatz:

#### Einzelne Quelle:
```python
confidence = (completeness * 0.3) + 
             (filter_match * 0.4) + 
             (source_reliability * 0.3)
```

#### Aggregiert (Multi-Source):
```python
weights = {'supabase': 0.55, 'notion': 0.45}
aggregated = sum(score * weight) / sum(weights)
```

### Threshold-Enforcement

**Automatisches "I don't know" wenn:**
1. `aggregated_confidence < threshold`
2. Alle Quellen haben `information_not_found = True`
3. Keine Quelle ist `verified = True`
4. Einzelne kritische Quelle unter Threshold (strict mode)

### Confidence-Aware Prompt Anpassung

```python
if confidence >= threshold + 0.05:
    # High confidence - kann lenient mode verwenden
    strictness = "lenient"
elif confidence >= threshold:
    # Meets threshold - moderate mode
    strictness = "moderate"
elif confidence >= threshold - 0.10:
    # Marginal - strict mode mit Disclaimern
    strictness = "strict"
else:
    # Below threshold - "I don't know"
    return dont_know_response
```

## 🔍 Data Conflict Detection

### Conflict Detection Workflow

```python
conflicts = detect_data_conflicts(retrieved_data, field_name="price")

if conflicts['has_conflicts']:
    for conflict in conflicts['conflict_details']:
        print(f"Field: {conflict['field']}")
        print(f"Source 1: {conflict['source1']['value']} (confidence: {conflict['source1']['confidence']})")
        print(f"Source 2: {conflict['source2']['value']} (confidence: {conflict['source2']['confidence']})")
```

### Conflict Resolution Strategies

**Strict Mode:**
- Präsentiere ALLE Versionen mit Zitaten
- KEINE automatische Auflösung
- Format: "Source A states X [Source: A], while Source B states Y [Source: B]"

**Moderate Mode:**
- Kann basierend auf Confidence-Scores auflösen
- Erwähne niedrigere Confidence-Version
- Format: "Based on higher confidence source (0.95): X [Source: A]. Note: Source B reports Y [0.80]"

**Lenient Mode:**
- Verwende höchste Confidence-Quelle
- Erwähne Konflikt in Fußnote
- Format: "X [Source: A]. (Alternative value from Source B: Y)"

## 📝 Citation Formatting

### Standard Citation Format

```
[Source: {source_type}-{source_id}]
```

**Beispiele:**
- `[Source: supabase-user-123]`
- `[Source: notion-project-456]`

### With Timestamp

```
[Source: {source_type}-{source_id}, Retrieved: {timestamp}]
```

**Beispiel:**
- `[Source: supabase-user-123, Retrieved: 2026-01-01 15:00 UTC]`

### Multiple Sources

```
[Sources: supabase-user-123, notion-profile-456]
```

## 🚀 Best Practices

### 1. **Wähle den richtigen Strictness Level**

| Use Case | Empfohlener Level | Begründung |
|----------|-------------------|------------|
| Medizinische Diagnosen | Strict | Patientensicherheit kritisch |
| Finanzberichte | Strict | Regulatorische Anforderungen |
| Kundenservice | Moderate | Balance zwischen Hilfe und Genauigkeit |
| Projektplanung | Moderate | Flexibilität mit Fakten-Basis |
| Brainstorming | Lenient | Kreativität mit Grundwahrheit |
| Code-Dokumentation | Moderate | Genauigkeit wichtig, Kontext hilfreich |

### 2. **Confidence Thresholds anpassen**

```python
# Kritische Anwendungen
confidence_threshold = 0.95

# Standard-Anwendungen
confidence_threshold = 0.85

# Explorative Anwendungen
confidence_threshold = 0.75
```

### 3. **Auto-Detection nutzen**

Für die meisten Anwendungen ist Auto-Detection optimal:

```python
result = generate_adaptive_prompt(
    query=query,
    retrieved_data=data,
    confidence_threshold=0.85
)
# System wählt automatisch basierend auf Datenqualität
```

### 4. **Response Validation implementieren**

Validiere IMMER kritische Antworten:

```python
validation = validate_response(
    query=query,
    llm_response=response,
    retrieved_data=data
)

if not validation['is_valid']:
    # Regenerate oder ablehnen
    handle_invalid_response(validation['issues'])
```

### 5. **Metriken monitoren**

```python
metrics = generator.get_metrics()

if metrics['dont_know_rate'] > 0.30:
    # Zu viele "I don't know" - Datenqualität prüfen
    investigate_data_quality()

if metrics['cache_hit_rate'] < 0.20:
    # Niedriger Cache-Hit - Cache-Strategie anpassen
    adjust_caching()
```

## ⚡ Performance-Optimierung

### 1. **Prompt Caching aktivieren**

```python
result = generator.generate_prompt(
    query=query,
    retrieved_data=data,
    use_cache=True  # Cache aktivieren
)
```

**Vorteile:**
- Schnellere Wiederholungsabfragen
- Reduzierte Berechnung
- Konsistente Prompts

**Nachteile:**
- Speicherverbrauch
- Stale data bei Updates

**Lösung:** Cache bei Webhook-Updates leeren

```python
@app.post("/api/v1/webhooks/supabase")
async def webhook(payload):
    prompt_generator.clear_cache()  # Cache invalidieren
```

### 2. **Batch-Processing**

Für mehrere Abfragen:

```python
results = []
for query in queries:
    result = generator.generate_prompt(
        query=query,
        retrieved_data=get_data(query),
        use_cache=True
    )
    results.append(result)
```

### 3. **Minimale Metadata bei hohem Volumen**

```python
user_prompt = create_user_prompt(
    query=query,
    retrieved_data=data,
    include_detailed_metadata=False,  # Reduziert Prompt-Größe
    include_confidence_analysis=True
)
```

## 🛠️ Troubleshooting

### Problem: Zu viele "I don't know" Antworten

**Ursachen:**
- Confidence threshold zu hoch
- Schlechte Datenqualität
- Unzureichende Quellenverifikation

**Lösungen:**
```python
# 1. Threshold senken (mit Vorsicht)
confidence_threshold = 0.80  # statt 0.85

# 2. Datenqualität verbessern
# 3. Mehr Quellen hinzufügen
# 4. Lenient mode für nicht-kritische Abfragen verwenden
```

### Problem: LLM ignoriert "I don't know" Anweisung

**Ursachen:**
- LLM zu stark trainiert auf Antworten
- System prompt nicht stark genug
- Fehlende Temperatur-Kontrolle

**Lösungen:**
```python
# 1. Strict mode verwenden
result = generate_strict_prompt(...)

# 2. LLM-Temperatur senken
llm_params = {"temperature": 0.1}

# 3. Pre-check implementieren
if result.should_use_dont_know:
    return result.dont_know_response  # Bevor LLM aufgerufen wird
```

### Problem: Konflikte werden nicht erkannt

**Ursachen:**
- Feldnamen unterschiedlich
- Datentypen inkompatibel
- Keine gemeinsamen Felder

**Lösungen:**
```python
# 1. Spezifisches Feld prüfen
conflicts = detect_conflicts(data, field_name="price")

# 2. Daten normalisieren vor Vergleich
# 3. Custom Conflict Detection implementieren
```

## 📈 Metriken und Monitoring

### Key Performance Indicators (KPIs)

1. **"I Don't Know" Rate**
   - Target: < 15% (außer bei schlechter Datenqualität)
   - Berechnung: `dont_know_responses / total_prompts`

2. **Cache Hit Rate**
   - Target: > 25% (bei wiederholten Abfragen)
   - Berechnung: `cache_hits / total_prompts`

3. **Validation Pass Rate**
   - Target: > 95%
   - Berechnung: `valid_responses / validated_responses`

4. **Average Confidence**
   - Target: > threshold + 0.05
   - Berechnung: `sum(confidences) / count`

### Monitoring Setup

```python
# Periodisches Monitoring
@app.get("/api/v1/monitoring/health")
async def monitoring_health():
    metrics = generator.get_metrics()
    
    alerts = []
    
    if metrics['dont_know_rate'] > 0.30:
        alerts.append("High 'I don't know' rate")
    
    if metrics['cache_hit_rate'] < 0.15:
        alerts.append("Low cache efficiency")
    
    return {
        "status": "warning" if alerts else "healthy",
        "alerts": alerts,
        "metrics": metrics
    }
```

## 🔐 Sicherheit und Compliance

### 1. **Data Privacy**
- Keine sensiblen Daten in System Prompts loggen
- Cache für sensitive Daten deaktivieren
- Metriken anonymisieren

### 2. **Audit Trail**
```python
import logging

logger.info({
    "event": "prompt_generated",
    "query_hash": hash(query),  # Nicht der Query selbst
    "confidence": confidence,
    "strictness": strictness,
    "timestamp": datetime.utcnow()
})
```

### 3. **Rate Limiting**
```python
from fastapi_limiter import FastAPILimiter

@app.post("/api/v1/prompt/generate")
@limiter.limit("100/minute")
async def generate_prompt(...):
    ...
```

## 📚 Weitere Ressourcen

- **Technische Spezifikation**: `TECHNICAL_SPEC.md`
- **Verwendungsbeispiele**: `examples/anti_hallucination_usage.py`
- **API-Dokumentation**: `http://localhost:8000/docs`
- **Validators**: `validators.py`
- **Prompt Templates**: `prompt_templates.py`
- **Integration**: `prompt_integration.py`

## 🆘 Support

Bei Fragen oder Problemen:
1. Überprüfe die Beispiele in `examples/`
2. Konsultiere die API-Dokumentation
3. Prüfe die Metriken für Hinweise
4. Öffne ein Issue im Repository

---

**Version:** 2.0.0  
**Zuletzt aktualisiert:** 2026-01-01  
**Autor:** Daniela Mümken
