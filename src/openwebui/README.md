# OpenWebUI Arena Integration für KI-Campus Chatbot

Dieses Verzeichnis enthält die OpenWebUI-Integration für das Chatbot Arena Benchmarking.

## 🎯 Status

✅ **Arena Mode funktioniert!** - Streaming-Response implementiert, body_iterator Fehler behoben  
✅ **Zwei Modelle verfügbar** - Original vs. Verbesserte Version  
✅ **Bereit für Massentests** - Mock-API läuft stabil auf Port 8001

## Übersicht

Das Setup ermöglicht es, zwei Versionen des KI-Campus Chatbots in OpenWebUI's Arena-Modus gegeneinander zu testen:

- **kicampus-original**: Die aktuelle Produktionsversion des Chatbots (Chat-History: 10 Nachrichten)
- **kicampus-improved**: Eine verbesserte Version mit erweiterten Kontext-Fenster (Chat-History: 15 Nachrichten)

## Dateien

- `openwebui_api_simple.py`: **[AKTIV]** Mock-API mit Streaming für Arena Mode Tests
- `openwebui_api_llm.py`: Vollständige API mit Azure OpenAI Integration (benötigt Azure Auth)
- `openwebui_api.py`: Original API (deprecated, hat Langfuse-Probleme)
- `assistant_improved.py`: Verbesserte Version des KI-Campus Assistenten
- `arena_benchmark.py`: CLI-Tool für manuelle Benchmarks (Alternative zu Arena Mode)
- `Dockerfile`: Docker-Image für den OpenWebUI API-Service
- `requirements.txt`: Python-Dependencies für den Service

## Setup

### 1. Voraussetzungen

- Docker und Docker Compose installiert
- OpenWebUI läuft (siehe [OpenWebUI Docs](https://docs.openwebui.com/))
- Zugriff auf die KI-Campus Vector-Datenbank (Qdrant)

### 2. Service starten

#### Option A: Mit Docker Compose (empfohlen)

```bash
# Im Root-Verzeichnis des Projekts
docker-compose up openwebui-api
```

#### Option B: Standalone Docker

```bash
# Docker Image bauen
docker build -t kicampus-openwebui -f src/openwebui/Dockerfile .

# Container starten
docker run -p 8001:8001 \
  --env-file .env \
  kicampus-openwebui
```

#### Option C: Lokale Entwicklung (Aktuell empfohlen für Tests)

```bash
# Dependencies installieren (falls noch nicht geschehen)
pip install fastapi uvicorn pydantic

# Mock-API mit Streaming-Support starten
python -m uvicorn src.openwebui.openwebui_api_simple:app --host 0.0.0.0 --port 8001

# Für echte LLM-Antworten (benötigt Azure Login):
# python -m uvicorn src.openwebui.openwebui_api_llm:app --host 0.0.0.0 --port 8001
```

### 3. OpenWebUI konfigurieren

1. OpenWebUI sollte bereits laufen auf `http://localhost:3001`
2. Gehe zu **Settings** → **Connections** → **OpenAI API**
3. Füge eine neue Connection hinzu:
   - **Base URL**: `http://host.docker.internal:8001/v1`
   - **API Key**: (optional, kann leer bleiben)
   - **Verify** klicken - sollte beide Modelle finden

4. **Arena Mode aktivieren**:
   - Öffne einen neuen Chat
   - Klicke oben auf das Modell-Dropdown
   - Wähle **"Arena (Side-by-side)"**
   - Wähle beide Modelle aus: `kicampus-original` und `kicampus-improved`

### 4. Arena-Benchmarking durchführen - **FUNKTIONIERT JETZT! ✅**

1. Öffne einen neuen Chat in OpenWebUI (`http://localhost:3001`)
2. Klicke oben auf das Modell-Dropdown und wähle **"Arena (Side-by-side)"**
3. Wähle beide Modelle: `kicampus-original` und `kicampus-improved`
4. Stelle Fragen - beide Modelle antworten parallel mit Streaming
5. Bewerte die Antworten und vergleiche die Qualität

**Hinweis**: Die aktuelle Mock-API gibt Demo-Antworten mit Präfix `[Original]` bzw. `[Verbessert]` zurück.  
Für echte LLM-Antworten muss `openwebui_api_llm.py` verwendet werden (benötigt stabile Azure Auth).

## API-Endpoints

Der Service bietet folgende OpenWebUI-kompatible Endpoints:

### `GET /`
Health check und Service-Info

### `GET /v1/models`
Liste aller verfügbaren Modelle

### `POST /v1/chat/completions`
Chat Completion Endpoint (OpenAI-kompatibel)

**Request:**
```json
{
  "model": "kicampus-original",
  "messages": [
    {"role": "user", "content": "Was ist Deep Learning?"}
  ],
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "kicampus-original",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Deep Learning ist..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

## Verbesserungen implementieren

Die verbesserte Version (`kicampus-improved`) befindet sich in `assistant_improved.py`. 

### Aktuelle Verbesserungen:
- Erhöhtes Chat-History-Limit (10 → 15 Nachrichten)
- Erweiterter Kontext für bessere Antworten

### Weitere Optimierungen hinzufügen:

1. **Bessere Retrieval-Strategie:**
```python
def retrieve_with_reranking(self, query: str):
    # Multi-stage retrieval mit Re-Ranking
    initial_chunks = self.retriever.retrieve(query, top_k=20)
    reranked_chunks = self.reranker.rerank(query, initial_chunks, top_k=5)
    return reranked_chunks
```

2. **Verbesserte Prompts:**
```python
IMPROVED_SYSTEM_PROMPT = """
Du bist ein hilfreicher KI-Assistent für KI-Campus.
Antworte präzise und strukturiert...
"""
```

3. **Query-Expansion:**
```python
def expand_query(self, query: str) -> str:
    # Erweitere die Query für besseres Retrieval
    expanded = self.llm.generate(
        f"Generiere 2-3 alternative Formulierungen für: {query}"
    )
    return f"{query} {expanded}"
```

## Benchmarking-Metriken

Folgende Aspekte sollten beim Benchmarking beachtet werden:

- **Antwortqualität**: Präzision und Vollständigkeit der Antworten
- **Quellenverwendung**: Korrekte Zitation von Kursmaterialien
- **Sprachqualität**: Natürlichkeit und Verständlichkeit
- **Relevanz**: Passung der Antwort zur Frage
- **Kontextverständnis**: Berücksichtigung des Chat-Verlaufs

## Troubleshooting

### Service startet nicht
```bash
# Logs prüfen
docker logs <container-id>

# Port-Konflikt?
lsof -i :8001
```

### OpenWebUI findet die Modelle nicht
- Prüfe, ob der Service läuft: `curl http://localhost:8001/v1/models`
- Überprüfe die Base URL in OpenWebUI
- Stelle sicher, dass keine CORS-Probleme vorliegen

### Antworten sind identisch
- Beide Versionen nutzen aktuell die gleiche Basis-Implementierung
- Implementiere Verbesserungen in `assistant_improved.py`

## Weiterführende Ressourcen

- [OpenWebUI Documentation](https://docs.openwebui.com/)
- [OpenAI API Specification](https://platform.openai.com/docs/api-reference)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Lizenz

Siehe root LICENSE file.
