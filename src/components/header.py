"""Top-of-page greeting."""
from datetime import datetime

import streamlit as st

from config.app_config import APP_FULL_NAME, APP_ICON


def render_header(user: dict) -> None:
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    st.title(f"{APP_ICON} {APP_FULL_NAME}")
    st.caption(f"{greeting}, {user['name']}! Upload a blood report to get a plain-language analysis.")
