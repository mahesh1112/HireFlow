# HireFlow — AI-Powered Resume Screening System

> Automatically shortlist the best candidates from hundreds of resumes using Google Gemini AI, semantic vector search (Pinecone), and deterministic knockout filters.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 + React 19 + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python 3.12+) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 (optional) |
| Vector DB | Pinecone (Serverless) |
| AI/LLM | Google Gemini 2.0 Flash |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| Auth | NextAuth v4 + JWT (HS256) |

---

## Recruiter Workflow

1. **Register/Login** → Secure recruiter account
2. **Upload Resumes** → Bulk upload 100+ PDF/DOCX files (AI parses in background)
3. **Paste Job Description** → Full JD text input
4. **Screen Candidates** → AI applies knockout filters + scoring in seconds
5. **Review Top-20 List** → Ranked candidates with fit scores & explanations
6. **Shortlist & Export** → Select candidates → Export as CSV

---

## Scoring Algorithm

```
Fit Score (0-100) = Skills Match × 40% + Experience Relevance × 25%
                  + Career Progression × 20% + Achievements × 15%
```

| Score | Status | Action |
|-------|--------|--------|
| 86-100 | EXCELLENT | Immediate interview |
| 61-85  | GOOD | Schedule interview |
| 31-60  | ADEQUATE | Backup pool |
| 0-30   | POOR | Auto-reject |

---

## Knockout Filters (Instant Reject)

- Experience years below 60% of requirement
- Missing any top-3 mandatory skills in recent experience
- Employment gaps > 12 months
- Location mismatch (when remote not allowed)
- Education requirements not met

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16
- API keys: Google Gemini, Pinecone

### 1. Clone & Configure

```bash
git clone https://github.com/sonal-pawar/HireFlow.git
cd HireFlow
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY, PINECONE_API_KEY, DATABASE_URL, JWT_SECRET
```

### 2. PostgreSQL Setup

```bash
# Connect as superuser
psql -U postgres

# Run these SQL commands:
CREATE USER hireflow WITH PASSWORD 'your_password';
CREATE DATABASE hireflow OWNER hireflow;
GRANT ALL PRIVILEGES ON DATABASE hireflow TO hireflow;
\q
```

Update `.env`:
```env
DATABASE_URL=postgresql+asyncpg://hireflow:your_password@localhost:5432/hireflow
```

### 3. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Tables are created automatically on first startup.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

---

## Docker Deployment (Recommended)

### Prerequisites

- Docker 24+
- Docker Compose v2

### 1. Configure Environment

```bash
cp .env.example .env
# Set your API keys in .env
```

Required `.env` values for Docker:

```env
# AI Services
GEMINI_API_KEY=your_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=hireflow-resumes
PINECONE_ENVIRONMENT=us-east-1

# Database (used by docker-compose)
POSTGRES_USER=hireflow
POSTGRES_PASSWORD=your_strong_password
POSTGRES_DB=hireflow
DATABASE_URL=postgresql+asyncpg://hireflow:your_strong_password@db:5432/hireflow

# Auth
JWT_SECRET=your-min-32-char-secret-key-here
NEXTAUTH_SECRET=your-min-32-char-nextauth-secret

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXTAUTH_URL=http://localhost:3000
```

### 2. Start All Services

```bash
docker compose up --build
```

This starts:
- **PostgreSQL 16** on port 5432
- **Redis 7** on port 6379
- **FastAPI backend** on port 8000
- **Next.js frontend** on port 3000

### 3. Stop Services

```bash
docker compose down           # Stop containers
docker compose down -v        # Stop + remove volumes (clears DB)
```

### Docker Architecture

```
┌─────────────────────────────────────────────────┐
│  Docker Compose Network: hireflow-network        │
│                                                  │
│  ┌──────────┐   ┌──────────┐   ┌─────────────┐  │
│  │ frontend │→  │ backend  │→  │ PostgreSQL  │  │
│  │  :3000   │   │  :8000   │   │   :5432     │  │
│  └──────────┘   └────┬─────┘   └─────────────┘  │
│                      │                           │
│                 ┌────┴──────┐                    │
│                 │  Redis    │                    │
│                 │  :6379    │                    │
│                 └───────────┘                    │
└─────────────────────────────────────────────────┘
         │                    │
    Pinecone (cloud)   Google Gemini (cloud)
```

---

## Production Deployment

### Frontend → Vercel

