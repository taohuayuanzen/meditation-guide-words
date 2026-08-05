# T3 交接文档：Dify 部署与智能体配置

> 日期：2026-08-05  
> 交接原因：切换至家中电脑继续  
> 关联任务：`docs/task/03-dify-setup.md`

---

## 一、当前状态

### 已完成部分

| 项目 | 状态 | 说明 |
|------|------|------|
| Dify 源码 | ✅ | `D:\project\github\dify\dify-1.16.1`，v1.16.1 |
| Docker Desktop | ✅ | v29.6.2，WSL2 后端 |
| Dify .env | ✅ | 已从 `.env.example` 复制，使用默认配置即可 |
| `backend/.env.example` | ✅ | 模板已创建，含 Dify 配置占位符 |
| 镜像加速器 | ✅ | `daemon.json` 已配置 `docker.1ms.run` |
| Docker 镜像 | 🔄 11/12 | 仅缺 `langgenius/dify-api:1.16.1` |

### 已拉取的 11 个镜像

`busybox:latest`, `redis:6-alpine`, `postgres:15-alpine`, `nginx:latest`, `ubuntu/squid:latest`, `semitechnologies/weaviate:1.27.0`, `langgenius/dify-sandbox:0.2.15`, `langgenius/dify-web:1.16.1`, `langgenius/dify-plugin-daemon:0.6.3-local`, `langgenius/dify-agent-backend:1.16.1`, `langgenius/dify-agent-local-sandbox:1.16.1`

---

## 二、家中电脑继续步骤

### 前置条件

- [ ] 安装 Docker Desktop（如未安装）
- [ ] git clone 本项目到本地
- [ ] 确保 C 盘 **≥10GB** 空闲（Dify 镜像 + WSL2 ≈ 15-20GB）

### 步骤 1：启动 Dify

由于镜像需要重新拉取（除非迁移 docker_data.vhdx），从零开始：

```powershell
# 1. 克隆 Dify（家中电脑）
mkdir D:\project\github
cd D:\project\github
git clone https://github.com/langgenius/dify.git
cd dify
git checkout v1.16.1   # 使用稳定版本

# 2. 配置 .env（默认即可）
cd docker
copy .env.example .env

# 3. 如果国内网络，先配置镜像加速器（否则跳过）
# 参考：docs/ops/docker-mirror-setup.md

# 4. 启动（有 VPN/代理会更顺利）
docker compose up -d
```

> 家中网络如果直连 Docker Hub 通畅，全程约 10-15 分钟即可完成。

### 步骤 2：初始化管理员

1. 浏览器访问 `http://localhost/install`
2. 设置管理员邮箱和密码
3. 登录 Dify 控制台

### 步骤 3：配置 DeepSeek 模型

1. Dify 右上角头像 → **设置** → **模型供应商**
2. 添加 **DeepSeek**，填入 API Key
3. 确认模型列表中包含 `deepseek-chat`

### 步骤 4：创建 App A — 冥想引导词生成

1. 工作室 → **创建应用** → 选择 **Chatflow**
2. 应用名：`冥想引导词生成`，API 名称：`meditation-script-gen`
3. 进入编排，配置 **LLM 节点**：

**System Prompt**（粘贴到 LLM 节点的 System 输入框）：

```
你是一位专业的冥想引导词创作专家。请根据用户的需求，生成一段适合朗读、节奏舒缓、结构清晰的冥想引导词。

要求：
1. 使用第二人称"你"，语气温柔、安抚。
2. 段落分明，包含开场、主体引导、结束三个部分。
3. 语言口语化，避免复杂术语。
4. 如用户未指定时长，默认生成 5~10 分钟可朗读的内容。
5. 输出纯文本，不要加 Markdown 标题、列表符号或表情。
```

**模型配置**：
- 模型：`deepseek-chat`
- 流式输出：✅ 开启
- 上下文轮数：6

4. 点击 **发布**

### 步骤 5：创建 App B — 冥想音频生成

1. 工作室 → **创建应用** → **Chatflow**
2. 应用名：`冥想音频生成`，API 名称：`meditation-audio-gen`

3. 添加输入变量：
   - 变量名：`script_content`，类型：`String`

4. 编排工作流：
   ```
   [开始] → [LLM 节点] → [结束]
               ↑
     script_content 变量
   ```

5. **LLM 节点 System Prompt**：

