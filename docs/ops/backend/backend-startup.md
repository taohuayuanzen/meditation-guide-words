# 后端启动与运维指南

## 环境要求

| 依赖 | 版本要求 | 说明 |
|---|---|---|
| Python | ≥ 3.11 | 建议通过 `uv` 管理解释器 |
| uv | 最新稳定版 | Python 包管理与虚拟环境 |
| 磁盘空间 | ≥ 500MB | 含 .venv 依赖包空间 |

---

## 首次启动

### 1. 安装依赖

```bash
cd backend
uv sync
```

此命令会：
- 创建 `.venv` 虚拟环境
- 安装 `pyproject.toml` 中声明的所有运行时依赖与开发依赖（含 Ruff）

### 2.（可选）配置环境变量

在 `backend/.env` 中按需覆盖默认配置：

```env
DATABASE_URL=sqlite:///./data/meditation.db
AUDIO_OUTPUT_DIR=./data/audio
DIFY_BASE_URL=http://localhost/v1
WORKER_CONCURRENCY=2
```

所有配置项均有默认值，无 `.env` 文件也可正常启动。

### 3. 启动服务

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

> **注意**：启动命令必须在 `backend/` 目录下执行，数据库路径 `./data/meditation.db` 相对于启动目录解析。

### 4. 验证

```bash
curl http://localhost:8000/api/health
# → {"status":"ok"}
```

首次启动后会自动创建：
- `data/meditation.db` — SQLite 数据库文件
- `data/audio/` — 音频输出目录

---

## 后续日常启动

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

每天第一次启动时若依赖无变化，跳过安装直接运行即可。

依赖有更新时先执行：
```bash
cd backend
uv sync
```

---

## 启动流程详解

```
uvicorn app.main:app
  │
  ├─ lifespan 启动事件
  │   ├─ init_db()          # 创建 data/ 和 data/audio/ 目录
  │   └─ create_tables()    # 执行 Base.metadata.create_all
  │       └─ 导入 app.models  # 注册 Script / AudioTask / Setting
  │
  ├─ CORS 中间件注册          # 允许 localhost:5173
  └─ 路由注册
      └─ GET /api/health    # 健康检查
```

---

## 常见问题

### Q1：启动报 `ModuleNotFoundError: No module named 'app'`

**原因**：未在 `backend/` 目录下启动。

**解决**：先 `cd backend`，再执行 `uv run uvicorn app.main:app`。

### Q2：数据库文件 `data/meditation.db` 未生成

**原因**：启动命令未在 `backend/` 目录下执行，或 `data/` 目录无写入权限。

**解决**：确认在 `backend/` 下启动，检查磁盘权限。

### Q3：`ruff: command not found`

**原因**：Ruff 通过 `uv sync` 安装到 `.venv`，直接调用未加入 PATH。

**解决**：通过 `uv run ruff` 调用：
```bash
uv run ruff check .
uv run ruff format .
```

### Q4：表结构变更后需要重建数据库

当前 T2 阶段无迁移工具，需要手动重建：

```bash
rm data/meditation.db    # 删除旧数据库
# 重新启动服务，自动建表
uv run uvicorn app.main:app --port 8000
```

> 后续任务将引入 Alembic 数据库迁移。

### Q5：端口 8000 被占用

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS / Linux
lsof -ti:8000 | xargs kill -9
```

或更换端口：
```bash
uv run uvicorn app.main:app --reload --port 8001
```
> 注意：前端 CORS 配置需同步改为新端口。

---

## 目录结构（启动后）

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # pydantic-settings 配置
│   ├── db.py                 # SQLAlchemy engine / session / create_tables
│   ├── models/
│   │   ├── __init__.py       # 模型集中导入
│   │   ├── script.py         # Script（引导词）
│   │   ├── audio_task.py     # AudioTask（音频任务）
│   │   └── setting.py        # Setting（应用设置）
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── setting.py        # LLM / TTS / Dify / General 配置 Schema
│   └── utils/
│       ├── __init__.py
│       └── time_utils.py     # utc_now() 时间工具
├── tests/
│   └── __init__.py
├── data/                     # 运行时数据（gitignore）
│   ├── meditation.db         # SQLite 数据库
│   └── audio/                # 生成音频文件
├── pyproject.toml            # 项目配置 + Ruff 规则
├── uv.lock                   # 依赖锁定
└── .python-version
```

---

## 相关文档

- [T2 任务文档](../../task/02-backend-foundation.md)
- [技术规范 — 第 3、4、8、14 章](../../tech/tech-spec.md)
- [PRD — 第 4、5 章](../../prd/meditation-guide-words-prd.md)
