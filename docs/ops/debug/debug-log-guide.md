# 调试日志使用指南

本文档面向 AI 应用与独立开发者，说明如何在 Windows + Git Bash 环境下开启、查看和过滤本项目的调试日志。

## 1. 日志系统说明

项目后端（FastAPI）与 Worker（`app.services.audio_worker`）使用 Python 标准库 `logging` 输出日志：

- 日志入口统一在 `backend/app/config.py` 的 `setup_logging()`。
- 默认日志级别由环境变量 `LOG_LEVEL` 控制，未设置时默认为 `INFO`。
- 排查问题时建议设置为 `DEBUG`，可看到请求体、响应事件、任务参数等详细信息。
- 日志直接输出到 stdout/stderr，**不会持久化到文件**，需自行重定向或复制保存。

## 2. 一键开启 DEBUG 日志

项目启动脚本 `scripts/start.bat` 与 `scripts/start.sh` 已默认注入 `LOG_LEVEL=DEBUG`。正常双击/执行脚本即可。

如需手动启动，在 Git Bash 中执行：

```bash
export LOG_LEVEL=DEBUG
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Worker 同理：

```bash
export LOG_LEVEL=DEBUG
cd backend
uv run python -m app.services.audio_worker
```

## 3. 查看日志

### 3.1 启动脚本输出的日志

`start.bat` / `start.sh` 启动的子进程会各自弹出窗口（Windows CMD）或在同一终端输出。DEBUG 日志通常以 `[模块名]` 前缀标识，例如：

```text
2026-08-10 14:32:02,123 - app.services.tts_aliyun - DEBUG - [AliyunTTS] qwen request: url=https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer model=qwen-audio-3.0-tts-plus voice=longanlingxin text_len=12 ...
```

### 3.2 按模块过滤

Git Bash 中可用 `grep` 过滤感兴趣的模块：

```bash
# 只看阿里云 TTS 相关日志
tail -f /path/to/log.txt | grep "AliyunTTS"

# 只看 Worker 任务日志
tail -f /path/to/log.txt | grep "AudioWorker"

# 只看 test-tts 接口日志
tail -f /path/to/log.txt | grep "test-tts"

# 只看 Dify 代理日志
tail -f /path/to/log.txt | grep "DifyProxy"
```

> 提示：Windows CMD 没有 `grep`，建议在 Git Bash 中操作。

### 3.3 日志重定向到文件

如需持久化，手动启动时重定向：

```bash
export LOG_LEVEL=DEBUG
cd backend
uv run uvicorn app.main:app --reload --port 8000 > backend.log 2>&1
```

Worker 同理：

```bash
uv run python -m app.services.audio_worker > worker.log 2>&1
```

## 4. 日志级别含义

| 级别 | 用途 | 示例 |
|---|---|---|
| `DEBUG` | 详细请求/响应、SSE 事件、参数映射 | 排查 TTS 失败时使用 |
| `INFO` | 关键流程节点 | 任务开始、test-tts 成功 |
| `WARNING` | 可恢复异常 | test-tts 失败、HTTP 4xx/5xx |
| `ERROR` | 严重错误 | SSE 解析失败、业务错误码 |

## 5. 安全与隐私

- 代码已避免在日志中打印完整 API Key，仅记录 `has_api_key=true/false` 或长度。
- 日志中会记录 model、voice、text 长度、instruction 长度等，**请勿将完整日志直接贴到公共平台或 issue 中**。
- 如需外部协助，建议先手动替换敏感信息，或只截取关键行。

## 6. 常用排查链路

```text
发现 TTS 报错
    │
    ▼
查看 [AudioWorker] 日志确认 task/script ID、model、voice、text_len
    │
    ▼
查看 [AliyunTTS] 日志确认实际请求 URL、payload_keys、SSE 错误码
    │
    ▼
必要时查询 SQLite（见《阿里云 TTS 排查清单》）
    │
    ▼
用 curl 直接调用阿里云接口复现
```

```text
发现 Dify 对话报错
    │
    ▼
查看 [DifyProxy] 日志确认 base_url、response_mode、query_len
    │
    ▼
查看 [DifyProxy] 响应状态码与 Dify 返回错误体
    │
    ▼
确认设置页或 backend/.env 中 Dify App Key 已配置
    │
    ▼
用 curl 直接调用 Dify /chat-messages 接口复现
```

## 7. 相关文档

- [阿里云 TTS 排查清单](./aliyun-tts-debug-checklist.md)
- [阿里云 TTS 音色更新说明](../aliyun/voice-update-guide.md)
- [阿里云百炼错误码](https://help.aliyun.com/zh/model-studio/error-code)
