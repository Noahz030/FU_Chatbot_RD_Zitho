# Deprecated Files

Diese Dateien sind veraltet und werden nicht mehr in der aktiven Implementierung verwendet.

## Veraltete API-Versionen

- **`voting_api_simple.py`** - Alte API-Implementierung (ersetzt durch `openwebui_api_llm.py`)
- **`arena_voting.py`** - Alte Voting-Logik (integriert in `openwebui_api_llm.py`)

## Veraltete UI-Komponenten

- **`voting_widget.py`** - Alte UI-Widget (ersetzt durch `voting_ui_simple.py`)

## Veraltete Assistenten

- **`assistant_improved.py`** - Veraltete Assistenten-Implementierung (verwendet jetzt Registry-basiertes System)

## Test und Benchmark Code

- **`test_arena.py`** - Alter Unit-Test Code
- **`arena_benchmark.py`** - Alter Benchmark Script
- **`arena_benchmark_interactive.py`** - Alter interaktiver Benchmark

## Veraltete Dateien

- **`arena_comparisons.json`** - Alte Test-Datei (verwenden jetzt JSONL-Format in `data/`)
- **`entrypoint.sh`** - Nicht verwendetes Startup-Script

## Aktuelle Dateien (verwenden)

Die folgenden Dateien sind aktuell und aktiv:

- ✅ **`openwebui_api_llm.py`** - Hauptmodul für Arena API
- ✅ **`voting_ui_simple.py`** - UI für Voting und Results
- ✅ **`voting_system.py`** - Datenmodelle für Comparisons
- ✅ **`arena_questions.py`** - Fragen-Katalog für Subsets

## Löschen dieser Dateien

Falls diese Dateien nicht mehr benötigt werden, können sie sicher gelöscht werden. Vorher sollte sichergestellt werden, dass kein Code mehr darauf referenziert.

```bash
rm -rf src/openwebui/deprecated/
```
