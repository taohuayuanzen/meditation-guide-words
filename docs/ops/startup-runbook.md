# 服务启动执行手册

> **适用范围**：本机（Windows）首次启动与日常启动冥想音频工作台全部服务
> **目标读者**：AI Agent 按步骤执行；人类可参考备注理解
> **涉及服务**：Dify、后端（FastAPI）、音频 Worker、前端（Vite）
> **固定路径**：
> - 项目根目录：`C:\projects\apps\meditation-guide-words`
> - Dify 目录：`C:\projects\github\dify\dify-1.16.1`
>
> 若路径不同，请全局替换后再执行。

---

## 0. 环境前提检查（首次启动前执行）

> 以下命令在 PowerShell 中执行。若某项不存在，请先安装对应依赖。

```powershell
uv --version
node -v
npm -v
docker --version
```

**预期输出示例**：

```text
uv 0.15.0
v24.18.0
11.16.0
Docker version 27.x.x
```

- `uv` 用于后端 Python 依赖管理与虚拟环境
- `node` / `npm` 用于前端
- `docker` 用于启动 Dify

> 💡 若 `docker` 命令找不到，先执行：
> ```powershell
> $env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
> ```
> 并确认 Docker Desktop 已启动（右下角鲸鱼图标常亮）。

---

## 1. 首次启动

> 首次启动会安装依赖、初始化数据库、编译前端资源。耗时约 3~10 分钟。

### 1.1 启动 Dify

> Dify 详细运维见 [`docs/ops/dify-operations.md`](./dify-operations.md)。本手册只负责检查与启动。

**步骤 1.1.1：检查 Dify 是否已在运行**

```powershell
curl -s -o $null -w "%{http_code}" --max-time 5 http://localhost/install
```

**判断**：
- 返回 `200` → Dify 已运行，跳过 1.1.2
- 返回其他或超时 → 执行 1.1.2

**步骤 1.1.2：启动 Dify**

```powershell
cd C:\projects\github\dify\dify-1.16.1\docker
docker compose up -d
```

**步骤 1.1.3：等待并确认**

```powershell
Start-Sleep -Seconds 20
$code = curl -s -o $null -w "%{http_code}" --max-time 5 http://localhost/install
if ($code -ne "200") {
    Write-Host "Dify 尚未就绪，继续等待..."
    Start-Sleep -Seconds 30
    $code = curl -s -o $null -w "%{http_code}" --max-time 5 http://localhost/install
}
Write-Host "Dify 状态码: $code"
```

**失败处理**：
- 若最终仍非 `200`，查看日志：
  ```powershell
  docker compose logs --tail 100
  ```
- 参考 [`docs/ops/dify-operations.md`](./dify-operations.md) 排错。

---

### 1.2 启动后端

**步骤 1.2.1：安装依赖**

```powershell
cd C:\projects\apps\meditation-guide-words\backend
uv sync
```

**判断**：
- 命令退出码为 `0` → 继续
- 非 `0` → 检查网络，重试 `uv sync`；若仍失败，终止并报告

**步骤 1.2.2：启动后端服务**

```powershell
cd C:\projects\apps\meditation-guide-words\backend
uv run uvicorn app.main:app --reload --port 8000
```

> 该命令会保持前台运行。后续日常启动中，可通过 `Start-Process` 或直接在后台运行。本手册默认在新终端/后台任务中运行。

**步骤 1.2.3：健康检查**

等待约 3 秒后执行：

```powershell
curl -s --max-time 5 http://localhost:8000/api/health
```

**预期输出**：

```json
{"status":"ok"}
```

**失败处理**：
- 无响应或返回非预期 → 检查后端正前进程是否存活，查看后端输出日志。

---

### 1.3 启动音频 Worker

> Worker 负责消费 `audio_tasks` 表并合成音频。不启动时音频任务会一直处于 `pending`。

**步骤 1.3.1：启动 Worker**

```powershell
cd C:\projects\apps\meditation-guide-words\backend
uv run python -m app.services.audio_worker
```

> 该命令会保持前台循环运行。

**步骤 1.3.2：检查 Worker 是否正常启动**

观察 Worker 输出。正常启动时无错误日志，进程持续运行。

**常见失败处理**：

若 Worker 输出包含 `no such column: audio_tasks.retry_count`，按以下步骤自动修复（保留数据）：

```powershell
cd C:\projects\apps\meditation-guide-words\backend
.venv\Scripts\python.exe - <<'PY'
import sqlite3
conn = sqlite3.connect('data/meditation.db')
cur = conn.cursor()
cur.execute("ALTER TABLE audio_tasks ADD COLUMN retry_count INTEGER DEFAULT 0")
conn.commit()
conn.close()
print('retry_count 列已添加')
PY
```

然后**重新启动 Worker**。

> 若 ALTER 执行失败（例如表被锁定），可停止后端和 Worker 后删除 `data/meditation.db`，再重新启动后端自动重建。**注意：删除数据库会丢失所有引导词、设置和任务记录。**

