"""Login / Sign-up page."""
import streamlit as st

from auth import auth_service, session_manager
from config.app_config import APP_FULL_NAME, APP_ICON, APP_NAME


def render_auth_page() -> None:
    st.markdown(f"<h1 style='text-align:center'>{APP_ICON} {APP_NAME}</h1>"
                f"<p style='text-align:center'>{APP_FULL_NAME} - understand your blood report in minutes</p>",
                unsafe_allow_html=True)

    if st.session_state.get("timed_out"):
        st.warning("You were signed out due to inactivity. Please sign in again.")

    _, col, _ = st.columns([1, 2, 1])
    with col:
        login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", width="stretch")
            if submitted:
                user = auth_service.authenticate(email, password)
                if user:
                    session_manager.login(user)
                    st.rerun()
                else:
                    st.error("Incorrect email or password.")

        with signup_tab:
            with st.form("signup_form"):
                name = st.text_input("Full name")
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Password (min 8 chars, letters + numbers)",
                                         type="password", key="signup_password")
                submitted = st.form_submit_button("Create account", width="stretch")
            if submitted:
                ok, msg = auth_service.register_user(name, email, password)
                (st.success if ok else st.error)(msg)
