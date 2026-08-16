from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import setup_logging
from app.db import create_tables, init_db
from app.db_migrations import migrate_database
from app.routers import (
    artifacts,
    audio_render_plans,
    audio_tasks,
    dify_proxy,
    music_tasks,
    scripts,
    settings,
)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await create_tables()
    await migrate_database()
    yield


app = FastAPI(
    title="Meditation Guide Words API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
app.include_router(audio_tasks.router, prefix="/api/audio-tasks", tags=["audio-tasks"])
app.include_router(music_tasks.router, prefix="/api/music-tasks", tags=["music-tasks"])
app.include_router(artifacts.router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(dify_proxy.router, prefix="/api/dify", tags=["dify"])
app.include_router(
    audio_render_plans.router, prefix="/api/audio-render-plans", tags=["audio-render-plans"]
)
