# 🏗️ System Architektur

Detaillierte Dokumentation der Arena Voting Systemarchitektur, Komponenten und Datenflüsse.

## 📐 High-Level Übersicht

```
┌───────────────────────────────────────────────────────────────┐
│                   PUBLIC INTERNET (HTTPS)                     │
│              (arena.ki-campus.org:443)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
            ┌──────────────▼──────────────┐
            │  🔒 Nginx Reverse Proxy    │
            │  (TLS Termination)         │
            │  Port 80/443               │
            │  - SSL Certificates        │
            │  - Rate Limiting           │
            │  - Compression             │
            └─┬─────────────┬────────────┘
              │             │
    ┌─────────▼──┐   ┌──────▼──────────┐
    │ arena-api  │   │  arena-ui       │
    │ Port 8001  │   │  Port 8002      │
    │ (internal) │   │  (internal)     │
    │            │   │                 │
    │ FastAPI    │   │  FastAPI        │
    │ ✅ LLM     │   │  ✅ Dashboard   │
    │ ✅ Voting  │   │  ✅ Results     │
    │ ✅ Storage │   │  ✅ Stats       │
    └───┬────────┘   └─────────────────┘
        │
  ┌─────▼──────────────────────┐
  │  STORAGE & SERVICES        │
  ├────────────────────────────┤
  │                            │
  │  arena_data Volume:        │
  │  /data/arena_votes.jsonl   │
  │                            │
  │  postgres:5432             │
  │  (optional, future use)    │
  │                            │
  └─────┬──────────────┬───────┘
        │              │
  ┌─────▼──┐      ┌────▼───┐
  │ Azure  │      │ Qdrant │
  │ OpenAI │      │ Vector │
  │ GPT-4  │      │ DB     │
  └────────┘      └────────┘
```

## 🐳 Docker Services

| Service | Image | Port | Rolle |
|---------|-------|------|-------|
| **arena-api** | FastAPI (custom) | 8001 | API Backend + Voting |
| **arena-ui** | FastAPI (custom) | 8002 | Web Dashboard |
| **nginx** | nginx:latest | 80/443 | Reverse Proxy + TLS |
| **postgres** | postgres:15 | 5432 | Database (optional) |
| **certbot** | certbot:latest | - | SSL Cert Manager |

## 🔄 Datenflüsse

### Flow 1: Voting Submit

```
┌─────────────────────────┐
│ Voting UI (Browser)     │
│ User klickt "Vote: A"   │
└────────────┬────────────┘
             │
             │ POST /arena/vote
             │ {"comparison_id": "...", "vote": "A"}
             ▼
┌─────────────────────────┐
│  Nginx (Port 443)       │
│  Route to 8001          │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  arena-api (8001)       │
│  verify_arena_key()     │
│  submit_vote()          │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ voting_system.py        │
│ update_vote()           │
│ Append to JSONL         │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ arena_votes.jsonl       │
│ (Volume: arena_data)    │
└─────────────────────────┘
```

### Flow 2: Load Comparisons

```
┌─────────────────────────┐
│ Voting UI (Browser)     │
│ GET /arena/comparisons  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Nginx (Port 443)       │
│  Route to 8001          │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  arena-api (8001)       │
│  get_all_comparisons()  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ voting_system.py        │
│ load_all_comparisons()  │
│ Read JSONL              │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ arena_votes.jsonl       │
│ (Read from Volume)      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ arena-api (8001)        │
│ Return JSON             │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Voting UI Dashboard     │
│ Render in Browser       │
└─────────────────────────┘
```

### Flow 3: Generate Statistics

```
┌──────────────────────────┐
│ GET /arena/statistics    │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  arena-api (8001)        │
│  get_statistics()        │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ voting_system.py         │
│ get_statistics()         │
│ Parse JSONL              │
│ Calculate:               │
│ - vote counts            │
│ - win rates              │
│ - model breakdown        │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Return JSON              │
│ {                        │
│   "total": 109,          │
│   "voted": 76,           │
│   "votes_a": 24,         │
│   "win_rate_a": 0.316,   │
│   ...                    │
│ }                        │
└──────────────────────────┘
```

## 📁 Dateistruktur & Rollen

