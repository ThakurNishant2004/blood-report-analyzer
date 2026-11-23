"""Input validation: email, password, PDF file and medical content."""
import re
from typing import Tuple

import filetype

from config.app_config import MAX_UPLOAD_MB

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

MEDICAL_KEYWORDS = [
    "hemoglobin", "haemoglobin", "cholesterol", "glucose", "creatinine", "platelet",
    "wbc", "rbc", "hdl", "ldl", "triglyceride", "tsh", "bilirubin", "sgpt", "sgot",
    "hba1c", "vitamin", "reference range", "blood", "serum", "urea", "lipid",
    "thyroid", "hematocrit", "mcv", "pathology", "laboratory",
]


def validate_email(email: str) -> Tuple[bool, str]:
    if not email or not EMAIL_RE.match(email.strip()):
        return False, "Please enter a valid email address."
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return False, "Password must contain at least one letter and one number."
    return True, ""


def validate_pdf_file(data: bytes) -> Tuple[bool, str]:
    """Check size and that the bytes really are a PDF (not just the extension)."""
    if not data:
        return False, "The uploaded file is empty."
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        return False, f"File is larger than {MAX_UPLOAD_MB} MB."
    kind = filetype.guess(data)
    if kind is None or kind.mime != "application/pdf":
        return False, "Only PDF files are supported."
    return True, ""


def validate_medical_content(text: str) -> Tuple[bool, str]:
    """A report should mention at least 3 known medical terms."""
    lowered = (text or "").lower()
    hits = sum(1 for k in MEDICAL_KEYWORDS if k in lowered)
    if hits < 3:
        return False, "This does not look like a blood/medical report. Please upload a lab report PDF."
    return True, ""
