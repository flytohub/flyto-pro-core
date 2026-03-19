"""
OpenAI Provider — ILLMService and IEmbeddingService implementations.

Supports:
- chat() with tool_calls (function calling)
- chat_stream() with streaming tool_calls
- generate() / generate_stream() for simple completions
- embed() / embed_batch() for embeddings

Requires: pip install flyto-pro[openai]
"""

import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional

from ..llm import (
    EmbeddingResponse,
    IEmbeddingService,
    ILLMService,
    LLMChunk,
    LLMResponse,
    ToolCallRequest,
    ToolCallResult,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def _tools_to_openai(tools: Optional[List[ToolCallRequest]]) -> Optional[List[Dict]]:
    """Convert ToolCallRequest list to OpenAI tool format."""
    if not tools:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


class OpenAILLMService(ILLMService):
    """
    OpenAI implementation of ILLMService.

    Full support for:
    - Text generation (generate, generate_stream)
    - Chat with tool calling (chat, chat_stream)
    - Streaming with token-by-token + tool_call deltas

    Usage:
        llm = OpenAILLMService(model="gpt-4o")

        # Simple chat
        response = await llm.chat(messages=[{"role": "user", "content": "Hello"}])

        # Chat with tools
        tools = [ToolCallRequest(name="get_weather", description="Get weather", parameters={...})]
        response = await llm.chat(messages=[...], tools=tools)
        for tc in response.tool_calls:
            print(tc.name, tc.arguments)

        # Streaming with tools
        async for chunk in llm.chat_stream(messages=[...], tools=tools):
            if chunk.text:
                print(chunk.text, end="")
            for tc in chunk.tool_calls:
                print(tc)
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **client_kwargs: Any,
    ):
        self._model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url
        self._client_kwargs = client_kwargs
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "openai is required for OpenAILLMService. "
                    "Install it with: pip install flyto-pro[openai]"
                )
            kwargs = {"api_key": self._api_key, **self._client_kwargs}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    # ── Simple generation ─────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async for chunk in self.chat_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            if chunk.text:
                yield chunk.text

    # ── Chat with tool calling ────────────────────────────────

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolCallRequest]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        client = self._get_client()
        params: Dict[str, Any] = {
            "model": kwargs.pop("model", self._model),
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        openai_tools = _tools_to_openai(tools)
        if openai_tools:
            params["tools"] = openai_tools
            params["tool_choice"] = tool_choice or "auto"

        response = await client.chat.completions.create(**params)
        choice = response.choices[0]
        usage = response.usage

        # Extract tool calls
        result_tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                result_tool_calls.append(
                    ToolCallResult(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            tokens_used=(usage.total_tokens if usage else 0),
            finish_reason=choice.finish_reason or "stop",
            tool_calls=result_tool_calls,
            metadata={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "id": response.id,
            },
        )

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolCallRequest]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMChunk]:
        client = self._get_client()
        params: Dict[str, Any] = {
            "model": kwargs.pop("model", self._model),
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        openai_tools = _tools_to_openai(tools)
        if openai_tools:
            params["tools"] = openai_tools
            params["tool_choice"] = tool_choice or "auto"

        stream = await client.chat.completions.create(**params)
        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            lc = LLMChunk()

            if delta.content:
                lc.text = delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    tc_data: Dict[str, Any] = {"index": tc.index}
                    if tc.id:
                        tc_data["id"] = tc.id
                    if tc.function and tc.function.name:
                        tc_data["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tc_data["arguments"] = tc.function.arguments
                    lc.tool_calls.append(tc_data)

            if chunk.choices[0].finish_reason:
                lc.finish_reason = chunk.choices[0].finish_reason

            yield lc

    # ── Properties ────────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "openai"

    async def is_available(self) -> bool:
        try:
            client = self._get_client()
            await client.models.list()
            return True
        except Exception:
            return False


class OpenAIEmbeddingService(IEmbeddingService):
    """
    OpenAI implementation of IEmbeddingService.

    Usage:
        embedder = OpenAIEmbeddingService()
        result = await embedder.embed("Hello world")
        print(result.embedding)  # [0.012, -0.034, ...]
    """

    def __init__(
        self,
        model: str = _DEFAULT_EMBEDDING_MODEL,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **client_kwargs: Any,
    ):
        self._model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url
        self._client_kwargs = client_kwargs
        self._client = None
        self._dimension: Optional[int] = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "openai is required for OpenAIEmbeddingService. "
                    "Install it with: pip install flyto-pro[openai]"
                )
            kwargs = {"api_key": self._api_key, **self._client_kwargs}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def embed(self, text: str) -> EmbeddingResponse:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=text,
        )
        data = response.data[0]
        self._dimension = len(data.embedding)
        return EmbeddingResponse(
            embedding=data.embedding,
            model=self._model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=texts,
        )
        tokens_per = (
            response.usage.total_tokens // len(texts) if response.usage else 0
        )
        results = []
        for item in response.data:
            self._dimension = len(item.embedding)
            results.append(
                EmbeddingResponse(
                    embedding=item.embedding,
                    model=self._model,
                    tokens_used=tokens_per,
                )
            )
        return results

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            defaults = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536,
            }
            return defaults.get(self._model, 1536)
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    async def is_available(self) -> bool:
        try:
            self._get_client()
            return self._api_key is not None
        except Exception:
            return False