```
src/openwebui/
├── openwebui_api_llm.py          # Main API Server
│   ├── FastAPI app
│   ├── CORS Middleware
│   ├── API Routes:
│   │   ├── POST /arena/save-comparison
│   │   ├── POST /arena/vote
│   │   ├── GET  /arena/statistics
│   │   ├── GET  /arena/comparisons
│   │   └── GET  /arena/comparison/{id}
│   └── Depends on: voting_system.py
│
├── voting_system.py              # Storage Engine
│   ├── ArenaComparison Dataclass
│   ├── Vote Dataclass
│   ├── JSONLStorage Class:
│   │   ├── save_comparison()
│   │   ├── update_vote()
│   │   ├── load_all_comparisons()
│   │   ├── get_statistics()
│   │   └── get_comparisons_by_subset()
│   ├── File: /data/arena_votes.jsonl
│   └── Format: JSON Lines (1 object per line)
│
├── voting_ui_simple.py           # Web UI Server
│   ├── FastAPI app
│   ├── GET / → returns HTML
│   ├── GET /results → Returns HTML Dashboard
│   │   ├── Load comparisons from API
│   │   ├── Filter by subset/status
│   │   ├── Search functionality
│   │   └── CSV Export button
│   └── CORS to allow API calls
│
├── data/
│   └── arena_votes.jsonl         # Live Vote Storage
│       ├── Format: JSON Lines
│       ├── 1 line = 1 Vote object
│       ├── ~1KB per vote
│       └── Append-only (never delete)
│
├── Dockerfile                    # API Container
│   ├── python:3.11-slim
│   ├── Installs requirements.txt
│   ├── CMD: uvicorn openwebui_api_llm:app
│   └── Exposes port 8001
│
└── requirements.txt              # Python Dependencies
    ├── fastapi
    ├── uvicorn
    ├── pydantic
    ├── azure-identity (optional)
    ├── azure-keyvault-secrets (optional)
    └── qdrant-client (optional)

docker-compose.prod.yml          # Orchestration
├── Services:
│   ├── arena-api (build: .)
│   ├── arena-ui (build: .)
│   ├── nginx
│   ├── postgres
│   └── certbot
├── Volumes:
│   ├── arena_data (for /data/arena_votes.jsonl)
│   └── pg_data (for postgres)
├── Networks:
│   └── arena_network
└── Environment: .env

nginx/
├── nginx.conf.prod               # Reverse Proxy Config
│   ├── Listen on 80/443
│   ├── TLS Setup (fullchain.pem + privkey.pem)
│   ├── Upstream to 8001 (API)
│   ├── Upstream to 8002 (UI)
│   ├── Rate limiting: /arena/*
│   └── Gzip compression
│
└── ssl/                          # TLS Certificates
    ├── fullchain.pem             # Public cert
    └── privkey.pem               # Private key
```

## 🔌 API Endpoints

### Health & Status
```
GET /health
GET /
```

### Voting Operations
```
POST /arena/save-comparison
Body: {
  "question": str,
  "model_a": str,
  "answer_a": str,
  "model_b": str,
  "answer_b": str
}
Response: {"success": true, "comparison_id": "uuid"}

POST /arena/vote
Body: {
  "comparison_id": str,
  "vote": "A" | "B" | "tie" | "both_bad",
  "comment": str (optional)
}
Response: {"success": true}
```

### Data Retrieval
```
GET /arena/statistics
Response: {
  "total_comparisons": int,
  "voted": int,
  "unvoted": int,
  "votes_for_a": int,
  "votes_for_b": int,
  "votes_tie": int,
  "votes_both_bad": int,
  "win_rate_a": float,
  "win_rate_b": float,
  "tie_rate": float,
  "both_bad_rate": float,
  "models_seen": [str, ...]
}

GET /arena/comparisons
GET /arena/comparisons?subset=1
Response: {
  "total": int,
  "comparisons": [
    {
      "id": str,
      "question": str,
      "timestamp": str,
      "model_a": str,
      "answer_a": str,
      "model_b": str,
      "answer_b": str,
      "vote": str | null,
      "vote_timestamp": str | null,
      "subset_id": int
    },
    ...
  ]
}

GET /arena/comparison/{comparison_id}
Response: (single comparison object)
```

## 📊 Vote Persistenz

### JSONL Format Beispiel

