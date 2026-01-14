# 🏆 Arena Voting System - Dokumentation

Leichtes, produktionsreifes Voting-System mit Web-Dashboard für paarweise Modellvergleiche.

## 🎯 Ziel

Sammle Votes zum Vergleich zweier KI-generierter Antworten. Jedes Vergleichspaar wird mit einer Bewertung versehen und alle Daten persistent als JSONL gespeichert.

## 🏗️ Architektur

```
┌────────────────────────────────────────┐
│         Browser                        │
├────────────────────────────────────────┤
│  Voting UI (8002)                      │
│  - Comparisons anzeigen                │
│  - Voting Interface                    │
│  - Live Statistiken                    │
│  - CSV Export                          │
├────────────────────────────────────────┤
│         FastAPI (8001)                 │
├──────────────────────┬─────────────────┤
│  Arena API           │  Storage        │
│ • /arena/vote        │                 │
│ • /arena/comparisons │  arena_votes.   │
│ • /arena/statistics  │  jsonl          │
├──────────────────────┴─────────────────┤
│    Optional: Azure OpenAI              │
└────────────────────────────────────────┘
```

## 📂 Kernkomponenten

| Datei | Zweck | Status |
|-------|-------|--------|
| `src/openwebui/voting_system.py` | JSONL-basierte Vote-Persistenz | ✅ Aktiv |
| `src/openwebui/voting_ui_simple.py` | Web Dashboard (Port 8002) | ✅ Aktiv |
| `src/openwebui/openwebui_api_llm.py` | API mit Voting Endpoints | ✅ Aktiv |
| `src/openwebui/arena_voting.py` | CLI Tool (optional) | ⚠️ Optional |
| `src/openwebui/voting_widget.py` | HTML Widget (optional) | ⚠️ Optional |
| `src/openwebui/data/arena_votes.jsonl` | Live Vote Storage | ✅ Aktiv |

**Voting API Endpoints (in openwebui_api_llm.py):**
```
POST   /arena/save-comparison      # Vergleich speichern
POST   /arena/vote                 # Vote abgeben
GET    /arena/statistics           # Statistiken
GET    /arena/comparisons          # Alle Comparisons
GET    /arena/comparison/{id}      # Einzelner Vergleich
```

## 🚀 Quick Start

### Docker (empfohlen)
```bash
# .env vorbereiten (lokal können Default-Werte reichen)
cp .env.production.template .env

# Services starten
ENVIRONMENT=LOCAL docker compose -f docker-compose.prod.yml up -d

# Zugriff
open http://localhost:8002/results
```

### Manuell (ohne Docker)
```bash
# Terminal 1: API starten
python -m uvicorn src.openwebui.openwebui_api_llm:app --port 8001

# Terminal 2: Voting UI starten
python -m uvicorn src.openwebui.voting_ui_simple:app --port 8002

# Browser öffnen
open http://localhost:8002/results
```

## 💻 Voting Dashboard nutzen

1. **Dashboard öffnen:** http://localhost:8002/results

2. **Comparisons laden:**
   - Wähle ein Subset (1-4) oder "Alle Subsets"
   - Klick auf "Suche" oder "Filter" um zu filtern

3. **Voten:**
   - Jede Zeile ohne Vote kann geklickt werden
   - Wähle eine der 4 Optionen:
     - **A**: Model A ist besser
     - **B**: Model B ist besser
     - **tie**: Beide gleichwertig
     - **both_bad**: Beide schlecht

4. **Ergebnisse ansehen:**
   - Gefilterte Tabelle zeigt alle Votes
   - Statistiken aktualisieren sich live
   - **CSV exportieren:** Button am unteren Ende

## 📊 Vote-Struktur

