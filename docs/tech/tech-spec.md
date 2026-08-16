# 冥想音频工作台 — 技术规范文档

## 1. 目标与边界

### 1.1 文档目标
本文档固化冥想音频工作台的技术边界、架构设计、接口约定与开发规范，作为后续编码、联调与部署的依据。

### 1.2 适用范围
- 前端：React + TypeScript 单页应用
- 后端：Python FastAPI 轻量服务
- 智能体：Dify 开源版（外部独立部署）
- 数据：SQLite 本地存储
- 部署：本地运行，单用户无登录

### 1.3 不在本期范围内的内容
- 背景音乐合成人声（V1.x 扩展）
- 多租户、用户注册登录体系
- 公网 SaaS 部署
- 桌面客户端打包（Electron/Tauri）
- 商业化付费、配额体系
- 云端对象存储

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web 前端                                │
│              React 18 + TypeScript + shadcn/ui                  │
│  ┌─────────────┐         ┌─────────────┐                       │
│  │  工作区 1    │         │  工作区 2    │                       │
│  │ 引导词对话  │  ─────→ │ 音频生成对话 │                       │
│  └─────────────┘         └─────────────┘                       │
│                                                                 │
│  Zustand（状态） + react-i18next（多语言） + Biome（规范）       │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API / SSE
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI 后端                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ 设置管理     │  │ 引导词 CRUD │  │ 音频任务管理             │ │
│  │ /settings   │  │ /scripts    │  │ /audio-tasks            │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Dify 代理    │  │ TTS 适配层   │  │ Worker 进程             │ │
│  │ 流式包装 SSE │  │ 火山/阿里云  │  │ 异步音频生成             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
│  SQLAlchemy 2.0 + SQLite + Ruff                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │ Dify API
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              Dify 开源版（外部独立部署）                         │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │ Chat App：引导词生成 │  │ Chat App：音频生成              │  │
│  │ /chat-messages      │  │ /chat-messages                  │  │
│  │ System Prompt + LLM │  │ System Prompt → TTS 参数解析    │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
│                                                                 │
│  部署路径示例：D:\project\github\dify                            │
│  多个本地项目可共享同一 Dify 实例，按应用隔离                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 技术栈与版本

| 层级 | 技术/工具 | 版本/说明 |
|---|---|---|
| 智能体框架 | Dify 开源版 | 以最新稳定 tag 为准，建议锁定 tag |
| 前端框架 | React | ^18.x |
| 前端语言 | TypeScript | ^5.x |
| 前端构建 | Vite | ^5.x |
| UI 组件库 | shadcn/ui | 基于 Radix UI + Tailwind CSS |
| 状态管理 | Zustand | ^4.x |
| 国际化 | react-i18next | ^14.x |
| 前端规范 | Biome | 格式化 + Lint |
| 后端框架 | FastAPI | ^0.111.x |
| 后端语言 | Python | ^3.11 |
| 后端依赖管理 | uv | 现代化 Python 包管理 |
| ORM | SQLAlchemy | ^2.x |
| 数据库 | SQLite | 本地文件 |
| 异步任务 | asyncio + 独立 worker | 无 Redis/Celery |
| 后端规范 | Ruff | Lint + 格式化 |
| 测试 | pytest | 后端接口单元测试 |
| 容器 | Docker + Docker Compose | 仅用于 Dify |

---

## 4. 目录结构

```
meditation-guide-words/
├── backend/                        # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 应用入口
│   │   ├── config.py               # 配置读取
│   │   ├── db.py                   # SQLAlchemy engine/session
│   │   ├── models/                 # ORM 模型
│   │   │   ├── script.py
│   │   │   ├── audio_task.py
│   │   │   └── setting.py
│   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── script.py
│   │   │   ├── audio_task.py
│   │   │   └── setting.py
│   │   ├── routers/                # API 路由
│   │   │   ├── settings.py
│   │   │   ├── scripts.py
│   │   │   ├── audio_tasks.py
│   │   │   └── dify_proxy.py
│   │   ├── services/               # 业务逻辑
│   │   │   ├── dify_service.py
│   │   │   ├── tts_service.py
│   │   │   └── audio_worker.py
│   │   └── utils/                  # 工具函数
│   ├── tests/                      # pytest 测试
│   ├── pyproject.toml
│   └── .python-version
│
├── frontend/                       # React 前端
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Header.tsx
│   │   │   ├── workspace/
│   │   │   │   ├── ScriptWorkspace.tsx
│   │   │   │   ├── AudioWorkspace.tsx
│   │   │   │   └── ChatPanel.tsx
│   │   │   └── settings/
│   │   │       ├── SettingsDialog.tsx
│   │   │       ├── LLMSettings.tsx
│   │   │       └── TTSSettings.tsx
│   │   ├── hooks/                  # 自定义 hooks
│   │   ├── stores/                 # Zustand stores
│   │   ├── services/               # API 调用封装
│   │   ├── locales/                # i18n 语言包
│   │   │   ├── zh.json
│   │   │   └── en.json
│   │   └── types/                  # TypeScript 类型
│   ├── package.json
│   ├── biome.json
│   └── tailwind.config.js
│
├── docs/
│   ├── prd/
│   │   └── meditation-guide-words-prd.md
│   └── tech/
│       └── tech-spec.md            # 本文档
│
├── data/                           # 运行时数据（gitignore）
│   ├── meditation.db               # SQLite 数据库
│   └── audio/                      # 生成音频文件
│
├── scripts/                        # 启动/工具脚本
│   ├── start.bat                   # Windows 一键启动
│   └── start.sh                    # macOS/Linux 一键启动
│
├── .gitignore
└── README.md
```