---

### 1.4 启动前端

**步骤 1.4.1：安装依赖**

```powershell
cd C:\projects\apps\meditation-guide-words\frontend
npm install
```

**判断**：
- 命令退出码为 `0` → 继续
- 非 `0` → 检查网络，重试 `npm install`；若仍失败，终止并报告

**步骤 1.4.2：启动前端开发服务器**

```powershell
cd C:\projects\apps\meditation-guide-words\frontend
npm run dev
```

> 该命令会保持前台运行。

**步骤 1.4.3：健康检查**

等待约 3 秒后执行：

```powershell
curl -s -o $null -w "%{http_code}" --max-time 5 http://localhost:5173/
```

**预期输出**：`200`

**失败处理**：
- 若返回 `000` 或其他 → 检查前端进程是否存活，查看前端输出日志。

---

### 1.5 首次启动完成检查清单

| 检查项 | 命令 | 预期结果 |
|---|---|---|
| Dify 运行 | `curl -s -o $null -w "%{http_code}" http://localhost/install` | `200` |
| 后端运行 | `curl -s http://localhost:8000/api/health` | `{"status":"ok"}` |
| Worker 运行 | 观察进程/日志 | 无报错，持续轮询 |
| 前端运行 | `curl -s -o $null -w "%{http_code}" http://localhost:5173/` | `200` |

全部通过即可访问 [http://localhost:5173](http://localhost:5173) 使用应用。

---

## 2. 日常启动

> 日常启动跳过依赖安装，直接启动四个服务。若依赖有更新，按"首次启动"对应步骤重新安装。

### 2.1 检查并启动 Dify

```powershell
$code = curl -s -o $null -w "%{http_code}" --max-time 5 http://localhost/install
if ($code -ne "200") {
    cd C:\projects\github\dify\dify-1.16.1\docker
    docker compose up -d
    Start-Sleep -Seconds 30
} else {
    Write-Host "Dify 已在运行"
}
```

---

### 2.2 启动后端

```powershell
cd C:\projects\apps\meditation-guide-words\backend
uv run uvicorn app.main:app --reload --port 8000
```

**启动后检查**：

```powershell
curl -s --max-time 5 http://localhost:8000/api/health
```

预期：`{"status":"ok"}`

---

### 2.3 启动 Worker

```powershell
cd C:\projects\apps\meditation-guide-words\backend
uv run python -m app.services.audio_worker
```

**启动后检查**：

观察输出，若出现 `no such column: audio_tasks.retry_count`，按 1.3.2 修复后重启。

---

### 2.4 启动前端

```powershell
cd C:\projects\apps\meditation-guide-words\frontend
npm run dev
```

**启动后检查**：

```powershell
curl -s -o $null -w "%{http_code}" --max-time 5 http://localhost:5173/
```

预期：`200`

---

## 3. 停止服务

如需停止全部或部分服务，参见 [`service-shutdown.md`](./service-shutdown.md)。

---

## 4. 日志查看

### 4.1 后端 / Worker 日志

- 若以后台任务启动，日志路径由任务系统决定（如 Kimi Code 后台任务面板）
- 若在前台 PowerShell 运行，直接观察当前终端输出

### 4.2 前端日志

- 前台运行时直接观察终端
- 构建错误可查看 `frontend/npm run build` 输出

### 4.3 Dify 日志

```powershell
cd C:\projects\github\dify\dify-1.16.1\docker
docker compose logs --tail 100
```

---

## 5. 故障排查速查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 前端页面无法打开 | 前端未启动或端口 5173 被占用 | 检查进程，或换端口 `npm run dev -- --port 5173 --strictPort` |
| 后端 `/api/health` 无响应 | 后端未启动或端口 8000 被占用 | 检查进程，或换端口 `--port 8001`（需同步前端代理） |
| 音频任务一直 `pending` | Worker 未启动 | 启动 Worker |
| Worker 报 `no such column: retry_count` | 数据库 schema 旧 | 执行 1.3.2 的 ALTER TABLE，或重建数据库 |
| Dify 无法访问 | Docker Desktop 未启动或容器未启动 | 启动 Docker Desktop，执行 `docker compose up -d` |
| `uv` 命令找不到 | 未安装 uv | 安装 [uv](https://docs.astral.sh/uv/getting-started/installation/) |
| `npm install` 卡住 | 网络问题 | 换镜像源：`npm install --registry=https://registry.npmmirror.com` |

---

## 6. 相关文档

- [服务停止执行手册](./service-shutdown.md)
- [后端启动与运维指南](./backend/backend-startup.md)
- [前端启动与运维指南](./frontend/frontend-startup.md)
- [Dify 日常运维](./dify-operations.md)
- [TTS 凭证与联调](./t5-tts-operations.md)
- [阿里云音色更新说明](./aliyun/voice-update-guide.md)
