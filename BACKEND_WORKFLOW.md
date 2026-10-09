# HireFlow Backend - Complete Application Workflow

## Table of Contents
1. [Application Architecture Overview](#application-architecture-overview)
2. [Tech Stack & Dependencies](#tech-stack--dependencies)
3. [Application Startup Flow](#application-startup-flow)
4. [Resume Upload & Processing Pipeline](#resume-upload--processing-pipeline)
5. [Job Description Creation & Parsing](#job-description-creation--parsing)
6. [Resume Screening & Candidate Matching](#resume-screening--candidate-matching)
7. [Data Storage Architecture](#data-storage-architecture)
8. [Business Unit Isolation](#business-unit-isolation)
9. [API Endpoints Summary](#api-endpoints-summary)

---

## Application Architecture Overview

HireFlow is an AI-powered Applicant Tracking System (ATS) built on **FastAPI** with PostgreSQL and Pinecone vector database. It automates resume screening using multiple AI services:

- **Google Gemini 2.5 Flash**: Resume/JD parsing and AI-powered scoring
- **Sentence Transformers (all-MiniLM-L6-v2)**: Semantic embeddings (384-dimensional vectors)
- **Pinecone**: Vector database for semantic resume search
- **PostgreSQL**: Primary relational database with BYTEA storage for files

---

## Tech Stack & Dependencies

### Core Framework
- **FastAPI**: Async web framework
- **SQLAlchemy 2.x**: Async ORM with PostgreSQL
- **Pydantic**: Data validation and settings management
- **Structlog**: Structured logging

### AI & ML Services
- **Google Gemini**: `google-generativeai` library
- **Sentence Transformers**: `all-MiniLM-L6-v2` model (384-dim embeddings)
- **Pinecone**: Vector database with cosine similarity

### Database
- **PostgreSQL**: Primary database with `asyncpg` driver
- **Storage**: BYTEA columns for binary file storage
- **Indexing**: GIN indexes for JSON fields, B-tree for foreign keys

### File Processing
- **PyMuPDF**: PDF text extraction
- **python-docx**: DOCX text extraction
- **hashlib**: SHA-256 content hashing for deduplication

---

## Application Startup Flow

### 1. Application Initialization (`main.py`)

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Application Startup (lifespan context manager)    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Create Database Tables (SQLAlchemy create_all)          │
│     - users                                                 │
│     - business_units                                        │
│     - user_units (many-to-many)                            │
│     - job_descriptions                                      │
│     - resumes                                               │
│     - upload_batches                                        │
│     - screening_results                                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Seed Business Units (idempotent upsert)                │
│     - DPU (Digital Publishing Unit)                         │
│     - Resource Management Group                             │
│     - Delivery Unit                                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Add Missing Columns (idempotent migrations)            │
│     - ALTER TABLE IF NOT EXISTS for backward compatibility  │
│     - Add indexes (content_hash, unit_id, job_position_id) │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Register API Routers                                    │
│     - /auth (login, register)                              │
│     - /resumes (upload, list, download)                    │
│     - /jobs (create, screen, list)                         │
│     - /screening-results (list, export, PDF)               │
│     - /admin (user management, bulk operations)            │
│     - /units (business unit management)                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  5. CORS Middleware Configuration                           │
│     - Allow origins: localhost:3000, 127.0.0.1:3000        │
│     - Allow credentials: true                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Resume Upload & Processing Pipeline

### Phase 1: File Upload (`POST /resumes/bulk-upload`)

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend uploads files (PDF/DOCX) with metadata            │
│  - files: List[UploadFile]                                 │
│  - job_position_id: str (linked to job)                    │
│  - unit_id: str (business unit)                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Validate User's Unit Access                            │
│     - Check if user belongs to the specified unit          │
│     - Query: user_units table (many-to-many)               │
│     - If not assigned → 403 Forbidden                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Create Upload Batch Record                             │
│     - Generate batch_id (UUID)                             │
│     - total_files: count of files                          │
│     - status: "processing"                                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Process Each File                                       │
│     ┌───────────────────────────────────────────────────┐  │
│     │  a. Read file bytes into memory                   │  │
│     │     - await read_upload_file_bytes(file)          │  │
│     │     - Validate MIME type (PDF/DOCX)               │  │
│     │     - Check file size (max 10 MB)                 │  │
│     └───────────────────────────────────────────────────┘  │
│                          │                                  │
│     ┌───────────────────────────────────────────────────┐  │
│     │  b. Compute SHA-256 Content Hash                  │  │
│     │     - hashlib.sha256(file_bytes).hexdigest()      │  │
│     │     - Used for duplicate detection                │  │
│     └───────────────────────────────────────────────────┘  │
│                          │                                  │
│     ┌───────────────────────────────────────────────────┐  │
│     │  c. Check for Duplicates                          │  │
│     │     - Query: resumes table                        │  │
│     │     - WHERE content_hash = hash                   │  │
│     │     - AND job_position_id = current_job           │  │
│     │     - If found → skip (deduplication)             │  │
│     └───────────────────────────────────────────────────┘  │
│                          │                                  │
│     ┌───────────────────────────────────────────────────┐  │
│     │  d. Create Resume Record                          │  │
│     │     - id: UUID                                     │  │
│     │     - resume_file: BYTEA (binary storage)         │  │
│     │     - file_mimetype: 'application/pdf' or DOCX    │  │
│     │     - content_hash: SHA-256                       │  │
│     │     - unit_id: business unit                      │  │
│     │     - job_position_id: linked job                 │  │
│     │     - parse_status: "pending"                     │  │
│     │     - upload_status: "completed"                  │  │
│     └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Queue Background Processing                             │
│     - Add _process_resume(resume_id) to background tasks   │
│     - FastAPI BackgroundTasks (async workers)              │
│     - Max 5 concurrent processing (asyncio.Semaphore)      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Return 202 Accepted Response                            │
│     - resume_ids: list of created IDs                      │
│     - batch_id: for tracking                               │
│     - skipped_files: duplicates                            │
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 2: Resume Parsing (Background Task)

**Function**: `_process_resume(resume_id, db_url)`  
**Execution**: Async background task (concurrent with up to 5 parallel workers)

```
┌─────────────────────────────────────────────────────────────┐
│  Background Task: _process_resume(resume_id)                │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Update Parse Status                                     │
│     - parse_status: "processing"                           │
│     - Commit to database                                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Extract Text from Resume                                │
│     ┌───────────────────────────────────────────────────┐  │
│     │  If resume.resume_file (BYTEA) exists:            │  │
│     │    - extract_text_from_bytes(bytes, mimetype)     │  │
│     │    - PDF: PyMuPDF (fitz.open(stream=...))        │  │
│     │    - DOCX: python-docx (Document(BytesIO))       │  │
│     │  Else (backward compat):                          │  │
│     │    - extract_text(file_path, content_type)        │  │
│     └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Parse Resume with Google Gemini                         │
│     ┌───────────────────────────────────────────────────┐  │
│     │  API: resume_parser.parse_resume(text)            │  │
│     │  Model: gemini-2.0-flash                          │  │
│     │  Temperature: 0.1 (deterministic)                 │  │
│     │  Max tokens: 4096                                 │  │
│     │                                                    │  │
│     │  Prompt Structure:                                │  │
│     │  "You are an expert resume parser.               │  │
│     │   Extract structured information..."              │  │
│     │                                                    │  │
│     │  Expected JSON Output:                            │  │
│     │  {                                                │  │
│     │    "candidate_name": str,                         │  │
│     │    "email": str | null,                          │  │
│     │    "phone": str | null,                          │  │
│     │    "location": str | null,                       │  │
│     │    "total_exp_years": float,                     │  │
│     │    "recent_skills": [str],                       │  │
│     │    "all_skills": [str],                          │  │
│     │    "education": [                                │  │
│     │      {                                            │  │
│     │        "degree": str,                            │  │
│     │        "institution": str,                       │  │
│     │        "year": int | null                        │  │
│     │      }                                            │  │
│     │    ],                                             │  │
│     │    "experience": [                               │  │
│     │      {                                            │  │
│     │        "title": str,                             │  │
│     │        "company": str,                           │  │
│     │        "duration_start": "YYYY-MM",              │  │
│     │        "duration_end": "YYYY-MM" | "Present",    │  │
│     │        "duration_years": float,                  │  │
│     │        "description": str,                       │  │
│     │        "achievements": [str],                    │  │
│     │        "skills_used": [str]                      │  │
│     │      }                                            │  │
│     │    ],                                             │  │
│     │    "employment_gaps": [                          │  │
│     │      {                                            │  │
│     │        "start": "YYYY-MM",                       │  │
│     │        "end": "YYYY-MM",                         │  │
│     │        "duration_months": int,                   │  │
│     │        "explanation": str | null                 │  │
│     │      }                                            │  │
│     │    ],                                             │  │
│     │    "certifications": [                           │  │
│     │      {                                            │  │
│     │        "name": str,                              │  │
│     │        "issuer": str | null,                     │  │
│     │        "year": int | null                        │  │
│     │      }                                            │  │
│     │    ]                                              │  │
│     │  }                                                │  │
│     │                                                    │  │
│     │  Retry Logic: 2 attempts with exponential backoff│  │
│     │  Fallback: If Gemini fails → regex extraction   │  │
│     └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Fallback Parsing (if Gemini fails)                     │
│     ┌───────────────────────────────────────────────────┐  │
│     │  Regex-based extraction:                          │  │
│     │  - Name: first line of text                      │  │
│     │  - Email: regex r"[\w.+-]+@[\w-]+\.[\w.-]+"      │  │
│     │  - Phone: regex r"[\+]?\d[\d\s\-]{8,14}\d"       │  │
│     │  - Experience: search for "X years of experience"│  │
│     │  - Skills: keyword matching against common list  │  │
│     │    ["python", "java", "react", "aws", ...]       │  │
│     │  - Location: Indian cities detection             │  │
│     │    ["pune", "bangalore", "mumbai", ...]          │  │
│     └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Generate Embeddings (Sentence Transformers)             │
│     ┌───────────────────────────────────────────────────┐  │
│     │  Service: embedding_service.embed_resume()        │  │
│     │  Model: all-MiniLM-L6-v2                          │  │
│     │  Output Dimension: 384                            │  │
│     │                                                    │  │
│     │  Three Vectors Generated:                         │  │
│     │  ┌─────────────────────────────────────────────┐  │  │
│     │  │ 1. experience_vector (384-dim)              │  │  │
│     │  │    Input: concatenated experience text       │  │  │
│     │  │    "{title} at {company}: {description}     │  │  │
│     │  │     {achievements}"                          │  │  │
│     │  └─────────────────────────────────────────────┘  │  │
│     │  ┌─────────────────────────────────────────────┐  │  │
│     │  │ 2. skills_vector (384-dim)                  │  │  │
│     │  │    Input: space-separated all_skills         │  │  │
│     │  │    "Python Java React AWS Docker..."         │  │  │
│     │  └─────────────────────────────────────────────┘  │  │
│     │  ┌─────────────────────────────────────────────┐  │  │
│     │  │ 3. full_profile_vector (384-dim)            │  │  │
│     │  │    Input: skills + experience combined       │  │  │
│     │  │    Primary vector for semantic search        │  │  │
│     │  └─────────────────────────────────────────────┘  │  │
│     │                                                    │  │
│     │  Process:                                         │  │
│     │  - model.encode(text, convert_to_numpy=True)     │  │
│     │  - Returns numpy array → convert to list[float]  │  │
│     └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Store Vectors in Pinecone                               │
│     ┌───────────────────────────────────────────────────┐  │
│     │  Service: pinecone_service.upsert_resume()        │  │
│     │  Index: hireflow-resumes                          │  │
│     │  Region: us-east-1 (AWS Serverless)               │  │
│     │  Metric: cosine similarity                        │  │
│     │                                                    │  │
│     │  Three Vector Records Created:                    │  │
│     │  ┌─────────────────────────────────────────────┐  │  │
│     │  │ Record 1: resume_{resume_id}                │  │  │
│     │  │   - values: full_profile_vector (384)       │  │  │
│     │  │   - metadata: {                             │  │  │
│     │  │       resume_id: str,                       │  │  │
│     │  │       candidate_name: str,                  │  │  │
│     │  │       location: str,                        │  │  │
│     │  │       total_exp_years: float,               │  │  │
│     │  │       all_skills: [str],                    │  │  │
│     │  │       user_id: str,                         │  │  │
│     │  │       unit_id: str,                         │  │  │
│     │  │       job_position_id: str,                 │  │  │
│     │  │       vector_type: "full_profile"           │  │  │
│     │  │     }                                        │  │  │
│     │  └─────────────────────────────────────────────┘  │  │
│     │  ┌─────────────────────────────────────────────┐  │  │
│     │  │ Record 2: resume_{resume_id}_skills         │  │  │
│     │  │   - values: skills_vector (384)             │  │  │
│     │  │   - metadata: {..., vector_type: "skills"}  │  │  │
│     │  └─────────────────────────────────────────────┘  │  │
│     │  ┌─────────────────────────────────────────────┐  │  │
│     │  │ Record 3: resume_{resume_id}_exp            │  │  │
│     │  │   - values: experience_vector (384)         │  │  │
│     │  │   - metadata: {..., vector_type: "exp..."}  │  │  │
│     │  └─────────────────────────────────────────────┘  │  │
│     │                                                    │  │
│     │  Returns: pinecone_id = "resume_{resume_id}"     │  │
│     └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Update Resume Record in PostgreSQL                      │
│     - parsed_data: full JSON object                        │
│     - candidate_name: extracted                            │
│     - candidate_email: extracted                           │
│     - candidate_location: extracted                        │
│     - total_exp_years: calculated                          │
│     - recent_skills: last 3 years                          │
│     - all_skills: complete list                            │
│     - pinecone_id: "resume_{resume_id}"                    │
│     - parse_status: "completed"                            │
│     - updated_at: now()                                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  8. Update Batch Status                                     │
│     - processed_files += 1                                 │
│     - If all processed → status: "completed"               │
└─────────────────────────────────────────────────────────────┘
```

---

## Job Description Creation & Parsing

### Endpoint: `POST /jobs/create`

```
┌─────────────────────────────────────────────────────────────┐
│  User submits job description text                          │
│  {                                                          │
│    "job_description_text": str,                            │
│    "job_title": str | null,                                │
│    "company": str | null,                                  │
│    "business_unit_id": str | null,                         │
│    "experience": "0-2 yrs" | "2-5 yrs" | etc,              │
│    "employee_type": "Full-time" | "Contract",              │
│    "location_office": "Kothrud" | "Baner",                 │
│    "remote_job": bool,                                     │
│    "hiring_leads": [str],                                  │
│    "recruiter_id": str | null,                             │
│    "valid_till": "2026-12-31" (ISO date)                   │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Parse JD with Google Gemini                             │
│     ┌───────────────────────────────────────────────────┐  │
│     │  API: resume_parser.parse_jd(text)                │  │
│     │  Model: gemini-2.0-flash                          │  │
│     │  Temperature: 0.1                                 │  │
│     │                                                    │  │
│     │  Prompt: Extract structured requirements...       │  │
│     │                                                    │  │
│     │  Expected JSON Output:                            │  │
│     │  {                                                │  │
│     │    "job_title": str,                              │  │
│     │    "company": str | null,                        │  │
│     │    "location": str | null,                       │  │
│     │    "required_min_exp_years": float,              │  │
│     │    "preferred_min_exp_years": float | null,      │  │
│     │    "required_skills": [                          │  │
│     │      {                                            │  │
│     │        "skill": str,                             │  │
│     │        "proficiency": "Beginner" | "Inter..." |  │  │
│     │                      "Advanced" | "Expert",      │  │
│     │        "years_required": float                   │  │
│     │      }                                            │  │
│     │    ],                                             │  │
│     │    "nice_to_have_skills": [str],                 │  │
│     │    "education_required": str | null,             │  │
│     │    "locations_accepted": [str],                  │  │
│     │    "willingness_to_relocate": str | null,        │  │
│     │    "top_3_mandatory_skills": [str, str, str]     │  │
│     │  }                                                │  │
│     │                                                    │  │
│     │  Retry: 3 attempts with exponential backoff      │  │
│     │  Fallback: Keyword extraction from JD text       │  │
│     └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Fallback Parsing (if Gemini fails)                     │
│     - Extract skills: keyword matching (COMMON_SKILLS list)│
│     - Extract experience: regex "(\d+)\+? years"           │
│     - Default job_title: "Software Engineer"               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Generate Job ID                                         │
│     - Format: HARB_###                                     │
│     - Query max existing ID → increment                    │
│     - Example: HARB_001, HARB_002, ...                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Create JobDescription Record                            │
│     - job_id: HARB_###                                     │
│     - user_id: current user                                │
│     - business_unit_id: from request                       │
│     - job_title: parsed or provided                        │
│     - company: parsed or provided                          │
│     - required_min_exp_years: parsed                       │
│     - required_skills: JSON array                          │
│     - nice_to_have_skills: JSON array                      │
│     - job_description_full: original text                  │
│     - status: "active"                                     │
│     - valid_till: parsed datetime                          │
│     - screening_count: 0                                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Return Job Record                                       │
│     - 201 Created                                          │
│     - Full job object with parsed requirements             │
└─────────────────────────────────────────────────────────────┘
```

---

## Resume Screening & Candidate Matching

### Endpoint: `POST /jobs/{job_id}/screen`

**This is the core intelligence of HireFlow** - a multi-stage pipeline combining semantic search, deterministic rules, and AI scoring.

```
┌─────────────────────────────────────────────────────────────┐
│  User triggers screening for a job                          │
│  POST /jobs/{job_id}/screen                                │
│  { "max_candidates": 20 }                                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 0: Pre-flight Checks                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - Load job description from database                 │  │
│  │ - Verify user owns the job                           │  │
│  │ - Get user's business unit(s)                        │  │
│  │ - Prepare parsed_jd dict for scoring                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: Generate JD Embeddings                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Service: embedding_service.embed_jd()                │  │
│  │ Model: all-MiniLM-L6-v2 (384-dim)                    │  │
│  │                                                       │  │
│  │ Two Vectors:                                         │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ 1. requirements_vector (384-dim)                │  │  │
│  │ │    Input: space-separated required skills       │  │  │
│  │ │    "Python Django AWS Docker PostgreSQL..."     │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ 2. full_jd_vector (384-dim)                     │  │  │
│  │ │    Input: requirements + full JD text           │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: Semantic Search in Pinecone                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Service: pinecone_service.search_by_jd()             │  │
│  │ Index: hireflow-resumes                              │  │
│  │ Metric: cosine similarity                            │  │
│  │ Top K: max_candidates × 3 (e.g., 20 → 60 pool)      │  │
│  │                                                       │  │
│  │ Filter: STRICT Business Unit Isolation              │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ If user has 1 unit:                             │  │  │
│  │ │   filter = {"unit_id": {"$eq": "unit_id"}}      │  │  │
│  │ │ If user has multiple units:                     │  │  │
│  │ │   filter = {"unit_id": {"$in": [ids...]}}       │  │  │
│  │ │ Else (backward compat):                         │  │  │
│  │ │   filter = {"user_id": {"$eq": "user_id"}}      │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │ Hybrid Search Strategy:                              │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ Query 1: Full Profile Search                    │  │  │
│  │ │   - vector: full_jd_vector                      │  │  │
│  │ │   - filter: unit_id + vector_type="full_prof..."│  │  │
│  │ │   - Returns: top K matches with scores          │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ Query 2: Skills-Focused Search                  │  │  │
│  │ │   - vector: requirements_vector                 │  │  │
│  │ │   - filter: unit_id + vector_type="skills"      │  │  │
│  │ │   - Returns: top K matches with scores          │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │ Score Merging:                                       │  │
│  │   - Profile score × 0.5 + Skills score × 0.5        │  │
│  │   - Deduplicate by resume_id                        │  │
│  │   - Sort by combined score (descending)             │  │
│  │                                                       │  │
│  │ Fallback: If Pinecone unavailable                    │  │
│  │   - Query PostgreSQL resumes table                  │  │
│  │   - Filter by unit_id + parse_status="completed"    │  │
│  │   - Assign neutral score: 0.5                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Returns: [                                                 │
│    {                                                        │
│      "resume_id": str,                                     │
│      "similarity_score": float (0.0-1.0),                  │
│      "metadata": {...}                                     │
│    },                                                       │
│    ...                                                      │
│  ]                                                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: Fetch Resume Records from PostgreSQL              │
│  - Query resumes table for matched resume_ids              │
│  - Create resume_map: {id: Resume} for fast lookup        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4: Concurrent Scoring (semaphore limit: 3)          │
│  Process each candidate:                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ For each candidate in semantic matches:              │  │
│  │                                                       │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ SUB-STAGE A: Knockout Filters                   │  │  │
│  │ │ Service: knockout_engine.check_knockouts()      │  │  │
│  │ │ Deterministic rules (immediate disqualification)│  │  │
│  │ │                                                  │  │  │
│  │ │ Rule 1: Experience Mismatch                     │  │  │
│  │ │   - Required: required_min_exp_years            │  │  │
│  │ │   - Buffer: 0.6× (allow 40% below)              │  │  │
│  │ │   - Example: 5yr req → 3yr min threshold        │  │  │
│  │ │   - Fail if: candidate_exp < threshold          │  │  │
│  │ │                                                  │  │  │
│  │ │ Rule 2: Missing Mandatory Skills               │  │  │
│  │ │   - Check: top_3_mandatory_skills               │  │  │
│  │ │   - Must be in recent_skills (last 3 years)     │  │  │
│  │ │   - Fuzzy match: case-insensitive contains      │  │  │
│  │ │   - Fail if: any of top 3 missing               │  │  │
│  │ │                                                  │  │  │
│  │ │ Rule 3: Recent Experience Irrelevant           │  │  │
│  │ │   - Analyze: last 2 years of experience         │  │  │
│  │ │   - Calculate: skills overlap ratio             │  │  │
│  │ │   - Fail if: overlap < 20% (career pivot flag)  │  │  │
│  │ │                                                  │  │  │
│  │ │ Rule 4: Employment Gaps                         │  │  │
│  │ │   - Threshold: MAX_GAP_MONTHS = 12              │  │  │
│  │ │   - Fail if: gap > 12 months (unexplained)      │  │  │
│  │ │                                                  │  │  │
│  │ │ Rule 5: Location Mismatch                       │  │  │
│  │ │   - If JD has locations_accepted list           │  │  │
│  │ │   - Fail if: candidate location not in list     │  │  │
│  │ │   - Skip if: remote_job = true                  │  │  │
│  │ │                                                  │  │  │
│  │ │ Rule 6: Education Requirements                  │  │  │
│  │ │   - If JD requires specific degree              │  │  │
│  │ │   - Check: candidate education list             │  │  │
│  │ │   - Fail if: degree not found                   │  │  │
│  │ │                                                  │  │  │
│  │ │ Returns: (passed: bool, failures: list[dict])   │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ IF KNOCKED OUT:                                 │  │  │
│  │ │ - Skip AI scoring (save API costs)              │  │  │
│  │ │ - Use deterministic scoring fallback            │  │  │
│  │ │ - Create ScreeningResult:                       │  │  │
│  │ │     fit_score: 0                                │  │  │
│  │ │     status: "POOR"                              │  │  │
│  │ │     passed_knockouts: false                     │  │  │
│  │ │     knockout_failures: [reasons]                │  │  │
│  │ │ - Still get skills analysis for transparency    │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ SUB-STAGE B: AI Scoring (if passed knockouts)  │  │  │
│  │ │ Service: scoring_engine.score_candidate()       │  │  │
│  │ │ Model: Google Gemini 2.5 Flash                  │  │  │
│  │ │ Temperature: 0.2 (slightly creative)            │  │  │
│  │ │ Max tokens: 2048                                │  │  │
│  │ │                                                  │  │  │
│  │ │ Prompt Structure:                               │  │  │
│  │ │ "You are an expert recruiter scoring...        │  │  │
│  │ │  Evaluate on 4 dimensions (0-100):"            │  │  │
│  │ │                                                  │  │  │
│  │ │ Dimension 1: SKILLS_MATCH (40% weight)         │  │  │
│  │ │   - Top-3 mandatory skills in recent exp?       │  │  │
│  │ │   - Proficiency level match?                    │  │  │
│  │ │   - Bonus for nice-to-have skills               │  │  │
│  │ │                                                  │  │  │
│  │ │ Dimension 2: EXPERIENCE_RELEVANCE (25% weight) │  │  │
│  │ │   - Years vs requirement                        │  │  │
│  │ │   - Domain/industry alignment                   │  │  │
│  │ │   - Role level appropriateness                  │  │  │
│  │ │   - Tech stack overlap                          │  │  │
│  │ │                                                  │  │  │
│  │ │ Dimension 3: CAREER_PROGRESSION (20% weight)   │  │  │
│  │ │   - Upward trajectory (title advancement)       │  │  │
│  │ │   - Increasing responsibilities                 │  │  │
│  │ │   - Promotions / scope growth                   │  │  │
│  │ │                                                  │  │  │
│  │ │ Dimension 4: ACHIEVEMENTS (15% weight)         │  │  │
│  │ │   - Specific metrics (%, $, numbers)            │  │  │
│  │ │   - Impact scope (team/org/customer)            │  │  │
│  │ │   - Technical complexity                        │  │  │
│  │ │                                                  │  │  │
│  │ │ Expected JSON Output:                           │  │  │
│  │ │ {                                               │  │  │
│  │ │   "scores": {                                   │  │  │
│  │ │     "skills_match": 0-100,                      │  │  │
│  │ │     "experience_relevance": 0-100,              │  │  │
│  │ │     "career_progression": 0-100,                │  │  │
│  │ │     "measurable_achievements": 0-100            │  │  │
│  │ │   },                                            │  │  │
│  │ │   "strengths": ["up to 4 statements"],          │  │  │
│  │ │   "weaknesses": ["up to 3 statements"],         │  │  │
│  │ │   "skills_matched": [                           │  │  │
│  │ │     {                                           │  │  │
│  │ │       "required_skill": str,                    │  │  │
│  │ │       "candidate_skill": str,                   │  │  │
│  │ │       "match_confidence": 0.0-1.0,              │  │  │
│  │ │       "years_in_profile": int                   │  │  │
│  │ │     }                                           │  │  │
│  │ │   ],                                            │  │  │
│  │ │   "skills_missing": [                           │  │  │
│  │ │     {                                           │  │  │
│  │ │       "required_skill": str,                    │  │  │
│  │ │       "importance": "high" | "medium" | "low"   │  │  │
│  │ │     }                                           │  │  │
│  │ │   ],                                            │  │  │
│  │ │   "match_explanation": "2-3 sentence summary"   │  │  │
│  │ │ }                                               │  │  │
│  │ │                                                  │  │  │
│  │ │ Weighted Fit Score Calculation:                │  │  │
│  │ │   fit_score = (                                │  │  │
│  │ │     skills_match × 0.40 +                      │  │  │
│  │ │     experience_relevance × 0.25 +              │  │  │
│  │ │     career_progression × 0.20 +                │  │  │
│  │ │     achievements × 0.15                        │  │  │
│  │ │   )                                             │  │  │
│  │ │                                                  │  │  │
│  │ │ Status Assignment:                              │  │  │
│  │ │   - EXCELLENT: fit_score >= 80                  │  │  │
│  │ │   - GOOD: fit_score >= 65                       │  │  │
│  │ │   - ADEQUATE: fit_score >= 50                   │  │  │
│  │ │   - POOR: fit_score < 50                        │  │  │
│  │ │                                                  │  │  │
│  │ │ Fallback: If Gemini fails                       │  │  │
│  │ │   - Use deterministic keyword matching          │  │  │
│  │ │   - Skills match: count overlaps                │  │  │
│  │ │   - Experience: ratio calculation               │  │  │
│  │ │   - Career: heuristic based on titles           │  │  │
│  │ │   - Achievements: detect numbers in text        │  │  │
│  │ │                                                  │  │  │
│  │ │ Retry: 3 attempts with exponential backoff     │  │  │
│  │ │ Timing: track screening_time_ms                │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │ ┌─────────────────────────────────────────────────┐  │  │
│  │ │ CREATE SCREENING RESULT OBJECT:                 │  │  │
│  │ │   result_id: UUID                               │  │  │
│  │ │   resume_id: from match                         │  │  │
│  │ │   job_id: current job                           │  │  │
│  │ │   fit_score: calculated                         │  │  │
│  │ │   status: EXCELLENT|GOOD|ADEQUATE|POOR          │  │  │
│  │ │   passed_knockouts: bool                        │  │  │
│  │ │   knockout_failures: [...]                      │  │  │
│  │ │   skills_match_score: from AI/deterministic     │  │  │
│  │ │   experience_relevance_score: ""                │  │  │
│  │ │   career_progression_score: ""                  │  │  │
│  │ │   achievements_score: ""                        │  │  │
│  │ │   strengths: [...]                              │  │  │
│  │ │   weaknesses: [...]                             │  │  │
│  │ │   skills_matched: [...]                         │  │  │
│  │ │   skills_missing: [...]                         │  │  │
│  │ │   match_explanation: str                        │  │  │
│  │ │   candidate_name: denormalized                  │  │  │
│  │ │   candidate_email: denormalized                 │  │  │
│  │ │   candidate_location: denormalized              │  │  │
│  │ │   total_exp_years: denormalized                 │  │  │
│  │ │   screening_time_ms: elapsed                    │  │  │
│  │ │   is_shortlisted: false (manual action)         │  │  │
│  │ └─────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Concurrency: asyncio.gather() with semaphore(3)           │
│  - Process up to 3 candidates simultaneously                │
│  - Rate limiting for Gemini API                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 5: Rank and Sort Results                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Sort Priority:                                        │  │
│  │   1. passed_knockouts: true first                    │  │
│  │   2. fit_score: descending                           │  │
│  │                                                       │  │
│  │ Assign Ranks:                                        │  │
│  │   - Only candidates who passed_knockouts get ranks   │  │
│  │   - rank = 1, 2, 3, ... (ascending)                  │  │
│  │   - Knocked-out candidates: rank = 0                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 6: Persist to Database                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Delete old screening results for this job         │  │
│  │    DELETE FROM screening_results                     │  │
│  │    WHERE job_id = current_job_id                     │  │
│  │                                                       │  │
│  │ 2. Insert new results (bulk insert)                  │  │
│  │    - All ScreeningResult objects                     │  │
│  │    - Both passed and knocked-out candidates          │  │
│  │                                                       │  │
│  │ 3. Update job metadata                               │  │
│  │    - job.screening_count += 1                        │  │
│  │    - job.updated_at = now()                          │  │
│  │                                                       │  │
│  │ 4. Commit transaction                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 7: Return Summary                                    │
│  {                                                          │
│    "message": "Screening complete",                        │
│    "job_id": "HARB_001",                                   │
│    "total_screened": 60,                                   │
│    "passed_knockouts": 42,                                 │
│    "top_candidates": 20                                    │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Storage Architecture

### PostgreSQL Schema

```
┌─────────────────────────────────────────────────────────────┐
│  PRIMARY DATABASE: PostgreSQL (async via asyncpg)           │
└─────────────────────────────────────────────────────────────┘

TABLE: users
─────────────────────────────────────────────────────────────
  id                  VARCHAR(36) PRIMARY KEY
  email               VARCHAR(255) UNIQUE NOT NULL
  hashed_password     VARCHAR(255) NOT NULL
  full_name           VARCHAR(255)
  role                VARCHAR(20) DEFAULT 'recruiter'
  created_at          TIMESTAMPTZ DEFAULT now()

TABLE: business_units
─────────────────────────────────────────────────────────────
  id                  VARCHAR(36) PRIMARY KEY
  unit_slug           VARCHAR(50) UNIQUE NOT NULL
  unit_name           VARCHAR(255) NOT NULL
  created_at          TIMESTAMPTZ DEFAULT now()

  RECORDS:
    - 00000000-0000-0000-0000-000000000001 | dpu | Digital Publishing Unit
    - 00000000-0000-0000-0000-000000000002 | resource_mgmt | Resource Management Group
    - 00000000-0000-0000-0000-000000000003 | delivery | Delivery Unit

TABLE: user_units (many-to-many)
─────────────────────────────────────────────────────────────
  user_id             VARCHAR(36) FK → users.id
  unit_id             VARCHAR(36) FK → business_units.id
  PRIMARY KEY (user_id, unit_id)

TABLE: job_descriptions
─────────────────────────────────────────────────────────────
  job_id                      VARCHAR(36) PRIMARY KEY
  user_id                     VARCHAR(36) FK → users.id
  business_unit_id            VARCHAR(36) FK → business_units.id
  job_title                   VARCHAR(500) NOT NULL
  company                     VARCHAR(255)
  location                    VARCHAR(255)
  required_min_exp_years      FLOAT DEFAULT 0
  preferred_min_exp_years     FLOAT
  required_skills             JSON  -- [{"skill": str, "proficiency": str, "years": int}]
  nice_to_have_skills         JSON  -- [str]
  education_required          VARCHAR(500)
  locations_accepted          JSON  -- [str]
  willingness_to_relocate     VARCHAR(100)
  job_description_full        TEXT NOT NULL
  screening_count             INT DEFAULT 0
  
  -- Lifecycle metadata
  experience                  VARCHAR(20)  -- "0-2 yrs", "2-5 yrs", etc
  employee_type               VARCHAR(50)  -- "Full-time", "Contract"
  location_office             VARCHAR(100) -- "Kothrud", "Baner"
  remote_job                  BOOLEAN DEFAULT false
  hiring_leads                JSON DEFAULT '[]'  -- [str]
  recruiter_id                VARCHAR(36) FK → users.id
  valid_till                  TIMESTAMPTZ
  status                      VARCHAR(20) DEFAULT 'active'  -- active|paused|filled
  
  created_at                  TIMESTAMPTZ DEFAULT now()
  updated_at                  TIMESTAMPTZ DEFAULT now()

  INDEXES:
    - idx_job_business_unit ON (business_unit_id)
    - idx_job_status ON (status)

TABLE: upload_batches
─────────────────────────────────────────────────────────────
  batch_id            VARCHAR(36) PRIMARY KEY
  user_id             VARCHAR(36) FK → users.id
  total_files         INT DEFAULT 0
  processed_files     INT DEFAULT 0
  failed_files        INT DEFAULT 0
  status              ENUM('pending','processing','completed','failed')
  created_at          TIMESTAMPTZ DEFAULT now()
  updated_at          TIMESTAMPTZ DEFAULT now()

TABLE: resumes
─────────────────────────────────────────────────────────────
  id                  VARCHAR(36) PRIMARY KEY
  user_id             VARCHAR(36) FK → users.id NOT NULL
  batch_id            VARCHAR(36) FK → upload_batches.batch_id
  unit_id             VARCHAR(36) FK → business_units.id
  job_position_id     VARCHAR(36) FK → job_descriptions.job_id
  
  filename            VARCHAR(500) NOT NULL
  file_path           VARCHAR(1000)  -- DEPRECATED: legacy field
  file_size           INT DEFAULT 0
  content_type        VARCHAR(100) NOT NULL
  
  -- BYTEA storage (PostgreSQL binary)
  resume_file         BYTEA  -- PDF/DOCX binary data
  file_mimetype       VARCHAR(50)
  content_hash        VARCHAR(64)  -- SHA-256 for deduplication
  
  upload_status       ENUM('pending','processing','completed','failed')
  parse_status        ENUM('pending','processing','completed','failed')
  
  parsed_data         JSON  -- Full resume parse result
  
  -- Denormalized fields for fast querying
  candidate_name      VARCHAR(255)
  candidate_email     VARCHAR(255)
  candidate_location  VARCHAR(255)
  total_exp_years     FLOAT
  recent_skills       JSON  -- [str] last 3 years
  all_skills          JSON  -- [str] complete list
  
  pinecone_id         VARCHAR(100)  -- "resume_{id}"
  
  created_at          TIMESTAMPTZ DEFAULT now()
  updated_at          TIMESTAMPTZ DEFAULT now()

  INDEXES:
    - idx_resumes_unit_id ON (unit_id)
    - idx_resumes_job_position ON (job_position_id)
    - idx_resumes_content_hash ON (content_hash)
    - idx_resumes_unit_job ON (unit_id, job_position_id)
    - idx_resumes_parse_status ON (parse_status)

TABLE: screening_results
─────────────────────────────────────────────────────────────
  result_id                      VARCHAR(36) PRIMARY KEY
  resume_id                      VARCHAR(36) FK → resumes.id NOT NULL
  job_id                         VARCHAR(36) FK → job_descriptions.job_id NOT NULL
  
  rank                           INT DEFAULT 0
  fit_score                      FLOAT DEFAULT 0.0
  status                         VARCHAR(20) DEFAULT 'POOR'  -- EXCELLENT|GOOD|ADEQUATE|POOR
  
  passed_knockouts               BOOLEAN DEFAULT true
  knockout_failures              JSON DEFAULT '[]'  -- [{"rule": str, "reason": str}]
  
  -- 4 scoring dimensions
  skills_match_score             FLOAT DEFAULT 0.0
  experience_relevance_score     FLOAT DEFAULT 0.0
  career_progression_score       FLOAT DEFAULT 0.0
  achievements_score             FLOAT DEFAULT 0.0
  
  -- AI-generated insights
  strengths                      JSON DEFAULT '[]'  -- [str]
  weaknesses                     JSON DEFAULT '[]'  -- [str]
  match_explanation              TEXT DEFAULT ''
  
  skills_matched                 JSON DEFAULT '[]'  -- [{skill, confidence, years}]
  skills_missing                 JSON DEFAULT '[]'  -- [{skill, importance}]
  
  -- Denormalized candidate info
  candidate_name                 VARCHAR(255)
  candidate_email                VARCHAR(255)
  candidate_location             VARCHAR(255)
  total_exp_years                FLOAT DEFAULT 0.0
  
  is_shortlisted                 BOOLEAN DEFAULT false
  screening_time_ms              INT DEFAULT 0
  
  created_at                     TIMESTAMPTZ DEFAULT now()

  INDEXES:
    - idx_screening_resume ON (resume_id)
    - idx_screening_job ON (job_id)
    - idx_screening_rank ON (job_id, rank)
```

---

### Pinecone Vector Database

```
┌─────────────────────────────────────────────────────────────┐
│  VECTOR DATABASE: Pinecone Serverless (AWS us-east-1)       │
└─────────────────────────────────────────────────────────────┘

INDEX: hireflow-resumes
─────────────────────────────────────────────────────────────
  Dimension: 384
  Metric: cosine
  Cloud: AWS
  Region: us-east-1
  Spec: Serverless

VECTOR RECORDS (3 per resume):
─────────────────────────────────────────────────────────────

Record 1: resume_{resume_id}
  id: "resume_12345678-abcd-..."
  values: [384 floats]  ← full_profile_vector
  metadata: {
    "resume_id": "12345678-abcd-...",
    "candidate_name": "John Doe",
    "location": "Pune",
    "total_exp_years": 5.5,
    "all_skills": ["Python", "Django", "AWS", ...],  (max 20)
    "user_id": "user-uuid",
    "unit_id": "00000000-0000-0000-0000-000000000001",
    "job_position_id": "HARB_001",
    "vector_type": "full_profile"
  }

Record 2: resume_{resume_id}_skills
  id: "resume_12345678-abcd-..._skills"
  values: [384 floats]  ← skills_vector
  metadata: {
    ... (same as above)
    "vector_type": "skills"
  }

Record 3: resume_{resume_id}_exp
  id: "resume_12345678-abcd-..._exp"
  values: [384 floats]  ← experience_vector
  metadata: {
    ... (same as above)
    "vector_type": "experience"
  }

QUERIES:
─────────────────────────────────────────────────────────────
1. Semantic Job Matching:
   - Query vector: full_jd_vector (384-dim)
   - Filter: {"unit_id": {"$eq": "unit_id"}, "vector_type": "full_profile"}
   - Top K: 60
   - Returns: Sorted by cosine similarity

2. Skills-Focused Search:
   - Query vector: requirements_vector (384-dim)
   - Filter: {"unit_id": {"$eq": "unit_id"}, "vector_type": "skills"}
   - Top K: 60
   - Returns: Sorted by cosine similarity

3. Hybrid Search:
   - Combine both queries
   - Merge scores: profile × 0.5 + skills × 0.5
   - Deduplicate by resume_id
```

---

## Business Unit Isolation

### Multi-Tenancy Design

```
┌─────────────────────────────────────────────────────────────┐
│  BUSINESS UNIT ISOLATION (Strict Multi-Tenancy)             │
└─────────────────────────────────────────────────────────────┘

Requirement: Cross-unit data leakage prevention
Implementation: Row-level filtering at API + Vector search level

┌─────────────────────────────────────────────────────────────┐
│  1. User → Unit Assignment (Many-to-Many)                   │
│     Table: user_units                                       │
│     - A user can belong to multiple units                   │
│     - Example: User A → [DPU, Delivery]                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Resume Upload (Unit Tagging)                            │
│     - Every resume MUST have unit_id                        │
│     - Derived from job.business_unit_id                     │
│     - Validation: User must belong to the unit              │
│     - Query: SELECT * FROM user_units                       │
│              WHERE user_id = X AND unit_id = Y              │
│     - If not found → 403 Forbidden                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Job Creation (Unit Scoping)                             │
│     - Jobs linked to business_unit_id (optional)            │
│     - Screening scoped to unit's resumes only               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Resume Listing (Unit Filtering)                         │
│     - Get user's units: get_current_user_units()            │
│     - Filter resumes:                                       │
│       WHERE unit_id IN (user's units)                       │
│     - Prevents cross-unit visibility                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Semantic Search (Pinecone Filtering)                    │
│     - CRITICAL: Filter at vector search level               │
│     - Single unit: {"unit_id": {"$eq": "unit_id"}}         │
│     - Multi units: {"unit_id": {"$in": [ids...]}}          │
│     - Ensures no cross-unit matches in screening            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Screening Results (Unit Inheritance)                    │
│     - Results inherit unit_id from resume                   │
│     - Job results only show candidates from job's unit      │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints Summary

### Authentication
```
POST   /auth/register          Create new user account
POST   /auth/login             Login with email/password → JWT token
GET    /auth/me                Get current user profile
```

### Resume Management
```
POST   /resumes/bulk-upload    Upload multiple resumes (PDF/DOCX)
                               - Files: List[UploadFile]
                               - job_position_id: str
                               - unit_id: str (optional, derived from job)
                               Returns: 202 Accepted + background processing

GET    /resumes                List resumes (paginated, unit-filtered)
                               Query: page, page_size, unit_id, job_position_id

GET    /resumes/{id}           Get single resume details

GET    /resumes/{id}/download  Download original resume file (BYTEA → PDF/DOCX)

DELETE /resumes/{id}           Delete resume + Pinecone vectors

POST   /resumes/reparse        Re-parse failed resumes (admin)
```

### Job Descriptions
```
POST   /jobs/create            Create job from JD text
                               - Gemini parsing of requirements
                               - Auto-generate HARB_### ID

GET    /jobs                   List jobs (user's jobs, unit-filtered)

GET    /jobs/{job_id}          Get job details

POST   /jobs/{job_id}/screen   Trigger candidate screening
                               - Semantic search → Knockout → AI scoring
                               - Returns top N ranked candidates

PUT    /jobs/{job_id}/status   Update job status (activate|pause|fill)

DELETE /jobs/{job_id}          Delete job + screening results
```

### Screening Results
```
GET    /screening-results      List all results (for user's jobs)
                               Query: page, page_size

GET    /screening-results/{result_id}
                               Get single result details

GET    /screening-results/{result_id}/pdf
                               Generate PDF analysis report
                               - AI-powered insights
                               - Dark-themed design

POST   /screening-results/{result_id}/action
                               Shortlist or reject candidate
                               Body: {"action": "shortlist" | "reject"}

POST   /screening-results/export
                               Export results to CSV
                               Body: {"job_id": str, "format": "csv"}
```

### Business Units
```
GET    /units                  List all business units

GET    /units/{unit_id}        Get unit details

POST   /units/{unit_id}/users  Assign users to unit (admin)

DELETE /units/{unit_id}/users/{user_id}
                               Remove user from unit (admin)
```

### Admin
```
GET    /admin/users            List all users (admin only)

PUT    /admin/users/{user_id}/role
                               Update user role (admin|recruiter)

POST   /admin/bulk-operations  Bulk actions (reparse, reindex, etc)
```

---

## Key Design Decisions

### 1. Why BYTEA Storage?
- **Previous**: Files stored on disk (file_path)
- **Now**: Files in PostgreSQL BYTEA columns
- **Reasons**:
  - Simplified deployment (no external file storage)
  - Atomic transactions (file + metadata)
  - Backup/restore simplicity
  - No file system sync issues

### 2. Why Three Vectors Per Resume?
- **full_profile_vector**: Holistic candidate matching
- **skills_vector**: Precise skill-based search
- **experience_vector**: Domain/industry alignment
- **Benefit**: Hybrid search strategy (profile + skills weighted)

### 3. Why Knockout Before AI Scoring?
- **Cost Optimization**: Skip expensive Gemini calls for obvious mismatches
- **Performance**: Deterministic filters are instant
- **Transparency**: Clear rejection reasons
- **Example**: 2yr candidate for 10yr role → instant knockout

### 4. Why Denormalize Candidate Fields?
- **Tables**: resumes, screening_results
- **Fields**: candidate_name, email, location, total_exp_years
- **Reason**: Fast queries without JOINs, immutable snapshots

### 5. Why Background Processing?
- **User Experience**: Immediate 202 Accepted response
- **Scalability**: Handle 200-file uploads without timeout
- **Concurrency**: Process 5 resumes simultaneously
- **Retries**: Graceful handling of API failures

---

## Performance Characteristics

### Resume Upload + Parse
```
Single Resume:
- Upload: ~50-200ms (BYTEA write)
- Text extraction: ~200-500ms (PyMuPDF/docx)
- Gemini parsing: ~2-4 seconds
- Embedding: ~100-300ms (local model)
- Pinecone upsert: ~100-200ms
Total: ~3-5 seconds per resume

Batch Upload (100 resumes):
- Sequential: ~5-8 minutes
- Concurrent (5 workers): ~1-2 minutes
```

### Screening
```
Single Job Screening (50 candidates):
- JD embedding: ~100ms
- Pinecone search: ~200-500ms
- Knockout filters: ~50ms per candidate (instant)
- Gemini scoring: ~2-3 seconds per candidate
- Concurrent (3 workers): ~30-50 seconds total

Knocked-out candidates: Skip Gemini → save ~70% time/cost
```

### Database Queries
```
- Resume listing (paginated): ~50-100ms
- Job details: ~20-50ms
- Screening results: ~100-200ms (includes JOINs)
- Index scans on unit_id, job_position_id: <10ms
```

---

## Error Handling & Fallbacks

### Gemini API Failures
- **Resume Parsing**: Fallback to regex extraction
- **JD Parsing**: Keyword matching from COMMON_SKILLS list
- **Scoring**: Deterministic scoring engine
- **Retries**: Exponential backoff (2-3 attempts)

### Pinecone Unavailable
- **Screening**: Query PostgreSQL resumes table with unit filter
- **Scoring**: Continue with fetched candidates
- **No vector scores**: Use neutral similarity (0.5)

### Database Connection Issues
- **Connection Pooling**: 10 base + 20 overflow connections
- **Async Retries**: SQLAlchemy engine-level retries
- **Graceful Degradation**: Return cached data when possible

### File Processing Errors
- **Corrupt PDFs**: Mark parse_status='failed', log error
- **Unsupported Formats**: Reject at upload (MIME validation)
- **Large Files**: 10MB limit enforced at endpoint

---

## Configuration (Environment Variables)

```bash
# Application
APP_NAME=HireFlow
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false

# Security
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=168  # 7 days

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/hireflow
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Google Gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash

# Pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=hireflow-resumes
PINECONE_ENVIRONMENT=us-east-1

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384

# File Upload
MAX_FILE_SIZE=10485760  # 10 MB
UPLOAD_DIR=/tmp/hireflow_uploads  # Legacy, not used with BYTEA

# Screening
MAX_SHORTLIST_CANDIDATES=20
MIN_FIT_SCORE_TO_SHOW=0
```

---

## Conclusion

HireFlow's backend is designed for:
- **Accuracy**: AI-powered parsing and scoring
- **Performance**: Concurrent processing, semantic search
- **Scalability**: Background tasks, connection pooling
- **Security**: Unit isolation, JWT auth, role-based access
- **Reliability**: Fallbacks at every layer, graceful degradation

The workflow combines:
1. **Human expertise** (knockout rules, weighted scoring)
2. **AI intelligence** (Gemini parsing/scoring, semantic matching)
3. **Engineering best practices** (async/await, retries, monitoring)

This creates a robust, production-ready ATS that scales from 10 to 10,000 candidates per job.
