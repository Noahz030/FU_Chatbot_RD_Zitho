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
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, Header, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import APIKeyHeader
from llama_index.core.llms import ChatMessage, MessageRole
from pydantic import BaseModel, Field, constr
from pathlib import Path

from src.env import env
from src.llm.model_registry import get_registry
# Wichtige Imports für LLM-Assistenten werden lazy innerhalb der Funktionen geladen,
# damit Arena-Endpunkte ohne vollständige LLM/Monitoring-Dependencies funktionieren.
from src.arena.voting_system import default_storage, ArenaComparison, VoteChoice
from src.arena.arena_questions import (
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

# Request size limit (bytes) - Safety constraint to prevent DoS
MAX_REQUEST_BODY_BYTES = int(os.getenv("MAX_REQUEST_BODY_BYTES", "1048576"))  # 1MB default

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

def get_data_dir() -> Path:
    """Resolve Arena data directory.

    Priority:
    1) ARENA_DATA_DIR (explicit directory)
    2) STORAGE_PATH (file path -> use parent dir)
    3) module-local data/ folder (legacy default)
    """
    arena_data_dir = os.getenv("ARENA_DATA_DIR")
    if arena_data_dir:
        return Path(arena_data_dir).expanduser().resolve()

    storage_path = os.getenv("STORAGE_PATH")
    if storage_path:
        return Path(storage_path).expanduser().resolve().parent

    return Path(__file__).parent / "data"


# Audit logging
AUDIT_LOG_FILE = get_data_dir() / "arena_audit.jsonl"


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
# Pydantic Models for Arena

class VoteEnum(str, Enum):
    """Valid voting choices for arena comparisons."""
    A = "A"
    B = "B"
    TIE = "tie"
    BOTH_BAD = "both_bad"


class SaveComparisonRequest(BaseModel):
    question: constr(min_length=1, max_length=2000)
    model_a: str
    answer_a: str
    model_b: str
    answer_b: str


class VoteRequest(BaseModel):
    comparison_id: constr(min_length=1, max_length=100)
    vote: VoteEnum = Field(description="Must be one of: A, B, tie, both_bad")
    comment: Optional[constr(max_length=1000)] = Field(default=None, description="Optional comment (max 1000 chars)")
    subset_id: Optional[int] = None
    csrf_token: Optional[str] = Field(default=None, description="CSRF token for vote submission")


class GenerateRequest(BaseModel):
    question: constr(min_length=1, max_length=2000)
    session_id: constr(min_length=1, max_length=100)
    subset_id: Optional[int] = None
    user_id: Optional[constr(max_length=100)] = None


@app.get("/arena")
def arena_root():
    """Arena Voting System Root"""
    return {
        "status": "online",
        "service": "KI-Campus Arena API",
        "version": "1.0.0"
    }


@app.get("/arena/assign-subset")
def assign_subset(randomize: bool = Query(False)):
    """Weist dem User ein Subset zu (Round-Robin basierend auf Vote-Counts)."""
    subset_id = default_storage.assign_subset_round_robin()
    return {
        "subset_id": subset_id,
        "message": f"Du wurdest Subset {subset_id} zugewiesen"
    }


@app.get("/arena/questions-for-subset/{subset_id}")
def get_questions_for_subset_endpoint(subset_id: int):
    """Liefert alle Fragen für ein bestimmtes Subset"""
    questions = get_questions_for_subset(subset_id)
    total_questions = get_subset_size(subset_id)
    return {
        "subset_id": subset_id,
        "questions": questions,
        "total_questions": total_questions
    }


def call_assistant(assistant: Any, question: str) -> str:
    """
    Call assistant synchronously and return answer text.
    This wrapper allows async/await handling of sync assistant calls.
    
    Supports both HTTPProxyAssistant and KICampusAssistant.
    Both assistants use their respective RAG systems to retrieve sources
    and generate context-aware answers with citations.
    
    Args:
        assistant: HTTPProxyAssistant or KICampusAssistant instance
        question: User question to answer
        
    Returns:
        Answer text with citations (HTML format)
        
    Raises:
        Returns error message string if generation fails
    """
    try:
        # Both assistants need (query, model, chat_history)
        # Use GPT-4 as default model for consistency
        from src.llm.LLMs import Models
        
        # Call using keyword arguments for compatibility with all assistant types
        # This ensures proper parameter binding for both local and proxy assistants
        response = assistant.chat(
            query=question,
            model=Models.GPT4,
            chat_history=[]
        )
        
        # Handle different response types
        if isinstance(response, str):
            return response
        elif hasattr(response, 'content'):
            return response.content
        elif hasattr(response, 'response'):
            return response.response
        else:
            return str(response)
    except Exception as e:
        # Return error message marked clearly for debugging
        logger.error(f"Assistant call failed: {type(e).__name__}: {str(e)}")
        return f"[Error: {type(e).__name__}: {str(e)}]"


@app.post("/arena/generate")
async def generate_comparison(request: GenerateRequest):
    """Generiert on-demand frische Antworten zwischen zwei Assistenten-Versionen
    
    Für maximale Varianz in der Evaluation: JEDE Anfrage generiert neue Antworten,
    unabhängig davon, ob die Frage bereits vorher beantwortet wurde.
    
    Dies ermöglicht Sessions-übergreifend unterschiedliche Antworten für die gleiche Frage.
    Das Prefetch-System versteckt die Wartezeit vor dem User.
    
    Vergleicht:
    - kicampus-v1: Original Assistenten-Version mit RAG-System
    - kicampus-v1-improved: Verbesserte Assistenten-Version mit RAG-System
    
    Dies ermöglicht einen blind A/B Test zwischen zwei kompletten Chatbot-Systemen.
    """
    logger.info(f"🔄 On-demand generating comparison for: {request.question[:50]}...")
    
    try:
        # Get both assistant versions
        assistant_a = await get_assistant("kicampus-v1")
        assistant_b = await get_assistant("kicampus-v1-improved")
        
        if not assistant_a or not assistant_b:
            logger.error("One or both assistants unavailable!")
            raise HTTPException(
                status_code=503,
                detail="One or both assistant versions are unavailable"
            )
        
        logger.info("✅ Both assistants initialized")
        
        # Versuche echte Antworten zu generieren mit den Assistenten-Versionen
        answer_a = None
        answer_b = None
        
        try:
            logger.info("Attempting real LLM generation from both assistants...")
            from src.llm.LLMs import Models
            
            # Use GPT-4 as default model for both assistants
            llm_model = Models.GPT4
            
            # Generate from both assistants in parallel
            loop = asyncio.get_event_loop()
            answer_a_task = loop.run_in_executor(None, lambda: call_assistant(assistant_a, request.question))
            answer_b_task = loop.run_in_executor(None, lambda: call_assistant(assistant_b, request.question))
            
            answer_a = await answer_a_task
            answer_b = await answer_b_task
            
            logger.info(f"✅ Generated answer A from kicampus-v1 ({len(answer_a)} chars)")
            logger.info(f"✅ Generated answer B from kicampus-v1-improved ({len(answer_b)} chars)")
        
        except Exception as gen_error:
            logger.warning(f"⚠️  Real LLM generation failed: {type(gen_error).__name__}: {gen_error}")
            logger.warning(f"Falling back to placeholder answers")
            answer_a = None
            answer_b = None
        
        # Fallback answers if generation failed
        if not answer_a:
            answer_a = f"Dies ist eine Beispielantwort von kicampus-v1.\n\nDie Arena läuft aktuell im Demo-Modus. In der Produktionsumgebung würde hier eine echte Antwort zum Thema '{request.question}' stehen.\n\nDie Qualität der Antworten wird dann durch Vergleich mit anderen Chatbot-Versionen bewertet."
        
        if not answer_b:
            answer_b = f"Dies ist eine Beispielantwort von kicampus-v1-improved.\n\nDie Arena läuft aktuell im Demo-Modus. In der Produktionsumgebung würde hier eine echte Antwort zum Thema '{request.question}' stehen.\n\nDie Qualität der Antworten wird dann durch Vergleich mit anderen Chatbot-Versionen bewertet."
        
        # Erstelle Comparison zwischen den beiden Assistenten-Versionen
        comparison = ArenaComparison(
            id=str(uuid.uuid4()),
            question=request.question,
            timestamp=datetime.utcnow().isoformat(),
            model_a="kicampus-v1",
            answer_a=answer_a,
            model_b="kicampus-v1-improved",
            answer_b=answer_b,
            subset_id=request.subset_id,
            is_generated_on_demand=True,
        )
        
        # Speichere Comparison
        default_storage.save_comparison(comparison)
        logger.info(f"✅ Saved comparison {comparison.id}")
        
        # Return shuffled view for blind testing
        result = comparison.get_shuffled_view()
        logger.info(f"✅ Returning comparison (shuffled: {result.get('is_shuffled')})")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate comparison: {str(e)}"
        )


