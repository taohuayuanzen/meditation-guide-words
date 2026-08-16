# T17：冥想音频分段合成、静音拼接与任务快照

> 任务状态：✅ 已实施

> 收口记录（2026-08-16）：preview 由服务端签发 render plan 与上下文摘要；创建任务会检测
> Script/TTS 配置变化；音频能力 API、完整本地处理阶段、可恢复 manifest、Qwen 非 SSML
> 路径和 CosyVoice 受控 SSML（≤10 秒）路径均已实现。自动测试不调用真实 TTS。

## 任务目标

基于 T16 生成并校验过的 `render_plan`，将当前“整篇正文一次提交 TTS”的 Worker 改造为可恢复的冥想音频渲染流水线：按语义段落合成语音，在指定位置插入确定性静音，最终输出统一 MP3，并确保重试始终复用创建任务时的计划、模型、音色和参数快照。

默认渲染路径：

```text
已校验 render_plan
  → 固化非敏感 TTS 快照
  → 分段生成中间 WAV
  → 生成静音片段
  → FFmpeg 拼接与统一编码
  → FFprobe 实测时长
  → 最终 MP3
```

---

## 前置依赖

- T16 完成，Script 具有 `script_plan`，preview API 可返回合法 `render_plan`。
- 当前 `AliyunTTS`、TTS 工厂、Audio Worker 和 AudioTask API 可用。
- 本地安装 FFmpeg 与 FFprobe；能力检查方式可复用音乐生成链路。

参考：

