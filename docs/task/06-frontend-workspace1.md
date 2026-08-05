# T6：前端基础与工作区 1 实现

## 任务目标

初始化 React + TypeScript + shadcn/ui 前端项目，搭建左侧边栏布局、实现工作区 1（引导词生成）的对话界面、流式 SSE 渲染和引导词保存功能。

**预计耗时**：2 ~ 2.5 天

---

## 前置依赖

- T1 完成（项目目录结构已创建）
- T4 完成（后端 API 已就绪，特别是 `/api/dify/script/chat` 和 `/api/scripts`）

---

## 详细步骤

### 6.1 初始化前端项目

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

### 6.2 安装依赖

```bash
npm install zustand react-i18next i18next i18next-browser-languagedetector
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install -D @biomejs/biome
```

### 6.3 安装 shadcn/ui

```bash
npx shadcn-ui@latest init
```

安装所需组件：

```bash
npx shadcn-ui@latest add button input textarea scroll-area sheet dialog
```

### 6.4 配置 Tailwind

`frontend/tailwind.config.js`：

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [require("tailwindcss-animate")],
}
```

`frontend/src/index.css`：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 6.5 配置 Biome

`frontend/biome.json`：

```json
{
  "$schema": "https://biomejs.dev/schemas/1.8.3/schema.json",
  "organizeImports": {
    "enabled": true
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true
    }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  }
}
```

`frontend/package.json` 添加脚本：

```json
{
  "scripts": {
    "lint": "biome lint ./src",
    "format": "biome format --write ./src"
  }
}
```

### 6.6 配置 i18n

`frontend/src/i18n/index.ts`：

```ts
import i18n from "i18next"
import { initReactI18next } from "react-i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import zh from "./locales/zh.json"
import en from "./locales/en.json"

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      zh: { translation: zh },
      en: { translation: en },
    },
    fallbackLng: "zh",
    interpolation: { escapeValue: false },
  })

export default i18n
```

`frontend/src/i18n/locales/zh.json`：

```json
{
  "workspace": {
    "script": "引导词生成",
    "audio": "音频生成"
  },
  "chat": {
    "placeholder": "输入你的需求...",
    "send": "发送",
    "save": "保存引导词"
  },
  "settings": {
    "title": "设置"
  }
}
```

### 6.7 创建 Zustand Store

`frontend/src/stores/appStore.ts`：

```ts
import { create } from "zustand"

interface AppState {
  currentWorkspace: "script" | "audio"
  setWorkspace: (workspace: "script" | "audio") => void
}

export const useAppStore = create<AppState>((set) => ({
  currentWorkspace: "script",
  setWorkspace: (workspace) => set({ currentWorkspace: workspace }),
}))
```

### 6.8 布局组件

#### 左侧边栏 `frontend/src/components/layout/Sidebar.tsx`

```tsx
import { useAppStore } from "@/stores/appStore"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"

export function Sidebar() {
  const { currentWorkspace, setWorkspace } = useAppStore()
  const { t } = useTranslation()

  return (
    <aside className="w-64 h-screen border-r flex flex-col p-4">
      <h1 className="text-xl font-bold mb-8">冥想引导词</h1>
      <nav className="flex flex-col gap-2">
        <Button
          variant={currentWorkspace === "script" ? "default" : "ghost"}
          onClick={() => setWorkspace("script")}
        >
          {t("workspace.script")}
        </Button>
        <Button
          variant={currentWorkspace === "audio" ? "default" : "ghost"}
          onClick={() => setWorkspace("audio")}
        >
          {t("workspace.audio")}
        </Button>
      </nav>
    </aside>
  )
}
```

#### 主布局 `frontend/src/components/layout/MainLayout.tsx`

```tsx
import { Sidebar } from "./Sidebar"
import { ScriptWorkspace } from "../workspace/ScriptWorkspace"
import { AudioWorkspace } from "../workspace/AudioWorkspace"
import { useAppStore } from "@/stores/appStore"