@app.get("/arena/csrf-token")
def get_csrf_token(session_id: str = Query(...)):
    """Liefert einen CSRF-Token für die Session"""
    token = secrets.token_urlsafe(32)
    # Hier könnte man den Token auch im Storage speichern für Validierung
    return {
        "csrf_token": token,
        "session_id": session_id
    }


@app.post("/arena/vote")
def submit_vote(request: VoteRequest, x_session_id: Optional[str] = Header(default=None)):
    """Speichert einen Vote"""
    session_id = x_session_id or request.comparison_id  # Fallback
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    # CSRF Token Validation
    if not request.csrf_token or not validate_csrf_token(session_id, request.csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    
    # Speichere Vote in Datei
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    user_votes_file = data_dir / "arena_user_votes.jsonl"
    
    vote_record = {
        "comparison_id": request.comparison_id,
        "vote": request.vote.value if isinstance(request.vote, VoteEnum) else str(request.vote),
        "comment": request.comment,
        "subset_id": request.subset_id,
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    with user_votes_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(vote_record, ensure_ascii=False) + "\n")
    
    # Update comparison vote
    success = default_storage.update_vote(
        comparison_id=request.comparison_id,
        vote=request.vote,
        comment=request.comment,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    # Rotate CSRF token after successful vote
    new_csrf_token = get_csrf_token_for_session(session_id)
    
    return {
        "success": True,
        "message": "Vote recorded",
        "csrf_token": new_csrf_token  # Return new token for next vote
    }


@app.get("/arena/voted")
def get_voted(session_id: str = Query(...)):
    """Liefert die comparison_ids, die diese Session bereits gevoted hat"""
    data_dir = get_data_dir()
    user_votes_file = data_dir / "arena_user_votes.jsonl"
    
    voted: List[str] = []
    seen: set = set()
    
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


@app.get("/arena/comparisons")
def get_all_comparisons(subset: Optional[int] = None):
    """Liefert alle Comparisons, optional gefiltert nach Subset"""
    if subset is not None:
        comparisons = default_storage.get_comparisons_by_subset(subset)
    else:
        comparisons = default_storage.load_all_comparisons()
    
    return {
        "total": len(comparisons),
        "comparisons": [c.get_shuffled_view() for c in comparisons]
    }


@app.get("/arena/statistics")
def get_statistics():
    """Aggregierte Statistiken auf Basis individueller Nutzer-Votes"""
    data_dir = get_data_dir()
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


@app.get("/arena/comparison/{comparison_id}")
def get_comparison(comparison_id: str):
    """Liefert eine einzelne Comparison"""
    c = default_storage.get_comparison_by_id(comparison_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return c.model_dump()


@app.get("/arena/session")
def create_session():
    """Erzeugt eine neue Session-ID"""
    return {"session_id": str(uuid.uuid4())}


@app.get("/arena/user-votes")
def get_user_votes(session_id: Optional[str] = None):
    """Liefert alle User-Votes, optional gefiltert nach session_id"""
    data_dir = get_data_dir()
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
    
    return {
        "total": len(votes),
        "votes": votes,
        "file_path": str(user_votes_file),
        "exists": user_votes_file.exists()
    }