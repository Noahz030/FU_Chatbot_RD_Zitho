# Arena Voting System - Production Deployment & Security Guide

## Overview

This document describes the security architecture and deployment checklist for the FU_Chatbot_RD_Zitho Arena Voting System.

---

## 🔐 Security Model

### Environment-Based Authentication

The system enforces **different security levels** based on the `ENVIRONMENT` variable:

| Environment | API Key Required | Rate Limiting | CAPTCHA | Use Case |
|---|---|---|---|---|
| **LOCAL** | ❌ No | ⚠️ Soft | ❌ No | Local development & testing |
| **STAGING** | ⚠️ Optional | ✅ Hard | ⚠️ Optional | Staging/QA environment |
| **PRODUCTION** | ✅ **Required** | ✅ Hard | ✅ **Required** | Live deployment |

### Critical: PRODUCTION Mode Enforcement

When `ENVIRONMENT=PRODUCTION`:
- ✅ All `/arena/*` endpoints require valid `X-Arena-Key` header
- ✅ All `/api/*` endpoints require valid `Api-Key` header
- ✅ CAPTCHA required on voting endpoints (when implemented)
- ✅ Rate limiting enforced (nginx + application-level)
- ✅ Encryption enabled for vote data at rest

**Failure to set `ENVIRONMENT=PRODUCTION` will expose endpoints without authentication.**

---

## 📋 Pre-Deployment Checklist

### 1. Generate Required Secrets

```bash
# Generate ARENA_API_KEY (for /arena/* endpoints)
python -c "import secrets; print('ARENA_API_KEY=' + secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY (for JSONL encryption)
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_hex(32))"

# Generate POSTGRES_PASSWORD
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"

# Generate REST_API_KEYS (can have multiple)
python -c "import secrets; print('REST_API_KEYS=[\"' + secrets.token_urlsafe(24) + '\", \"' + secrets.token_urlsafe(24) + '\"]')"
```

### 2. Set Up reCAPTCHA v3 (Bot Protection)

