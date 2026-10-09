# Resume–Job Matching Application – Complete Technical Architecture & Flow Documentation

**Document Type:** Technical Architecture & Flow Documentation
**Application Name:** HireFlow
**Prepared By:** Senior Business Analyst – Technical Architecture
**Date:** February 2026
**Version:** 1.0
**Audience:** Leadership, Technical Stakeholders, Recruiters, Product Owners

---

---

## Table of Contents

1. Executive Summary
2. System Component Breakdown
3. End-to-End System Architecture (Text Diagram)
4. Resume Processing Flow (Detailed)
5. Job Posting Processing Flow
6. Pinecone Storage Analysis
7. Embeddings – Layman Explanation
8. Ranking & Matching Logic
9. LLM Interaction Flow
10. Integrated Data Flow
11. Current Gaps / Observed Limitations
12. Tagging & Metadata Strategy (Conceptual Recommendation)
13. Tech Stack Overview
14. Scalability Considerations
15. Security & Compliance
16. Conclusion

---

---

## 1. Executive Summary

### 1.1 System Purpose

HireFlow is an AI-powered resume screening system designed to automatically evaluate and shortlist the most qualified candidates from large volumes of uploaded resumes. The system eliminates hours of manual screening by intelligently comparing each candidate's profile against a structured job description using a multi-layered evaluation pipeline.

At its core, HireFlow combines three complementary evaluation mechanisms:

- **Semantic Vector Search** – Understanding meaning beyond exact keywords
- **Deterministic Knockout Filters** – Hard rule-based disqualification
- **LLM-Powered Scoring** – Contextual evaluation by a large language model

### 1.2 Target Users

| User Role | Primary Activities |
|-----------|-------------------|
| Recruiter | Upload resumes, enter job descriptions, trigger screening, view ranked candidates, export shortlists |
| Admin | View organization-wide statistics, monitor system usage, reprocess failed resumes |

### 1.3 Core Objective

The fundamental objective of HireFlow is **semantic resume-job matching at scale**. Unlike traditional keyword-based systems, HireFlow understands the meaning and context of both a resume and a job description. A candidate who lists "ML Engineering" experience can be correctly matched to a job requiring "Machine Learning" skills even without an exact keyword match.

### 1.4 High-Level Technology Explanation

HireFlow achieves semantic matching through a three-technology pipeline:

**Step 1 – Embeddings:**
Resume and job description text is converted into numerical vectors (lists of 384 numbers) by an AI model. These numbers capture the semantic meaning of the text – similar concepts produce similar numbers.

**Step 2 – Vector Search (Pinecone):**
When a recruiter triggers screening, the job description is also converted to a vector. Pinecone instantly searches through thousands of stored resume vectors and returns the candidates whose vectors are mathematically closest – meaning most semantically similar.

**Step 3 – LLM Ranking (Google Gemini):**
The top candidates returned from vector search are then individually evaluated by Google Gemini 2.0 Flash, which acts as an expert recruiter, assigning granular scores and producing written explanations of each candidate's strengths and weaknesses.

The result is a ranked shortlist delivered to the recruiter within minutes, complete with detailed justifications for each candidate's placement.

---

---

## 2. System Component Breakdown

HireFlow consists of **10 logical components** working together as an integrated system.

---

### Component 1: Frontend – Recruiter UI

| Attribute | Details |
|-----------|---------|
| **Purpose** | Provides the user interface for all recruiter and admin interactions with the system |
| **Technology** | Next.js 15, React 19, TypeScript, Tailwind CSS, Radix UI, Zustand 5.0, Axios, NextAuth v4 |
| **Inputs** | Recruiter actions (file uploads, JD text input, button clicks, filter selections) |
| **Outputs** | API requests to the Backend, rendered candidate cards, CSV exports |
| **Dependencies** | Backend API Layer, NextAuth session management |

**Key Pages:**

| Page | Route | Purpose |
|------|-------|---------|
| Landing | `/` | Welcome and navigation to login/register |
| Login | `/auth/login` | Recruiter authentication |
| Register | `/auth/register` | New recruiter account creation |
| Dashboard | `/dashboard` | Stats overview, charts, recent job listings |
| Upload | `/upload` | Bulk resume upload with drag-and-drop |
| Screen | `/screen` | Job description input and screening trigger |
| Shortlist | `/shortlist` | Ranked results, candidate cards, export |

---

### Component 2: Backend API Layer

| Attribute | Details |
|-----------|---------|
| **Purpose** | Serves as the central nervous system – receives all frontend requests, coordinates business logic, and returns structured responses |
| **Technology** | FastAPI 0.115.6 (Python 3.12+), Uvicorn ASGI server, Pydantic v2 for request/response validation |
| **Inputs** | HTTP requests from the Frontend (authenticated via JWT Bearer tokens) |
| **Outputs** | JSON responses, background task triggers, database writes |
| **Dependencies** | Primary Database, Resume Parsing Module, Embedding Service, Vector Database, LLM Integration Layer, File Storage Layer |

**API Surface (endpoint groups):**

| Group | Base Path | Description |
|-------|-----------|-------------|
| Authentication | `/api/auth` | Register, login, profile, token refresh |
| Resumes | `/api/resumes` | Upload, list, retrieve, delete resumes |
| Jobs | `/api/jobs` | Create, list, retrieve, delete job descriptions; trigger screening |
| Screening | `/api/screening-results` | Results, shortlisting actions, CSV export |
| Admin | `/api/admin` | Dashboard statistics, logs |
| Health | `/api/health` | System health check |

---

### Component 3: Resume Parsing Module

| Attribute | Details |
|-----------|---------|
| **Purpose** | Extracts raw text from uploaded PDF/DOCX files and then uses an LLM to parse that text into a structured JSON data structure |
| **Technology** | pdfplumber 0.11.4 (PDF extraction), python-docx 1.1.2 (DOCX extraction), Google Gemini 2.0 Flash (AI parsing) |
| **Inputs** | Binary file (PDF or DOCX), raw text string |
| **Outputs** | Structured JSON containing candidate profile (name, email, skills, experience, education, certifications, employment gaps) |
| **Dependencies** | File Storage Layer, LLM Integration Layer |

**Processing Details:**
- PDF files are extracted using pdfplumber, which reads all pages
- DOCX files are extracted using python-docx, which reads all paragraphs and tables
- Extracted text is passed to Google Gemini with a structured prompt requesting JSON output
- The module implements retry logic with 3 attempts and exponential backoff (2–10 seconds) to handle transient API errors
- If all retries fail, safe default values are applied to prevent data loss

---

### Component 4: Embedding Generation Service

| Attribute | Details |
|-----------|---------|
| **Purpose** | Converts text (resume content or job description) into numerical vectors that capture semantic meaning |
| **Technology** | sentence-transformers library with the `all-MiniLM-L6-v2` model |
| **Inputs** | Text strings (resume skills, experience descriptions, job requirements, full JD text) |
| **Outputs** | 384-dimensional floating-point vectors |
| **Dependencies** | None (runs locally; no external API call) |

**Embedding Strategy:**

| Vector Type | Source Text | Usage |
|-------------|-------------|-------|
| Resume Full Profile | Skills + Experience text combined | Primary similarity search |
| Resume Skills | All skills list concatenated | Skills-specific matching |
| Resume Experience | Job titles + descriptions + achievements | Experience-specific matching |
| JD Requirements | Required skills list | Matches against Resume Skills vector |
| JD Full | Requirements + full JD text | Matches against Resume Full Profile vector |

---

### Component 5: Vector Database – Pinecone

| Attribute | Details |
|-----------|---------|
| **Purpose** | Stores all resume embedding vectors and enables sub-second semantic similarity search across thousands of candidates |
| **Technology** | Pinecone Serverless (AWS, us-east-1), cosine similarity metric, 384-dimensional index |
| **Inputs** | Resume vectors with metadata (upsert), JD query vectors (search) |
| **Outputs** | Top-K most similar resume IDs and metadata with similarity scores |
| **Dependencies** | Embedding Generation Service |