---

## 5. Dify 部署与集成

### 5.1 外部独立部署
Dify 部署在独立于本项目的目录，例如：
```
D:/project/github/dify/
```
通过 Docker Compose 启动，多个本地项目可共享同一 Dify 实例。

### 5.2 应用规划
在 Dify 中创建两个 Chat 应用：

| 应用 | Dify 应用名建议 | 用途 |
|---|---|---|
| App A | `meditation-script-gen` | 工作区 1：自然语言对话生成冥想引导词 |
| App B | `meditation-audio-gen` | 量化语义停顿与声音描述，输出供应商无关 `render_plan` |

### 5.3 配置项
后端 `settings` 表中保存：
- `dify_base_url`：Dify API 地址，如 `http://localhost/v1`
- `dify_script_app_key`：App A 的 API Key
- `dify_audio_app_key`：App B 的 API Key

### 5.4 调用方式
前端不直接请求 Dify，所有 Dify 请求经过 FastAPI `/api/dify/*` 代理：
- 后端读取本地保存的 Dify 配置
- 将 Dify 返回的流式 chunk 包装为 SSE 返回前端
- 统一处理错误、日志、格式转换

---

## 6. 前后端接口约定

### 6.1 基础约定
- 基础路径：`/api`
- 请求/响应格式：JSON
- 流式响应：`Content-Type: text/event-stream`
- 错误格式：
```json
{
  "detail": "错误描述"
}
```

### 6.2 设置接口

#### GET `/api/settings`
返回当前全部设置。

#### POST `/api/settings`
保存设置。

#### POST `/api/settings/test-llm`
测试 LLM 连接。

#### POST `/api/settings/test-tts`
测试 TTS 连接。

### 6.3 引导词接口

#### GET `/api/scripts`
列出所有引导词，支持分页。

#### POST `/api/scripts`
保存引导词。结构化脚本提交 `script_plan`，服务端根据 blocks 生成纯文本 `content`；旧格式仍可只提交 `content`。

#### GET `/api/scripts/{id}`
获取单条引导词。

#### PUT `/api/scripts/{id}`
更新引导词。

#### DELETE `/api/scripts/{id}`
删除引导词。

### 6.4 音频任务接口

#### POST `/api/audio-tasks`
提交音频生成任务。
请求体：
```json
{
  "script_id": 1,
  "voice_prompt": "温柔女声，语速慢，正念风格"
}
```
响应：
```json
{
  "id": 1,
  "status": "pending"
}
```

#### GET `/api/audio-tasks`
列出任务列表。

#### GET `/api/audio-tasks/{id}`
获取任务状态。

#### GET `/api/audio-tasks/{id}/download`
下载音频文件。

#### POST `/api/audio-tasks/{id}/retry`
重试失败任务。

### 6.5 Dify 代理接口

#### POST `/api/dify/script/chat`
工作区 1 对话，返回 SSE。

#### POST `/api/dify/audio/chat`
工作区 2 对话，返回 SSE。

### 6.6 音频编排预览接口

#### GET `/api/audio-render-plans/pause-profiles`
返回版本化的轻柔、标准、深度停顿档案。

#### POST `/api/audio-render-plans/preview`
读取结构化 Script，调用 App B，强校验并标准化 `render_plan`，返回 `zh_v1` 预计时长；不创建 AudioTask，不调用 TTS。

---

## 7. 数据流详细说明

### 7.1 工作区 1：生成引导词
```
用户输入 → 前端 ChatPanel
              ↓
         POST /api/dify/script/chat
              ↓
         FastAPI 代理 → Dify App A
              ↓
         Dify LLM 流式输出完整 JSON
              ↓
         FastAPI SSE → 前端
              ↓
         完整 JSON 校验成功后保存 script_plan → POST /api/scripts
              ↓
         SQLite scripts 表
```

