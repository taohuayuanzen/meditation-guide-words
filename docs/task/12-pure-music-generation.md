# T12：Fun-Music 后端基础与源音乐生成

## 任务目标

接入阿里云百炼 `fun-music-v1`，建立纯音乐模块的配置、数据模型、任务 API 和后台 Worker，实现从自然语言 Prompt 到原始 WAV 文件落盘的可靠链路。

本任务重点解决两类高风险问题：

- 在不影响现有设置、引导词和引导音频数据的前提下扩展数据库。
- 模型生成成功后即使下载失败，也不得因自动重试而重复调用模型、产生重复费用。

本任务结束时可通过后端 API 创建任务并获得本地原始 WAV；目标时长 MP3、前端工作区和产物页集成分别由 T13、T14 完成。

---

## 前置条件

- 现有 FastAPI、SQLite 和 Audio Worker 可正常运行。
- 真实联调前，阿里云百炼华北 2（北京）业务空间已开通 `fun-music-v1` 邀测权限。
- 已取得北京地域 Workspace ID 和 API Key。

> 自动测试必须使用 HTTP Mock，不得调用真实计费接口。真实调用需另行明确授权。

---

## 范围

### 包含

- 独立 `music_config`
- `settings` 表幂等迁移
- `music_tasks` 表
- Fun-Music 非流式适配层
- Music Worker 基础任务循环
- 原始 WAV 下载与长期保存
- 分阶段状态持久化
- 模型调用与下载的差异化重试
- 音乐任务创建、列表、详情和重试 API
- 后端单元测试

### 不包含

- FFmpeg / FFprobe
- 循环、裁剪、交叉淡化
- 目标时长 MP3
- WAV / MP3 下载选择
- 删除文件生命周期
- Music Worker 启停脚本集成
- 前端设置页和纯音乐工作区
- 产物页集成
- 真实计费联调

---

## 已确认的基础决策

| 决策项 | 结果 |
|---|---|
| 供应商 | 阿里云百炼 |
| 模型 | `fun-music-v1` |
| 地域 | 华北 2（北京） |
| 调用方式 | 非流式，由独立后台 Worker 执行 |
| 内容类型 | 仅纯音乐，服务端强制 `is_instrumental=true` |
| 源格式 | WAV |
| AIGC 尾部水印 | 默认关闭 |
| Prompt | 直接接收最终 Prompt，不调用 Dify 或其他 LLM |
| API Key | 独立存入 `music_config`，可在 T14 前端中从 TTS 配置复制 |
| 模型重试 | 自动重试最多 1 次 |
| 下载重试 | 获得 URL 后额外重试最多 2 次，不重新生成 |
| AI 标识 | 数据库/API 标注，不写入文件名或音频元数据 |

---

## 1. 数据库扩展

### 1.1 `settings.music_config`

修改：

- `backend/app/models/setting.py`
- `backend/app/schemas/setting.py`
- `backend/app/routers/settings.py`
- 前端共享类型可留到 T14 处理

默认结构：

```json
{
  "provider": "aliyun",
  "api_key": "",
  "workspace_id": "",
  "base_url": "",
  "model": "fun-music-v1",
  "source_format": "wav",
  "output_format": "mp3",
  "enable_aigc_watermark": false,
  "worker_concurrency": 1
}
```

约束：

- 第一版 `provider` 固定为 `aliyun`。
- 第一版 `model` 固定为 `fun-music-v1`。
- `source_format` 固定为 `wav`。
- `output_format` 在本任务中仅作为后续 T13 预留字段。
- `base_url` 为空时根据 Workspace ID 生成：

  ```text
  https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1
  ```

- 设置 API 不得在日志中输出 API Key。

### 1.2 幂等 SQLite 迁移

新增 `backend/app/db_migrations.py`。

当前 `Base.metadata.create_all()` 不会为已有表增加列，因此启动顺序调整为：

1. 初始化数据库目录。
2. 检查并迁移已有表。
3. 导入 ORM 模型并执行 `create_all()`。

迁移要求：

- 使用 `PRAGMA table_info(settings)` 检查 `music_config`。
- 字段不存在时执行 `ALTER TABLE`。
- 已存在时跳过。
- 已有 `settings.id=1` 的新字段初始化为空对象或默认配置。
- 连续执行两次不报错、不覆盖用户值。
- 迁移前后的 `settings`、`scripts`、`audio_tasks` 数据保持不变。

