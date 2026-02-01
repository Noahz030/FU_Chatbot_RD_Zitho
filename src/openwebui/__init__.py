"""Legacy openwebui package.

This package is kept for backward compatibility. The Arena implementation
has moved to src.arena.
"""

from src.arena.openwebui_api_llm import app  # re-export

__all__ = ["app"]
