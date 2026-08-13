# T13：纯音乐时长适配、任务恢复与文件生命周期

## 任务目标

在 T12 已能生成并保存原始 WAV 的基础上，引入系统 FFmpeg / FFprobe，将源音乐循环、裁剪和交叉淡化为 1～60 分钟目标时长 MP3，并补齐任务恢复、格式下载、删除和 Worker 启停能力。

本任务完成后，纯音乐后端链路可以不依赖前端，通过 API 完成：

```text
创建任务 → 生成 WAV → 时长适配 MP3 → 查询 → 下载 → 重试 → 删除
```

**预计耗时**：1 ～ 1.5 天

---

## 前置依赖

- T12 已完成。
- `music_tasks` 已包含源文件、目标时长、最终文件和阶段恢复所需字段。
- Music Worker 能把任务推进到 `status=processing`、`stage=source_ready`。

---

## 范围

### 包含

- FFmpeg / FFprobe 可用性检测
- 音频真实时长探测
- 循环、裁剪、交叉淡化、首尾淡化
- 目标时长 MP3
- Worker 阶段接续和进程重启恢复
- WAV / MP3 文件列表与下载 API
- 删除任务和全部文件
- 启停脚本集成
- 后端状态 / 能力检查
- 后端测试与本地非计费验收

### 不包含

- 前端纯音乐工作区
- 前端音乐设置
- Prompt 预设与预览
- 产物页 UI
- 播放器音量
- 引导音频混合、ducking 或响度混合
- 多段模型生成拼接

---

## 已确认决策

| 决策项 | 结果 |
|---|---|
| 目标时长预设 | 5 / 10 / 15 / 20 / 30 分钟 |
| 自定义范围 | 1～60 分钟 |
| 源文件 | 长期保留 WAV |
| 最终文件 | MP3 |
| 长时长策略 | 单段源音乐本地循环，不重复调用模型 |
| 删除 | 同时删除源文件、最终文件、临时文件和任务记录 |
| 取消 | MVP 不强制取消 processing 任务 |
| FFmpeg | 必要系统依赖，启动时检查 |
| FFmpeg 缺失时创建任务 | 后端返回 503，并指出缺失能力 |
| MP3 编码 | `libmp3lame` 192 kbps，保留源采样率和声道 |
| 源时长 | `source_duration_seconds` 使用 FFprobe 的文件真实时长 |
| 费用估算 | 保留阿里云 usage 生成时计算的 `estimated_cost`，不按探测时长重算 |
| 真实计费验收 | 最多调用模型一次；首次失败即停止，不触发模型自动重试 |

---

## 1. FFmpeg 能力检查

新增能力检查服务，例如：

```text
backend/app/services/media_capabilities.py
```

检查：

```text
ffmpeg -version
ffprobe -version
```

要求：

- 使用参数数组启动进程，不通过 shell 拼接。
- 设置短超时。
- 缓存检查结果，避免每次请求都创建进程。
- 提供后端只读能力接口，例如：

  ```text
  GET /api/music-tasks/capabilities
  ```

  返回：

  ```json
  {
    "ffmpeg_available": true,
    "ffprobe_available": true,
    "music_processing_available": true
  }
  ```

缺少 FFmpeg 时：

- FastAPI、现有 Audio Worker 和前端仍可启动。
- Music Worker 不得进入后处理循环。
- 已有产物仍可查询和下载。
- 新建音乐任务由后端返回 HTTP 503 并指出具体缺失能力；T14 同时禁用提交，避免绕过前端后产生无法完成的 pending 任务。

---

## 2. 音频后处理服务

新增：

```text
backend/app/services/music_postprocessor.py
```

职责：

- 使用 ffprobe 获取真实时长、采样率和声道。
- 根据目标时长构建安全的 FFmpeg 参数。
- 生成临时 MP3。
- 校验结果并原子重命名。

### 2.1 文件路径

```text
data/music/source/{task_id}.wav
data/music/final/{task_id}_{target_minutes}min.mp3.part
data/music/final/{task_id}_{target_minutes}min.mp3
```

