# Dify 编排页“同步数据中”修复操作手册

> 适用环境：Dify 开源版 `1.16.1`，Windows + Docker Desktop  
> 当前实例目录：`C:\projects\github\dify\dify-1.16.1\docker`  
> 故障现象：编排页持续显示“同步数据中，只需几秒钟”，无法正常编辑  
> 修复目标：让 API 与 `api_websocket` 使用同一个 `SECRET_KEY`  
> 最后更新：2026-08-14

本文是当前实例的人工修复流程。执行过程中会修改 Dify 的 `docker/.env`，并重建 API、WebSocket 和 Worker 容器；不会删除数据库、应用、工作流或模型配置。

建议预留 10～15 分钟维护时间。操作期间 Dify 控制台和 API 会短暂不可用。

---

## 1. 已确认的故障原因

当前环境已经确认：

- `docker/.env` 中的 `SECRET_KEY` 为空。
- API 容器挂载了共享目录 `/app/api/storage`。
- `api_websocket` 容器没有挂载该目录。
- API 与 WebSocket 因此各自生成了不同的 `.dify_secret_key`。
- 浏览器 WebSocket 被服务端拒绝。
- `api_websocket` 日志包含：

```text
Socket authentication failed
jwt.exceptions.InvalidSignatureError: Signature verification failed
401 Unauthorized: Invalid token signature
```

Redis 从 API 和 WebSocket 容器内均可正常 `PING`，因此本次不要先修改 Redis 密码、清空 Redis 或重建数据库。

本手册采用以下修复策略：

1. 读取 API 已经持久化的 `.dify_secret_key`。
2. 把它写入 `docker/.env` 的 `SECRET_KEY`。
3. 重建相关容器，让所有进程加载同一密钥。

复用现有密钥比生成新密钥更稳妥，可以尽量避免现有登录会话和签名立即失效。

---

## 2. 将要修改的内容

### 2.1 唯一需要修改的配置文件

```text
C:\projects\github\dify\dify-1.16.1\docker\.env
```

修改前：

```dotenv
SECRET_KEY=
```

修改后：

```dotenv
SECRET_KEY=<volumes/app/storage/.dify_secret_key 中的现有值>
```

不要添加引号、前后空格或行内注释。

### 2.2 只读取、不修改的密钥文件

```text
C:\projects\github\dify\dify-1.16.1\docker\volumes\app\storage\.dify_secret_key
```

### 2.3 需要重建的容器

```text
api
api_websocket
worker
worker_beat
```

不需要删除 PostgreSQL、Redis、Weaviate 或任何 volume。

---

## 3. 安全注意事项

- 不要把 `SECRET_KEY` 粘贴到聊天、Issue、截图或操作记录中。
- 不要把 Dify 的 `.env`、`.dify_secret_key` 或本手册生成的备份提交到 Git。
- 不要执行 `docker compose down -v`；`-v` 会删除持久化 volume。
- 不要删除 `docker/volumes` 目录。
- 不要生成新密钥覆盖 `.dify_secret_key`。
- 不要使用 `docker logs` 输出完整请求体或用户数据。
- PowerShell 检查只显示密钥长度和哈希前缀，不显示密钥原文。

---

## 4. 修复前备份与检查

以普通 PowerShell 或管理员 PowerShell 打开终端。如果普通终端无权连接 Docker，请使用管理员 PowerShell。

### 4.1 进入 Dify Docker 目录

```powershell
$difyDockerDir = 'C:\projects\github\dify\dify-1.16.1\docker'
Set-Location -LiteralPath $difyDockerDir
```

确认当前目录：

```powershell
Get-Location
Test-Path -LiteralPath '.\.env'
Test-Path -LiteralPath '.\volumes\app\storage\.dify_secret_key'
```

三个结果应分别为正确目录、`True`、`True`。任一文件不存在时停止操作，不要自行创建空密钥文件。

### 4.2 检查容器状态

```powershell
docker compose ps
```

至少确认以下服务存在：

- `api`
- `api_websocket`
- `web`
- `nginx`
- `db_postgres`
- `redis`

### 4.3 创建本地备份

