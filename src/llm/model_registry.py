"""
Model Registry for Chatbot Arena
Enables plug-and-play version management without code changes
"""

import importlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Type
from datetime import datetime

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a single chatbot version"""
    
    id: str
    name: str
    description: str
    enabled: bool
    params: dict[str, Any]
    source: str  # Format: "module.path:ClassName"
    release_date: str
    tags: list[str]
    
    @property
    def release_datetime(self) -> datetime:
        """Parse release date to datetime"""
        return datetime.fromisoformat(self.release_date)
    
    def to_openai_model(self) -> dict:
        """Convert to OpenAI models list format"""
        return {
            "id": self.id,
            "object": "model",
            "created": int(self.release_datetime.timestamp()),
            "owned_by": "ki-campus",
            "permission": [],
            "root": self.id,
            "parent": None,
        }


class ModelRegistry:
    """
    Load and manage chatbot versions from YAML configuration
    
    Supports dynamic model loading without code changes
    """
    
    def __init__(self, config_path: str = "config/models.yaml"):
        """
        Initialize registry from configuration file
        
        Args:
            config_path: Path to models.yaml configuration file
                        (relative to current working directory or absolute)
        """
        self.config_path = Path(config_path)
        
        # If relative path doesn't exist, try from parent directory
        # (handles both local and Docker execution contexts)
        if not self.config_path.exists() and not self.config_path.is_absolute():
            alt_path = Path("..") / self.config_path
            if alt_path.exists():
                self.config_path = alt_path
        
        self.models: dict[str, ModelConfig] = {}
        self._assistant_cache: dict[str, Any] = {}
        
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using default models")
            self.load_default_models()
        else:
            logger.info(f"Using config from: {self.config_path.resolve()}")
            self.load_config()
    
    def load_default_models(self) -> None:
        """Load default models when config file is not available"""
        default_config = """
models:
    kicampus-v1:
        name: "KI-Campus (Original)"
        description: "Original chatbot version via HTTPProxyAssistant"
        enabled: true
        params:
            api_base_url: "http://chatbot-original:80"
            api_key: "arena-test-key"
            timeout: 45
        source: "src.llm.http_proxy_assistant:HTTPProxyAssistant"
        release_date: "2025-01-01"
        tags:
            - "original"
            - "baseline"
            - "stable"

    kicampus-v1-improved:
        name: "KI-Campus (Improved)"
        description: "Improved chatbot version via HTTPProxyAssistant"
        enabled: true
        params:
            api_base_url: "http://chatbot-improved:80"
            api_key: "arena-test-key"
            timeout: 45
            use_thread_api: true
        source: "src.llm.http_proxy_assistant:HTTPProxyAssistant"
        release_date: "2025-06-01"
        tags:
            - "improved"
            - "extended-context"
            - "stable"
