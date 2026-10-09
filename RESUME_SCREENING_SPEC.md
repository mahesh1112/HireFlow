# Resume Screening System - Complete Implementation Blueprint

## 👤 Role Description

**As a Resume Screening Application Expert**, your role is to implement a comprehensive, production-ready resume screening and candidate shortlisting system using Next.js + React for the frontend. You will architect and build an intelligent matching engine that automatically evaluates resumes against job descriptions using deterministic knockout filters combined with AI-powered scoring. Your responsibility spans full-stack development across React UI components, backend, database, vector embeddings, and AI integration, ensuring accurate candidate ranking with explainable insights for recruiters.

---

## 🎯 Executive Summary

Build a complete resume screening system that automatically shortlists candidates based on Job Descriptions provided by recruiters.

**Technology Stack:**
- Frontend: Next.js 15+ with React 19+
- Backend: FastAPI
- Database: PostgreSQL 16
- Vector DB: Pinecone (Serverless)
- Cache: Redis
- AI/LLM: Google Gemini 2.5 Flash
- Embeddings: sentence-transformers (all-MiniLM-L6-v2)
- Auth: Next-Auth + JWT

**MVP Timeline:** 5 phases → Production-ready shortlisting

---

## 🧠 Core Recruiter Shortlisting Logic

### 1. INSTANT KNOCKOUT FILTERS (Immediate Reject)

These are deterministic rules that immediately disqualify candidates:

- ❌ **Experience years mismatch**: JD requires 5+ years → Resume shows <3 years
- ❌ **Missing ANY top-3 JD skills**: Evidence must be from last 3 years of work
- ❌ **Recent irrelevant experience**: Last 2 years must align with JD requirements
- ❌ **Employment gaps >12 months**: Unexplained gaps are auto-rejected
- ❌ **Location/availability mismatch**: Geographic or visa requirements not met
- ❌ **Education requirements not met**: Minimum qualification thresholds

### 2. CANDIDATE RANKING (Top 20 Shortlist)

Weighted scoring for candidates who pass knockout filters:

| Category | Weight | Criteria |
|----------|--------|----------|
| Skills Match | 40% | Top-3 JD skills present & proficiency level |
| Experience Relevance | 25% | Years of experience + domain alignment |
| Career Progression | 20% | Growth trajectory and role advancement |
| Measurable Achievements | 15% | Quantified impact and impact scope |

### 3. SHORTLIST DECISION TIERS

| Status | Range | Priority | Action |
|--------|-------|----------|--------|
| 🟢 EXCELLENT | 86-100 | Top priority | Immediate interview |
| 🔵 GOOD | 61-85 | Strong candidates | Review & schedule |
| 🟡 ADEQUATE | 31-60 | Consider if needed | Backup pool |
| 🔴 POOR | 0-30 | Auto-reject | Reject notification |

---

## 🏗️ Technical Architecture

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | Next.js + React | 15+ / 19+ | Recruiter dashboard, JD input, candidate shortlists |
| Backend | FastAPI | Latest | Resume parsing, JD matching, ranking engine |
| Database | PostgreSQL | 16 | Resumes metadata, screening results |
| Cache | Redis | Latest | Session management, result caching |
| Vector DB | Pinecone | Serverless | Semantic resume-JD matching |
| AI/LLM | Google Gemini | 2.5 Flash | Resume parsing + fit scoring |
| Embeddings | sentence-transformers | all-MiniLM-L6-v2 | Semantic similarity (384-dim vectors) |
| Authentication | Next-Auth + JWT | Latest | Secure recruiter access |

---

## 🚀 Implementation Roadmap (5 Sequential Phases)

### PHASE 0: Project Scaffold

Generate complete monorepo for resume screening system:

#### **Frontend Setup (Next.js 15+ with React 19+)**

Use Next.js default command to bootstrap React-powered frontend:

```bash
# Create Next.js 15+ project with React 19+ and recommended defaults
npx create-next-app@latest frontend --typescript --tailwind --eslint

# Navigate to frontend directory
cd frontend

# Verify React 19+ is installed (automatically included with Next.js 15+)
npm list react react-dom

# Install additional React ecosystem dependencies
npm install next-auth axios zustand
npm install @radix-ui/react-dialog @radix-ui/react-select lucide-react
npm install react-hook-form zod
```

The default Next.js + React scaffolding creates the foundation structure:

```
frontend/
├── app/                          # App Router (Next.js 15 default)
│   ├── layout.tsx                # Root layout
│   ├── page.tsx                  # Home/index page
│   └── globals.css               # Global styles
├── components/                   # Reusable components
├── public/                       # Static assets
├── .eslintrc.json               # ESLint config
├── tsconfig.json                # TypeScript config
├── tailwind.config.ts           # Tailwind CSS config
├── next.config.ts               # Next.js config
└── package.json                 # Dependencies
```

**Customize structure for resume screening:**

```bash
# Create required directories
mkdir -p app/{auth,dashboard,upload,screen,shortlist}
mkdir -p components/{ui,forms,cards,layouts}
mkdir -p lib/{api,hooks,utils}
mkdir -p styles
```

#### **Backend Setup (FastAPI)**

Create backend folder and FastAPI project:

```bash
# Create backend directory
mkdir -p backend/app/{api,models,services,utils}
mkdir -p backend/tests
```

#### **Project Root Structure**

```
resumescreen/
├── frontend/                     # Next.js app (created with npx create-next-app)
├── backend/                      # FastAPI application
├── docker-compose.yml
├── .env.example
├── .github/workflows/
├── README.md
└── DEPLOYMENT.md
```

**Include all config files:** package.json, requirements.txt, Dockerfiles, docker-compose.yml

---

### PHASE 1: Backend Core

**Core Functionality:**

1. **DATABASE SCHEMA**
   - User (recruiter profile)
   - Resume (parsed resume data + embeddings)
   - JobDescription (parsed JD + requirements)
   - ScreeningResult (ranking, scores, explanations)
   - UploadBatch (bulk upload tracking)

2. **UPLOAD API**
   - `POST /api/resumes/bulk-upload` - Accept 100+ PDF/DOCX files
   - Background processing with job queue
   - Progress tracking and status updates

3. **JD API**
   - `POST /api/jobs/screen` - Paste JD → Get shortlist with scores
   - `GET /api/screening-results/{job_id}` - Retrieve ranked candidates

4. **KNOCKOUT FILTERS** (Deterministic Logic)
   - Experience validation
   - Skill verification
   - Employment gap analysis
   - Location/availability check
   - Education requirement validation

5. **PINECONE INTEGRATION**
   - Hybrid search (semantic + keyword matching)
   - Resume embeddings storage (384-dim)
   - Real-time retrieval for JD matching

---

### PHASE 2: Recruiter Frontend (Next.js + React)

**Setup Instructions:**

Start with the Next.js + React scaffold created in PHASE 0, then customize:

```bash
cd frontend

# Verify React 19+ is available (comes with Next.js 15+)
npm list react

# Install React UI and form handling libraries
npm install @radix-ui/react-dialog @radix-ui/react-select lucide-react
npm install react-hook-form zod
npm install -D @types/node @types/react @types/react-dom

# Start development server with React hot reload
npm run dev
```

**Customize React component structure from default Next.js:**

```bash
# Remove default files
rm app/page.tsx

# Create Next.js App Router pages
mkdir -p app/{auth,dashboard,upload,screen,shortlist}
touch app/layout.tsx           # Root React layout with auth wrapper
touch app/auth/{route.ts,login,register}    # Auth React pages
touch app/dashboard/page.tsx   # Recruiter dashboard React component
touch app/upload/page.tsx      # Resume upload React component
touch app/screen/page.tsx      # JD screening React component
touch app/shortlist/page.tsx   # Shortlist results React component

# Create reusable React components & hooks
mkdir -p components/{ui,forms,cards}
touch components/ui/{button,input,card,dialog}.tsx
touch components/forms/{LoginForm,UploadForm}.tsx
touch components/cards/{CandidateCard,ResultCard}.tsx

# Create React custom hooks
mkdir -p hooks
touch hooks/{useAuth,useResumeUpload,useScreening}.ts
```

