"""
LLM Client — Multi-provider AI interface for Nexora Customer Success FTE.

Supports:
  - Anthropic Claude  (provider="anthropic")
  - OpenAI GPT        (provider="openai")
  - Google Gemini     (provider="gemini")

Provider is selected via the LLM_PROVIDER environment variable.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Structured response returned by any LLM provider."""

    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    tokens_used: int = 0          # convenience: input + output
    latency_ms: float = 0.0
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if self.tokens_used == 0:
            self.tokens_used = self.input_tokens + self.output_tokens


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

class LLMClient:
    """
    Unified interface for multiple LLM providers.

    Usage::

        client = LLMClient()           # reads LLM_PROVIDER from env
        response = client.generate(
            system_prompt="You are a helpful support agent.",
            user_prompt="How do I reset my password?",
        )
        print(response.content)
    """

    # Default models per provider
    DEFAULT_MODELS: dict[str, str] = {
        "anthropic": "claude-sonnet-4-6",
        "openai": "gpt-4o-mini",
        "gemini": "gemini-1.5-flash",
    }

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.provider = (provider or os.getenv("LLM_PROVIDER", "anthropic")).lower()
        self.model = model or os.getenv("LLM_MODEL", self.DEFAULT_MODELS.get(self.provider, ""))
        self._api_key = api_key or self._resolve_api_key()
        logger.info("LLMClient initialised: provider=%s model=%s", self.provider, self.model)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Generate a response synchronously.

        Returns an :class:`LLMResponse` even on failure (with ``error`` set).
        """
        start = time.perf_counter()
        try:
            if self.provider == "anthropic":
                response = self._call_anthropic(system_prompt, user_prompt, max_tokens)
            elif self.provider == "openai":
                response = self._call_openai(system_prompt, user_prompt, max_tokens)
            elif self.provider == "gemini":
                response = self._call_gemini(system_prompt, user_prompt, max_tokens)
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider!r}")

            response.latency_ms = (time.perf_counter() - start) * 1000
            return response

        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("LLM generation failed [%s]: %s", self.provider, exc)
            return LLMResponse(
                content="",
                provider=self.provider,
                model=self.model,
                latency_ms=latency_ms,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _call_anthropic(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> LLMResponse:
        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

        client = anthropic.Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = message.content[0].text if message.content else ""
        return LLMResponse(
            content=content,
            provider="anthropic",
            model=self.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

    def _call_openai(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> LLMResponse:
        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "openai package not installed. Run: pip install openai"
            ) from exc

        client = OpenAI(api_key=self._api_key)
        completion = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = completion.choices[0].message.content or ""
        usage = completion.usage
        return LLMResponse(
            content=content,
            provider="openai",
            model=self.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    def _call_gemini(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> LLMResponse:
        try:
            import google.generativeai as genai  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "google-generativeai not installed. Run: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt,
        )
        result = model.generate_content(
            user_prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        content = result.text if result.text else ""
        # Gemini usage metadata may not always be available
        usage = getattr(result, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        return LLMResponse(
            content=content,
            provider="gemini",
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> Optional[str]:
        key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        env_var = key_map.get(self.provider)
        if env_var:
            return os.getenv(env_var)
        return None

    def is_configured(self) -> bool:
        """Return True if an API key is available for the selected provider."""
        return bool(self._api_key)

    def __repr__(self) -> str:
        configured = "configured" if self.is_configured() else "NO API KEY"
        return f"<LLMClient provider={self.provider!r} model={self.model!r} [{configured}]>"
