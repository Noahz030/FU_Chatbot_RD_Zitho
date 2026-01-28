"""
OpenWebUI-kompatible API mit echter Azure OpenAI Integration und Streaming-Support.
Inkludiert Arena Voting System für Benchmarking.
"""

import asyncio
import json
import os
import random
import secrets
import time
import uuid
import hashlib
import logging
from datetime import datetime
from typing import AsyncGenerator, Literal, Optional, Any, Annotated, Dict, Tuple, List

from fastapi import FastAPI, HTTPException, Depends, Header, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import APIKeyHeader
from llama_index.core.llms import ChatMessage, MessageRole
from pydantic import BaseModel, Field
from pathlib import Path

from src.env import env
from src.llm.model_registry import get_registry
# Wichtige Imports für LLM-Assistenten werden lazy innerhalb der Funktionen geladen,
# damit Arena-Endpunkte ohne vollständige LLM/Monitoring-Dependencies funktionieren.
from src.openwebui.voting_system import default_storage, ArenaComparison
from src.openwebui.arena_questions import (
    get_all_questions, 
    get_questions_by_category, 
    get_questions_by_type,
    get_questions_for_subset,
    get_subset_size,
)

app = FastAPI(
    title="KI-Campus Chatbot Arena API",
    description="OpenWebUI-kompatible API mit Azure OpenAI Integration",
    version="1.0.0",
)

logger = logging.getLogger(__name__)

# Request size limit (bytes)
MAX_REQUEST_BODY_BYTES = int(os.getenv("MAX_REQUEST_BODY_BYTES", "10240"))  # 10KB default

@app.middleware("http")
async def enforce_request_size_limit(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(status_code=413, content={"detail": "Payload too large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header"})

        body = await request.body()
        if len(body) > MAX_REQUEST_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})

        # Preserve body for downstream handlers
        request._body = body

    return await call_next(request)

# CORS mit konfigurierbaren Origins
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
if allowed_origins == ["*"]:
    # Development: Allow all
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,  # Cannot use credentials with wildcard origin
    )
else:
    # Production: Restrict to specific domains
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )

# API Key Authentication für Arena-Endpunkte
api_key_header = APIKeyHeader(name="X-Arena-Key", auto_error=False)


async def verify_arena_key(api_key: Optional[str] = Depends(api_key_header)):
    """Verifiziere API-Key für Arena-Endpunkte (nur in Production)"""
    # In Production Mode: API-Key erforderlich
    if os.getenv("ENVIRONMENT", "LOCAL") == "PRODUCTION":
        arena_api_key = os.getenv("ARENA_API_KEY")
        if not arena_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Arena API key not configured on server",
            )
        if not api_key or api_key != arena_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing Arena API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
    # In LOCAL/STAGING: Kein API-Key erforderlich
    return True


def check_generation_rate_limit(session_id: str, client_ip: Optional[str] = None) -> None:
    """Check rate limits for /arena/generate endpoint.
    
    Two layers:
    - Per (session_id, client_ip): up to SESSION_MAX_REQ within WINDOW_SECONDS
    - Per client_ip: up to IP_MAX_REQ within WINDOW_SECONDS
    """
    global _rate_limit_cache, _rate_limit_ip_cache
    
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    def _prune(cache: dict) -> dict:
        return {k: [t for t in v if t >= window_start] for k, v in cache.items() if v}

    # Periodic cleanup to keep memory bounded
    if len(_rate_limit_cache) > RATE_LIMIT_CLEANUP_THRESHOLD:
        _rate_limit_cache = _prune(_rate_limit_cache)
    if len(_rate_limit_ip_cache) > RATE_LIMIT_CLEANUP_THRESHOLD:
        _rate_limit_ip_cache = _prune(_rate_limit_ip_cache)

    cache_key = (session_id, client_ip or "unknown")
    ip_key = client_ip or "unknown"

    # Session+IP bucket
    session_ts = [t for t in _rate_limit_cache.get(cache_key, []) if t >= window_start]
    if len(session_ts) >= RATE_LIMIT_SESSION_MAX_REQUESTS:
        retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - min(session_ts))))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_SESSION_MAX_REQUESTS} generations per {RATE_LIMIT_WINDOW_SECONDS} seconds for this session. Retry after {retry_after} seconds."
        )

    # IP-wide bucket
    ip_ts = [t for t in _rate_limit_ip_cache.get(ip_key, []) if t >= window_start]
    if len(ip_ts) >= RATE_LIMIT_IP_MAX_REQUESTS:
        retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - min(ip_ts))))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_IP_MAX_REQUESTS} generations per {RATE_LIMIT_WINDOW_SECONDS} seconds for this IP. Retry after {retry_after} seconds."
        )

    # Record current timestamp
    session_ts.append(now)
    ip_ts.append(now)
    _rate_limit_cache[cache_key] = session_ts
    _rate_limit_ip_cache[ip_key] = ip_ts


