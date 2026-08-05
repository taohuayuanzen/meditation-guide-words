# T9：阿里云百炼 Qwen-Audio-TTS 接入

## 任务目标

将阿里云 TTS 适配器从旧的 sambert 接口升级为百炼 Qwen-Audio-TTS（`qwen-audio-3.0-tts-plus`），支持 SSE 流式合成、`instruction` 自然语言指令控制；同步调整设置页阿里云表单字段与前后端类型。

**预计耗时**：1 ~ 1.5 天

---

## 背景

用户为**阿里云百炼 Token Plan 个人会员**，需通过百炼 API 调用语音合成模型 `qwen-audio-3.0-tts-plus`。该模型与现有 AliyunTTS（sambert 的 `aigc/text2audio/generation` 二进制接口）协议完全不同，需重写适配器。

### 官方接口要点（已核对）

- 端点：`POST https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer`
  - 官方建议使用业务空间（Workspace）专属域名；旧域名 `https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer` 仍可用
  - **华北2（北京）地域**，需北京地域 API Key
- 鉴权：`Authorization: Bearer <api_key>`
- 流式：请求头加 `X-DashScope-SSE: enable`，服务端以 SSE 返回
  - `sentence-synthesis` 事件：`output.audio.data` 为 Base64 音频块，**按顺序追加即完整音频**
  - 结束：`output.finish_reason == "stop"`
- 请求体：
  ```json
  {
    "model": "qwen-audio-3.0-tts-plus",
    "input": {
      "text": "...",
      "voice": "longanlingxin",
      "format": "mp3",
      "sample_rate": 48000,
      "volume": 50,
      "rate": 1.0,
      "instruction": "温柔女声，语速慢"
    }
  }
  ```
- 参数：`format`(mp3/pcm/wav/opus，默认 mp3)、`sample_rate`(8000~48000)、`volume`(0~100，默认50)、`rate`(0.5~2.0)、`pitch`(0.5~2.0)、`instruction`（方言/情感/角色自然语言指令，**上限 100 字符**，中文按 2 字符计）、`language_hints`
- 系统音色（plus 仅 2 个）：`longanlingxin`（龙安灵心，知心温暖女声，25 岁，中/英）、`longanlufeng`（龙安鲁风，明亮开朗男声，25 岁，中/英）；另有 500+ 基础音色（命名 `qwen-audio-3.0-tts-plus-{后缀}`，列表为官方 Excel）
- 参考文档：
  - 用户模型文档（ID 3046858，需登录）：https://bailian.console.aliyun.com/cn-beijing/?tab=doc#/doc/?type=model&url=3046858
  - HTTP API 参考：https://help.aliyun.com/zh/model-studio/cosyvoice-tts-http-api
  - Qwen-Audio-TTS 音色列表：https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list

---

## 前置依赖

- T5 完成（TTS 适配层 `TTSBase`/`AliyunTTS`/`get_tts_service` 已就绪）
- T8 完成（设置页 TTS 表单、`test-tts` 真实合成已就绪）
- 用户侧：百炼 API Key（北京地域）、确认 Token Plan 覆盖 `qwen-audio-3.0-tts-plus`、WorkspaceId（可选）

---

## 详细步骤

### 9.1 后端：重写 AliyunTTS 适配器（model 分发）

`backend/app/services/tts_aliyun.py`：

- `AliyunTTS.__init__(api_key, secret_key="", model="qwen-audio-3.0-tts-plus", base_url="https://dashscope.aliyuncs.com/api/v1", *, transport=None)`
- `is_available()`：`api_key` 非空即可
- `synthesize(text, voice_id, speed=1.0, volume=1.0, output_format="mp3", instruction=None)`：
  - 若 `model` 以 `sambert` 开头 → 走**旧路径**（`{base_url}/services/aigc/text2audio/generation`，二进制响应），保持向后兼容
  - 否则 → **Qwen 路径**：
    1. URL：`{base_url.rstrip('/')}/services/audio/tts/SpeechSynthesizer`
    2. body：`{"model": model, "input": {"text": text, "voice": voice_id, "format": output_format, "sample_rate": 48000, "volume": clamp(round(volume*50), 0, 100), "rate": speed, ...instruction}}`
    3. `instruction` 非空时传入（**≤100 字符截断**，中文按 2 字符计）
    4. headers 增加 `X-DashScope-SSE: enable`
    5. `client.stream("POST", ...)` → 逐行解析 SSE（`data: ` 前缀），累积 `output.audio.data` 的 base64 → 统一解码返回 bytes
    6. 响应非 2xx 或 JSON 含 `code`/`message` 时抛 `RuntimeError`
  - 需注入 `httpx.MockTransport`（测试用），与现有 Volcano 一致

### 9.2 后端：TTSBase 接口与工厂

- `backend/app/services/tts_base.py`：`synthesize` 增加可选参数 `instruction: str | None = None`
- `backend/app/services/tts_volcano.py`：`synthesize` 签名同步增加 `instruction=None`（忽略该参数）
- `backend/app/services/tts_factory.py`：`AliyunTTS(api_key=..., secret_key=..., model=config.get("model", "qwen-audio-3.0-tts-plus"), base_url=config.get("base_url", "https://dashscope.aliyuncs.com/api/v1"))`

### 9.3 后端：Schema 扩展

`backend/app/schemas/setting.py` 的 `TTSConfig` 增加：

```python
model: str = "qwen-audio-3.0-tts-plus"
base_url: str = "https://dashscope.aliyuncs.com/api/v1"
```

> SQLite 的 `settings` 表为 JSON 列，无需迁移。

### 9.4 后端：Worker 传递 instruction

