# Docker 镜像加速器配置指南

## 问题背景

在中国大陆直接访问 Docker Hub（`docker.io`）拉取镜像时，经常遇到以下错误：

- `unexpected EOF` — 网络连接中断
- `dial tcp: lookup ... on ...: no such host` — DNS 解析失败
- `i/o timeout` — 下载超时
- 下载速度极慢（< 100KB/s）

原因：Docker Hub 的 CDN 节点（`production.cloudfront.docker.com`）在国内访问不稳定。

**解决方案**：为 Docker Desktop 配置国内镜像加速器（registry mirror），所有镜像拉取请求通过加速器中转。

---

## 操作步骤

### 1. 打开 Docker Desktop 设置

- Windows 任务栏右下角找到 Docker 鲸鱼图标
- 右键 → **Settings**（或点击齿轮图标 ⚙️）

### 2. 进入 Docker Engine 配置

- 左侧菜单选择 **Docker Engine**
- 右侧会显示 JSON 格式的配置编辑器

### 3. 添加 registry-mirrors

在原有 JSON 中添加 `"registry-mirrors"` 字段。以下为完整的推荐配置：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io"
  ]
}
```

> **注意**：JSON 语法严格，最后一个 `}` 前不能有逗号，所有字符串必须使用双引号。

### 4. 应用并重启

- 点击右下角 **Apply & Restart** 按钮
- Docker Desktop 会自动重启，等待状态变为 "Docker Desktop is running"（约 30 秒）

### 5. 验证配置

打开终端（PowerShell），确认 mirror 已生效：

```powershell
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
docker info | Select-String "Registry Mirrors|Mirrors"
```

如果输出包含 `https://docker.1ms.run` 和 `https://docker.m.daocloud.io`，说明配置成功。

---

## 可用镜像地址

| 镜像地址 | 来源 | 说明 |
|---|---|---|
| `https://docker.1ms.run` | Docker 镜像代理 | 社区维护，稳定性好 |
| `https://docker.m.daocloud.io` | DaoCloud | 老牌国内镜像服务 |
| `https://docker.xuanyuan.me` | 轩辕镜像 | 社区维护 |
| `https://hub.rat.dev` | Rat Hub | 社区代理 |
| `https://镜像加速器地址.mirror.aliyuncs.com` | 阿里云 ACR | 需注册阿里云账号获取专属地址 |

> **建议**：配置 2~3 个镜像地址作为冗余，docker 会依次尝试直到成功拉取。

### 阿里云专属镜像（可选）

如有阿里云账号，建议配置专属加速器地址（速度更快、更稳定）：

1. 登录 [cr.console.aliyun.com](https://cr.console.aliyun.com)
2. 左侧「镜像工具」→「镜像加速器」
3. 复制专属地址（格式：`https://<你的ID>.mirror.aliyuncs.com`）
4. 将其作为 `registry-mirrors` 的第一个地址

---

## 故障排查

### Q1：配置后仍然拉取失败

先检查镜像是否生效：

```powershell
docker info | Select-String "Mirrors"
```

如果没有输出镜像地址，可能是 JSON 格式错误。检查：
- 是否有中文引号或多余逗号
- `registry-mirrors` 是否拼写正确（注意 `-` 和 `s`）
- 是否点击了 Apply & Restart

### Q2：某个镜像地址不可用

Docker 会依次尝试配置的多个镜像地址。如果某一个挂了，会自动 fallback 到下一个。

如果所有镜像都不可用，可以：
- 更换镜像地址列表
- 使用 VPN/代理后直接拉取（不经过加速器）
- 向镜像加速器提供商反馈

### Q3：WSL2 环境下镜像不生效

Docker Desktop WSL2 模式下，`daemon.json` 的 `registry-mirrors` 配置自动同步到 WSL2 内的 Docker 守护进程，无需额外操作。

如果仍然不生效，尝试在 WSL2 内检查：

```bash
# 在 WSL2 终端中
cat /etc/docker/daemon.json
```

### Q4：恢复默认配置（不使用镜像）

如果想恢复直连 Docker Hub（如已配置代理或 VPN），删除 `registry-mirrors` 字段后 Apply & Restart 即可。

---

## 相关文档

- [Docker 官方文档 — daemon.json](https://docs.docker.com/reference/cli/dockerd/#daemon-configuration-file)
- [T3-Dify 部署任务](../task/03-dify-setup.md)
- [技术规范 — 第 5 章 Dify 部署](../tech/tech-spec.md)
