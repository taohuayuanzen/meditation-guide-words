# T15：MiniMax 音乐供应商接入与双供应商切换

> 任务状态：✅ 已完成（2026-08-13）
>
> 自动验收：后端 114 项测试、Ruff、前端 lint、生产构建及中英文 JSON 检查通过；自动测试未调用真实音乐接口。
>
> 真实联调：在最多 3 次授权额度内共使用 2 次调用。首次因 API Key 鉴权失败停止且未自动重试；修正 Key 后复用任务 `#2` 成功生成并保留源 MP3 与最终 MP3。源文件实测 135.210 秒、44.1 kHz、双声道、256 kbps；最终文件实测 300.000 秒、44.1 kHz、双声道、192 kbps。用户人工试听验收通过，确认无可辨识人声、吟唱、歌词或念白。

## 任务目标

在保留阿里云百炼 `fun-music-v1` 全部现有能力的前提下，接入 MiniMax `music-3.0`，将当前单一供应商音乐链路升级为可安全切换的双供应商架构，并默认使用 MiniMax 生成纯音乐。

本任务完成后的主链路：

```text
选择 MiniMax → 创建任务并固化供应商 → music-3.0 生成原始 MP3
→ 下载并长期保留 → FFmpeg 时长适配 → 最终 MP3 → 试听 / 下载 / 产物管理
```

同时满足：

- 阿里云配置、适配器和历史任务完整保留。
- 切换供应商不会覆盖另一家的凭证。
- 历史阿里云任务不会在重试时误用 MiniMax。
- MiniMax 模型调用失败后不自动重新生成，避免同步调用结果不确定时重复计费。

---

## 前置依赖

- T12～T14 已完成，现有阿里云音乐生成、FFmpeg 后处理、纯音乐工作区和产物管理可用。
- 系统已安装 FFmpeg / FFprobe。
- 真实联调前已取得可调用 `music-3.0` 的 MiniMax API Key，并获得单独的真实调用授权。

参考：

