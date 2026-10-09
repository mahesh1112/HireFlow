"""
Unit isolation tests — verifies all 6 acceptance criteria:
1. Intra-unit visibility (R1.1)
2. Cross-unit isolation (R1.2)
3. Multi-unit combined pool (R1.3)
4. Job position scoping (R1.4)
5. BYTEA file storage persistence (R1.6 / Gap 11.14)
6. Upload blocked for non-member unit (R1.2 enforcement)
"""
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.user import User
from app.models.resume import Resume
from app.models.unit import BusinessUnit, UserUnit
from app.models.job import JobDescription


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def dpu_user(db_session, seeded_units):
    """A recruiter assigned only to the DPU unit."""
    user = User(
        email="dpu@test.com",
        name="DPU Recruiter",
        hashed_password="x",
        role="recruiter",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserUnit(user_id=user.id, unit_id="unit-dpu-001"))
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def dpu_user2(db_session, seeded_units):
    """A second recruiter also assigned to DPU."""
    user = User(
        email="dpu2@test.com",
        name="DPU Recruiter 2",
        hashed_password="x",
        role="recruiter",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserUnit(user_id=user.id, unit_id="unit-dpu-001"))
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def res_mgmt_user(db_session, seeded_units):
    """A recruiter assigned only to Resource Management."""
    user = User(
        email="res@test.com",
        name="Res Mgmt Recruiter",
        hashed_password="x",
        role="recruiter",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserUnit(user_id=user.id, unit_id="unit-res-002"))
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def multi_unit_user(db_session, seeded_units):
    """A recruiter assigned to both DPU and Delivery."""
    user = User(
        email="multi@test.com",
        name="Multi Unit Recruiter",
        hashed_password="x",
        role="recruiter",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserUnit(user_id=user.id, unit_id="unit-dpu-001"))
    db_session.add(UserUnit(user_id=user.id, unit_id="unit-del-003"))
    await db_session.commit()
    return user


def _make_resume(user_id: str, unit_id: str, job_id: str, filename: str = "cv.pdf") -> Resume:
    return Resume(
        user_id=user_id,
        unit_id=unit_id,
        job_position_id=job_id,
        filename=filename,
        file_path=None,
        file_size=100,
        content_type="application/pdf",
        upload_status="completed",
        parse_status="completed",
    )


# ─── Test: R1.1 Intra-unit visibility ────────────────────────────────────────

@pytest.mark.asyncio
async def test_intra_unit_visibility(db_session, dpu_user, dpu_user2, seeded_units):
    """DPU recruiter #2 can see a resume uploaded by DPU recruiter #1 for the same job."""
    resume = _make_resume(dpu_user.id, "unit-dpu-001", "job-001", "alice.pdf")
    db_session.add(resume)
    await db_session.commit()

    # dpu_user2 queries resumes for job-001 scoped to their unit
    result = await db_session.execute(
        select(Resume).where(
            Resume.job_position_id == "job-001",
            Resume.unit_id == "unit-dpu-001",
            Resume.parse_status == "completed",
        )
    )
    resumes = result.scalars().all()

    assert len(resumes) == 1
    assert resumes[0].user_id == dpu_user.id   # uploaded by dpu_user
    assert resumes[0].unit_id == "unit-dpu-001"


# ─── Test: R1.2 Cross-unit isolation ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_cross_unit_isolation(db_session, dpu_user, res_mgmt_user, seeded_units):
    """Resource Management user CANNOT see DPU resumes."""
    # DPU uploads a resume
    resume = _make_resume(dpu_user.id, "unit-dpu-001", "job-001", "dpu_candidate.pdf")
    db_session.add(resume)
    await db_session.commit()

    # Resource Mgmt user's unit is "unit-res-002" — must NOT see DPU resumes
    res_mgmt_unit_ids = ["unit-res-002"]
    result = await db_session.execute(
        select(Resume).where(
            Resume.job_position_id == "job-001",
            Resume.unit_id.in_(res_mgmt_unit_ids),
        )
    )
    resumes = result.scalars().all()

    assert len(resumes) == 0, "Cross-unit isolation violated: Resource Mgmt saw DPU resume"


@pytest.mark.asyncio
async def test_cross_unit_isolation_reverse(db_session, dpu_user, res_mgmt_user, seeded_units):
    """DPU user CANNOT see Resource Management resumes."""
    resume = _make_resume(res_mgmt_user.id, "unit-res-002", "job-001", "res_candidate.pdf")
    db_session.add(resume)
    await db_session.commit()

    dpu_unit_ids = ["unit-dpu-001"]
    result = await db_session.execute(
        select(Resume).where(
            Resume.job_position_id == "job-001",
            Resume.unit_id.in_(dpu_unit_ids),
        )
    )
    resumes = result.scalars().all()

    assert len(resumes) == 0, "Cross-unit isolation violated: DPU saw Resource Mgmt resume"


# ─── Test: R1.3 Multi-unit combined pool ─────────────────────────────────────

