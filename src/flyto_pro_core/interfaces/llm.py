"""
LLM Service Interfaces

Abstract interfaces for LLM and embedding services.
Implementations: OpenAI, Anthropic, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional


# ── Data Models ───────────────────────────────────────────────────


@dataclass
class ToolCallRequest:
    """Tool definition passed to the LLM."""

    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})


@dataclass
class ToolCallResult:
    """A tool call returned by the LLM."""

    id: str
    name: str
    arguments: str  # JSON string


@dataclass
class LLMResponse:
    """Standard LLM response format."""

    content: str
    model: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    tool_calls: List[ToolCallResult] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tool_calls is None:
            self.tool_calls = []


@dataclass
class LLMChunk:
    """A single chunk from a streaming LLM response."""

    text: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    # tool_calls format: [{"index": int, "id": str, "name": str, "arguments": str}]
    finish_reason: Optional[str] = None


@dataclass
class EmbeddingResponse:
    """Standard embedding response format."""

    embedding: List[float]
    model: str
    tokens_used: int = 0


# ── LLM Service Interface ────────────────────────────────────────


class ILLMService(ABC):
    """
    Abstract interface for LLM services.

    Supports three modes:
    1. generate()       — single prompt → response
    2. chat()           — multi-turn messages → response (with optional tool_calls)
    3. chat_stream()    — multi-turn messages → streaming chunks (with tool_calls)

    Implementations should handle:
    - API communication
    - Rate limiting
    - Error handling and retries
    - Token counting
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate text completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Generate text with streaming response.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Provider-specific options

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolCallRequest]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Multi-turn chat completion with optional tool calling.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            tools: Optional list of tool definitions for function calling
            tool_choice: "auto", "none", or specific tool name
            **kwargs: Provider-specific options

        Returns:
            LLMResponse with assistant's reply and optional tool_calls
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolCallRequest]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMChunk]:
        """
        Streaming multi-turn chat with tool calling support.

        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            tools: Optional tool definitions
            tool_choice: Tool selection mode
            **kwargs: Provider-specific options

        Yields:
            LLMChunk objects with text deltas and/or tool_call deltas
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name being used."""
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """Get the provider name (e.g., 'openai', 'anthropic', 'ollama')."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the service is available."""
        pass


class IEmbeddingService(ABC):
    """
    Abstract interface for embedding services.

    Implementations should handle:
    - Text to vector conversion
    - Batch processing
    - Caching (optional)
    """

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResponse:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResponse with vector
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResponse objects
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get the embedding dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name being used."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the service is available."""
        pass


