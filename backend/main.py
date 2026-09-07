"""
backend/main.py
─────────────────────────────────────────────────────────────────────────────
FastAPI application entry point.

Run with:
    cd backend
    uvicorn main:app --reload --port 8000
─────────────────────────────────────────────────────────────────────────────
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

app = FastAPI(
    title="Interview Trainer Agent API",
    description="RAG-powered interview preparation backend using watsonx.ai",
    version="1.0.0",
)

# ALLOWED_ORIGINS env var: comma-separated list of allowed origins.
# e.g. "https://your-app.vercel.app,http://localhost:5173"
_raw = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
)
origins = [o.strip() for o in _raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Interview Trainer Agent API is running. See /docs for the API reference."}
