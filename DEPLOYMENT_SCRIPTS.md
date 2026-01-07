# Deployment Scripts Guide

Dieses Dokument erklärt die Verwendung der Deployment-Scripts für Production.

## Übersicht

Die Arena verfügt über folgende Automation Scripts:

| Script | Zweck | Häufigkeit |
|--------|-------|-----------|
| `init-ssl.sh` | Let's Encrypt SSL-Zertifikate | Einmalig |
| `setup-env.sh` | Environment-Konfiguration | Einmalig |
| `gen-secrets.sh` | Secret-Generierung | Bei Bedarf |
| `deploy.sh` | Docker Deployment & Management | Per Deployment |
| `backup.sh` | Daten-Sicherung | Täglich (cronjob) |
| `healthcheck.sh` | System-Überwachung | Stündlich (cronjob) |

## 1. deploy.sh - Deployment & Lifecycle Management

Verwaltet den kompletten Docker Deployment Lifecycle.

### Verwendung

```bash
# Vollständiges Deployment (build, start, health check)
./scripts/deploy.sh deploy

# Nur Images bauen
./scripts/deploy.sh build

# Services starten
./scripts/deploy.sh start

# Services stoppen
./scripts/deploy.sh stop

# Service-Status anzeigen
./scripts/deploy.sh status

# Logs ansehen
./scripts/deploy.sh logs                 # Alle
./scripts/deploy.sh logs arena-api       # Nur API

# Health Checks durchführen
./scripts/deploy.sh health

# Backup vor Deployment
./scripts/deploy.sh backup

# Backup wiederherstellen
./scripts/deploy.sh restore /var/backups/arena/arena_votes_20250107-120000.jsonl
```

### Was macht `deploy deploy`?

1. ✓ .env Validierung (required vars, ENVIRONMENT=PRODUCTION)
2. ✓ Pre-deployment Backup erstellen
3. ✓ Docker Images bauen (--no-cache)
4. ✓ Alte Container stoppen/entfernen
5. ✓ Neue Container starten
6. ✓ Health Checks durchführen (API, UI, Docker, Statistiken)
7. ✓ Status bericht anzeigen

### Logs

Alle Deploy-Logs werden in `/var/log/arena-deploy.log` gespeichert.

```bash
# Logs ansehen
tail -f /var/log/arena-deploy.log

# Letzte 50 Zeilen
tail -50 /var/log/arena-deploy.log

# Errors filtern
grep ERROR /var/log/arena-deploy.log
```

## 2. backup.sh - Daten-Sicherung

Erstellt tägliche Backups der Arena Votes.

### Verwendung

```bash
# Backup erstellen (lokal + optional S3)
./scripts/backup.sh backup

# Verfügbare Backups auflisten
./scripts/backup.sh list

# Backup Integrität überprüfen
./scripts/backup.sh verify /var/backups/arena/arena_votes_20250107-120000.jsonl

# Aus Backup wiederherstellen
./scripts/backup.sh restore /var/backups/arena/arena_votes_20250107-120000.jsonl
```

### Automatische Backups (Cronjob)

```bash
# Tägliches Backup um 2:00 Uhr
0 2 * * * /path/to/scripts/backup.sh backup >> /var/log/arena-backup.log 2>&1

# Wöchentliches Backup um Montag 3:00 Uhr
0 3 * * 1 RETENTION_DAYS=90 /path/to/scripts/backup.sh backup

# Backup Verifikation täglich um 3:00 Uhr (nach Backup)
5 3 * * * /path/to/scripts/backup.sh list >> /var/log/arena-backup-verify.log 2>&1
```

### Backup Directory Struktur

```
/var/backups/arena/
├── arena_votes_20250107-120000.jsonl    (aktives Backup)
├── arena_votes_20250106-120000.jsonl    (1 Tag alt)
└── arena_votes_20250105-120000.jsonl    (2 Tage alt)
```

Alte Backups werden automatisch nach 30 Tagen gelöscht (konfigurierbar via `RETENTION_DAYS`).

### S3 Offsite Backup (Optional)

```bash
# Mit S3 Backup
S3_BUCKET=my-backup-bucket S3_PREFIX=arena-prod ./scripts/backup.sh backup

# Als Cronjob
0 2 * * * S3_BUCKET=my-backup-bucket ./scripts/backup.sh backup

# Voraussetzungen:
# - AWS CLI installiert
# - AWS Credentials konfiguriert
# - S3 Bucket exists
# - IAM Permissions für s3:PutObject
```

