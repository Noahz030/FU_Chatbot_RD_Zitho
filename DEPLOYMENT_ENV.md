# Environment Configuration Setup Guide

Dieser Guide erklärt, wie man die Arena-Umgebung für Production konfiguriert.

## Übersicht

Die Konfiguration besteht aus drei Dateien:

1. **`.env.example`** - Development Template (mit allen möglichen Optionen)
2. **`.env.prod.example`** - Production Template (sicherheitsoptimiert)
3. **`.env`** - Deine echte Konfiguration (niemals committen!)

## Zwei Wege zur Konfiguration

### Way 1: Automatische Setup (empfohlen)

```bash
# Auf der VM:
./scripts/setup-env.sh

# Das Skript wird dich interaktiv durch alle Schritte führen:
# - Fragt nach Domain Name
# - Generiert sichere Passwords automatisch
# - Validiert alle erforderlichen Variablen
# - Erklärt die nächsten Schritte
```

### Way 2: Manuelle Konfiguration

```bash
# Template kopieren
cp .env.prod.example .env

# Mit Texteditor öffnen und ausfüllen
nano .env
# oder
vim .env

# Sicherstellen, dass Datei sicher ist
chmod 600 .env
```

## Erforderliche Variablen (mussen gefüllt sein)

### 1. Deployment & Infrastructure

```env
ENVIRONMENT=PRODUCTION              # Muss PRODUCTION sein
DOMAIN_NAME=arena.ki-campus.org     # Muss mit SSL-Cert match
DEBUG_MODE=false                    # Immer false in Production
```

### 2. Security & Authentication

```env
# PostgreSQL Password (mindestens 32 Zeichen)
POSTGRES_PASSWORD=your_secure_password_here

# Arena API Key (für /arena/* Endpoints)
ARENA_API_KEY=your_secure_api_key_here

# REST API Keys (komma-separiert)
REST_API_KEYS=key1,key2,key3

# CORS Origins (komma-separiert, NIEMALS "*" in Production!)
CORS_ORIGINS=https://arena.ki-campus.org
```

### 3. Azure OpenAI (erforderlich für LLM)

```env
AZURE_OPENAI_URL=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=sk-...
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDER_DEPLOYMENT=text-embedding-3-large
```

### 4. Qdrant Vector Database (erforderlich für RAG)

```env
PROD_QDRANT_URL=https://your-qdrant-instance.cloud.qdrant.io
PROD_QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=web_assistant
```

## Sichere Secrets generieren

### Verwendung des Setup-Skripts:

```bash
./scripts/setup-env.sh --generate-secrets
# Das Skript generiert automatisch starke Passwords
```

### Manuell mit OpenSSL:

```bash
# 32-Zeichen (16 Bytes Hex) Secret generieren
openssl rand -hex 16
# Beispiel: 7d8f4a2c9e1b5c3f8a2b4d6e8f0a1c3d

# 64-Zeichen (32 Bytes Hex) Secret
openssl rand -hex 32
# Beispiel: 5e8f3a1c9b7d4f2a8e6c1b3d5f7a9c0e2f4b6d8a0c2e4f6a8b0d2f4e6a8c0e
```

### Sichere Passwords generieren:

```bash
# Alphanumerisch mit Sonderzeichen
openssl rand -base64 32

# Nur alphanumerisch
openssl rand -base64 32 | tr -d '/' | head -c 32

# Mit Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Optional: Azure Key Vault

In Production wird empfohlen, Secrets in Azure Key Vault zu speichern statt in .env:

```env
USE_KEY_VAULT=true
KEY_VAULT_NAME=kicwa-keyvault-prod
```

Mit Key Vault brauchst du keine Secrets in der .env zu haben - sie werden automatisch über Azure Managed Identity geladen.

Siehe [DEPLOYMENT_KEYVAULT.md](./DEPLOYMENT_KEYVAULT.md) für die vollständige Anleitung.

## Optional: Langfuse Monitoring

```env
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk_...
LANGFUSE_SECRET_KEY=sk_...
```

## Optional: Drupal Integration

```env
DRUPAL_URL=https://ki-campus.org
DRUPAL_CLIENT_ID=your_client_id
DRUPAL_CLIENT_SECRET=your_client_secret
```

## Schritt-für-Schritt auf der VM

### 1. Repository klonen

```bash
git clone https://github.com/Noahz030/FU_Chatbot_RD_Zitho.git
cd FU_Chatbot_RD_Zitho
git checkout feature/openwebui-arena
```

### 2. Umgebung konfigurieren

```bash
# Automatisch (empfohlen)
./scripts/setup-env.sh

# Oder manuell
cp .env.prod.example .env
nano .env
chmod 600 .env
```

### 3. Validierung (optional)

```bash
# .env überprüfen
./scripts/setup-env.sh --validate-only