**Index Configuration:**

| Setting | Value |
|---------|-------|
| Index Name | `hireflow-resumes` (configurable) |
| Dimensions | 384 |
| Similarity Metric | Cosine |
| Deployment | Serverless |
| Cloud / Region | AWS / us-east-1 |

---

### Component 6: Primary Database – PostgreSQL

| Attribute | Details |
|-----------|---------|
| **Purpose** | Persistent relational storage for all application data: users, job descriptions, resumes (metadata and parsed data), screening results |
| **Technology** | PostgreSQL 16, SQLAlchemy 2.0 async ORM, asyncpg driver, Alembic for schema migrations |
| **Inputs** | ORM write operations from Backend API Layer |
| **Outputs** | Structured query results for API responses |
| **Dependencies** | None (foundational layer) |

**Tables:**

| Table | Primary Content |
|-------|----------------|
| `users` | Recruiter and admin accounts |
| `job_descriptions` | Structured job requirements (parsed from JD text) |
| `upload_batches` | Batch progress tracking for bulk uploads |
| `resumes` | File metadata, parsed candidate JSON, Pinecone vector ID |
| `screening_results` | Rankings, scores, strengths, weaknesses, skill analysis |

---

### Component 7: LLM Integration Layer

| Attribute | Details |
|-----------|---------|
| **Purpose** | Interfaces with Google Gemini for two distinct tasks: (1) parsing unstructured text into structured JSON, (2) evaluating a candidate against a job and producing scores and explanations |
| **Technology** | Google Gemini 2.0 Flash (`gemini-2.0-flash`) via Google AI Studio API |
| **Inputs** | Structured prompts containing resume JSON + job requirements (for scoring) or raw text (for parsing) |
| **Outputs** | Structured JSON with scores, strengths, weaknesses, skill analysis, match explanation |
| **Dependencies** | GEMINI_API_KEY environment variable |

**Dual Usage:**

| Task | When Called | Input | Output |
|------|-------------|-------|--------|
| Resume Parsing | After file upload | Raw resume text | Structured candidate JSON |
| JD Parsing | When job is created | Raw JD text | Structured requirements JSON |
| Candidate Scoring | During screening | Resume JSON + JD requirements | Scores + narrative explanations |

---

### Component 8: Ranking & Scoring Engine

| Attribute | Details |
|-----------|---------|
| **Purpose** | Applies a two-phase evaluation to each candidate: first a deterministic knockout filter, then a weighted AI scoring model |
| **Technology** | Python business logic in `knockout_engine.py` and `scoring_engine.py` |
| **Inputs** | Parsed resume JSON, parsed job requirements JSON, Gemini scoring output |
| **Outputs** | `passed_knockouts` boolean, `fit_score` (0–100), category scores, `status` tier, `rank` integer |
| **Dependencies** | LLM Integration Layer (for AI scoring), fallback deterministic formulas |

**Scoring Formula:**

```
Fit Score (0–100) =
  Skills Match Score       × 40%  +
  Experience Relevance     × 25%  +
  Career Progression       × 20%  +
  Measurable Achievements  × 15%
```

---

### Component 9: File Storage Layer

| Attribute | Details |
|-----------|---------|
| **Purpose** | Saves uploaded resume files to disk, provides text extraction utilities |
| **Technology** | aiofiles 24.1.0 (async I/O), local disk storage |
| **Inputs** | Binary file content from multipart form upload |
| **Outputs** | File path on disk, extracted plain text |
| **Dependencies** | Operating system filesystem |

**Storage Path Pattern:**
`/tmp/hireflow_uploads/{user_id}/{uuid}.{ext}`

Note: The current implementation uses local disk (`/tmp`) which is not persistent across container restarts. This is an identified architectural gap addressed in Section 11.

---

### Component 10: Authentication Layer

| Attribute | Details |
|-----------|---------|
| **Purpose** | Secures all API endpoints and manages user identity across frontend and backend |
| **Technology** | python-jose (backend JWT), bcrypt (password hashing), NextAuth v4 (frontend session), HS256 algorithm |
| **Inputs** | Email/password credentials (login), JWT Bearer token (subsequent requests) |
| **Outputs** | JWT access token (login), validated user identity (per request) |
| **Dependencies** | Users table in PostgreSQL |

**Token Lifecycle:**
- Token issued on successful login (7-day expiry)
- All API requests require `Authorization: Bearer <token>` header
- Frontend (NextAuth) manages token storage and automatic header injection
- Token validation performed by FastAPI dependency on every protected endpoint

---

---

## 3. End-to-End System Architecture (Text Diagram)

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RECRUITER BROWSER                           │
│                     (Next.js 15 – React 19)                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  HTTPS / REST API
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKEND API LAYER                             │
│                   (FastAPI + Python 3.12)                           │
│                                                                     │
│   ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│   │  Auth   │  │ Resumes  │  │   Jobs    │  │    Screening     │  │
│   │ Router  │  │  Router  │  │  Router   │  │     Router       │  │
│   └─────────┘  └──────────┘  └───────────┘  └──────────────────┘  │
└──────┬──────────────┬────────────────┬───────────────┬─────────────┘
       │              │                │               │
       ▼              ▼                ▼               ▼
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────────────┐
│PostgreSQL│  │  File Storage│  │  Google  │  │    Pinecone     │
│  (RDB)   │  │  /tmp/...    │  │  Gemini  │  │  Vector Index   │
│          │  │  (Local Disk)│  │  2.0 Flash│  │  (Serverless)   │
└──────────┘  └──────────────┘  └──────────┘  └─────────────────┘
                                      │
                               ┌──────────────┐
                               │  Sentence-   │
                               │ Transformers │
                               │ (Embeddings) │
                               └──────────────┘
```

---

### 3.2 Resume Processing Architecture

```
RECRUITER UPLOADS FILE(S)
         │
         ▼
FRONTEND (react-dropzone)
─────────────────────────────────────────────────────────
         │  POST /api/resumes/bulk-upload
         ▼
BACKEND API (resumes.py)
         │
         ├──► [SYNC]  Validate file (type, size)
         │
         ├──► [SYNC]  Save file to /tmp/hireflow_uploads/{user_id}/{uuid}.ext
         │
         ├──► [SYNC]  Create UploadBatch + Resume DB records
         │
         └──► [ASYNC BACKGROUND TASK - up to 5 concurrent]
                   │
                   ├──► Extract text (pdfplumber / python-docx)
                   │
                   ├──► Parse text → Gemini LLM → Structured JSON
                   │
                   ├──► Generate Embeddings (sentence-transformers)
                   │         ├── Full Profile Vector (384-dim)
                   │         ├── Skills Vector (384-dim)
                   │         └── Experience Vector (384-dim)
                   │
                   ├──► Upsert 3 Vectors → Pinecone (with metadata)
                   │
                   └──► Update Resume DB record (parsed_data, pinecone_id, status)
```

---

### 3.3 Screening Architecture

```
RECRUITER ENTERS JD TEXT
         │
         ▼
FRONTEND (screen/page.tsx)
─────────────────────────────────────────────────────────
         │  POST /api/jobs/create → POST /api/jobs/{id}/screen
         ▼
