# I2：阿里云 TTS 音频任务因 Dify 返回无效音色 ID 失败

## 缺陷现象

工作区 2 选择引导词并输入声音描述（如"温柔女声，节奏缓和，适当留白"）后创建音频任务，任务最终状态为 `failed`，错误信息：

```text
阿里云 TTS 合成失败: [InvalidParameter] [cosyvoice:]Engine error [411]: TTS speak operation failed
```

设置页中 TTS 测试连接（使用 `longanlufeng`）可以正常合成。

## 复现步骤

1. 在设置页配置 TTS 供应商为 `aliyun`，模型 `qwen-audio-3.0-tts-plus`，音色 `longanlufeng`，填写有效 API Key。
2. 进入工作区 2，选择一条已保存的引导词。
3. 声音描述输入"温柔女声，节奏缓和，适当留白"。
4. 点击"生成"。
5. 前端调用 Dify App B 解析声音描述，返回 `tts_params`：

   ```json
   {
     "voice_id": "female_gentle_01",
     "speed": 0.85,
     "volume": 1,
     "emotion": "gentle",
     "output_format": "mp3"
   }
   ```

6. Worker 处理任务时把 `voice_id=female_gentle_01` 传给阿里云 TTS。
7. 任务失败，状态变为 `failed`，`error_msg` 记录 `[InvalidParameter] [cosyvoice:]Engine error [411]...`。

## 错误日志

Worker 日志：

```text
[AudioWorker] task=2 script=4 provider=aliyun model=qwen-audio-3.0-tts-plus voice=female_gentle_01 text_len=1073 speed=0.85 volume=1.0 format=mp3 instruction_len=14
[AliyunTTS] SSE business error: code=InvalidParameter message=[cosyvoice:]Engine error [411]: TTS speak operation failed request_id=...
```

## 根因分析

1. **Dify App B 返回通用占位音色**：当前 System Prompt 只要求 LLM"根据性别、年龄感选择合理的 voice_id"，没有限定必须是当前 TTS 供应商支持的音色。LLM 因此输出了描述性占位符 `female_gentle_01`，而非阿里云实际支持的音色 ID（如 `longanlufeng`）。
2. **Worker 优先使用任务级 `voice_id`**：`backend/app/services/audio_worker.py` 中优先级为 `tts_params.voice_id > tts_config.voice_id`。任务级参数覆盖了设置页中已验证有效的阿里云音色。
3. **阿里云拒绝无效音色**：`qwen-audio-3.0-tts-plus` 模型只支持 `longan*` / `loong*` 系列系统音色，收到 `female_gentle_01` 后返回 `InvalidParameter` / `[cosyvoice:]Engine error [411]`。

## 影响范围

- 音频生成 Worker：使用阿里云供应商时，任何由 Dify 返回非阿里云音色的任务都会失败。
- 工作区 2 的全链路音频生成：自然语言声音描述功能不可用。
- 不影响设置页 `test-tts`，因为测试连接直接使用 `tts_config.voice_id`。

## 修复方案

### 已实施的代码修复

修改 `backend/app/services/audio_worker.py`，对 `aliyun` provider 增加任务级 `voice_id` 的防御性校验：若任务级 `voice_id` 不是阿里云已知音色前缀（`long` / `loong` / `sambert`），则回退到设置页配置的 `tts_config.voice_id`。`speed`、`volume`、`output_format` 仍按任务级参数生效。

```python
provider = tts_config.get("provider", "volcano")
voice_id = tts_params.get("voice_id") or ""
if provider == "aliyun" and voice_id:
    if not (
        voice_id.startswith("long")
        or voice_id.startswith("loong")
        or voice_id.startswith("sambert")
    ):
        voice_id = ""
voice_id = voice_id or tts_config.get("voice_id") or ""
if not voice_id:
    raise ValueError("未配置音色（voice_id）")
```

同时补充单元测试 `backend/tests/test_audio_worker.py::test_process_task_aliyun_invalid_voice_id_fallback`，验证无效 `female_gentle_01` 会回退到 `longanlufeng`。

### 建议补充的 Dify 配置修复

进入 Dify 控制台，修改"冥想音频生成"（App B）的 System Prompt，明确要求 LLM 只输出当前供应商支持的音色 ID。例如：

```text
当前 TTS 供应商为阿里云百炼，模型为 qwen-audio-3.0-tts-plus。
请从用户描述中提取声音参数，voice_id 必须选自以下阿里云音色：
- longanlingxin
- longanlufeng

JSON Schema：
{
  "voice_id": "longanlufeng",
  "speed": 0.85,
  "volume": 1.0,
  "emotion": "gentle",
  "output_format": "mp3"
}
```

## 验证结果

- `uv run pytest -q`：49 passed
- 重试任务 2 后状态变为 `completed`
- 生成音频文件 `./data/audio/2.mp3`（9.7 MB）
- `GET /api/audio-tasks/2/download` 返回 `200`

## 关联文件

- `backend/app/services/audio_worker.py`
- `backend/app/services/tts_aliyun.py`
- `backend/tests/test_audio_worker.py`
- `frontend/src/components/settings/TTSSettings.tsx`
- `frontend/src/components/workspace/AudioWorkspace.tsx`
- `frontend/src/services/difyService.ts`
- `docs/task/03-dify-setup.md`
- `docs/ops/debug/aliyun-tts-debug-checklist.md`

## 风险备注

- 本次代码修复是防御性回退，仍允许任务级 `voice_id` 覆盖设置页配置；只有当任务级音色明显不属于阿里云命名空间时才回退。
- 若后续新增阿里云音色前缀不在 `long` / `loong` / `sambert` 范围内，需同步更新 `audio_worker.py` 的前缀白名单，或改为从设置页拉取有效音色列表进行校验。
- 如果 Dify App B 的 Prompt 不修正，其他参数（如 `emotion`）仍可能包含供应商不支持的内容，但当前只发现 `voice_id` 导致失败。
