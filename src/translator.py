from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from google import genai

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationResult:
    text_vi: str
    used_fallback: bool = False
    error: Optional[str] = None


class GeminiTranslator:
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash-002") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def translate_to_vietnamese(self, text: str, context: str = "football news") -> TranslationResult:
        text = (text or "").strip()
        if not text:
            return TranslationResult(text_vi="", used_fallback=False)

        prompt = (
            "Translate the following football news text to Vietnamese.\n"
            "- Keep proper names, team names, player names, and scores as-is.\n"
            "- Keep URLs unchanged.\n"
            "- Keep it concise and natural.\n"
            f"- Context: {context}\n\n"
            "Text:\n"
            f"{text}\n"
        )

        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                resp = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )
                out = (getattr(resp, "text", None) or "").strip()
                if not out:
                    raise RuntimeError("Empty translation response")
                return TranslationResult(text_vi=out, used_fallback=False)
            except Exception as e:
                last_err = e
                logger.warning("Gemini translate failed attempt=%s err=%s", attempt, e)
                time.sleep(min(2**attempt, 8))

        return TranslationResult(text_vi=text, used_fallback=True, error=str(last_err) if last_err else "unknown_error")