**React UI Components & Features:**

1. **Authentication React Pages** (`app/auth/`)
   - `/auth/login` → React login component with JWT
   - `/auth/register` → React registration component
   - Built with React Hook Form + Zod validation
   - Uses next-auth for session management

2. **Dashboard React Component** (`app/dashboard/page.tsx`)
   - React state management with Zustand
   - Real-time statistics updates
   - Interactive charts and metrics
   - Quick action buttons

3. **Resume Upload React Component** (`app/upload/page.tsx`)
   - React file drop zone component
   - Real-time progress tracking with React hooks
   - File validation using React components
   - Batch processing feedback

4. **Job Screening React Component** (`app/screen/page.tsx`)
   - React form for JD input
   - Real-time React state updates
   - Processing indicators
   - React event handlers

5. **React Results Components** (`components/cards/`)
   - `CandidateCard.tsx` - Reusable React component for candidate display
   - Fit Score visualization with React
   - Status tier badges
   - Strengths/weaknesses React lists
   - Detailed explanation sections

6. **Shortlist Management React Component** (`app/shortlist/page.tsx`)
   - React checkbox selection with useCallback hooks
   - Bulk action handlers
   - CSV/PDF export functionality via React click handlers

**React Development Workflow:**

```bash
# Start dev server with React hot module reload (HMR)
npm run dev

# Build optimized React production bundle
npm run build

# Run production React build
npm start

# Run linter and format React code
npm run lint

# Run TypeScript type checking for React components
npm run type-check
```

**React Architecture:**
- Server Components for layouts and data fetching
- Client Components for interactive UI (React hooks)
- API Routes for backend integration
- React Context + Zustand for state management
- React Suspense for async operations

---

### PHASE 3: AI Matching Engine

**Smart Shortlisting:**

1. **RESUME PARSER** (Gemini 2.5 Flash)
   - Extract structured data from PDF/DOCX
   - Identify skills, experience duration, gaps
   - Validate against predefined taxonomies

2. **JD PARSER** (Gemini 2.5 Flash)
   - Parse job requirements from text
   - Extract required skills (top-3 mandatory)
   - Identify minimum experience requirements
   - Detect location/availability constraints

3. **KNOCKOUT RULES ENGINE** (Deterministic)
   - Auto-reject before ranking
   - Generate rejection reasons
   - Maintain audit trail for transparency

4. **SCORING ENGINE** (Gemini-powered)
   - Calculate fit_score (0-100)
   - Generate explainable insights
   - Provide strength/weakness analysis

5. **RANKING ALGORITHM**
   - Top-20 candidates by combined score
   - Weighted category scoring
   - Diversity-aware ranking (optional)

---

### PHASE 4: Results & Analytics

**Recruiter Dashboard:**

```
[HEADER] 1,247 resumes indexed | 23% match latest JD
│
[RESULTS] Top 20 candidates
├── Rank | Candidate Name | Fit Score | Status | Actions
├── 1    | John Doe       | 92        | EXCELLENT | View | Shortlist | Export
├── 2    | Jane Smith     | 87        | EXCELLENT | View | Shortlist | Export
├── 3    | Bob Johnson    | 78        | GOOD      | View | Shortlist | Export
└── ...
│
[STATS]
├── Shortlist rate: 18%
├── Avg processing: 2.1s per batch
├── Top skills matched: Python (85%), AWS (72%), FastAPI (68%)
└── Top skills missing: Kubernetes (15%), Docker (12%)

[EXPORT] CSV + PDF shortlist reports
```

---

### PHASE 5: Production Ready