def get_csrf_token_for_session(session_id: str) -> str:
    """Get or generate CSRF token for a session.
    
    Args:
        session_id: User session ID
        
    Returns:
        CSRF token (32 bytes, URL-safe)
    """
    if session_id not in _csrf_token_cache:
        _csrf_token_cache[session_id] = secrets.token_urlsafe(32)
    return _csrf_token_cache[session_id]


def validate_csrf_token(session_id: str, token: str) -> bool:
    """Validate CSRF token for a session.
    
    Args:
        session_id: User session ID
        token: CSRF token to validate
        
    Returns:
        True if token is valid, False otherwise
    """
    expected_token = _csrf_token_cache.get(session_id)
    if not expected_token or not token:
        return False
    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(expected_token, token)


def rotate_csrf_token(session_id: str) -> str:
    """Rotate CSRF token after successful vote to prevent token reuse.
    
    Args:
        session_id: User session ID
        
    Returns:
        New CSRF token
    """
    _csrf_token_cache[session_id] = secrets.token_urlsafe(32)
    return _csrf_token_cache[session_id]

# Rate limiting cache for /arena/generate endpoint
# Format: {(session_id, client_ip): [request_timestamps]}
_rate_limit_cache: dict[tuple[str, str], list[float]] = {}
# Format: {client_ip: [request_timestamps]}
_rate_limit_ip_cache: dict[str, list[float]] = {}
# Allow short bursts: 10 req/min per session+IP; cap per IP to prevent multi-session abuse
RATE_LIMIT_SESSION_MAX_REQUESTS = 10
RATE_LIMIT_IP_MAX_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_CLEANUP_THRESHOLD = 10000  # Cleanup cache if size exceeds this

# CSRF token cache for voting endpoints
# Format: {session_id: csrf_token}
_csrf_token_cache: dict[str, str] = {}

# Lazy-Loading der Assistenten via ModelRegistry
# Assistants are loaded on-demand to avoid failures during startup
_assistants_cache: dict[str, Any] = {}

# Validation bounds
MAX_QUESTION_LEN = 500
MAX_COMMENT_LEN = 500
MAX_ID_LEN = 64
MAX_TOKEN_LEN = 128

# Audit logging
AUDIT_LOG_FILE = Path(__file__).parent / "data" / "arena_audit.jsonl"


