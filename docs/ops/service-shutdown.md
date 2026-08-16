# 服务停止执行手册

> **适用范围**：本机（Windows）停止冥想音频工作台全部服务
> **目标读者**：AI Agent 按步骤执行；人类可参考备注理解
> **涉及服务**：前端（Vite）、音频 Worker、后端（FastAPI）、Dify
> **固定路径**：
> - 项目根目录：`C:\projects\apps\meditation-guide-studio`
> - Dify 目录：`C:\projects\github\dify\dify-1.16.1`
>
> 若路径不同，请全局替换后再执行。

---

## 0. 安全提示

> ⚠️ 本手册涉及结束操作系统进程和停止 Docker 容器。执行前请确认：
> - 没有正在进行的音频生成任务（否则可能导致任务中断并标记为失败）
> - 你确实想要停止对应服务
>
> 建议先阅读第 1 章的"停止前检查"，确认待停止的进程信息后再执行停止操作。

---

## 1. 停止前检查

> 以下命令用于列出当前运行的相关进程和容器，**不会结束任何进程**。

### 1.1 检查前端（端口 5173）

```powershell
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue |
    Select-Object LocalPort, OwningProcess,
        @{Name="ProcessName";Expression={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}},
        @{Name="CommandLine";Expression={
            (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.OwningProcess)" -ErrorAction SilentlyContinue).CommandLine
        }}
```

### 1.2 检查后端（端口 8000）

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    Select-Object LocalPort, OwningProcess,
        @{Name="ProcessName";Expression={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}},
        @{Name="CommandLine";Expression={
            (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.OwningProcess)" -ErrorAction SilentlyContinue).CommandLine
        }}
```

### 1.3 检查音频 Worker

```powershell
Get-WmiObject Win32_Process |
    Where-Object { $_.CommandLine -like "*app.services.audio_worker*" } |
    Select-Object ProcessId, ProcessName, CommandLine
```

### 1.4 检查 Dify 容器

```powershell
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
cd C:\projects\github\dify\dify-1.16.1\docker
docker compose ps
```

---

## 2. 一键停止全部服务

> 按依赖反向顺序停止：前端 → Worker → 后端 → Dify。

```powershell
# 1. 停止前端（端口 5173）
$frontendPid = (Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue).OwningProcess
if ($frontendPid) {
    Write-Host "正在停止前端进程 (PID: $frontendPid)..."
    Stop-Process -Id $frontendPid -Force
} else {
    Write-Host "前端未运行"
}

# 2. 停止音频 Worker
$workerProcesses = Get-WmiObject Win32_Process |
    Where-Object { $_.CommandLine -like "*app.services.audio_worker*" }
if ($workerProcesses) {
    foreach ($proc in $workerProcesses) {
        Write-Host "正在停止 Worker 进程 (PID: $($proc.ProcessId))..."
        Stop-Process -Id $proc.ProcessId -Force
    }
} else {
    Write-Host "Worker 未运行"
}

# 3. 停止后端（端口 8000）
$backendPid = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess
if ($backendPid) {
    Write-Host "正在停止后端进程 (PID: $backendPid)..."
    Stop-Process -Id $backendPid -Force
} else {
    Write-Host "后端未运行"
}

# 4. 停止 Dify
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
cd C:\projects\github\dify\dify-1.16.1\docker
Write-Host "正在停止 Dify 容器..."
docker compose down

Write-Host "全部服务停止完成"
```

---

## 3. 单独停止某个服务

### 3.1 只停止前端

```powershell
$pid = (Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue).OwningProcess
if ($pid) {
    Write-Host "停止前端进程 (PID: $pid)"
    Stop-Process -Id $pid -Force
} else {
    Write-Host "前端未运行"
}
```

### 3.2 只停止音频 Worker

```powershell
$processes = Get-WmiObject Win32_Process |
    Where-Object { $_.CommandLine -like "*app.services.audio_worker*" }
if ($processes) {
    foreach ($proc in $processes) {
        Write-Host "停止 Worker 进程 (PID: $($proc.ProcessId))"
        Stop-Process -Id $proc.ProcessId -Force
    }
} else {
    Write-Host "Worker 未运行"
}
```

### 3.3 只停止后端

```powershell
$pid = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess
if ($pid) {
    Write-Host "停止后端进程 (PID: $pid)"
    Stop-Process -Id $pid -Force
} else {
    Write-Host "后端未运行"
}
```

### 3.4 只停止 Dify

```powershell
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
cd C:\projects\github\dify\dify-1.16.1\docker
docker compose down
```

> `docker compose down` 会停止容器但保留数据卷。

---

## 4. 停止后验证

> 执行停止操作后，应确认服务确实已停止。

### 4.1 验证前端已停止

```powershell
$code = curl -s -o $null -w "%{http_code}" --max-time 3 http://localhost:5173/
if ($code -eq "000") {
    Write-Host "前端已停止"
} else {
    Write-Host "前端仍可能运行，状态码: $code"
}
```

### 4.2 验证后端已停止

```powershell
$code = curl -s -o $null -w "%{http_code}" --max-time 3 http://localhost:8000/api/health
if ($code -eq "000") {
    Write-Host "后端已停止"
} else {
    Write-Host "后端仍可能运行，状态码: $code"
}
```

### 4.3 验证 Worker 已停止

```powershell
$processes = Get-WmiObject Win32_Process |
    Where-Object { $_.CommandLine -like "*app.services.audio_worker*" }
if ($processes) {
    Write-Host "Worker 仍在运行"
} else {
    Write-Host "Worker 已停止"
}
```

### 4.4 验证 Dify 已停止

```powershell
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
cd C:\projects\github\dify\dify-1.16.1\docker
$containers = docker compose ps -q
if ($containers) {
    Write-Host "Dify 容器仍在运行"
} else {
    Write-Host "Dify 容器已停止"
}
```

---

## 5. 常见问题

### Q1：按端口找不到进程，但服务似乎还在运行

可能原因：服务运行在 IPv6 或不同端口，或 `Get-NetTCPConnection` 需要管理员权限。

处理：

```powershell
# 按进程名模糊查找
Get-Process | Where-Object { $_.ProcessName -like "*node*" -or $_.ProcessName -like "*python*" }
```

### Q2：停止 Dify 时提示 `docker: command not found`

处理：先设置 Docker PATH：

```powershell
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
```

### Q3：Stop-Process 失败，提示拒绝访问

处理：以管理员身份重新打开 PowerShell 再执行。

### Q4：只想重启服务，不需要完全停止

处理：
1. 执行本手册停止服务
2. 按 [`startup-runbook.md`](./startup-runbook.md) 重新启动

---

## 6. 相关文档

- [服务启动执行手册](./startup-runbook.md)
- [Dify 日常运维](./dify-operations.md)
- [后端启动与运维指南](./backend/backend-startup.md)
- [前端启动与运维指南](./frontend/frontend-startup.md)
