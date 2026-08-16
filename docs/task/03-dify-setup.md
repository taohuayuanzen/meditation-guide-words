# T3：Dify 开源版部署与智能体配置

> T16 之后，实际 Dify 发布与验证以 [语义停顿 Prompt 发布手册](../ops/dify/publish-pause-semantics-prompts.md) 为准；本文保留初始部署背景。

## 任务目标

在指定外部路径独立部署 Dify 开源版，创建两个 Chat 应用，分别配置"引导词生成"和"音频生成"的 System Prompt 与变量，验证 API 连通性，为 FastAPI 代理提供可调用的 Dify 端点。

**预计耗时**：1 ~ 1.5 天

---

## 前置依赖

- T1 完成（项目目录结构已创建）
- 本地已安装 Docker 和 Docker Compose

---

## 当前进度（2026-08-05 晚 · 已完成）

> **实际部署路径**：`C:\projects\github\dify\dify-1.16.1`（家中电脑，与文档示例 `D:\project\github\dify` 不同；脚本侧由环境变量 `DIFY_DIR` 覆盖，见 T8）

### 已完成

- [x] Dify 源码已就绪（`C:\projects\github\dify\dify-1.16.1`，v1.16.1）
- [x] Docker Desktop v29.6.2 已安装（WSL2 后端）
- [x] Dify `.env` 已从 `.env.example` 创建（默认配置，`SECRET_KEY` 留空自动生成）
- [x] `backend/.env.example` 模板已创建
- [x] Docker `daemon.json` 已配置镜像加速器（`docker.1ms.run`）
- [x] 12/12 个 Docker 镜像已拉取完成（本机全量重拉，直连 Docker Hub）
- [x] Dify 已启动：`docker compose up -d`（15 个容器，`docker-api-1` healthy）
- [x] 管理员账号已创建（`http://localhost/install`）
- [x] DeepSeek 模型已配置（插件 `langgenius/deepseek:0.0.19` 已安装并配置 API Key）
- [x] 两个 Chatflow 应用已创建并配置 System Prompt
- [x] 两个应用的 API Key 已获取并填入 `backend/.env`
- [x] curl 验证 API 连通性（App A 流式 / App B blocking 均正常）

### 应用信息

| 应用 | Dify App ID | API Key | 说明 |
|---|---|---|---|
| App A 冥想引导词生成 | `b9f7e107-3684-488e-9850-ca0ed1d25fef` | `app-8xRdywVvvHTU0TbltNn2FE0D` | streaming，deepseek-chat，上下文 6 轮 |
| App B 冥想音频生成 | `be4954e7-24bd-489b-80b8-0b1bc7fc958f` | `app-AJ5RHvv2bNgt7T7ee86FYavz` | blocking，输出 TTS 参数 JSON |

### 镜像拉取状态

| 镜像 | 状态 |
|------|------|
| `busybox:latest` | ✅ |
| `redis:6-alpine` | ✅ |
| `postgres:15-alpine` | ✅ |
| `nginx:latest` | ✅ |
| `ubuntu/squid:latest` | ✅ |
| `semitechnologies/weaviate:1.27.0` | ✅ |
| `langgenius/dify-sandbox:0.2.15` | ✅ |
| `langgenius/dify-web:1.16.1` | ✅ |
| `langgenius/dify-plugin-daemon:0.6.3-local` | ✅ |
| `langgenius/dify-agent-backend:1.16.1` | ✅ |
| `langgenius/dify-agent-local-sandbox:1.16.1` | ✅ |
| `langgenius/dify-api:1.16.1` | ✅（4.15GB，直连拉取，偶发 EOF 断流，重试 4 次完成） |

### 实践经验

- **DaoCloud 镜像**（`docker.m.daocloud.io`）对小镜像速度快，但 `dify-api` 大镜像未缓存
- **`docker.1ms.run`** 能拉取 `dify-api` 的大层（单次拉到 155MB/326MB 后断流）
- **VPN/代理直连 Docker Hub** 是最终可靠方案（本机 4 次重试完成全部镜像）
- Docker 层缓存支持断点续传，重试跳过已下载层
- **Dify 1.16 登录密码需 Base64 编码**（`FieldEncryption.decrypt_field`）
- **Console API 需携带 CSRF**：`X-CSRF-Token` 头 = `csrf_token` cookie 值
- **DeepSeek 是插件式提供商**：需先安装 `langgenius/deepseek` 插件（详见踩坑记录）
- **工作流节点 ID 不能含连字符 `-`**：模板正则 `[a-zA-Z0-9_]` 不匹配，需用 `llm1`/`start`/`answer1` 这类 ID

