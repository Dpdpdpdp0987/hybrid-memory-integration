# 🚀 Quick Start: Anti-Hallucination Prompt System

Schnelleinstieg in das erweiterte Anti-Halluzination Prompt-System.

## 📦 Installation

Keine zusätzlichen Dependencies erforderlich. Das System verwendet bereits vorhandene Bibliotheken.

```bash
# Repository klonen (falls noch nicht geschehen)
git clone https://github.com/Dpdpdpdp0987/hybrid-memory-integration.git
cd hybrid-memory-integration

# Dependencies installieren
pip install -r requirements.txt

# Environment konfigurieren
cp .env.example .env
# .env mit deinen Credentials bearbeiten
```

## ⚡ Schnellstart (5 Minuten)

### 1. Server starten

```bash
python main.py
```

Server läuft auf: `http://localhost:8000`  
API-Dokumentation: `http://localhost:8000/docs`

### 2. Erste Prompt-Generierung (curl)

```bash
# Adaptive Prompt mit Auto-Detection
curl -X POST "http://localhost:8000/api/v1/prompt/generate/adaptive" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the user status?",
    "sources": ["supabase", "notion"]
  }'
```

### 3. Python Client Beispiel

```python
import requests

# Adaptive Prompt generieren
response = requests.post(
    "http://localhost:8000/api/v1/prompt/generate/adaptive",
    json={
        "query": "What is the current project status?",
        "sources": ["supabase", "notion"]
    }
)

result = response.json()

# Prompt verwenden
if result['should_use_dont_know']:
    print(result['dont_know_response'])
else:
    # Mit deinem LLM verwenden
    prompt = result['prompt']
    print(f"System: {prompt['system_prompt'][:200]}...")
    print(f"User: {prompt['user_prompt'][:200]}...")
```

## 🎯 Häufigste Use Cases

### Use Case 1: Kritische Abfragen (Medizin, Finanzen, Recht)

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/prompt/generate",
    json={
        "query": "What is the patient's medication dosage?",
        "sources": ["supabase", "notion"],
        "strictness_level": "strict",  # Maximale Sicherheit
        "confidence_threshold": 0.95   # Hohe Schwelle
    }
)

result = response.json()
```

**Eigenschaften:**
- ❌ ZERO Tolerance für Halluzinationen
- ✅ Jede Info MUSS zitiert werden
- ✅ "I don't know" bei Unsicherheit

### Use Case 2: Allgemeine Abfragen (Standard)

```python
response = requests.post(
    "http://localhost:8000/api/v1/prompt/generate/adaptive",
    json={
        "query": "What are the recent updates?",
        "sources": ["supabase", "notion"]
    }
)
```

**Eigenschaften:**
- ✅ Automatische Strictness-Wahl
- ✅ Balanciert Genauigkeit & Hilfsbereitschaft
- ✅ Anpassung an Datenqualität

### Use Case 3: Explorative Abfragen (Brainstorming)

```python
response = requests.post(
    "http://localhost:8000/api/v1/prompt/generate",
    json={
        "query": "What could be potential improvements?",
        "sources": ["supabase", "notion"],
        "strictness_level": "lenient",
        "confidence_threshold": 0.75
    }
)
```

**Eigenschaften:**
- ✅ Flexibler, aber akkurat
- ✅ Kontext erlaubt
- ✅ Begründete Inferenzen möglich

### Use Case 4: Response Validierung

```python
# Nach LLM-Antwort validieren
validation = requests.post(
    "http://localhost:8000/api/v1/prompt/validate",
    json={
        "query": "What is the balance?",
        "llm_response": "The balance is $1500 [Source: supabase-acc-123]",
        "sources": ["supabase"],
        "strict_validation": True
    }
)

result = validation.json()

if not result['is_valid']:
    print(f"⚠️ Validation failed: {result['issues']}")
else:
    print("✅ Response is valid")
```

### Use Case 5: Konflikt-Erkennung

```python
# Wenn mehrere Quellen unterschiedliche Daten haben
comparison = requests.post(
    "http://localhost:8000/api/v1/prompt/compare",
    json={
        "query": "What is the product price?",
        "sources": ["supabase", "notion"]
    }
)

result = comparison.json()

if result['conflict_analysis']['has_conflicts']:
    print("⚠️ Conflicts detected!")
    for conflict in result['conflict_analysis']['conflict_details']:
        print(f"  Field: {conflict['field']}")
        print(f"  Source 1: {conflict['source1']['value']}")
        print(f"  Source 2: {conflict['source2']['value']}")
```

## 📊 Metriken abrufen

```python
# Aktuelle Metriken
metrics = requests.get("http://localhost:8000/api/v1/prompt/metrics")
data = metrics.json()

print(f"Prompts generiert: {data['metrics']['prompts_generated']}")
print(f"'I don't know' Rate: {data['metrics']['dont_know_rate']:.2%}")
print(f"Cache Hit Rate: {data['metrics']['cache_hit_rate']:.2%}")
```

## 🔧 Programmierung (direkter Import)

### Beispiel 1: Strict Prompt

```python
from prompt_integration import generate_strict_prompt
from models import DataResponse, SourceMetadata, ConfidenceScore, SourceType
from datetime import datetime

# Deine DataResponse Objekte
data_responses = [
    DataResponse(
        data={"medication": "Metformin", "dosage": "500mg"},
        source_metadata=SourceMetadata(
            source_type=SourceType.SUPABASE,
            source_id="patient-123",
            table_name="medications"
        ),
        confidence=ConfidenceScore(
            score=0.95,
            reasoning="High quality data",
            factors={"completeness": 0.95}
        ),
        information_not_found=False,
        verified=True,
        timestamp=datetime.utcnow()
    )
]

