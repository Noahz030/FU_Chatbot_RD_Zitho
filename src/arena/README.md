# Arena (ehemals openwebui)

Dieser Ordner ist die **aktive Implementierung** der Arena‑API und des Voting‑UI.
Das frühere Verzeichnis [src/openwebui](../openwebui) existiert weiterhin als
**Kompatibilitäts‑Layer** (Wrapper), damit bestehende Importe nicht brechen.

**Aktive Entry‑Points:**
- `src.arena.openwebui_api_llm:app` (Arena API)
- `src.arena.voting_ui_simple:app` (Voting UI)

**Datenablage:**
Die JSONL‑Daten liegen in [src/arena/data](data). Die Ablage kann über
`ARENA_DATA_DIR` oder `STORAGE_PATH` überschrieben werden (siehe Docker Compose).