### 磁盘空间

- 已清理 WPSDrive 缓存释放 **23.3GB**
- Docker 数据盘（`docker_data.vhdx`）约 13.9GB
- 建议保持 **≥5GB** 空闲

---

## 详细步骤

### 3.1 选择 Dify 部署路径

部署路径：`D:\project\github\dify\dify-1.16.1`（v1.16.1 稳定 tag，已就绪）。

> **决策确认**：使用实际解压路径 `D:\project\github\dify\dify-1.16.1`，带版本号便于后续升级管理。多个本地项目可共享此 Dify 实例。

### 3.2 启动 Dify

```powershell
# Docker 不在 PATH 时需先设置
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"
cd D:\project\github\dify\dify-1.16.1\docker
docker compose up -d
```

首次启动会拉取镜像并初始化数据库。如遇网络问题，参见 `docs/ops/docker-mirror-setup.md`。

### 3.3 初始化管理员账号

访问 `http://localhost/install`，按提示创建管理员账号。

### 3.4 创建两个 Chat 应用

登录 Dify 后，进入"工作室"，分别创建：

| 应用名 | API 名称 | 类型 |
|---|---|---|
| `冥想引导词生成` | `meditation-script-gen` | Chatflow |
| `冥想音频生成` | `meditation-audio-gen` | Chatflow |

> **决策确认**：两个应用均选择 **Chatflow**，支持可视化工作流编排，后续可灵活加入变量、条件分支等节点。

### 3.5 配置"引导词生成"应用（App A）

#### System Prompt 示例

```
你是一位专业的冥想引导词创作专家。每次回复都返回完整的最新 JSON，不返回局部 patch 或 JSON 以外的内容。

要求：
1. 使用第二人称"你"，语气温柔、安抚。
2. 按“开场安顿 → 主体练习 → 回收注意 → 结束”组织，目标时长包含朗读与留白。
3. block 按完整表达或练习步骤划分，主体显式安排 breath、observe 或 practice。
4. pause_after.kind 只允许 short、paragraph、breath、observe、practice、transition、ending、none。
5. breath.count 为 1～10；observe/practice 的 suggested_seconds 为 5～60。
6. 不输出 SSML、Markdown、XML、方括号停顿标记或供应商参数。

JSON Schema：
{"title":"标题","version":1,"target_duration_seconds":600,"blocks":[{"text":"可读正文","pause_after":{"kind":"paragraph"}}]}
```

#### 模型配置
- **模型提供商**：DeepSeek（与项目 `Setting.llm_config.provider` 默认值一致）
- 在 Dify 设置页 → 模型供应商 → 添加 DeepSeek，填入 API Key
- 在 Chatflow 编排中选择 DeepSeek 模型（如 `deepseek-chat`）
- 流式输出：开启
- 上下文轮数：建议 6 轮

> **决策确认**：使用 DeepSeek 作为 LLM 提供商，与项目后端 Schema 默认 `provider = "deepseek"` 保持一致。

### 3.6 配置"音频生成"应用（App B）

#### System Prompt 示例

```
你是冥想音频编排助理。输入包含 script_plan、pause_profile、voice_prompt 和 tts_context。只量化停顿并提取声音参数，不得改写、删减、新增或重排正文。

JSON Schema：
{
  "version": 1,
  "pause_profile_id": "standard_v1",
  "voice": {"voice_id":"允许列表中的 ID","rate":0.86,"volume":1.0,"pitch":1.0,"instruction":"简洁声音描述"},
  "segments": [{"id":"b1","text":"原文","pause_after_ms":1800,"pause_kind":"paragraph","pause_strategy":"silence"}]
}

规则：
1. segments 与 blocks 的 ID、顺序、文本严格一一对应。
2. short 使用 natural；none 使用 natural 且为 0ms；其余使用 silence。
3. 时长严格按 pause_profile 计算；voice_id 只能来自 allowed_voices。
4. rate 为 0.75～1.05，volume 为 0～2，pitch 为 0.5～2；情绪合并到 instruction。
5. 不输出 SSML、供应商请求体、代码块或解释。
```

