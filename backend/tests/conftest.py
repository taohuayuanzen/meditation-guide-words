import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.services.media_capabilities import MediaCapabilities


@pytest.fixture(autouse=True)
def music_capabilities_available(monkeypatch):
    monkeypatch.setattr(
        "app.routers.music_tasks.get_media_capabilities",
        lambda: MediaCapabilities(ffmpeg_available=True, ffprobe_available=True),
    )
    monkeypatch.setattr(
        "app.routers.audio_tasks.get_media_capabilities",
        lambda: MediaCapabilities(ffmpeg_available=True, ffprobe_available=True),
    )


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield session_factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        async with db_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
