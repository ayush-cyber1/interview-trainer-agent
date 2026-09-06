"""
backend/resume_parser/parser.py
─────────────────────────────────────────────────────────────────────────────
Accepts an uploaded file (PDF or DOCX) and returns extracted plain text
plus a lightweight skills/title list used to enrich the retrieval query.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import io
import re
from pathlib import Path

# ── common tech/domain skill keywords for quick extraction ────────────────
_SKILL_KEYWORDS = {
    # Languages / runtimes
    "python", "java", "javascript", "typescript", "golang", "rust", "c++", "c#",
    "ruby", "php", "swift", "kotlin", "scala", "r",
    # Web / frameworks
    "react", "angular", "vue", "next.js", "fastapi", "django", "flask", "spring",
    "express", "node.js", "nodejs",
    # Data
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "spark", "hadoop", "kafka", "airflow", "dbt", "pandas", "numpy",
    # Cloud / DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd",
    "jenkins", "github actions",
    # ML / AI
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
    "scikit-learn", "llm", "rag",
    # Soft / domain
    "agile", "scrum", "jira", "product management", "data analysis",
    "stakeholder management", "a/b testing",
}


def _extract_skills(text: str) -> list[str]:
    lower = text.lower()
    found = []
    for kw in _SKILL_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, lower):
            found.append(kw)
    return sorted(found)


def parse_pdf(file_bytes: bytes) -> str:
    """Extract raw text from a PDF byte stream."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pypdf is not installed. Run: pip install pypdf") from exc

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def parse_docx(file_bytes: bytes) -> str:
    """Extract raw text from a DOCX byte stream."""
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "python-docx is not installed. Run: pip install python-docx"
        ) from exc

    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs)


def parse_resume(file_bytes: bytes, filename: str) -> dict:
    """
    Parse a resume file and return:
        {
            "raw_text": str,
            "skills": list[str],
            "error": str | None,
        }
    """
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            text = parse_pdf(file_bytes)
        elif suffix in (".docx", ".doc"):
            text = parse_docx(file_bytes)
        else:
            return {
                "raw_text": "",
                "skills": [],
                "error": f"Unsupported file type '{suffix}'. Please upload a PDF or DOCX.",
            }
        skills = _extract_skills(text)
        return {"raw_text": text, "skills": skills, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"raw_text": "", "skills": [], "error": str(exc)}
