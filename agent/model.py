from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from utils.config import settings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional during early scaffolding
    OpenAI = None


ChatMessage = Mapping[str, str]


class ModelClientError(RuntimeError):
    """Raised when the model client cannot complete a request."""


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model_name: str
    used_mock: bool


def build_messages(
    *,
    system_prompt: str | None = None,
    history: Sequence[ChatMessage] | None = None,
    user_message: str,
) -> list[dict[str, str]]:
    """Build a chat-completions style message list."""
    messages: list[dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for item in history or []:
        role = item.get("role", "").strip()
        content = item.get("content", "").strip()
        if role in {"system", "user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})
    return messages


class LLMClient:
    """Small wrapper around an OpenAI-compatible chat completion API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        use_mock: bool | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.base_url = base_url if base_url is not None else settings.openai_base_url
        self.model_name = model_name if model_name is not None else settings.model_name
        self.use_mock = use_mock if use_mock is not None else settings.use_mock_model
        self.temperature = (
            temperature if temperature is not None else settings.model_temperature
        )
        self.max_tokens = (
            max_tokens if max_tokens is not None else settings.model_max_tokens
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.model_timeout_seconds
        )

        self._client: Any | None = None

    def chat(
        self,
        *,
        user_message: str,
        history: Sequence[ChatMessage] | None = None,
        system_prompt: str | None = None,
    ) -> ModelResponse:
        """Return the assistant reply for the given message context."""
        messages = build_messages(
            system_prompt=system_prompt,
            history=history,
            user_message=user_message,
        )

        if self.use_mock:
            return self._mock_chat(user_message=user_message, history=history)

        return self._real_chat(messages=messages)

    def generate_text(
        self,
        *,
        user_message: str,
        history: Sequence[ChatMessage] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Convenience wrapper used by the agent core."""
        response = self.chat(
            user_message=user_message,
            history=history,
            system_prompt=system_prompt,
        )
        return response.text

    def _mock_chat(
        self,
        *,
        user_message: str,
        history: Sequence[ChatMessage] | None = None,
    ) -> ModelResponse:
        turn_count = len(history or [])
        text = (
            "这是一个用于联调的 mock 模型回复。"
            f" 当前收到的用户消息是：{user_message}"
            f"。当前历史消息条数：{turn_count}。"
            " 后续接入真实模型后，这里会返回正式分析结果。"
        )
        return ModelResponse(
            text=text,
            model_name=self.model_name,
            used_mock=True,
        )

    def _real_chat(self, *, messages: Sequence[Mapping[str, str]]) -> ModelResponse:
        client = self._get_client()

        try:
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=list(messages),
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:  # pragma: no cover - depends on remote service
            raise ModelClientError(f"Model request failed: {exc}") from exc

        text = self._extract_text(completion)
        return ModelResponse(
            text=text,
            model_name=self.model_name,
            used_mock=False,
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        if OpenAI is None:
            raise ModelClientError(
                "The openai package is not installed. Run `pip install -r requirements.txt`."
            )

        if not self.api_key:
            raise ModelClientError(
                "OPENAI_API_KEY is missing. Set it in your .env file or enable USE_MOCK_MODEL."
            )

        client_kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout_seconds,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self._client = OpenAI(**client_kwargs)
        return self._client

    @staticmethod
    def _extract_text(completion: Any) -> str:
        try:
            content = completion.choices[0].message.content
        except (AttributeError, IndexError, KeyError, TypeError) as exc:
            raise ModelClientError("Model response did not contain valid text.") from exc

        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    piece = item.get("text")
                else:
                    piece = getattr(item, "text", None)
                if piece:
                    parts.append(str(piece).strip())
            text = "\n".join(part for part in parts if part)
        else:
            text = str(content).strip()

        if not text:
            raise ModelClientError("Model response text was empty.")

        return text


default_model_client = LLMClient()
