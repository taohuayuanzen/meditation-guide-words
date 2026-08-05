# T5 操作文档：TTS 凭证配置与 Worker 联调

> 日期：2026-08-05
> 适用范围：TTS 适配层（火山引擎 / 阿里云 DashScope）与异步音频 Worker 所需的人工操作
> 关联任务：`docs/task/05-tts-and-worker.md`
> 说明：本文档仅覆盖**需要人工操作**的部分：供应商凭证开通、数据库重建、TTS 配置、Worker 启动与真实凭证联调验证。

---

## 一、人工操作清单

| # | 操作 | 是否需要 | 说明 |
|---|------|---------|------|
| 1 | 开通 TTS 供应商服务并获取凭证 | 必做 | 火山引擎 或 阿里云 DashScope，二选一 |
| 2 | 重建开发数据库 | 必做（一次性） | T5 为 `AudioTask` 新增 `retry_count` 列，无迁移工具 |
| 3 | 在设置中配置 TTS 凭证 | 必做 | 通过 `POST /api/settings`（或后续设置页） |
| 4 | 启动音频 Worker | 必做 | `python -m app.services.audio_worker` |
| 5 | 真实凭证联调验证 | 必做 | test-tts → 建任务 → 下载，确认端到端可用 |

---

## 二、TTS 供应商凭证开通

> 两家供应商二选一。代码均已按真实协议实现，但**未经过真实凭证验证**，联调时以本节为准调整参数。

### 2.1 火山引擎（推荐，国内网络直连稳定）

