# T2：后端基础能力建设

## 任务目标

初始化 FastAPI 后端项目，配置 `uv` 依赖管理、Ruff 代码规范、SQLAlchemy 2.0 ORM，创建核心数据模型和数据库初始化逻辑，为后续 API 开发奠定后端基础。

**预计耗时**：1 ~ 1.5 天

---

## 前置依赖

- T1 完成（项目目录结构已创建）

---

## 详细步骤

### 2.1 初始化后端项目

在 `backend/` 目录下执行：

```bash
cd backend
uv init --python 3.11
```

### 2.2 添加依赖

```bash
uv add fastapi uvicorn sqlalchemy pydantic-settings aiosqlite httpx pytest pytest-asyncio
```

> `aiosqlite` 用于 SQLite 异步支持；`httpx` 用于调用 Dify/TTS 服务；`pytest` 相关用于测试。

### 2.3 配置 Ruff

在 `backend/pyproject.toml` 中添加：

```toml
[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP", "B"]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"
```

### 2.4 创建时间工具函数

`backend/app/utils/time_utils.py`：

```python
from datetime import datetime, timezone


def utc_now() -> datetime:
    """返回当前 UTC 时间，避免直接使用已弃用的 datetime.utcnow。"""
    return datetime.now(timezone.utc)
```

> 所有 ORM 模型的 `default` 和 `onupdate` 统一使用 `utc_now` 而非已弃用的 `datetime.utcnow`。

### 2.5 创建项目入口

`backend/app/main.py`：

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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
```

### 2.6 配置管理

`backend/app/config.py`：

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/meditation.db"
    audio_output_dir: str = "./data/audio"
    dify_base_url: str = "http://localhost/v1"
    worker_concurrency: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
```

### 2.7 数据库初始化

`backend/app/db.py`：

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config import settings

Base = declarative_base()

# 将 sqlite:/// 转换为 sqlite+aiosqlite:///
database_url = settings.database_url
if database_url.startswith("sqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

engine = create_async_engine(database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def init_db():
    os.makedirs(os.path.dirname(settings.database_url.replace("sqlite:///", "")), exist_ok=True)
    os.makedirs(settings.audio_output_dir, exist_ok=True)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### 2.8 创建 ORM 模型

`backend/app/models/script.py`：

```python
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.utils.time_utils import utc_now


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str]
    content: Mapped[str]
    session_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now
    )
```

`backend/app/models/audio_task.py`：

```python
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.utils.time_utils import utc_now


class AudioTask(Base):
    __tablename__ = "audio_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"))
    voice_prompt: Mapped[str]
    tts_params: Mapped[dict | None]
    status: Mapped[str] = mapped_column(default="pending")
    file_path: Mapped[str | None]
    error_msg: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    completed_at: Mapped[datetime | None]
```

`backend/app/models/setting.py`：

```python
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.utils.time_utils import utc_now


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1, autoincrement=False)
    llm_config: Mapped[dict] = mapped_column(default=dict)
    tts_config: Mapped[dict] = mapped_column(default=dict)
    dify_config: Mapped[dict] = mapped_column(default=dict)
    general_config: Mapped[dict] = mapped_column(default=dict)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now)
```

### 2.9 数据库表创建

`backend/app/db.py` 增加建表逻辑：

```python
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

在 `lifespan` 中调用：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await create_tables()
    yield
```

### 2.10 创建 Pydantic Schemas

`backend/app/schemas/setting.py`：

```python
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "deepseek"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = None


class TTSConfig(BaseModel):
    provider: str = "volcano"
    api_key: str = ""
    secret_key: str = ""
    voice_id: str = ""
    speed: float = Field(default=1.0, ge=0.5, le=2)
    volume: float = Field(default=1.0, ge=0, le=2)
    output_format: str = "mp3"


class DifyConfig(BaseModel):
    base_url: str = "http://localhost/v1"
    script_app_key: str = ""
    audio_app_key: str = ""


class GeneralConfig(BaseModel):
    language: str = "zh"
    theme: str = "light"
    audio_output_dir: str = "./data/audio"


class SettingSchema(BaseModel):
    llm_config: LLMConfig
    tts_config: TTSConfig
    dify_config: DifyConfig
    general_config: GeneralConfig
```

> `backend/app/schemas/script.py` 和 `backend/app/schemas/audio_task.py` 的 Schema 将在 T4（后端 API 开发）中按需创建，T2 仅建立 `setting.py`。

### 2.11 本地运行验证

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

访问 `http://localhost:8000/api/health`，应返回 `{"status":"ok"}`。

---

## 关键设计点

- 使用 `aiosqlite` + SQLAlchemy 2.0 的 `Mapped` 类型注解风格，保持类型安全。
- `database_url` 在配置层用标准 `sqlite:///` 写法，在 `db.py` 中转换为 `sqlite+aiosqlite:///`。
- `Setting` 表固定 `id=1`，`autoincrement=False` 防止意外自增，作为单用户本地设置的全局唯一记录。
- 时间字段统一使用 `app.utils.time_utils.utc_now()` 替代已弃用的 `datetime.utcnow`。
- `AudioTask` 中声音提示词字段命名为 `voice_prompt`，语义清晰，区别于引导词正文 `content`。
- 数据库与音频目录在启动时自动创建。启动命令需在 `backend/` 目录下执行，确保相对路径正确解析。

---

## 验收标准

- [x] `backend/pyproject.toml` 配置完成，`uv sync` 可安装依赖
- [x] `ruff check .` 和 `ruff format .` 可正常运行
- [x] `uv run uvicorn app.main:app --reload` 成功启动，健康检查接口返回 `ok`
- [x] SQLite 数据库文件 `data/meditation.db` 自动创建，且包含 `scripts`、`audio_tasks`、`settings` 三张表
- [x] CORS 已配置，允许前端 `localhost:5173` 访问

---

## 关联文档

- `docs/tech/tech-spec.md` 第 3、4、8、14 章
- `docs/prd/meditation-guide-words-prd.md` 第 4、5 章

---

## 风险备注

- ~~Windows 下 `sqlite:///./data/meditation.db` 的相对路径解析需验证~~ → 已验证：从项目根目录启动 uvicorn 时，`./data/` 解析至项目根 `data/`，正常运行。
- SQLAlchemy 2.0 异步模式对 `Mapped[dict | None]` 的 JSON 序列化 → 已确认需在 `mapped_column()` 中显式指定 `JSON` 类型（如 `mapped_column(JSON, default=None)`），否则启动报 `MappedAnnotationError`。已在模型代码中修正。