BACKEND API (jobs.py)
         │
         ├──► [1] Parse JD text → Gemini → Structured requirements JSON
         │
         ├──► [2] Generate JD Embeddings
         │         ├── JD Full Vector (384-dim)
         │         └── JD Requirements Vector (384-dim)
         │
         ├──► [3] Semantic Search in Pinecone
         │         ├── Query: Full Profile search (weight: 50%)
         │         ├── Query: Skills search (weight: 50%)
         │         └── Return Top 100 candidates by combined score
         │
         └──► [4] ASYNC SCREENING PIPELINE (up to 3 concurrent)
                   │
                   ▼  FOR EACH CANDIDATE:
                   │
                   ├──► [4a] Fetch Resume data from PostgreSQL
                   │
                   ├──► [4b] KNOCKOUT FILTER (deterministic, fast)
                   │         ├── Rule 1: Experience years check
                   │         ├── Rule 2: Top-3 mandatory skills check
                   │         ├── Rule 3: Recent experience relevance check
                   │         ├── Rule 4: Employment gap check
                   │         ├── Rule 5: Location check
                   │         └── Rule 6: Education check
                   │         Result: passed_knockouts (true/false)
                   │
                   ├──► [4c] AI SCORING (Gemini – for passed candidates)
                   │         ├── Skills Match (0-100)
                   │         ├── Experience Relevance (0-100)
                   │         ├── Career Progression (0-100)
                   │         └── Measurable Achievements (0-100)
                   │
                   ├──► [4d] Compute Weighted Fit Score (0-100)
                   │
                   ├──► [4e] Assign Status Tier (EXCELLENT/GOOD/ADEQUATE/POOR)
                   │
                   └──► [4f] Save ScreeningResult to PostgreSQL
                             │
                             ▼
                   SORT: passed_knockouts DESC, fit_score DESC
                   ASSIGN RANK: 1, 2, 3...
                             │
                             ▼
                   RETURN RANKED RESULTS TO FRONTEND
```

---

### 3.4 Data Persistence Points

| Data Type | Where Stored | When Written |
|-----------|-------------|--------------|
| User accounts | PostgreSQL – `users` | On registration |
| Job descriptions | PostgreSQL – `job_descriptions` | On JD creation |
| Resume files (binary) | Local disk – `/tmp/hireflow_uploads/` | On upload |
| Resume metadata | PostgreSQL – `resumes` | On upload (updated after parse) |
| Resume parsed data | PostgreSQL – `resumes.parsed_data` (JSON) | After Gemini parsing |
| Resume vectors | Pinecone – `hireflow-resumes` index | After embedding generation |
| Screening results | PostgreSQL – `screening_results` | After each candidate is scored |

### 3.5 Sync vs Async Processes

| Process | Type | Reason |
|---------|------|--------|
| File validation and save | Synchronous | Must complete before responding |
| DB record creation | Synchronous | Required for tracking |
| Resume text extraction and Gemini parsing | Asynchronous (background) | Can take 2–5 seconds per file |
| Embedding generation | Asynchronous (background) | Part of parse pipeline |
| Pinecone upsert | Asynchronous (background) | Part of parse pipeline |
| JD parsing | Synchronous (inline) | Required before screening begins |
| Candidate scoring pipeline | Asynchronous (202 Accepted) | 30–60 seconds for 100 candidates |

---

---

## 4. Resume Processing Flow (Detailed)

### 4.1 Step-by-Step Processing Flow

**Step 1 – Resume Upload**

The recruiter navigates to the Upload page and drags and drops up to 200 PDF or DOCX files. The frontend validates each file's type and size (max 10MB) client-side before submission. An HTTP POST request is sent to `/api/resumes/bulk-upload` with all files as multipart form data.

**Step 2 – File Storage**

Upon receiving files, the backend validates each file server-side (type and size). Valid files are saved to local disk at the path:

```
/tmp/hireflow_uploads/{user_id}/{uuid4}.{ext}
```

An `UploadBatch` record is created in PostgreSQL to track the overall batch, and an individual `Resume` record is created for each file with `upload_status: "completed"` and `parse_status: "pending"`.

The API returns a `202 Accepted` response with the `batch_id` for progress polling.

**Step 3 – Text Extraction**

A background task is triggered (up to 5 concurrent per batch). The file is read from disk:
- **PDF files**: pdfplumber iterates through all pages and concatenates the text
- **DOCX files**: python-docx reads all paragraph and table cell text

The result is a single plain-text string containing the full resume content.

**Step 4 – Data Cleaning**

The extracted text is passed as-is to the Gemini LLM. The structured prompt instructs Gemini to intelligently handle noise, formatting artifacts, and inconsistencies inherent in resume text. Gemini is responsible for interpreting ambiguous date formats, abbreviations, and role descriptions.

**Step 5 – Embedding Generation**

After successful Gemini parsing, the sentence-transformers model (`all-MiniLM-L6-v2`) generates three distinct 384-dimensional vectors from specific portions of the parsed resume data:

| Vector | Source Content |
|--------|---------------|
| Full Profile Vector | All skills + all experience descriptions combined |
| Skills Vector | `all_skills` list concatenated as a string |
| Experience Vector | Job titles + companies + descriptions + achievement text |

**Step 6 – Pinecone Storage**

Three vectors are upserted into the Pinecone index `hireflow-resumes` with the vector ID pattern `resume_{resume_id}_{vector_type}`. Each vector carries metadata for filtering and display purposes.

**Step 7 – Metadata Storage in PostgreSQL**

The Resume record is updated with:
- `parsed_data`: Full JSON from Gemini
- `candidate_name`, `candidate_email`, `candidate_location`: Denormalized for fast querying
- `total_exp_years`, `recent_skills`, `all_skills`: Denormalized for knockout filters
- `pinecone_id`: The primary Pinecone vector ID
- `parse_status: "completed"`

---

### 4.2 Physical Storage Summary

| Layer | Data Stored | Purpose |
|-------|------------|---------|
| Local Disk | Binary PDF/DOCX file | Source file retention, re-parsing capability |
| PostgreSQL `resumes` table | File metadata, parsed JSON, candidate fields | Structured queries, screening data source |
| Pinecone Vector Index | 3 × 384-dimensional float vectors per resume | Semantic similarity search |

---

### 4.3 Data Stored in Pinecone per Resume

Each resume produces **3 vector entries** in Pinecone. Example metadata structure for the primary (full profile) vector:

```json
{
  "id": "resume_a1b2c3d4_full_profile",
  "values": [0.023, -0.145, 0.389, ...],
  "metadata": {
    "resume_id": "a1b2c3d4-...",
    "candidate_name": "Jane Smith",
    "location": "Austin, TX",
    "total_exp_years": 6.5,
    "all_skills": ["Python", "Django", "PostgreSQL", "AWS"],
    "user_id": "u9f8e7d6...",
    "vector_type": "full_profile"
  }
}
```

### 4.4 Chunking Strategy

The current implementation does **not** use text chunking. Each resume is treated as a single unit. The three vectors (full profile, skills, experience) serve as specialized views of the same document rather than positional chunks. This is an architectural simplification that trades granularity for operational simplicity.

---

---

## 5. Job Posting Processing Flow

### 5.1 Job Description Creation

When a recruiter enters raw job description text on the Screen page and clicks "Parse Job Description":

1. The frontend sends a `POST /api/jobs/create` request with the raw JD text.
2. The backend passes the text to Google Gemini with a structured extraction prompt.
3. Gemini returns a structured JSON containing all parsed requirements.
4. The parsed data is stored in the `job_descriptions` table in PostgreSQL.

### 5.2 Parsed Job Description Structure

The Gemini parsing extracts and structures the following fields from the raw JD text:

```
job_title                : "Senior Backend Engineer"
company                  : "Acme Corp" (if stated)
location                 : "Austin, TX"
required_min_exp_years   : 5.0
preferred_min_exp_years  : 7.0
required_skills          : [{"skill": "Python", "proficiency": "Expert", "years_required": 3}, ...]
nice_to_have_skills      : [{"skill": "Kubernetes"}, ...]
education_required       : "Bachelor's in Computer Science or equivalent"
locations_accepted       : ["Austin, TX", "Remote"]
willingness_to_relocate  : "Yes, with relocation package"
job_description_full     : <full original text preserved>
```

### 5.3 Embedding Generation for Job Descriptions

Two vectors are generated per job description:

| Vector | Source | Purpose |
|--------|--------|---------|
| JD Full Vector | Required skills + full JD text | Matches against resume Full Profile Vector |
| JD Requirements Vector | Required skills list concatenated | Matches against resume Skills Vector |

These vectors are generated at screening time (not stored in Pinecone) and used as the query vectors for the Pinecone search.

### 5.4 Pinecone Indexing (Job Side)

Job description vectors are **not persistently stored in Pinecone**. They are generated on-demand each time a screening run is initiated. This design choice keeps the Pinecone index exclusively as a resume index, simplifying namespace management and avoiding stale JD data.

### 5.5 Metadata Storage

All structured job data is stored in PostgreSQL. The `job_descriptions` table captures the full parsed requirements, enabling:
- Display of parsed requirements to the recruiter for verification
- Use as the scoring criteria during the LLM evaluation phase
- Historical record of all screening sessions associated with each job

---

---

## 6. Pinecone Storage Analysis

### 6.1 Vector ID Structure

Pinecone vector IDs follow a deterministic naming convention:

```
resume_{resume_id}_{vector_type}
```

**Examples:**
```
resume_a1b2c3d4-e5f6-7890-abcd-ef1234567890_full_profile
resume_a1b2c3d4-e5f6-7890-abcd-ef1234567890_skills
resume_a1b2c3d4-e5f6-7890-abcd-ef1234567890_experience
```

This structure enables:
- Easy identification of which resume each vector belongs to
- Easy deletion of all vectors for a given resume
- Vector type isolation for targeted queries

### 6.2 Embedding Values

Each vector consists of 384 floating-point numbers between approximately -1.0 and +1.0, generated by the `all-MiniLM-L6-v2` sentence-transformers model. These numbers are not human-interpretable but mathematically encode the semantic content of the source text.

### 6.3 Metadata JSON (Full Example)

```json
{
  "id": "resume_a1b2c3d4-e5f6-7890-abcd-ef1234567890_full_profile",
  "values": [0.023, -0.145, 0.389, 0.012, -0.067, ...],
  "metadata": {
    "resume_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "candidate_name": "Jane Smith",
    "location": "Austin, TX",
    "total_exp_years": 6.5,
    "all_skills": ["Python", "Django", "PostgreSQL", "Redis", "AWS", "Docker"],
    "user_id": "u9f8e7d6-c5b4-a3d2-e1f0-987654321abc",
    "vector_type": "full_profile"
  }
}
```

### 6.4 Namespace Usage

The current implementation uses the **default namespace** (no namespace isolation). This means all vectors from all recruiters and all organizations share the same searchable space. This is an architectural gap – see Section 11.

### 6.5 Similarity Metric

| Metric | Value |
|--------|-------|
| Algorithm | Cosine Similarity |
| Score Range | 0.0 (no similarity) to 1.0 (identical) |
| Interpretation | Higher score = more semantically similar |

Cosine similarity measures the angle between two vectors rather than their magnitude, making it robust to differences in text length between resumes.

### 6.6 Hybrid Search Score Computation

```
Combined Score for Candidate =
  cosine_similarity(JD_full_vector, resume_full_profile_vector) × 0.50  +
  cosine_similarity(JD_requirements_vector, resume_skills_vector)  × 0.50
