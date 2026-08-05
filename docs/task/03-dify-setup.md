# T3：Dify 开源版部署与智能体配置

## 任务目标

在指定外部路径独立部署 Dify 开源版，创建两个 Chat 应用，分别配置"引导词生成"和"音频生成"的 System Prompt 与变量，验证 API 连通性，为 FastAPI 代理提供可调用的 Dify 端点。

**预计耗时**：1 ~ 1.5 天

---

## 前置依赖

- T1 完成（项目目录结构已创建）
- 本地已安装 Docker 和 Docker Compose

---

## 详细步骤

### 3.1 选择 Dify 部署路径

建议部署到 `D:/project/github/dify`，作为多个本地项目共享的 Dify 实例。

```bash
mkdir -p D:/project/github
cd D:/project/github
git clone https://github.com/langgenius/dify.git
cd dify
```

> 建议使用稳定 tag，而非 main 分支：
> ```bash
> git checkout $(git describe --tags $(git rev-list --tags --max-count=1))
> ```

### 3.2 启动 Dify

```bash
cd docker
docker-compose up -d
```

首次启动会拉取镜像并初始化数据库，耗时约 5~15 分钟。

### 3.3 初始化管理员账号

访问 `http://localhost/install`，按提示创建管理员账号。

### 3.4 创建两个 Chat 应用

登录 Dify 后，进入"工作室"，分别创建：

| 应用名 | API 名称 | 类型 |
|---|---|---|
| `冥想引导词生成` | `meditation-script-gen` | Chatflow / Chatbot |
| `冥想音频生成` | `meditation-audio-gen` | Chatflow |

### 3.5 配置"引导词生成"应用（App A）

#### System Prompt 示例

```
你是一位专业的冥想引导词创作专家。请根据用户的需求，生成一段适合朗读、节奏舒缓、结构清晰的冥想引导词。

要求：
1. 使用第二人称"你"，语气温柔、安抚。
2. 段落分明，包含开场、主体引导、结束三个部分。
3. 语言口语化，避免复杂术语。
4. 如用户未指定时长，默认生成 5~10 分钟可朗读的内容。
5. 输出纯文本，不要加 Markdown 标题、列表符号或表情。
```

#### 模型配置
- 在"编排"中选择 LLM 模型（后续通过设置页调用时，Dify 会使用其自身配置的模型，FastAPI 只负责转发）。
- 流式输出：开启
- 上下文轮数：建议 6 轮

### 3.6 配置"音频生成"应用（App B）

#### System Prompt 示例

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

#### 变量配置
在 Chatflow 中定义一个输入变量：
- `script_content`：引导词正文，字符串类型

工作流设计：
```
用户输入（声音描述） + 变量 script_content
        ↓
LLM 节点（解析为 TTS 参数 JSON）
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

将以下信息记录下来，后续填入设置页或环境变量：

```
DIFY_BASE_URL=http://localhost/v1
DIFY_SCRIPT_APP_KEY=xxx
DIFY_AUDIO_APP_KEY=xxx
```

---

## 关键设计点

- Dify 部署在 `D:/project/github/dify`，与 meditation-guide-words 项目解耦，可被多个项目共享。
- 两个 Chat 应用职责单一：一个只生成文本，一个只解析声音提示词。
- App B 的 LLM 必须严格输出 JSON，System Prompt 中需反复强调"只输出 JSON"。
- 流式响应使用 Dify 的 `response_mode=streaming`；解析 TTS 参数使用 `blocking` 更稳定。

---

## 验收标准

- [ ] Dify 成功部署到 `D:/project/github/dify` 并通过 Docker 运行
- [ ] 管理员账号已创建，可登录 `http://localhost`
- [ ] 已创建两个 Chat 应用，分别命名为"冥想引导词生成"和"冥想音频生成"
- [ ] App A 的 System Prompt 配置完成，流式调用可返回引导词文本
- [ ] App B 的 System Prompt 配置完成，blocking 调用可返回标准 JSON 参数
- [ ] 已获取两个应用的 API Key 并记录
- [ ] 通过 `curl` 验证两个应用 API 均可正常访问

---

## 关联文档

- `docs/tech/tech-spec.md` 第 5 章
- `docs/prd/meditation-guide-words-prd.md` 第 6 章

---

## 风险备注

- Windows Docker Desktop 默认挂载到 WSL2，路径兼容性需注意。建议使用 `D:/project/github/dify` 绝对路径启动。
- Dify 首次启动镜像较大，网络不稳定时可能失败，需重试或配置镜像加速。
- App B 输出 JSON 不稳定时，可在 System Prompt 中增加示例（few-shot）提升一致性。