1. Go to [Google reCAPTCHA Console](https://www.google.com/recaptcha/admin)
2. Create a new site:
   - **Display name**: Arena Voting System
   - **reCAPTCHA type**: reCAPTCHA v3
   - **Domains**: `arena.ki-campus.org`, `ki-campus.org`
3. Copy `Site Key` and `Secret Key` to `.env.production`:
   ```
   RECAPTCHA_SITE_KEY=<your-site-key>
   RECAPTCHA_SECRET_KEY=<your-secret-key>
   ```

### 3. Update `.env.production`

Edit `.env.production` and set **all CRITICAL fields**:

```bash
# Critical security settings
ENVIRONMENT=PRODUCTION
USE_KEY_VAULT=true
ARENA_API_KEY=<generated-above>
ENCRYPTION_KEY=<generated-above>
POSTGRES_PASSWORD=<generated-above>
REST_API_KEYS=<generated-above>
RECAPTCHA_SECRET_KEY=<from-google>
RECAPTCHA_SITE_KEY=<from-google>

# Deployment settings
DOMAIN_NAME=arena.ki-campus.org
CORS_ORIGINS=https://arena.ki-campus.org,https://ki-campus.org

# Azure Key Vault (if using)
KEY_VAULT_NAME=kicwa-keyvault-prod
USE_KEY_VAULT=true
```

**⚠️ IMPORTANT**: Never commit `.env.production` with real secrets. It's in `.gitignore`.

### 4. Verify Azure Key Vault (If Enabled)

If `USE_KEY_VAULT=true`, ensure all secrets are stored in Azure Key Vault with proper names (hyphens instead of underscores):

```
ARENA-API-KEY
ENCRYPTION-KEY
POSTGRES-PASSWORD
RECAPTCHA-SECRET-KEY
REST-API-KEYS
```

VM must have **Managed Identity** with Key Vault read permissions.

### 5. Deploy with Docker Compose

```bash
# Build and start services
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# Verify services are healthy
docker compose -f docker-compose.prod.yml ps

# Check logs for startup errors
docker compose -f docker-compose.prod.yml logs arena-api
docker compose -f docker-compose.prod.yml logs arena-ui
```

### 6. Smoke Tests

```bash
# Test without API key (should fail in PRODUCTION)
curl -X POST http://localhost:8001/arena/vote \
  -H "Content-Type: application/json" \
  -d '{"comparison_id": "test", "vote": "A"}'
# Expected: 401 Unauthorized

# Test with API key (should succeed)
ARENA_KEY=$(grep ARENA_API_KEY .env.production | cut -d= -f2)
curl -X GET http://localhost:8001/arena/assign-subset \
  -H "X-Arena-Key: $ARENA_KEY"
# Expected: 200 OK with subset assignment

# Test UI loads
curl http://localhost:8002/
# Expected: 200 OK with HTML page
```

---

## 🔑 API Key Management

### Arena API Key (`X-Arena-Key` Header)

Used for all `/arena/*` endpoints (voting, generation, statistics).

```bash
# Single key setup
ARENA_API_KEY=<your-secret-key>

# Client usage
curl -X POST https://arena.ki-campus.org:8001/arena/vote \
  -H "X-Arena-Key: $ARENA_KEY" \
  -H "Content-Type: application/json" \
  -d '{"comparison_id": "123", "vote": "A"}'
```

**Rotation:**
- Change key in `.env.production`
- Restart services: `docker compose -f docker-compose.prod.yml restart arena-api`
- Update clients with new key

### REST API Keys (`Api-Key` Header)

Used for `/api/chat` and `/api/feedback` endpoints.

```bash
# Multiple keys setup (JSON list)
REST_API_KEYS=["key1", "key2", "key3"]

# Client usage
curl -X POST https://arena.ki-campus.org:8001/api/chat \
  -H "Api-Key: key1" \
  -H "Content-Type: application/json" \
  -d '{"question": "..."}'
```

---

## 🛡️ Security Features

### 1. Authentication
- ✅ API Key validation on all protected endpoints
- ✅ Environment-based enforcement (LOCAL = no auth, PRODUCTION = required)

### 2. Encryption
- ✅ Vote data encrypted at rest (AES-256-GCM in JSONL)
- ✅ HTTPS enforced (nginx redirect + TLS)

### 3. Rate Limiting
- ✅ Nginx level: Global + per-endpoint limits
- ✅ Application level: Token bucket on `/arena/generate` (1 req/5s per session)

### 4. Bot Protection (Planned)
- ⏳ reCAPTCHA v3 on voting endpoints
- ⏳ Honeypot fields in voting form
- ⏳ Session-based vote cooldown

### 5. Session Management
- ✅ Session IDs validated against voted comparisons
- ✅ Subset assignment prevents multiple voting per user

### 6. Audit Logging
- ⏳ All votes logged with session ID + timestamp
- ⏳ Failed API key attempts logged
- ⏳ Audit trail maintained in separate JSONL file

---

## 📊 Monitoring & Alerts

### Key Metrics to Monitor

```bash
# Check API key failures
docker compose -f docker-compose.prod.yml logs arena-api | grep "Invalid.*API"

# Monitor vote submissions
docker compose -f docker-compose.prod.yml logs arena-api | grep "arena.vote"

# Check rate limiting hits
docker compose -f docker-compose.prod.yml logs nginx | grep "429\|limit"
```

### Alert Triggers (Recommended)

1. **High Auth Failures**: >5 failed API key attempts in 5 minutes
2. **High Error Rate**: Error rate on `/arena/*` endpoints >5%
3. **Generation Spike**: >20 requests to `/arena/generate` in 1 minute
4. **Vote Anomalies**: >50 votes from same session in <1 hour

---

## 🔄 Maintenance & Rotation

### Quarterly Security Tasks

- [ ] Rotate ARENA_API_KEY
- [ ] Rotate REST_API_KEYS
- [ ] Rotate ENCRYPTION_KEY (requires data migration)
- [ ] Review audit logs for anomalies
- [ ] Update reCAPTCHA keys if needed

### Log Cleanup

```bash
# Rotate audit logs (keep 90 days)
find src/openwebui/data -name "audit.log*" -mtime +90 -delete

# Archive vote data
tar czf arena_votes_archive_$(date +%Y%m%d).tar.gz src/openwebui/data/arena_votes.jsonl
```

---

## 🚨 Troubleshooting

### Arena API Returns 401 on All Requests

**Cause**: Missing or incorrect `X-Arena-Key` header in PRODUCTION mode.

**Fix**:
```bash
# Check ARENA_API_KEY is set
grep ARENA_API_KEY .env.production

# Check ENVIRONMENT is PRODUCTION
grep "^ENVIRONMENT=" .env.production

# Restart API
docker compose -f docker-compose.prod.yml restart arena-api
```

### Votes Not Being Recorded

**Cause**: Encryption key mismatch or JSONL file permissions.

**Fix**:
```bash
# Check ENCRYPTION_KEY matches between app and .env
ls -la src/openwebui/data/

# Check file permissions (should be readable by container)
docker compose -f docker-compose.prod.yml exec arena-api cat /app/src/openwebui/data/arena_votes.jsonl
```

### High Error Rate on `/arena/generate`

**Cause**: Rate limiting or insufficient LLM quota.

**Fix**:
```bash
# Check rate limit headers
curl -v https://arena.ki-campus.org/arena/generate -H "X-Arena-Key: $KEY" 2>&1 | grep -i "rate\|limit"

# Check LLM API quota
grep "Azure OpenAI" docker compose -f docker-compose.prod.yml logs arena-api
```

---

## 📞 Support & Escalation

For security incidents:
1. Check `/app/src/openwebui/data/audit.log` for suspicious activity
2. Review `ARENA_API_KEY` usage logs
3. If key compromised: Rotate immediately, check docker-compose logs for unauthorized access
4. Contact infrastructure team if Data breach suspected

---

## Links & References

- [Azure Key Vault Setup](https://learn.microsoft.com/en-us/azure/key-vault/)
- [reCAPTCHA v3 Documentation](https://developers.google.com/recaptcha/docs/v3)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
