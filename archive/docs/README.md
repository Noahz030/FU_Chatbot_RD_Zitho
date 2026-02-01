# Archived: Deprecated Documentation

## `SEEDING.md.deprecated`

### Status: ❌ DEPRECATED (Feb 1, 2026)

Diese Datei beschreibt den **alten Pre-Seeding Workflow** von Januar 2026.

### Grund der Archivierung

Das Arena-System wurde zwischen Jan 22-28 2026 umgestellt auf:
- ✅ **On-Demand Generation** (pro Session)
- ✅ **Hardcoded Question Catalog** (`src/arena/arena_questions.py`)
- ✅ **Live Response Generation** (`src/arena/openwebui_api_llm.py`)

**SEEDING.md beschrieb den alten Workflow:**
- ❌ Pre-Generation aller Antworten
- ❌ Speicherung in JSON-Dateien
- ❌ Keine echte Varianz zwischen Sessions

### Falls noch benötigt

Falls du die alte Seeding-Logik brauchst (Referenz, Legacy-System):
1. Kopiere `SEEDING.md.deprecated` zurück nach `docs/`
2. Nutze es als Referenz für alte Scripts
3. Beachte: Diese Workflows funktionieren nicht mehr mit aktuellem System!

### Aktuelle Dokumentation

Für aktuelle Arena-Features siehe:
- `VOTING.md` - Arena Dokumentation
- `src/arena/arena_questions.py` - Question Catalog
- `src/arena/openwebui_api_llm.py` - API Implementation

### Archivierungsdatum

- **Datum:** Feb 1, 2026
- **Grund:** Cleanup docs/ - Pre-Seeding deprecated in favor of On-Demand Generation
- **Commit:** chore: Archive deprecated SEEDING.md documentation
