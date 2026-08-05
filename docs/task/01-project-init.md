<!-- 状态：✅ 验收通过（2026-08-05）
     初始提交：f2350d0 chore: init project structure and scripts
     已推送至远程：github.com/taohuayuanzen/meditation-guide-words（main 分支） -->

# T1：项目初始化与基础设施搭建

## 任务目标

搭建 `meditation-guide-words` 项目的基础骨架，创建清晰的目录结构、初始化 Git 仓库、编写 README 和启动脚本框架，为后续前后端、Dify 集成开发提供统一入口。

**预计耗时**：0.5 ~ 1 天

---

## 前置依赖

无。

---

## 详细步骤

### 1.1 创建项目根目录结构

在项目根目录 `D:/project/apps/meditation-guide-words` 下创建以下目录：

```
meditation-guide-words/
├── backend/              # FastAPI 后端源码
├── frontend/             # React 前端源码
├── scripts/              # 启动/工具脚本
├── data/                 # 运行时数据（gitignore）
├── docs/                 # 已存在，包含 prd/ 与 tech/
│   ├── prd/
│   └── tech/
├── .gitignore
└── README.md
```

创建目录命令：
```bash
mkdir -p backend/app frontend/src scripts data/audio
```

### 1.2 初始化 Git 仓库

```bash
git init
```

### 1.3 编写 `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.env

# Node
node_modules/
dist/
build/
*.log

# Data
data/*
!data/.gitkeep

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

> 注意：保留 `data/.gitkeep` 让目录存在但忽略运行时文件。

### 1.4 创建 `data/.gitkeep`

```bash
touch data/.gitkeep
```

### 1.5 编写 `README.md`

README 至少包含：
- 项目简介
- 核心功能（工作区 1 / 工作区 2）
- 技术栈
- 快速开始（环境要求、安装步骤、启动方式）
- 项目结构说明
- 相关文档链接（`docs/prd/`、`docs/tech/`、`docs/task/`）

### 1.6 创建启动脚本框架

#### `scripts/start.sh`（macOS/Linux）

```bash
#!/usr/bin/env bash
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
echo "Project root: $ROOT"

# 1. 检查 Dify 是否运行（后续 T3 完善）
echo "[TODO] 检查 Dify 运行状态"

# 2. 启动后端（后台）
echo "[TODO] 启动 FastAPI 后端"

# 3. 启动音频 Worker（后台）
echo "[TODO] 启动音频 Worker"

# 4. 启动前端
echo "[TODO] 启动前端"

wait
```

#### `scripts/start.bat`（Windows）

```bat
@echo off
setlocal
set ROOT=%~dp0..
echo Project root: %ROOT%

echo [TODO] 检查 Dify 运行状态
echo [TODO] 启动 FastAPI 后端
echo [TODO] 启动音频 Worker
echo [TODO] 启动前端

pause
```

> 本期只搭框架，具体命令在 T8 完善。

### 1.7 提交初始版本

```bash
git add .
git commit -m "chore: init project structure and scripts"
```

---

## 关键设计点

- `data/` 目录用于存放 SQLite 数据库和音频文件，必须被 `.gitignore` 忽略，避免把本地数据提交到仓库。
- 启动脚本将来需要跨项目启动外部 Dify（位于 `D:/project/github/dify`），脚本中应使用绝对路径或环境变量配置。
- README 是项目入口文档，应链接到 PRD、Tech Spec 和所有 Task 文档。

---

## 验收标准

- [ ] 项目目录结构与本文档一致
- [ ] `.gitignore` 正确忽略 `data/`、`node_modules/`、`__pycache__/` 等
- [ ] `README.md` 包含项目简介、技术栈、快速开始、文档链接
- [ ] `scripts/start.sh` 和 `scripts/start.bat` 存在且可执行
- [ ] 初始 Git 提交成功

---

## 关联文档

- `docs/prd/meditation-guide-words-prd.md`：项目背景与功能需求
- `docs/tech/tech-spec.md`：目录结构、技术栈、部署目标

---

## 风险备注

- Windows 下 Bash 脚本与 Bat 脚本需分别维护，注意路径分隔符和后台进程启动方式差异。
- 如果后续使用 `uv` 或 `npm`，启动脚本需要检测命令是否存在并给出友好提示。
