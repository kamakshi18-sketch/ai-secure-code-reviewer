import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import asyncio
from typing import AsyncGenerator
import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["CHROMADB_URL"] = "http://localhost:8000"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32-chars"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["LOG_LEVEL"] = "DEBUG"

from main import app
from database.session import Base, get_db
from core.config import settings
from core.security import get_password_hash, create_access_token
from models import User, UserRole, Repository, RepositoryStatus, Scan, ScanStatus, ScanType, Finding, Severity, FindingStatus, Patch, PatchStatus


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role=UserRole.DEVELOPER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(admin_user: User) -> dict:
    token = create_access_token(subject=admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_repository(db_session: AsyncSession, test_user: User) -> Repository:
    repo = Repository(
        owner_id=test_user.id,
        github_id=123456,
        name="test-repo",
        full_name="testuser/test-repo",
        description="Test repository",
        url="https://github.com/testuser/test-repo",
        clone_url="https://github.com/testuser/test-repo.git",
        default_branch="main",
        language="python",
        is_private=False,
        status=RepositoryStatus.CLONED,
        local_path="/tmp/test-repo",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)
    return repo


@pytest_asyncio.fixture
async def test_scan(db_session: AsyncSession, test_repository: Repository, test_user: User) -> Scan:
    scan = Scan(
        repository_id=test_repository.id,
        initiated_by_id=test_user.id,
        scan_type=ScanType.FULL,
        status=ScanStatus.COMPLETED,
        branch="main",
        scanners_used=["semgrep", "bandit"],
        total_findings=2,
        critical_count=0,
        high_count=1,
        medium_count=1,
        low_count=0,
        info_count=0,
    )
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)
    return scan


@pytest_asyncio.fixture
async def test_findings(db_session: AsyncSession, test_scan: Scan) -> list:
    findings = [
        Finding(
            scan_id=test_scan.id,
            scanner="semgrep",
            rule_id="sql-injection",
            rule_name="SQL Injection",
            severity=Severity.HIGH,
            status=FindingStatus.OPEN,
            cwe_id="CWE-89",
            owasp_category="A03:2021",
            file_path="app/models.py",
            line_start=42,
            message="Potential SQL injection via string formatting",
            confidence=0.9,
        ),
        Finding(
            scan_id=test_scan.id,
            scanner="bandit",
            rule_id="B608",
            rule_name="Hardcoded SQL Query",
            severity=Severity.MEDIUM,
            status=FindingStatus.OPEN,
            cwe_id="CWE-89",
            file_path="app/utils.py",
            line_start=15,
            message="Possible SQL injection",
            confidence=0.7,
        ),
    ]
    for f in findings:
        db_session.add(f)
    await db_session.commit()
    for f in findings:
        await db_session.refresh(f)
    return findings


@pytest_asyncio.fixture
async def test_patch(db_session: AsyncSession, test_scan: Scan, test_findings: list) -> Patch:
    patch = Patch(
        scan_id=test_scan.id,
        finding_id=test_findings[0].id,
        status=PatchStatus.GENERATED,
        diff="--- a/app/models.py\n+++ b/app/models.py\n@@ -39,7 +39,7 @@\n     def get_user(user_id):\n-        query = f\"SELECT * FROM users WHERE id = {user_id}\"\n+        query = \"SELECT * FROM users WHERE id = %s\"\n         cursor.execute(query, (user_id,))",
        file_path="app/models.py",
        language="python",
        llm_provider="openai",
        llm_model="gpt-4-turbo-preview",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)
    return patch