### 7.2 工作区 2：生成音频
```
用户选择 Script + 输入声音提示词
              ↓
         POST /api/audio-tasks
              ↓
         FastAPI 创建任务（status=pending）
              ↓
         Worker 进程拉取任务
              ↓
         调用 Dify App B 解析声音提示词为 TTS 参数 JSON
              ↓
         调用 FastAPI TTS 适配层（火山/阿里云）
              ↓
         音频文件写入 data/audio/{task_id}.mp3
              ↓
         更新任务状态 status=completed + file_path
              ↓
         前端轮询 /api/audio-tasks/{id} 或长轮询获取状态
              ↓
         播放 / 下载音频
```

---

## 8. 数据模型

### 8.1 Script（引导词）
```python
class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    content: Mapped[str]
    script_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    session_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)
```

### 8.2 AudioTask（音频任务）
```python
class AudioTask(Base):
    __tablename__ = "audio_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"))
    voice_prompt: Mapped[str]
    tts_params: Mapped[dict | None]  # JSON
    status: Mapped[str]  # pending / processing / completed / failed
    file_path: Mapped[str | None]
    error_msg: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    completed_at: Mapped[datetime | None]
```

### 8.3 Setting（应用设置）
```python
class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1, autoincrement=False)
    llm_config: Mapped[dict]
    tts_config: Mapped[dict]
    dify_config: Mapped[dict]
    general_config: Mapped[dict]
    updated_at: Mapped[datetime] = mapped_column(default=utc_now)
```

> 时间字段统一使用 `app.utils.time_utils.utc_now()`，替代已弃用的 `datetime.utcnow`。

---

## 9. 异步任务设计

### 9.1 架构
- 不引入 Redis/Celery，使用 SQLite 作为任务队列持久化。
- 独立 worker 进程启动一个事件循环，轮询 `audio_tasks` 表中 `status='pending'` 的任务。
- 默认并发数为 2，通过 `asyncio.Semaphore` 控制。

### 9.2 任务状态流转
```
pending → processing → completed
   ↓           ↓
  retry      failed
```

### 9.3 Worker 启动方式
```bash
uv run python -m app.services.audio_worker
```
一键启动脚本中同时启动 FastAPI 与 Worker：
```bash
uv run fastapi dev app/main.py &
uv run python -m app.services.audio_worker &
npm run dev --prefix frontend &
```

### 9.4 失败重试
- 任务失败自动重试 1 次。
- 仍失败则 `status='failed'`，`error_msg` 记录原因。
- 用户可通过界面点击重试。

---

## 10. TTS 适配层

### 10.1 设计原则
- App A 输出正文与语义停顿；App B 只输出标准化、供应商无关的 `render_plan`。
- 后端复算停顿档案，校验 segment 文本、顺序、策略、音色及数值范围，不信任任意 JSON。
- 实际 TTS 调用统一走 FastAPI 后端，避免 API Key 暴露在前端或 Dify。
- 适配层屏蔽火山引擎、阿里云等供应商接口差异。

### 10.2 标准 TTS 请求 Schema
```json
{
  "text": "引导词正文",
  "voice_id": "zh-CN-XiaoxiaoNeural",
  "speed": 0.9,
  "volume": 1.0,
  "emotion": "gentle",
  "output_format": "mp3"
}
```

### 10.3 供应商适配
- `TTSServiceVolcano`：火山引擎 TTS
- `TTSServiceAliyun`：阿里云 TTS
- 工厂函数根据 `tts_config.provider` 创建对应实例。

### 10.4 音色列表
- MVP 阶段音色 ID 由用户在设置页手动填写。
- V1.x 可扩展为后端从供应商 API 拉取音色列表供选择。

---

## 11. 开发与部署

### 11.1 环境准备
- Python 3.11+
- Node.js 18+
- uv
- Docker + Docker Compose（用于 Dify）

### 11.2 后端初始化
```bash
cd backend
uv sync
uv run alembic upgrade head  # 如引入迁移
uv run fastapi dev app/main.py
```

### 11.3 前端初始化
```bash
cd frontend
npm install
npm run dev
```

### 11.4 Dify 启动
```bash
cd D:/project/github/dify
docker-compose up -d
```

### 11.5 一键启动脚本
`scripts/start.bat`（Windows）和 `scripts/start.sh`（macOS/Linux）负责：
1. 检查 Dify 是否运行，未运行则提示或启动
2. 启动 FastAPI 后端
3. 启动音频 Worker
4. 启动前端开发服务器

---

## 12. 代码规范