# Strict Prompt generieren
result = generate_strict_prompt(
    query="What is the medication dosage?",
    retrieved_data=data_responses,
    confidence_threshold=0.90
)

if result.should_use_dont_know:
    print(result.dont_know_response)
else:
    # Mit LLM verwenden
    system_prompt = result.prompt_template.system_prompt
    user_prompt = result.prompt_template.user_prompt
```

### Beispiel 2: Adaptive Prompt

```python
from prompt_integration import generate_adaptive_prompt

# System wählt automatisch optimale Strictness
result = generate_adaptive_prompt(
    query="What is the project status?",
    retrieved_data=data_responses
)

print(f"Auto-detected: {result.strictness_level}")
print(f"Confidence: {result.aggregated_confidence:.3f}")
```

### Beispiel 3: PromptGenerator Klasse

```python
from prompt_integration import PromptGenerator
from validators import DataValidator

# Generator erstellen
validator = DataValidator(confidence_threshold=0.85)
generator = PromptGenerator(validator=validator)

# Prompt mit Cache generieren
result = generator.generate_prompt(
    query="What is the status?",
    retrieved_data=data_responses,
    auto_detect_strictness=True,
    use_cache=True  # Cache aktivieren
)

# Metriken abrufen
metrics = generator.get_metrics()
print(f"Cache Hit Rate: {metrics['cache_hit_rate']:.2%}")
```

## 🎚️ Wann welche Strictness?

| Situation | Strictness | Threshold | Begründung |
|-----------|------------|-----------|------------|
| Medizinische Diagnose | `strict` | 0.95 | Patientensicherheit |
| Finanzielle Beratung | `strict` | 0.90 | Regulatorisch |
| Kundenservice | `moderate` | 0.85 | Balance |
| Projektplanung | `moderate` | 0.85 | Flexibilität |
| Brainstorming | `lenient` | 0.75 | Kreativität |
| Code-Doku | `moderate` | 0.85 | Genauigkeit |

## 🚨 Häufige Fehler vermeiden

### ❌ Fehler 1: Strictness zu niedrig für kritische Daten

```python
# FALSCH - zu niedrig für medizinische Daten
response = generate_prompt(
    query="Patient medication?",
    strictness_level="lenient"  # ❌ Zu riskant!
)

# RICHTIG
response = generate_strict_prompt(
    query="Patient medication?",
    confidence_threshold=0.95  # ✅ Sicher
)
```

### ❌ Fehler 2: "I don't know" ignorieren

```python
# FALSCH - Response trotz niedrigem Confidence verwenden
result = generate_prompt(...)
llm_response = call_llm(result.prompt_template)  # ❌

# RICHTIG - Pre-check
result = generate_prompt(...)
if result.should_use_dont_know:
    return result.dont_know_response  # ✅ Sicher
else:
    llm_response = call_llm(result.prompt_template)
```

### ❌ Fehler 3: Response nicht validieren

```python
# FALSCH - keine Validierung
llm_response = call_llm(prompt)
return llm_response  # ❌ Könnte Halluzinationen enthalten

# RICHTIG - mit Validierung
llm_response = call_llm(prompt)
validation = validate_response(query, llm_response, data)
if not validation['is_valid']:
    # Retry oder Fehler
    return handle_invalid_response()
return llm_response  # ✅
```

## 📚 Weiterführende Ressourcen

- **Vollständiger Guide**: [ANTI_HALLUCINATION_GUIDE.md](ANTI_HALLUCINATION_GUIDE.md)
- **Technische Spec**: [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md)
- **Beispiele**: [examples/anti_hallucination_usage.py](examples/anti_hallucination_usage.py)
- **Tests**: [tests/test_anti_hallucination_prompts.py](tests/test_anti_hallucination_prompts.py)
- **API-Docs**: http://localhost:8000/docs (nach Server-Start)

## 🆘 Support

### Problem: Zu viele "I don't know"

**Lösung:**
1. Datenqualität prüfen
2. Threshold senken (mit Vorsicht)
3. Mehr Quellen hinzufügen
4. Lenient mode für nicht-kritische Queries

### Problem: LLM ignoriert Anweisungen

**Lösung:**
1. Strict mode verwenden
2. Temperature senken (0.1)
3. Pre-check mit `should_use_dont_know`

### Problem: Performance

**Lösung:**
1. Cache aktivieren: `use_cache=True`
2. Detailed metadata deaktivieren bei Volumen
3. Webhook Cache-Invalidierung nutzen

## ✅ Checkliste für Production

- [ ] Strictness-Level für Use Cases definiert
- [ ] Confidence-Thresholds konfiguriert
- [ ] Response-Validierung implementiert
- [ ] Metriken-Monitoring eingerichtet
- [ ] Cache-Strategie definiert
- [ ] Error-Handling implementiert
- [ ] Logging konfiguriert
- [ ] Tests geschrieben

## 🎉 Fertig!

Du bist jetzt bereit, das Anti-Halluzination-System zu verwenden!

**Nächste Schritte:**
1. ✅ Erstes Prompt generieren
2. ✅ Mit eigenem LLM testen
3. ✅ Response validieren
4. ✅ Metriken monitoren

Bei Fragen: Siehe [ANTI_HALLUCINATION_GUIDE.md](ANTI_HALLUCINATION_GUIDE.md)

---

**Version:** 2.0.0  
**Autor:** Daniela Mümken  
**Datum:** 2026-01-01