1. **TESTS**
   - pytest: 90% backend coverage
   - Jest: Component testing for frontend
   - Playwright: E2E testing (Login → Screen → Shortlist)
   - AI golden dataset: 95% accuracy validation

2. **DOCKER**
   - One-command deployment: `docker compose up`
   - Multi-stage builds for optimization
   - Health checks and restart policies

3. **SECURITY**
   - Rate limiting on all APIs
   - Input validation and sanitization
   - JWT token rotation
   - CORS and CSRF protection

4. **MONITORING**
   - Processing metrics and logs
   - Error tracking and alerting
   - Performance monitoring
   - Usage analytics

---

## 📊 Data Structures

### Parsed Resume (Gemini Output)

```json
{
  "candidate_id": "uuid",
  "candidate_name": "John Doe",
  "email": "john@email.com",
  "phone": "+91-9876543210",
  "location": "Bangalore, India",
  "total_exp_years": 7,
  "recent_skills": [
    "Python",
    "FastAPI",
    "AWS",
    "PostgreSQL",
    "Docker"
  ],
  "all_skills": [
    "Python",
    "FastAPI",
    "AWS",
    "PostgreSQL",
    "Docker",
    "JavaScript",
    "React",
    "Git"
  ],
  "education": [
    {
      "degree": "B.Tech Computer Science",
      "institution": "IIT Bombay",
      "year": 2017
    }
  ],
  "experience": [
    {
      "title": "Senior Backend Engineer",
      "company": "TechCorp",
      "location": "Bangalore",
      "duration_start": "2022-01-01",
      "duration_end": "Present",
      "duration_years": 2,
      "description": "Led backend infrastructure",
      "achievements": [
        "Reduced API latency by 40%",
        "Managed team of 5 engineers",
        "Increased system throughput 3x"
      ],
      "skills_used": ["Python", "FastAPI", "AWS", "PostgreSQL"]
    },
    {
      "title": "Backend Engineer",
      "company": "StartupXYZ",
      "location": "Pune",
      "duration_start": "2019-06-01",
      "duration_end": "2021-12-31",
      "duration_years": 2.5,
      "description": "Built API services",
      "achievements": [
        "Launched 3 microservices",
        "Improved deploy time by 60%",
        "Mentored 2 junior developers"
      ],
      "skills_used": ["Python", "Django", "PostgreSQL", "Docker"]
    }
  ],
  "employment_gaps": [
    {
      "start": "2022-01-01",
      "end": "2022-02-15",
      "duration_months": 1.5,
      "explanation": "Between jobs"
    }
  ],
  "certifications": [
    {
      "name": "AWS Solutions Architect Associate",
      "issuer": "Amazon",
      "year": 2021
    }
  ],
  "embeddings": {
    "experience_vector": [...],  # 384-dim vector
    "skills_vector": [...],       # 384-dim vector
    "full_profile_vector": [...]  # 384-dim vector
  }
}
```

### Job Description (Parsed)

```json
{
  "job_id": "uuid",
  "job_title": "Senior Backend Engineer",
  "company": "TechCorp",
  "location": "Bangalore, India",
  "required_min_exp_years": 5,
  "preferred_min_exp_years": 7,
  "required_skills": [
    {
      "skill": "Python",
      "proficiency": "Advanced",
      "years_required": 5
    },
    {
      "skill": "FastAPI",
      "proficiency": "Advanced",
      "years_required": 3
    },
    {
      "skill": "AWS",
      "proficiency": "Intermediate",
      "years_required": 2
    }
  ],
  "nice_to_have_skills": [
    "Kubernetes",
    "Docker",
    "React"
  ],
  "education_required": "B.Tech/B.E in Computer Science",
  "locations_accepted": ["Bangalore", "Remote"],
  "wilingness_to_relocate": "Preferred",
  "job_description_full": "...",
  "embeddings": {
    "requirements_vector": [...],  # 384-dim vector
    "full_jd_vector": [...]         # 384-dim vector
  }
}
```

