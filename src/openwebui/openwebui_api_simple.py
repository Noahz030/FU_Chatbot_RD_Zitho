"""
OpenWebUI-kompatible API - SIMPLIFIED VERSION ohne Langfuse für schnelles Testen.
"""

from typing import AsyncGenerator, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="KI-Campus Chatbot Arena API (Test Mode)",
    description="OpenWebUI-kompatible API ohne LLM-Backend für Tests",
    version="1.0.0-test",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = Field(default=False)


class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]


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
    return {
        "status": "online",
        "service": "KI-Campus Chatbot Arena (Test Mode)",
        "available_models": ["kicampus-original", "kicampus-improved"],
        "note": "This is a simplified test version. Replace with full version once dependencies are resolved.",
    }


@app.get("/v1/models")
def list_models() -> ModelsResponse:
    return ModelsResponse(
        data=[
            ModelInfo(id="kicampus-original", created=1700000000, owned_by="ki-campus"),
            ModelInfo(id="kicampus-improved", created=1700000000, owned_by="ki-campus"),
        ]
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Mock endpoint für Tests - gibt Demo-Antworten zurück."""
    
    if request.model not in ["kicampus-original", "kicampus-improved"]:
        raise HTTPException(status_code=400, detail=f"Unknown model: {request.model}")
    
    user_message = request.messages[-1].content if request.messages else ""
    
    # Demo-Antworten basierend auf dem Modell
    if request.model == "kicampus-original":
        response_text = f"[Original] Demo-Antwort auf: '{user_message}'\n\nDies ist die Standard-Version des KI-Campus Chatbots. Um die echten LLM-Antworten zu erhalten, müssen alle Dependencies korrekt installiert werden."
    else:
        response_text = f"[Verbessert] Erweiterte Antwort auf: '{user_message}'\n\nDies ist die verbesserte Version mit erweitertem Kontext-Fenster. Um die echten LLM-Antworten zu erhalten, müssen alle Dependencies korrekt installiert werden."
    
    import time
    response_data = {
        "id": f"chatcmpl-test-{abs(hash(response_text))}",
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
            "prompt_tokens": len(user_message.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(user_message.split()) + len(response_text.split())
        },
        "system_fingerprint": None
    }
    
    return response_data


@app.get("/health")
def health():
    return {"status": "healthy", "mode": "test"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
