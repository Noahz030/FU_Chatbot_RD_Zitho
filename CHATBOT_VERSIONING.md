# Chatbot Versioning for Arena

## Problem Statement

Die Arena ermöglicht es, verschiedene Chatbot-Versionen zu vergleichen. Derzeit sind 2 Versionen hardcodiert:
- `kicampus-original` - Basis-Version (10-message history)
- `kicampus-improved` - Verbesserte Version (15-message history)

Wenn das original Repository neue Versionen entwickelt, brauchen wir ein flexibles System, um diese zu integrieren **ohne Code-Änderungen** an der Arena selbst.

## Solution: Configuration-based Model Registry

### 1. Model Registry File

**Datei:** `config/models.yaml`

```yaml
models:
  kicampus-v1:
    name: "KI-Campus (Original)"
    description: "Original chatbot with 10-message context"
    enabled: true
    params:
      context_window: 10
      model_enum: "gpt4"
    source: "src.llm.assistant:KICampusAssistant"
    release_date: "2025-01-01"
    
  kicampus-v1-improved:
    name: "KI-Campus (Improved)"
    description: "Enhanced chatbot with 15-message context"
    enabled: true
    params:
      context_window: 15
      model_enum: "gpt4"
    source: "src.llm.assistant_improved:KICampusAssistantImproved"
    release_date: "2025-06-01"
    
  kicampus-v2:
    name: "KI-Campus v2.0"
    description: "New version from upstream repo (Jan 2026)"
    enabled: false  # Beispiel: noch nicht aktiviert
    params:
      context_window: 20
      model_enum: "gpt4"
    source: "src.llm.assistant_v2:KICampusAssistantV2"
    release_date: "2026-01-09"
    
arena:
  enabled_models:
    - "kicampus-v1"
    - "kicampus-v1-improved"
    # - "kicampus-v2"  # Uncomment zum Testen aktivieren
```

### 2. Model Factory Pattern

**Datei:** `src/llm/model_registry.py` (NEU)

```python
from dataclasses import dataclass
from typing import Type, Optional, Any
import yaml
from pathlib import Path

@dataclass
class ModelConfig:
    """Model configuration from registry"""
    name: str
    description: str
    enabled: bool
    params: dict[str, Any]
    source: str
    release_date: str

class ModelRegistry:
    """Load and manage chatbot versions from configuration"""
    
    def __init__(self, config_file: str = "config/models.yaml"):
        self.config_path = Path(config_file)
        self.models: dict[str, ModelConfig] = {}
        self.load_config()
    
    def load_config(self):
        """Load model registry from YAML"""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        for model_id, model_data in config['models'].items():
            self.models[model_id] = ModelConfig(**model_data)
    
    def get_model_class(self, model_id: str) -> Type:
        """Dynamically import assistant class by model ID"""
        model = self.models[model_id]
        module_path, class_name = model.source.rsplit(':', 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    
    def get_enabled_models(self) -> list[str]:
        """Get list of enabled model IDs"""
        config = yaml.safe_load(open(self.config_path))
        return config['arena']['enabled_models']
    
    def create_assistant(self, model_id: str, **kwargs):
        """Factory method to create assistant instance"""
        if model_id not in self.models:
            raise ValueError(f"Unknown model: {model_id}")
        
        model_config = self.models[model_id]
        if not model_config.enabled:
            raise ValueError(f"Model disabled: {model_id}")
        
        assistant_class = self.get_model_class(model_id)
        
        # Pass version-specific params to assistant
        params = {**model_config.params, **kwargs}
        return assistant_class(**params)
```

### 3. Updated Arena API Integration

**Datei:** `src/openwebui/openwebui_api_llm.py` (MODIFIED)

