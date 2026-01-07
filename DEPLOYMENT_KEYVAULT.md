# Azure Key Vault Integration für Secrets Management

Dieses Dokument erklärt, wie man Azure Key Vault in der Production-Umgebung zur sicheren Verwaltung von Secrets aktiviert.

## Warum Azure Key Vault?

- **Zentralisierte Secrets-Verwaltung**: Alle Passwörter und API-Keys an einem sicheren Ort
- **Managed Identity**: Keine Passwörter/Keys in der .env Datei nötig
- **Audit Logging**: Alle Zugriffe werden geloggt
- **Rotation Support**: Automatische und manuelle Key-Rotation möglich
- **RBAC**: Granulare Zugriffskontrolle

## Architektur

```
VM mit Azure Managed Identity
    ↓
Docker Container (arena-api)
    ↓
Code lädt ENVIRONMENT=PRODUCTION
    ↓
env.py: USE_KEY_VAULT=true
    ↓
Azure SDK authentifiziert mit Managed Identity
    ↓
Azure Key Vault liest Secrets
    ↓
LLMs.py nutzt Secrets (API Keys, Passwords, etc.)
```

## Schritt-für-Schritt Setup

### 1. Azure CLI installieren (auf der VM)

```bash
# Ubuntu/Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Oder via apt
sudo apt-get update
sudo apt-get install -y azure-cli
```

### 2. Key Vault erstellen (in Azure Portal oder CLI)

```bash
# Login
az login

# Resource Group
RESOURCE_GROUP="fu-chatbot-rg"
LOCATION="westeurope"
az group create --name $RESOURCE_GROUP --location $LOCATION

# Key Vault erstellen
KEYVAULT_NAME="kicwa-keyvault-prod"
az keyvault create \
  --resource-group $RESOURCE_GROUP \
  --name $KEYVAULT_NAME \
  --location $LOCATION \
  --enable-purge-protection true
```

### 3. Managed Identity auf VM aktivieren

```bash
# VM-ID abrufen
VM_ID=$(az vm show --resource-group $RESOURCE_GROUP --name fu-arena-vm --query id -o tsv)

# Managed Identity erstellen
IDENTITY_NAME="fu-arena-identity"
az identity create \
  --resource-group $RESOURCE_GROUP \
  --name $IDENTITY_NAME

# Identity zur VM hinzufügen
az vm identity assign \
  --resource-group $RESOURCE_GROUP \
  --name fu-arena-vm \
  --identities "/subscriptions/{subscription-id}/resourcegroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/$IDENTITY_NAME"

# Principal ID abrufen
PRINCIPAL_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name $IDENTITY_NAME \
  --query principalId -o tsv)
```

### 4. Key Vault Zugriff für Managed Identity konfigurieren

```bash
# Get Secret permission
az keyvault set-policy \
  --name $KEYVAULT_NAME \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list

# Cert permission (optional, für SSL-Zertifikate)
az keyvault set-policy \
  --name $KEYVAULT_NAME \
  --object-id $PRINCIPAL_ID \
  --certificate-permissions get list
```

### 5. Secrets in Key Vault speichern

```bash
# Azure OpenAI Credentials
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "AZURE-OPENAI-API-KEY" \
  --value "sk-..."

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "AZURE-OPENAI-URL" \
  --value "https://your-resource.openai.azure.com/"

# Qdrant Credentials
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "PROD-QDRANT-API-KEY" \
  --value "your_qdrant_key"

# PostgreSQL Password
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "POSTGRES-PASSWORD" \
  --value "your_secure_password"

# Arena API Key
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "ARENA-API-KEY" \
  --value "$(openssl rand -hex 32)"

# REST API Keys
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "REST-API-KEYS" \
  --value "key1,key2,key3"
```

### 6. .env für Key Vault konfigurieren

```bash
# .env auf der VM
ENVIRONMENT=PRODUCTION
USE_KEY_VAULT=true
KEY_VAULT_NAME=kicwa-keyvault-prod
DOMAIN_NAME=arena.ki-campus.org
CORS_ORIGINS=https://arena.ki-campus.org

# Hinweis: Andere Secrets brauchen NICHT in .env zu sein!
# Sie werden automatisch aus Key Vault geladen
```

### 7. Docker Container mit Managed Identity starten

```bash
# Docker compose up mit neuer .env
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## Wie es funktioniert (technisch)

### env.py Lazy Loading

```python
from src.env import env