### Screening Result

```json
{
  "result_id": "uuid",
  "resume_id": "uuid",
  "job_id": "uuid",
  "rank": 1,
  "fit_score": 92,
  "status": "EXCELLENT",
  "passed_knockouts": true,
  "knockout_failures": [],
  "category_scores": {
    "skills_match": 95,
    "experience_relevance": 90,
    "career_progression": 85,
    "measurable_achievements": 88
  },
  "strengths": [
    "8 years Python experience > 5 years required",
    "Recent AWS projects align with role",
    "Leadership experience demonstrated",
    "Quantified achievements: 40% latency reduction"
  ],
  "weaknesses": [
    "No Docker experience mentioned",
    "Limited Kubernetes exposure",
    "Gap in 2022 (1.5 months)"
  ],
  "match_explanation": "Strong technical fit with relevant leadership experience. Exceeds experience requirements and demonstrates mastery of core technologies. Minor gaps in containerization tools.",
  "skills_matched": [
    {
      "required_skill": "Python",
      "candidate_skill": "Python",
      "match_confidence": 0.98,
      "years_in_profile": 7
    },
    {
      "required_skill": "FastAPI",
      "candidate_skill": "FastAPI",
      "match_confidence": 0.95,
      "years_in_profile": 2
    }
  ],
  "skills_missing": [
    {
      "required_skill": "Kubernetes",
      "candidate_has": false,
      "importance": "high"
    }
  ],
  "created_at": "2026-02-21T10:30:00Z",
  "screening_time_ms": 2100
}
```

---

## 🎛️ Scoring Algorithm

### Detailed Scoring Formula

```
Total Fit Score = (Skills_Match × 0.40) + (Experience_Relevance × 0.25) + 
                  (Career_Progression × 0.20) + (Achievements × 0.15)

Where each component (0-100):

SKILLS_MATCH (40% weight):
- Top-3 required skills present: 25 points each (75 max)
- Proficiency level match: 15 points
- Recent usage (last 3 years): 10 points
Score = (matched_skills / total_required) × 100

EXPERIENCE_RELEVANCE (25% weight):
- Years of experience vs requirement: 0-40 points
- Domain alignment: 20 points
- Role level appropriateness: 30 points
- Technology stack familiarity: 10 points
Score = (experience_points / 100) × 100

CAREER_PROGRESSION (20% weight):
- Role advancement trajectory: 40 points
- Increased responsibilities: 30 points
- Promotions/title growth: 20 points
- Consistent growth indicators: 10 points
Score = (progression_points / 100) × 100

MEASURABLE_ACHIEVEMENTS (15% weight):
- Quantified metrics in achievements: 40 points
- Impact scope (team/org/customers): 30 points
- Technical complexity demonstrated: 20 points
- Multiple significant achievements: 10 points
Score = (achievement_points / 100) × 100
```

### Shortlist Thresholds

- **🟢 EXCELLENT (86-100):** Priority shortlist - immediate interview consideration
- **🔵 GOOD (61-85):** Strong candidates - schedule interviews
- **🟡 ADEQUATE (31-60):** Backup candidates - consider if needed
- **🔴 POOR (0-30):** Auto-rejected - below minimum thresholds

---

## 📱 Recruiter Workflow

1. **LOGIN as Recruiter** → Password-protected dashboard
2. **UPLOAD 100+ Resumes** → 5 mins bulk processing with progress tracking
3. **PASTE Job Description** → Text input or file upload
4. **CLICK "SCREEN CANDIDATES"** → Real-time screening begins
5. **REVIEW Top-20 Ranked List**
   - View fit score, status tier, strengths/weaknesses
   - Expand candidate profile for detailed view
6. **BULK SHORTLIST** → Select candidates from results
7. **EXPORT SHORTLIST** → Download as CSV for interviews
8. **VIEW DASHBOARD** → All shortlists + historical stats

---

## 🔧 Environment Setup (.env.example)

