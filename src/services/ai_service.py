"""Entry points used by the UI: run an analysis, answer a follow-up question."""
import os
from typing import List, Optional, Tuple

import streamlit as st

from agents.analysis_agent import AnalysisAgent
from agents.chat_agent import ChatAgent
from agents.model_manager import ModelManager


def _secret(name: str) -> Optional[str]:
    try:
        value = st.secrets.get(name)
    except Exception:  # no secrets.toml present
        value = None
    return value or os.environ.get(name)


def _api_key() -> Optional[str]:
    key = _secret("GROQ_API_KEY")
    return key.strip() if key else None


def _model_override() -> Optional[Tuple[str, ...]]:
    raw = _secret("GROQ_MODELS")
    models = tuple(m.strip() for m in raw.split(",") if m.strip()) if raw else ()
    return models or None


@st.cache_resource(show_spinner=False)
def _manager_for(key: str, models: Optional[Tuple[str, ...]]) -> ModelManager:
    return ModelManager(key, list(models) if models else None)


def get_model_manager() -> Optional[ModelManager]:
    key = _api_key()
    return _manager_for(key, _model_override()) if key else None


def has_api_key() -> bool:
    return bool(_api_key())


def test_connection() -> Tuple[bool, str]:
    """Send a tiny request through the cascade; return (ok, human-readable message)."""
    mm = get_model_manager()
    if mm is None:
        return False, "No GROQ_API_KEY found. Add it to .streamlit/secrets.toml and restart."
    try:
        _, model = mm.complete([{"role": "user", "content": "Reply with the word OK."}], max_tokens=200)
        return True, f"Connected. Model used: {model}"
    except Exception as exc:
        return False, str(exc)


def analyze_report(report_text: str, patient: dict, previous: Optional[List[str]] = None) -> dict:
    return AnalysisAgent(get_model_manager()).analyze(report_text, patient, previous)


@st.cache_resource(show_spinner=False, max_entries=20)
def _cached_chat_agent(session_id: int, report_text: str, analysis_text: str) -> ChatAgent:
    """Search index is built once per session and reused across reruns."""
    return ChatAgent(report_text, analysis_text)


def answer_followup(session: dict, question: str, history: List[dict]) -> str:
    agent = _cached_chat_agent(session["id"], session["report_text"], session["analysis"] or "")
    agent.mm = get_model_manager()
    return agent.answer(question, history)
