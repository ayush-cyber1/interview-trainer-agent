# Interview Trainer Agent

A full-stack, RAG-powered interview preparation tool. Provide your profile (role, level, optional resume), and the agent retrieves relevant interview knowledge from a local corpus, then uses **IBM watsonx.ai** to generate a personalised set of technical and behavioral questions, model answers, and improvement tips.

---

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10 + |
| Node.js | 18 + |
| npm | 9 + |

---

## 1. Clone / open the project

```bash
cd interview-trainer-agent
```

---

## 2. Configure credentials

```bash
# Copy the template
cp .env.example backend/.env
```



> **Never commit `backend/.env`** — it is already listed in `.gitignore`.  
> Only `.env.example` (with empty values) is committed.

---

## 3. Set up the backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Build the vector store

This step embeds the local corpus using `all-MiniLM-L6-v2` (downloads ~85 MB on first run, then cached). **No watsonx.ai call is made here.**

```bash
# Still inside backend/ with venv active
python -m ingestion.build_vector_store
```

Expected output:
```
[1/4] Loading embedding model: all-MiniLM-L6-v2
[2/4] Flattening corpus …
       Found 69 chunks across 5 files.
[3/4] Connecting to Chroma …
[4/4] Embedding and storing 69 new chunks …
✓ Vector store built at: backend/vector_store/chroma_db
  Total chunks indexed: 69
```

To **force a full rebuild** (e.g. after editing corpus files):
```bash
python -m ingestion.build_vector_store --force
```

---

## 5. Start the backend server

```bash
# Inside backend/ with venv active
uvicorn main:app --reload --port 8000
```

Verify it's up:
```bash
curl http://localhost:8000/health
# {"status":"ok","vector_store":"ok","watsonx_configured":true}
```

Interactive API docs: **http://localhost:8000/docs**

---

## 6. Set up and start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 7. Using the app

1. **Profile Setup** — Enter your name, choose experience level, select a job role, optionally upload a PDF or DOCX resume.
2. Click **Save Profile** — the backend extracts skills from your resume.
3. Click **Generate Questions** — the RAG pipeline runs (5–20 s depending on network).
4. **Results & Tips** — browse technical and behavioral questions with model answers and tips. View your readiness score.
5. Click **Download Prep Sheet** to save a plain-text version.
6. **History** tab shows all generations from your current session.

---

## 8. Adding more roles / questions

1. Create a new JSON file in `backend/ingestion/corpus/` following the same schema as the existing files (see `software_engineer.json` for reference).
2. Re-run `python -m ingestion.build_vector_store` (new chunks are added incrementally — existing ones are not re-embedded).
3. No code changes needed.

---

## 9. Switching to a Granite model

When IBM Granite becomes available in your watsonx.ai project catalog:

1. Open `backend/.env`.
2. Change **only** this one line:
   ```dotenv
   WATSONX_MODEL_ID=ibm/granite-13b-instruct-v2
   ```
3. Restart the backend (`uvicorn main:app --reload --port 8000`).

No other change is needed anywhere in the codebase.

---

## 10. Project structure

Every folder and meaningful file is annotated so you can find any piece of the project just by reading this tree.

