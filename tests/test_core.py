"""Quick checks for the core logic. Run:  python tests/test_core.py   (or: pytest)"""
import os
import sys
import tempfile

os.environ["HIA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from agents.chat_agent import ChatAgent  # noqa: E402
from agents.knowledge_base import abnormal, extract_findings, rule_based_report  # noqa: E402
from auth import auth_service  # noqa: E402
from auth.database import init_db  # noqa: E402
from config.sample_data import SAMPLE_REPORT  # noqa: E402
from utils.validators import validate_email, validate_medical_content, validate_password  # noqa: E402


def test_validators():
    assert validate_email("a@b.com")[0]
    assert not validate_email("nope")[0]
    assert validate_password("abcdef12")[0]
    assert not validate_password("short1")[0]
    assert not validate_password("onlyletters")[0]
    assert validate_medical_content(SAMPLE_REPORT)[0]
    assert not validate_medical_content("Shopping list: milk, eggs, bread")[0]


def test_extraction_on_sample():
    f = {x["key"]: x for x in extract_findings(SAMPLE_REPORT, "Male")}
    assert f["hb"]["value"] == 11.2 and f["hb"]["status"] == "Low"
    assert f["hba1c"]["value"] == 6.1 and f["hba1c"]["status"] == "High"
    assert f["ldl"]["status"] == "High" and f["hdl"]["status"] == "Low"
    assert f["vitd"]["value"] == 14.5 and f["vitd"]["status"] == "Low"
    assert f["b12"]["status"] == "Low"
    assert f["wbc"]["status"] == "Normal" and f["plt"]["status"] == "Normal"
    assert f["tsh"]["status"] == "Normal"
    assert f["alt"]["value"] == 52 and f["alt"]["status"] == "High"
    assert f["tc"]["value"] == 228  # not confused with LDL/HDL lines


def test_gender_specific_range():
    text = "Hemoglobin 12.5 g/dL"
    assert extract_findings(text, "Male")[0]["status"] == "Low"
    assert extract_findings(text, "Female")[0]["status"] == "Normal"


def test_offline_report():
    findings = extract_findings(SAMPLE_REPORT, "Male")
    report = rule_based_report(findings)
    assert "Key Findings" in report and len(abnormal(findings)) >= 8


def test_auth_sessions_and_limit():
    init_db()
    ok, _ = auth_service.register_user("Test User", "t@example.com", "password1")
    assert ok
    assert not auth_service.register_user("Test User", "t@example.com", "password1")[0]  # duplicate
    assert auth_service.authenticate("t@example.com", "wrongpass1") is None
    user = auth_service.authenticate("T@Example.com", "password1")
    assert user and user["name"] == "Test User"

    sid = auth_service.create_session(user["id"], "t", SAMPLE_REPORT, {"gender": "Male"}, "analysis", "m")
    assert auth_service.get_session(sid, user["id"]) is not None
    assert auth_service.get_session(sid, user["id"] + 99) is None  # ownership enforced
    auth_service.add_message(sid, "user", "hi")
    assert auth_service.get_messages(sid)[0]["content"] == "hi"
    assert auth_service.recent_analyses(user["id"])

    before = auth_service.remaining_analyses(user["id"])
    auth_service.log_analysis(user["id"])
    assert auth_service.remaining_analyses(user["id"]) == before - 1
    assert auth_service.seconds_until_reset() > 0

    auth_service.delete_session(sid, user["id"])
    assert auth_service.get_session(sid, user["id"]) is None
    assert auth_service.get_messages(sid) == []  # cascade delete


def test_chat_retrieval():
    agent = ChatAgent(SAMPLE_REPORT, "Hemoglobin is low which may indicate anaemia.")
    top = " ".join(agent.retrieve("What is my LDL cholesterol?"))
    assert "LDL" in top
    ans = agent.answer("Why is hemoglobin low?")  # offline mode (no model manager)
    assert "Offline mode" in ans


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
