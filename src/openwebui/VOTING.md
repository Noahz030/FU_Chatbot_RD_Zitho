# 🏆 Arena Voting System - Dokumentation

Vollständiges System für Side-by-Side Benchmarking von KI-Campus Chatbot Versionen mit automatischem Voting und Statistik-Logging.

## 🎯 Ziel

Vergleiche zwei Versionen des KI-Campus Chatbots (**original** vs **verbessert**) side-by-side in OpenWebUI Arena Mode und vote welche Version besser ist.

## 🏗️ Architektur

```
┌─────────────────────────────────────────┐
│         Browser / UI Layer              │
├─────────────────────────────────────────┤
│  OpenWebUI (3001)  │  Voting UI (8002)  │
├─────────────────────────────────────────┤
│         API Layer (FastAPI)             │
├──────────────────────────────┬──────────┤
│   LLM API (8001)             │ Storage  │
│ • /v1/chat/completions      │ (JSONL)  │
│ • /arena/vote               │          │
│ • /arena/statistics         │          │
├──────────────────────────────┴──────────┤
│      Azure OpenAI GPT-4 (via Lab KV)    │
└─────────────────────────────────────────┘
```

## 📂 Dateien

**Voting System Kern:**
- `src/openwebui/voting_system.py` - Vote Storage (JSONL-basiert)
- `src/openwebui/voting_ui.py` - Web UI Dashboard (Port 8002)
- `src/openwebui/voting_widget.py` - Widget für HTML Injection
- `src/openwebui/arena_voting.py` - CLI Tool

**API Integration:**
- `src/openwebui/openwebui_api_llm.py` - Hauptgruppe mit Voting Endpoints
  - `/arena/save-comparison` - Speichert Vergleich
  - `/arena/vote` - Submitiert Vote
  - `/arena/statistics` - Zeigt Statistiken
  - `/arena/comparisons` - Alle Vergleiche
  - `/arena/comparison/{id}` - Einzelner Vergleich
  - `/arena/user-votes` - **NEU:** Per-User Votes mit Session-IDs (für detaillierte Analyse)
  - `/arena/assign-subset` - Subset-Zuordnung für Benutzer
  - `/arena/voted` - Bereits gevotet von dieser Session

**Daten:**
- `src/openwebui/data/arena_votes.jsonl` - Persistent Vote Storage (JSONL Format)
- `src/openwebui/data/arena_user_votes.jsonl` - **NEU:** Detaillierte Voting-Einträge mit Session-Tracking

## 🚀 Quick Start

### Option 1: Automatisch (empfohlen)
```bash
./start_arena.sh
```

### Option 2: Manuell
```bash
# Terminal 1: Azure Login
az login --tenant "c6ff58bc-993e-4bdb-8d10-6013e2cd361f"

# Terminal 2: API starten
export KEY_VAULT_NAME="kicwa-keyvault-lab"
python -m uvicorn src.openwebui.openwebui_api_llm:app --port 8001 &

# Terminal 3: OpenWebUI starten
docker run -d -p 3001:8080 -v open-webui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/open-webui/open-webui:main

# Terminal 4: Voting UI starten
python -m uvicorn src.openwebui.voting_ui:app --port 8002 &
```

## 💻 Verwendung

### 1. Chat in OpenWebUI
```
http://localhost:3001
→ New Chat
→ Model Dropdown: "Arena (Side-by-side)"
→ Wähle: kicampus-original + kicampus-improved
→ Stelle Frage
```

### 2. Vote im Voting Dashboard
```
http://localhost:8002
→ Alle Vergleiche werden automatisch geladen
→ Für jeden Vergleich: Vote abgeben (A/B/Tie)
→ Optional: Kommentar hinzufügen
→ Submit
```

### 3. Statistiken ansehen
```
Im Voting Dashboard (Port 8002):
- Insgesamt Vergleiche
- Gevotet vs Ausstehend
- Win Rate Model A vs B
- Tie Rate
- Live Updates
```

## 🔧 API Beispiele

### Vergleich speichern
```bash
curl -X POST http://localhost:8001/arena/save-comparison \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Was ist Machine Learning?",
    "model_a": "kicampus-original",
    "answer_a": "...",
    "model_b": "kicampus-improved",
    "answer_b": "..."
  }'
```

### Vote abgeben
```bash
curl -X POST http://localhost:8001/arena/vote \
  -H "Content-Type: application/json" \
  -d '{
    "comparison_id": "uuid-here",
    "vote": "B",
    "comment": "Bessere Erklärung"
  }'
```

### Statistiken abrufen
```bash
curl http://localhost:8001/arena/statistics | jq .
```

### **NEU: User-Votes mit Session-IDs abrufen**
```bash
# Alle Votes mit Session-Tracking
curl http://localhost:8001/arena/user-votes | jq .

# Nur Votes einer spezifischen Session
curl http://localhost:8001/arena/user-votes?session_id=YOUR_SESSION_ID | jq .
```