源 WAV 不得被覆盖。

### 2.2 处理规则

- 源时长约等于目标时长：转码并校准目标时长。
- 源时长长于目标时长：裁剪并添加结尾淡出。
- 源时长短于目标时长：循环源音乐，在衔接处交叉淡化，达到目标时长后裁剪。

循环实现采用固定复杂度的“无缝循环单元”：将源音乐尾部与头部交叉淡化为一个可重复单元，再循环该单元至目标时长，避免滤镜图随目标时长或循环次数线性增长。循环单元属于临时文件，成功或失败后均须清理。

默认参数：

- 循环交叉淡化：4 秒。
- 开头淡入：3 秒。
- 结尾淡出：8 秒。
- 最终时长误差：不超过 1 秒。
- MP3 编码：`libmp3lame`、192 kbps；保留源采样率和声道，不做响度标准化。

边界处理：

- 源音乐短于交叉淡化长度时，按源时长比例缩短淡化，不能生成非法滤镜参数。
- 实际循环交叉淡化取 `min(4 秒, 源时长 / 3)`。
- 目标时长小于默认首尾淡化总长时，自动缩短淡化。
- 输入为空、损坏或无音频流时明确失败。

安全要求：

- 不把 Prompt、文件名或用户输入直接拼入 shell 字符串。
- 文件路径由服务端根据 task ID 生成。
- 目标时长限制为 60～3600 秒。
- FFmpeg 进程设置合理超时。
- 失败时清理 `.part`，保留源 WAV。

---

## 3. Worker 阶段接续与恢复

扩展 `backend/app/services/music_worker.py`。

最终阶段：

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

后处理步骤：

1. 查询 `processing/source_ready` 任务。
2. 确认源 WAV 存在。
3. 更新 `stage=processing`。
4. 运行后处理服务。
5. 使用 ffprobe 校验最终 MP3 时长。
6. 保存 `file_path`、`final_duration_seconds`，并使用 FFprobe 的真实源文件时长更新 `source_duration_seconds`；已按阿里云 usage 计算的 `estimated_cost` 保持不变。
7. 更新 `status=completed`、`completed_at`。

### 3.1 进程重启恢复

Worker 启动时根据持久化状态恢复：

| 已有状态 | 恢复动作 |
|---|---|
| pending，无远端结果 | 从模型生成继续 |
| processing/generating，有远端 URL | 跳过模型，进入下载 |
| processing/downloading，有完整 WAV | 跳过下载，进入后处理 |
| processing/source_ready | 进入后处理 |
| processing/processing，有完整 MP3 | 校验后标记 completed |
| processing/processing，只有 `.part` | 删除 `.part`，重新后处理 |
| failed，有 WAV | 用户重试后仅重新后处理 |

后处理失败不得重新下载或重新调用模型。

---

## 4. 下载和删除 API

扩展 `/api/music-tasks`。

### `GET /api/music-tasks/{id}/downloads`

返回当前真实存在的文件：

```json
{
  "items": [
    {
      "kind": "source",
      "format": "wav",
      "label": "原始 WAV",
      "size": 12345678,
      "duration_seconds": 198,
      "download_url": "/api/music-tasks/1/download/source"
    },
    {
      "kind": "final",
      "format": "mp3",
      "label": "10 分钟 MP3",
      "size": 4567890,
      "duration_seconds": 600,
      "download_url": "/api/music-tasks/1/download/final"
    }
  ]
}
```

### `GET /api/music-tasks/{id}/download/{kind}`

- `kind=source`：下载 WAV。
- `kind=final`：下载 MP3。
- 文件不存在返回 404。
- 不接受客户端直接传文件路径。

### `POST /api/music-tasks/{id}/retry`

扩展 T12 行为：

- 有最终 MP3：校验后标记完成。
- 有 WAV：只重新后处理。
- 有远端 URL：只重新下载。
- 只有明确未成功生成的任务才允许重新调用模型。

### `DELETE /api/music-tasks/{id}`

