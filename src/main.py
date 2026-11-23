"""HIA - Health Insights Agent. Streamlit entry point.

Run locally:  streamlit run src/main.py   (or: streamlit run streamlit_app.py)
"""
import json
import os
import sys

# Make "src" importable no matter how Streamlit launches the script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st  # noqa: E402

from agents.knowledge_base import abnormal, extract_findings  # noqa: E402
from auth import auth_service, session_manager  # noqa: E402
from auth.database import init_db  # noqa: E402
from components.analysis_form import render_analysis_form  # noqa: E402
from components.auth_pages import render_auth_page  # noqa: E402
from components.footer import render_footer  # noqa: E402
from components.header import render_header  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402
from config.app_config import APP_FULL_NAME, APP_ICON  # noqa: E402
from services import ai_service  # noqa: E402

STATUS_ICON = {"Normal": "🟢 Normal", "Low": "🟡 Low", "High": "🔴 High"}


def render_session(user: dict, session: dict) -> None:
    st.subheader(session["title"])
    patient = json.loads(session["patient_info"] or "{}")
    findings = extract_findings(session["report_text"], patient.get("gender"))

    if findings:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tests detected", len(findings))
        c2.metric("Out of range", len(abnormal(findings)))
        c3.metric("Analysed by", session.get("model_used") or "-")
        st.dataframe(
            [{"Test": f["name"], "Value": f"{f['value']:g} {f['unit']}",
              "Reference": f["reference"], "Status": STATUS_ICON[f["status"]]} for f in findings],
            width="stretch", hide_index=True,
        )

    if session.get("model_used") == "knowledge-base" and st.session_state.get("last_ai_error"):
        with st.expander("Why was the AI unavailable?"):
            st.code(st.session_state.last_ai_error, language=None)
    st.markdown(session["analysis"] or "_No analysis stored._")
    st.download_button("⬇️ Download analysis (.md)", session["analysis"] or "",
                       file_name="hia_analysis.md", mime="text/markdown")
    with st.expander("📄 Extracted report text"):
        st.text(session["report_text"])

    # ---- follow-up chat (RAG) ----
    st.divider()
    st.subheader("💬 Ask follow-up questions")
    history = auth_service.get_messages(session["id"])
    for m in history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    question = st.chat_input("e.g. Why is my hemoglobin low? What should I eat?")
    if question:
        auth_service.add_message(session["id"], "user", question)
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = ai_service.answer_followup(session, question, history)
            st.markdown(answer)
        auth_service.add_message(session["id"], "assistant", answer)


def run() -> None:
    st.set_page_config(page_title=f"{APP_FULL_NAME}", page_icon=APP_ICON, layout="wide")
    init_db()
    session_manager.init_state()

    if not st.session_state.user:
        render_auth_page()
        render_footer()
        return

    if session_manager.enforce_timeout():
        st.rerun()

    user = st.session_state.user
    render_sidebar(user)
    render_header(user)

    session_id = st.session_state.current_session_id
    session = auth_service.get_session(session_id, user["id"]) if session_id else None
    if session:
        render_session(user, session)
    else:
        render_analysis_form(user)
    render_footer()


if __name__ == "__main__":
    run()