# Oder manuell
echo "ENVIRONMENT: $(grep ENVIRONMENT .env)"
echo "DOMAIN_NAME: $(grep DOMAIN_NAME .env)"
echo "POSTGRES_PASSWORD: $(grep POSTGRES_PASSWORD .env | cut -d= -f2 | head -c 10)..."
```

### 4. SSL-Zertifikate initialisieren

```bash
sudo ./scripts/init-ssl.sh arena.ki-campus.org admin@ki-campus.org
```

### 5. Docker starten

```bash
docker compose -f docker-compose.prod.yml up -d

# Health prüfen
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8001/health
```

## Security Checkliste

Vor dem Deployment überprüfen:

- [ ] `ENVIRONMENT=PRODUCTION` (nicht STAGING/LOCAL)
- [ ] `DEBUG_MODE=false`
- [ ] `DOMAIN_NAME` match DNS A-Record und SSL-Cert
- [ ] `POSTGRES_PASSWORD` ist mindestens 32 Zeichen
- [ ] `ARENA_API_KEY` ist mindestens 32 Zeichen
- [ ] `REST_API_KEYS` sind einzigartig und stark
- [ ] `CORS_ORIGINS` restricted auf echte Domains (niemals `*`)
- [ ] `AZURE_OPENAI_API_KEY` und `PROD_QDRANT_API_KEY` nicht in Git
- [ ] `.env` file ist in `.gitignore`
- [ ] `.env` permissions sind 600: `chmod 600 .env`
- [ ] Alle Secrets über Key Vault verwaltet (empfohlen)

## Debugging

### .env validieren

```bash
# Syntax überprüfen
cat .env | grep -v '^#' | grep -v '^$' | head -20

# Für bestimmte Variablen überprüfen
grep POSTGRES_PASSWORD .env
grep ARENA_API_KEY .env
grep USE_KEY_VAULT .env
```

### Umgebungsvariablen in Container überprüfen

```bash
# In Container gehen
docker compose -f docker-compose.prod.yml exec arena-api /bin/sh

# Variablen überprüfen
echo $ENVIRONMENT
echo $DOMAIN_NAME
echo $AZURE_OPENAI_URL
```

### Log überprüfen bei Fehlern

```bash
# Container Logs ansehen
docker compose -f docker-compose.prod.yml logs arena-api

# Nur Fehler
docker compose logs --tail 50 | grep -i error
```

## Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| `ModuleNotFoundError: No module named 'src'` | Python path falsch | `docker compose` aus Repo-Root ausführen |
| `Connection refused` auf Port 8001 | API nicht gestartet | `docker compose logs arena-api` überprüfen |
| `CORS error` im Browser | CORS_ORIGINS zu restriktiv | Check `CORS_ORIGINS=https://your-domain.com` |
| `Key Vault authentication failed` | Managed Identity nicht konfiguriert | Siehe DEPLOYMENT_KEYVAULT.md |
| `SSL certificate not found` | init-ssl.sh nicht ausgeführt | `./scripts/init-ssl.sh` ausführen |

## Best Practices

### 1. Separiere Development und Production

```bash
# Development
.env              # Lokale Konfiguration (git-ignored)
.env.example      # Template für Development

# Production
.env.prod.example # Template für Production
.env              # Echte Secrets (niemals committen!)
```

### 2. Nutze Azure Key Vault für Secrets

```env
USE_KEY_VAULT=true
KEY_VAULT_NAME=kicwa-keyvault-prod

# Dann brauchst du keine Secrets in .env!
# Sie werden automatisch über Managed Identity geladen
```

### 3. Rotiere Secrets regelmäßig

```bash
# Jährlich oder bei Sicherheitsbedenken
openssl rand -hex 32  # Neuen Secret generieren
az keyvault secret set --vault-name $KEYVAULT_NAME --name "POSTGRES-PASSWORD" --value "new_password"
```

### 4. Secure .env Datei

```bash
# Nur Owner darf lesen/schreiben
chmod 600 .env

# In .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# Nicht per SCP übertragen (unverschlüsselt)
# Stattdessen SSH nutzen oder in Key Vault speichern
```

## Weitere Ressourcen

- [.env.prod.example](../.env.prod.example) - Production Template
- [DEPLOYMENT_KEYVAULT.md](./DEPLOYMENT_KEYVAULT.md) - Key Vault Setup
- [DEPLOYMENT_SSL.md](./DEPLOYMENT_SSL.md) - SSL Certificate Setup
- [scripts/setup-env.sh](../scripts/setup-env.sh) - Automatisches Setup
- [scripts/init-ssl.sh](../scripts/init-ssl.sh) - SSL Initialisierung
