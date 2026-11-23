"""Sidebar: new analysis, session history, daily limit, logout."""
import streamlit as st

from auth import auth_service, session_manager
from config.app_config import APP_ICON, APP_NAME, DAILY_ANALYSIS_LIMIT
from services.ai_service import has_api_key, test_connection


def render_sidebar(user: dict) -> None:
    with st.sidebar:
        st.markdown(f"### {APP_ICON} {APP_NAME}")
        st.write(f"👤 **{user['name']}**")

        if st.button("➕ New analysis", width="stretch", type="primary"):
            session_manager.new_analysis()
            st.rerun()

        st.markdown("#### Your sessions")
        sessions = auth_service.list_sessions(user["id"])
        if not sessions:
            st.caption("No sessions yet.")
        for s in sessions:
            col_open, col_del = st.columns([5, 1])
            is_current = st.session_state.current_session_id == s["id"]
            label = ("📂 " if is_current else "📄 ") + s["title"]
            if col_open.button(label, key=f"open_{s['id']}", width="stretch"):
                session_manager.open_session(s["id"])
                st.rerun()
            if col_del.button("🗑", key=f"del_{s['id']}", help="Delete session"):
                session_manager.remove_session(s["id"])
                st.rerun()

        st.divider()
        used = auth_service.analyses_today(user["id"])
        st.progress(min(used / DAILY_ANALYSIS_LIMIT, 1.0))
        hours, rem = divmod(auth_service.seconds_until_reset(), 3600)
        st.caption(f"Analyses today: {used}/{DAILY_ANALYSIS_LIMIT} · resets in {hours}h {rem // 60}m (UTC)")
        st.caption("🔑 API key found" if has_api_key() else "🟡 Offline mode (no API key)")
        if has_api_key() and st.button("Test AI connection", width="stretch"):
            with st.spinner("Testing..."):
                ok, msg = test_connection()
            (st.success if ok else st.error)(msg)

        if st.button("Log out", width="stretch"):
            session_manager.logout()
            st.rerun()