```

Top 100 candidates by combined score are retrieved for further evaluation.

---

---

## 7. Embeddings – Layman Explanation

### 7.1 What Are Embeddings?

Imagine you could represent any piece of text – a resume, a job description, a skills list – as a point in space. Not two-dimensional space like a map, but a 384-dimensional space where proximity means similarity in meaning.

When we convert a resume to an embedding vector, we get 384 numbers. When we convert a job description, we get another set of 384 numbers. If the resume and job description are about similar things (e.g., both involve Python, data engineering, and cloud work), their 384 numbers will be very close together mathematically.

This is what the `all-MiniLM-L6-v2` AI model does: it reads text and outputs a "location" in this 384-dimensional meaning space.

### 7.2 Why Vector Similarity Works

Traditional keyword search would miss a candidate who lists "ML Engineering" when the job requires "Machine Learning." Vector search has no such limitation. Because the AI model was trained on vast amounts of text, it knows that "ML Engineering" and "Machine Learning" mean the same thing – and their embeddings will be nearly identical.

More importantly, vector search captures context:
- "Python for data analysis" and "data engineering with Python" are very similar
- "Java developer" and "Frontend React engineer" are very different
- "5 years of DevOps" is closer to "4 years of infrastructure" than to "5 years of UX design"

This allows HireFlow to find the best-fit candidates even when they phrase their experience differently from the job description.

### 7.3 Why Pinecone Instead of SQL Search

| Approach | SQL LIKE/ILIKE Search | Pinecone Vector Search |
|----------|----------------------|----------------------|
| Match type | Exact keyword | Semantic meaning |
| Speed at scale | Slow (full table scan) | Milliseconds (optimized index) |
| Synonym handling | No | Yes |
| Context awareness | No | Yes |
| Scalability | Degrades with size | Constant speed |

A SQL search for "Python developer" would not return a resume that says "expertise in Django and FastAPI" even though both imply Python proficiency. Pinecone would correctly identify this semantic connection.

### 7.4 The Dimensionality Concept

Why 384 dimensions? Each dimension captures a different aspect of meaning. Some dimensions might encode whether text relates to technical vs. non-technical concepts. Others might encode seniority level, domain (finance, healthcare, engineering), or specific technology families. No single dimension is interpretable in isolation – the meaning emerges from all 384 working together.

The `all-MiniLM-L6-v2` model was chosen because it produces high-quality 384-dimensional vectors that balance accuracy with computational efficiency. It runs locally without any API call, making embedding generation fast and free.

---

---

## 8. Ranking & Matching Logic

### 8.1 Full Matching Lifecycle

The matching process is a sequential five-phase pipeline executed per screening run:

```
Phase 1: Job Embedding Generation
         ↓
Phase 2: Pinecone Semantic Search → Top 100 Candidates
         ↓
Phase 3: Knockout Filter (Deterministic) → Pass / Fail
         ↓
Phase 4: AI Scoring (Gemini) → Category Scores (0–100 each)
         ↓
