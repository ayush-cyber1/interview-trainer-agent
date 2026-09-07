"""
backend/api/routes.py
─────────────────────────────────────────────────────────────────────────────
FastAPI route definitions.

Endpoints:
  GET  /health          — liveness + config check
  POST /profile         — accept form + optional resume file, extract skills
  POST /generate        — run the full RAG pipeline, return Q&A + tips
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import settings
from generation.generator import generate_interview_prep
from resume_parser.parser import parse_resume
from retrieval.vector_store import retrieve

from .models import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ProfileResponse,
    QuestionItem,
    ReadinessAssessment,
)

router = APIRouter()

# ── session-level store (in-memory, per-process) ─────────────────────────
# Stores the last parsed skills so /generate can pick them up.
_session: dict[str, dict] = {}


# ─────────────────────────────────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    db_path = settings.VECTOR_STORE_PATH
    vector_store_status = "ok" if db_path.exists() else "not built — run build_vector_store.py"
    watsonx_ok = bool(settings.WATSONX_API_KEY and settings.WATSONX_PROJECT_ID and settings.WATSONX_URL)
    return HealthResponse(
        status="ok",
        vector_store=vector_store_status,
        watsonx_configured=watsonx_ok,
    )


# ─────────────────────────────────────────────────────────────────────────
# POST /profile
# ─────────────────────────────────────────────────────────────────────────

@router.post("/profile", response_model=ProfileResponse)
async def profile(
    name: str = Form(...),
    experience_level: str = Form(...),
    job_role: str = Form(...),
    job_title: str | None = Form(default=None),
    resume: UploadFile | None = File(default=None),
):
    skills: list[str] = []
    resume_error: str | None = None

    if resume and resume.filename:
        file_bytes = await resume.read()
        if not file_bytes:
            resume_error = "Uploaded file is empty."
        else:
            parsed = parse_resume(file_bytes, resume.filename)
            if parsed["error"]:
                resume_error = parsed["error"]
            else:
                skills = parsed["skills"]

    # Store in session keyed by name (simple; production would use a real session)
    _session[name] = {
        "name": name,
        "experience_level": experience_level,
        "job_role": job_role,
        "job_title": job_title,
        "skills": skills,
    }

    response = ProfileResponse(
        status="ok",
        name=name,
        experience_level=experience_level,
        job_role=job_role,
        skills_extracted=skills,
    )

    if resume_error:
        # Return a 207-style response with a warning in the body
        return JSONResponse(
            status_code=200,
            content={**response.model_dump(), "resume_warning": resume_error},
        )

    return response


# ─────────────────────────────────────────────────────────────────────────
# POST /generate
# ─────────────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    # Validate watsonx config up-front so error is clear
    if not settings.WATSONX_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="WATSONX_API_KEY is not configured. Fill in backend/.env and restart.",
        )
    if not settings.WATSONX_URL:
        raise HTTPException(
            status_code=503,
            detail="WATSONX_URL is not configured. Fill in backend/.env and restart.",
        )

    # Enrich skills from session if available
    session_data = _session.get(req.name, {})
    merged_skills = list(set(req.skills + session_data.get("skills", [])))

    # Build retrieval query
    query = f"{req.job_role} {req.experience_level} interview questions"
    if merged_skills:
        query += " " + " ".join(merged_skills[:10])

    try:
        chunks = retrieve(
            query=query,
            role=req.job_role,
            level=req.experience_level,
            top_k=settings.RETRIEVAL_TOP_K,
            embedding_model=settings.EMBEDDING_MODEL,
            db_path=settings.VECTOR_STORE_PATH,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Vector store error: {exc}. Have you run build_vector_store.py?",
        ) from exc

    try:
        result = generate_interview_prep(
            name=req.name,
            role=req.job_role,
            level=req.experience_level,
            skills=merged_skills,
            retrieved_chunks=chunks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation error: {exc}") from exc

    # Coerce into typed response
    def _to_qi(item: dict) -> QuestionItem:
        return QuestionItem(
            question=item.get("question", ""),
            model_answer=item.get("model_answer", ""),
            tip=item.get("tip", ""),
        )

    readiness_raw = result.get("readiness", {})
    return GenerateResponse(
        technical=[_to_qi(q) for q in result.get("technical", [])],
        behavioral=[_to_qi(q) for q in result.get("behavioral", [])],
        readiness=ReadinessAssessment(
            score=float(readiness_raw.get("score", 5)),
            recommendations=readiness_raw.get("recommendations", []),
        ),
    )
