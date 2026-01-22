# FU Campus Chatbot - Arena Voting System

Leichtes, produktionsreifes System zum Vergleichen und Bewerten von KI-generierten Antworten mit Web-Dashboard, On-Demand-Generierung und statistischer Auswertung.

## 🎯 Überblick

Das System besteht aus zwei Hauptkomponenten:
- **Arena API** (Port 8001): FastAPI Backend mit On-Demand Answer Generation, Voting-Endpoints und JSONL-basierter Persistenz
- **Voting Dashboard** (Port 8002): Web-Interface mit 4-Subset System, Background-Prefetching und Blind A/B Testing

### ✨ Neue Features (Januar 2026)
- 🎯 **4-Subset System**: 59 Fragen in 4 Subsets à ~15 Fragen aufgeteilt
- ⚡ **On-Demand Generierung**: Frische Antworten für jede Session (maximale Varianz)
- 🚀 **5-Fragen Prefetch Buffer**: Parallele Background-Generierung für minimale Wartezeit
- 🔀 **Round-Robin Subset-Zuweisung**: Gleichmäßige Verteilung der User auf Subsets
- ✅ **Completion Detection**: Automatischer Stopp nach 15 Fragen pro Subset
- 🔒 **Subset-Validierung**: Backend prüft dass Fragen zum zugewiesenen Subset gehören

Alle Votes werden persistent in `arena_votes.jsonl` gespeichert.

## 🚀 Quick Start

### Local Development (mit Docker)

```bash
# Repository klonen
git clone <repo> && cd FU_Chatbot_RD_Zitho

# .env Datei vorbereiten (siehe docs/ENVIRONMENT.md)
cp .env.production.template .env

# Services starten
ENVIRONMENT=LOCAL docker compose -f docker-compose.prod.yml up -d

# Status überprüfen
docker ps | grep arena
```

**Zugriff:**
- 🎯 Voting Dashboard: http://localhost:8002
- 📊 Statistiken API: http://localhost:8001/arena/statistics
- 🔍 Alle Comparisons: http://localhost:8001/arena/comparisons

### Voting UI nutzen

1. Öffne http://localhost:8002/results
2. Wähle Subset oder "Alle Subsets"
3. Klick auf eine Frage zum Voten (wenn nicht bereits gevotet)
4. Wähle: A gewinnt / B gewinnt / Unentschieden / Beide schlecht
5. Ergebnisse werden live aktualisiert
6. **CSV Export** für alle Daten verfügbar

## 📂 Projektstruktur

```
src/openwebui/
├── arena_api.py                    # Alias für openwebui_api_llm.py
├── openwebui_api_llm.py           # Main API (LLM + Voting + On-Demand Generation)
├── arena_questions.py             # ✨ NEW: Question catalog mit 4 Subsets
├── voting_ui_simple.py            # Voting Dashboard mit Prefetching
├── voting_system.py               # JSONL-basierte Vote-Persistenz
├── voting_system.py               # JSONL Storage Engine
├── voting_ui_simple.py            # Web Dashboard
├── arena_voting.py                # CLI Tool (optional)
├── data/
│   └── arena_votes.jsonl          # Live Vote Storage
└── requirements.txt

docker-compose.prod.yml            # Production Stack (4 Services)
nginx/
├── nginx.conf.prod                # Reverse Proxy Config
└── ssl/                           # SSL Certificates

docs/
├── ENVIRONMENT.md                 # Alle .env Variablen erklärt
├── SSL_TLS_SETUP.md               # Certificate Management
└── VM-REQUIREMENTS.md             # Infrastructure Requirements

scripts/
├── deploy-production.sh           # Deployment Lifecycle
├── health-check.sh                # Monitoring
└── arena_seed_*.py                # Daten importieren
```

## 🔧 Konfiguration

### Minimale .env Variablen

```env
ENVIRONMENT=LOCAL          # oder PRODUCTION
DOMAIN_NAME=localhost      # oder deine Domain
POSTGRES_PASSWORD=dev      # Für Zukunftserweiterungen

# Für LLM-Features (optional)
AZURE_OPENAI_URL=...       # Azure OpenAI Endpoint
AZURE_OPENAI_API_KEY=...   # API Key
QDRANT_URL=...             # Vector DB URL
QDRANT_API_KEY=...         # API Key
```

