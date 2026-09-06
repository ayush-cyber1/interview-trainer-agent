"""
backend/generation/generator.py
─────────────────────────────────────────────────────────────────────────────
Constructs the RAG prompt and calls watsonx.ai via the raw REST API (httpx).
The ONLY value that needs to change to swap models is WATSONX_MODEL_ID in .env.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import re

import httpx

from config import settings

# ── IAM token cache (simple in-memory, refreshed on 401) ─────────────────
_cached_token: str | None = None


def _get_iam_token() -> str:
    """Exchange the API key for a short-lived IAM bearer token."""
    global _cached_token
    if _cached_token:
        return _cached_token

    resp = httpx.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": settings.WATSONX_API_KEY,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    resp.raise_for_status()
    _cached_token = resp.json()["access_token"]
    return _cached_token


def _invalidate_token() -> None:
    global _cached_token
    _cached_token = None


def _build_prompt(
    name: str,
    role: str,
    level: str,
    skills: list[str],
    retrieved_chunks: list[dict],
) -> str:
    # Keep context concise — include question + short answer only to save tokens
    context_lines = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        context_lines.append(
            f"[{i}] ({chunk.get('type','')}, {chunk.get('level','')}) "
            f"Q: {chunk.get('question','')[:120]} "
            f"A: {chunk.get('model_answer','')[:120]}"
        )
    context = "\n".join(context_lines)

    skills_str = ", ".join(skills) if skills else "not specified"

    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert interview coach. You output ONLY raw JSON — no markdown, no explanation, no preamble, no trailing text.
<|eot_id|><|start_header_id|>user<|end_header_id|>

Generate an interview preparation set for this candidate.

CANDIDATE:
Name: {name} | Role: {role} | Level: {level} | Skills: {skills_str}

REFERENCE QUESTIONS (use as inspiration, adapt for this candidate):
{context}

OUTPUT RULES:
- Output ONLY the JSON object below. No text before or after it.
- Do NOT wrap in markdown code fences.
- Keep each model_answer to 2-3 sentences max.
- Keep each tip to 1 sentence max.

JSON SCHEMA (fill every field):
{{"technical":[{{"question":"...","model_answer":"...","tip":"..."}},{{"question":"...","model_answer":"...","tip":"..."}},{{"question":"...","model_answer":"...","tip":"..."}},{{"question":"...","model_answer":"...","tip":"..."}},{{"question":"...","model_answer":"...","tip":"..."}}],"behavioral":[{{"question":"...","model_answer":"...","tip":"..."}},{{"question":"...","model_answer":"...","tip":"..."}},{{"question":"...","model_answer":"...","tip":"..."}},{{"question":"...","model_answer":"...","tip":"..."}},{{"question":"...","model_answer":"...","tip":"..."}}],"readiness":{{"score":7,"recommendations":["...","...","..."]}}}}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
{{"""
    return prompt


def _call_watsonx(prompt: str) -> str:
    """POST to watsonx.ai generation endpoint. Returns the generated text."""
    if not settings.WATSONX_API_KEY:
        raise ValueError(
            "WATSONX_API_KEY is empty. Please fill in backend/.env before running."
        )
    if not settings.WATSONX_PROJECT_ID:
        raise ValueError(
            "WATSONX_PROJECT_ID is empty. Please fill in backend/.env before running."
        )
    if not settings.WATSONX_MODEL_ID:
        raise ValueError(
            "WATSONX_MODEL_ID is empty. Please fill in backend/.env before running."
        )
    if not settings.WATSONX_URL:
        raise ValueError(
            "WATSONX_URL is empty. Please fill in backend/.env before running."
        )

    token = _get_iam_token()

    payload = {
        "model_id": settings.WATSONX_MODEL_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 3500,
            "repetition_penalty": 1.05,
            "stop_sequences": [],
        },
        "project_id": settings.WATSONX_PROJECT_ID,
    }

    # WATSONX_URL is used exactly as provided in .env — no modifications
    url: str = settings.WATSONX_URL

    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=90,
        )

        if resp.status_code == 401:
            _invalidate_token()
            token = _get_iam_token()
            resp = httpx.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=90,
            )

        resp.raise_for_status()
        data = resp.json()
        return data["results"][0]["generated_text"]

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"watsonx.ai returned HTTP {exc.response.status_code}: {exc.response.text}"
        ) from exc


