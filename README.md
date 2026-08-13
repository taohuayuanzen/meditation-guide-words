# 冥想引导工作台

本地运行的冥想引导词生成 Web 应用：通过自然语言对话生成冥想引导词，并根据声音提示词解析出 TTS 参数、异步生成冥想音频，支持在线播放与下载。

## 核心功能

- **工作区 1：引导词生成** — 与 Dify 智能体对话，自然语言流式生成冥想引导词，支持多轮改写，一键保存到本地。
- **工作区 2：音频生成** — 选择已保存引导词，用自然语言描述声音风格（如"温柔女声，语速慢"），解析为 TTS 参数后异步合成，支持播放、下载与失败重试。
- **设置页** — 可视化配置 LLM、TTS、Dify、通用设置（语言/主题/音频目录），支持测试连接、中英文切换、深浅色主题。

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + shadcn/ui + Zustand + react-i18next + Biome |
| 后端 | Python FastAPI + SQLAlchemy 2.0 + SQLite + Ruff |
| 智能体 | Dify 开源版（外部独立部署，App A 引导词 / App B 音频参数解析） |
| 音频 | TTS 适配层（火山引擎 / 阿里云 DashScope）+ 异步 Worker（SQLite 任务队列） |

## 环境要求

- Python 3.11+、uv
- Node.js 20.19+（Vite 8 要求）
- Docker + Docker Compose（用于启动 Dify）
- 真实账号/凭证：DeepSeek（或其他 OpenAI 兼容 LLM）、火山引擎或阿里云 TTS

## 快速开始

### 方式一：一键脚本

```bash
# Windows
.\start.ps1

# 首次启动（安装/同步依赖）
.\start.ps1 -Install

# 也可双击或命令行调用包装器
start.bat

# macOS / Linux
# 请按下方“手动启动”执行
```

脚本会：检查并尝试启动 Dify → 校验后端、Worker、前端并仅启动未运行的服务。后端、Worker、前端分别在独立 PowerShell 窗口中运行。若 Dify 已运行则直接复用；仅当 Dify 未就绪且无法从本地目录启动时失败退出。可通过环境变量 `DIFY_DIR` 指定 Dify 根目录，例如 `C:\projects\github\dify\dify-1.16.1`；其下须存在 `docker\\docker-compose.yml` 或 `docker\\docker-compose.yaml`。

若 Dify 位于 `C:\projects\github\dify\dify-1.16.1`，可在 PowerShell 中设置用户级环境变量：

```powershell
[Environment]::SetEnvironmentVariable(
  'DIFY_DIR',
  'C:\projects\github\dify\dify-1.16.1',
  'User'
)
```

设置后请重新打开终端或资源管理器，再运行 `start.bat` 或 `./start.ps1`。

### 方式二：手动启动

```powershell
# 终端 1：后端
cd backend
uv sync
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# 终端 2：音频 Worker（生成音频时需要）
cd backend
.\.venv\Scripts\python.exe -m app.services.audio_worker

# 终端 3：前端
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

> 详细说明见 `docs/ops/backend/backend-startup.md`、`docs/ops/frontend/frontend-startup.md`。

## 首次使用配置

启动后在页面右上角点击 **设置 ⚙️**，按标签页配置：

1. **大模型（LLM）**：供应商、API Base URL、API Key、模型名称，点击"测试连接"验证。
2. **语音合成（TTS）**：选择火山引擎或阿里云，填写 API Key / Secret Key / App ID / 音色 ID 等，点击"测试合成"验证。
3. **Dify**：填写 Dify 地址与两个应用的 API Key（App A / App B）。
4. **通用**：语言（中/英）、主题（浅色/深色）、音频保存目录。
5. 点击"保存全部"。

> TTS 凭证获取与联调步骤见 `docs/ops/t5-tts-operations.md`；Dify 部署与 App 创建见 `docs/ops/t3-operations.md`。

## 项目结构

```
meditation-guide-words/
├── backend/        # FastAPI 后端源码 + pytest 测试
├── frontend/       # React 前端源码
├── scripts/        # 一键启动脚本（start.bat / start.sh）
├── data/           # 运行时数据（gitignore）：SQLite 数据库、音频文件
├── docs/           # 项目文档
│   ├── prd/        # 产品需求文档
│   ├── tech/       # 技术规范文档
│   ├── task/       # 分阶段任务文档
│   ├── ops/        # 运维操作文档
│   └── test/       # 验收测试用例
└── knowledge/      # 知识资料
```

## 开发命令

```bash
# 后端测试与检查
cd backend
uv run pytest          # 单元测试
uv run ruff check .    # Lint
uv run ruff format .   # 格式化

# 前端检查与构建
cd frontend
npm run lint           # Biome Lint
npm run format         # Biome 格式化
npm run build          # 类型检查 + 生产构建
```

## 常见问题

| 问题 | 处理 |
|---|---|
| 页面对话返回 `[HTTP 502]` | 后端未启动：`cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` |
| 音频任务一直 `pending` | Worker 未启动：`.\.venv\Scripts\python.exe -m app.services.audio_worker` |
| 任务 `failed`（`no such column: retry_count`） | 数据库需重建：删除 `backend/data/meditation.db` 后重启后端 |
| `test-tts` 失败 | 按 `docs/ops/t5-tts-operations.md` 核对凭证（火山需 AK/SK + AppID） |
| Dify 相关接口报"配置未完成" | 在设置页配置 Dify 两个 App 的 API Key |

## 相关文档

- [产品需求文档](docs/prd/meditation-guide-words-prd.md)
- [技术规范文档](docs/tech/tech-spec.md)
- [任务文档](docs/task/)
- [运维文档](docs/ops/)
- [验收测试用例](docs/test/)