**Alle Variablen:** Siehe [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)

## 📊 API Endpoints

| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| GET | `/health` | Health Check |
| GET | `/arena/statistics` | Voting Statistiken |
| GET | `/arena/comparisons` | Alle Comparisons laden |
| GET | `/arena/comparisons?subset=1` | Nur Subset 1 |
| POST | `/arena/save-comparison` | Vergleich speichern |
| POST | `/arena/vote` | Vote abgeben |

## 🐳 Docker

### Starten
```bash
ENVIRONMENT=LOCAL docker compose -f docker-compose.prod.yml up -d
```

### Logs anschauen
```bash
docker compose -f docker-compose.prod.yml logs -f arena-api
docker compose -f docker-compose.prod.yml logs -f arena-ui
```

### Services neu starten
```bash
docker compose -f docker-compose.prod.yml restart arena-api arena-ui
```

### Herunterfahren
```bash
docker compose -f docker-compose.prod.yml down
```

## 🚀 Production Deployment

1. **Server vorbereiten:** Docker + Docker Compose installieren
2. **Repo klonen:** `git clone <repo> && cd FU_Chatbot_RD_Zitho`
3. **.env konfigurieren:** Siehe [DEPLOYMENT.md](DEPLOYMENT.md)
4. **Deployen:** `./scripts/deploy-production.sh deploy`

Oder manuell:
```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
./scripts/health-check.sh
```

## 📚 Dokumentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Systemarchitektur & Datenflüsse
- **[VOTING.md](VOTING.md)** - Voting-System Details
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production Deployment Checkliste
- **[docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)** - .env Konfiguration
- **[docs/SSL_TLS_SETUP.md](docs/SSL_TLS_SETUP.md)** - Zertifikat Setup
- **[docs/VM-REQUIREMENTS.md](docs/VM-REQUIREMENTS.md)** - Infrastructure

## 🛠️ Entwicklung

### Dependencies installieren
```bash
python -m pip install -r src/openwebui/requirements.txt
```

### API lokal starten
```bash
python -m uvicorn src.openwebui.openwebui_api_llm:app --port 8001
```

### Voting UI lokal starten
```bash
python -m uvicorn src.openwebui.voting_ui_simple:app --port 8002
```

## 📊 Datenformat

Votes werden als JSONL (JSON Lines) gespeichert:

```json
{
  "id": "uuid",
  "question": "Beispielfrage",
  "timestamp": "2026-01-14T13:00:00",
  "model_a": "kicampus-original",
  "answer_a": "Antwort A...",
  "model_b": "kicampus-improved",
  "answer_b": "Antwort B...",
  "vote": "A",
  "vote_timestamp": "2026-01-14T13:05:00",
  "subset_id": 1,
  "comment": "optional"
}
```

## 🆘 Troubleshooting

**API nicht erreichbar?**
```bash
curl http://localhost:8001/health
docker logs fu-arena-api
```

**Voting UI zeigt keine Daten?**
```bash
curl http://localhost:8001/arena/comparisons
```

**SSL-Fehler?**
```bash
# Dev-Zertifikate regenerieren
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem -out nginx/ssl/fullchain.pem \
  -subj "/C=DE/ST=Berlin/L=Berlin/O=FU/CN=localhost"
docker restart fu-arena-nginx
```

## 📋 Status

✅ **Arena System vollständig produktionsreif**
✅ **Voting-System live mit JSONL-Persistenz**
✅ **Web-Dashboard mit CSV-Export**
✅ **Docker Production Stack ready**
✅ **SSL/TLS automatisiert**

- Code:
    - UI and Results: `src/openwebui/voting_ui_simple.py`
    - Lightweight Arena API: `src/openwebui/arena_api.py`
    - Storage (append-only JSONL): `src/openwebui/data/arena_votes.jsonl` (not committed)

## Run locally (two processes)

Start the API (arena endpoints only):

```zsh
/Users/browse/FU_Chatbot_RD_Zitho/.venv/bin/python -m uvicorn src.openwebui.arena_api:app --host 127.0.0.1 --port 8001
```

Start the UI (voting + results dashboard):

```zsh
/Users/browse/FU_Chatbot_RD_Zitho/.venv/bin/python -m uvicorn src.openwebui.voting_ui_simple:app --host 127.0.0.1 --port 8002
```

