"""
OpenAI LLM Provider Implementation.

Adapter for OpenAI's API (GPT-4, GPT-3.5, embeddings).
Implements retry logic, error handling, and rate limiting.
"""

from typing import Any, AsyncIterator, Dict, List, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.domain.exceptions import (
    InvalidModelError,
    LLMProviderError,
    RateLimitError,
)
from src.domain.interfaces import ILLMProvider
from src.domain.models import Message, MessageRole


class OpenAIProvider(ILLMProvider):
    """
    OpenAI API implementation with streaming support.
    
    RISK: OpenAI API can be unreliable during high load.
    Mitigation: Retry logic with exponential backoff.
    
    TODO: Add cost tracking per request
    TODO: Add request/response caching for identical prompts
    """

    def __init__(
        self,
        api_key: str,
        organization: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            organization: Optional organization ID
            base_url: Optional custom API base URL (for proxies or testing)
        """
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )

        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            organization=organization,
            base_url=base_url,
        )
        self._token_encoder = None  # Lazy load tiktoken

    @retry(
        retry=retry_if_exception_type((LLMProviderError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """
        Generate completion using OpenAI Chat Completions API.
        
        Automatically retries on transient failures with exponential backoff.
        """
        try:
            # Convert domain messages to OpenAI format
            openai_messages = self._convert_messages_to_openai(messages)
            
            # Build request parameters
            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            # Add tools if provided
            if tools:
                kwargs["tools"] = [
                    {"type": "function", "function": tool} for tool in tools
                ]
                kwargs["tool_choice"] = "auto"
            
            # Make API call
            response = await self.client.chat.completions.create(**kwargs)
            
            # Extract response
            choice = response.choices[0]
            assistant_message = choice.message
            
            # Handle tool calls
            tool_calls = None
            if assistant_message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_message.tool_calls
                ]
            
            return Message(
                role=MessageRole.ASSISTANT,
                content=assistant_message.content or "[Tool call]",  # Placeholder when calling tools
                tool_calls=tool_calls,
                metadata={
                    "model": model,
                    "finish_reason": choice.finish_reason,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )
            
        except Exception as e:
            # Parse OpenAI-specific errors
            error_msg = str(e)
            
            if "rate_limit" in error_msg.lower():
                raise RateLimitError("openai", retry_after=60)
            elif "invalid" in error_msg.lower() and "model" in error_msg.lower():
                raise InvalidModelError("openai", model)
            else:
                raise LLMProviderError(f"OpenAI API error: {error_msg}") from e

    async def stream_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream completion tokens in real-time from OpenAI.
        
        Yields tokens as they arrive for better UX in chat interfaces.
        Note: Tool calls are not supported in streaming mode.
        """
        try:
            # Convert domain messages to OpenAI format
            openai_messages = self._convert_messages_to_openai(messages)
            
            # Build request parameters (no tools in streaming mode)
            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }
            
            # Stream API call
            stream = await self.client.chat.completions.create(**kwargs)
            
            # Yield tokens as they arrive
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = str(e)
            
            if "rate_limit" in error_msg.lower():
                raise RateLimitError("openai", retry_after=60)
            elif "invalid" in error_msg.lower() and "model" in error_msg.lower():
                raise InvalidModelError("openai", model)
            else:
                raise LLMProviderError(f"OpenAI streaming error: {error_msg}") from e

    async def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """
        Generate embedding using OpenAI Embeddings API.
        
        Note: text-embedding-3-small is more cost-effective than ada-002
        for most use cases.
        """
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text,
            )
            return response.data[0].embedding
            
        except Exception as e:
            raise LLMProviderError(f"OpenAI embedding error: {str(e)}") from e

    def get_token_count(self, text: str, model: str) -> int:
        """
        Count tokens using tiktoken.
        
        Important for managing context windows and cost estimation.
        """
        if self._token_encoder is None:
            try:
                import tiktoken
                # Use cl100k_base encoding for GPT-4 and GPT-3.5-turbo
                self._token_encoder = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                # Rough estimate if tiktoken not available (4 chars ≈ 1 token)
                return len(text) // 4
        
        return len(self._token_encoder.encode(text))

    def _convert_messages_to_openai(
        self,
        messages: List[Message],
    ) -> List[Dict[str, Any]]:
        """Convert domain messages to OpenAI API format."""
        openai_messages = []
        
        for msg in messages:
            openai_msg: Dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }
            
            # Add tool call information if present
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            
            openai_messages.append(openai_msg)
        
        return openai_messages