`backend/app/services/audio_worker.py` 中 `service.synthesize(...)` 增加 `instruction=task.voice_prompt`（声音自然语言描述，如"温柔女声，语速慢，正念风格"）。火山适配器忽略该参数，阿里云 Qwen 将其作为 `instruction`。

### 9.5 前端：设置页阿里云表单调整

`frontend/src/components/settings/TTSSettings.tsx`：

- provider 选项：`volcano`（火山引擎）/ `aliyun`（阿里云百炼 Qwen Audio TTS，i18n label 更新）
- 当 `provider === "aliyun"` 时显示：
  - **model**：Select（`qwen-audio-3.0-tts-plus` / `qwen-audio-3.0-tts-flash`）
  - **api_key**：文本（password）
  - **voice_id（音色）**：Select 内置系统音色（`longanlingxin` 龙安灵心 / `longanlufeng` 龙安鲁风）+ "自定义…"选项切换为文本输入框（填基础音色 ID）
  - **speed / volume / output_format（mp3/wav）**：沿用现有控件（映射见 9.1）
  - **base_url**：文本输入（默认 `https://dashscope.aliyuncs.com/api/v1`，可填 MaaS 专属域名）
- 当 `provider === "aliyun"` 时**隐藏** `secret_key` / `appid` / `cluster`（火山专用）
- `frontend/src/types/index.ts` 的 `TTSConfig` 同步增加 `model`、`base_url`
- `frontend/src/i18n/locales/zh.json` / `en.json` 增加：`settings.model`、`settings.voiceCustom`（自定义）等文案

### 9.6 后端测试

`backend/tests/test_tts.py` 补充：

- `AliyunTTS` Qwen 路径：MockTransport 返回 SSE 文本（`data: {...sentence-synthesis...}` 若干条 + `finish_reason=stop`），断言累积 base64 == 预期音频
- model 分发：`sambert-*` → 旧端点；`qwen-audio-*` → 新端点
- 参数映射：`volume*50`、`rate=speed`、`format=output_format`、`instruction` 传递与超长截断
- 非 2xx / 业务错误码 → 抛 `RuntimeError`

`backend/tests/test_audio_worker.py`：FakeTTS 捕获 `instruction` 参数，断言 worker 传入 `task.voice_prompt`

### 9.7 文档更新

- `docs/ops/t5-tts-operations.md`：阿里云段落改为 Qwen-Audio-TTS（model/base_url/音色/instruction/凭证注意点）
- 本任务完成后追加"当前进度"章节

---

## 关键设计点

- **model 分发**：`model` 字段同时作为接口分发键（`sambert-*` 旧路径 / `qwen-audio-*`、`cosyvoice-*` 新路径），保留兼容、零数据迁移
- **SSE 流式累积**：复用 `data:` 行解析模式（与前端 sseParser 同思路），逐块 base64 追加，避免二次下载 URL
- **instruction 直通**：`voice_prompt` 自然语言直接驱动合成（Qwen 特有能力），截断至 100 字符
- **参数映射**：现有 `volume(0-2) ×50 → 0-100`、`speed → rate(0.5-2)`、`output_format → format`，最大复用现有设置字段
- **长文本**：SSE 单请求整段合成，worker 保留 5000 字安全线；超限联调后补分片

---

## 验收标准

- [ ] `AliyunTTS` 支持 `qwen-audio-3.0-tts-plus`（SSE 流式）与 `sambert-*` 旧路径自动分发
- [ ] `TTSConfig.model` / `base_url` 字段生效，`get_tts_service` 正确传参
- [ ] Worker 将 `voice_prompt` 作为 `instruction` 传给阿里云（火山忽略，不报错）
- [ ] 设置页阿里云表单：model 下拉、音色下拉+自定义、字段条件显示、base_url 可配
- [ ] 后端 pytest 全过、前端 biome/build 通过
- [ ] 真实凭证联调：`test-tts` 合成成功；工作区 2 生成音频可播放/下载

---

## 关联文档

- `docs/tech/tech-spec.md` 第 10 章（TTS 适配层）
- `docs/prd/meditation-guide-words-prd.md` 第 4.4.2 章（TTS 配置）
- `docs/ops/t5-tts-operations.md`（阿里云凭证与联调）
- `docs/task/05-tts-and-worker.md`（T5 适配层基线）
- `docs/task/08-settings-and-polish.md`（设置页基线）

---

## 风险备注

- **Token Plan 覆盖**：需在百炼控制台确认 `qwen-audio-3.0-tts-plus` 在 Token Plan 计费范围内（否则按量计费）
- **地域限制**：仅华北2（北京）可用，API Key 必须为北京地域
- **单次文本上限**：官方文档未写明；SSE 流式按句返回，先按整段合成，若超限（联调报错）再补分片拼接
- **instruction 限制**：≤100 字符（中文按 2 字符计），超长需截断
- **MaaS 专属域名**：不填 base_url 时走旧 `dashscope.aliyuncs.com`（仍可用）；填 `{WorkspaceId}.cn-beijing.maas.aliyuncs.com` 性能更稳（需用户提供 WorkspaceId）

---

## 决策确认表（2026-08-06 已确认）

| 决策点 | 结论 |
|---|---|
| 适配器改造方式 | model 分发，保留 sambert 旧路径 |
| 接口地址 | 新增 `base_url` 字段，默认旧域名 `https://dashscope.aliyuncs.com/api/v1` |
| 模型字段 | 新增 `model` 字段，默认 `qwen-audio-3.0-tts-plus`（可切 flash） |
| 音色配置 | 系统音色下拉（龙安灵心/龙安鲁风）+ 自定义输入 |
| instruction | 支持：worker 传 `voice_prompt`，adapter 内 ≤100 字符截断 |
| 长文本 | 先单请求（SSE 整段），超限联调后再补分片 |