```bash
# Google Gemini API
GEMINI_API_KEY=your-gemini-key-here

# Pinecone Vector Database
PINECONE_API_KEY=your-pinecone-key-here
PINECONE_INDEX_NAME=resume-index
PINECONE_ENVIRONMENT=us-west1-gcp-free

# PostgreSQL Database
DATABASE_URL=postgresql://user:password@localhost:5432/resumescreen
DATABASE_POOL_SIZE=10

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# JWT Authentication
JWT_SECRET=your-super-secret-key-change-in-production
JWT_EXPIRY=7d

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Next-Auth
NEXTAUTH_SECRET=your-nextauth-secret-change-in-production
NEXTAUTH_URL=http://localhost:3000

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Environment
NODE_ENV=development
ENVIRONMENT=local

# Logging
LOG_LEVEL=debug

# File Upload
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=pdf,docx,xlsx
```

---

## 🧪 Testing Requirements

| Test Type | Tools | Coverage | Scope |
|-----------|-------|----------|-------|
| Unit Tests | pytest | 90% | Individual functions, utilities |
| Integration Tests | pytest | 85% | Database, APIs, external services |
| React Component Tests | Jest + React Testing Library | 80% | React component rendering, hooks, state |
| E2E Tests | Playwright | 75% | Login → Screen → Shortlist flow |
| AI Matching Tests | Golden dataset | 95% | Resume parsing, knockout filters, scoring |
| Load Testing | locust/k6 | - | 1000+ resumes, concurrent screening |
| Security Tests | OWASP | - | SQL injection, XSS, CSRF protection |

### Key Test Scenarios

```
☑ React Component Tests (Jest + React Testing Library)
  ├─ LoginForm component rendering
  ├─ UploadForm drag-drop functionality
  ├─ CandidateCard score display
  ├─ Shortlist selection hooks
  ├─ Form validation with Zod
  └─ Navigation between pages

☑ Backend API Tests
  ├─ Authentication & Authorization
  ├─ File upload validation
  ├─ Bulk resume processing
  ├─ JD parsing accuracy
  ├─ Knockout filter logic
  ├─ Scoring algorithm correctness
  └─ Error handling & edge cases

☑ React E2E Tests (Playwright)
  ├─ Login flow with next-auth
  ├─ Drag-drop resume upload interaction
  ├─ Form validation error states
  ├─ Results display and pagination
  ├─ Shortlist selection and bulk actions
  ├─ CSV/PDF export from React components
  └─ Session persistence

☑ AI Model Tests
  ├─ Resume extraction accuracy
  ├─ Skill matching precision
  ├─ Gap detection accuracy
  ├─ Scoring consistency
  └─ Explanation quality
```

---

## 🚀 Deployment

### Local Development

Start all services with Docker (Next.js + React frontend + FastAPI backend):

```bash
# Start all services
docker compose up

# Services available at:
# Frontend (Next.js + React): http://localhost:3000
# Backend (FastAPI): http://localhost:8000
# Database (PostgreSQL): localhost:5432
# Redis Cache: localhost:6379
# Pinecone: cloud-based (API key required)

# In separate terminal - run Next.js dev server with React Hot Module Reload:
cd frontend
npm run dev
```

### Cloud Deployment

```
Frontend:  Vercel (Next.js + React auto-deployment)
Backend:   Railway or Render (FastAPI + PostgreSQL)
Vector DB: Pinecone (serverless)
Cache:     Redis Cloud
Domain:    Custom domain with SSL
Email:     SendGrid or AWS SES
Storage:   AWS S3 for resume files
Monitoring: Sentry, DataDog, or LogRocket
```

### Production Checklist

- [ ] Secrets in environment variables (not in code)
- [ ] Database backups automated (daily)
- [ ] SSL/TLS certificates configured
- [ ] Rate limiting enabled on all APIs
- [ ] CORS properly configured
- [ ] Error tracking and monitoring active
- [ ] Logs aggregated and searchable
- [ ] Auto-scaling configured
- [ ] Health checks passing
- [ ] Load testing completed

