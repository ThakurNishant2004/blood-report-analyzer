"""Chat Agent: lightweight RAG (pure-Python TF-IDF retrieval) over the report and its analysis.

No scikit-learn / SciPy needed, so it also runs on locked-down machines that block compiled DLLs.
"""
import math
import re
from collections import Counter
from typing import Dict, List, Optional

from agents.model_manager import ModelManager
from config.app_config import CHAT_MODELS
from config.prompts import CHAT_SYSTEM_PROMPT

STOPWORDS = set(
    "a an and are as at be by for from has have how i in is it its me my of on or that the this to "
    "was what when where which who why will with you your do does can should about".split()
)


def split_text(text: str, size: int = 600, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks, preferring line boundaries."""
    chunks, current = [], ""
    for line in (text or "").splitlines():
        if len(current) + len(line) + 1 > size and current:
            chunks.append(current.strip())
            current = current[-overlap:] if overlap else ""
        current += line + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _terms(text: str) -> List[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]  # unigrams + bigrams


class ChatAgent:
    def __init__(self, report_text: str, analysis_text: str, model_manager: Optional[ModelManager] = None):
        self.mm = model_manager
        self.chunks = (
            [f"[Report] {c}" for c in split_text(report_text)]
            + [f"[Analysis] {c}" for c in split_text(analysis_text)]
        )
        counts = [Counter(_terms(c)) for c in self.chunks]
        df = Counter(t for c in counts for t in c)
        n = len(self.chunks)
        self.idf: Dict[str, float] = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}
        self.vectors = [self._normalize(c) for c in counts]

    def _normalize(self, counts: Counter) -> Dict[str, float]:
        vec = {t: tf * self.idf[t] for t, tf in counts.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def retrieve(self, query: str, k: int = 4) -> List[str]:
        q = self._normalize(Counter(_terms(query)))
        if not q or not self.chunks:
            return self.chunks[:k]
        scores = [sum(w * v.get(t, 0.0) for t, w in q.items()) for v in self.vectors]
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.chunks[i] for i in top if scores[i] > 0] or self.chunks[:k]

    @staticmethod
    def contextualize(question: str, history: List[dict]) -> str:
        """Short follow-ups ('and what about it?') borrow the previous question for retrieval."""
        if len(question.split()) < 6:
            prev = [m["content"] for m in history if m["role"] == "user"]
            if prev:
                return f"{prev[-1]} {question}"
        return question

    def answer(self, question: str, history: Optional[List[dict]] = None) -> str:
        history = history or []
        context_chunks = self.retrieve(self.contextualize(question, history))

        if self.mm is None:
            return ("**Offline mode** (no API key). Most relevant parts of your report:\n\n"
                    + "\n\n".join(f"> {c}" for c in context_chunks[:3]))

        context = "\n\n".join(context_chunks)
        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        for m in history[-6:]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user",
                         "content": f"Context from the report:\n{context}\n\nQuestion: {question}"})
        try:
            text, _ = self.mm.complete(messages, temperature=0.2, max_tokens=2000, models=CHAT_MODELS)
            return text
        except Exception as exc:
            return ("Sorry, the AI service is unavailable right now. Relevant parts of your report:\n\n"
                    + "\n\n".join(f"> {c}" for c in context_chunks[:3])
                    + f"\n\n`Reason: {str(exc)[:300]}`")
