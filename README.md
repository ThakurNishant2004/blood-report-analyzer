# 🩺 HIA - Health Insights Agent

An AI agent that reads a blood-test report (PDF), explains it in plain language, and lets you ask follow-up questions about it.
Built with **Streamlit + Groq (Llama models) + SQLite**, and deployable on Streamlit Community Cloud in minutes.

> ⚠️ Educational project. It does not give medical advice.

## 🌟 Features

| Area | What it does |
|---|---|
| **Analysis Agent** | Built-in knowledge base (22 common tests, gender-specific ranges) pre-screens values, then the LLM writes the report. Uses the user's previous analyses as in-context examples for trend awareness. |
| **Chat Agent (RAG)** | Follow-up Q&A: the report and analysis are chunked, indexed with a pure-Python TF-IDF (no SciPy/scikit-learn needed) and the best chunks are sent to the LLM as context. |
| **Multi-model cascade** | Groq models are tried in order: `gpt-oss-120b` → `gpt-oss-20b` → `qwen3.8-27b` (Groq retires models often, so override them with `GROQ_MODELS = "a, b"` in secrets). If all fail, the app falls back to the knowledge base, so it never crashes during a demo. |
| **Sessions** | Every analysis is a saved session (report, analysis, chat history); view, switch and delete past sessions. |
| **Auth** | Sign up / sign in (PBKDF2-hashed passwords), inactivity timeout (60 min), users can only open their own sessions. |
| **PDF handling** | Max 20 MB / 50 pages, real file-type check (not just the extension), checks the PDF actually looks like a medical report. |
| **Daily limit** | 15 analyses/day per user with progress bar and reset countdown. |
| **Sample report** | One click demo without needing a PDF (`public/sample_report.pdf` is also included for upload testing). |
| **Offline mode** | Works without any API key (knowledge-base analysis only) - handy if the internet fails on review day. |

## 🧱 Architecture

```
PDF / Sample ─► pdf_extractor ─► Analysis Agent ──► Groq (ModelManager cascade)
                                   │  ▲                     │
                     knowledge_base│  │previous analyses    ▼
                     (ranges,      │  └──────────── SQLite (users, sessions, messages, usage)
                      rule report) ▼
                              Session saved ──► Chat Agent (TF-IDF retrieval ─► Groq)
```

## 🚀 Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then paste your Groq key
streamlit run streamlit_app.py
```
Get a free Groq key at <https://console.groq.com/keys>. Without a key the app runs in offline mode.

## ☁️ Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Go to <https://share.streamlit.io> → **New app** → pick the repo, branch `main`, main file `streamlit_app.py`.
3. **Advanced settings → Secrets**, paste: `GROQ_API_KEY = "your-key"`
4. Deploy. Done.

> **Note:** Streamlit Cloud storage is ephemeral, so the SQLite file (accounts and sessions) resets when the app restarts or redeploys. That is fine for a demo; for production you would swap `src/auth/database.py` for a hosted database such as Supabase/PostgreSQL.

## 📁 Project structure

```
hia/
├── streamlit_app.py            # root entry point (used for deployment)
├── requirements.txt
├── README.md
├── .streamlit/
│   ├── config.toml             # theme, upload size
│   └── secrets.toml.example    # GROQ_API_KEY template
├── public/sample_report.pdf    # sample PDF to test uploads
├── tests/test_core.py          # unit tests (python tests/test_core.py)
└── src/
    ├── main.py                 # app flow: auth → sidebar → form / session view
    ├── auth/
    │   ├── database.py         # SQLite schema + helpers
    │   ├── auth_service.py     # users, sessions, messages, daily usage
    │   └── session_manager.py  # login state, timeout, open/delete session
    ├── agents/
    │   ├── knowledge_base.py   # reference ranges, value extraction, offline report
    │   ├── analysis_agent.py   # prompt building, in-context learning, fallback
    │   ├── chat_agent.py       # RAG: chunking, TF-IDF retrieval, answer
    │   └── model_manager.py    # Groq multi-model cascade
    ├── services/ai_service.py  # entry points + cached index/clients
    ├── components/             # auth_pages, sidebar, header, footer, analysis_form
    ├── config/                 # app_config, prompts, sample_data
    └── utils/                  # validators, pdf_extractor
```

## 🎤 2-minute demo script for the reviewer

1. Create an account and sign in.
2. **New analysis → Use sample report → Analyze.** Point out the table of values with 🔴/🟡/🟢 status, then the AI report.
3. Ask a follow-up: *"Why is my hemoglobin low?"* and *"What should I eat for high LDL?"* (RAG chat).
4. Upload `public/sample_report.pdf`, then try a non-medical PDF to show validation.
5. Show the sidebar: session history, daily limit counter, delete session.

## ❓ Likely viva questions

- **Why an "agent"?** Two cooperating agents with their own tools: analysis (knowledge base + LLM) and chat (retriever + LLM), with automatic fallback behaviour.
- **What is RAG here?** Retrieve the most relevant report chunks (TF-IDF cosine similarity), then generate the answer from only that context, which reduces hallucination.
- **Why a model cascade?** Free-tier rate limits and deprecations; the next model is used automatically.
- **How is data secured?** Salted PBKDF2 password hashes, per-user session ownership checks, upload validation, inactivity timeout.
- **Limitations / future work:** no scanned-PDF OCR, ranges are general adult ranges, ephemeral demo storage; future work is OCR, hosted DB, trend charts across reports.

## 🧪 Tests

```bash
python tests/test_core.py
```