#### 变量配置
在 Chatflow 中定义四个字符串输入变量：`script_plan`、`pause_profile`、`voice_prompt`、`tts_context`（结构化值以 JSON 字符串传入）。

工作流设计：
```
声音描述 + 四个受控输入变量
        ↓
LLM 节点（输出供应商无关 render_plan）
        ↓
结束节点（输出 JSON）
```

> 实际 TTS 调用不走 Dify 节点，而是 FastAPI 后端拿到 JSON 后调用 TTS 服务。

### 3.7 获取 API Key

分别在两个应用的"访问 API"页面获取 API Key：
- App A API Key → 用于工作区 1
- App B API Key → 用于工作区 2

### 3.8 验证 Dify API 连通性

使用 `curl` 或 Postman 测试 App A：

```bash
curl -X POST 'http://localhost/v1/chat-messages' \
  --header 'Authorization: Bearer {APP_A_API_KEY}' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "inputs": {},
    "query": "生成一段5分钟睡前放松冥想引导词",
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "local-user"
  }'
```

应返回 SSE 流式数据。

测试 App B：

```bash
curl -X POST 'http://localhost/v1/chat-messages' \
  --header 'Authorization: Bearer {APP_B_API_KEY}' \
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

应返回包含 TTS 参数 JSON 的响应。

### 3.9 记录配置信息

将获取的 API Key 填入 `backend/.env` 文件（从 `.env.example` 复制）：

```bash
# 复制模板文件
copy backend\.env.example backend\.env

# 编辑 backend\.env，填入实际的 API Key：
DIFY_BASE_URL=http://localhost/v1
DIFY_SCRIPT_APP_KEY=app-xxxxxxxxxxxxx
DIFY_AUDIO_APP_KEY=app-xxxxxxxxxxxxx
```

> `backend/.env` 已在 `.gitignore` 中，不会提交到版本控制。

---

## 关键设计点

- Dify 部署在 `D:/project/github/dify/dify-1.16.1`，与 meditation-guide-words 项目解耦，可被多个项目共享。
- 两个 Chat 应用职责单一：一个只生成文本，一个只解析声音提示词。
- App B 的 LLM 必须严格输出 JSON，System Prompt 中需反复强调"只输出 JSON"。
- 流式响应使用 Dify 的 `response_mode=streaming`；解析 TTS 参数使用 `blocking` 更稳定。

---

## 验收标准

- [x] Dify 成功部署到 `C:\projects\github\dify\dify-1.16.1` 并通过 Docker 运行
- [x] 管理员账号已创建，可登录 `http://localhost`
- [x] 已创建两个 Chat 应用，分别命名为"冥想引导词生成"和"冥想音频生成"
- [x] App A 的 System Prompt 配置完成，流式调用可返回引导词文本
- [x] App B 的 System Prompt 配置完成，blocking 调用可返回标准 JSON 参数
- [x] 已获取两个应用的 API Key 并记录
- [x] 通过 `curl` 验证两个应用 API 均可正常访问

---

## 关联文档

- `docs/tech/tech-spec.md` 第 5 章
- `docs/prd/meditation-guide-words-prd.md` 第 6 章
- `docs/ops/docker-mirror-setup.md` — Docker 镜像加速器配置（国内用户必读）
- `docs/ops/t3-handover.md` — T3 交接文档（当前状态 + 继续步骤）

---

## 风险备注

- **Docker 不在 PATH**：需设置 `$env:Path = "C:\Program Files\Docker\Docker\resources\bin;$env:Path"` 或加入系统 PATH。
- **Docker credential 助手报错**：`docker-credential-desktop: executable file not found in %PATH%`，原因同上。
- **国内网络问题**：Dify 首次启动需拉取 10+ 个镜像（总计约 10GB），公共镜像对大镜像层（>50MB）缓存不完整。推荐使用 VPN/代理直连 Docker Hub。
- **磁盘空间**：Dify 全套镜像 + WSL2 VM 约需 15-20GB。确保 C 盘 ≥5GB 空闲。
- **`docker info` 不显示镜像**：`Registry Mirrors:` 始终为空，但不影响实际使用（已验证镜像确实走加速器）。
- App B 输出 JSON 不稳定时，可在 System Prompt 中增加示例（few-shot）提升一致性。
