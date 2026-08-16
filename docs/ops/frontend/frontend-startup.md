# 前端启动与运维指南

## 环境要求

| 依赖 | 版本要求 | 说明 |
|---|---|---|
| Node.js | ≥ 20.19（Vite 8 要求，本机为 v24.18.0） | 通过 `node -v` 确认 |
| npm | 随 Node 附带（本机 11.16.0） | 包管理器 |
| 磁盘空间 | ≥ 500MB | 含 `node_modules` 依赖体积 |

> 前端与后端是**两个独立进程**，需分别启动。前端开发服务器默认端口 `5173`，通过 Vite 代理把 `/api` 转发到后端 `8000`。

---

## 首次启动

### 1. 安装依赖

```powershell
cd C:\projects\apps\meditation-guide-words\frontend
npm install
```

- 生成 `node_modules/` 与 `package-lock.json`
- 首次安装约 1~3 分钟
- 若依赖有变更（新任务新增组件/库），重复执行本步即可增量更新

### 2. 启动前端开发服务器

```powershell
npm run dev
```

启动后终端显示：

```
  VITE v8.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

### 3. 验证

浏览器访问 `http://localhost:5173`，预期：
- 左侧边栏显示"冥想音频工作台"
- 顶栏右侧 `⚙️` 按钮为禁用态（占位，T8 开放）
- 两个工作区可切换

> 前端必须与后端（`http://localhost:8000`）同时运行，否则对话/音频功能不可用（代理报 500）。

---

## 完整启动（后端 + Worker + 前端）

```powershell
# 终端 1：后端（先启动，确保建表）
cd C:\projects\apps\meditation-guide-words\backend
uv run uvicorn app.main:app --port 8000

# 终端 2：音频 Worker（仅生成音频时需要）
cd C:\projects\apps\meditation-guide-words\backend
uv run python -m app.services.audio_worker

# 终端 3：前端
cd C:\projects\apps\meditation-guide-words\frontend
npm run dev
```

> 后端/Worker 的启动细节见 `docs/ops/backend/backend-startup.md` 与 `docs/ops/t5-tts-operations.md`。

---

## 后续日常启动

依赖无变化时跳过安装，直接：

```powershell
cd C:\projects\apps\meditation-guide-words\frontend
npm run dev
```

依赖有更新时先执行：

```powershell
cd C:\projects\apps\meditation-guide-words\frontend
npm install
```

---

## 常用命令

| 命令 | 用途 |
|---|---|
| `npm run dev` | 启动开发服务器（热更新，端口 5173） |
| `npm run build` | 类型检查（tsc）+ 生产构建，产物在 `dist/` |
| `npm run preview` | 本地预览生产构建产物 |
| `npm run lint` | Biome 静态检查 `src/` |
| `npm run format` | Biome 格式化 `src/`（单引号 + 分号，tech-spec 12.1） |

**代码检查节奏**（提交前建议执行）：

```powershell
npm run lint        # 无错误
npm run format      # 无改动（或执行后重新检查）
npm run build       # tsc + vite 构建通过
```

---

## 目录结构（启动后）

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/         # Sidebar / Header / MainLayout
│   │   ├── ui/             # shadcn/ui 组件（button/select/textarea/...）
│   │   └── workspace/      # ScriptWorkspace / AudioWorkspace / TaskItem
│   ├── i18n/locales/       # zh.json / en.json 语言包
│   ├── services/           # API 封装（http/script/audioTask/dify）
│   ├── stores/             # Zustand 全局状态
│   ├── types/              # TS 类型
│   ├── utils/              # SSE 解析器等
│   ├── App.tsx / main.tsx / index.css
│   ├── vite.config.ts      # @ 别名 + /api 代理到 8000
│   ├── tailwind.config.js  # Tailwind v3 配置
│   ├── biome.json          # Biome 规范
│   └── tsconfig*.json
├── dist/                   # 生产构建产物（gitignore）
└── package.json
```

---

## 常见问题

### Q1：`npm run dev` 报端口被占用 / 端口自动变化

```powershell
# 查看占用 5173 的进程并结束
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

或强制固定端口启动：

```powershell
npm run dev -- --port 5173 --strictPort
```

### Q2：页面打开但接口报 500 / 连接失败

- 确认后端已启动：`curl http://localhost:8000/api/health` → `{"status":"ok"}`
- 确认代理配置：`frontend/vite.config.ts` 中 `/api` → `http://localhost:8000`

### Q3：`npm install` 卡住或网络超时

- 换 npm 镜像源（临时）：
  ```powershell
  npm install --registry=https://registry.npmmirror.com
  ```
- 或全局设置镜像后重装

### Q4：`biome` / 构建报 Node 版本过低

- Vite 8 要求 Node ≥ 20.19，本机 v24.18.0 满足；如使用旧版本请升级 Node

### Q5：改了样式没生效

- 开发服务器热更新通常即时生效；若修改了 `tailwind.config.js` 或 `index.css`，Vite 会自动重启相关模块
- 确认类名在 `content` 覆盖范围内（`./src/**/*.{ts,tsx}`）

### Q6：shadcn 组件新增

```powershell
cd C:\projects\apps\meditation-guide-words\frontend
npx shadcn@2.3.0 add <组件名> -y
```

> 注意：官方最新 CLI（shadcn@4.x）init 在当前工程存在兼容问题，本项目固定使用 `shadcn@2.3.0`（详见 T6 任务文档）。

---

## 相关文档

- [T6 任务文档](../../task/06-frontend-workspace1.md)
- [后端启动与运维指南](../backend/backend-startup.md)
- [T5 操作文档（TTS 凭证）](../t5-tts-operations.md)
- [T6+T7 前端统一验收测试](../../test/06-07-frontend-acceptance.md)
