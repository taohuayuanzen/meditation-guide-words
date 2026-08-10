# 阿里云 TTS 排查清单

针对后端或 Worker 调用阿里云百炼 TTS 时出现的错误（典型如 `[InvalidParameter] Please ensure input text is valid.`），按本清单逐步定位根因。

## 1. 典型报错

```text
阿里云 TTS 合成失败: [InvalidParameter] Please ensure input text is valid.
```

该错误来自阿里云 SSE 响应，官方解释为：未发送待合成文本，或 `text` 参数赋值失败。实际项目中更常见的原因是 **model 与 voice 不匹配** 或 **待合成文本为空**。

## 2. 前置检查

- 已使用 `scripts/start.bat` 或 `scripts/start.sh` 启动服务（默认 `LOG_LEVEL=DEBUG`）。
- 确认 API Key 为**华北 2（北京）地域**的百炼 API Key。
- 确认所选 model 与 voice 来自同一模型系列（见下表）。

## 3. 核对 model 与 voice 匹配关系

| model | 支持的系统音色 | 不支持示例 |
|---|---|---|
| `qwen-audio-3.0-tts-plus` | `longanlingxin`、`longanlufeng` | `longanyang`、`longanhuan_v3` |
| `qwen-audio-3.0-tts-flash` | `longanfengyue`、`longanyuanfei`、`longanlingxi`、`longanxiaoxin`、`longanhuan_v3.6`、`longjielidou_v3.6`、`longpaopao_v3.6`、`longhuohuo_v3.6`、`longchuanshu_v3.6`、`loongmary`、`loongeva_v3.6`、`loongjohn` | `longanyang` |
| `cosyvoice-v3-flash` | `longanyang`、`longanhuan_v3` | `longanlingxin` |

