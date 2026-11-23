"""Streamlit session-state helpers: login state, timeout, current chat session."""
import time

import streamlit as st

from auth import auth_service
from config.app_config import SESSION_TIMEOUT_MINUTES


def init_state() -> None:
    for key, default in {"user": None, "last_active": None, "current_session_id": None,
                         "timed_out": False}.items():
        st.session_state.setdefault(key, default)


def login(user: dict) -> None:
    st.session_state.user = user
    st.session_state.current_session_id = None
    st.session_state.timed_out = False
    touch()


def touch() -> None:
    st.session_state.last_active = time.time()


def logout(timed_out: bool = False) -> None:
    for key in ("user", "last_active", "current_session_id"):
        st.session_state[key] = None
    st.session_state.timed_out = timed_out


def enforce_timeout() -> bool:
    """Log the user out after SESSION_TIMEOUT_MINUTES of inactivity. Returns True if logged out."""
    last = st.session_state.get("last_active")
    if st.session_state.get("user") and last and time.time() - last > SESSION_TIMEOUT_MINUTES * 60:
        logout(timed_out=True)
        return True
    touch()
    return False


def new_analysis() -> None:
    st.session_state.current_session_id = None


def open_session(session_id: int) -> None:
    st.session_state.current_session_id = session_id


def remove_session(session_id: int) -> None:
    user = st.session_state.user
    auth_service.delete_session(session_id, user["id"])
    if st.session_state.current_session_id == session_id:
        st.session_state.current_session_id = None