Ein Vote wird als JSONL-Zeile gespeichert:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "Was ist die Hauptstadt von Deutschland?",
  "timestamp": "2026-01-14T10:30:00.000000",
  "model_a": "gpt-4",
  "answer_a": "Berlin ist die Hauptstadt und größte Stadt Deutschlands.",
  "model_b": "claude-3",
  "answer_b": "Die Hauptstadt Deutschlands ist Berlin.",
  "vote": "B",
  "vote_timestamp": "2026-01-14T10:35:45.123456",
  "comment": "Antwort B ist prägnanter",
  "subset_id": 1
}
```

**Feld-Erklärung:**
- `id`: Eindeutige Comparison-ID
- `question`: Die Frage, die beiden Modellen gestellt wurde
- `timestamp`: Wann wurde der Vergleich erstellt?
- `model_a`, `model_b`: Namen der verglichenen Modelle
- `answer_a`, `answer_b`: Antworten der Modelle
- `vote`: Die Abstimmung (A/B/tie/both_bad)
- `vote_timestamp`: Wann wurde gevotet?
- `comment`: Optional, Kommentar zum Vote
- `subset_id`: Welchem Subset gehört dieser Vergleich an?

## 📈 Statistiken API

### Alle Votes abrufen
```bash
curl http://localhost:8001/arena/statistics
```

**Response:**
```json
{
  "total_comparisons": 109,
  "voted": 76,
  "unvoted": 33,
  "votes_for_a": 24,
  "votes_for_b": 22,
  "votes_tie": 21,
  "votes_both_bad": 9,
  "win_rate_a": 0.3157894736842105,
  "win_rate_b": 0.2894736842105263,
  "tie_rate": 0.27631578947368424,
  "both_bad_rate": 0.11842105263157894,
  "models_seen": ["gpt-4", "claude-3", "llama-2", ...]
}
```

### Comparisons laden
```bash
# Alle
curl http://localhost:8001/arena/comparisons

# Nur Subset 1
curl http://localhost:8001/arena/comparisons?subset=1
```

## 🛠️ Daten importieren

### Ohne LLM (nur Vergleiche speichern)
```bash
python scripts/arena_seed_fixed.py \
  --input data/fixed_questions.txt \
  --api-url http://127.0.0.1:8001
```

### Mit LLM (Antworten generieren)
```bash
python scripts/arena_seed_with_llm.py \
  --input data/fixed_questions.txt \
  --api-url http://127.0.0.1:8001
```

## 🔧 Konfiguration

### Environment Variablen

```env
# API
ENVIRONMENT=LOCAL              # oder PRODUCTION
ARENA_API_KEY=<generate>        # Optional für Production

# Voting UI
CORS_ORIGINS=*                 # Oder specific domain

# Storage
JSONL_PATH=/data/arena_votes.jsonl

# Azure (optional für LLM)
AZURE_OPENAI_URL=https://...
AZURE_OPENAI_API_KEY=...
```

## 📂 Datenspeicherung

**Pfad:** `src/openwebui/data/arena_votes.jsonl`

**Format:** JSON Lines (jede Zeile = ein Vote)

**Persistenz:** Im Docker-Volume `arena_data` (bleibt nach Container-Stop)

**Backup:**
```bash
cp src/openwebui/data/arena_votes.jsonl arena_votes.backup.jsonl
```

## 🆘 Troubleshooting

### Keine Daten geladen?
```bash
# Überprüfe, ob Daten vorhanden sind
curl http://localhost:8001/arena/comparisons | python -m json.tool | head -20
```

### API antwortet nicht?
```bash
# Health Check
curl http://localhost:8001/health

# Logs anschauen
docker logs fu-arena-api
```

### CSV Export funktioniert nicht?
```bash
# Überprüfe Browser-Konsole auf Fehler
# Stelle sicher, dass Comparisons geladen sind
```

## 🔐 Sicherheit

- ✅ JSONL-Datei ist schreibgeschützt im Volume (nur API schreibt)
- ✅ CORS einschränkbar via .env
- ✅ Optional API-Key für /arena/vote endpoint
- ✅ Keine PII (personally identifiable information) gespeichert

## 📚 Weiterführende Dokumentation

- **[README.md](README.md)** - Haupteinstieg
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Systemarchitektur
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production Deployment
