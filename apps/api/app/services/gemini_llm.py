"""Cloud LLM via Google Gemini (replaces local Ollama)."""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_client_configured = False


def _ensure_configured() -> None:
    global _client_configured
    if _client_configured:
        return
    if not settings.gemini_api_key.strip():
        raise RuntimeError("GEMINI_API_KEY is not configured")
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    _client_configured = True


def gemini_available() -> bool:
    return bool(settings.gemini_api_key.strip())


def _response_text(response) -> str:
    if not response.candidates:
        raise RuntimeError("Gemini returned no candidates")
    parts = response.candidates[0].content.parts if response.candidates[0].content else []
    text = "".join(getattr(p, "text", "") or "" for p in parts).strip()
    if not text:
        raise RuntimeError("Gemini returned empty text")
    return text


def gemini_chat(system: str, user: str, max_tokens: int = 800) -> str:
    _ensure_configured()
    import google.generativeai as genai

    model = genai.GenerativeModel(
        settings.gemini_model,
        system_instruction=system,
    )
    try:
        response = model.generate_content(
            user,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=max_tokens,
            ),
        )
        return _response_text(response)
    except Exception as exc:
        logger.error("Gemini chat failed: %s", exc)
        raise


def gemini_generate_json(system: str, user: str, max_tokens: int = 2048) -> str:
    _ensure_configured()
    import google.generativeai as genai

    model = genai.GenerativeModel(
        settings.gemini_model,
        system_instruction=system,
    )
    try:
        response = model.generate_content(
            user,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        return _response_text(response)
    except Exception as exc:
        logger.error("Gemini JSON generation failed: %s", exc)
        raise