```powershell
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $env:LOCALAPPDATA 'DifyBackups'
$backupDir = Join-Path $backupRoot "workflow-sync-$timestamp"
New-Item -ItemType Directory -Path $backupDir | Out-Null

Copy-Item -LiteralPath '.\.env' -Destination (Join-Path $backupDir '.env')
Copy-Item `
    -LiteralPath '.\volumes\app\storage\.dify_secret_key' `
    -Destination (Join-Path $backupDir '.dify_secret_key')

Get-ChildItem -LiteralPath $backupDir | Select-Object Name, Length
```

预期出现两个非空文件：`.env` 和 `.dify_secret_key`。

备份保存在当前 Windows 用户的 `%LOCALAPPDATA%\DifyBackups`，位于 Dify Git 仓库之外。该目录仍含敏感信息，不要通过聊天或邮件发送。

### 4.4 确认当前 `.env` 的 SECRET_KEY 为空

以下命令不会输出密钥内容：

```powershell
$secretEnvLine = Get-Content -LiteralPath '.\.env' -Encoding UTF8 |
    Where-Object { $_ -match '^SECRET_KEY=' } |
    Select-Object -First 1

if ($null -eq $secretEnvLine) {
    Write-Output 'SECRET_KEY 行不存在'
} else {
    $currentValue = ($secretEnvLine -split '=', 2)[1]
    Write-Output "SECRET_KEY 已设置：$([bool]$currentValue)，长度：$($currentValue.Length)"
}
```

当前已知预期为：

```text
SECRET_KEY 已设置：False，长度：0
```

如果这里已经显示为 `True`，停止操作，重新排查容器是否仍使用旧环境变量。

---

## 5. 写入现有持久化密钥

推荐使用下面的 PowerShell 脚本自动替换。脚本不会把密钥打印到终端。

```powershell
$envPath = Join-Path $difyDockerDir '.env'
$secretPath = Join-Path $difyDockerDir 'volumes\app\storage\.dify_secret_key'

$secret = [IO.File]::ReadAllText($secretPath).Trim()

if ([string]::IsNullOrWhiteSpace($secret)) {
    throw '.dify_secret_key 为空，停止操作'
}

if ($secret.Length -lt 32) {
    throw "密钥长度异常：$($secret.Length)，停止操作"
}

$lines = [Collections.Generic.List[string]]::new()
$lines.AddRange([IO.File]::ReadAllLines($envPath))
$found = $false

for ($index = 0; $index -lt $lines.Count; $index++) {
    if ($lines[$index].StartsWith('SECRET_KEY=')) {
        if ($found) {
            throw '.env 中存在多个 SECRET_KEY 行，停止操作并人工检查'
        }
        $lines[$index] = "SECRET_KEY=$secret"
        $found = $true
    }
}

if (-not $found) {
    $lines.Add("SECRET_KEY=$secret")
}

$utf8WithoutBom = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllLines($envPath, $lines, $utf8WithoutBom)

Write-Output "SECRET_KEY 已写入，长度：$($secret.Length)"
```

正常情况下只显示长度，不显示密钥。

### 5.1 验证 `.env` 修改结果

```powershell
$savedLine = Get-Content -LiteralPath $envPath -Encoding UTF8 |
    Where-Object { $_ -match '^SECRET_KEY=' } |
    Select-Object -First 1

$savedSecret = ($savedLine -split '=', 2)[1]
$sourceSecret = [IO.File]::ReadAllText($secretPath).Trim()

Write-Output "SECRET_KEY 行数量：$((Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^SECRET_KEY=' }).Count)"
Write-Output "已保存密钥长度：$($savedSecret.Length)"
Write-Output "与持久化密钥一致：$($savedSecret -ceq $sourceSecret)"
```

预期：

```text
SECRET_KEY 行数量：1
已保存密钥长度：64
与持久化密钥一致：True
```

文件末尾换行不计入密钥长度。当前密钥文件本身为 65 字节，其中包含一个换行字符，因此读取并 `Trim()` 后通常为 64 个字符。

确认一致后，可清除当前 PowerShell 会话中的明文变量：

```powershell
Remove-Variable secret, savedSecret, sourceSecret, currentValue -ErrorAction SilentlyContinue
```

### 5.2 校验 Compose 配置语法

```powershell
docker compose config --quiet
```

预期无输出且退出码为 `0`：

```powershell
Write-Output "Compose 校验退出码：$LASTEXITCODE"
```