- [MiniMax 音乐生成 API](https://platform.minimaxi.com/docs/api-reference/music-generation)
- [MiniMax 音乐生成指南](https://platform.minimaxi.com/docs/guides/music-generation)
- [MiniMax 按量计费](https://platform.minimaxi.com/docs/guides/pricing-paygo)

> 自动测试必须使用 HTTP Mock，不得调用 MiniMax 或阿里云真实接口。真实调用次数和产物保留规则另行确认。

---

## 已确认决策

| 决策项 | 结果 |
|---|---|
| 默认供应商 | MiniMax |
| MiniMax 模型 | 正式版 `music-3.0`，不使用 `music-3.0-free` |
| MiniMax 调用方式 | 非流式同步调用 |
| MiniMax 响应交付 | `output_format=url`，不使用 hex |
| MiniMax 原始格式 | MP3，不假定支持 WAV |
| MiniMax 内容类型 | 服务端固定 `is_instrumental=true`，不传歌词 |
| MiniMax 歌词优化 | 固定 `lyrics_optimizer=false` |
| MiniMax AIGC 尾部水印 | 固定关闭 |
| MiniMax 费用 | 暂不估算，展示“以 MiniMax 账单为准” |
| 配置结构 | 双供应商嵌套配置，分别保留两套凭证 |
| 任务归属 | 创建时固化供应商和模型 |
| 历史任务 | `fun-music-v1` 任务归属阿里云，不允许切换供应商重试 |
| MiniMax 生成重试 | 失败后不自动再次调用模型；只允许用户明确手动重试 |
| 下载和 FFmpeg 重试 | 可自动重试，不触发新的模型调用 |
| 前端测试 | 不新增前端自动测试栈，执行 lint、构建和人工验收 |

---

## 范围

### 包含

- 双供应商音乐配置及旧配置迁移
- MiniMax `music-3.0` 适配器
- 音乐供应商统一接口和分发器
- 音乐任务供应商、模型和源格式快照
- 历史阿里云任务迁移与兼容
- MiniMax 原始 MP3 下载、恢复和长期保留
- WAV / MP3 通用源文件生命周期
- MiniMax 防重复计费重试规则
- 音乐设置页供应商切换和独立凭证表单
- 工作区、任务卡、下载弹窗和产物页的供应商/格式/费用适配
- 后端单元测试、前端构建检查和人工验收清单更新
- README 和运维说明更新

### 不包含

- 删除阿里云 `fun-music-v1` 能力
- MiniMax `music-3.0-free`、`music-2.6` 或翻唱模型
- MiniMax 流式或 hex 音频传输
- 歌词生成、人声歌曲或参考音频翻唱
- 多供应商自动故障转移
- 模型失败后自动切换另一供应商
- 跨供应商重试已有任务
- 多段模型生成拼接
- 凭证加密体系改造
- 前端自动测试框架

---

## 1. 双供应商配置

将当前扁平 `music_config` 升级为：

```json
{
  "provider": "minimax",
  "worker_concurrency": 1,
  "output_format": "mp3",
  "enable_aigc_watermark": false,
  "aliyun": {
    "api_key": "",
    "workspace_id": "",
    "base_url": "",
    "model": "fun-music-v1",
    "source_format": "wav"
  },
  "minimax": {
    "api_key": "",
    "base_url": "https://api.minimaxi.com/v1",
    "model": "music-3.0",
    "source_format": "mp3"
  }
}
```

后端建议拆分为：

```text
MusicConfig
AliyunMusicConfig
MiniMaxMusicConfig
```

约束：

- `provider` 仅允许 `minimax` 或 `aliyun`，默认 `minimax`。
- 两个供应商配置始终同时保存在 `music_config` 中。
- 切换 `provider` 只改变新任务使用的供应商，不清空、不复制、不覆盖凭证。
- MiniMax `base_url` 默认 `https://api.minimaxi.com/v1`，只允许有效 HTTP(S) 地址且不得包含凭证、查询参数或片段。
- MiniMax 模型固定 `music-3.0`，源格式固定 MP3。
- 阿里云模型、Workspace endpoint 推导和 WAV 源格式保持现状。
- 设置 API 和日志不得泄露任一供应商的 API Key。
- 本任务沿用现有本地配置存储机制，不扩大为系统级密钥管理改造。

### 1.1 旧配置迁移

现有数据库中的扁平阿里云配置：

```json
{
  "provider": "aliyun",
  "api_key": "...",
  "workspace_id": "...",
  "base_url": "...",
  "model": "fun-music-v1",
  "source_format": "wav",
  "output_format": "mp3",
  "enable_aigc_watermark": false,
  "worker_concurrency": 1
}
```

必须幂等迁移为新结构：

- 原 `api_key`、`workspace_id`、`base_url` 和模型迁入 `aliyun`。
- 补齐默认 `minimax` 配置，但 API Key 为空。
- 活跃供应商改为 `minimax`。
- 保留通用的并发、最终格式和水印设置。
- 已是新结构时跳过，不覆盖用户数据。
- 连续启动或连续执行迁移不会再次改写配置。

由于默认供应商改为 MiniMax，但新 Key 尚未配置，迁移后允许保存和查看已有任务；创建新任务前必须明确提示缺少 MiniMax API Key。

---

## 2. 任务数据迁移与供应商快照

扩展 `music_tasks`：

```text
provider       TEXT
source_format  TEXT
```

创建新任务时固化：

- `provider`
- `model`
- `source_format`
- `output_format`

迁移规则：

- 所有现有 `model=fun-music-v1` 的任务设置 `provider=aliyun`、`source_format=wav`。
- 新 MiniMax 任务设置 `provider=minimax`、`model=music-3.0`、`source_format=mp3`。
- 迁移必须幂等并保留任务状态、错误、远端 URL、文件路径和时间字段。
- 旧任务即使失败且没有远端结果，重试时也只能使用阿里云配置。
- 当前全局供应商变化不得改变已有任务的供应商、模型或源格式。

任务 API 响应增加 `provider` 和 `source_format`，但继续隐藏完整签名 URL 和供应商凭证。

---

## 3. 供应商统一接口

新增通用服务，例如：

```text
backend/app/services/music_provider.py
backend/app/services/music_minimax.py
```

保留：

```text
backend/app/services/music_aliyun.py
```

供应商分发关系：

```text
Music Worker
    ↓
music_provider.generate_music(task.provider, task.model, config, prompt)
    ├── minimax → music_minimax.generate_music
    └── aliyun  → music_aliyun.generate_music
```

统一生成结果至少包含：

```text
request_id
audio_id              可空
audio_url
expires_at            可空
duration_seconds
sample_rate           可空
channels              可空
source_format
estimated_cost        可空
```

供应商适配器只负责：

- 配置与请求构建
- HTTP 调用
- 响应解析
- 供应商错误标准化
- 返回统一结果

供应商适配器不得直接写数据库、下载文件或执行 FFmpeg。

---

## 4. MiniMax `music-3.0` 适配器

服务端点：

```text
POST {base_url}/music_generation
```

默认完整地址：

```text
https://api.minimaxi.com/v1/music_generation
```

固定请求：

```json
{
  "model": "music-3.0",
  "prompt": "最终 Prompt",
  "stream": false,
  "output_format": "url",
  "audio_setting": {
    "sample_rate": 44100,
    "bitrate": 256000,
    "format": "mp3"
  },
  "aigc_watermark": false,
  "lyrics_optimizer": false,
  "is_instrumental": true
}
```

要求：

- 使用 `Authorization: Bearer {api_key}`。
- `Content-Type` 固定为 `application/json`。
- 不发送 `lyrics`。
- 不允许前端覆盖模型、纯音乐、流式、返回格式、水印和歌词优化参数。
- Prompt 直接使用工作区提交的 `effective_prompt`，保留现有首句“创作适合纯音乐。”。
- Prompt 长度按 MiniMax 纯音乐接口约束限制为 1～2000 个字符，前后端都应校验。
- 生成超时独立配置，不能复用普通下载超时。

### 4.1 响应解析

成功条件至少包括：

- HTTP 成功。
- `base_resp.status_code == 0`。
- `data.status` 表示生成完成。
- `data.audio` 为有效 HTTPS URL。

字段映射：

- `trace_id` → `request_id`
- `data.audio` → `audio_url`
- MiniMax 无独立 audio ID 时 → `audio_id=null`
- `extra_info.music_duration` 毫秒转换为秒
- `extra_info.music_sample_rate` → `sample_rate`
- `extra_info.music_channel` → `channels`
- `source_format=mp3`
- URL 过期时间按官方 24 小时有效期记录
- `estimated_cost=null`

若返回结构与预期不符，标记 `MUSIC_RESPONSE_INVALID`，不得把响应中的凭证或完整签名 URL写入日志或前端错误。

### 4.2 错误标准化

至少覆盖：

- 配置缺失
- API Key 无效
- 无模型调用权限或账户余额问题
- 请求参数错误
- Prompt 内容审核拒绝
- 429 限流
- 请求超时
- 网络错误
- MiniMax 业务状态失败
- HTTP 5xx
- 响应结构异常

要求：

- 保留经过脱敏和截断的供应商错误码/说明，便于排障。
- 不记录 Authorization、API Key 或完整音频 URL。
- MiniMax 生成阶段的所有错误均不得触发 Worker 自动再次调用模型。

---

## 5. Worker 与重试规则

保留现有阶段：

```text
pending
  ↓
processing / generating
  ↓
processing / downloading
  ↓
processing / source_ready
  ↓
processing / processing
  ↓
completed
```

### 5.1 按任务快照选择供应商

Worker 必须使用任务中的 `provider` 和 `model`：

- `minimax/music-3.0`：读取 `music_config.minimax`。
- `aliyun/fun-music-v1`：读取 `music_config.aliyun`。
- 不支持的组合明确失败，不回退到当前全局供应商。
- 对应供应商凭证缺失时明确失败，不尝试另一供应商。

### 5.2 MiniMax 生成重试

MiniMax 模型调用失败时：

- 第一次失败后直接标记 `failed`。
- Worker 不增加自动模型调用次数。
- 429、网络错误、超时和 5xx 也不自动重新生成。
- 错误提示说明“未自动重试，以避免重复计费”。
- 用户可以通过任务卡明确手动重试。
- 对同步请求超时或连接中断等结果不确定的情况，手动重试前必须弹出可能重复计费的确认提示。
- 后端对需要重新生成的重试要求显式确认字段，例如 `confirm_regenerate=true`，避免绕过前端误触发。

阿里云已有生成重试策略保持现状，不在本任务中删除；但同样必须按任务的阿里云归属执行。

### 5.3 下载和后处理重试

获得 MiniMax URL 后：

- 先持久化 `request_id`、URL、过期时间、格式和媒体信息并 commit。
- 再下载到 `.part` 临时文件。
- 下载失败复用同一 URL，按现有策略自动重试，不重新调用模型。
- 本地原始 MP3 存在时跳过生成和下载，直接进入后处理。
- 原始 MP3 下载完成后即使 FFmpeg 失败也必须保留。
- FFmpeg 失败只重新处理本地源文件。
- URL 已过期且本地源文件不存在时明确失败，不自动生成新音乐。

---

## 6. 多格式源文件生命周期

源文件路径按任务格式生成：

```text
阿里云：data/music/source/{task_id}.wav
MiniMax：data/music/source/{task_id}.mp3
最终：  data/music/final/{task_id}_{target_minutes}min.mp3
```

修改统一文件服务：

- `canonical_source_path()` 根据 `task.source_format` 选择扩展名。
- 查找、恢复、下载、删除和 `.part` 清理均支持 WAV / MP3。
- 禁止客户端传入任意服务器路径。
- 历史 WAV 文件查找行为保持兼容。
- 原始文件不因生成最终 MP3 而覆盖或删除。
- 重命名仍只作用于最终 MP3。

下载列表示例：

```json
{
  "items": [
    {
      "kind": "source",
      "format": "mp3",
      "label": "原始 MP3",
      "download_url": "/api/music-tasks/2/download/source"
    },
    {
      "kind": "final",
      "format": "mp3",
      "label": "10 分钟 MP3",
      "download_url": "/api/music-tasks/2/download/final"
    }
  ]
}
```

下载响应的 MIME type 必须根据实际文件格式返回，不能再用 `kind=source` 推断一定是 WAV。

删除任务时清理：

- 对应源 WAV 或 MP3
- 源文件 `.part`
- 最终 MP3
- FFmpeg 循环和编码临时文件
- 数据库任务记录

---

## 7. FFmpeg 后处理适配

现有时长处理逻辑继续负责：

- FFprobe 探测真实时长、采样率和声道
- 循环和交叉淡化
- 裁剪
- 首尾淡化
- 输出 `libmp3lame` 192 kbps 最终 MP3
- 最终时长误差不超过 1 秒

调整要求：

- 输入接受受控目录内的 WAV 或 MP3，不根据扩展名假定编码。
- MiniMax 返回的 `music_duration` 只作为生成结果元数据；原始文件落盘后仍以 FFprobe 实测时长更新 `source_duration_seconds`。
- MiniMax 的 `estimated_cost` 保持 `null`，不得根据源时长套用阿里云单价。
- 最终文件格式和 T13 的时长处理规则保持不变。

---

## 8. 音乐任务 API

### `POST /api/music-tasks`

创建时：

- 读取当前 `music_config.provider`。
- 只校验当前供应商所需凭证。
- MiniMax 只要求 API Key；不要求 Workspace ID。
- 阿里云继续要求 API Key 和 Workspace ID。
- 将供应商、模型和源格式写入任务。
- FFmpeg / FFprobe 不可用时仍按现有规则返回 503。

### `POST /api/music-tasks/{id}/retry`

按任务现有产物恢复：

- 有最终 MP3：只校验并恢复完成状态。
- 有源 WAV / MP3：只进入 FFmpeg 后处理。
- 有有效远端 URL：只重新下载。
- 有远端标识但缺少 URL：禁止重新生成，避免重复计费。
- 明确需要重新调用 MiniMax 时，要求用户确认重新生成。
- 任何重试都不得改变任务供应商和模型。

### 列表、详情和下载

- 返回 `provider`、`model`、`source_format`。
- 不返回远端签名 URL。
- 下载列表按真实文件格式生成。
- 费用为空属于有效状态，不得序列化为 `0`。

---

## 9. 前端音乐设置

音乐设置页增加供应商选择：

- MiniMax（默认）
- 阿里云百炼

### 9.1 MiniMax 面板

字段：

- API Key
- 模型：只读 `music-3.0`
- Base URL：高级设置，默认 `https://api.minimaxi.com/v1`
- 原始格式：只读 MP3
- 最终格式：只读 MP3
- 纯音乐：只读开启
- AIGC 尾部水印：只读关闭

配置检查：

- 检查 API Key 非空。
- 检查 Base URL 合法。
- 检查 FFmpeg / FFprobe capabilities。
- 不调用真实 `music-3.0`，不产生费用。
- 成功提示“配置和本地处理能力可用，模型权限将在首次生成时验证”。

### 9.2 阿里云面板

保留现有字段和行为：

- Workspace ID
- API Key
- Base URL
- `fun-music-v1`
- 原始 WAV / 最终 MP3
- 复制当前阿里云 TTS API Key

切换供应商后两套表单值均保留；保存设置时同时提交两套配置。

---

## 10. 工作区、任务卡和产物页

工作区生成可用性按当前供应商判断：

- MiniMax：API Key + FFmpeg + FFprobe。
- 阿里云：API Key + Workspace ID + FFmpeg + FFprobe。

任务和产物展示：

- 显示供应商和模型。
- MiniMax 完成任务显示源音乐真实时长。
- MiniMax 费用显示“以 MiniMax 账单为准”，不显示 `¥0.00`。
- 阿里云继续显示现有估算费用和“以阿里云账单为准”。
- 下载弹窗显示真实存在的“原始 MP3”或“原始 WAV”。
- 删除提示使用“原始音乐”，不再写死“原始 WAV”。

MiniMax 生成失败后的手动重试提示：

```text
本次生成结果可能不确定。重新生成会再次调用 MiniMax，并可能重复计费。是否继续？
```

下载或 FFmpeg 失败且已有远端 URL / 本地源文件时，重试按钮应说明只恢复下载或处理，不会再次调用模型。

---

## 11. 费用规则

MiniMax 当前音乐 API 文档推荐 `music-3.0`，但公开价格页面的音乐型号信息与接口模型列表未完全同步，因此本任务不硬编码 MiniMax 单价。

规则：

- MiniMax `estimated_cost=null`。
- 前端显示“费用以 MiniMax 账单为准”。
- 不将空费用转换为 `0`。
- 不使用目标时长、源时长或旧版 MiniMax 模型价格推算。
- 阿里云 `fun-music-v1` 继续沿用现有按源音乐秒数估算逻辑。
- 后续官方价格明确时，再单独增加集中式费率配置和测试。

---

## 12. 安全与可观测性

- API Key 只用于服务端 Authorization 请求头。
- 前后端日志不得输出任一供应商的 API Key。
- 不记录 MiniMax 或阿里云完整签名 URL。
- 错误详情必须移除 Bearer token、疑似 API Key 和 URL 查询参数。
- 日志包含任务 ID、供应商、模型、阶段、Prompt 长度和脱敏后的请求 ID。
- 不记录完整 Prompt，避免用户内容进入运行日志。
- Base URL 必须通过结构化 URL 校验，不能包含用户名、密码、查询参数或片段。
- 下载继续限制在受控音乐目录，防止路径穿越。

---

## 13. 数据迁移与兼容验证

迁移至少覆盖：

1. 旧扁平阿里云配置迁入嵌套结构。
2. 已有新结构时保持不变。
3. 连续执行迁移保持幂等。
4. 原阿里云 API Key、Workspace ID 和自定义 Base URL 不丢失。
5. 默认供应商正确切换为 MiniMax。
6. 所有旧 `fun-music-v1` 任务标记为阿里云和 WAV。
7. 已有失败、处理中和完成任务的状态与文件路径不变。
8. 历史 WAV 仍可试听、下载、重命名最终文件和删除。
9. 旧任务重试只使用阿里云配置。
10. 新 MiniMax 任务只使用 MiniMax 配置。

---

## 14. 自动测试要求

建议新增：

```text
backend/tests/test_music_minimax.py
backend/tests/test_music_provider.py
```

并扩展现有音乐配置、迁移、Worker、任务和文件测试。

至少覆盖：

1. MiniMax 请求使用 `music-3.0`。
2. 固定非流式、URL 返回、MP3、44.1 kHz、256 kbps。
3. 固定纯音乐、关闭歌词优化和水印，不发送 lyrics。
4. Prompt 长度 1～2000 校验。
5. 成功解析 URL、trace ID、毫秒时长、采样率和声道。
6. MiniMax 业务错误、HTTP 错误、限流、审核、超时和异常响应映射。
7. MiniMax 任意生成失败均不触发自动模型重试。
8. 用户明确确认后才允许重新生成。
9. 获得 URL 后先持久化再下载。
10. 下载失败只复用 URL，不调用模型。
11. FFmpeg 失败保留原始 MP3，重试不调用模型。
12. URL 过期且无本地源文件时不自动生成。
13. 任务按自身供应商路由，不使用当前全局供应商。
14. 旧阿里云任务迁移和重试行为不变。
15. 双供应商配置切换不丢失凭证。
16. MP3 源文件路径、下载 MIME、列表标签和删除正确。
17. MiniMax 费用为空且不会显示为零元。
18. API 和日志不泄露 API Key 或完整签名 URL。
19. 阿里云原有适配器和测试继续通过。
20. 自动测试不访问真实外部接口。

前端不新增自动测试框架。完成后执行：

```text
后端全量测试
Ruff 检查
前端 lint
前端生产构建
中英文 JSON / 文案检查
```

---

## 15. 人工验收

更新 `docs/test/music-workspace-manual-checklist.md`，至少验证：

1. 音乐设置默认选择 MiniMax。
2. MiniMax 和阿里云表单切换后各自凭证不丢失。
3. MiniMax 不显示 Workspace ID 或复制阿里云 TTS Key 按钮。
4. 阿里云原有设置项和复制 Key 功能仍可用。
5. 配置检查不产生模型调用。
6. MiniMax 缺少 Key 时禁用新建任务，但已有任务仍可查看和下载。
7. 新任务固化 MiniMax / `music-3.0` / MP3。
8. 旧任务显示阿里云 / `fun-music-v1` / WAV。
9. 切换全局供应商不改变已有任务。
10. MiniMax 原始 MP3 和目标时长 MP3 均可下载。
11. 下载 MIME、文件扩展名、大小和时长正确。
12. MiniMax 任务费用显示“以 MiniMax 账单为准”。
13. 阿里云任务继续显示原有估算费用。
14. MiniMax 生成失败后不自动重试。
15. 手动重新生成前显示重复计费确认。
16. 下载或处理重试不显示模型计费确认，且不调用模型。
17. 产物播放、重命名和删除支持 MiniMax MP3 源文件生命周期。
18. 删除提示不再把所有源文件写死为 WAV。
19. 中英文文案完整。

### 15.1 真实联调

真实计费联调不随自动测试执行。开始前另行确认：

- MiniMax API Key 已配置并可调用正式版 `music-3.0`。
- 本次允许的最大模型调用次数。
- 是否保留真实源 MP3 和最终 MP3。

联调顺序：

1. 使用默认纯音乐预设创建一条目标 5 分钟的新任务。
2. 确认请求为非流式、URL、MP3、`is_instrumental=true`。
3. 首次模型调用失败即停止，不自动再次调用。
4. 成功后确认 URL 先持久化，再下载原始 MP3。
5. 确认原始 MP3 长期保留。
6. 确认最终 MP3 时长误差不超过 1 秒。
7. 验证播放器、两种 MP3 下载、供应商、模型、AI 标识和费用文案。
8. 由用户人工试听，确认没有可辨识人声、吟唱、歌词或念白。
9. 试听不通过时不自动再次生成。

---

## 验收标准

- [x] 音乐配置可同时保存 MiniMax 和阿里云两套凭证
- [x] 默认音乐供应商为 MiniMax
- [x] MiniMax 固定使用正式版 `music-3.0`
- [x] MiniMax 固定非流式、URL 返回和原始 MP3
- [x] MiniMax 服务端固定纯音乐、关闭歌词优化和尾部水印
- [x] 阿里云 `fun-music-v1` 适配器和配置完整保留
- [x] 旧扁平阿里云配置可幂等迁移且不丢失数据
- [x] 旧 `fun-music-v1` 任务归属阿里云和 WAV
- [x] 新任务固化供应商、模型和源格式
- [x] 切换全局供应商不会改变已有任务
- [x] 旧任务不允许跨供应商重试
- [x] MiniMax 生成失败后不会自动再次调用模型
- [x] MiniMax 手动重新生成具有明确计费确认
- [x] 下载和 FFmpeg 处理可自动重试且不触发模型调用
- [x] 原始 WAV / MP3 均可恢复、下载和删除
- [x] MiniMax 原始 MP3 可处理为目标时长 MP3
- [x] 最终 MP3 时长误差不超过 1 秒
- [x] MiniMax 费用不做估算，显示“以 MiniMax 账单为准”
- [x] 阿里云费用估算保持现状
- [x] API 和日志不泄露凭证或完整签名 URL
- [x] 阿里云原有自动测试继续通过
- [x] 新增测试不调用真实付费接口
- [x] 前端 lint 和生产构建通过，不新增前端自动测试框架
- [x] `docs/test/`、README 和相关运维说明已更新

---

## 预计涉及文件

### 新增

```text
backend/app/services/music_provider.py
backend/app/services/music_minimax.py
backend/tests/test_music_provider.py
backend/tests/test_music_minimax.py
docs/task/15-minimax-music-provider.md
```

### 修改

```text
backend/app/db_migrations.py
backend/app/models/music_task.py
backend/app/schemas/setting.py
backend/app/schemas/music_task.py
backend/app/routers/settings.py
backend/app/routers/music_tasks.py
backend/app/services/music_aliyun.py
backend/app/services/music_worker.py
backend/app/services/music_files.py
backend/app/services/music_postprocessor.py
backend/tests/test_music_migration.py
backend/tests/test_music_worker.py
backend/tests/test_music_tasks.py
backend/tests/test_music_files.py
backend/tests/test_settings.py
frontend/src/types/index.ts
frontend/src/utils/settingsValidation.ts
frontend/src/services/settingsService.ts
frontend/src/components/settings/MusicSettings.tsx
frontend/src/components/workspace/MusicWorkspace.tsx
frontend/src/components/workspace/MusicTaskItem.tsx
frontend/src/components/workspace/ArtifactWorkspace.tsx
frontend/src/i18n/locales/zh.json
frontend/src/i18n/locales/en.json
docs/test/music-workspace-manual-checklist.md
README.md
```

---

## 实施顺序

1. 增加配置和任务字段迁移，并完成迁移测试。
2. 建立供应商统一接口，保持阿里云测试通过。
3. 实现 MiniMax 适配器和 HTTP Mock 测试。
4. 按任务快照改造 Worker 和防重复计费逻辑。
5. 将源文件生命周期泛化为 WAV / MP3。
6. 扩展任务 API、下载和重试确认。
7. 改造前端双供应商设置及配置校验。
8. 更新工作区、任务卡、下载弹窗、产物页和费用文案。
9. 更新 README、运维说明和人工验收清单。
10. 执行全部非计费检查。
11. 获得单独授权后执行真实 MiniMax 联调并保留约定产物。