```python
from src.llm.model_registry import ModelRegistry

# Initialize registry once at startup
_registry = None
_assistants_cache: dict[str, Any] = {}

def get_registry() -> ModelRegistry:
    """Lazy load model registry"""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry

@app.get("/v1/models")
async def list_models():
    """List all available models (registry-based)"""
    registry = get_registry()
    enabled_models = registry.get_enabled_models()
    
    models = []
    for model_id in enabled_models:
        config = registry.models[model_id]
        models.append({
            "id": model_id,
            "object": "model",
            "created": int(datetime.fromisoformat(config.release_date).timestamp()),
            "owned_by": "ki-campus",
            "permission": [],
            "root": model_id,
            "parent": None,
        })
    
    return {"object": "list", "data": models}

async def get_assistant(model: str):
    """Get or create assistant for model (registry-based)"""
    global _assistants_cache
    
    if model not in _assistants_cache:
        registry = get_registry()
        try:
            _assistants_cache[model] = registry.create_assistant(model)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load model: {str(e)}")
    
    return _assistants_cache[model]

@app.post("/v1/chat/completions")
async def chat_completion(request: ChatCompletionRequest):
    """Chat endpoint (now model-agnostic via registry)"""
    assistant = await get_assistant(request.model)
    # ... rest of chat logic unchanged
```

## Integration Steps

### Phase 1: Current State (Jan 2026)
- ✅ Upstream remote configured
- ✅ main branch synced
- 🔄 **Create model registry configuration** (models.yaml)
- 🔄 **Implement ModelRegistry class** (model_registry.py)
- 🔄 **Update Arena API** to use registry instead of hardcoding

### Phase 2: Testing
- Run test suite with registry
- Verify both v1 and v1-improved models work
- Test listing models endpoint
- Performance baseline

### Phase 3: Upstream Integration
- When upstream updates chatbot, create new entry in models.yaml
- Extract version info from upstream release
- Add new assistant class to registry
- Test compatibility with Arena

### Phase 4: Production
- Deploy registry configuration
- Monitor model selection in voting
- Track statistics per model version

## Benefits

1. **Plug and Play:** Neue Chatbot-Versionen durch YAML-Config hinzufügen
2. **Zero Code Changes:** Arena API bleibt unverändert
3. **Version Tracking:** Arena kann Votes pro Version tracken
4. **A/B Testing:** Parallel multiple Versionen testen
5. **Rollback:** Einfach Versionen in YAML deaktivieren
6. **Upgrades:** Upstream changes ohne Code-Merges

## Example: Adding New Upstream Version

Wenn upstream Repository eine neue `KICampusAssistantV2` definiert:

```yaml
# 1. Füge zu config/models.yaml hinzu:
kicampus-v2:
  name: "KI-Campus v2.0"
  description: "New AI model with improved reasoning"
  enabled: false  # Start disabled for testing
  params:
    context_window: 20
    model_enum: "gpt4"
  source: "src.llm.assistant_v2:KICampusAssistantV2"
  release_date: "2026-01-15"

# 2. Merging upstream changes
git merge upstream/main

# 3. Enable for testing in Arena
arena:
  enabled_models:
    - "kicampus-v1"
    - "kicampus-v1-improved"
    - "kicampus-v2"  # Enable

# 4. Test locally
./scripts/test-deployment.sh

# 5. Deploy when ready
git push origin feature/openwebui-arena
```

## Files Modified/Created

| File | Status | Change |
|------|--------|--------|
| `config/models.yaml` | NEW | Model registry configuration |
| `src/llm/model_registry.py` | NEW | Registry and factory implementation |
| `src/openwebui/openwebui_api_llm.py` | MODIFIED | Use registry instead of hardcoding |
| `pyproject.toml` | MODIFIED | Add PyYAML dependency (if needed) |
| `CHATBOT_VERSIONING.md` | NEW | This documentation |

## Future Enhancements

- [ ] Database-backed model registry (replace YAML)
- [ ] Version compatibility matrix
- [ ] Automatic version detection from upstream
- [ ] Model metrics per version
- [ ] A/B test statistics
- [ ] Version deprecation warnings