def _extract_outermost_json(text: str) -> str:
    """
    Find the outermost {...} block by bracket counting.
    More robust than a greedy regex — handles nested objects and
    LLM preamble/postamble text correctly.
    """
    start = text.find("{")
    if start == -1:
        return ""
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    # If we never closed, return everything from start (truncated JSON — try anyway)
    return text[start:]


def _parse_json_response(raw: str) -> dict:
    """
    Robustly extract and parse the JSON block from the LLM response.
    Handles:
      - Preamble text before the JSON
      - Markdown code fences (```json ... ```)
      - Truncated responses (attempts json.loads with repair)
      - Unicode escape issues
    """
    # 1. Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # 2. The prompt ends with `{` so the LLM continues from the first key.
    #    Detect "continuation" format: starts with `"technical"` or any JSON key
    #    (no leading `{`), and prepend the opening brace.
    #    If a `{` is already the first non-whitespace char (full JSON or preamble),
    #    leave it alone — _extract_outermost_json will find the right block.
    if cleaned and cleaned[0] != "{":
        # Check whether this looks like a JSON continuation (starts with a key)
        # or genuinely has a { somewhere inside (preamble case)
        first_brace = cleaned.find("{")
        first_quote = cleaned.find('"')
        if first_brace == -1 or (first_quote != -1 and first_quote < first_brace):
            # Continuation: `"technical": [...]` — prepend {
            cleaned = "{" + cleaned

    # 3. Extract outermost JSON object by bracket counting
    json_str = _extract_outermost_json(cleaned)

    if not json_str:
        raise ValueError(f"No JSON object found in LLM response:\n{raw[:600]}")

    # 4. Parse — if truncated, attempt to close open structures
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Attempt lightweight repair: close any unclosed arrays/objects
        repaired = _repair_truncated_json(json_str)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse JSON from LLM response.\n"
                f"Raw (first 600 chars): {raw[:600]}\n"
                f"Parse error: {exc}"
            ) from exc


def _repair_truncated_json(s: str) -> str:
    """
    Close unclosed JSON arrays and objects so a truncated response can
    still be parsed. Works for the common case of a response cut by
    max_new_tokens mid-way through a string value or key.
    """
    # Step 1: close an unterminated string literal at the very end
    # Count unescaped quotes to decide if we're inside a string
    in_str = False
    escape_next = False
    for ch in s:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_str = not in_str
    if in_str:
        s = s + '"'  # close the open string

    # Step 2: remove trailing incomplete key-value (e.g. `,"tip":`)
    s = re.sub(r',\s*"[^"]*"\s*:\s*$', "", s)
    # Step 3: remove trailing comma before a closing bracket/brace
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # Step 4: walk and build a closing stack
    stack = []
    in_string = False
    escape_next2 = False
    for ch in s:
        if escape_next2:
            escape_next2 = False
            continue
        if ch == "\\" and in_string:
            escape_next2 = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()

    # Close any unclosed structures in reverse order
    return s + "".join(reversed(stack))


def generate_interview_prep(
    name: str,
    role: str,
    level: str,
    skills: list[str],
    retrieved_chunks: list[dict],
) -> dict:
    """
    Full generation step:
      1. Build prompt from profile + retrieved context
      2. Call watsonx.ai
      3. Parse structured JSON response
    Returns a dict with keys: technical, behavioral, readiness
    """
    prompt = _build_prompt(name, role, level, skills, retrieved_chunks)
    raw_text = _call_watsonx(prompt)
    result = _parse_json_response(raw_text)

    # Validate minimal structure
    for key in ("technical", "behavioral", "readiness"):
        if key not in result:
            result[key] = [] if key != "readiness" else {"score": 5, "recommendations": []}

    return result
