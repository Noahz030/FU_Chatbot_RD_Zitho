# openwebui (legacy)

Dieses Verzeichnis bleibt als **Kompatibilitäts-Layer** erhalten.
Die aktive Arena‑Implementierung ist nach [src/arena](../arena) umgezogen.

**Bitte künftig verwenden:**
- `src.arena.openwebui_api_llm:app` (Arena API)
- `src.arena.voting_ui_simple:app` (Voting UI)

Die Module hier re-exportieren nur die neuen Entry‑Points, um bestehende
Imports und Deployments nicht zu brechen.