export function MainLayout() {
  const { currentWorkspace } = useAppStore()

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        {currentWorkspace === "script" ? <ScriptWorkspace /> : <AudioWorkspace />}
      </main>
    </div>
  )
}
```

### 6.9 工作区 1 界面

#### 线框描述

```
┌──────────────────────────────────────────────────────────────┐
│  引导词生成                                        [设置 ⚙️]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 用户：生成一段 10 分钟睡前冥想引导词                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ AI：现在，请找一个舒适的位置坐下或躺下...（流式输出）   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ [保存引导词]                                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  [输入框...                              ]         [发送]    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 实现 `frontend/src/components/workspace/ScriptWorkspace.tsx`

核心逻辑：
- 维护消息列表（user/assistant）
- 输入框发送消息到 `/api/dify/script/chat`
- 使用 `EventSource` 接收 SSE，实时追加 AI 回复
- 提供"保存引导词"按钮，调用 `/api/scripts` POST

```tsx
import { useState, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Message {
  role: "user" | "assistant"
  content: string
}

export function ScriptWorkspace() {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)

  const handleSend = async () => {
    if (!input.trim()) return

    const userMsg: Message = { role: "user", content: input }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setIsStreaming(true)

    const response = await fetch("/api/dify/script/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        inputs: {},
        query: input,
        response_mode: "streaming",
        conversation_id: "",
        user: "local-user",
      }),
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let assistantContent = ""

    setMessages((prev) => [...prev, { role: "assistant", content: "" }])

    while (reader) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      // TODO: 解析 Dify SSE 格式，提取有效文本
      assistantContent += chunk
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        return [...prev.slice(0, -1), { ...last, content: assistantContent }]
      })
    }

    setIsStreaming(false)
  }

  const handleSave = async () => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant")
    if (!lastAssistant) return

    await fetch("/api/scripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: `引导词 ${new Date().toLocaleString()}`,
        content: lastAssistant.content,
        session_id: "",
      }),
    })
  }

  return (
    <div className="flex flex-col h-full p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">{t("workspace.script")}</h2>
        <Button onClick={handleSave} disabled={isStreaming}>
          {t("chat.save")}
        </Button>
      </div>

      <ScrollArea className="flex-1 border rounded-lg p-4 mb-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`mb-4 p-3 rounded-lg ${
              msg.role === "user" ? "bg-blue-100 ml-auto max-w-[80%]" : "bg-gray-100 max-w-[80%]"
            }`}
          >
            {msg.content}
          </div>
        ))}
      </ScrollArea>

      <div className="flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t("chat.placeholder")}
          className="flex-1"
          rows={2}
        />
        <Button onClick={handleSend} disabled={isStreaming}>
          {t("chat.send")}
        </Button>
      </div>
    </div>
  )
}
```

### 6.10 Dify SSE 解析

Dify 的 SSE 每条消息格式大致如下：

```
data: {"event": "message", "answer": "..."}\n\n
```

需要在工具函数中解析：

`frontend/src/utils/sseParser.ts`：

```ts
export function parseDifySSEChunk(chunk: string): string {
  const lines = chunk.split("\n")
  let result = ""
  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = line.slice(6)
      try {
        const json = JSON.parse(data)
        if (json.event === "message" && json.answer) {
          result += json.answer
        }
      } catch {
        // 非 JSON 行忽略
      }
    }
  }
  return result
}
```

### 6.11 API 基础路径配置

`frontend/vite.config.ts` 配置代理：

```ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
})
```

### 6.12 入口文件

`frontend/src/main.tsx`：

```tsx
import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App.tsx"
import "./index.css"
import "./i18n"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

`frontend/src/App.tsx`：

```tsx
import { MainLayout } from "./components/layout/MainLayout"

function App() {
  return <MainLayout />
}

export default App
```

---

## 关键设计点

- 前端状态使用 Zustand，只保存全局状态（当前工作区、设置弹窗开关），聊天消息用本地 `useState`。
- SSE 使用 `fetch + ReadableStream`，不直接用 `EventSource`，因为需要 POST 请求体。
- Dify SSE 解析单独封装为工具函数，便于工作区 2 复用。
- shadcn/ui 组件按需安装，保持依赖精简。
- 保存引导词时自动生成标题（可用用户首句或时间戳）。

---

## 验收标准

- [ ] `npm run dev` 可启动前端，访问 `http://localhost:5173`
- [ ] 左侧边栏可在"引导词生成"和"音频生成"之间切换
- [ ] 工作区 1 可输入自然语言并发送
- [ ] 后端返回的 SSE 流式内容能在界面中逐字显示
- [ ] 多轮对话上下文可延续（Dify 自动维护 `conversation_id`）
- [ ] "保存引导词"按钮可将当前 AI 回复保存到后端，并可在工作区 2 引用
- [ ] Biome lint 和 format 无错误
- [ ] 中英文切换可在设置页实现（设置页在 T8，但 i18n 框架已就绪）