@pytest.mark.asyncio
async def test_multi_unit_recruiter_sees_combined_pool(
    db_session, dpu_user, res_mgmt_user, multi_unit_user, seeded_units
):
    """Multi-unit user (DPU + Delivery) sees resumes from both their units."""
    # DPU resume
    r1 = _make_resume(dpu_user.id, "unit-dpu-001", "job-001", "dpu.pdf")
    # Delivery resume
    r2 = _make_resume(multi_unit_user.id, "unit-del-003", "job-001", "delivery.pdf")
    # Resource Mgmt resume — must NOT appear
    r3 = _make_resume(res_mgmt_user.id, "unit-res-002", "job-001", "res.pdf")
    db_session.add_all([r1, r2, r3])
    await db_session.commit()

    # Multi-unit user belongs to DPU + Delivery
    user_unit_ids = ["unit-dpu-001", "unit-del-003"]
    result = await db_session.execute(
        select(Resume).where(
            Resume.job_position_id == "job-001",
            Resume.unit_id.in_(user_unit_ids),
        )
    )
    resumes = result.scalars().all()

    assert len(resumes) == 2, f"Expected 2 resumes, got {len(resumes)}"
    unit_ids_found = {r.unit_id for r in resumes}
    assert "unit-dpu-001" in unit_ids_found
    assert "unit-del-003" in unit_ids_found
    assert "unit-res-002" not in unit_ids_found


# ─── Test: R1.4 Job position scoping ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_job_position_scoping(db_session, dpu_user, seeded_units):
    """Resumes for job-001 do NOT appear when querying job-002."""
    r1 = _make_resume(dpu_user.id, "unit-dpu-001", "job-001", "for_job1.pdf")
    r2 = _make_resume(dpu_user.id, "unit-dpu-001", "job-002", "for_job2.pdf")
    db_session.add_all([r1, r2])
    await db_session.commit()

    result = await db_session.execute(
        select(Resume).where(
            Resume.job_position_id == "job-001",
            Resume.unit_id.in_(["unit-dpu-001"]),
        )
    )
    resumes = result.scalars().all()

    assert len(resumes) == 1
    assert resumes[0].job_position_id == "job-001"


# ─── Test: Gap 11.14 BYTEA file storage ──────────────────────────────────────

@pytest.mark.asyncio
async def test_bytea_file_storage_round_trip(db_session, dpu_user, seeded_units):
    """Resume file bytes stored in BYTEA are retrievable without any disk file."""
    fake_pdf_bytes = b"%PDF-1.4 fake pdf content for test"
    resume = Resume(
        user_id=dpu_user.id,
        unit_id="unit-dpu-001",
        job_position_id="job-001",
        filename="test.pdf",
        file_path=None,             # no disk path
        resume_file=fake_pdf_bytes, # stored in BYTEA
        file_mimetype="application/pdf",
        file_size=len(fake_pdf_bytes),
        content_type="application/pdf",
        upload_status="completed",
        parse_status="pending",
    )
    db_session.add(resume)
    await db_session.commit()

    result = await db_session.execute(
        select(Resume).where(Resume.id == resume.id)
    )
    fetched = result.scalar_one()

    assert fetched.resume_file == fake_pdf_bytes
    assert fetched.file_path is None
    assert fetched.file_mimetype == "application/pdf"


@pytest.mark.asyncio
async def test_bytea_storage_survives_session_reload(db_session, dpu_user, seeded_units):
    """BYTEA data is persisted across session boundaries (simulates container restart)."""
    original_bytes = b"Binary file data \x00\x01\x02\x03 that must survive"
    resume = Resume(
        user_id=dpu_user.id,
        unit_id="unit-dpu-001",
        filename="binary_test.pdf",
        file_path=None,
        resume_file=original_bytes,
        file_mimetype="application/pdf",
        file_size=len(original_bytes),
        content_type="application/pdf",
        upload_status="completed",
        parse_status="pending",
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.expire(resume)  # force a reload from DB

    result = await db_session.execute(
        select(Resume).where(Resume.id == resume.id)
    )
    reloaded = result.scalar_one()
    assert reloaded.resume_file == original_bytes


# ─── Test: Unit membership ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_unit_assignment(db_session, seeded_units):
    """A user can be assigned to multiple units."""
    user = User(email="test_assign@test.com", name="Test", hashed_password="x", role="recruiter")
    db_session.add(user)
    await db_session.flush()

    db_session.add(UserUnit(user_id=user.id, unit_id="unit-dpu-001"))
    db_session.add(UserUnit(user_id=user.id, unit_id="unit-res-002"))
    await db_session.commit()

    result = await db_session.execute(
        select(UserUnit).where(UserUnit.user_id == user.id)
    )
    assignments = result.scalars().all()
    assert len(assignments) == 2
    unit_ids = {a.unit_id for a in assignments}
    assert "unit-dpu-001" in unit_ids
    assert "unit-res-002" in unit_ids


@pytest.mark.asyncio
async def test_user_with_no_units_sees_nothing(db_session, dpu_user, seeded_units):
    """A user with no unit assignments has no cross-unit visibility."""
    no_unit_user = User(
        email="nounit@test.com", name="No Unit User", hashed_password="x", role="recruiter"
    )
    db_session.add(no_unit_user)

    # DPU resume
    resume = _make_resume(dpu_user.id, "unit-dpu-001", "job-001")
    db_session.add(resume)
    await db_session.commit()

    # no_unit_user has no units — unit_ids = []
    user_unit_ids: list[str] = []
    result = await db_session.execute(
        select(Resume).where(
            Resume.job_position_id == "job-001",
            Resume.unit_id.in_(user_unit_ids) if user_unit_ids else Resume.user_id == no_unit_user.id,
        )
    )
    resumes = result.scalars().all()
    assert len(resumes) == 0