---

## 📋 Claude Execution Steps

1. **PHASE 0** → Download ZIP → Extract locally → Run `npx create-next-app@latest frontend` → Install dependencies
2. **PHASE 1** → Replace backend files → Test APIs with curl/Postman
3. **PHASE 2** → Build React components on Next.js scaffold → `npm run dev` → Browser test React components
4. **PHASE 3** → Integrate AI Engine → Test with sample JD
5. **PHASE 4** → Build React Analytics Dashboard → Role testing scenarios
6. **PHASE 5** → `docker compose up` → Production-ready deployment

---

## ✅ Success Metrics

| Metric | Target | Validation |
|--------|--------|-----------|
| Bulk resume upload | <5 minutes for 100 files | Performance test |
| JD screening response | <3 seconds for Top-20 | Average query time |
| Knockout accuracy | 95%+ | Golden dataset validation |
| Candidate ranking | Consistent scoring | A/B testing with recruiters |
| Export functionality | 100% data accuracy | CSV/PDF verification |
| Docker deployment | One-command setup | `docker compose up` test |
| Test coverage | 90% backend (pytest), 80% React frontend (Jest) | pytest + Jest reports |
| Uptime | 99.9% availability | Monitoring dashboard |
| Resumes indexed | Unlimited (cloud-based) | Load testing |
| Concurrent users | 100+ simultaneous | Load test results |

---

## 📚 API Specification (OpenAPI 3.0)

### Authentication Endpoints

```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh-token
GET /api/auth/profile
```

### Resume Endpoints

```
POST /api/resumes/bulk-upload         # Upload multiple resumes
GET /api/resumes/{resume_id}          # Get parsed resume
GET /api/resumes                       # List all resumes (paginated)
DELETE /api/resumes/{resume_id}       # Delete resume
POST /api/resumes/{resume_id}/parse   # Re-parse resume with Gemini
```

### Job Description Endpoints

```
POST /api/jobs/create                 # Create new job posting
GET /api/jobs/{job_id}                # Get job details
PUT /api/jobs/{job_id}                # Update job posting
POST /api/jobs/{job_id}/screen        # Screen candidates for job
GET /api/jobs/{job_id}/screening-results  # Get screening results
DELETE /api/jobs/{job_id}             # Delete job posting
```

### Screening Endpoints

```
GET /api/screening-results            # List all screening results
GET /api/screening-results/{result_id}    # Get detailed result
POST /api/screening-results/{result_id}/actions   # Mark as shortlisted
POST /api/screening-results/export    # Export results (CSV/PDF)
```

### Admin Endpoints

```
GET /api/admin/stats                  # System statistics
GET /api/admin/logs                   # Activity logs
POST /api/admin/reprocess             # Reprocess resumes
```

---

## 🔐 Security Considerations

- **Input Validation:** Sanitize all file uploads and text inputs
- **Rate Limiting:** Max 100 requests/minute per user
- **CORS:** Configure allowed origins
- **CSRF Protection:** Token-based CSRF prevention
- **JWT Security:** Use HS256 or RS256 with secure secrets
- **Database:** Parameterized queries to prevent SQL injection
- **File Upload:** Validate file types, scan for malware
- **Secrets Management:** Use environment variables, never hardcode
- **Logging:** Log security events without sensitive data
- **Monitoring:** Alert on suspicious activity patterns

---

## 📞 Support & Maintenance

- **Issue Tracking:** GitHub Issues for bugs and features
- **Documentation:** Comprehensive README and API docs
- **Monitoring:** Real-time alerts for errors and performance issues
- **Backup Strategy:** Automated daily database backups
- **Update Policy:** Security patches within 48 hours
- **SLA:** 99.9% uptime guaranteed

---

**Version:** 1.0  
**Last Updated:** February 21, 2026  
**Status:** Ready for Implementation
