"""Switchable chat providers (OpenAI, Groq, Gemini) behind one small interface."""
from __future__ import annotations

import json
import re
from typing import Callable, Protocol

from app.config import Settings


class ProviderError(RuntimeError):
    pass


class ChatProvider(Protocol):
    name: str
    model: str

    def complete_json(self, system: str, user: str) -> dict: ...


def parse_json(text: str) -> dict:
    """Parse model output into a dict, tolerating code fences and surrounding prose."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise ProviderError(f"Antwort ist kein JSON: {text[:200]}")


class OpenAICompatProvider:
    """Works for the OpenAI and Groq SDKs (same chat.completions interface)."""

    def __init__(self, name: str, client, model: str):
        self.name, self.client, self.model = name, client, model
        self._use_temperature = True

    def complete_json(self, system: str, user: str) -> dict:
        kwargs = dict(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        try:
            if self._use_temperature:
                try:
                    resp = self.client.chat.completions.create(temperature=0, **kwargs)
                except Exception as e:  # some reasoning models reject temperature
                    if "temperature" not in str(e):
                        raise
                    self._use_temperature = False
                    resp = self.client.chat.completions.create(**kwargs)
            else:
                resp = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            raise ProviderError(f"{self.name}: {e}") from e
        return parse_json(resp.choices[0].message.content or "")


class GeminiProvider:
    def __init__(self, api_key: str, model: str):
        from google import genai

        self.name, self.model = "gemini", model
        self.client = genai.Client(api_key=api_key)

    def complete_json(self, system: str, user: str) -> dict:
        from google.genai import types

        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system, temperature=0, response_mime_type="application/json"
                ),
            )
        except Exception as e:
            raise ProviderError(f"gemini: {e}") from e
        return parse_json(resp.text or "")


class ProviderRegistry:
    """Lazily constructs providers; only those with an API key are 'configured'."""

    def __init__(self) -> None:
        self._factories: dict[str, tuple[str, Callable[[], ChatProvider]]] = {}
        self._cache: dict[str, ChatProvider] = {}

    def register(self, name: str, model: str, factory: Callable[[], ChatProvider]) -> None:
        self._factories[name] = (model, factory)
        self._cache.pop(name, None)

    def get(self, name: str) -> ChatProvider:
        if name not in self._factories:
            raise ProviderError(f"Provider '{name}' ist nicht konfiguriert (API-Key fehlt?)")
        if name not in self._cache:
            self._cache[name] = self._factories[name][1]()
        return self._cache[name]

    def available(self) -> list[dict]:
        return [{"name": n, "model": m} for n, (m, _) in self._factories.items()]

    @classmethod
    def from_settings(cls, s: Settings) -> "ProviderRegistry":
        reg = cls()
        if s.openai_api_key:
            def _openai():
                from openai import OpenAI
                return OpenAICompatProvider("openai", OpenAI(api_key=s.openai_api_key), s.openai_chat_model)
            reg.register("openai", s.openai_chat_model, _openai)
        if s.groq_api_key:
            def _groq():
                from groq import Groq
                return OpenAICompatProvider("groq", Groq(api_key=s.groq_api_key), s.groq_chat_model)
            reg.register("groq", s.groq_chat_model, _groq)
        if s.gemini_api_key:
            reg.register("gemini", s.gemini_chat_model, lambda: GeminiProvider(s.gemini_api_key, s.gemini_chat_model))
        return reg
