# T4：后端核心 API 开发

## 任务目标

在 FastAPI 后端实现设置、引导词、音频任务和 Dify 代理四类核心 API，完成与前端的数据交互接口，并实现 Dify 流式响应的 SSE 包装。

**预计耗时**：2 ~ 2.5 天

---

## 前置依赖

- T2 完成（后端基础、数据库模型、Schemas 已就绪）
- T3 完成（Dify 已部署，两个应用 API Key 已获取）

---

## 详细步骤

### 4.1 注册路由

在 `backend/app/main.py` 中注册路由器：

```python
from app.routers import settings, scripts, audio_tasks, dify_proxy

app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
app.include_router(audio_tasks.router, prefix="/api/audio-tasks", tags=["audio-tasks"])
app.include_router(dify_proxy.router, prefix="/api/dify", tags=["dify"])
```

### 4.2 设置 API

`backend/app/routers/settings.py`：

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.setting import Setting
from app.schemas.setting import SettingSchema

router = APIRouter()


@router.get("", response_model=SettingSchema)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting).where(Setting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting(id=1)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    return SettingSchema(
        llm_config=setting.llm_config,
        tts_config=setting.tts_config,
        dify_config=setting.dify_config,
        general_config=setting.general_config,
    )


@router.post("", response_model=SettingSchema)
async def save_settings(payload: SettingSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting).where(Setting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting(id=1)
        db.add(setting)

    setting.llm_config = payload.llm_config.model_dump()
    setting.tts_config = payload.tts_config.model_dump()
    setting.dify_config = payload.dify_config.model_dump()
    setting.general_config = payload.general_config.model_dump()

    await db.commit()
    await db.refresh(setting)
    return payload


@router.post("/test-llm")
async def test_llm(config: LLMConfig):
    # TODO: 调用 LLM 健康检查接口
    return {"status": "ok"}


@router.post("/test-tts")
async def test_tts(config: TTSConfig):
    # TODO: 调用 TTS 测试接口
    return {"status": "ok"}
```

### 4.3 引导词 API

`backend/app/routers/scripts.py`：

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.script import Script
from app.schemas.script import ScriptCreate, ScriptResponse

router = APIRouter()


@router.get("", response_model=list[ScriptResponse])
async def list_scripts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script).order_by(Script.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ScriptResponse, status_code=201)
async def create_script(payload: ScriptCreate, db: AsyncSession = Depends(get_db)):
    script = Script(**payload.model_dump())
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return script


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: int, payload: ScriptCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    for key, value in payload.model_dump().items():
        setattr(script, key, value)
    await db.commit()
    await db.refresh(script)
    return script


@router.delete("/{script_id}", status_code=204)
async def delete_script(script_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    await db.delete(script)
    await db.commit()
```

### 4.4 音频任务 API

`backend/app/routers/audio_tasks.py`：

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.audio_task import AudioTask
from app.schemas.audio_task import AudioTaskCreate, AudioTaskResponse

router = APIRouter()


@router.post("", response_model=AudioTaskResponse, status_code=201)
async def create_task(payload: AudioTaskCreate, db: AsyncSession = Depends(get_db)):
    task = AudioTask(
        script_id=payload.script_id,
        voice_prompt=payload.voice_prompt,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=list[AudioTaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudioTask).order_by(AudioTask.created_at.desc()))
    return result.scalars().all()


@router.get("/{task_id}", response_model=AudioTaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/download")
async def download_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task or task.status != "completed" or not task.file_path:
        raise HTTPException(status_code=404, detail="Audio not ready")
    return FileResponse(task.file_path)


@router.post("/{task_id}/retry", response_model=AudioTaskResponse)
async def retry_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "pending"
    task.error_msg = None
    await db.commit()
    await db.refresh(task)
    return task
```

### 4.5 Dify 代理 SSE 接口

`backend/app/routers/dify_proxy.py`：

```python
import json
import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.setting import Setting

router = APIRouter()


async def get_dify_config(db: AsyncSession):
    result = await db.execute(select(Setting).where(Setting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=400, detail="Settings not configured")
    return setting.dify_config


async def stream_dify(request: Request, api_key: str, base_url: str):
    body = await request.json()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async def event_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat-messages",
                headers=headers,
                json=body,
                timeout=60.0,
            ) as response:
                async for chunk in response.aiter_text():
                    yield f"data: {chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/script/chat")
async def chat_script(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_dify_config(db)
    return await stream_dify(request, config["script_app_key"], config["base_url"])


@router.post("/audio/chat")
async def chat_audio(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_dify_config(db)
    return await stream_dify(request, config["audio_app_key"], config["base_url"])
```

> 注意：Dify SSE 数据格式需要在前端按行解析，具体事件类型需参考 Dify 官方文档。

### 4.6 测试连接接口实现

`test-llm` 实现：使用配置中的 `api_key`、`base_url`、`model` 向 LLM 发送一条简单请求（如"hi"），返回是否成功。

`test-tts` 实现：调用 TTS 服务合成一句短文本，验证凭证与接口可用性。

> TTS 测试可依赖 T5 完成后的 `TTSService`，T4 可先留 TODO 或做基础校验。

### 4.7 单元测试

`backend/tests/test_scripts.py` 示例：

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db import AsyncSessionLocal, Base, engine


@pytest.fixture(scope="function")
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_script(client):
    response = await client.post("/api/scripts", json={
        "title": "测试引导词",
        "content": "请闭上眼睛...",
        "session_id": "test-session"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "测试引导词"
    assert data["id"] is not None
```

---

## 关键设计点

- 所有 API 以 `/api` 为前缀，与前端代理配置对齐。
- Dify 代理接口从 SQLite 读取 `dify_config`，避免 API Key 暴露给前端。
- SSE 包装时保留 Dify 原始 chunk，前端按 Dify 协议解析。
- `AudioTask` 创建后立即返回 `pending` 状态，实际合成由 T5 的 worker 处理。
- 设置表使用固定 `id=1`，不存在时自动创建默认记录。

---

## 验收标准

- [ ] `/api/health`、`/api/settings`、`/api/scripts`、`/api/audio-tasks` 接口可用
- [ ] 设置 CRUD 正确持久化到 SQLite
- [ ] 引导词 CRUD 完整，包含创建、查询、更新、删除
- [ ] 音频任务可创建、查询、下载（完成后）、重试
- [ ] `/api/dify/script/chat` 和 `/api/dify/audio/chat` 能正确转发到 Dify 并返回 SSE
- [ ] 后端单元测试覆盖设置、引导词、音频任务核心接口，测试通过
- [ ] Ruff 检查无错误

---

## 关联文档

- `docs/tech/tech-spec.md` 第 6、7、8 章
- `docs/prd/meditation-guide-words-prd.md` 第 4.4、4.5 章

---

## 风险备注

- Dify SSE chunk 格式较复杂，可能包含 `event`、`message`、`agent_message` 等多种事件，前端需正确解析。
- `test-llm` 和 `test-tts` 依赖外部 API，测试时可能因网络或凭证失败，可考虑 mock。