- [Qwen-Audio-TTS/CosyVoice HTTP API](https://help.aliyun.com/zh/model-studio/cosyvoice-tts-http-api)
- [SSML 与 LaTeX](https://help.aliyun.com/zh/model-studio/ssml-latex-user-guide)

---

## 已确认决策

| 决策项 | 结果 |
|---|---|
| 默认 TTS | `qwen-audio-3.0-tts-plus` |
| 留白保证方式 | 分段合成 + 后端静音拼接 |
| 长留白 | 超过 10 秒统一由后端插入静音 |
| SSML | 仅作为 CosyVoice 优化路径，不进入业务数据 |
| 总时长 | 包含语音、自然停顿和确定性留白 |
| 重试 | 保存并复用 render plan、模型、音色和参数快照 |
| 多供应商 | 渲染计划和静音策略保持供应商无关 |

---

## 范围

### 包含

- AudioTask 的 render plan、停顿档案和非敏感 TTS 快照
- 任务创建时的强校验与快照固化
- Qwen-Audio-TTS 分段 WAV 合成
- 确定性静音生成、FFmpeg 拼接和最终 MP3 编码
- 分段缓存、阶段状态、失败恢复和重试一致性
- 实测时长、预计偏差及可观测性
- CosyVoice SSML 能力判断和可选渲染分支
- 后端单元测试和本地集成测试

### 不包含

- App A/App B Prompt 和 render plan 生成逻辑
- 逐段时间轴编辑器
- 将默认模型切换到 CosyVoice
- 背景音乐混音、响度母带处理或空间音效
- 旧格式脚本兼容
- 未经授权的真实付费 TTS 调用

---

## 1. AudioTask 数据模型与快照

扩展 `audio_tasks`，建议增加：

```text
render_plan              JSON NOT NULL for new tasks
render_plan_version      INTEGER
pause_profile_id         TEXT
tts_snapshot             JSON
estimated_speech_seconds FLOAT
estimated_pause_seconds  FLOAT
estimated_total_seconds  FLOAT
actual_duration_seconds  FLOAT NULL
stage                    TEXT
completed_segments       INTEGER DEFAULT 0
```

`tts_snapshot` 只保存可安全持久化且影响结果一致性的字段：

```json
{
  "provider": "aliyun",
  "model": "qwen-audio-3.0-tts-plus",
  "voice_id": "longanlingxin",
  "rate": 0.86,
  "volume": 1.0,
  "pitch": 1.0,
  "instruction": "温柔、平静、呼吸感自然，语速稍慢，避免播音腔",
  "output_format": "mp3",
  "sample_rate": 48000,
  "base_url": "https://dashscope.aliyuncs.com/api/v1"
}
```

规则：

- 不得把 API Key、Secret、Authorization、临时 URL 保存到快照。
- Worker 使用快照中的 provider/model/voice/参数；凭证在执行时从当前对应供应商配置读取。
- 全局设置后续变化不得改变已有任务的模型、音色、rate、instruction、计划或档案。
- 对应供应商凭证缺失时任务明确失败，不切换供应商或模型。
- 旧 AudioTask 字段保留兼容读取；新任务不得只依赖松散的 `tts_params`。

### 1.1 迁移

- 新字段均采用可安全迁移的 nullable/default 策略，再由新建任务强制写入。
- 历史任务保持原状态、文件路径和下载能力。
- 历史失败任务继续走旧重试路径或明确提示不支持新渲染器，不自动伪造 render plan。
- 迁移必须幂等。

---

## 2. 创建任务协议

调整 `POST /api/audio-tasks`：

```json
{
  "script_id": 12,
  "voice_prompt": "温柔、平静，语速稍慢",
  "render_plan": {},
  "render_plan_digest": "sha256:..."
}
```

创建时必须：

1. 重新读取 Script，确认支持可控留白。
2. 重新校验 `render_plan` 与 `script_plan`、停顿档案一致。
3. 读取当前 TTS 配置并校验 model/voice 组合。
4. 生成规范化 JSON 和 SHA-256 digest，防止预览后客户端篡改。
5. 固化 `tts_snapshot` 和预计时长摘要。
6. 检查 FFmpeg / FFprobe 可用。
7. 创建 `pending/plan_validated` 任务。

如预览后 Script、档案版本或 TTS 配置已变化，应返回冲突错误并要求重新生成预览，不能用过期计划继续生成。

---

## 3. 渲染策略

### 3.1 微停顿与确定性留白分工

- 逗号、顿号和句内节奏由正文标点、rate 和 instruction 控制，不拆成独立请求。
- `pause_strategy=natural` 视为自然微停顿提示，通过标点规范化和 instruction 改善，不额外插入等长静音。
- `pause_strategy=silence` 作为确定性停顿，必须形成语音边界，并由后端静音或受支持的运行时 SSML 精确实现。
- 为保证计划总时长一致，未被物理插入的自然微停顿只计入 T16 的 natural pause budget，不能同时计入 deterministic pause。

策略映射由 T16 的 render plan 协议和服务端校验固定，不能由适配器根据毫秒阈值临时猜测。

### 3.2 分段合成

首期使用 WAV 作为中间格式：

```text
data/audio/work/{task_id}/speech_000.wav
data/audio/work/{task_id}/silence_000.wav
data/audio/work/{task_id}/manifest.json
data/audio/{task_id}.mp3
```

要求：

- 每个需要确定性停顿的 block 结束一个语音段。
- 相邻无确定性停顿的 blocks 可合并后一次合成，减少请求数并保持韵律连续。
- 合并后文本不得超过当前模型限制和服务端安全线。
- 单任务 TTS 请求数设置上限，建议首期不超过 40；超限在创建任务时拒绝并提示调整脚本结构。
- Qwen 请求使用快照中的 model/voice/rate/volume/instruction，输出 WAV、统一采样率。
- `pitch` 只有适配器和当前模型支持时才发送；不支持时创建任务阶段应明确处理，不能静默造成快照与实际请求不一致。

### 3.3 静音生成

- 使用 FFmpeg `anullsrc` 或等价的受控本地方法生成与语音段采样率、声道一致的静音 WAV。
- 静音时长以整数毫秒为输入，输出误差目标不超过 20ms。
- 任何长度的确定性留白均由统一静音模块生成；超过 10 秒不拆成 SSML，直接生成本地静音。
- 静音文件按 duration + 音频规格缓存复用，避免重复创建相同片段。

### 3.4 拼接与编码

- 使用 manifest 或 FFmpeg concat demuxer/filter 按 `speech → silence → speech` 顺序拼接。
- 所有中间文件先验证存在、非空、格式一致。
- 最终统一编码为 MP3；现有下载 URL 和播放器保持兼容。
- 写入 `.part`，FFmpeg 成功且 FFprobe 校验通过后原子替换最终文件。
- 最终实测时长写入 `actual_duration_seconds`。
- 完成后计算与预计总时长的偏差百分比，用于 T18 校准，不将偏差本身判为任务失败，除非超过安全阈值。

---

## 4. Qwen-Audio-TTS 适配器调整

当前适配器支持整体 `rate`、`volume` 和 `instruction`，需要补充：

- `pitch` 参数映射及能力校验。
- 显式中间输出格式、采样率配置。
- 对每段请求返回可验证的 WAV。
- instruction 继续遵守当前模型的 100 字符规则。
- provider 错误标准化，携带任务 ID、segment index、脱敏 request ID。
- 不记录完整段落文本，只记录字符数和摘要 hash。

适配器不得负责：

- 解析 render plan
- 决定停顿时长
- 生成静音
- 拼接文件
- 写数据库状态

---

## 5. CosyVoice SSML 优化路径

首期默认仍为 Qwen，但渲染器设计需保留能力分支：

```text
provider capabilities
  supports_instruction
  supports_ssml
  supports_pitch
  max_ssml_break_ms
  supported_voices
```

当且仅当当前 model + voice 明确支持 SSML 时：

- 最多 10 秒的停顿可转换为运行时 SSML `<break>`。
- 请求设置 `enable_ssml=true`。
- 超过 10 秒的停顿仍使用本地静音。
- SSML 只在适配器请求构建阶段生成，不写入 Script、render plan、任务快照或前端。
- 不支持 SSML 的音色必须回到分段合成 + 静音路径，不能把标签当普通文本提交。

为减少首期变量，T17 可以先完成能力接口和测试桩，再由 T18 真实 A/B 验证是否启用 CosyVoice SSML 路径。

---

## 6. Worker 阶段与可恢复执行

建议阶段：

```text
pending / plan_validated
processing / synthesizing
processing / assembling
processing / encoding
processing / verifying
completed
failed
```

`manifest.json` 至少记录：

```json
{
  "task_id": 21,
  "render_plan_digest": "sha256:...",
  "tts_snapshot_digest": "sha256:...",
  "segments": [
    {
      "index": 0,
      "speech_file": "speech_000.wav",
      "speech_completed": true,
      "pause_after_ms": 1800,
      "pause_strategy": "silence"
    }
  ]
}
```

恢复规则：

- 每个语音段合成成功、文件校验通过后再更新 manifest 和数据库进度。
- Worker 重启或用户重试时，digest 一致且段文件有效则跳过已完成段，避免重复调用 TTS。
- digest 不一致时禁止复用旧中间文件，并报告计划不一致；不得混合两个版本的片段。
- 拼接或编码失败只重做本地阶段，不重新调用已完成的 TTS 段。
- 最终 MP3 已存在且 FFprobe 校验通过时，重试只恢复完成状态。
- 完成任务后可清理 work 目录；失败任务保留有效中间段用于恢复。
- 删除任务时同时清理最终文件、work 目录和 `.part` 文件。

### 6.1 自动重试

现有 Worker 对整任务自动重试会导致已经成功的段被重复合成。改造后：

- 自动重试仍可保留 1 次，但必须通过 manifest 跳过完成段。
- 网络或供应商错误只影响当前 segment。
- 结果不确定的超时不能把无校验文件标记为完成；重试可能再次调用该 segment，并在日志中标注。
- 不允许在重试时重新调用 App B 或重新生成 render plan。
- 不允许因为当前全局模型变化而改变任务路由。

---

## 7. 时长、质量和边界校验

完成后使用 FFprobe 获取：

- 最终时长
- 采样率
- 声道数
- 编码格式

质量规则：

- 最终格式必须为可播放 MP3。
- 静音总时长与 render plan 确定性停顿总和误差目标不超过 `±100ms`。
- 最终音频不得在拼接边界出现损坏、明显爆音或重复帧。
- 首期不做响度标准化，但各段必须使用同一 voice、rate、volume、pitch 和采样率。
- 预计总时长与实测总时长偏差写入任务响应；目标为 `±10%`。
- 空音频、零时长、异常超短段或 FFprobe 失败均视为任务失败。

---

## 8. API 响应与下载

AudioTask 响应增加：

```json
{
  "pause_profile_id": "standard_v1",
  "stage": "synthesizing",
  "completed_segments": 4,
  "total_segments": 12,
  "estimated_total_seconds": 592,
  "actual_duration_seconds": null,
  "provider": "aliyun",
  "model": "qwen-audio-3.0-tts-plus",
  "voice_id": "longanlingxin"
}
```

安全要求：

- 不返回 API Key、完整 base URL 中的敏感查询参数或 Authorization。
- 列表接口无需返回完整 render plan；详情接口可返回脱敏后的计划摘要，供后续诊断。
- 下载接口继续只允许访问任务记录对应的受控最终文件。

---

## 9. 自动测试要求

自动测试使用 FakeTTS / MockTransport 和本地短音频，不访问真实外部接口。至少覆盖：

1. 创建任务固化 render plan 和非敏感 TTS 快照。
2. 快照不包含 API Key/Secret/Authorization。
3. 全局设置变化不影响已有任务的模型、音色和参数。
4. render plan 或 snapshot digest 不匹配时拒绝复用缓存。
5. 相邻微停顿 blocks 正确合并，确定性停顿正确分段。
6. 超过单任务 segment/request 上限时创建失败。
7. 中间 WAV 的 model、voice、rate、volume、pitch、instruction 映射正确。
8. 静音时长、采样率和声道正确。
9. 5 秒、10 秒、20 秒、60 秒留白均可正确渲染。
10. 拼接顺序和最终 MP3 格式正确。
11. FFprobe 实测时长写入任务。
12. segment 失败后只重试未完成段。
13. 拼接/编码失败不重新调用 TTS。
14. Worker 重启可从 manifest 恢复。
15. 最终文件已存在时重试只恢复状态。
16. 删除任务清理最终文件、work 目录和临时文件。
17. Qwen 路径不生成或发送 SSML。
18. CosyVoice 仅在 model/voice 能力允许时启用 SSML。
19. 超过 10 秒的 CosyVoice 留白仍走本地静音。
20. 日志不包含完整引导词、API Key 或 Authorization。

完成后执行：

```text
后端全量 pytest
Ruff 检查
前端类型检查/构建（确认 API 类型未破坏）
FFmpeg/FFprobe 本地短样本集成测试
```

---

## 10. 验收标准

- [ ] 新 AudioTask 固化 render plan、档案和非敏感 TTS 快照
- [ ] Worker 不再把整篇引导词作为唯一一次 TTS 请求
- [ ] 默认 Qwen 路径可按计划插入确定性静音
- [ ] 超过 10 秒的留白由后端生成，不依赖模型自由理解
- [ ] 微停顿与确定性留白不会重复计时
- [ ] 中间格式统一且最终输出为可播放 MP3
- [ ] 分段失败后可复用已完成段，不重复调用全部 TTS
- [ ] 拼接或编码失败不会触发新的模型调用
- [ ] 重试不重新生成 render plan，不受全局设置变化影响
- [ ] 实测时长、预计偏差、阶段和进度可查询
- [ ] Qwen 不接收 SSML，CosyVoice SSML 仅按能力启用
- [ ] API 和日志不泄露凭证或完整引导词
- [ ] 自动测试不调用真实付费接口

---

## 预计涉及文件

### 新增

```text
backend/app/services/audio_renderer.py
backend/app/services/audio_render_files.py
backend/app/services/audio_postprocessor.py
backend/app/services/tts_capabilities.py
backend/tests/test_audio_renderer.py
backend/tests/test_audio_postprocessor.py
backend/tests/test_tts_capabilities.py
docs/task/17-meditation-audio-render-pipeline.md
```

### 修改

```text
backend/app/db_migrations.py
backend/app/models/audio_task.py
backend/app/schemas/audio_task.py
backend/app/routers/audio_tasks.py
backend/app/routers/settings.py
backend/app/services/audio_worker.py
backend/app/services/tts_base.py
backend/app/services/tts_aliyun.py
backend/app/services/tts_factory.py
backend/tests/test_audio_worker.py
backend/tests/test_audio_tasks.py
backend/tests/test_tts.py
frontend/src/types/index.ts
docs/ops/t5-tts-operations.md
docs/tech/tech-spec.md
```

---

## 实施顺序

1. 增加 AudioTask 快照、阶段和时长字段及幂等迁移。
2. 建立 TTS 能力描述和统一的分段合成输入。
3. 实现中间 WAV、受控目录和 manifest。
4. 实现静音生成、拼接、编码和 FFprobe 验证。
5. 将 Audio Worker 改造成可恢复的阶段式流水线。
6. 完成 Qwen 默认路径测试。
7. 增加 CosyVoice SSML 能力分支及 Mock 测试。
8. 完成失败恢复、删除和安全测试。
9. 更新运维与技术文档。

---

## 风险备注

- 分段过细会增加模型调用次数、成本和段间音色波动，因此必须合并微停顿段并限制请求数。
- 单纯拼接 MP3 字节不可靠，必须使用统一中间格式和 FFmpeg 重新编码。
- TTS 超时可能处于结果不确定状态；manifest 只能记录经过文件校验的完成段。
- 不同模型/音色的 SSML 与 instruction 支持范围不同，必须通过能力表判断，不能只按模型名前缀推断。
- Windows 文件占用可能影响原子替换和清理，测试需要覆盖句柄关闭与失败恢复。
