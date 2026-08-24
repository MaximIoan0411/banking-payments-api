import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings
from app.database import Base
from app.main import app as fastapi_app
from app.dependencies import get_db
from app.limiter import limiter

import app.models  

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL

if not TEST_DB_URL or "test" not in TEST_DB_URL:
    raise RuntimeError(
        "Invalid TEST_DATABASE_URL. Tests aborted to protect the production database."
    )


@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limiter():
    limiter.reset()
    yield


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_engine, setup_database):
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(test_engine):
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post("/auth/register", json={
        "email": "user1@test.com",
        "password": "parola123",
        "full_name": "Test User",
    })
    login = await client.post("/auth/login", data={
        "username": "user1@test.com",
        "password": "parola123",
    })
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def funded_sender(client):
    await client.post("/auth/register", json={
        "email": "sender@test.com",
        "password": "parola123",
        "full_name": "Sender User",
    })
    login = await client.post("/auth/login", data={
        "username": "sender@test.com",
        "password": "parola123",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    await client.post(
        "/transactions/deposits",
        json={"amount": "500.00", "description": "test funds"},
        headers=headers,
    )
    account = await client.get("/accounts/me", headers=headers)
    return {"headers": headers, "account_number": account.json()["account_number"]}


@pytest_asyncio.fixture
async def recipient(client):
    await client.post("/auth/register", json={
        "email": "recipient@test.com",
        "password": "parola123",
        "full_name": "Recipient User",
    })
    login = await client.post("/auth/login", data={
        "username": "recipient@test.com",
        "password": "parola123",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    account = await client.get("/accounts/me", headers=headers)
    return {"headers": headers, "account_number": account.json()["account_number"]}