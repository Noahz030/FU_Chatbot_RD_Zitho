# Archived: Old Config Files

## Status: ❌ DEPRECATED

Diese Konfigurationsdateien werden **nicht mehr verwendet** von der Arena.

## Grund der Archivierung

Die Arena (seit Jan 26, 2026) verwendet jetzt:
- ✅ **HTTPProxyAssistant** mit direktem Proxy zu den Chatbots
- ✅ **Registry-System** für Assistent-Verwaltung
- ✅ **kicampus-v1** und **kicampus-v1-improved** direkt über Proxy

Diese alten Modell-Configs waren für das vorherige System:
- Alte OpenAI API Integration
- Mistral und GWDG direkt
- Nicht mehr relevant

## Dateien

- `models.yaml` - Produktions-Modelle (veraltet)
- `models.local.yaml` - Lokal/Dev Modelle (veraltet)

## Wenn du diese brauchen solltest

1. Kopiere sie zurück nach `config/` im Root
2. Aktualisiere die Pfade/API-Keys
3. Nutze sie für andere LLM-Systeme (nicht Arena)

## Archivierungsdatum

- **Datum:** Feb 1, 2026
- **Grund:** Cleanup Repository Structure
- **Commit:** chore: Archive old config/ directory