### Backup Verifikation

```bash
# JSONL Integrität überprüfen
./scripts/backup.sh verify /var/backups/arena/arena_votes_20250107-120000.jsonl

# Backup-Größe überprüfen
ls -lh /var/backups/arena/

# Backup Inhalt preview
head -5 /var/backups/arena/arena_votes_20250107-120000.jsonl | python3 -m json.tool
```

## 3. healthcheck.sh - System Überwachung

Überprüft die Gesundheit aller Services.

### Verwendung

```bash
# Vollständige Health Checks
./scripts/healthcheck.sh all

# Einzelne Checks
./scripts/healthcheck.sh api          # Nur API
./scripts/healthcheck.sh ui           # Nur UI
./scripts/healthcheck.sh docker       # Docker Container
./scripts/healthcheck.sh disk         # Festplattenspeicher
./scripts/healthcheck.sh stats        # Arena Statistiken
```

### Was wird überprüft?

**API Health:**
- GET /health Endpunkt erreichbar
- HTTP 200 Response

**UI Health:**
- GET / Endpunkt erreichbar
- HTML Response

**Docker Containers:**
- fu-arena-api: running
- fu-arena-ui: running
- fu-arena-nginx: running
- fu-arena-postgres: running
- fu-arena-certbot: running (optional)

**Disk Usage:**
- /var/backups/arena Größe
- /data Volume Größe

**Arena Statistics:**
- Total comparisons
- Voted/unvoted counts
- Model performance

### Automatische Überwachung (Cronjob)

```bash
# Stündlich überprüfen
0 * * * * /path/to/scripts/healthcheck.sh all >> /var/log/arena-health.log 2>&1

# Mit Email Alerts
0 * * * * ALERT_EMAIL=admin@example.com /path/to/scripts/healthcheck.sh all

# Mit Slack Alerts
0 * * * * SLACK_WEBHOOK=https://hooks.slack.com/... /path/to/scripts/healthcheck.sh all
```

### Alerting

```bash
# Email Alerts
ALERT_EMAIL=admin@example.com ./scripts/healthcheck.sh all

# Slack Alerts
SLACK_WEBHOOK=https://hooks.slack.com/services/... ./scripts/healthcheck.sh all

# Beide kombiniert
ALERT_EMAIL=admin@example.com \
SLACK_WEBHOOK=https://hooks.slack.com/services/... \
./scripts/healthcheck.sh all
```

## Production Setup

### Cronjob Installation

```bash
# Alle Scripts als Cronjobs installieren
sudo crontab -e

# Hinzufügen:
0 2 * * * cd /home/ubuntu/FU_Chatbot_RD_Zitho && ./scripts/backup.sh backup >> /var/log/arena-backup.log 2>&1
0 * * * * cd /home/ubuntu/FU_Chatbot_RD_Zitho && ./scripts/healthcheck.sh all >> /var/log/arena-health.log 2>&1
0 6 * * 0 cd /home/ubuntu/FU_Chatbot_RD_Zitho && ./scripts/deploy.sh health >> /var/log/arena-weekly-check.log 2>&1
```

### Log Rotation

```bash
# /etc/logrotate.d/arena
/var/log/arena-*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        systemctl reload-or-restart rsyslog > /dev/null 2>&1 || true
    endscript
}

# Installation
sudo cp /path/to/logrotate-arena /etc/logrotate.d/arena
sudo logrotate -v /etc/logrotate.d/arena
```

### Überwachungs-Dashboard

Mit `healthcheck.sh stats` regelmäßig aufrufen für Monitoring:

```bash
# Stündlich Statistiken in Datei schreiben
0 * * * * cd /home/ubuntu/FU_Chatbot_RD_Zitho && \
  echo "$(date): $(./scripts/healthcheck.sh stats)" >> /var/log/arena-stats.log 2>&1
```

## Häufige Aufgaben

### Neues Deployment durchführen

```bash
# 1. Code aktualisieren
git pull origin feature/openwebui-arena

# 2. Dependencies überprüfen
./scripts/setup-env.sh --validate-only

# 3. Backup vor Deployment
./scripts/backup.sh backup

# 4. Deployment durchführen
./scripts/deploy.sh deploy

# 5. Logs überprüfen
./scripts/healthcheck.sh all
```

