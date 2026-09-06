"""
backend/api/models.py
─────────────────────────────────────────────────────────────────────────────
Pydantic request/response models for the FastAPI endpoints.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── /profile ─────────────────────────────────────────────────────────────

class ProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    experience_level: Literal["Fresher", "Mid", "Senior"]
    job_role: str = Field(..., min_length=1, max_length=120)
    job_title: str | None = Field(default=None, max_length=200)


class ProfileResponse(BaseModel):
    status: str
    name: str
    experience_level: str
    job_role: str
    skills_extracted: list[str]


# ── /generate ────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    experience_level: Literal["Fresher", "Mid", "Senior"]
    job_role: str = Field(..., min_length=1, max_length=120)
    skills: list[str] = Field(default_factory=list)


class QuestionItem(BaseModel):
    question: str
    model_answer: str
    tip: str


class ReadinessAssessment(BaseModel):
    score: float = Field(..., ge=0, le=10)
    recommendations: list[str]


class GenerateResponse(BaseModel):
    technical: list[QuestionItem]
    behavioral: list[QuestionItem]
    readiness: ReadinessAssessment


# ── /health ───────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    vector_store: str
    watsonx_configured: bool
