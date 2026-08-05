# T5：TTS 适配层与异步音频生成

## 任务目标

实现 TTS 供应商适配层（火山引擎、阿里云），封装统一调用接口；实现基于 SQLite 的异步音频生成 Worker；提供音频文件存储与静态下载服务。

**预计耗时**：2 ~ 2.5 天

---

## 前置依赖

- T2 完成（数据库模型、配置管理已就绪）
- T4 完成（音频任务 API 已创建）

---

## 详细步骤

### 5.1 设计统一 TTS 接口

`backend/app/services/tts_base.py`：

```python
from abc import ABC, abstractmethod
from pathlib import Path


class TTSBase(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        volume: float = 1.0,
        output_format: str = "mp3",
    ) -> bytes:
        """返回音频二进制数据"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查配置是否可用"""
        pass
```

### 5.2 实现火山引擎 TTS 适配器

`backend/app/services/tts_volcano.py`：

```python
import httpx
from app.services.tts_base import TTSBase


class VolcanoTTS(TTSBase):
    def __init__(self, api_key: str, secret_key: str = ""):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://openspeech.bytedance.com/api/v1/tts"

    async def synthesize(self, text, voice_id, speed=1.0, volume=1.0, output_format="mp3"):
        payload = {
            "app": {"appid": "", "token": "", "cluster": ""},
            "user": {"uid": "local-user"},
            "audio": {
                "voice_type": voice_id,
                "encoding": output_format,
                "speed_ratio": speed,
                "volume_ratio": volume,
            },
            "request": {
                "reqid": "",
                "text": text,
                "text_type": "plain",
                "operation": "query",
            },
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer;{self.api_key}"},
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.content

    def is_available(self):
        return bool(self.api_key)
```

> 火山引擎 TTS 实际接口参数以官方最新文档为准，此处为示例结构。

### 5.3 实现阿里云 TTS 适配器

`backend/app/services/tts_aliyun.py`：

```python
import httpx
from app.services.tts_base import TTSBase


class AliyunTTS(TTSBase):
    def __init__(self, api_key: str, secret_key: str = ""):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts"

    async def synthesize(self, text, voice_id, speed=1.0, volume=1.0, output_format="mp3"):
        payload = {
            "appkey": self.api_key,
            "text": text,
            "format": output_format,
            "sample_rate": 16000,
            "voice": voice_id,
            "speech_rate": int((speed - 1.0) * 100),
            "volume": int(volume * 100),
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, timeout=60.0)
            response.raise_for_status()
            return response.content

    def is_available(self):
        return bool(self.api_key)
```

### 5.4 TTS 工厂

`backend/app/services/tts_factory.py`：

```python
from app.services.tts_volcano import VolcanoTTS
from app.services.tts_aliyun import AliyunTTS


def get_tts_service(config: dict):
    provider = config.get("provider", "volcano")
    if provider == "volcano":
        return VolcanoTTS(config.get("api_key", ""), config.get("secret_key", ""))
    elif provider == "aliyun":
        return AliyunTTS(config.get("api_key", ""), config.get("secret_key", ""))
    raise ValueError(f"Unsupported TTS provider: {provider}")
```

### 5.5 实现异步 Worker

`backend/app/services/audio_worker.py`：

```python
import asyncio
import json
import os
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models.audio_task import AudioTask
from app.models.script import Script
from app.models.setting import Setting
from app.services.tts_factory import get_tts_service


async def process_task(task_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
        task = result.scalar_one()

        result = await db.execute(select(Script).where(Script.id == task.script_id))
        script = result.scalar_one()

        result = await db.execute(select(Setting).where(Setting.id == 1))
        setting = result.scalar_one()

        task.status = "processing"
        await db.commit()

        try:
            # 解析 TTS 参数
            tts_params = task.tts_params or {}
            voice_id = tts_params.get("voice_id", setting.tts_config.get("voice_id", ""))
            speed = float(tts_params.get("speed", setting.tts_config.get("speed", 1.0)))
            volume = float(tts_params.get("volume", setting.tts_config.get("volume", 1.0)))
            output_format = tts_params.get("output_format", setting.tts_config.get("output_format", "mp3"))

            service = get_tts_service(setting.tts_config)
            audio_bytes = await service.synthesize(
                text=script.content,
                voice_id=voice_id,
                speed=speed,
                volume=volume,
                output_format=output_format,
            )

            output_dir = setting.general_config.get("audio_output_dir", "./data/audio")
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{task.id}.{output_format}")
            with open(file_path, "wb") as f:
                f.write(audio_bytes)

            task.status = "completed"
            task.file_path = file_path
            task.completed_at = datetime.utcnow()
        except Exception as e:
            task.status = "failed"
            task.error_msg = str(e)
        finally:
            await db.commit()


async def worker_loop(concurrency: int = 2):
    semaphore = asyncio.Semaphore(concurrency)

    async def run_task(task_id):
        async with semaphore:
            await process_task(task_id)

    while True:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AudioTask.id)
                .where(AudioTask.status.in_(["pending"]))
                .order_by(AudioTask.created_at)
                .limit(concurrency)
            )
            pending_ids = [row[0] for row in result.all()]

        if not pending_ids:
            await asyncio.sleep(2)
            continue

        await asyncio.gather(*[run_task(tid) for tid in pending_ids])


if __name__ == "__main__":
    asyncio.run(worker_loop(concurrency=2))
```

### 5.6 音频文件静态服务

在 `backend/app/main.py` 中增加：

```python
from fastapi.staticfiles import StaticFiles

app.mount("/api/audio-files", StaticFiles(directory="./data/audio"), name="audio-files")
```