```jsonl
{"id":"uuid-1","question":"Was ist 2+2?","timestamp":"2026-01-14T10:00:00","model_a":"gpt-4","answer_a":"2+2=4","model_b":"claude","answer_b":"4","vote":"B","vote_timestamp":"2026-01-14T10:05:00","subset_id":1}
{"id":"uuid-2","question":"Erkläre KI","timestamp":"2026-01-14T10:01:00","model_a":"gpt-4","answer_a":"KI ist...","model_b":"claude","answer_b":"Künstliche Intelligenz...","vote":"tie","vote_timestamp":"2026-01-14T10:10:00","subset_id":2}
```

### Speicherort & Volumen

- **Docker Path:** `/data/arena_votes.jsonl` (inside API container)
- **Volume:** `arena_data` (persists after container stop)
- **Host Mapping:** `./src/openwebui/data/arena_votes.jsonl` (wenn mounted)

### Append-Only Strategie

1. **Neue Comparison:** Wird sofort ins JSONL appended
2. **Vote:** Wird als neue Zeile appended (nicht überschrieben)
3. **Read:** Werden beim Load aggregiert (letzter Vote pro ID zählt)
4. **Backups:** Einfach Datei kopieren (snapshot zu beliebigem Zeitpunkt)

## 🔐 Sicherheit

### CORS
```env
CORS_ORIGINS=https://arena.ki-campus.org,https://chat.ki-campus.org
```

### API Key (Optional)
```python
# In .env
ARENA_API_KEY=<secure-random-key>

# Wird validiert in verify_arena_key()
# Required für POST /arena/vote in PRODUCTION
```

### TLS/SSL
- Automatisch via Certbot (Let's Encrypt)
- Nginx terminiert TLS
- Backends nur via localhost

### Rate Limiting
```nginx
# In nginx.conf.prod
limit_req_zone $binary_remote_addr zone=api_zone:10m rate=10r/s;
limit_req zone=api_zone burst=20 nodelay;
```

## ⚙️ Environment-Variablen

```env
# Core
ENVIRONMENT=PRODUCTION        # or LOCAL
DOMAIN_NAME=arena.ki-campus.org
POSTGRES_PASSWORD=<secure>

# API
ARENA_API_KEY=<generate>      # For vote endpoints
CORS_ORIGINS=*                # or specific domains

# Storage
JSONL_PATH=/data/arena_votes.jsonl

# Azure (Optional für LLM)
AZURE_OPENAI_URL=https://...
AZURE_OPENAI_API_KEY=...
QDRANT_URL=https://...
QDRANT_API_KEY=...

# Key Vault (Optional)
USE_KEY_VAULT=false
KEY_VAULT_NAME=kicwa-keyvault-lab
```

## 🚀 Deployment-Pfad

```
Development (LOCAL)
    ↓
    - ENVIRONMENT=LOCAL
    - Dev certificates
    - Mock data
    ↓
Staging (STAGING)
    ↓
    - Real Azure credentials
    - Real Qdrant
    - Testing with users
    ↓
Production (PRODUCTION)
    ↓
    - Let's Encrypt certificates
    - Key Vault secrets
    - Monitoring & alerts
    - Backups & recovery
```

## 📈 Skalierbarkeit

### Aktuell (single server)
- Max ~1000 votes/day
- Max ~10k comparisons
- Single JSONL file (< 10MB)

### Für 100k+ votes
1. Migrate JSONL → PostgreSQL
2. Add indexing on (comparison_id, subset_id)
3. Implement pagination in API
4. Add caching layer (Redis)
5. Horizontal scaling (multiple API instances)

## 🔧 Betrieb & Monitoring

### Health Checks
```bash
curl http://localhost:8001/health
curl http://localhost:8002/
```

### Logs
```bash
docker compose -f docker-compose.prod.yml logs -f arena-api
docker compose -f docker-compose.prod.yml logs -f arena-ui
docker compose -f docker-compose.prod.yml logs -f nginx
```

### Backup
```bash
cp src/openwebui/data/arena_votes.jsonl arena_votes.backup-$(date +%Y%m%d).jsonl
```

### Metriken (manuell)
```bash
curl http://localhost:8001/arena/statistics | python -m json.tool
```

## 📚 Weitere Dokumentation

- **[README.md](../README.md)** - Quick Start
- **[VOTING.md](../VOTING.md)** - Voting System Details
- **[DEPLOYMENT.md](../DEPLOYMENT.md)** - Production Deployment
