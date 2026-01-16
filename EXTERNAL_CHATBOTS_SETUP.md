# External Chatbot Integration for Arena

This setup allows the Arena to compare two externally-hosted chatbot versions:
- **Original**: `scieneers/kic-web-assistant` (Port 9001)
- **Improved**: `KI-Campus/FU_Chatbot` (Port 9002)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Arena API (Port 8001)                      │
│          HTTPProxyAssistant (Proxy Layer)               │
└────────────┬─────────────────────────┬──────────────────┘
             │ HTTP /api/chat          │ HTTP /api/chat
             ▼                         ▼
┌────────────────────────┐  ┌──────────────────────────┐
│   chatbot-original     │  │   chatbot-improved       │
│   (Port 9001)          │  │   (Port 9002)            │
│   kic-web-assistant    │  │   FU_Chatbot             │
└────────────────────────┘  └──────────────────────────┘
```

## Prerequisites

1. **Azure CLI Authentication**:
   ```bash
   az login --tenant "c6ff58bc-993e-4bdb-8d10-6013e2cd361f"
   ```

2. **Repositories Cloned**:
   - Original: `/Users/browse/kic-web-assistant-original`
   - Improved: `/Users/browse/kic-chatbot-improved`

3. **Docker Desktop Running**

## Quick Start

### 1. Start External Chatbots

```bash
# Build and start both chatbot containers
cd /Users/browse/FU_Chatbot_RD_Zitho
docker compose -f docker-compose.chatbots.yml up -d

# Check health
curl http://localhost:9001/health  # Should return "OK"
curl http://localhost:9002/health  # Should return "OK"
```

### 2. Start Arena System

```bash
# Start Arena API (uses HTTP proxy to connect to chatbots)
docker compose -f docker-compose.prod.yml up -d arena-api arena-ui

# Check Arena health
curl http://localhost:8001/health
curl http://localhost:8002/  # Voting UI
```

### 3. Test Integration

```bash
# Test original chatbot
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kicampus-v1",
    "messages": [{"role": "user", "content": "Was ist Machine Learning?"}],
    "stream": false
  }'

# Test improved chatbot
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kicampus-v1-improved",
    "messages": [{"role": "user", "content": "Was ist Machine Learning?"}],
    "stream": false
  }'
```

## Configuration Files

### Docker Compose: `docker-compose.chatbots.yml`
- Runs both chatbot versions as separate containers
- Mounts Azure CLI credentials for Key Vault access
- Both use `kicwa-keyvault-lab` (not prod!)
- Includes Langfuse tracking for each version

### Model Registry: `config/models.yaml`
```yaml
models:
  kicampus-v1:
    source: "src.llm.http_proxy_assistant:HTTPProxyAssistant"
    params:
      api_base_url: "http://chatbot-original"  # Docker service name
      api_key: "arena-test-key"
      timeout: 60
      
  kicampus-v1-improved:
    source: "src.llm.http_proxy_assistant:HTTPProxyAssistant"
    params:
      api_base_url: "http://chatbot-improved"
      api_key: "arena-test-key"
      timeout: 60
```

### For Local Testing: `config/models.local.yaml`
Use `localhost:9001` and `localhost:9002` instead of Docker service names.

## HTTPProxyAssistant

Located in: `src/llm/http_proxy_assistant.py`

This proxy forwards Arena API requests to external chatbot APIs:
- Converts LlamaIndex `ChatMessage` to `/api/chat` format
- Handles authentication via `Api-Key` header
- Manages timeouts and error handling
- Compatible with both `chat()` and `chat_with_course()` methods

## Seeding Comparisons

Generate new comparisons with real chatbot responses:

```bash
cd /Users/browse/FU_Chatbot_RD_Zitho

# Seed from question file
python scripts/arena_seed_with_llm.py \
  --input data/fixed_questions_for_seeding.json \
  --api-url http://localhost:8001

# This will:
# 1. Call both chatbot APIs for each question
# 2. Store comparisons in src/openwebui/data/arena_votes.jsonl
# 3. Ready for voting in Arena UI
```

## Key Differences: Original vs Improved

| Aspect | Original (kic-web-assistant) | Improved (FU_Chatbot) |
|--------|------------------------------|----------------------|
| **Repository** | scieneers/kic-web-assistant | KI-Campus/FU_Chatbot |
| **Context Window** | 10 messages | 15 messages |
| **Dependencies** | Base Poetry setup | + langgraph, pymupdf, vosk |
| **Release Date** | 2024-01-01 | 2025-06-01 |
| **Port** | 9001 | 9002 |

## Troubleshooting

### Chatbots not accessible
```bash
# Check container logs
docker logs chatbot-original
docker logs chatbot-improved

# Verify Azure login
az account show

# Test direct API call
curl -H "Api-Key: arena-test-key" \
  http://localhost:9001/health
```

### Arena can't connect to chatbots
```bash
# Check if running on Docker network
docker network inspect fu_chatbot_rd_zitho_arena_chatbots

# Verify models.yaml uses correct URLs:
# - Docker: http://chatbot-original, http://chatbot-improved
# - Local: http://localhost:9001, http://localhost:9002
```

### Key Vault access denied
```bash
# Ensure using LAB vault (not PROD)
# Check environment variable in docker-compose.chatbots.yml:
KEY_VAULT_NAME: "kicwa-keyvault-lab"

# Re-authenticate
az login --tenant "c6ff58bc-993e-4bdb-8d10-6013e2cd361f"
```

## Ports Overview

| Service | Port | URL |
|---------|------|-----|
| **Chatbot Original** | 9001 | http://localhost:9001 |
| **Chatbot Improved** | 9002 | http://localhost:9002 |
| **Langfuse Original** | 3001 | http://localhost:3001 |
| **Langfuse Improved** | 3002 | http://localhost:3002 |
| **Arena API** | 8001 | http://localhost:8001 |
| **Arena UI** | 8002 | http://localhost:8002 |
| **Postgres (Chatbots)** | 5433 | localhost:5433 |

## Next Steps

1. ✅ Build and start both chatbot containers
2. ✅ Configure HTTPProxyAssistant in models.yaml
3. ⏳ Test end-to-end integration
4. ⏳ Seed new comparisons with real differences
5. ⏳ Run Arena voting with multiple users
6. ⏳ Analyze results and iterate

## Notes

- Both chatbots use **Azure Key Vault LAB** (not prod)
- Azure CLI credentials mounted read-only from `~/.azure`
- Langfuse instances track each chatbot separately
- All API calls authenticated with `arena-test-key`
- HTTPProxyAssistant caches sessions for performance
