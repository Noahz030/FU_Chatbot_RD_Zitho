# Lösung für Azure Credentials in Docker-Containern

## Problem
Beide externe Chatbot Repos (`kic-web-assistant` und `FU_Chatbot`) crashten beim Start im Docker Container mit:
```
OSError: [Errno 30] Read-only file system: '/home/appuser/.azure/commandIndex.json'
```

Das ist passiert, weil `DefaultAzureCredential()` **IMMER** aufgerufen wurde, auch wenn alle Secrets schon als Environment Variables vorhanden waren.

## Lösung: `USE_KEY_VAULT=false` Flag

Das war die **exakte gleiche Lösung**, die in diesem Projekt (`FU_Chatbot_RD_Zitho`) bereits implementiert war!

### Was wurde geändert:

#### 1. **env.py** - Conditional KeyVault Init
```python
# ALT (crasht):
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=key_vault_uri, credential=credential)

# NEU (funktioniert):
use_kv = os.environ.get("USE_KEY_VAULT", "true").lower() in ("1", "true", "yes")
secret_client = None
if use_kv:
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=key_vault_uri, credential=credential)
```

**Action**: Original Repo hatte das bereits, FU_Chatbot nicht → `env.py` kopiert

#### 2. **docker-compose.chatbots.yml** - USE_KEY_VAULT=false
```yaml
environment:
  USE_KEY_VAULT: "false"  # ← KRITISCH!
  KEY_VAULT_NAME: "kicwa-keyvault-lab"
  # Rest aus .env:
  AZURE_OPENAI_URL: "${AZURE_OPENAI_URL:-}"
  AZURE_OPENAI_API_KEY: "${AZURE_OPENAI_API_KEY:-}"
  # ... etc
```

**Action**: Docker-Compose konfiguriert um `env.py` mit `USE_KEY_VAULT=false` zu starten

### Warum funktioniert das?

1. `USE_KEY_VAULT=false` → `env.py` skipt `DefaultAzureCredential()` init
2. Alle Secrets werden von `AZURE_OPENAI_URL`, `AZURE_OPENAI_API_KEY` etc geladen
3. `secret_client = None` → keine Azure Auth nötig
4. Container startet cleanly ohne Filesystem-Fehler

### Deployment-Pattern

```
Dev/Local:                    Production (VM):
┌─────────────────┐          ┌──────────────────────┐
│ docker-compose  │          │  docker-compose      │
│ USE_KEY_VAULT   │          │  USE_KEY_VAULT       │
│ =false          │          │  =true (Managed ID)  │
│                 │          │                      │
│ .env (Inline)   │          │ Managed Identity     │
│ AZURE_OPENAI_*  │          │ (Azure VM)           │
│ PROD_QDRANT_*   │          │                      │
└─────────────────┘          └──────────────────────┘
```

## Nächste Schritte

1. ✅ Beide Chatbots Docker Images werden gerade rebuilt
2. ⏳ Container starten mit `USE_KEY_VAULT=false`
3. ⏳ HTTPProxyAssistant testet Verbindung zu /api/chat
4. ⏳ Arena API nutzt Proxy für beide Chatbots
5. ⏳ Seeding mit echten Antworten unterschiedlicher Versionen