def _normalize_ip(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    ip = ip.strip()
    if ip.startswith("[") and "]" in ip:
        ip = ip[1:ip.index("]")]
    if ":" in ip and ip.count(":") == 1:
        ip = ip.split(":")[0]
    return ip


def get_client_ip(request: Request) -> Optional[str]:
    """Resolve client IP with proxy-awareness."""
    if os.getenv("ENVIRONMENT", "LOCAL") == "PRODUCTION":
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return _normalize_ip(xff.split(",")[0])
        xri = request.headers.get("x-real-ip")
        if xri:
            return _normalize_ip(xri)
    if request.client:
        return _normalize_ip(request.client.host)
    return None


def _hash_ip(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    salt = os.getenv("AUDIT_IP_SALT", "")
    digest = hashlib.sha256(f"{salt}{ip}".encode("utf-8")).hexdigest()
    return digest[:12]


def write_audit_event(
    event_type: str,
    *,
    session_id: Optional[str] = None,
    comparison_id: Optional[str] = None,
    subset_id: Optional[int] = None,
    vote: Optional[str] = None,
    request: Optional[Request] = None,
    detail: Optional[str] = None,
) -> None:
    try:
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        client_ip = get_client_ip(request) if request else None
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "session_id": session_id,
            "comparison_id": comparison_id,
            "subset_id": subset_id,
            "vote": vote,
            "client_ip_hash": _hash_ip(client_ip),
            "user_agent": request.headers.get("user-agent") if request else None,
            "detail": detail,
        }
        with AUDIT_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Failed to write audit log: %s", e)


async def get_assistant(model_id: str) -> Any:
    """
    Get or create assistant instance for a model
    Uses registry for dynamic loading and caching
    
    Args:
        model_id: Model identifier (e.g., "kicampus-v1")
        
    Returns:
        Assistant instance
        
    Raises:
        HTTPException: If model not found or disabled
    """
    global _assistants_cache
    
    if model_id not in _assistants_cache:
        try:
            registry = get_registry()
            _assistants_cache[model_id] = registry.get_or_create_assistant(model_id)
        except (ValueError, ImportError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to load model '{model_id}': {str(e)}"
            )
    
    return _assistants_cache[model_id]


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = Field(default=False)
    temperature: float = Field(default=0.0)
    max_tokens: int = Field(default=400)


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


@app.get("/")
def root():
    try:
        registry = get_registry()
        enabled_models = registry.get_enabled_models()
    except Exception:
        enabled_models = []
    
    return {
        "status": "online",
        "service": "KI-Campus Chatbot Arena",
        "available_models": enabled_models,
        "llm_backend": "Azure OpenAI + GWDG",
        "azure_configured": bool(env.AZURE_OPENAI_API_KEY),
        "version_management": "ModelRegistry (config/models.yaml)",
    }


@app.get("/v1/models")
def list_models() -> ModelsResponse:
    """List all available models from registry"""
    registry = get_registry()
    enabled_models = registry.get_enabled_models()
    
    models = []
    for model_id in enabled_models:
        config = registry.get_model_config(model_id)
        models.append(ModelInfo(
            id=config.id,
            created=int(config.release_datetime.timestamp()),
            owned_by="ki-campus"
        ))
    
    return ModelsResponse(data=models)


def convert_to_llama_messages(messages: list[Message]) -> list[ChatMessage]:
    """Konvertiert OpenAI-Format zu LlamaIndex ChatMessage Format."""
    llama_messages = []
    for msg in messages:
        if msg.role == "system":
            role = MessageRole.SYSTEM
        elif msg.role == "assistant":
            role = MessageRole.ASSISTANT
        else:
            role = MessageRole.USER
        llama_messages.append(ChatMessage(role=role, content=msg.content))
    return llama_messages


async def stream_llm_response(
    assistant: Any,
    query: str,
    chat_history: list[ChatMessage],
    model: Any,
    request_model: str,
) -> AsyncGenerator[str, None]:
    """
    Streamt die LLM-Response als Server-Sent Events (SSE).
    
    Da LlamaIndex standardmäßig keine Token-by-Token Streaming-API hat,
    simulieren wir Streaming durch Wort-basierte Chunks.
    """
    completion_id = f"chatcmpl-{abs(hash(query + str(time.time())))}"
    created = int(time.time())
    
    try:
        # Hole die vollständige Response vom LLM
        # TODO: Für echtes Streaming müsste die LLM-Schnittstelle angepasst werden
        response = await asyncio.to_thread(
            assistant.chat,
            query=query,
            model=model,
            chat_history=chat_history
        )
        
        response_text = response.content
        
        # Streame die Response wortweise
        words = response_text.split()
        for i, word in enumerate(words):
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": word + " " if i < len(words) - 1 else word
                        },
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.02)  # Kleine Verzögerung für visuelles Feedback
        
        # Sende finalen Chunk
        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request_model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        error_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request_model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": f"\n\n[Fehler: {str(e)}]"
                    },
                    "finish_reason": "error"
                }
            ]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-kompatible Chat-Completions mit echter LLM-Integration.
    Unterstützt sowohl Streaming als auch nicht-Streaming Responses.
    
    Models werden dynamisch aus dem Registry geladen.
    """
    
    # Validate model
    try:
        registry = get_registry()
        registry.get_model_config(request.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get assistant via registry
    assistant = await get_assistant(request.model)
    
    # Extrahiere User-Query und Chat-History
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list is empty")
    
    # Konvertiere zu LlamaIndex Format
    llama_messages = convert_to_llama_messages(request.messages)
    
    # Letzte User-Nachricht ist die Query
    user_messages = [msg for msg in llama_messages if msg.role == MessageRole.USER]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")
    
    query = user_messages[-1].content
    
    # Chat-History ohne die letzte User-Nachricht
    chat_history = llama_messages[:-1]
    
    # Verwende GPT-4 als Basis-Modell (lazy import to avoid startup failures)
    from src.llm.LLMs import Models
    llm_model = Models.GPT4
    
    # Streaming-Response
    if request.stream:
        return StreamingResponse(
            stream_llm_response(
                assistant=assistant,
                query=query,
                chat_history=chat_history,
                model=llm_model,
                request_model=request.model
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    # Nicht-Streaming Response
    try:
        response = await asyncio.to_thread(
            assistant.chat,
            query=query,
            model=llm_model,
            chat_history=chat_history
        )
        
        response_text = response.content
        
        return {
            "id": f"chatcmpl-{abs(hash(response_text))}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop",
                    "logprobs": None
                }
            ],
            "usage": {
                "prompt_tokens": len(query.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(query.split()) + len(response_text.split())
            },
            "system_fingerprint": None
        }
    except Exception as e:
        # Detaillierte Fehlerausgabe zur Diagnose
        import traceback, sys
        tb = traceback.format_exc()
        err_type = type(e).__name__
        # Logge den Fehler samt Stacktrace in die Container-Logs
        print(f"LLM Error Type: {err_type}")
        print(f"LLM Error Message: {e}")
        print(tb)
        raise HTTPException(status_code=500, detail=f"LLM Error: {err_type}: {str(e)}")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "mode": "production",
        "azure_configured": bool(env.AZURE_OPENAI_API_KEY)
    }


# ============================================================================
# Arena Voting Endpoints
# ============================================================================

@app.get("/arena/questions")
def get_arena_questions(category: Optional[str] = Query(None), question_type: Optional[str] = Query(None)):
    """
    Gibt die verfügbaren Evaluationsfragen zurück.
    
    Args:
        category: Optional Kategorie-Filter (z.B. 'wissen_allgemein', 'noise_out_of_scope')
        question_type: Optional Typ-Filter (z.B. 'single_hop_rag', 'multi_hop_rag', 'robustness_test')
    
    Returns:
        Liste von Fragen oder gefiltert nach Kategorie/Typ
    """
    try:
        if question_type:
            questions = get_questions_by_type(question_type)
        elif category:
            questions = get_questions_by_category(category)
        else:
            questions = get_all_questions()
        
        return {
            "success": True,
            "count": len(questions),
            "questions": questions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving questions: {str(e)}")


@app.get("/arena/questions-for-subset/{subset_id}")
def get_questions_for_subset_endpoint(subset_id: int):
    """
    Gibt die Fragen für eine spezifische Subset zurück.
    
    Args:
        subset_id: Subset-ID (1-4)
    
    Returns:
        Liste von Fragen für die Subset mit Metadaten
        
    Raises:
        400: Wenn subset_id nicht 1-4 ist
    """
    try:
        if subset_id < 1 or subset_id > 4:
            raise ValueError("subset_id must be between 1 and 4")
        
        questions = get_questions_for_subset(subset_id)
        subset_size = get_subset_size(subset_id)
        
        return {
            "success": True,
            "subset_id": subset_id,
            "total_questions": subset_size,
            "questions": questions
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving subset questions: {str(e)}")



class SaveComparisonRequest(BaseModel):
    """Request body für das Speichern eines Arena-Vergleichs."""
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LEN)
    model_a: str = Field(min_length=1, max_length=MAX_ID_LEN)
    answer_a: str = Field(min_length=1)
    model_b: str = Field(min_length=1, max_length=MAX_ID_LEN)
    answer_b: str = Field(min_length=1)


class VoteRequest(BaseModel):
    """Request body für das Voten."""
    comparison_id: str = Field(min_length=1, max_length=MAX_ID_LEN)
    vote: Literal["A", "B", "tie", "both_bad"]
    comment: Optional[str] = Field(default=None, max_length=MAX_COMMENT_LEN)
    subset_id: Optional[int] = Field(default=None, ge=1, le=4)
    csrf_token: Optional[str] = Field(default=None, max_length=MAX_TOKEN_LEN)  # CSRF token for vote submission protection


class GenerateComparisonRequest(BaseModel):
    """Request to generate answers on-demand for a question."""
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LEN, description="Die zu stellende Frage")
    session_id: Optional[str] = Field(default=None, max_length=MAX_ID_LEN, description="Optional Session ID for tracking")
    user_id: Optional[str] = Field(default=None, max_length=MAX_ID_LEN, description="Optional User ID for tracking")
    subset_id: Optional[int] = Field(default=None, ge=1, le=4, description="Optional subset assignment")


@app.post("/arena/generate")
async def generate_comparison(
    request: GenerateComparisonRequest,
    http_request: Request,
    auth: bool = Depends(verify_arena_key),
):
    """
    Generiert on-demand Antworten von beiden Modellen für eine Frage.
    Speichert die Comparison in der globalen JSONL und gibt sie zurück.
    
    WICHTIG: Validiert, dass die Frage zur zugeordneten Subset des Users gehört.
    Implementiert Rate-Limiting: max 1 Anfrage pro 5 Sekunden pro Session+IP.
    
    DEDUPLIZIERUNG: Prüft ob für diese Frage + Subset bereits ein Comparison existiert.
    Falls ja, wird das existierende zurückgegeben statt erneut zu generieren.
    
    Dies ermöglicht pro-User Generierung mit Varianz in den Antworten,
    statt vorab fest geseete Vergleiche zu nutzen.
    
    Args:
        request: GenerateComparisonRequest mit question, session_id, user_id und subset_id
        auth: API-Key Verification
        x_forwarded_for: Client IP from proxy (X-Forwarded-For header)
        
    Returns:
        ArenaComparison mit answers_a und answer_b von beiden Modellen
        
    Raises:
        400: Wenn question nicht zur subset_id gehört
        429: Wenn Rate-Limit überschritten (max 1 pro 5 Sekunden)
        503: Wenn ein Modell nicht verfügbar ist
    """
    try:
        # Extract client IP
        client_ip = get_client_ip(http_request)
        
        # Validate that question belongs to the user's subset
        if request.subset_id is not None:
            valid_questions = get_questions_for_subset(request.subset_id)
            if request.question not in valid_questions:
                logger.error(f"Question validation failed: '{request.question}' not in subset {request.subset_id}")
                logger.error(f"Valid questions for subset {request.subset_id}: {valid_questions}")
                write_audit_event(
                    "invalid_question_subset",
                    session_id=request.session_id,
                    subset_id=request.subset_id,
                    request=http_request,
                    detail="question_not_in_subset",
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Question '{request.question}' does not belong to subset {request.subset_id}"
                )
        
        # DEDUPLIZIERUNG: Prüfe ob bereits ein Comparison für diese Frage + Subset existiert
        all_comparisons = default_storage.load_all_comparisons()
        existing = next(
            (c for c in all_comparisons 
             if c.question == request.question and c.subset_id == request.subset_id),
            None
        )
        
        if existing:
            # Return existing comparison (already shuffled) - NO RATE LIMIT for cached responses
            return existing.get_shuffled_view()
        
        # Check rate limit ONLY for new LLM generations (after deduplication check)
        try:
            check_generation_rate_limit(request.session_id or "unknown", client_ip)
        except HTTPException as e:
            if e.status_code == 429:
                write_audit_event(
                    "rate_limit_generate",
                    session_id=request.session_id,
                    request=http_request,
                    detail=e.detail if isinstance(e.detail, str) else None,
                )
            raise
        
        # Get both assistants
        assistant_a = await get_assistant("kicampus-v1")
        assistant_b = await get_assistant("kicampus-v1-improved")
        
        if not assistant_a or not assistant_b:
            raise HTTPException(
                status_code=503,
                detail="One or both model endpoints are unavailable"
            )
        
        # Call both models in parallel
        loop = asyncio.get_event_loop()
        answer_a_task = loop.run_in_executor(None, lambda: call_assistant(assistant_a, request.question))
        answer_b_task = loop.run_in_executor(None, lambda: call_assistant(assistant_b, request.question))
        
        answer_a = await answer_a_task
        answer_b = await answer_b_task
        
        # Create comparison
        comparison = ArenaComparison(
            id=str(uuid.uuid4()),
            question=request.question,
            timestamp=datetime.utcnow().isoformat(),
            model_a="kicampus-v1",
            answer_a=answer_a,
            model_b="kicampus-v1-improved",
            answer_b=answer_b,
            session_id=request.session_id,
            user_id=request.user_id,
            subset_id=request.subset_id,
            is_generated_on_demand=True,
        )
        
        # Save to global JSONL
        default_storage.save_comparison(comparison)

        write_audit_event(
            "generate_success",
            session_id=request.session_id,
            subset_id=request.subset_id,
            request=http_request,
        )
        
        # Return shuffled view for blind testing
        return comparison.get_shuffled_view()
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="One or both models timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating comparison: {str(e)}")


def call_assistant(assistant: Any, question: str) -> str:
    """
    Call assistant synchronously and return answer text.
    This wrapper allows async/await handling of sync assistant calls.
    """
    try:
        # HTTPProxyAssistant needs (query, model, chat_history)
        # Use GPT4 as default model
        from src.llm.LLMs import Models
        response = assistant.chat(question, Models.GPT4, chat_history=[])
        
        if isinstance(response, str):
            return response
        elif hasattr(response, 'content'):
            return response.content
        elif hasattr(response, 'response'):
            return response.response
        else:
            return str(response)
    except Exception as e:
        # Return error message marked clearly
        return f"[Error: {type(e).__name__}: {str(e)}]"


@app.post("/arena/save-comparison")
def save_comparison(request: SaveComparisonRequest, auth: bool = Depends(verify_arena_key)):
    """
    Speichert einen neuen Arena-Vergleich.
    
    Returns die comparison_id für späteres Voting.
    """
    comparison = ArenaComparison(
        id=str(uuid.uuid4()),
        question=request.question,
        timestamp=datetime.utcnow().isoformat(),
        model_a=request.model_a,
        answer_a=request.answer_a,
        model_b=request.model_b,
        answer_b=request.answer_b,
    )
    
    default_storage.save_comparison(comparison)
    
    return {
        "success": True,
        "comparison_id": comparison.id,
        "message": "Comparison saved successfully"
    }


@app.post("/arena/vote")
def submit_vote(
    request: VoteRequest,
    http_request: Request,
    x_session_id: Optional[str] = Header(default=None),
    auth: bool = Depends(verify_arena_key),
):
    """
    Submitted einen Vote für einen existierenden Vergleich.
    Validiert CSRF-Token zur Verhinderung von Cross-Site Vote Submission.
    """
    if not x_session_id:
        write_audit_event("vote_rejected", request=http_request, detail="missing_session_id")
        raise HTTPException(status_code=400, detail="X-Session-ID header required")

    # Prevent duplicate vote on the same comparison by the same session
    data_dir = Path(__file__).parent / "data"
    user_votes_file = data_dir / "arena_user_votes.jsonl"
    if user_votes_file.exists():
        with user_votes_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("session_id") == x_session_id and obj.get("comparison_id") == request.comparison_id:
                    write_audit_event(
                        "vote_rejected",
                        session_id=x_session_id,
                        comparison_id=request.comparison_id,
                        request=http_request,
                        detail="duplicate_vote",
                    )
                    raise HTTPException(
                        status_code=403,
                        detail="Diese Session hat diesen Vergleich bereits gevotet."
                    )

    # Validate CSRF token (unless API key is provided, which bypasses CSRF)
    if request.csrf_token and not validate_csrf_token(x_session_id, request.csrf_token):
        write_audit_event(
            "csrf_invalid",
            session_id=x_session_id,
            comparison_id=request.comparison_id,
            request=http_request,
            detail="csrf_token_invalid",
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing CSRF token. This vote cannot be processed for security reasons."
        )

    # 1) Session-basiertes Vote-Logging (append-only JSONL)
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    user_votes_file = data_dir / "arena_user_votes.jsonl"
    user_vote = {
        "comparison_id": request.comparison_id,
        "vote": request.vote,
        "comment": request.comment,
        "subset_id": request.subset_id,
        "session_id": x_session_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    with user_votes_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(user_vote, ensure_ascii=False) + "\n")

    # 2) Backwards-compatibility: globale Ansicht weiterhin aktualisieren
    success = default_storage.update_vote(
        comparison_id=request.comparison_id,
        vote=request.vote,
        comment=request.comment
    )
    
    if not success:
        write_audit_event(
            "vote_rejected",
            session_id=x_session_id,
            comparison_id=request.comparison_id,
            request=http_request,
            detail="comparison_not_found",
        )
        raise HTTPException(status_code=404, detail="Comparison ID not found")
    
    # 3) Rotate CSRF token after successful vote to prevent token reuse
    new_token = rotate_csrf_token(x_session_id)

    write_audit_event(
        "vote_submitted",
        session_id=x_session_id,
        comparison_id=request.comparison_id,
        subset_id=request.subset_id,
        vote=request.vote,
        request=http_request,
    )
    
    return {
        "success": True,
        "message": f"Vote '{request.vote}' recorded successfully",
        "csrf_token": new_token  # Return new token for next vote
    }


@app.get("/arena/comparisons")
def get_all_comparisons(subset: Optional[int] = None, auth: bool = Depends(verify_arena_key)):
    """
    Gibt alle gespeicherten Vergleiche zurück, optional gefiltert nach subset_id.
    
    Parameters:
    - subset: Optional subset_id (1-4) zum Filtern der Vergleiche
    """
    # Auto-Migration: Weise unzugewiesenen Vergleichen Subsets zu
    default_storage.assign_subsets_to_unassigned()
    
    if subset is not None:
        comparisons = default_storage.get_comparisons_by_subset(subset)
    else:
        comparisons = default_storage.load_all_comparisons()
    
    # Return shuffled views to prevent position bias in blind A/B testing
    return {
        "total": len(comparisons),
        "comparisons": [c.get_shuffled_view() for c in comparisons],
        "subset": subset
    }


@app.get("/arena/assign-subset")
def assign_subset(
    randomize: bool = Query(False, description="Randomize subset assignment (LOCAL only)"),
    auth: bool = Depends(verify_arena_key),
):
    """
    Weist einen Subset (1-4) per Round-Robin-Verfahren zu.
    Basiert auf der Anzahl der bisherigen Votes pro Subset.
    """
    if os.getenv("ENVIRONMENT", "LOCAL") != "PRODUCTION" and randomize:
        subset_id = random.choice([1, 2, 3, 4])
        return {"subset_id": subset_id}

    subset_id = default_storage.assign_subset_round_robin()
    return {"subset_id": subset_id}


@app.get("/arena/csrf-token")
def get_csrf_token(session_id: str, auth: bool = Depends(verify_arena_key)):
    """Get CSRF token for a session. Called by voting UI before voting."""
    token = get_csrf_token_for_session(session_id)
    return {"csrf_token": token}


@app.get("/arena/statistics")
def get_statistics(auth: bool = Depends(verify_arena_key)):
    """Aggregierte Statistiken über individuelle Nutzer-Votes.

    Reduziert auf den jeweils letzten Vote je (session_id, comparison_id).
    """
    data_dir = Path(__file__).parent / "data"
    user_votes_file = data_dir / "arena_user_votes.jsonl"

    latest: Dict[Tuple[str, str], Dict] = {}
    if user_votes_file.exists():
        with user_votes_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                key = (obj.get("session_id", ""), str(obj.get("comparison_id", "")))
                ts = obj.get("timestamp") or ""
                if key not in latest or ts >= latest[key].get("timestamp", ""):
                    latest[key] = obj

    totals = {"A": 0, "B": 0, "tie": 0, "both_bad": 0}
    for v in latest.values():
        ch = v.get("vote")
        if ch in totals:
            totals[ch] += 1
    voted_count = sum(totals.values())
    return {
        "distinct_user_votes": len(latest),
        "votes_for_a": totals["A"],
        "votes_for_b": totals["B"],
        "votes_tie": totals["tie"],
        "votes_both_bad": totals["both_bad"],
        "win_rate_a": (totals["A"] / voted_count) if voted_count else 0,
        "win_rate_b": (totals["B"] / voted_count) if voted_count else 0,
        "tie_rate": (totals["tie"] / voted_count) if voted_count else 0,
        "both_bad_rate": (totals["both_bad"] / voted_count) if voted_count else 0,
    }


@app.get("/arena/voted")
def get_voted(session_id: str = Query(..., description="Client Session-ID"), auth: bool = Depends(verify_arena_key)):
    """Liste aller comparison_ids, die diese Session bereits gevoted hat."""
    data_dir = Path(__file__).parent / "data"
    user_votes_file = data_dir / "arena_user_votes.jsonl"
    voted: List[str] = []
    seen: set[str] = set()
    if user_votes_file.exists():
        with user_votes_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("session_id") == session_id:
                    cid = str(obj.get("comparison_id", ""))
                    if cid and cid not in seen:
                        seen.add(cid)
                        voted.append(cid)
    return {"comparison_ids": voted}


@app.get("/arena/session")
def create_session(auth: bool = Depends(verify_arena_key)):
    """Erzeugt eine neue Session-ID (optional – Clients können auch selbst UUIDs erzeugen)."""
    return {"session_id": str(uuid.uuid4())}


@app.get("/arena/user-votes")
def get_user_votes(session_id: Optional[str] = None, auth: bool = Depends(verify_arena_key)):
    """Liefert alle User-Votes mit Session-IDs. Optional filterbar nach session_id."""
    # Use the same path logic as submit_vote
    data_dir = Path(__file__).parent / "data"
    user_votes_file = data_dir / "arena_user_votes.jsonl"
    
    votes = []
    if user_votes_file.exists():
        with user_votes_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if session_id is None or obj.get("session_id") == session_id:
                        votes.append(obj)
                except Exception:
                    continue
    
    return {"total": len(votes), "votes": votes}


@app.get("/arena/comparison/{comparison_id}")
def get_comparison(comparison_id: str, auth: bool = Depends(verify_arena_key)):
    """
    Gibt einen spezifischen Vergleich zurück.
    """
    comparison = default_storage.get_comparison_by_id(comparison_id)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    return comparison.model_dump()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