"""
        config_data = yaml.safe_load(default_config)
        # Parse model configurations (same as load_config)
        for model_id, model_data in config_data['models'].items():
            model = ModelConfig(
                id=model_id,
                name=model_data['name'],
                description=model_data['description'],
                enabled=model_data['enabled'],
                params=model_data['params'],
                source=model_data['source'],
                release_date=model_data['release_date'],
                tags=model_data.get('tags', [])
            )
            self.models[model_id] = model
        logger.info(f"Loaded {len(self.models)} default models")
    
    def load_config(self) -> None:
        """Load model configurations from YAML file"""
        try:
            with open(self.config_path, encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'models' not in config_data:
                raise ValueError("Invalid config: missing 'models' section")
            
            # Parse model configurations
            for model_id, model_data in config_data['models'].items():
                model = ModelConfig(
                    id=model_id,
                    name=model_data['name'],
                    description=model_data['description'],
                    enabled=model_data['enabled'],
                    params=model_data['params'],
                    source=model_data['source'],
                    release_date=model_data['release_date'],
                    tags=model_data.get('tags', [])
                )
                self.models[model_id] = model
            
            logger.info(f"Loaded {len(self.models)} models from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model registry: {e}")
            raise
    
    def get_model_config(self, model_id: str) -> ModelConfig:
        """
        Get configuration for a specific model
        
        Args:
            model_id: Model identifier
            
        Returns:
            ModelConfig object
            
        Raises:
            ValueError: If model not found or disabled
        """
        if model_id not in self.models:
            available = ", ".join(self.models.keys())
            raise ValueError(
                f"Unknown model '{model_id}'. Available: {available}"
            )
        
        model = self.models[model_id]
        if not model.enabled:
            raise ValueError(
                f"Model '{model_id}' is disabled. "
                "Enable in config/models.yaml to use."
            )
        
        return model
    
    def get_enabled_models(self) -> list[str]:
        """Get list of enabled model IDs from currently loaded models"""
        return [model_id for model_id, model in self.models.items() if model.enabled]
    
    def get_default_model(self) -> str:
        """Get default model ID from configuration"""
        with open(self.config_path, encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        return config_data['arena'].get('default_model', 'kicampus-v1-improved')
    
    def list_models(self, enabled_only: bool = True) -> list[ModelConfig]:
        """
        List all available models
        
        Args:
            enabled_only: If True, only return enabled models
            
        Returns:
            List of ModelConfig objects
        """
        models = [m for m in self.models.values()]
        
        if enabled_only:
            models = [m for m in models if m.enabled]
        
        return sorted(models, key=lambda m: m.release_datetime)
    
    def _load_assistant_class(self, source: str) -> Type:
        """
        Dynamically import assistant class
        
        Args:
            source: Import path in format "module.path:ClassName"
            
        Returns:
            Assistant class
            
        Raises:
            ImportError: If class cannot be loaded
        """
        try:
            module_path, class_name = source.rsplit(':', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ValueError, ImportError, AttributeError) as e:
            raise ImportError(
                f"Failed to load {source}: {e}"
            ) from e
    
    def create_assistant(
        self, 
        model_id: str,
        **kwargs: Any
    ) -> Any:
        """
        Factory method to create assistant instance
        
        Args:
            model_id: Model identifier
            **kwargs: Additional arguments to pass to assistant
            
        Returns:
            Assistant instance
            
        Raises:
            ValueError: If model not found/disabled
            ImportError: If assistant class cannot be loaded
        """
        # Get configuration
        config = self.get_model_config(model_id)
        
        # Load assistant class dynamically
        assistant_class = self._load_assistant_class(config.source)
        
        # Merge config params with kwargs (kwargs take precedence)
        params = {**config.params, **kwargs}
        
        logger.info(
            f"Creating assistant '{model_id}' with params: {params}"
        )
        
        # Instantiate assistant
        try:
            assistant = assistant_class(**params)
            return assistant
        except TypeError as e:
            raise ValueError(
                f"Failed to instantiate {config.source}: {e}"
            ) from e
    
    def get_or_create_assistant(
        self,
        model_id: str,
        **kwargs: Any
    ) -> Any:
        """
        Get cached assistant or create new one
        
        Uses lazy loading to avoid instantiation until needed
        
        Args:
            model_id: Model identifier
            **kwargs: Additional arguments
            
        Returns:
            Assistant instance (cached)
        """
        if model_id not in self._assistant_cache:
            self._assistant_cache[model_id] = self.create_assistant(
                model_id,
                **kwargs
            )
        
        return self._assistant_cache[model_id]
    
    def clear_cache(self) -> None:
        """Clear cached assistants (useful for testing)"""
        self._assistant_cache.clear()
        logger.info("Assistant cache cleared")
    
    def get_model_info(self, model_id: str) -> dict:
        """
        Get comprehensive info about a model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Dictionary with model information
        """
        config = self.get_model_config(model_id)
        
        return {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "enabled": config.enabled,
            "params": config.params,
            "source": config.source,
            "release_date": config.release_date,
            "tags": config.tags,
            "openai_format": config.to_openai_model(),
        }


# Global registry instance
_registry_instance: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """
    Get or create global registry instance
    
    Lazy initialization pattern for single instance
    """
    global _registry_instance
    
    if _registry_instance is None:
        _registry_instance = ModelRegistry()
    
    return _registry_instance


def reload_registry() -> None:
    """Reload registry from configuration (useful for hot-reload)"""
    global _registry_instance
    _registry_instance = None
    get_registry()
