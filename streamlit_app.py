"""Root entry point so Streamlit Cloud can auto-detect the app.

Deploy with main file = streamlit_app.py (or src/main.py, both work).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from main import run  # noqa: E402

run()