### Nach Fehler Recovery

```bash
# 1. Fehler überprüfen
./scripts/healthcheck.sh all
docker compose logs arena-api

# 2. Backup vor Recovery
./scripts/backup.sh backup

# 3. Zu letztem bekannten Zustand zurückkehren
./scripts/backup.sh list
./scripts/backup.sh restore /var/backups/arena/arena_votes_20250106-120000.jsonl

# 4. Services neustarten
./scripts/deploy.sh stop
./scripts/deploy.sh start
```

### Secrets rotieren

```bash
# 1. Neue Secrets generieren
./scripts/gen-secrets.sh --for postgres
./scripts/gen-secrets.sh --for arena

# 2. In Azure Key Vault aktualisieren (falls USE_KEY_VAULT=true)
az keyvault secret set \
  --vault-name kicwa-keyvault-prod \
  --name "POSTGRES-PASSWORD" \
  --value "$(openssl rand -hex 32)"

# 3. .env lokal aktualisieren (falls nicht mit Key Vault)
nano .env
# POSTGRES_PASSWORD=<new_value>
# ARENA_API_KEY=<new_value>

# 4. Deployment mit neuen Secrets durchführen
./scripts/deploy.sh deploy
```

### SSL Zertifikat erneuern

```bash
# Manual renewal (normalerweise automatisch)
docker compose -f docker-compose.prod.yml exec certbot certbot renew --verbose

# Oder neu initialisieren
./scripts/init-ssl.sh arena.ki-campus.org admin@ki-campus.org
```

## Troubleshooting

### Deploy schlägt fehl

```bash
# 1. Logs überprüfen
tail -50 /var/log/arena-deploy.log

# 2. Docker Logs überprüfen
docker compose -f docker-compose.prod.yml logs arena-api

# 3. .env Validierung
./scripts/setup-env.sh --validate-only

# 4. Disk Space überprüfen
df -h
./scripts/healthcheck.sh disk

# 5. Mit vollem Rebuild neu versuchen
./scripts/deploy.sh build
./scripts/deploy.sh start
```

### Backup schlägt fehl

```bash
# 1. Backup Log überprüfen
tail -50 /var/log/arena-backup.log

# 2. Volumes überprüfen
docker volume ls

# 3. Backup Directory Permissions
ls -la /var/backups/arena

# 4. Manuell Backup erstellen
docker run --rm \
  -v fu_chatbot_rd_zitho_arena_data:/data \
  -v /var/backups/arena:/bkp \
  alpine \
  cp /data/arena_votes.jsonl /bkp/manual_backup_$(date +%s).jsonl
```

### Health Check fehlgeschlagen

```bash
# 1. Einzelne Services überprüfen
./scripts/healthcheck.sh api
./scripts/healthcheck.sh ui
./scripts/healthcheck.sh docker

# 2. Container Logs
docker compose logs

# 3. Network Status
docker network ls
docker network inspect fu_chatbot_rd_zitho_arena_network

# 4. Services neustarten
./scripts/deploy.sh stop
./scripts/deploy.sh start
./scripts/healthcheck.sh all
```

## Sicherheits-Checklist

- [ ] .env Datei nicht in Git committet
- [ ] .env Permissions 600: `chmod 600 .env`
- [ ] Backups täglich durchgeführt
- [ ] Backups überprüft auf Integrität
- [ ] Health Checks laufen regelmäßig
- [ ] Logs überwacht auf Errors
- [ ] SSL Zertifikate auto-renewing
- [ ] Secrets in Azure Key Vault (empfohlen)
- [ ] Backup Retention Policy beachtet
- [ ] Disaster Recovery Plan getestet

## Weitere Ressourcen

- [DEPLOYMENT_ENV.md](./DEPLOYMENT_ENV.md) - Environment Setup
- [DEPLOYMENT_KEYVAULT.md](./DEPLOYMENT_KEYVAULT.md) - Key Vault Integration
- [DEPLOYMENT_SSL.md](./DEPLOYMENT_SSL.md) - SSL Setup
- [docker-compose.prod.yml](../docker-compose.prod.yml) - Docker Konfiguration
