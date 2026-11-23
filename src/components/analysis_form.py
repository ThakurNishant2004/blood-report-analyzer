"""New-analysis form: choose report source, enter patient details, run analysis."""
from datetime import datetime

import streamlit as st

from auth import auth_service, session_manager
from config.app_config import DAILY_ANALYSIS_LIMIT, MAX_PDF_PAGES, MAX_UPLOAD_MB
from config.sample_data import SAMPLE_REPORT
from services import ai_service
from utils.pdf_extractor import PDFError, extract_text_from_pdf


def render_analysis_form(user: dict) -> None:
    st.subheader("New analysis")

    remaining = auth_service.remaining_analyses(user["id"])
    if remaining == 0:
        st.error(f"Daily limit of {DAILY_ANALYSIS_LIMIT} analyses reached. Please come back tomorrow.")
        return

    source = st.radio("Report source", ["Upload PDF", "Use sample report"], horizontal=True)

    uploaded = None
    if source == "Upload PDF":
        uploaded = st.file_uploader(f"Blood report (PDF, up to {MAX_UPLOAD_MB} MB / {MAX_PDF_PAGES} pages)",
                                    type=["pdf"])
    else:
        with st.expander("Preview sample report"):
            st.code(SAMPLE_REPORT, language=None)

    st.markdown("**Patient details**")
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", min_value=1, max_value=120, value=30)
    gender = c2.selectbox("Gender", ["Male", "Female", "Other / prefer not to say"])
    notes = st.text_area("Symptoms or medicines (optional)", placeholder="e.g. feeling tired, taking iron tablets")

    if not st.button("🔍 Analyze report", type="primary"):
        return

    # 1) get report text
    if source == "Upload PDF":
        if uploaded is None:
            st.warning("Please upload a PDF first.")
            return
        try:
            report_text, pages = extract_text_from_pdf(uploaded.getvalue())
        except PDFError as exc:
            st.error(str(exc))
            return
        title = f"{uploaded.name[:24]} · {datetime.now():%d %b %H:%M}"
    else:
        report_text = SAMPLE_REPORT
        title = f"Sample report · {datetime.now():%d %b %H:%M}"

    # 2) analyze
    patient = {"age": int(age), "gender": gender, "notes": notes.strip()}
    with st.spinner("Analyzing your report... this can take 10-20 seconds"):
        result = ai_service.analyze_report(report_text, patient, auth_service.recent_analyses(user["id"]))

    st.session_state.last_ai_error = result.get("error")

    # 3) store + open
    session_id = auth_service.create_session(
        user["id"], title, report_text, patient, result["analysis"], result["model"])
    auth_service.log_analysis(user["id"])
    session_manager.open_session(session_id)
    st.rerun()
