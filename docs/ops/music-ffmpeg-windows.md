# Windows FFmpeg 与纯音乐运维

## 1. 安装 FFmpeg

项目不会自动安装系统软件。任选一种 Windows 包管理方式：

```powershell
# winget
winget install --id Gyan.FFmpeg -e

# 或 Chocolatey
choco install ffmpeg

# 或 Scoop
scoop install ffmpeg
```

安装完成后关闭并重新打开 PowerShell，确认两个命令都可用：

```powershell
ffmpeg -version
ffprobe -version
```

如果命令仍找不到，检查 FFmpeg 的 `bin` 目录是否已加入系统 `PATH`，然后重新打开终端和应用启动窗口。

## 2. 能力检查

启动后访问：

```text
GET http://localhost:8000/api/music-tasks/capabilities
```

正常结果：

```json
{
  "ffmpeg_available": true,
  "ffprobe_available": true,
  "music_processing_available": true
}
```

FFmpeg 缺失不会阻止后端、引导音频 Worker 或前端启动，但 Music Worker 不会启动，
新建纯音乐任务和新格式的分段引导音频任务都会返回 503。历史整篇 TTS 任务仍按旧路径处理。

新格式引导音频也可检查：

```text
GET http://localhost:8000/api/audio-tasks/capabilities
```

正常结果中的 `audio_rendering_available` 应为 `true`。

## 3. 启停与恢复

`start.ps1` 会检查 FFmpeg/FFprobe，并在能力完整时启动：

```powershell
.\start.ps1
```

手动启动 Music Worker：

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.music_worker
```

`stop.ps1` 会停止 Audio Worker 和 Music Worker。处理中任务被中断后，下次启动会根据远端 URL、源 WAV/MP3、最终 MP3 或 `.part` 文件恢复，不会因本地后处理失败重新调用模型。

## 4. 文件目录

```text
backend/data/music/source/{task_id}.wav
backend/data/music/source/{task_id}.mp3
backend/data/music/final/{task_id}_{target_minutes}min.mp3
```

阿里云源 WAV 与 MiniMax 源 MP3 均长期保留。删除音乐任务时会一并删除源文件、最终 MP3、临时文件和数据库记录，操作不可恢复。

## 5. 配置与计费

- 默认供应商为 MiniMax，固定正式版 `music-3.0`、非流式、URL 返回、纯音乐和源 MP3；只需 API Key。
- 阿里云保留 `fun-music-v1`，使用华北 2（北京）业务空间的 Workspace ID 和 API Key，源格式为 WAV。
- 两套凭证独立保存；新任务在创建时固化供应商和模型，历史任务不会随全局设置切换。
- MiniMax 费用以 MiniMax 账单为准；阿里云按实际源音乐秒数估算。目标时长由本地 FFmpeg 循环或裁剪产生。
- MiniMax 模型调用失败后不自动重试。手动重新生成需要确认可能重复计费；下载和后处理恢复不会再次调用模型。
- 自动测试不会调用真实模型。真实联调必须先约定最大调用次数和产物保留规则。