Open in browser:

- Voting UI: http://127.0.0.1:8002/
- Results dashboard: http://127.0.0.1:8002/results (filters, search, CSV export)

## API surface (used by UI)

- `GET  /arena/comparisons` – list comparisons
- `GET  /arena/statistics` – aggregate stats (backend-only)
- `GET  /arena/comparison/{id}` – one comparison
- `POST /arena/save-comparison` – create new comparison
- `POST /arena/vote` – record a vote `{comparison_id, vote: "A"|"B"|"tie", comment?}`

## Notes & Troubleshooting

- Use `127.0.0.1` explicitly (not `localhost`) to avoid Safari localhost quirks.
- The results page shows live status messages and logs to the browser console on errors.
- CSV export escapes quotes and replaces newlines for Excel/Sheets compatibility.
- Data is stored in `src/openwebui/data/arena_votes.jsonl`; keep it out of commits.
- If results show "Lade…" endlessly: verify API is up and `GET /arena/comparisons` returns data.
- If Safari reports JS syntax errors, ensure you’re on branch `feature/openwebui-arena` (contains fixes for newline/quote escaping and missing elements).

## 🌱 Seeding Comparisons

You can seed via the API (`POST /arena/save-comparison`) or the helper scripts in `scripts/`.

### ⚠️ CRITICAL: Storage Path

**The Arena loads comparisons from `src/openwebui/data/arena_votes.jsonl`**

Seeding scripts automatically write to the correct location. Make sure to:
- Use `scripts/arena_seed_external.py` for external chatbot APIs
- The script will write to `src/openwebui/data/arena_votes.jsonl` (NOT `data/arena_votes.jsonl`)
- Verify seeded data appears in http://localhost:8002 after running

### Seeding External Chatbots (via API)

For comparing two external chatbot versions:

```bash
# Seed with fixed questions (one per line in UTF-8 text file)
python scripts/arena_seed_external.py

# The script will:
# 1. Load questions from data/fixed_questions.txt
# 2. Call both chatbots via Arena API (/v1/chat/completions)
# 3. Write comparisons to src/openwebui/data/arena_votes.jsonl
# 4. Make them immediately visible in the voting UI
```

**Setup required:**
- Create `data/fixed_questions.txt` with one question per line
- Both external chatbots must be running
- Arena API must be accessible at `http://localhost:8001`

### Legacy: Direct JSONL Seeding

For pre-existing answer pairs:

```bash
# From a newline-separated questions file
python scripts/arena_seed.py --questions path/to/questions.txt

# From a JSON array
python scripts/arena_seed.py --json path/to/items.json

# Custom models and answer templates
python scripts/arena_seed.py \
    --questions questions.txt \
    --model-a "kicampus-original" \
    --model-b "kicampus-improved" \
    --storage-file src/openwebui/data/arena_votes.jsonl

# Preview without saving
python scripts/arena_seed.py --questions questions.txt --dry-run
```

# Data Extraction

# Moodle
To access content from Moodle, you need access to Moodle courses via the REST API. To set up the integration, do the following steps:
0. Get admin access to moodle.
1. Enable Web Services: _Site Administration_ -> _General_ -> _Advanced Features_ -> _Enable web services_
2. Enable REST Protocol: _Site Administration_ -> _Server_ -> _Web Services_ -> _Manage Protocols_ -> _Enable REST protocol_
3. (Optional): Create a technical new user/roles
4. Create a new external service _Site Administration_ -> _Server_ -> _External services_. Give it a name and enable _Enabled_, _Authorized users only_ and _Can download files_ (under _Show more..._).
5. Add the user as an _Authorised User_ to the external service.
6. Add the following functions to the external service:
    - core_block_get_course_blocks
    - core_course_get_categories
    - core_course_get_contents
    - core_course_get_course_content_items
    - core_course_get_course_module
    - core_course_get_courses
    - core_course_get_module
7. Create a token for the user and external service under _Site Administration_ -> _Server_ -> _Manage tokens_. This allows you to authenticate against the REST API.

You can try it out with a GET request against this url (swap TOKEN for your token und FUNCTION against the function to test):
https://ki-campus-test.fernuni-hagen.de/webservice/rest/server.php?wstoken=TOKEN&wsfunction=FUNCTION&moodlewsrestformat=json