- `pending`：允许删除。
- `processing`：返回 409，MVP 不强制取消。
- `completed/failed`：允许删除。
- 删除源 WAV、最终 MP3、残留 `.part` 和数据库记录。
- 路径必须从数据库和受控目录解析，防止路径穿越。

下载、删除以及 T14 的音乐重命名共用统一文件生命周期服务；`music_tasks` 路由和 `artifacts` 路由不得各自实现一套路径和删除逻辑。

---

## 5. 启停脚本

更新：

- `start.ps1`
- `stop.ps1`
- `scripts/start.sh`
- `backend/.env.example`（如增加音乐并发或目录配置）

启动：

1. 检查 `ffmpeg`、`ffprobe`。
2. 启动 FastAPI。
3. 启动现有 Audio Worker。
4. FFmpeg 可用时启动 Music Worker。
5. 启动前端。

停止：

- 同时识别 `app.services.audio_worker` 和 `app.services.music_worker`。
- 如存在 processing 音乐任务，显示中断提示。
- 被中断的任务在下次启动后按阶段恢复。

不得因 FFmpeg 缺失阻止整个应用启动。

---

## 6. 测试要求

新增建议：

```text
backend/tests/test_music_postprocessor.py
backend/tests/test_music_recovery.py
backend/tests/test_music_files.py
```

使用本地短音频测试，不调用阿里云。

至少覆盖：

1. FFmpeg / FFprobe 可用与不可用。
2. 源音乐短于目标时长时正确循环。
3. 源音乐长于目标时长时正确裁剪。
4. 最终时长误差不超过 1 秒。
5. 首尾淡化和循环交叉淡化参数合法。
6. 极短源音频的淡化边界。
7. 损坏、空文件和无音频流失败。
8. FFmpeg 超时和失败清理 `.part`。
9. 处理失败保留源 WAV。
10. Worker 从 URL、WAV、MP3、`.part` 各阶段恢复。
11. 后处理重试不会下载或重新生成。
12. 下载列表只返回真实存在文件。
13. 下载 kind 和路径校验。
14. pending 可删除、processing 禁止删除。
15. completed/failed 删除全部文件和记录。
16. FFmpeg 缺失时其他应用能力仍可用。

---

## 验收标准

- [ ] 启动时可检查 FFmpeg 和 FFprobe
- [ ] FFmpeg 缺失不会阻止整个应用启动
- [ ] 源 WAV 可转换为目标时长 MP3
- [ ] 支持目标时长 60～3600 秒
- [ ] 预设时长的数据约束支持 5 / 10 / 15 / 20 / 30 分钟
- [ ] 短音乐通过循环和 4 秒交叉淡化扩展
- [ ] 最终音频包含 3 秒淡入和 8 秒淡出，边界情况下安全缩短
- [ ] 最终时长误差不超过 1 秒
- [ ] 不覆盖或删除源 WAV
- [ ] 后处理不触发新的模型调用
- [ ] Worker 中断后可按阶段恢复
- [ ] WAV 和 MP3 均可通过 API 下载
- [ ] pending 任务可删除，processing 任务返回 409
- [ ] 删除 completed/failed 任务时清理全部文件和记录
- [ ] Music Worker 已纳入启停脚本
- [ ] 后端链路可不依赖前端完成端到端操作
- [ ] 自动测试不调用真实付费接口

---

## 预计涉及文件

### 新增

```text
backend/app/services/media_capabilities.py
backend/app/services/music_postprocessor.py
backend/tests/test_music_postprocessor.py
backend/tests/test_music_recovery.py
backend/tests/test_music_files.py
```

### 修改

```text
backend/app/services/music_worker.py
backend/app/routers/music_tasks.py
backend/app/schemas/music_task.py
backend/app/main.py
backend/app/config.py
start.ps1
stop.ps1
scripts/start.sh
backend/.env.example
```

---

## 后续依赖

T14 使用本任务提供的 capabilities、任务、下载和删除 API，实现完整纯音乐用户界面与产物集成。