> 下载接口仍走 `/api/audio-tasks/{id}/download`，内部读取 `file_path` 返回 `FileResponse`。

### 5.7 失败重试机制

Worker 中首次失败后不自动重试，由前端调用 `/api/audio-tasks/{id}/retry` 将状态重置为 `pending`。

如需自动重试，可在 `AudioTask` 中增加 `retry_count` 字段，Worker 中失败时判断是否小于最大重试次数。

### 5.8 测试

`backend/tests/test_tts.py`：

```python
import pytest
from app.services.tts_factory import get_tts_service


def test_tts_factory():
    service = get_tts_service({"provider": "volcano", "api_key": "test"})
    assert service.is_available()
```

---

## 关键设计点

- TTS 适配层屏蔽供应商差异，统一返回音频二进制 bytes。
- Worker 无 Redis 依赖，使用 SQLite 作为任务队列，适合本地单用户场景。
- Worker 通过 `asyncio.Semaphore` 控制并发，避免同时合成过多音频导致资源耗尽。
- 音频文件命名使用 `task_id.format`，便于直接映射下载。
- 失败后状态明确为 `failed`，错误信息写入 `error_msg`。

---

## 验收标准

- [ ] `VolcanoTTS` 和 `AliyunTTS` 实现统一 `TTSBase` 接口
- [ ] `get_tts_service` 工厂函数可根据配置切换供应商
- [ ] Worker 进程能轮询 `pending` 任务并依次处理
- [ ] 音频生成成功后，文件保存到 `data/audio/` 并更新任务状态为 `completed`
- [ ] 音频生成失败后，任务状态为 `failed` 并记录错误信息
- [ ] `/api/audio-tasks/{id}/download` 可下载已完成音频
- [ ] TTS 测试连接接口可用（至少验证凭证非空）

---

## 关联文档

- `docs/tech/tech-spec.md` 第 9、10 章
- `docs/prd/meditation-guide-words-prd.md` 第 4.3 章

---

## 风险备注

- 火山引擎与阿里云 TTS 接口参数、鉴权方式差异较大，需参考各自官方文档调整。
- 长文本 TTS 可能需要分片合成，MVP 阶段可先限制单条引导词长度（如 < 5000 字）。
- Worker 进程崩溃会导致未完成任务停滞，建议启动脚本中监控 worker 状态或自动重启。

---

## 当前进度（2026-08-05 · 已完成）

### 已完成

- [x] `app/services/` 包：`tts_base`（统一接口）、`tts_volcano`、`tts_aliyun`、`tts_factory`
- [x] 火山引擎适配器：AK/SK 签名 → Access Token（实例级缓存 + 401 自动刷新）→ TTS 合成，返回解码拼接后的音频 bytes
- [x] 阿里云适配器：DashScope `aigc/text2audio/generation` HTTP + API-Key，`voice_id` 映射为 `model`，`speed→rate`、`volume×100`
- [x] Worker：轮询 pending → processing → 合成写文件 → completed / failed；失败自动重试 1 次后置 failed；文本 >5000 字直接失败
- [x] `AudioTask` 新增 `retry_count` 字段；创建任务接口支持 `tts_params`；retry 接口重置 `retry_count/file_path`
- [x] `test-tts` 接入 `get_tts_service` 工厂做配置校验（不发起外部合成）
- [x] 单元测试 15 个新增（TTS 适配器 mock 测试 + Worker 全流程），全部通过（31 passed）
- [x] Ruff 检查通过

### 关键实现决策（已确认）

| 决策点 | 结论 |
|---|---|
| 适配器实现深度 | 按两家真实协议实现（火山 AK/SK 签名换 token、阿里 DashScope），单元测试 mock 外部调用，需真实凭证联调 |
| 失败重试 | 自动重试 1 次：首次失败 `retry_count=1` 回 `pending`，二次失败置 `failed` |
| tts_params 写入 | `AudioTaskCreate` 增加可选 `tts_params`，参数优先级：任务级 > 全局 `tts_config` |
| 静态音频服务 | 不挂载 `/api/audio-files`（StaticFiles 目录浏览有风险），仅保留 `/download` |
| 长文本 | 不做分片，合成前校验长度 ≤ 5000 字，超长置失败 |
| 测试范围 | 工厂/适配器 mock 测试 + Worker pending→completed/failed 全流程 |

### 与文档差异 / 附带修改

- **火山引擎**：任务文档示例（`Bearer; {api_key}` 直接调用、空 appid/cluster）无法工作。真实流程为 `POST /api/v1/auth/token`（HMAC-SHA256 签名）获取 Access Token，再调用 `/api/v1/tts`，响应为 base64 音频帧需解码拼接。`TTSConfig` 新增 `appid`、`cluster`（默认 `volcano_tts`）字段。
- **阿里云**：任务文档示例的 `nls-gateway-.../stream/v1/tts` 为 WebSocket 协议（HTTP POST 不可用），改用 DashScope TTS HTTP 接口，`api_key` 即 DashScope API-Key，`voice_id` 即 sambert 模型名（如 `sambert-zhichu-v1`）。
- `AudioTask` 新增 `retry_count` 列。当前无迁移工具，**开发库 `backend/data/meditation.db` 需删除重建**（参照 `docs/ops/backend/backend-startup.md` Q4）。
- Worker 函数签名支持注入 `session_factory` / `poll_interval` / `max_batches`，便于测试与按需调用；启动方式 `uv run python -m app.services.audio_worker`。
- `scripts/start.bat` 的 Worker 启动 TODO 暂未填充（backend/frontend 启动同样为 TODO，留待后续任务统一）。