Phase 5: Score Aggregation + Ranking → Final Ranked List
```

---

### 8.2 Phase 1 – Job Embedding Generation

Before any candidate can be evaluated, the job description must be converted to the same vector format as resumes. Two JD vectors are generated on-demand:
- **JD Full Vector**: Captures the overall job meaning
- **JD Requirements Vector**: Captures required skill semantics specifically

---

### 8.3 Phase 2 – Pinecone Semantic Search

Two parallel Pinecone queries are executed:

**Query A:** Match JD Full Vector against all Resume Full Profile Vectors
**Query B:** Match JD Requirements Vector against all Resume Skills Vectors

Results are combined with equal weighting (50%/50%) and the top 100 candidates by combined score are selected. This set of 100 candidates is the pool that enters the subsequent phases.

The `K` value (number of candidates retrieved) is dynamically computed as:

```
K = min(max_candidates × 3, 100)
```

This retrieves more candidates than needed to allow knockout filters to thin the pool to the desired final count.

If Pinecone is unavailable, a fallback database query retrieves candidates by recency as a degraded backup.

---

### 8.4 Phase 3 – Knockout Filter (6 Deterministic Rules)

The knockout engine applies six sequential, deterministic rules. A candidate is disqualified (`passed_knockouts = false`) if **any single rule fails**. This phase runs in approximately 10–50 milliseconds per candidate.

| Rule ID | Rule Name | Logic |
|---------|-----------|-------|
| 1 | Experience Mismatch | Candidate years < required × 0.6 (40% buffer applied) |
| 2 | Missing Mandatory Skills | Any of top-3 mandatory skills absent from recent skills |
| 3 | Recent Experience Irrelevant | Overlap of required skills in last 2 years' experience < 20% |
| 4 | Employment Gap | Any employment gap > 12 months detected |
| 5 | Location Mismatch | Candidate location not in accepted locations AND relocation not accepted |
| 6 | Education Not Met | Candidate's degree text doesn't match required level keywords |

**Skill Matching in Rule 2:**
Skill matching uses a three-level check:
1. Exact case-insensitive match
2. Partial substring match (e.g., "JavaScript" matches "JS")
3. Fuzzy abbreviation matching

**Output per candidate:**
```json
{
  "passed_knockouts": false,
  "knockout_failures": [
    {
      "rule": "MISSING_MANDATORY_SKILLS",
      "reason": "Candidate's recent skills do not include 'Kubernetes', which is a mandatory requirement for this role."
    }
  ]
}
```

---

### 8.5 Phase 4 – LLM Contextual Scoring

For candidates who pass all knockout filters, Google Gemini 2.0 Flash performs a nuanced contextual evaluation across four dimensions:

| Dimension | Weight | What It Evaluates |
|-----------|--------|--------------------|
| Skills Match | 40% | Presence, depth, and recency of required skills |
| Experience Relevance | 25% | Domain alignment, role level, years vs. requirement |
| Career Progression | 20% | Trajectory, advancement, increasing responsibility |
| Measurable Achievements | 15% | Quantified impact (%, $, headcount, latency reduction) |

Each dimension receives a score from 0 to 100. Gemini also produces:
- Up to 4 **strength statements** (specific and evidence-backed)
- Up to 3 **weakness/gap statements** (specific and evidence-backed)
- A `match_explanation` (2–3 sentence recruiter-ready summary)
- A `skills_matched` list with confidence and years for each matched skill
- A `skills_missing` list with importance levels

**Fallback (Deterministic Scoring):** If Gemini is unavailable, the scoring engine applies mathematical formulas using parsed resume data:

| Dimension | Fallback Formula |
|-----------|-----------------|
| Skills Match | `(recent_matches / required_skills) × 75% + (all_matches / required_skills) × 25%` |
| Experience Relevance | `min(candidate_years / required_years, 1.5) × 70` |
| Career Progression | `min(40 + num_roles × 10, 100)` |
| Measurable Achievements | `min(30 + total_achievements × 5, 100)` |

---

### 8.6 Phase 5 – Score Aggregation and Ranking

**Weighted Fit Score:**
```
Fit Score = (Skills Match × 0.40) + (Experience Relevance × 0.25) +
            (Career Progression × 0.20) + (Measurable Achievements × 0.15)
```

**Status Tier Assignment:**

| Score Range | Status | Recruiter Interpretation |
|-------------|--------|--------------------------|
| 86 – 100 | EXCELLENT | Immediate interview recommended |
| 61 – 85 | GOOD | Schedule interview for review |
| 31 – 60 | ADEQUATE | Backup pool; consider if pipeline is thin |
| 0 – 30 | POOR | Not recommended for this role |

**Final Ranking:**

Candidates are sorted in the following priority order:
1. `passed_knockouts = true` always ranks above `passed_knockouts = false`
2. Within the passed group: sorted by `fit_score` descending
3. Rank integers (1, 2, 3...) are assigned only to knockout-passed candidates
4. Failed knockout candidates are stored but appear at the bottom with `rank = 0`

---

---

## 9. LLM Interaction Flow

### 9.1 Overview of LLM Calls

Google Gemini 2.0 Flash is called at three distinct points in the HireFlow workflow:

| Call | Trigger | Input | Output |
|------|---------|-------|--------|
| Resume Parsing | Post file upload (background) | Raw resume text | Structured candidate JSON |
| JD Parsing | Job creation | Raw JD text | Structured requirements JSON |
| Candidate Scoring | Screening pipeline | Resume JSON + JD requirements | Scores + narrative evaluations |

---

### 9.2 Data Passed to LLM for Scoring

HireFlow does not pass the full raw resume text to Gemini for scoring. Instead, it passes the **structured parsed JSON** (extracted during resume parsing). This offers significant advantages:

- **Token efficiency**: Structured JSON is more compact than formatted resume text
- **Consistency**: Gemini evaluates structured data rather than interpreting formatting
- **Reliability**: Parsing artifacts do not affect scoring
- **Cost control**: Fewer tokens consumed per scoring call

**What is passed:**
1. The full parsed resume JSON (candidate profile, skills, experience, education, certifications)
2. The full parsed job requirements JSON (required skills, minimum experience, nice-to-haves, education requirements)

---

### 9.3 Scoring Prompt Structure (Documentation Example)

The scoring prompt is a structured instruction set sent to Gemini. The following is a representative example for documentation purposes:

```
You are an expert recruiter with 15 years of experience evaluating candidates for
senior technical roles. Your task is to score the following candidate's resume
against the provided job description.

CANDIDATE PROFILE:
{
  "candidate_name": "Jane Smith",
  "total_exp_years": 6.5,
  "all_skills": ["Python", "Django", "PostgreSQL", "Redis", "AWS", "Docker"],
  "recent_skills": ["Python", "Django", "PostgreSQL"],
  "experience": [
    {
      "title": "Backend Engineer",
      "company": "TechCorp",
      "duration_years": 4.0,
      "achievements": ["Reduced API latency by 35%", "Led team of 4 engineers"],
      "skills_used": ["Python", "Django", "PostgreSQL"]
    }
  ],
  "education": [{"degree": "B.S. Computer Science", "institution": "UT Austin"}],
  "certifications": [{"name": "AWS Certified Developer"}]
}

JOB REQUIREMENTS:
{
  "job_title": "Senior Backend Engineer",
  "required_min_exp_years": 5,
  "required_skills": [
    {"skill": "Python", "proficiency": "Expert"},
    {"skill": "PostgreSQL", "proficiency": "Intermediate"},
    {"skill": "AWS", "proficiency": "Intermediate"}
  ],
  "nice_to_have_skills": [{"skill": "Kubernetes"}],
  "education_required": "Bachelor's in Computer Science or equivalent"
}

Evaluate the candidate on 4 dimensions (each 0-100):
1. Skills Match (0-100): Evaluate presence, recency, and depth of required skills
2. Experience Relevance (0-100): Domain alignment, role level, and years match
3. Career Progression (0-100): Upward trajectory, increasing responsibility
4. Measurable Achievements (0-100): Quantified impact with metrics

