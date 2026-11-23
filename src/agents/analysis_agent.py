"""Analysis Agent: knowledge-base pre-screening + LLM report + in-context learning."""
from typing import List, Optional

from agents.knowledge_base import extract_findings, findings_to_markdown, rule_based_report
from agents.model_manager import ModelManager
from config.app_config import MAX_REPORT_CHARS
from config.prompts import ANALYSIS_SYSTEM_PROMPT


def build_messages(report_text: str, patient: dict, table_md: str, previous: Optional[List[str]]) -> List[dict]:
    patient_block = (
        f"Age: {patient.get('age', 'not given')}\n"
        f"Gender: {patient.get('gender', 'not given')}\n"
        f"Notes (symptoms/medicines): {patient.get('notes') or 'none'}"
    )
    # In-context learning: earlier analyses of the same user give trend context.
    prev_block = ""
    if previous:
        prev_block = ("\n\nEarlier analyses for this user (use only for trend comparison, "
                      "do not repeat them):\n" + "\n---\n".join(previous))
    user_msg = (
        f"Patient details:\n{patient_block}\n\n"
        f"Pre-screened values from the built-in knowledge base:\n{table_md}"
        f"{prev_block}\n\n"
        f'Blood report text:\n"""\n{report_text[:MAX_REPORT_CHARS]}\n"""'
    )
    return [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


class AnalysisAgent:
    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.mm = model_manager

    def analyze(self, report_text: str, patient: dict, previous: Optional[List[str]] = None) -> dict:
        findings = extract_findings(report_text, patient.get("gender"))

        if self.mm is None:
            note = "Offline mode: no GROQ_API_KEY configured, so this analysis uses the built-in knowledge base only."
            return {"analysis": rule_based_report(findings, note), "model": "knowledge-base", "findings": findings}

        messages = build_messages(report_text, patient, findings_to_markdown(findings), previous)
        try:
            text, model = self.mm.complete(messages, temperature=0.3, max_tokens=4096)
            return {"analysis": text, "model": model, "findings": findings}
        except Exception as exc:
            note = "The AI models were unreachable, so this analysis uses the built-in knowledge base only."
            return {
                "analysis": rule_based_report(findings, note),
                "model": "knowledge-base",
                "findings": findings,
                "error": str(exc),
            }
