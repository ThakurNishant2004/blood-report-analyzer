"""PDF text extraction with validation (type, size, page count, content)."""
import io
from typing import Tuple

import pdfplumber

from config.app_config import MAX_PDF_PAGES
from utils.validators import validate_medical_content, validate_pdf_file


class PDFError(Exception):
    """Raised with a user-friendly message when a PDF cannot be used."""


def extract_text_from_pdf(data: bytes) -> Tuple[str, int]:
    ok, msg = validate_pdf_file(data)
    if not ok:
        raise PDFError(msg)

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = len(pdf.pages)
            if pages > MAX_PDF_PAGES:
                raise PDFError(f"PDF has {pages} pages; the maximum is {MAX_PDF_PAGES}.")
            text = "\n".join((p.extract_text() or "") for p in pdf.pages).strip()
    except PDFError:
        raise
    except Exception as exc:  # corrupt / encrypted file
        raise PDFError(f"Could not read this PDF ({exc}).") from exc

    if len(text) < 50:
        raise PDFError("No readable text found. Scanned (image-only) PDFs are not supported.")

    ok, msg = validate_medical_content(text)
    if not ok:
        raise PDFError(msg)
    return text, pages