Return ONLY valid JSON with no additional text:
{
  "scores": {
    "skills_match": <integer 0-100>,
    "experience_relevance": <integer 0-100>,
    "career_progression": <integer 0-100>,
    "measurable_achievements": <integer 0-100>
  },
  "strengths": ["Specific strength 1", "Specific strength 2", "...", "..."],
  "weaknesses": ["Specific gap 1", "Specific gap 2", "Specific gap 3"],
  "skills_matched": [
    {
      "required_skill": "Python",
      "candidate_skill": "Python",
      "match_confidence": 0.95,
      "years_in_profile": 4
    }
  ],
  "skills_missing": [
    {
      "required_skill": "Kubernetes",
      "candidate_has": false,
      "importance": "low"
    }
  ],
  "match_explanation": "Jane Smith is a strong candidate for this Senior Backend Engineer role, with 6.5 years of Python and PostgreSQL experience that directly aligns with the core requirements. Her AWS certification and quantified achievements demonstrate both cloud competency and measurable impact."
}
```

### 9.4 Token Optimization Strategy

| Strategy | Implementation |
|----------|---------------|
| Structured JSON input | Resume parsed data (not raw text) sent to LLM |
| Minimal prompt | Concise instruction format, no lengthy preamble |
| JSON-only response | Gemini instructed to return only JSON, no markdown |
| Retry with backoff | 3 retries prevent redundant first-attempt failures |
| Deterministic fallback | Zero LLM tokens consumed if API is unavailable |
| Parallelism cap | Max 3 concurrent scoring calls (controls burst spend) |

---

---

## 10. Integrated Data Flow

### 10.1 Complete End-to-End Lifecycle

```
RECRUITER INITIATES SCREENING SESSION
           │
           │  "Find me the best Python engineers for this role"
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Job Description Creation                           │
│  POST /api/jobs/create                                      │
│  Backend → Gemini LLM → Structured JD JSON                  │
│  Backend → PostgreSQL → Save job_descriptions record        │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: JD Embedding Generation                            │
│  sentence-transformers → JD Full Vector (384-dim)           │
│  sentence-transformers → JD Requirements Vector (384-dim)   │
│  [Vectors NOT stored; generated fresh per screening run]    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Pinecone Semantic Search                           │
│  Query A: JD Full Vector vs. all Resume Full Profile Vectors│
│  Query B: JD Requirements Vector vs. all Skills Vectors     │
│  Combine scores: 50% Query A + 50% Query B                  │
│  Retrieve Top 100 candidate resume_ids                      │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Metadata Fetch from PostgreSQL                     │
│  SELECT * FROM resumes WHERE id IN (top_100_resume_ids)     │
│  Retrieves parsed_data JSON for each candidate              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Knockout Filter (Concurrent, up to 3 at once)      │
│  Apply 6 deterministic rules per candidate                  │
│  Output: passed_knockouts boolean + failure reasons         │
└────────────────────────────┬────────────────────────────────┘
                             │
                     ┌───────┴───────┐
                     │               │
             PASSED KNOCKOUTS   FAILED KNOCKOUTS
                     │               │
                     ▼               ▼
