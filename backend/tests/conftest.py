"""
Shared pytest fixtures for HireFlow backend tests.
"""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import User, Resume, UploadBatch, JobDescription, ScreeningResult
from app.models.unit import BusinessUnit, UserUnit


# In-memory SQLite for fast tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_units(db_session):
    """Seed the 3 standard business units for tests."""
    units = [
        BusinessUnit(id="unit-dpu-001", unit_slug="dpu", unit_name="Digital Publishing Unit"),
        BusinessUnit(id="unit-res-002", unit_slug="resource_mgmt", unit_name="Resource Management Group"),
        BusinessUnit(id="unit-del-003", unit_slug="delivery", unit_name="Delivery Unit"),
    ]
    for u in units:
        db_session.add(u)
    await db_session.commit()
    return units


@pytest.fixture
def sample_user_data():
    return {
        "email": "test@hireflow.io",
        "name": "Test Recruiter",
        "company": "Test Corp",
        "password": "testpassword123",
    }


@pytest.fixture
def sample_resume_data():
    return {
        "candidate_name": "Alice Engineer",
        "email": "alice@example.com",
        "phone": "+1-555-0100",
        "location": "Bangalore, India",
        "total_exp_years": 7,
        "recent_skills": ["Python", "FastAPI", "AWS", "PostgreSQL"],
        "all_skills": ["Python", "FastAPI", "AWS", "PostgreSQL", "Docker", "React"],
        "education": [
            {"degree": "B.Tech Computer Science", "institution": "IIT Bombay", "year": 2017}
        ],
        "experience": [
            {
                "title": "Senior Backend Engineer",
                "company": "TechCorp",
                "location": "Bangalore",
                "duration_start": "2022-01",
                "duration_end": "Present",
                "duration_years": 2,
                "description": "Led backend infrastructure",
                "achievements": ["Reduced API latency by 40%", "Managed team of 5"],
                "skills_used": ["Python", "FastAPI", "AWS", "PostgreSQL"],
            }
        ],
        "employment_gaps": [],
        "certifications": [
            {"name": "AWS Solutions Architect", "issuer": "Amazon", "year": 2021}
        ],
    }


@pytest.fixture
def sample_jd_data():
    return {
        "job_title": "Senior Backend Engineer",
        "required_min_exp_years": 5,
        "required_skills": [
            {"skill": "Python", "proficiency": "Advanced", "years_required": 5},
            {"skill": "FastAPI", "proficiency": "Advanced", "years_required": 3},
            {"skill": "AWS", "proficiency": "Intermediate", "years_required": 2},
        ],
        "nice_to_have_skills": ["Docker", "Kubernetes"],
        "education_required": "B.Tech Computer Science",
        "locations_accepted": ["Bangalore", "Remote"],
        "willingness_to_relocate": "Preferred",
        "top_3_mandatory_skills": ["Python", "FastAPI", "AWS"],
        "job_description_full": "We are looking for a Senior Backend Engineer...",
    }