1. 注册登录 [火山引擎](https://www.volcengine.com/)，完成**实名认证**。
2. 控制台搜索"**语音技术**" → 进入控制台 → 开通 **TTS 语音合成**服务。
3. 获取凭证：

| 配置字段 | 获取位置 | 说明 |
|---------|---------|------|
| `api_key`（Access Key） | 右上角头像 → **访问控制（IAM）** → 密钥管理 | 创建密钥对，即 AK |
| `secret_key`（Secret Key） | 同上 | 即 SK |
| `appid`（应用 ID） | 语音技术控制台 → **应用管理** → 创建应用 | T5 新增字段，鉴权必需 |
| `cluster` | 官方默认 `volcano_tts` | 一般无需修改 |
| `voice_id`（音色） | 语音技术控制台 → **音色列表** 或官方文档 | 例：`BV001_streaming`（温柔女声） |

> 坑：AK/SK 是火山引擎**账号级**密钥，不是语音服务的 App ID，两者都要配。鉴权时会用 AK/SK 对 appid 签发临时 Access Token，返回的 base64 音频帧由后端解码拼接，无需人工处理。

### 2.2 阿里云 DashScope（百炼）

1. 注册登录 [阿里云](https://www.aliyun.com/)，完成**实名认证**。
2. 开通 [百炼（DashScope）](https://dashscope.console.aliyun.com/)，模型广场搜索"语音合成"。
3. 获取凭证：

| 配置字段 | 获取位置 | 说明 |
|---------|---------|------|
| `api_key` | 百炼控制台 → **API-KEY** → 创建 | DashScope API-Key |
| `voice_id` | 模型广场 sambert 系列 | 即模型名，例：`sambert-zhichu-v1`（知楚） |

> `secret_key`、`appid`、`cluster` 阿里云不需要，留空即可。后端把 `voice_id` 作为 `model`、`speed` 映射 `rate`、`volume` 按 ×100 映射。

---

## 三、重建开发数据库（一次性，必做）

T5 给 `audio_tasks` 表新增了 `retry_count` 列。项目当前**无迁移工具**，已存在的开发库不会自动加列，Worker 读写该列会报 `no such column: audio_tasks.retry_count`。

> 以下会**删除全部本地引导词 / 音频任务 / 设置**。若需保留数据，先导出，或等后续引入 Alembic 迁移。

```powershell
cd C:\projects\apps\meditation-guide-words\backend

# 删除旧数据库（音频文件在 data/audio/，不受影响）
Remove-Item data\meditation.db -ErrorAction SilentlyContinue

# 重启后端，lifespan 会自动建表（含 retry_count 列）
uv run uvicorn app.main:app --reload --port 8000
```

验证：

```powershell
curl http://localhost:8000/api/health
# → {"status":"ok"}
```

---

## 四、配置 TTS 凭证

TTS 凭证由设置页持久化到 `settings` 表（`tts_config`），**不写入 `.env`**。前端设置页完成后可直接在页面配置；当前阶段用 API：

```powershell
# 火山引擎示例
curl -X POST http://localhost:8000/api/settings `
  -H "Content-Type: application/json" `
  --data-binary "@setting-volcano.json"
```

`setting-volcano.json`（完整 Schema，含 LLM / Dify / 通用默认值）：

```json
{
  "llm_config": {
    "provider": "deepseek",
    "base_url": "",
    "api_key": "",
    "model": "",
    "temperature": 0.7,
    "max_tokens": null
  },
  "tts_config": {
    "provider": "volcano",
    "api_key": "AK",
    "secret_key": "SK",
    "appid": "应用ID",
    "cluster": "volcano_tts",
    "voice_id": "BV001_streaming",
    "speed": 1.0,
    "volume": 1.0,
    "output_format": "mp3"
  },
  "dify_config": {
    "base_url": "http://localhost/v1",
    "script_app_key": "",
    "audio_app_key": ""
  },
  "general_config": {
    "language": "zh",
    "theme": "light",
    "audio_output_dir": "./data/audio"
  }
}
```

阿里云只需把 `provider` 改为 `aliyun`，填 `api_key` + `voice_id`，其余留空。

---

## 五、启动音频 Worker

Worker 是**独立进程**，与 FastAPI 分开启动：

```powershell
cd C:\projects\apps\meditation-guide-words\backend
uv run python -m app.services.audio_worker
```

- 默认并发 2（`WORKER_CONCURRENCY` 可改 `.env`），每 2 秒轮询一次 `pending` 任务
- 正常启动后无输出，有任务时处理并写日志到终端
- 失败自动重试 1 次，仍失败置 `failed` 并写 `error_msg`
- 启动顺序：先启动后端（建表），再启动 Worker

> 手动联调可只开 Worker 窗口观察日志；Worker 崩溃会导致任务停滞，可用 `taskkill` 后重新启动。

---

## 六、端到端联调验证

> 需先完成：数据库重建 + 凭证配置 + Worker 启动。

```powershell
# ① 测试 TTS 凭证是否可用（只校验配置完整性，不真实合成）
curl -X POST http://localhost:8000/api/settings/test-tts `
  -H "Content-Type: application/json" `
  -d '{"provider":"volcano","api_key":"AK","secret_key":"SK","appid":"appid","cluster":"volcano_tts","voice_id":"BV001_streaming","speed":1.0,"volume":1.0,"output_format":"mp3"}'
# → {"status":"ok"}

# ② 创建一条引导词
curl -X POST http://localhost:8000/api/scripts `
  -H "Content-Type: application/json" `
  -d '{"title":"测试","content":"请闭上眼睛，深呼吸三次，感受身体的放松。","session_id":""}'

# ③ 提交音频任务（把 <SCRIPT_ID> 换成上一步返回的 id）
curl -X POST http://localhost:8000/api/audio-tasks `
  -H "Content-Type: application/json" `
  -d '{"script_id":1,"voice_prompt":"温柔女声，语速慢，正念风格","tts_params":{"voice_id":"BV001_streaming","speed":0.9,"volume":1.0,"output_format":"mp3"}}'

# ④ 轮询任务状态，等待 completed（或 failed + error_msg）
curl http://localhost:8000/api/audio-tasks/1

# ⑤ 下载音频验证文件头
curl -o test.mp3 http://localhost:8000/api/audio-tasks/1/download
# MP3 文件头应为 49 44 33（"ID3"）或 0xFF Ex
```

**排查要点**

| 现象 | 可能原因 |
|------|---------|
| `no such column: audio_tasks.retry_count` | 未重建数据库，见第三节 |
| 任务一直 `pending` | Worker 未启动 / Worker 崩溃 |
| `failed` + `401` | 火山 AK/SK/AppID 不匹配，或未开通服务 |
| `failed` + `文本过长` | 正文超过 5000 字上限（MVP 限制，不做分片） |
| `failed` + `未配置音色` | `tts_params` 与设置均未填 `voice_id` |

---

## 七、常见问题

| # | 问题 | 解法 |
|---|------|------|
| 1 | 火山 `message` 为英文错误码 | 核对 `api_key`（AK）、`secret_key`（SK）、`appid` 是否配套；AK/SK 需在语音技术控制台绑定对应应用 |
| 2 | 阿里云返回 404 / InvalidApiKey | 确认是 DashScope API-Key（形如 `sk-`），且已开通百炼服务 |
| 3 | 音色 ID 不确定 | 火山看控制台音色列表；阿里看百炼模型广场 sambert 模型名 |
| 4 | 下载 404 `Audio file missing` | 音频目录被清理或路径变更，重新合成 |
| 5 | 多次重试仍失败 | 先跑 `test-tts` 排除凭证问题，再查看 `error_msg` |

---

## 相关文档

- [T5 任务文档](../task/05-tts-and-worker.md)
- [后端启动与运维指南](backend/backend-startup.md)
- [技术规范 — 第 9、10 章](../tech/tech-spec.md)
