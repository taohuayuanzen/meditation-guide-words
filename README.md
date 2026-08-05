# 冥想引导词生成工具

本地运行的冥想引导词生成 Web 应用：通过自然语言对话生成冥想引导词，并根据声音提示词解析出 TTS 参数、生成音频。

## 核心功能

- **工作区 1：引导词生成** — 与 Dify 智能体对话，自然语言生成冥想引导词，可保存、编辑、管理引导词。
- **工作区 2：音频生成** — 选择引导词并输入声音提示词（如"温柔女声，语速慢"），异步生成 TTS 音频，支持播放与下载。

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + shadcn/ui + Zustand + react-i18next |
| 后端 | Python FastAPI + SQLAlchemy 2.0 + SQLite |
| 智能体 | Dify 开源版（外部独立部署） |
| 音频 | TTS 适配层（火山引擎 / 阿里云） |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- uv
- Docker + Docker Compose（用于启动 Dify）

### 安装与启动

> 说明：启动脚本当前为框架占位，具体启动命令将在后续任务（T8）完善。

1. **启动 Dify**（外部独立部署，如 `D:/project/github/dify`）
   ```bash
   cd D:/project/github/dify
   docker-compose up -d
   ```
2. **启动后端**
   ```bash
   cd backend
   uv sync
   uv run fastapi dev app/main.py
   ```
3. **启动前端**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. 访问 `http://localhost:5173`

也可直接运行 `scripts/start.bat`（Windows）或 `scripts/start.sh`（macOS/Linux）一键启动。

## 项目结构

```
meditation-guide-words/
├── backend/        # FastAPI 后端源码
├── frontend/       # React 前端源码
├── scripts/        # 启动/工具脚本
├── data/           # 运行时数据（gitignore）：SQLite 数据库、音频文件
├── docs/           # 项目文档
│   ├── prd/        # 产品需求文档
│   ├── tech/       # 技术规范文档
│   └── task/       # 分阶段任务文档
└── knowledge/      # 知识资料（当前为空）
```

## 相关文档

- [产品需求文档](docs/prd/meditation-guide-words-prd.md)
- [技术规范文档](docs/tech/tech-spec.md)
- [任务文档](docs/task/)
