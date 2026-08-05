import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

Base = declarative_base()

# 将 sqlite:/// 转换为 sqlite+aiosqlite:/// 以支持异步
database_url = settings.database_url
if database_url.startswith("sqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

engine = create_async_engine(database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def init_db() -> None:
    """创建数据库文件目录和音频输出目录。"""
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    os.makedirs(settings.audio_output_dir, exist_ok=True)


async def create_tables() -> None:
    """根据 ORM 模型创建所有数据库表。"""
    # 确保模型已导入（触发 Base 注册）
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI 依赖注入：获取数据库会话。"""
    async with AsyncSessionLocal() as session:
        yield session
