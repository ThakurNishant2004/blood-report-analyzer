"""Central configuration: names, limits and model lists."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

APP_NAME = "HIA"
APP_FULL_NAME = "Health Insights Agent"
APP_ICON = "🩺"

# Upload / PDF limits
MAX_UPLOAD_MB = 20
MAX_PDF_PAGES = 50

# Usage limits
DAILY_ANALYSIS_LIMIT = 15
SESSION_TIMEOUT_MINUTES = 60

# Storage (SQLite file; on Streamlit Cloud this is ephemeral, see README)
DB_PATH = os.environ.get("HIA_DB_PATH", os.path.join(BASE_DIR, "data", "hia.db"))

# Groq model cascade: tried in this order until one succeeds
# Groq retires models often (the old Llama ones are shut down), so the list can be
# overridden without touching code: set  GROQ_MODELS = "model-a, model-b"  in secrets.toml.
# Current names: https://console.groq.com/docs/models
ANALYSIS_MODELS = [
    "openai/gpt-oss-120b",   # primary
    "openai/gpt-oss-20b",    # secondary
    "qwen/qwen3.8-27b",      # tertiary
]
CHAT_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]

# Max characters of report text sent to the LLM
MAX_REPORT_CHARS = 12000