### 1.3 `MusicTask` 模型

新增 `backend/app/models/music_task.py`：

```text
id                       INTEGER PK
prompt                   TEXT
effective_prompt         TEXT
preset_params            JSON
model                    TEXT
status                   TEXT
stage                    TEXT
retry_count              INTEGER
download_retry_count     INTEGER
request_id               TEXT NULL
remote_audio_id          TEXT NULL
remote_audio_url         TEXT NULL
remote_url_expires_at    DATETIME NULL
source_duration_seconds  INTEGER NULL
target_duration_seconds  INTEGER
final_duration_seconds   INTEGER NULL
sample_rate              INTEGER NULL
channels                 INTEGER NULL
source_file_path         TEXT NULL
file_path                TEXT NULL
output_format            TEXT
is_ai_generated          BOOLEAN
watermark_enabled        BOOLEAN
estimated_cost           REAL NULL
error_code               TEXT NULL
error_msg                TEXT NULL
created_at               DATETIME
completed_at             DATETIME NULL
```

本任务使用的状态：

- `pending`：等待 Worker。
- `processing`：Worker 正在处理。
- `failed`：当前阶段不可自动恢复。

本任务使用的阶段：

- `generating`
- `downloading`
- `source_ready`

源 WAV 下载成功后保持 `status=processing`、`stage=source_ready`，由 T13 接续后处理并最终标记 `completed`。

在 `backend/app/models/__init__.py` 导入 `MusicTask`。

---

## 2. Fun-Music 适配层

新增：

```text
backend/app/services/music_aliyun.py
```

服务端点：

```text
POST {base_url}/services/audio/music/generation
```

固定请求：

```json
{
  "model": "fun-music-v1",
  "input": {
    "prompt": "最终 Prompt",
    "is_instrumental": true,
    "format": "wav",
    "enable_aigc_watermark": false
  }
}
```

要求：

- 不发送 `X-DashScope-SSE`。
- `is_instrumental`、格式和水印由服务端固定，不接受前端覆盖。
- 生成总超时建议 10 分钟。
- 返回结构化结果，不直接修改数据库。

解析并返回：

- `request_id`
- `output.audio.id`
- `output.audio.url`
- `output.audio.expires_at`
- `output.extra_info.channels`
- `output.extra_info.sample_rate`
- `usage.duration`

错误标准化：

- 配置缺失
- API Key 无效
- Workspace ID / endpoint 错误
- 未开通邀测权限
- 429 限流
- 内容审核拒绝
- 请求超时
- 响应结构异常

日志不得输出：

- API Key
- Authorization 请求头
- 带完整签名参数的临时 URL

---

## 3. Music Worker 基础链路

新增：

```text
backend/app/services/music_worker.py
```

默认并发数为 1，独立于现有 Audio Worker。

### 3.1 生成阶段

1. 查询最早的 `pending` 任务。
2. 更新为 `status=processing`、`stage=generating`。
3. 调用 `fun-music-v1`。
4. 成功后立即保存并 commit：
   - request ID
   - audio ID
   - 临时 URL
   - URL 过期时间
   - 接口返回的源时长、采样率、声道
5. 根据源音乐秒数计算费用估算。

费用字段仅为估算值，单价集中定义，不能散落硬编码；实际账单以阿里云控制台为准。

### 3.2 下载阶段

1. 更新 `stage=downloading`。
2. 使用数据库中已保存的 URL 下载，不重新调用模型。
3. 写入：

   ```text
   data/music/source/{task_id}.wav.part
   ```

4. 校验响应成功且文件非空。
5. 原子重命名为：

   ```text
   data/music/source/{task_id}.wav
   ```

6. 保存 `source_file_path`。
7. 更新为 `status=processing`、`stage=source_ready`。

### 3.3 防重复计费

必须按已有状态决定恢复点：

- 没有 `request_id` 和远端 URL：允许执行模型调用。
- 已有远端 URL：只能重试下载。
- 已有本地 WAV：不得重新下载或重新生成，直接保持 `source_ready`。
- 模型调用失败且没有生成结果：自动重试最多 1 次。
- 下载失败：复用同一 URL，额外自动重试最多 2 次。
- URL 过期且本地 WAV 不存在：标记失败，不自动重新生成。