不要直接运行不带 `--quiet` 的 `docker compose config`，因为展开后的配置可能把 `SECRET_KEY` 打印到终端。

---

## 6. 重建相关容器

确认第 5 章全部通过后执行：

```powershell
docker compose up -d --force-recreate api api_websocket worker worker_beat
```

说明：

- `--force-recreate` 确保容器重新读取 `.env`。
- 不使用 `down`，数据库和其他服务保持运行。
- 不使用 `-v`。
- Dify API 和控制台会短暂中断。

等待容器启动：

```powershell
docker compose ps api api_websocket worker worker_beat
```

API 可能需要约 30～90 秒完成迁移检查和健康检查。可循环查看：

```powershell
for ($attempt = 1; $attempt -le 18; $attempt++) {
    $status = docker inspect `
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' `
        docker-api-1 2>$null

    Write-Output "[$attempt/18] api: $status"
    if ($status -eq 'healthy') { break }
    Start-Sleep -Seconds 5
}
```

如果 Compose 项目名不是 `docker`，实际容器名可能不同。以 `docker compose ps` 输出为准，不要猜测容器名。

---

## 7. 服务端验证

### 7.1 比较容器环境变量的脱敏指纹

当前实例容器名为 `docker-api-1` 和 `docker-api_websocket-1`。执行：

```powershell
foreach ($container in @('docker-api-1', 'docker-api_websocket-1')) {
    docker exec $container python -c `
        "import hashlib,os; v=os.getenv('SECRET_KEY',''); print('$container', 'set='+str(bool(v)), 'len='+str(len(v)), 'sha256='+hashlib.sha256(v.encode()).hexdigest()[:12] if v else 'sha256=-')"
}
```

通过条件：

- 两行均为 `set=True`。
- 两行长度相同且至少 32。
- 两行 `sha256` 前缀完全相同。

不要使用 `docker exec ... env` 或 `docker inspect` 直接打印完整环境变量。

### 7.2 检查 API 健康状态

```powershell
curl.exe -s -o NUL -w "console=%{http_code} total=%{time_total}s`n" http://localhost/
curl.exe -s -o NUL -w "api=%{http_code} total=%{time_total}s`n" http://localhost/v1
```

入口返回 `200`、`307` 或 `308` 均可接受，关键是能快速响应而非连接失败。

### 7.3 检查 WebSocket 错误日志

先记住：只有浏览器重新连接后才能验证签名错误是否消失。因此先执行第 8 章的浏览器验证，再运行：

```powershell
docker logs --since 5m docker-api_websocket-1 2>&1 |
    Select-String -Pattern 'InvalidSignatureError|Invalid token signature|Socket authentication failed' -CaseSensitive:$false
```

通过条件：没有新输出。

如果日志里只出现容器重建前的旧时间记录，应缩短 `--since` 范围或核对日志时间戳。

---

## 8. 浏览器验证

1. 关闭所有 Dify 编排页面。
2. 重新打开 `http://localhost`。
3. 如果登录状态异常，退出后重新登录。
4. 进入“工作室”。
5. 打开 App A 的编排页。
6. 使用 `Ctrl+F5` 强制刷新。
7. 等待 5～10 秒。

通过条件：

- “同步数据中，只需几秒钟”提示消失。
- 工作流节点可点击、移动和编辑。
- 页面不再重复弹出同步提示。
- 自动保存状态正常显示。

然后打开 App B，重复相同检查。该问题是全局 WebSocket 鉴权问题，两个应用都应同时恢复。

> 不建议用“随便移动一个节点”作为第一次验证，以免留下无意义草稿。先点击节点打开配置面板；确认页面稳定后再进行实际 Prompt 修改。

恢复后，按照 [App A / App B 语义停顿 Prompt 发布手册](./publish-pause-semantics-prompts.md) 更新和发布 Prompt。

---

## 9. 完整验收清单

- [ ] `.env` 和 `.dify_secret_key` 已备份。
- [ ] `.env` 中只有一个 `SECRET_KEY=`。
- [ ] `SECRET_KEY` 与原 `.dify_secret_key` 内容一致。
- [ ] `docker compose config --quiet` 通过。
- [ ] API、WebSocket、Worker、Worker Beat 已重建。
- [ ] API 恢复 healthy。
- [ ] API 和 WebSocket 的密钥脱敏指纹一致。
- [ ] App A 编排页同步提示消失。
- [ ] App B 编排页同步提示消失。
- [ ] 没有新的 `InvalidSignatureError`。
- [ ] Dify 已重新登录或现有登录状态正常。
- [ ] 未删除数据库、Redis 或 volumes。

---

## 10. 异常处理

### 10.1 `docker compose` 无权连接 Docker

现象：

```text
permission denied while trying to connect to the docker API
```

处理：

1. 确认 Docker Desktop 已启动。
2. 关闭当前终端。
3. 使用管理员身份打开 PowerShell。
4. 重新从第 4.1 节开始。

### 10.2 API 容器无法启动

只查看最近日志：

```powershell
docker logs --since 10m docker-api-1 2>&1 | Select-Object -Last 100
```

常见检查：

- `.env` 是否出现多个 `SECRET_KEY=`。
- 密钥行是否被引号包裹。
- 密钥是否被换行截断。
- `docker compose config --quiet` 是否通过。

不要删除数据库或 volumes。

### 10.3 修改后被要求重新登录

如果复用的是原 `.dify_secret_key`，通常现有登录仍可继续；浏览器中仍可能保留旧的短期 Token。

处理顺序：

1. 退出 Dify。
2. 关闭 Dify 标签页。
3. 重新打开并登录。
4. 再进入编排页。

重新登录不会删除应用或工作流。

### 10.4 JWT 错误消失，但仍有 Redis receive 错误

先验证编排页面是否已经可以编辑。

- 如果页面已恢复：记录 Redis 错误频率，作为独立问题后续排查，不要立即改 Redis 密码。
- 如果页面仍卡住：再检查 `REDIS_SOCKET_TIMEOUT`、Socket.IO Pub/Sub 和 Dify 1.16.x 已知问题。

两个容器内执行 Redis `PING` 成功并不能完全证明 Pub/Sub 长连接正常，但已经排除最基础的网络和认证失败。

### 10.5 页面仍显示同步中，日志也无签名错误

按顺序检查：

1. API/WebSocket 密钥脱敏指纹是否一致。
2. 浏览器是否重新登录并 `Ctrl+F5`。
3. Nginx `/socket.io/` 请求是否返回 `101 Switching Protocols`。
4. 浏览器控制台是否还有 `Connection rejected by server`。
5. `api_websocket` 是否持续运行而非反复重启。

不要通过隐藏同步遮罩或直接修改数据库绕过。

---

## 11. 回退方案

如果写入 `SECRET_KEY` 后出现新的严重故障：

1. 保存当前错误日志，但不要包含密钥和完整请求体。
2. 停止继续编辑工作流。
3. 如果已经重新打开 PowerShell，先把 `$backupDir` 设置为第 4.3 节实际输出的备份目录。
4. 从第 4.3 节的备份恢复 `.env`：

```powershell
Copy-Item `
    -LiteralPath (Join-Path $backupDir '.env') `
    -Destination (Join-Path $difyDockerDir '.env') `
    -Force
```

5. 重新创建相关容器：

```powershell
docker compose up -d --force-recreate api api_websocket worker worker_beat
```

注意：恢复空 `SECRET_KEY` 会恢复修复前状态，编排同步问题可能再次出现。此操作只是回到原始环境，不是最终解决方案。

替代修复是通过 `docker-compose.override.yaml` 给 `api_websocket` 挂载共享 storage：

```yaml
services:
  api_websocket:
    volumes:
      - ./volumes/app/storage:/app/api/storage
```

该方案应在显式 `SECRET_KEY` 方案无法使用时再评估。不要同时修改多个方向，否则难以判断实际生效原因。

---

## 12. 修复记录模板

```text
执行日期：
执行人：
修复前 .env SECRET_KEY：空 / 已设置（不要记录值）
备份目录：
Compose 配置校验：通过 / 失败
相关容器重建：成功 / 失败
API 健康状态：
API/WebSocket 密钥指纹是否一致：是 / 否（只记录是否一致）
App A 编排页：正常 / 异常
App B 编排页：正常 / 异常
InvalidSignatureError：已消失 / 仍存在
Redis receive 错误：无 / 仍存在
备注：
```

操作记录中不要填写完整 `SECRET_KEY`、Dify App API Key、模型 API Key、完整引导词或完整工作流数据。