---

## 关联文档

- `docs/tech/tech-spec.md` 第 3、4、6、12 章
- `docs/prd/meditation-guide-words-prd.md` 第 4.2、4.4、8.1 章

---

## 风险备注

- shadcn/ui 初始化可能因 Tailwind 版本或配置问题失败，需按官方文档逐步执行。
- Dify SSE chunk 可能跨多个 JSON 对象，解析逻辑需要健壮性测试。
- 工作区 1 和工作区 2 的 Dify `conversation_id` 应独立维护，避免上下文串扰。

---

## 当前进度（2026-08-05 · 已完成）

### 已完成

- [x] `frontend/` 初始化（Vite + React 18 + TypeScript，`npm run dev` 可启动）
- [x] Tailwind v3.4 + PostCSS + `tailwindcss-animate` 配置完成
- [x] shadcn/ui 初始化（New York + zinc）+ 安装 button/input/textarea/scroll-area/sheet/dialog/select
- [x] Biome（单引号 + 分号，tech-spec 12.1）+ vite `@` 别名 + `/api` 代理到 `http://localhost:8000`
- [x] i18n（react-i18next + LanguageDetector），zh/en 语言包**全量**翻译
- [x] Zustand store + 布局（Sidebar / Header / MainLayout），工作区切换保持各工作区状态（均挂载 + `hidden` 切换）
- [x] 顶栏 `⚙️` 设置占位按钮（disabled，T8 接入）
- [x] 工作区 1：SSE 流式对话（健壮解析 `event:`/`data:`、跨帧缓冲、`message`/`agent_message`/`error` 事件）、多轮 `conversation_id` 回传、保存引导词（时间戳标题 + session_id）
- [x] `biome lint` / `biome format` 无错误；`tsc -b && vite build` 通过
- [x] 冒烟验证：`http://localhost:5173` 正常返回、`/api/health` 代理连通、模块编译无错

### 关键实现决策（已确认）

| 决策点 | 结论 |
|---|---|
| 技术栈版本 | Tailwind v3.4 + React 18，按任务文档 |
| 代码风格 | Biome 单引号 + 分号（tech-spec 12.1），任务文档示例代码被统一格式化 |
| 设置入口 | 顶栏放 `⚙️` 占位按钮，T8 实现弹窗 |
| 前端测试 | 不加前端单测；Biome 保证质量，验收走手动 E2E（见 `docs/test/`） |
| 语言包 | zh / en 全量翻译 |
| 工作区状态保持 | 两个工作区常驻挂载 + CSS `hidden` 切换，切换不丢会话（PRD 4.1） |

### 与文档差异 / 附带修改

- `shadcn-ui` 包名已废弃；`shadcn@4.16.1` init 存在 workspace 配置 bug，改用 **`shadcn@2.3.0`**（Tailwind v3 兼容）完成 init 与组件安装
- shadcn 生成的 CSS 变量为 `oklch`，`tailwind.config.js` 中颜色统一改为 `oklch(var(--...))`（否则 `hsl()` 包装会失效）；修复 shadcn 追加的重复 `require("tailwindcss-animate")`（ESM 下不可用）
- `vite.config.ts` 别名改用 `fileURLToPath(new URL('./src', import.meta.url))`（`__dirname` 在 ESM 不可用）
- `/api/scripts` 实际返回 `{items, total}`，`scriptService.fetchScripts` 按该结构解析
- TS 6.0 弃用 `baseUrl`，tsconfig 仅保留 `paths`
- 聊天区改用原生滚动容器 + 底部哨兵自动滚动（shadcn ScrollArea 无法直接拿 viewport ref），任务列表仍用 ScrollArea
- 新增 `src/services/`（http/script/audioTask/dify）、`src/utils/sseParser.ts`（缓冲式 SSE 解析器，可复用）
- Vite 模板自带 oxlint 已移除，仅保留 Biome