### 12.1 前端
- 使用 Biome 进行格式化和 Lint
- 配置 `biome.json`，规则：
  - 2 空格缩进
  - 单引号
  - 行尾分号
  - 最大行宽 100
- 类型安全：禁止 `any`

### 12.2 后端
- 使用 Ruff 进行格式化和 Lint
- `pyproject.toml` 配置 Ruff 规则：
  - `E`, `F`, `I`, `N`, `W`, `UP`, `B`
- 类型注解：尽可能使用 `Mapped[...]` 和 Pydantic 严格模型
- 函数长度控制在 60 行以内

### 12.3 命名约定
- 前端组件：PascalCase
- 前端 hooks/services：camelCase
- 后端模块/函数：snake_case
- 数据库表/字段：snake_case

---

## 13. 测试策略

### 13.1 范围
本期仅对后端核心接口编写单元测试，覆盖：
- 设置 CRUD
- 引导词 CRUD
- 音频任务创建与状态流转
- Dify 代理接口错误处理

### 13.2 工具
- `pytest`
- `pytest-asyncio`
- `httpx`（测试 FastAPI TestClient）
- SQLite in-memory 测试数据库

### 13.3 测试命令
```bash
cd backend
uv run pytest
```

---

## 14. 配置项清单

### 14.1 后端环境变量（`.env`，可选）
| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATABASE_URL` | SQLite 路径 | `sqlite:///./data/meditation.db` |
| `AUDIO_OUTPUT_DIR` | 音频输出目录 | `./data/audio` |
| `DIFY_BASE_URL` | Dify API 地址 | `http://localhost/v1` |
| `WORKER_CONCURRENCY` | Worker 并发数 | 2 |

### 14.2 前端运行时配置
- 后端 API 地址：`http://localhost:8000`
- 通过 `.env` 或 `config.ts` 配置

### 14.3 设置页持久化配置
全部保存到 SQLite `settings` 表：
- `llm_config`：provider、base_url、api_key、model、temperature、max_tokens
- `tts_config`：provider、api_key、secret_key、voice_id、speed、volume、format
- `dify_config`：base_url、script_app_key、audio_app_key
- `general_config`：language、theme、audio_output_dir

---

## 15. 安全与约束

### 15.1 API Key 存储
- LLM、TTS、Dify 的 API Key 均以明文形式存储在本地 SQLite。
- 适用于本地个人工具，后续如考虑共享/上线应升级为加密存储。

### 15.2 访问控制
- 本地单用户，无登录体系。
- FastAPI 与前端均监听 `localhost`，不对外暴露。

### 15.3 文件安全
- 音频文件仅保存在本地 `data/audio`。
- 后端静态文件接口仅提供音频下载，不做目录遍历。

---

## 16. 风险与兜底方案

| 风险 | 影响 | 兜底方案 |
|---|---|---|
| Dify 外部部署路径用户未准备 | 高 | 启动脚本检测并提供一键 clone/启动 Dify 的引导 |
| TTS 供应商接口变更 | 中 | 适配层独立封装，变更只改一个文件 |
| 长音频合成耗时过长 | 中 | 异步队列 + 任务状态持久化，允许后台运行 |
| SQLite 并发写锁 | 低 | Worker 单进程 + 协程，写操作串行化 |
| 用户未配置 API Key | 中 | 设置页醒目提示，接口返回友好错误 |
| Dify 应用未创建 | 高 | README 提供初始化步骤，考虑初始化脚本 |

---

## 17. 附录：决策确认来源

本文档技术决策基于 PRD 阶段确认清单：

| 编号 | 决策项 | 选型 |
|---|---|---|
| 1 | Dify 部署方式 | 外部独立部署到 `D:\project\github\dify`，多项目共享 |
| 2 | Dify 应用组织 | 两个独立 Chat 应用 |
| 3 | 前端与 Dify 集成 | 前端 → FastAPI 代理 → Dify API |
| 4 | 流式协议 | FastAPI 包装成 SSE |
| 5 | 前端状态 | Zustand |
| 6 | UI 组件库 | shadcn/ui |
| 7 | 后端 ORM | SQLAlchemy 2.0 |
| 8 | 异步任务 | SQLite 状态 + 独立 worker |
| 9 | TTS 适配 | FastAPI 标准 TTS API，Dify 调用 |
| 10 | 音频存储 | 本地文件系统 |
| 11 | API Key 存储 | 明文 SQLite |
| 12 | 开发环境 | uv + npm |
| 13 | 部署形态 | 纯 Web 本地访问 |
| 14 | 国际化 | react-i18next |
| 15 | 代码规范 | Biome + Ruff |
| 16 | 测试 | 后端核心接口测试 |
| 17 | Git 分支 | main 单分支 |

---

文档版本：v1.0
创建时间：2026-08-05