> 完整音色列表参考：[Qwen-Audio-TTS 音色列表](https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list)、[CosyVoice 音色列表](https://help.aliyun.com/zh/model-studio/cosyvoice-tts-voice-list)。

## 4. 排查步骤

### 步骤 1：查看设置页当前配置

打开 `http://localhost:5173/settings/tts`，确认：

- 供应商是否为 `aliyun`
- model 是否为预期值
- 音色 ID 是否为当前 model 支持的系统音色，或自定义音色是否拼写正确
- base_url 是否为 `https://dashscope.aliyuncs.com/api/v1`（默认）或正确的 MaaS 专属域名

### 步骤 2：查看 test-tts 日志

在设置页点击“测试连接”，观察后端日志中的 `[test-tts]` 行：

```text
[test-tts] provider=aliyun model=qwen-audio-3.0-tts-plus voice=longanlingxin base_url=https://dashscope.aliyuncs.com/api/v1 has_api_key=True
```

如果测试连接也失败，说明是配置问题；如果测试连接成功但音频任务失败，说明问题在 Worker 或任务数据。

### 步骤 3：查看 Worker 任务日志

音频生成时，查找 `[AudioWorker]` 日志：

```text
[AudioWorker] task=1 script=3 provider=aliyun model=qwen-audio-3.0-tts-plus voice=longanlingxin text_len=523 speed=1.0 volume=1.0 format=mp3 instruction_len=12
```

重点确认：

- `text_len` 是否为 0 或过小。
- `model` 与 `voice` 是否匹配。
- `instruction_len` 是否超过 100（代码会自动截断，但可辅助判断）。

### 步骤 4：查看 AliyunTTS 请求日志

```text
[AliyunTTS] qwen request: url=... model=qwen-audio-3.0-tts-plus voice=longanlingxin text_len=523 instruction_len=12 payload_keys=['text', 'voice', 'format', 'sample_rate', 'volume', 'rate', 'instruction']
```

确认 `payload_keys` 包含 `text` 和 `voice`，且 `text_len` 正常。

### 步骤 5：查看 SSE 业务错误

若服务端返回错误，日志会输出：

```text
[AliyunTTS] SSE business error: code=InvalidParameter message=Please ensure input text is valid. request_id=xxxx-xxxx
```

记录 `request_id`，可用于阿里云控制台进一步查询。

### 步骤 6：查询 SQLite 核对原始数据

在 Git Bash 中进入 backend 目录，用 Python 直接查询：

```bash
cd backend
.venv/Scripts/python - <<'PY'
import sqlite3, json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
conn = sqlite3.connect("data/meditation.db")
conn.row_factory = sqlite3.Row

# 查看失败的任务
task_id = 1  # 替换为实际任务 ID
row = conn.execute(
    "SELECT id, script_id, voice_prompt, tts_params, error_msg, status, retry_count FROM audio_tasks WHERE id=?",
    (task_id,),
).fetchone()
print("Task:", dict(row))

# 查看对应脚本内容
script = conn.execute(
    "SELECT id, title, content FROM scripts WHERE id=?", (row["script_id"],)
).fetchone()
print("Script:", dict(script))

# 查看 TTS 配置
setting = conn.execute("SELECT tts_config FROM settings WHERE id=1").fetchone()
print("TTS config:", json.loads(setting["tts_config"]))
PY
```

关注：

- `script.content` 是否为空或仅空白。
- `audio_tasks.tts_params` 里的 `voice_id` 是否与设置页一致。
- `settings.tts_config` 里的 `model` 和 `voice_id` 是否匹配。

### 步骤 7：用 curl 直接复现

替换 `<YOUR_API_KEY>`、`<MODEL>`、`<VOICE>`、`<TEXT>`：

```bash
curl -X POST https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer \
-H "Authorization: Bearer <YOUR_API_KEY>" \
-H "Content-Type: application/json" \
-H "X-DashScope-SSE: enable" \
-d '{
  "model": "<MODEL>",
  "input": {
    "text": "<TEXT>",
    "voice": "<VOICE>",
    "format": "mp3",
    "sample_rate": 24000,
    "volume": 50,
    "rate": 1.0
  }
}'
```

如果 curl 能复现同样的错误，说明是阿里云侧参数问题（model/voice/text 等）；如果 curl 成功但项目失败，说明是代码参数传递问题。

## 5. 常见日志模式 → 可能原因

| 日志/报错 | 最可能原因 | 下一步 |
|---|---|---|
| `[AliyunTTS] SSE business error: code=InvalidParameter message=Please ensure input text is valid.` | model/voice 不匹配，或 `text` 为空/仅空白 | 核对 model/voice 组合，查 SQLite 看 `script.content` |
| `[AudioWorker] task=... text_len=0 ...` | 引导词为空 | 检查脚本生成与保存逻辑 |
| `[test-tts] HTTP error: Client error '401 Unauthorized'...` | API Key 错误、过期、地域不对，或 Token Plan 专属 key 未配专属 base_url | 检查 base_url 和 API Key |
| `[AliyunTTS] SSE business error: code=InvalidParameter message=[cosyvoice:]Engine error [411]...` | cosyvoice 模型使用了其他模型的音色 | 核对音色列表 |
| `[AliyunTTS] SSE business error: code=InvalidParameter message=[tts:]Engine return error code: 428` | instruction 超长或格式不对（cosyvoice 系统音色） | 缩短/调整 voice_prompt |
| `[AudioWorker] task=... provider=aliyun model=... voice=...` 但 voice 明显是火山音色（如 `BV001_streaming`） | 切换 provider 后未更新 voice_id | 在设置页重新选择阿里云音色 |

## 6. 快速修复建议

- **model/voice 不匹配**：在设置页重新选择 model，系统会自动重置为对应音色列表中的第一个音色。
- **text 为空**：检查工作区 1 的脚本是否正确保存，或重新生成脚本后再创建音频任务。
- **instruction 问题**：使用 qwen-audio 模型时可输入任意自然语言指令；使用 cosyvoice 系统音色时避免自由指令。
- **API Key/地域问题**：确认使用华北 2（北京）地域的 Key；Token Plan 专属 Key 需配合专属 base_url。

## 7. 仍无法定位

若按清单排查后仍无法解决，请提供以下信息：

1. 设置页截图或 `settings.tts_config` 完整内容（**请打码 API Key**）。
2. 失败任务的 `audio_tasks` 记录（`voice_prompt`、`tts_params`、`error_msg`）。
3. 对应 `scripts.content` 前 200 字。
4. 后端/Worker 的 `[AliyunTTS]` 和 `[AudioWorker]` 相关日志。
5. 如有 `request_id`，请一并提供。

## 8. 相关文档

- [调试日志使用指南](./debug-log-guide.md)
- [阿里云 TTS 音色更新说明](../aliyun/voice-update-guide.md)
- [阿里云百炼非实时语音合成用户指南](https://help.aliyun.com/zh/model-studio/non-realtime-tts-user-guide)
- [阿里云百炼错误码](https://help.aliyun.com/zh/model-studio/error-code)