```
interview-trainer-agent/
│
├── .env.example                          # Credential template — copy to backend/.env and fill in
├── README.md                             # This file — setup, usage, structure
├── ARCHITECTURE.md                       # Blueprint: sequence diagram, component descriptions, Lite notes
│
├── backend/                              # Python FastAPI backend
│   ├── .env                              # Real credentials (git-ignored — never commit)
│   ├── config.py                         # Central settings via pydantic-settings; reads backend/.env
│   ├── main.py                           # FastAPI app entry point; registers router + CORS middleware
│   ├── requirements.txt                  # All Python dependencies
│   │
│   ├── api/                              # HTTP layer — route handlers and Pydantic schemas
│   │   ├── __init__.py
│   │   ├── routes.py                     # GET /health · POST /profile · POST /generate
│   │   └── models.py                     # Request/response Pydantic models (ProfileRequest, GenerateResponse …)
│   │
│   ├── ingestion/                        # Knowledge-base corpus + vector store build tooling
│   │   ├── __init__.py
│   │   ├── build_vector_store.py         # Run once: embeds corpus locally → persists to Chroma
│   │   └── corpus/                       # Seed interview Q&A — add a new .json here to extend roles
│   │       ├── software_engineer.json    # 15 questions (technical + behavioral, Fresher/Mid/Senior)
│   │       ├── data_analyst.json         # 14 questions
│   │       ├── product_manager.json      # 13 questions
│   │       ├── hr_specialist.json        # 13 questions
│   │       └── sales_executive.json      # 14 questions
│   │
│   ├── retrieval/                        # Vector store query logic (no watsonx.ai calls here)
│   │   ├── __init__.py
│   │   └── vector_store.py               # Lazy-loads embedding model; queries Chroma with role/level filter
│   │
│   ├── generation/                       # Prompt construction + watsonx.ai REST call
│   │   ├── __init__.py
│   │   └── generator.py                  # Builds prompt · exchanges API key for IAM token · POSTs to WATSONX_URL
│   │
│   ├── resume_parser/                    # PDF / DOCX resume text extraction
│   │   ├── __init__.py
│   │   └── parser.py                     # pypdf (PDF) + python-docx (DOCX) + ~50-keyword skill scanner
│   │
│   └── vector_store/                     # Created at build time — git-ignored
│       └── chroma_db/                    # Persisted Chroma HNSW index + metadata
│
└── frontend/                             # React 18 + TypeScript (Vite)
    ├── index.html                        # Vite HTML shell
    ├── package.json                      # npm dependencies (react, recharts, lucide-react …)
    ├── vite.config.ts                    # Vite config; proxies /api → http://localhost:8000
    ├── tsconfig.json                     # TypeScript compiler options
    └── src/
        ├── main.tsx                      # React DOM entry point
        ├── App.tsx                       # Root component; routing (BrowserRouter) + shared state
        ├── index.css                     # Global CSS variables, reset, animations
        ├── types.ts                      # Shared TypeScript interfaces (ProfileData, GenerateResponse …)
        ├── api.ts                        # Axios wrappers for submitProfile / generatePrep / checkHealth
        ├── components/
        │   ├── Layout.tsx                # Top nav (Profile Setup · Results & Tips · History) + <Outlet>
        │   └── Layout.module.css
        └── pages/
            ├── ProfilePage.tsx           # Profile form: name, level chips, role select, drag-drop resume
            ├── ProfilePage.module.css
            ├── ResultsPage.tsx           # Technical/behavioral tabs, expandable Q&A cards, readiness gauge
            ├── ResultsPage.module.css
            ├── HistoryPage.tsx           # Last-10-sessions list (in-memory, current tab)
            └── HistoryPage.module.css
```

> **Tip — adding a new role:** drop a JSON file into `backend/ingestion/corpus/` matching the schema of any existing file, then run `python -m ingestion.build_vector_store`. No code changes needed anywhere else.

---

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| `WATSONX_API_KEY is empty` error | Fill in `backend/.env` and restart uvicorn |
| `Vector store error … build_vector_store.py` | Run `python -m ingestion.build_vector_store` first |
| Resume skills not extracted | Ensure the file is a valid PDF or DOCX (not a scanned image-only PDF) |
| `401 Unauthorized` from watsonx.ai | Check that `WATSONX_API_KEY` is correct and not expired |
| Frontend can't reach backend | Confirm uvicorn is running on port 8000; Vite proxy is configured for `/api` |
| Slow generation | Normal — RAG + LLM inference takes 5–20 s. The spinner on the button confirms it's working. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM inference | IBM watsonx.ai (raw REST, no SDK) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local) |
| Vector store | Chroma (local, embedded, persisted to disk) |
| Backend | Python · FastAPI · Uvicorn · pydantic-settings · httpx |
| Resume parsing | pypdf · python-docx |
| Frontend | React 18 · TypeScript · Vite · Recharts · Lucide React |
