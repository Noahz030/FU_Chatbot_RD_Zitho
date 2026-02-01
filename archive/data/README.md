# Archived: Old Question and Backup Files

## Status: ❌ DEPRECATED

Diese Dateien werden **nicht mehr von der Arena verwendet**.

## Archivierte Dateien

### `fixed_questions.json` (Dec 28, 2025)
- **Inhalt:** 62 alte Evaluierungs-Fragen
- **Status:** Veraltet, abgelöst durch `arena_questions.py` (Python-Katalog)
- **Grund:** Die Arena nutzt jetzt direkt die Fragen aus `src/openwebui/arena_questions.py` (hardcoded, 4 Subsets à ~15 Fragen)

### `fixed_questions_for_seeding.json` (Jan 14, 2026)
- **Inhalt:** 60 Seeding-spezifische Fragen
- **Status:** War für Seeding-Prozess, nicht mehr relevant
- **Grund:** Arena verwendet jetzt die standardisierten Fragen aus `arena_questions.py`

## Im Root `/data/` Ordner behalten

- ✅ **`arena_votes.jsonl`** - KRITISCH! Enthält alle User-Abstimmungen (60+ Votes)
  - **NICHT LÖSCHEN!** Diese Daten sind das Evaluierungsergebnis

## Deleted Files (nicht archiviert, da unwichtig)

- 🗑️ `arena_votes_backup_20260116_200941.jsonl` - Altes Backup (8 KB)
- 🗑️ `fixed_questions.txt` - Text-Export (redundant)

## Falls needed

Falls du diese Fragen-Sets für andere Zwecke brauchst:
1. Kopiere `fixed_questions.json` oder `fixed_questions_for_seeding.json` zurück nach `data/`
2. Aktualisiere die Referenzen im Code

## Archivierungsdatum

- **Datum:** Feb 1, 2026
- **Grund:** Cleanup data/ directory - use arena_questions.py instead
- **Commit:** chore: Cleanup data/ directory