┌────────────────────────┐  ┌──────────────────────────────────┐
│  STEP 6: Gemini Scoring│  │  Store result with knockout      │
│  Resume JSON + JD JSON │  │  failure details. No AI scoring. │
│  → Category Scores     │  │  rank = 0                        │
│  → Strengths/Weaknesses│  └──────────────────────────────────┘
│  → Match Explanation   │
└───────────┬────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 7: Weighted Score Computation                         │
│  Fit Score = (Skills×0.40) + (Exp×0.25) + (Prog×0.20)      │
│            + (Achieve×0.15)                                 │
│  Status = EXCELLENT / GOOD / ADEQUATE / POOR                │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 8: Sort and Rank                                      │
│  ORDER BY passed_knockouts DESC, fit_score DESC             │
│  Assign rank integers 1, 2, 3...                           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 9: Persist to PostgreSQL                              │
│  INSERT INTO screening_results (all fields per candidate)   │
│  UPDATE job_descriptions.screening_count += 1               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 10: Return Ranked Results to Frontend                 │
│  GET /api/jobs/{job_id}/screening-results                   │
│  Frontend renders ranked candidate cards                    │
│  Recruiter reviews, shortlists, or exports CSV             │
└─────────────────────────────────────────────────────────────┘
```

---

### 10.2 Orchestration Summary

The screening pipeline is orchestrated by the `jobs.py` router's `_screen_candidates` background function. Key orchestration characteristics:

- **Async concurrency**: Python `asyncio.Semaphore(3)` limits concurrent scoring to 3 candidates simultaneously
- **Error isolation**: A scoring failure for one candidate does not stop the pipeline; it logs the error and continues
- **Partial results**: Results are persisted incrementally as each candidate is scored, enabling partial result retrieval
- **Progress visibility**: The `GET /jobs/{job_id}/screening-status` endpoint allows the frontend to poll for completion

---

---

## 11. Current Gaps / Observed Limitations

### 11.1 No Namespace Isolation in Pinecone

**Description:** All recruiter resume vectors share the default Pinecone namespace. A recruiter's semantic search retrieves from the global pool, not just their own uploaded resumes.

**Business Impact:** In a multi-tenant SaaS environment, this would expose candidates across organizational boundaries and produce inaccurate results. Currently mitigated by filtering on `user_id` in metadata, but this is a post-retrieval filter rather than a pre-retrieval partition – it is less efficient and less secure.

---

### 11.2 No Structured Tagging System

**Description:** Resumes and job descriptions are stored with raw skill lists and parsed text but no standardized tag taxonomy. "JavaScript," "JS," "ECMAScript," and "ES6" are all treated as separate entities unless the LLM happens to unify them.

**Business Impact:** Reduces precision of skill-based matching and makes reporting on "how many Python engineers do we have?" unreliable. Search recall is unpredictable across different skill naming conventions.

---

### 11.3 No Skill Ontology

**Description:** HireFlow has no internal knowledge graph or taxonomy mapping related skills (e.g., "React" → "JavaScript framework" → "Frontend"), technology families, or seniority implications of skill combinations.

**Business Impact:** The system cannot reason about implied skills (knowing React implies JavaScript knowledge) or identify transferable skills across adjacent domains.

---

### 11.4 No Metadata Pre-Filtering Before Vector Search

**Description:** Pinecone is queried without pre-filters (e.g., filter to only candidates with `total_exp_years >= 4` before semantic ranking). All metadata filtering happens after retrieval.

**Business Impact:** For recruiters with large resume pools (thousands of candidates), this means irrelevant candidates consume search capacity and degrade result quality. Pinecone supports metadata filtering natively, but it is not currently utilized.

---

### 11.5 No Hybrid Keyword + Vector Search

**Description:** The system relies entirely on vector (semantic) similarity. There is no BM25 or keyword-based retrieval component that could be blended with vector scores.

**Business Impact:** For highly specific technical requirements (e.g., a niche certification like "Certified SAFe® 6.0 Agilist"), vector search may rank generalists ahead of the exact-match candidate. Hybrid search would guarantee that exact matches receive a boosted score.

---

### 11.6 Local Disk File Storage (Non-Persistent)

**Description:** Uploaded resume files are stored at `/tmp/hireflow_uploads/` on the server's local filesystem. In containerized environments, this storage is ephemeral and lost on container restart.

**Business Impact:** Loss of original files means re-upload would be required after any server restart or redeployment. Cloud object storage (S3, GCS, Azure Blob) is the appropriate solution for production.

---

### 11.7 Limited Explainability

**Description:** While strengths, weaknesses, and match explanations are generated, the system does not provide insight into *why* a candidate scored 73 vs. 72. The LLM's scoring rationale is a black box beyond the narrative statements.

**Business Impact:** Recruiters may distrust rankings they cannot fully audit, especially when defending hiring decisions to hiring managers or HR compliance teams.

---

### 11.8 No Recruiter Feedback Learning Loop

**Description:** When a recruiter shortlists or rejects a candidate, this action is stored in the database (`is_shortlisted` field) but is never used to improve future rankings for that recruiter.

**Business Impact:** The system cannot learn individual recruiter preferences or organizational hiring patterns over time. Every screening session starts from scratch with no institutional memory.

---

### 11.9 No Resume Classification Layer

**Description:** Resumes are not pre-classified into domains (e.g., "Software Engineering," "Data Science," "Product Management," "Sales") before entry into the vector index.

**Business Impact:** A job description for a Data Scientist may semantically match resumes from Research Scientists or Statisticians that are ultimately wrong-domain matches. A classification layer would allow domain-level pre-filtering.

---

### 11.10 Redis Cache Not Integrated

**Description:** Redis is provisioned in the Docker Compose file but the application code does not explicitly use it for session caching, rate limiting, or result caching.

**Business Impact:** Every identical request (e.g., viewing the same screening results page) re-queries the database. At scale, this creates unnecessary database load.

---

---

## 12. Tagging & Metadata Strategy (Conceptual Recommendation)

> ⚠️ This section is **conceptual documentation only**. It describes architectural direction without specifying any code changes.

### 12.1 Why Tagging Is Necessary

The current system stores resumes as blobs of parsed text and flat skill lists. While effective for semantic search, this structure cannot support:
- Precision filtering (e.g., "show only AWS-certified candidates in Austin")
- Structured analytics (e.g., "which required skills are hardest to find?")
- Meaningful comparison (e.g., "which candidates have React AND Node.js?")

Tagging transforms free-text data into structured, queryable attributes.

---

### 12.2 Recommended Tag Categories

#### Category 1: Technical Skills
Normalized skill names mapped to a canonical taxonomy:

| Raw Skill | Canonical Tag | Category |
|-----------|--------------|---------|
| Python, py | `python` | programming_language |
| React.js, ReactJS | `react` | frontend_framework |
| PostgreSQL, Postgres | `postgresql` | database |
| K8s, Kubernetes | `kubernetes` | infrastructure |
| ML, Machine Learning | `machine_learning` | ai_ml |

#### Category 2: Domain / Industry
High-level industry alignment:

- `software_engineering` / `data_engineering` / `data_science` / `devops`
- `finance_tech` / `healthcare_tech` / `ecommerce`
- `product_management` / `ux_design` / `sales_engineering`

#### Category 3: Seniority Level
Mapped from experience years and title keywords:

| Years Experience | Title Signal | Tag |
|-----------------|-------------|-----|
| 0–2 | "Associate," "Junior," "I" | `entry_level` |
| 2–5 | "Engineer," "Developer" | `mid_level` |
| 5–10 | "Senior," "Lead," "Staff" | `senior` |
| 10+ | "Principal," "Director," "VP" | `staff_plus` |

#### Category 4: Location / Work Mode
Standardized location tags:

- City-level: `austin_tx` / `new_york_ny` / `san_francisco_ca`
- Country: `us` / `uk` / `canada`
- Work mode: `remote_ok` / `hybrid` / `onsite_only`

#### Category 5: Certifications
Recognized certification identifiers:

- `aws_certified_developer` / `aws_solutions_architect`
- `google_professional_cloud` / `azure_fundamentals`
- `pmp` / `cpa` / `cissp`

---

### 12.3 Where Tags Should Be Stored

Tags should be stored in two complementary locations:

**In PostgreSQL (for structured querying):**
A normalized `tags` JSON field on the `resumes` and `job_descriptions` tables, or a dedicated `resume_tags` junction table for efficient SQL filtering:

```
resumes.tags = {
  "skills": ["python", "django", "postgresql"],
  "domain": ["software_engineering"],
  "seniority": "senior",
  "location": "austin_tx",
  "work_mode": "remote_ok",
  "certifications": ["aws_certified_developer"]
}
```

**In Pinecone Metadata (for pre-retrieval filtering):**
The same structured tags included in the Pinecone vector metadata enable Pinecone's native metadata filtering to exclude irrelevant candidates *before* semantic scoring. This dramatically improves precision and speed for large datasets.

---

### 12.4 How Metadata Filtering Improves Precision

Without metadata filtering, a Pinecone query for "Senior Python Developer in Austin" returns the top 100 most semantically similar resumes globally. Many may be junior candidates or located in other cities.

With metadata filtering, the same query can restrict the search space:

```
Filter: {
  "seniority": "senior",
  "skills": {"$in": ["python"]},
  "location": {"$in": ["austin_tx", "remote_ok"]}
}
```

This means Pinecone only searches within the qualified subset, returning more precise semantic matches within the correct population.

**Result:** Higher relevance of top-K results, lower LLM scoring waste (fewer irrelevant candidates consuming Gemini tokens), and more defensible ranking logic.

---

---

## 13. Tech Stack Overview

### 13.1 Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Next.js | 15.x | React-based full-stack framework with App Router |
| UI Library | React | 19.x | Component-based UI rendering |
| Language | TypeScript | 5.x | Type-safe JavaScript |
| Styling | Tailwind CSS | 3.x | Utility-first CSS framework |
| UI Primitives | Radix UI | Latest | Accessible, unstyled UI components |
| Icons | lucide-react | Latest | SVG icon library |
| Form Handling | react-hook-form + zod | Latest | Form state and validation |
| Global State | Zustand | 5.0 | Lightweight state management |
| HTTP Client | Axios | 1.7.9 | REST API communication with interceptors |
| Authentication | NextAuth | v4 | JWT session management for frontend |
| File Upload | react-dropzone | Latest | Drag-and-drop file upload UI |
| Charts | Recharts | 2.14 | Data visualization for dashboard |
| Notifications | react-hot-toast | Latest | Toast notification system |

---

### 13.2 Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | 0.115.6 | Async Python REST API framework |
| Runtime | Python | 3.12+ | Backend language |
| ASGI Server | Uvicorn | 0.34.0 | Production-grade async server (2 workers) |
| ORM | SQLAlchemy | 2.0.36 | Async database access layer |
| DB Driver | asyncpg | Latest | Async PostgreSQL driver |
| Migrations | Alembic | 1.14.0 | Database schema version control |
| Auth | python-jose | Latest | JWT creation and validation (HS256) |
| Passwords | bcrypt | Latest | Password hashing (cost factor 12) |
| Logging | structlog | 24.4.0 | Structured JSON logging |
| PDF Parsing | pdfplumber | 0.11.4 | PDF text extraction |
| DOCX Parsing | python-docx | 1.1.2 | Word document text extraction |
| File I/O | aiofiles | 24.1.0 | Async file read/write operations |

---

### 13.3 Database

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Primary DB | PostgreSQL 16 | Relational data (users, jobs, resumes, results) |
| Cache | Redis 7 | Session caching (provisioned; not fully integrated) |
| Connection Pool | asyncpg pool | 10 base connections, 20 overflow |

---

### 13.4 AI & ML Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | Google Gemini 2.0 Flash | Resume/JD parsing and candidate scoring |
| Embedding Model | all-MiniLM-L6-v2 | 384-dim semantic vector generation |
| Embedding Library | sentence-transformers | Local model inference |
| Vector Database | Pinecone Serverless | Semantic similarity search |

---

### 13.5 Infrastructure & Deployment

| Component | Technology | Environment |
|-----------|-----------|-------------|
| Containerization | Docker (multi-stage builds) | All environments |
| Orchestration | Docker Compose v2 | Development / self-hosted |
| Frontend Hosting | Vercel | Production |
| Backend Hosting | Railway / Render | Production |
| Database Hosting | Railway PostgreSQL / Supabase | Production |
| Vector DB | Pinecone Cloud | Production |
| CI/CD | GitHub Actions | Automated testing and deployment |

---

---

## 14. Scalability Considerations

### 14.1 High-Volume Resume Handling

The system accepts up to 200 resumes per upload batch. Background processing with a semaphore limit of 5 concurrent parsings prevents resource saturation. At an average of 3 seconds per resume (Gemini parse + embedding), 200 resumes would process in approximately 2 minutes with 5-way parallelism.

**For higher volume (1,000+ resumes):**
- Implement a proper task queue (Celery + Redis) to distribute work across multiple workers
- Replace per-request background tasks with a persistent worker pool
- Add batch embedding (process multiple resumes in a single model.encode() call)

---

### 14.2 Batch Embedding

The current implementation generates embeddings one resume at a time. The sentence-transformers library supports batch encoding, which is significantly faster for large sets:

```
# Current (sequential):    100 resumes × 50ms = 5 seconds
# Batch encoding:          100 resumes in single call ≈ 500ms
```

Batching should be implemented when processing queues exceed 10 resumes simultaneously.

---

### 14.3 Pinecone Index Scaling

Pinecone Serverless automatically scales read/write throughput based on demand. With 3 vectors per resume:

| Resume Count | Pinecone Vectors | Notes |
|-------------|-----------------|-------|
| 1,000 | 3,000 | Free tier sufficient |
| 100,000 | 300,000 | Standard serverless plan |
| 1,000,000 | 3,000,000 | Enterprise plan required |

For multi-tenant deployments, namespaces should isolate each organization's vectors to prevent cross-contamination and enable per-namespace deletion.

---

### 14.4 Async Processing

The FastAPI backend is fully async-native. All I/O operations (database queries, file reads, API calls) are non-blocking using Python's `asyncio`. This allows a single server process with 2 Uvicorn workers to handle many concurrent requests efficiently.

For the screening pipeline, the `asyncio.Semaphore(3)` limit is the primary concurrency control, tunable via configuration for more powerful servers.

---

### 14.5 Database Connection Pool

PostgreSQL connections are pooled with:
- **Base pool size**: 10 connections
- **Overflow**: 20 additional connections under peak load

For high-volume deployments, PgBouncer (connection pooler) should be placed between the application and PostgreSQL to reduce connection overhead.

---

### 14.6 Caching Strategy

**Current state:** Redis is deployed but not actively used for caching.

**Recommended caching targets:**

| Data | Cache Key | TTL | Benefit |
|------|-----------|-----|---------|
| Dashboard stats | `stats:{user_id}` | 5 min | Avoids repeated aggregate queries |
| Screening results | `results:{job_id}` | 1 hour | Instant re-loads for the same session |
| Resume list | `resumes:{user_id}:page:{n}` | 2 min | Reduces DB load during pagination |

---

---

## 15. Security & Compliance

### 15.1 Authentication & Authorization

| Mechanism | Implementation |
|-----------|---------------|
| Password Hashing | bcrypt with cost factor 12 (~100ms intentional slowdown against brute force) |
| Token Format | JWT (JSON Web Token), HS256 algorithm |
| Token Expiry | 7 days |
| Token Location | HTTP Authorization header (Bearer scheme) – not in cookies or URL |
| Secret Length | Minimum 32 characters, randomly generated |
| Role Enforcement | Every protected endpoint checks user role via FastAPI dependency injection |

### 15.2 API Security

| Control | Implementation |
|---------|---------------|
| CORS | Configured to allow only specified origins (localhost:3000 in dev) |
| Rate Limiting | 100 requests/minute per IP (in-memory counter) |
| Input Validation | All request bodies validated by Pydantic models before processing |
| SQL Injection | Prevented by SQLAlchemy ORM (parameterized queries; no raw SQL interpolation) |
| File Upload Validation | Type check (allowlist: PDF, DOCX) and size check (max 10MB) on both client and server |

### 15.3 PII Handling

Resume data contains sensitive personal information: names, email addresses, phone numbers, and location data.

**Current Implementation:**
- PII is stored in PostgreSQL `parsed_data` JSON and denormalized columns
- Access is controlled by user_id association (recruiters only see their own uploads)
- Files are stored on local disk with path obfuscation via UUID naming

**Gaps:**
- No encryption at rest for resume files or parsed data
- No data retention policy or automatic deletion schedule
- No anonymization option for archived resumes

### 15.4 Infrastructure Security

| Control | Implementation |
|---------|---------------|
| Container Security | Docker containers run as non-root user (`appuser`) |
| Secret Management | All sensitive values (API keys, DB passwords, JWT secrets) in environment variables; `.env` excluded from git via `.gitignore` |
| HTTPS | Enforced at the hosting layer (Vercel for frontend, Railway for backend) |
| Dependency Security | Python packages pinned in `requirements.txt`; Node packages in `package-lock.json` |

### 15.5 Audit Logging

**Current state:** The `GET /admin/logs` endpoint is a documented stub (placeholder) – it exists in the API contract but returns no data. Real audit logging is partially implemented via `structlog` at service level (logging key events to stdout).

**Gap:** No database-persisted audit trail for compliance use cases (who accessed which resume, when was a candidate shortlisted, who exported data).

### 15.6 Data Retention

**Current state:** No automated data retention or deletion policies are implemented. Resume files, parsed data, and screening results accumulate indefinitely.

**Compliance consideration:** GDPR, CCPA, and similar regulations may require:
- Right to erasure (candidate requests deletion of their resume)
- Data retention limits (e.g., delete resumes after 12 months of inactivity)
- Explicit consent tracking for resume storage

---

---

## 16. Conclusion

### 16.1 Architecture Maturity

HireFlow represents a **well-structured, production-viable first iteration** of an AI-powered resume screening system. The architectural choices are modern, composable, and grounded in real-world engineering patterns. The separation of concerns between parsing (Gemini), indexing (Pinecone), scoring (Gemini + deterministic fallback), and storage (PostgreSQL) reflects mature multi-service design thinking.

---

### 16.2 Strengths

| Strength | Description |
|----------|-------------|
| Modern Tech Stack | Next.js 15 + FastAPI + PostgreSQL + Pinecone is a production-grade, cloud-native combination |
| Dual-Layer Screening | Knockout filters provide instant disqualification before expensive LLM calls, optimizing cost |
| Explainability | Strengths, weaknesses, skill match analysis, and match explanations are generated per candidate |
| Async Architecture | Fully async backend enables high concurrency without blocking |
| Graceful Degradation | Deterministic fallback scoring when Gemini is unavailable prevents service failures |
| Containerized Deployment | Docker Compose enables reproducible, one-command deployment |
| Type Safety | TypeScript on the frontend + Pydantic on the backend enforce data contract integrity |
| Observability Foundation | structlog provides structured logging ready for log aggregation services |

---

### 16.3 Risks

| Risk | Severity | Description |
|------|----------|-------------|
| Local File Storage | High | Resume files lost on container restart; not suitable for production |
| No Pinecone Namespacing | High | Multi-tenant data leakage risk in shared deployments |
| Redis Not Utilized | Medium | Provisioned but unused; represents operational overhead without benefit |
| No Audit Trail | Medium | Compliance exposure for GDPR/CCPA scenarios |
| Gemini API Dependency | Medium | Screening quality degrades significantly on Gemini unavailability |
| Rate Limiting In-Memory | Low | Rate limiter resets on server restart; not suitable for multi-process deployments |

---

### 16.4 Identified Gaps

| Priority | Gap | Business Impact |
|----------|-----|----------------|
| 1 | Cloud file storage (S3/GCS) | Production readiness |
| 2 | Pinecone namespace isolation | Data security in multi-tenant use |
| 3 | Structured tagging system | Precision and analytics |
| 4 | Metadata pre-filtering | Search quality at scale |
| 5 | Hybrid keyword + vector search | Exact match guarantee |
| 6 | Redis cache integration | Performance at scale |
| 7 | Audit logging | Compliance readiness |
| 8 | Data retention policies | Regulatory compliance |
| 9 | Recruiter feedback loop | Continuous improvement |
| 10 | Skill ontology / taxonomy | Semantic precision |

---

### 16.5 Strategic Improvement Direction

HireFlow has successfully established the core matching pipeline. The next phase of development should focus on three strategic tracks:

**Track 1 – Production Hardening**
Replace local file storage with cloud object storage, implement Pinecone namespace isolation, activate Redis caching, and establish audit logging and data retention policies.

**Track 2 – Precision Improvement**
Build a structured tagging and skill taxonomy system, implement Pinecone metadata pre-filtering, and introduce hybrid keyword + vector search to improve result relevance, especially for highly specific technical roles.

**Track 3 – Intelligence Accumulation**
Implement a recruiter feedback loop where shortlisting and rejection decisions improve future ranking weights. Build per-organization preference models that learn which candidate profiles have historically succeeded. This transforms HireFlow from a one-time screener into a continuously improving recruiting intelligence platform.

---

---

*Document End*

---

**Document Metadata**

| Field | Value |
|-------|-------|
| System Analyzed | HireFlow – AI Resume Screening System |
| Codebase Branch | dev |
| Codebase Commit | 6d4de83 (feat: initial HireFlow implementation) |
| Analysis Date | February 2026 |
| Document Version | 1.0 |
| Total Sections | 16 |
| Analysis Scope | Full codebase – frontend, backend, services, models, configs, Docker |