**Response Format:**
```json
{
  "total": 23,
  "votes": [
    {
      "comparison_id": "550e8400-e29b-41d4-a716-446655440000",
      "vote": "B",
      "comment": null,
      "subset_id": 1,
      "session_id": "96356d34-3dbf-48b9-822c-19ed7f8f1481",
      "timestamp": "2026-01-14T14:47:14.576334"
    },
    ...
  ]
}
```

## 📊 Voting Dashboard & Analytics

### 1️⃣ Vergleiche-Dashboard: `/results`
```
http://localhost:8002/results
```
- Zeigt alle Comparisons mit aggregierten Votes
- Filter: Alle / Nur gevotet / Nur offen
- Subset-Filter für fokussierte Analyse
- **CSV Export** aller Voting-Daten
- Suche in Fragen & Antworten

### 2️⃣ **NEU: User-Votes Analyse: `/user-votes`**
```
http://localhost:8002/user-votes
```
- Detaillierte Voting-Records pro Session
- **Session-ID**: Eindeutige User-Kennung
- Timestamp: Wann jeder Vote abgegeben wurde
- Vote-Tracing: Wer hat was und wann gewählt?
- Subset-Zuordnung pro User sichtbar
- **CSV Export** für statistische Auswertung
- Suche nach Session oder Comparison-ID

### Integration in Voting Workflow:
```
Voting UI (/results) → "👥 User-Votes ansehen" → Detaillierte Analyse (/user-votes)
```

Dies ermöglicht:
- ✅ Vollständige Nachvollziehbarkeit der Abstimmungen
- ✅ Multi-Session-Tracking für A/B Testing
- ✅ Deduplication per Session (letzte Vote zählt)
- ✅ CSV Export für externe Analyse

Datei: `src/openwebui/data/arena_votes.jsonl`

Jede Zeile ist ein JSON Objekt:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "Was ist Machine Learning?",
  "timestamp": "2025-12-10T12:29:00.000000",
  "model_a": "kicampus-v1",
  "answer_a": "...",
  "model_b": "kicampus-v1-improved",
  "answer_b": "...",
  "vote": "B",
  "vote_timestamp": "2025-12-10T12:30:00.000000",
  "comment": "Bessere Detailverlauf",
  "subset_id": 1
}
```

## 🎮 CLI Tool

Für Testzwecke oder automatisierte Workflows:

```bash
# Interaktiv: Frage stellen → beide Modelle fragen → voten
python src/openwebui/arena_voting.py

# Statistiken anzeigen
python src/openwebui/arena_voting.py --stats

# In JSON exportieren
python src/openwebui/arena_voting.py --export results.json
```

## 📈 Workflow für Massentests

**Pro Durchgang (1-2 Stunden):**

1. Starte alle Services: `./start_arena.sh`
2. Öffne OpenWebUI: http://localhost:3001
3. Aktiviere Arena Mode (beide Modelle)
4. Stelle 10-20 Testfragen zu verschiedenen KI-Themen
5. Öffne Voting Dashboard: http://localhost:8002
6. Bewerte alle Vergleiche
7. Exportiere Ergebnisse: `python src/openwebui/arena_voting.py --export results.json`

**Beispiel-Fragen:**
- Was ist Künstliche Intelligenz?
- Erkläre Machine Learning
- Was sind Neural Networks?
- Wie funktioniert Deep Learning?
- Was ist Reinforcement Learning?
- Nenne Anwendungen von KI
- Was sind CNNs?
- Erkläre Natural Language Processing

## 🔍 Debugging

### API startet nicht
```bash
# Prüfe Azure Login
az account show

# Prüfe Logs
tail -50 /tmp/llm_api.log
```

### OpenWebUI antwortet nicht
```bash
# Prüfe Container
docker ps | grep openwebui

# Logs anschauen
docker logs openwebui
```

### Voting UI zeigt keine Vergleiche
```bash
# Prüfe ob API läuft
curl http://localhost:8001/arena/statistics

# Prüfe Browser Console (F12) auf Fehler
```

## 🛑 Stoppen

```bash
# Alle Prozesse stoppen
pkill -f "uvicorn"
docker stop openwebui
```

## 🔄 Weitere Entwicklung

Mögliche Erweiterungen:
- [ ] Automatische Fragen-Batches einplanen
- [ ] Emotion/Tone Analyse der Antworten
- [ ] A/B Testing mit Statistik-Signifikanz
- [ ] Dashboard mit Charts (Chart.js)
- [ ] Datenexport zu CSV/Excel
- [ ] Batch-Processing API
- [ ] Webhooks für externe Integration

## 📞 Support

Probleme? Schau in `src/openwebui/SETUP.md` oder:
```bash
# Logs prüfen
tail -f /tmp/llm_api.log
tail -f /tmp/voting_ui.log
docker logs -f openwebui
```

---

**Happy Benchmarking! 🚀**
