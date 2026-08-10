# I1：阿里云 TTS 测试连接返回 400 Bad Request

## 缺陷现象

在设置页 → 语音合成 → 选择供应商 `aliyun` 并填写 API Key、音色 ID 后，点击“测试连接”报错：

```text
TTS 连接失败: Client error '400 Bad Request' for url
'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2audio/generation'
```

## 复现步骤

1. 打开 `http://localhost:5173/settings/tts`
2. 供应商选择“阿里云”
3. 填写有效的阿里云百炼 API Key（北京地域）
4. 音色 ID 填写非 Sambert 系列的值，例如：
   - `longanyang`
   - `longanhuan_v3.6`
   - `Cherry`
   - `qwen-audio-3.0-tts-plus`
5. 点击“测试连接”
6. 后端返回 400 Bad Request

## 错误日志

后端无异常栈，仅通过 `httpx.HTTPStatusError` 抛出：

```text
Client error '400 Bad Request' for url
'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2audio/generation'
```

## 根因分析

当前后端 `backend/app/services/tts_aliyun.py` 仍使用阿里云**已弃用的旧版 Sambert HTTP 接口**：

```text
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2audio/generation
```

请求体把前端填写的 `voice_id` 直接作为 `model` 发送：

```json
{
  "model": "{voice_id}",
  "input": { "text": "你好，这是一段测试音频。" },
  "parameters": {
    "format": "mp3",
    "sample_rate": 48000,
    "volume": 100,
    "rate": 1.0
  }
}
```

而根据阿里云官方《非实时语音合成用户指南》（[help.aliyun.com/.../non-realtime-tts-user-guide](https://help.aliyun.com/zh/model-studio/non-realtime-tts-user-guide)），新模型系列需要使用完全不同的接口和请求结构：

| 模型系列 | 端点 | 请求结构 |
|---|---|---|
| Qwen-Audio-TTS / CosyVoice | `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer` | `{"model": "...", "input": {"text": "...", "voice": "...", "format": "...", "sample_rate": ...}}` |
| Qwen-TTS / MiniMax | `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` | `{"model": "...", "input": {"text": "...", "voice": "...", "language_type": "..."}}` |

核心不匹配点：

1. **端点错误**：旧 `text2audio/generation` 仅支持早期 Sambert 模型，官方已建议新项目优先使用 CosyVoice / Qwen-TTS。
2. **字段层级错误**：新接口需要同时提供 `model`（模型名）和 `voice`（音色名），并把音色放在 `input.voice` 中；当前代码把 `voice_id` 当作 `model` 直接发送。
3. **响应格式错误**：旧接口直接返回音频二进制；新接口非流式返回 JSON，音频 URL 在 `output.audio.url` 中，需要二次下载。
4. **配置字段缺失**：当前 `TTSConfig` 只有 `voice_id`，缺少 `model` 和 `base_url`，无法正确调用新接口。

## 影响范围

- 设置页 `test-tts` 接口：阿里云供应商测试失败。
- 音频生成 Worker：使用阿里云供应商时，真实音频合成也会失败。
- 前端 `TTSSettings.tsx`：缺少 model / base_url / 音色选择等必要配置项。

## 关联修复任务

- **T9**：`docs/task/09-aliyun-qwen-tts.md` — 阿里云百炼 Qwen-Audio-TTS 接入
  - 重写 `AliyunTTS` 适配器，按 `model` 字段分发新旧接口
  - `TTSConfig` 增加 `model`、`base_url`
  - 前端增加 model 下拉、音色选择/自定义、base_url 输入
  - Worker 将 `voice_prompt` 作为 `instruction` 传入

## 建议修复范围

1. **后端**
   - `backend/app/services/tts_aliyun.py`：重写为按 `model` 分发，支持 `sambert-*` 旧路径和 `qwen-audio-*` / `cosyvoice-*` / `qwen3-tts-*` 新路径。
   - `backend/app/services/tts_base.py`：`synthesize` 增加 `instruction` 可选参数。
   - `backend/app/services/tts_volcano.py`：同步签名，忽略 `instruction`。
   - `backend/app/services/tts_factory.py`：把 `model`、`base_url` 传给 `AliyunTTS`。
   - `backend/app/schemas/setting.py`：`TTSConfig` 增加 `model`、`base_url`。
   - `backend/app/services/audio_worker.py`：合成时传入 `instruction=task.voice_prompt`。

2. **前端**
   - `frontend/src/types/index.ts`：`TTSConfig` 增加 `model`、`base_url`。
   - `frontend/src/components/settings/TTSSettings.tsx`：
     - provider 为 `aliyun` 时显示 `model` 下拉（如 `qwen-audio-3.0-tts-plus` / `cosyvoice-v3-flash` / `qwen3-tts-flash`）
     - 音色支持系统音色下拉 + 自定义输入
     - 显示 `base_url` 输入框
     - 隐藏火山专用字段（`secret_key`、`appid`、`cluster`）
   - `frontend/src/i18n/locales/zh.json` / `en.json`：补充相关文案。

3. **测试**
   - `backend/tests/test_tts.py`：补充新接口路径的 MockTransport 测试（SSE 累积、URL 下载、参数映射、错误处理）。
   - `backend/tests/test_audio_worker.py`：验证 worker 传入 `instruction`。

## 验收标准

- [ ] 填写 `provider=aliyun`、`model=qwen-audio-3.0-tts-plus`、`voice_id=longanlingxin`、有效 API Key 后，测试连接成功。
- [ ] 填写 `provider=aliyun`、`model=cosyvoice-v3-flash`、`voice_id=longanyang`、有效 API Key 后，测试连接成功。
- [ ] 旧 `model=sambert-zhichu-v1` 仍可走旧接口（向后兼容）。
- [ ] Worker 使用阿里云生成音频任务可正常完成并保存文件。
- [ ] 后端 pytest 全部通过。
- [ ] 前端 `npm run lint`、`npm run build` 通过。

## 风险备注

- 阿里云百炼非实时语音合成仅华北2（北京）地域可用，需使用北京地域 API Key。
- 不同模型系列音色不通用，需在前端明确提示用户按所选 model 填写对应音色。
- 若用户没有 WorkspaceId，可继续使用旧域名 `https://dashscope.aliyuncs.com/api/v1`；有 WorkspaceId 时建议使用专属域名以获得更稳定性能。