1. Import the repo on [vercel.com](https://vercel.com)
2. Set **Root Directory** to `frontend`
3. Set **Framework Preset** to `Next.js`
4. Add all environment variables from `.env`:

```env
NEXT_PUBLIC_API_URL=https://your-backend-domain.com/api
NEXT_PUBLIC_APP_URL=https://your-frontend-domain.vercel.app
NEXTAUTH_URL=https://your-frontend-domain.vercel.app
NEXTAUTH_SECRET=<strong-random-secret>
```

5. Deploy — Vercel handles CI/CD automatically on push.

### Backend → Railway

1. Create a new project on [railway.app](https://railway.app)
2. Connect your GitHub repo, set **Root Directory** to `backend`
3. Railway auto-detects the `Dockerfile`
4. Add environment variables:

```env
GEMINI_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=hireflow-resumes
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/hireflow
JWT_SECRET=<strong-random-secret>
ALLOWED_ORIGINS=["https://your-frontend.vercel.app"]
ENVIRONMENT=production
DEBUG=false
```

5. Add a **PostgreSQL** plugin in Railway — it auto-injects `DATABASE_URL`.

### Backend → Render

1. New Web Service → connect repo → set **Root Directory** to `backend`
2. **Runtime**: Docker
3. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add the same environment variables as Railway above.

### Database → Supabase (Alternative to Railway PostgreSQL)

1. Create a project on [supabase.com](https://supabase.com)
2. Go to **Project Settings → Database** and copy the connection string
3. Use the pooled connection string for the backend:

```env
DATABASE_URL=postgresql+asyncpg://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### Vector DB → Pinecone

1. Create an account on [pinecone.io](https://pinecone.io)
2. Create a **Serverless** index:
   - Name: `hireflow-resumes`
   - Dimensions: `384`
   - Metric: `cosine`
   - Cloud: `AWS`, Region: `us-east-1`
3. Copy your API key to `.env`

### Cache → Upstash Redis (Optional)

1. Create a Redis database on [upstash.com](https://upstash.com)
2. Copy the Redis URL:

```env
REDIS_URL=rediss://default:password@host.upstash.io:6379
```

> Redis is optional. Leave `REDIS_URL=` empty to run without caching.

### Production Environment Variables Summary

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google AI Studio API key | Yes |
| `PINECONE_API_KEY` | Pinecone API key | Yes |
| `PINECONE_INDEX_NAME` | Pinecone index name | Yes |
| `DATABASE_URL` | PostgreSQL async connection URL | Yes |
| `JWT_SECRET` | Min 32-char random string | Yes |
| `NEXTAUTH_SECRET` | Min 32-char random string | Yes |
| `NEXTAUTH_URL` | Full frontend URL (with https) | Yes |
| `NEXT_PUBLIC_API_URL` | Full backend API URL | Yes |
| `REDIS_URL` | Redis connection URL | No |
| `ALLOWED_ORIGINS` | JSON array of allowed CORS origins | Yes |
| `ENVIRONMENT` | `production` | Yes |
| `DEBUG` | `false` | Yes |

---

## API Documentation

Full OpenAPI docs available at: `http://localhost:8000/docs`

### Key Endpoints

```
POST /api/auth/register          Register new recruiter
POST /api/auth/login             Login (form-encoded)
GET  /api/auth/profile           Get current user
POST /api/resumes/bulk-upload    Upload 100+ resumes (multipart)
GET  /api/resumes/batch/{id}     Check upload progress
POST /api/jobs/create            Parse & create job from JD text
GET  /api/jobs                   List all jobs (paginated)
POST /api/jobs/{id}/screen       Start candidate screening
GET  /api/jobs/{id}/screening-results  Get ranked results
POST /api/screening-results/{id}/actions  Shortlist/reject
POST /api/screening-results/export  Export CSV
GET  /api/admin/stats            Dashboard statistics
GET  /api/health                 Health check
```

---

## Testing

### Backend (pytest)

```bash
cd backend
source venv/bin/activate   # or venv\Scripts\activate on Windows
pytest tests/ -v
pytest tests/ -v --cov=app --cov-report=html   # with coverage
```

### Frontend (Jest)

```bash
cd frontend
npm test
npm run test:coverage
npm run type-check   # TypeScript check
npm run lint         # ESLint
```

---

## Project Structure

```
HireFlow/
├── frontend/                    # Next.js 15 + React 19
│   ├── app/                     # App Router pages
│   │   ├── (dashboard)/         # Protected dashboard routes
│   │   │   ├── dashboard/       # Stats overview
│   │   │   ├── upload/          # Resume bulk upload
│   │   │   ├── screen/          # JD input & screening
│   │   │   └── shortlist/       # Ranked results
│   │   ├── auth/                # Login & register
│   │   └── api/auth/            # NextAuth handler
│   ├── components/
│   │   ├── ui/                  # Reusable UI primitives
│   │   ├── forms/               # LoginForm, UploadForm
│   │   ├── cards/               # CandidateCard
│   │   └── layouts/             # Sidebar, Header
│   ├── lib/
│   │   ├── api/                 # API client functions
│   │   ├── hooks/               # Custom React hooks
│   │   └── utils/               # Utility functions
│   └── store/                   # Zustand global state
│
├── backend/                     # FastAPI Python backend
│   ├── app/
│   │   ├── api/                 # Route handlers
│   │   │   ├── auth.py          # Authentication
│   │   │   ├── resumes.py       # Upload & parsing
│   │   │   ├── jobs.py          # JD & screening
│   │   │   ├── screening.py     # Results & export
│   │   │   └── admin.py         # Dashboard stats
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── services/
│   │   │   ├── resume_parser.py    # Gemini resume parsing
│   │   │   ├── knockout_engine.py  # Deterministic filters
│   │   │   ├── scoring_engine.py   # AI + weighted scoring
│   │   │   ├── embedding_service.py # sentence-transformers
│   │   │   └── pinecone_service.py  # Vector search
│   │   └── utils/               # Auth, file handling
│   ├── tests/                   # pytest test suite
│   └── main.py                  # FastAPI app entry point
│
├── docker-compose.yml           # One-command deployment
├── .env.example                 # Environment template
└── README.md
```

---

## Security

- JWT tokens (HS256, 7-day expiry)
- bcrypt password hashing (cost factor 12)
- Rate limiting: 100 requests/minute per IP
- CORS configured for allowed origins only
- Input validation on all endpoints (Pydantic)
- File type validation on upload (PDF/DOCX only, max 10 MB)
- SQL injection protection via SQLAlchemy ORM
- Non-root Docker containers

---

## License

MIT
