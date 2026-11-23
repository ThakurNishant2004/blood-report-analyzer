"""Groq multi-model cascade: try models in order until one succeeds."""
from typing import List, Optional, Tuple

from config.app_config import ANALYSIS_MODELS


class ModelManager:
    def __init__(self, api_key: str, models: Optional[List[str]] = None):
        from groq import Groq  # imported lazily so the app can start without a key

        self.client = Groq(api_key=api_key)
        self.models = models or ANALYSIS_MODELS

    def complete(
        self,
        messages: List[dict],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        models: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        """Return (text, model_used). Raises RuntimeError if every model fails."""
        errors = []
        for model in models or self.models:
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = resp.choices[0].message.content
                if text and text.strip():
                    return text, model
                errors.append(f"{model}: empty response")
            except Exception as exc:  # rate limit, model removed, network...
                errors.append(f"{model}: {str(exc)[:220]}")
        raise RuntimeError("All models failed -> " + " | ".join(errors))
