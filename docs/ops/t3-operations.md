# T3 操作文档：Dify 日常运维

> 日期：2026-08-05  
> 适用范围：Dify 开源版（`C:\projects\github\dify\dify-1.16.1`）日常启动、停止与状态检查  
> 关联任务：`docs/task/03-dify-setup.md`  
> 说明：本文档仅覆盖**日常运维**部分；Dify Web 控制台操作、费用监控、备份升级等见后续任务文档。

---

## 1. Docker Desktop 启动（重启电脑后必做）

Docker Desktop **未设置开机自启**，每次重启电脑后需手动启动：

1. 点击开始菜单 → 启动 **Docker Desktop**
2. 等待右下角鲸鱼图标变为常亮（WSL2 后端就绪，约 20~60 秒）

> 若设为自启可减少一步，但会拖慢开机，默认保持手动。

---

## 2. Dify 启动 / 停止 / 重启

所有命令需在 Dify 的 `docker` 目录下执行，且 Docker 可能不在 PATH（首次需设置）：

```powershell
# ① 设置 Docker PATH（若 docker 命令找不到时执行）
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"

# ② 进入 Dify docker 目录
cd C:\projects\github\dify\dify-1.16.1\docker
```

### 2.1 启动

```powershell
docker compose up -d
```

- 镜像已就绪，后续启动通常 1~3 分钟
- 首次（或重拉镜像后）会执行数据库迁移，`api` 容器需等待 health 通过

### 2.2 停止

```powershell
docker compose down
```

- 停止容器，**保留数据卷**（数据库、插件、存储不丢失）

### 2.3 重启

```powershell
docker compose restart
```

- 不改配置时的快速重启

---

## 3. 状态检查

```powershell
# 查看所有容器状态
docker ps

# 关键容器应显示 Up (healthy)：nginx / api / db_postgres / redis
# 预期 15 个容器运行

# 检查 API 容器健康日志
docker logs -f docker-api-1

# 验证 Web 入口（应返回 200）
curl -s -o /dev/null -w "%{http_code}" http://localhost/install
```

**访问入口**

| 用途 | 地址 |
|---|---|
| Dify 控制台 | http://localhost |
| Dify API（服务端） | http://localhost/v1 |
| 首次安装页 | http://localhost/install |

---

## 4. 代理（VPN）说明

| 场景 | 是否需要代理 |
|---|---|
| 日常 LLM 调用（DeepSeek API） | **不需要**（已实测直连可达） |
| 拉取 Docker 镜像 | 需要（或使用镜像加速器） |
| 安装/更新 Dify 市场插件 | 需要 |

> 日常使用无需开代理；仅在首次拉镜像或更新插件时临时开启。

---

## 5. 常用命令速查

```powershell
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
cd C:\projects\github\dify\dify-1.16.1\docker

docker compose up -d          # 启动
docker compose down           # 停止（保留数据）
docker compose restart        # 重启
docker ps                     # 查看容器
docker images                 # 查看镜像
docker logs -f docker-api-1   # API 容器日志
docker compose logs --tail 100   # 最近 100 行全部日志
```

---

## 相关文档

- [T3 任务文档](../task/03-dify-setup.md)
- [T3 交接文档](t3-handover.md)
- [Docker 镜像加速器配置](docker-mirror-setup.md)