class Config:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "LOCAL")
        self.use_key_vault = os.getenv("USE_KEY_VAULT", "false").lower() == "true"
        
        if self.use_key_vault:
            # Azure SDK lädt Secrets automatisch mit Managed Identity
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            credential = DefaultAzureCredential()  # Nutzt Managed Identity!
            vault_url = f"https://{os.getenv('KEY_VAULT_NAME')}.vault.azure.net/"
            client = SecretClient(vault_url=vault_url, credential=credential)
            
            # Secrets laden
            self.azure_openai_api_key = client.get_secret("AZURE-OPENAI-API-KEY").value
            self.prod_qdrant_api_key = client.get_secret("PROD-QDRANT-API-KEY").value
            # ... weitere Secrets
        else:
            # Development: Aus .env laden
            self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            self.prod_qdrant_api_key = os.getenv("PROD_QDRANT_API_KEY")
```

### LLMs.py Nutzung

```python
from src.env import env

def get_embedder(self) -> AzureOpenAIEmbedding:
    # env.azure_openai_api_key kommt aus Key Vault oder .env
    embedder = AzureOpenAIEmbedding(
        api_key=env.azure_openai_api_key,
        azure_endpoint=env.azure_openai_url,
        ...
    )
    return embedder
```

## Security Best Practices

### ✅ Was ihr tun solltet

1. **Managed Identity nutzen** (nicht Secret/Password)
   ```bash
   # RICHTIG
   USE_KEY_VAULT=true
   KEY_VAULT_NAME=kicwa-keyvault-prod
   
   # FALSCH
   AZURE_KEYVAULT_PASSWORD=xxx
   ```

2. **Purge Protection aktivieren**
   ```bash
   az keyvault create --enable-purge-protection true
   ```

3. **Soft Delete aktivieren** (automatisch in neueren Vaults)
   ```bash
   az keyvault update --name $KEYVAULT_NAME --enable-soft-delete true
   ```

4. **Firewall konfigurieren**
   ```bash
   # Nur VNet-Zugriff erlauben
   az keyvault update \
     --name $KEYVAULT_NAME \
     --default-action Deny \
     --bypass AzureServices
   ```

5. **RBAC korrekt setzen**
   ```bash
   # Nur minimale Permissions
   az keyvault set-policy \
     --name $KEYVAULT_NAME \
     --object-id $PRINCIPAL_ID \
     --secret-permissions get list  # Nur get und list!
   ```

### ❌ Was ihr NICHT tun solltet

1. **Keys in .env speichern** (wenn Key Vault aktiv ist)
2. **Admin-Zugriff für Container-Identity geben**
3. **Secrets in Logs committen**
4. **Purge Protection deaktivieren** (Accidental deletion Risk)

## Debugging

### Key Vault Zugriff testen

```bash
# Innerhalb des Containers
python3 << 'EOF'
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

try:
    credential = DefaultAzureCredential()
    vault_url = f"https://{os.getenv('KEY_VAULT_NAME')}.vault.azure.net/"
    client = SecretClient(vault_url=vault_url, credential=credential)
    
    # Test secret abrufen
    secret = client.get_secret("AZURE-OPENAI-API-KEY")
    print(f"✓ Key Vault connection successful!")
    print(f"  Secret name: {secret.name}")
    print(f"  Secret value length: {len(secret.value)} chars")
except Exception as e:
    print(f"✗ Key Vault connection failed:")
    print(f"  {e}")
EOF
```

### Logs überprüfen

```bash
# Container logs
docker compose -f docker-compose.prod.yml logs arena-api

# Azure Audit Log
az monitor activity-log list \
  --resource-group $RESOURCE_GROUP \
  --max-events 50
```

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| `CredentialUnavailableError` | Managed Identity nicht konfiguriert | `az vm identity assign` ausführen |
| `AuthorizationFailed` | Keine Permissions auf Vault | RBAC Policy setzen |
| `SecretNotFound` | Secret existiert nicht | Secret Namen überprüfen |
| `RequestLimitExceeded` | Zu viele Requests | Client-Caching nutzen |

## Monitoring

### Key Vault Audit Log

```bash
# Alle Secret Zugriffe anzeigen
az monitor activity-log list \
  --resource-group $RESOURCE_GROUP \
  --query "[?resourceId=='$KEYVAULT_ID' && eventName.value=='Microsoft.KeyVault/vaults/secrets/get']" \
  --output table
```

### Diagnostics enablen

```bash
# Log Analytics konfigurieren
az keyvault diagnostic-settings create \
  --name kv-diagnostics \
  --vault-name $KEYVAULT_NAME \
  --workspace-resource-id $WORKSPACE_ID \
  --logs '[{"category":"AuditEvent","enabled":true}]'
```

## Weitere Ressourcen

- [Azure Key Vault Dokumentation](https://learn.microsoft.com/en-us/azure/key-vault/)
- [Azure Managed Identity](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
- [Azure SDK für Python](https://learn.microsoft.com/en-us/python/azure/)
- [Keyvault Python SDK](https://learn.microsoft.com/en-us/python/api/azure-keyvault-secrets/)