获得远端 URL 后，任何自动异常处理路径都不得再次进入模型调用。

---

## 4. 音乐任务 API

新增：

```text
backend/app/schemas/music_task.py
backend/app/routers/music_tasks.py
```

并在 `backend/app/main.py` 挂载 `/api/music-tasks`。

### `POST /api/music-tasks`

```json
{
  "prompt": "前半段稍明亮，后半段逐渐安静",
  "effective_prompt": "创作用于睡前冥想的纯音乐……",
  "preset_params": {
    "scene": "sleep",
    "moods": ["calm", "warm"]
  },
  "target_duration_seconds": 600
}
```

校验：

- `effective_prompt` 非空且限制合理长度。
- `target_duration_seconds` 为 60～3600，为 T13 预留。
- API Key 和 Workspace ID 已配置。
- 服务端覆盖模型、格式、纯音乐和水印参数。

### `GET /api/music-tasks`

- 按创建时间倒序。
- 返回任务状态、阶段、源时长、估算费用和错误信息。
- 不返回 API Key。

### `GET /api/music-tasks/{id}`

- 返回完整任务详情，但不暴露带签名的远端 URL。

### `POST /api/music-tasks/{id}/retry`

- 根据现有字段恢复生成或下载。
- 已有 URL / WAV 时不得重新生成。

下载、删除和最终文件 API 由 T13 完成。

---

## 5. 测试要求

新增建议：

```text
backend/tests/test_music_aliyun.py
backend/tests/test_music_worker.py
backend/tests/test_music_tasks.py
backend/tests/test_music_migration.py
```

至少覆盖：

1. 正确构建非流式 Fun-Music 请求。
2. 服务端强制纯音乐、WAV、关闭尾部水印。
3. 正确解析远端结果和 usage.duration。
4. API Key、Workspace ID、邀测、限流、审核和超时错误。
5. 模型调用失败最多自动重试 1 次。
6. 获得 URL 后先持久化再下载。
7. 下载失败复用 URL，最多额外重试 2 次。
8. 下载失败不会重新调用模型。
9. 已有 WAV 时直接恢复到 `source_ready`。
10. URL 过期且无 WAV 时明确失败。
11. `.part` 不会被当作完成文件。
12. 目标时长只允许 60～3600 秒。
13. 迁移可连续执行两次。
14. 迁移保留全部现有数据。
15. API 响应和日志不泄露 API Key 或签名 URL。

---

## 验收标准

- [ ] `settings` 支持独立 `music_config`
- [ ] 旧 SQLite 数据迁移后完整保留
- [ ] 迁移连续执行两次保持幂等
- [ ] `music_tasks` 表和最终字段一次性建好，T13 无需再改表结构
- [ ] API 可创建、列表和查看音乐任务
- [ ] 服务端固定使用 `fun-music-v1`
- [ ] 服务端固定 `is_instrumental=true`、WAV、关闭尾部水印
- [ ] Worker 使用非流式调用且默认并发为 1
- [ ] 模型结果先持久化再下载
- [ ] 原始 WAV 保存到 `data/music/source`
- [ ] 下载完成后任务进入 `processing/source_ready`
- [ ] 模型调用自动重试不超过 1 次
- [ ] 下载额外重试不超过 2 次
- [ ] 已获得 URL 后不会因重试重复调用模型
- [ ] API 和日志不泄露凭证或完整签名 URL
- [ ] 自动测试不调用真实付费接口

---

## 预计涉及文件

### 新增

```text
backend/app/db_migrations.py
backend/app/models/music_task.py
backend/app/schemas/music_task.py
backend/app/routers/music_tasks.py
backend/app/services/music_aliyun.py
backend/app/services/music_worker.py
backend/tests/test_music_aliyun.py
backend/tests/test_music_worker.py
backend/tests/test_music_tasks.py
backend/tests/test_music_migration.py
```

### 修改

```text
backend/app/db.py
backend/app/main.py
backend/app/models/__init__.py
backend/app/models/setting.py
backend/app/schemas/setting.py
backend/app/routers/settings.py
```

---

## 后续依赖

- T13：从 `processing/source_ready` 接续 FFmpeg 后处理，生成最终 MP3 并完善文件生命周期。
- T14：增加音乐设置 UI、纯音乐工作区、Prompt 预设、试听下载和产物管理。
