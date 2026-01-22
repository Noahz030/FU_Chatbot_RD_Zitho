"""
HTTP Proxy Assistant for Arena

Forwards requests to external chatbot APIs instead of instantiating locally.
Used to integrate external chatbot versions (original vs improved) into Arena.
"""

import logging
from typing import Optional
import requests
from llama_index.core.llms import ChatMessage, MessageRole

from src.llm.LLMs import Models

logger = logging.getLogger(__name__)


class HTTPProxyAssistant:
    """
    Proxy assistant that forwards chat requests to an external API
    
    This allows integrating externally-hosted chatbots without running them locally.
    The external API must implement the /api/chat endpoint compatible with KICampusAssistant.
    """
    
    def __init__(self, api_base_url: str, api_key: str = "arena-test-key", timeout: int = 60, use_thread_api: bool = False, **kwargs):
        """
        Initialize HTTP proxy assistant
        
        Args:
            api_base_url: Base URL of the external chatbot API (e.g., http://localhost:9001)
            api_key: API key for authentication
            timeout: Request timeout in seconds
            use_thread_api: If True, uses thread-based API (user_query + thread_id) instead of messages list
            **kwargs: Additional parameters (e.g., context_window) ignored by proxy
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.use_thread_api = use_thread_api
        self.session = requests.Session()
        self.session.headers.update({"Api-Key": api_key})
        
        logger.info(f"HTTPProxyAssistant initialized for {api_base_url} (thread_api={use_thread_api})")
    
    def _convert_chat_history(self, chat_history: list[ChatMessage]) -> list[dict]:
        """Convert LlamaIndex ChatMessage to API format"""
        messages = []
        for msg in chat_history:
            role = "user" if msg.role == MessageRole.USER else "assistant"
            messages.append({"role": role, "content": msg.content})
        return messages
    
    def chat(
        self, 
        query: str, 
        model: Models, 
        chat_history: list[ChatMessage] = None
    ) -> ChatMessage:
        """
        Send chat request to external API
        
        Args:
            query: User query
            model: Model enum (gpt4, etc.)
            chat_history: Previous chat messages
            
        Returns:
            ChatMessage with response from external API
        """
        chat_history = chat_history or []
        
        # Build request payload based on API version
        if self.use_thread_api:
            # Improved chatbot: thread-based API (user_query + thread_id)
            payload = {
                "user_query": {
                    "role": "user",
                    "content": query
                },
                "thread_id": None,  # Stateless for Arena
                "model": model.value if hasattr(model, 'value') else str(model),
            }
        else:
            # Original chatbot: stateless messages list
            payload = {
                "messages": self._convert_chat_history(chat_history) + [
                    {"role": "user", "content": query}
                ],
                "model": model.value if hasattr(model, 'value') else str(model),
            }
        
        try:
            logger.debug(f"Calling {self.api_base_url}/api/chat")
            response = self.session.post(
                f"{self.api_base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract response content
            # Expected format: {"message": "...", "response_id": "..."} for KICampus API
            answer = data.get("message", data.get("response", ""))
            
            logger.info(f"Received response ({len(answer)} chars)")
            
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content=answer
            )
            
        except requests.Timeout:
            logger.error(f"Timeout calling {self.api_base_url}/api/chat")
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content=f"[ERROR: Request timeout after {self.timeout}s]"
            )
        except requests.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content=f"[ERROR: HTTP {e.response.status_code}]"
            )
        except Exception as e:
            logger.error(f"Error calling external API: {type(e).__name__}: {e}")
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content=f"[ERROR: {type(e).__name__}]"
            )
    
    def chat_with_course(
        self,
        query: str,
        model: Models,
        course_id: Optional[int] = None,
        chat_history: list[ChatMessage] = None,
        module_id: Optional[int] = None,
    ) -> ChatMessage:
        """
        Send course-specific chat request to external API
        
        Args:
            query: User query
            model: Model enum
            course_id: Optional course ID for filtering
            chat_history: Previous chat messages
            module_id: Optional module ID for filtering
            
        Returns:
            ChatMessage with response from external API
        """
        chat_history = chat_history or []
        
        payload = {
            "messages": self._convert_chat_history(chat_history) + [
                {"role": "user", "content": query}
            ],
            "model": model.value if hasattr(model, 'value') else str(model),
        }
        
        if course_id:
            payload["course_id"] = course_id
        if module_id:
            payload["module_id"] = module_id
        
        try:
            logger.debug(f"Calling {self.api_base_url}/api/chat (course_id={course_id})")
            response = self.session.post(
                f"{self.api_base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            answer = data.get("message", data.get("response", ""))
            
            logger.info(f"Received course response ({len(answer)} chars)")
            
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content=answer
            )
            
        except Exception as e:
            logger.error(f"Error in chat_with_course: {type(e).__name__}: {e}")
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content=f"[ERROR: {type(e).__name__}]"
            )
