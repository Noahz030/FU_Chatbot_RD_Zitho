"""Legacy entrypoint wrapper for Arena API.

Use src.arena.openwebui_api_llm:app going forward.
"""

from src.arena.openwebui_api_llm import app

__all__ = ["app"]