```
你是一位声音设计助理。用户会用自然语言描述他想要的冥想音频声音风格。请从描述中提取以下参数，并输出为严格的 JSON 格式，不要输出任何其他内容。

JSON Schema：
{
  "voice_id": "音色ID字符串",
  "speed": 0.8,
  "volume": 1.0,
  "emotion": "情绪标签，如 gentle/calm/warm",
  "output_format": "mp3"
}

规则：
1. 如果用户没有指定具体音色，请根据性别、年龄感选择合理的 voice_id。
2. speed 范围 0.5~2.0，冥想场景建议 0.8~1.0。
3. volume 范围 0~2.0，默认 1.0。
4. 只输出 JSON，不要加 markdown 代码块、不要解释。
```

6. 模型：`deepseek-chat`，响应模式：`blocking`
7. 点击 **发布**

### 步骤 6：获取 API Key

1. 两个应用分别进入 **访问 API** 页面
2. 复制 API Key（格式：`app-xxxxxxxxxxxxx`）

### 步骤 7：记录到项目 .env

```bash
cd <项目目录>/backend
copy .env.example .env
# 编辑 .env，填入：
DIFY_BASE_URL=http://localhost/v1
DIFY_SCRIPT_APP_KEY=app-xxxxxxxxxxxxx    # App A 的 Key
DIFY_AUDIO_APP_KEY=app-xxxxxxxxxxxxx     # App B 的 Key
```

### 步骤 8：验证

```bash
# 测试 App A（引导词生成）
curl -X POST 'http://localhost/v1/chat-messages' \
  --header 'Authorization: Bearer <APP_A_API_KEY>' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "inputs": {},
    "query": "生成一段5分钟睡前放松冥想引导词",
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "local-user"
  }'

# 测试 App B（音频参数解析）
curl -X POST 'http://localhost/v1/chat-messages' \
  --header 'Authorization: Bearer <APP_B_API_KEY>' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "inputs": {
      "script_content": "请闭上眼睛，深呼吸..."
    },
    "query": "温柔女声，语速慢，正念风格",
    "response_mode": "blocking",
    "conversation_id": "",
    "user": "local-user"
  }'
```

---

## 三、踩坑记录

| # | 问题 | 原因 | 解法 |
|---|------|------|------|
| 1 | `docker-credential-desktop: not found` | Docker 不在 PATH | `$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"` |
| 2 | `unexpected EOF` 拉取失败 | 国内访问 Docker Hub 不稳定 | 配置镜像加速器 或 开 VPN 直连 |
| 3 | `docker.1ms.run` 大层断流 | 公共镜像对 >50MB 层限速/限流 | 多次重试利用断点续传，或换 DaoCloud |
| 4 | `docker.m.daocloud.io` 拉不到 dify-api | 该镜像未缓存 `langgenius/dify-api` | 换回 `docker.1ms.run` 或 VPN 直连 |
| 5 | `docker info` 不显示镜像 | 已知 bug，不影响实际功能 | 忽略，镜像仍然走加速器 |
| 6 | Docker Desktop 无法启动 | C 盘已满 | 清理 WPSDrive（23GB）等后释放空间 |
| 7 | `daemon.json` 修改后不生效 | WSL2 后端需重启 Docker Desktop | Apply & Restart 即可 |

---

## 四、配置文件速查

### Docker daemon.json（镜像加速器）

文件路径：`C:\Users\<用户名>\.docker\daemon.json`

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
    "https://docker.1ms.run"
  ]
}
```

### 项目 .env（后端配置）

文件路径：`<项目根>/backend/.env.example`（复制为 `.env` 后填入）

### Dify .env

文件路径：`D:\project\github\dify\dify-1.16.1\docker\.env`
默认配置即可，无需修改。

---

## 五、Docker 常用命令

```powershell
# 设置 PATH（Docker 不在系统 PATH 时每次需执行）
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"

# 查看运行容器
docker ps

# 查看所有容器（含已停止）
docker ps -a

# 查看镜像
docker images

# 查看日志（容器名用 docker ps 查看）
docker logs -f <容器名>

# 停止所有服务
cd D:\project\github\dify\dify-1.16.1\docker
docker compose down

# 重启
docker compose restart
```

---

## 相关文档

- [T3 任务文档](../task/03-dify-setup.md)
- [Docker 镜像加速器配置](docker-mirror-setup.md)
- [技术规范 — 第 5 章](../tech/tech-spec.md)
