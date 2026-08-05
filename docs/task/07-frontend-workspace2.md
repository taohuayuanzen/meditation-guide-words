# T7：前端工作区 2 与音频生成界面

## 任务目标

实现工作区 2（音频生成）的完整前端界面：选择已保存的引导词、用自然语言描述声音风格、提交异步生成任务、展示任务状态列表、播放与下载生成音频。

**预计耗时**：2 ~ 2.5 天

---

## 前置依赖

- T6 完成（前端基础、布局、工作区 1 已实现）
- T4 完成（音频任务 API 已就绪）
- T5 完成（TTS 适配层与 Worker 已就绪）

---

## 详细步骤

### 7.1 引导词列表 API 封装

`frontend/src/services/scriptService.ts`：

```ts
import type { Script } from "@/types"

export async function fetchScripts(): Promise<Script[]> {
  const res = await fetch("/api/scripts")
  if (!res.ok) throw new Error("Failed to fetch scripts")
  return res.json()
}

export async function fetchScript(id: number): Promise<Script> {
  const res = await fetch(`/api/scripts/${id}`)
  if (!res.ok) throw new Error("Failed to fetch script")
  return res.json()
}
```

`frontend/src/types/index.ts`：

```ts
export interface Script {
  id: number
  title: string
  content: string
  session_id?: string
  created_at: string
  updated_at: string
}

export interface AudioTask {
  id: number
  script_id: number
  voice_prompt: string
  tts_params?: Record<string, unknown>
  status: "pending" | "processing" | "completed" | "failed"
  file_path?: string
  error_msg?: string
  created_at: string
  completed_at?: string
}
```

### 7.2 音频任务 API 封装

`frontend/src/services/audioTaskService.ts`：

```ts
import type { AudioTask } from "@/types"

export async function createAudioTask(scriptId: number, voicePrompt: string): Promise<AudioTask> {
  const res = await fetch("/api/audio-tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ script_id: scriptId, voice_prompt: voicePrompt }),
  })
  if (!res.ok) throw new Error("Failed to create audio task")
  return res.json()
}

export async function fetchAudioTasks(): Promise<AudioTask[]> {
  const res = await fetch("/api/audio-tasks")
  if (!res.ok) throw new Error("Failed to fetch audio tasks")
  return res.json()
}

export async function fetchAudioTask(id: number): Promise<AudioTask> {
  const res = await fetch(`/api/audio-tasks/${id}`)
  if (!res.ok) throw new Error("Failed to fetch audio task")
  return res.json()
}

export async function retryAudioTask(id: number): Promise<AudioTask> {
  const res = await fetch(`/api/audio-tasks/${id}/retry`, { method: "POST" })
  if (!res.ok) throw new Error("Failed to retry audio task")
  return res.json()
}

export function getAudioDownloadUrl(id: number): string {
  return `/api/audio-tasks/${id}/download`
}
```

### 7.3 工作区 2 界面实现

#### 线框描述

```
┌─────────────────────────────────────────────────────────────────┐
│  音频生成                                             [设置 ⚙️]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  选择引导词： [ 请选择已保存的引导词 ▼ ]                         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 引导词预览                                                 │ │
│  │ 现在，请找一个舒适的位置坐下或躺下...（只读 Textarea）     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  声音描述： [ 温柔女声，语速慢，正念风格        ]       [生成]   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 任务列表                                                   │ │
│  │ #1 排队中...                                  [取消/重试] │ │
│  │ #2 合成中...                                              │ │
│  │ #3 已完成  [播放] [下载]                                  │ │
│  │ #4 失败：音色ID无效                          [重试]        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### `frontend/src/components/workspace/AudioWorkspace.tsx`

```tsx
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import { fetchScripts } from "@/services/scriptService"
import {
  createAudioTask,
  fetchAudioTasks,
  retryAudioTask,
  getAudioDownloadUrl,
} from "@/services/audioTaskService"
import type { Script, AudioTask } from "@/types"

export function AudioWorkspace() {
  const { t } = useTranslation()
  const [scripts, setScripts] = useState<Script[]>([])
  const [selectedScriptId, setSelectedScriptId] = useState<string>("")
  const [voicePrompt, setVoicePrompt] = useState("")
  const [tasks, setTasks] = useState<AudioTask[]>([])
  const [isGenerating, setIsGenerating] = useState(false)

  useEffect(() => {
    fetchScripts().then(setScripts)
    fetchAudioTasks().then(setTasks)
  }, [])

  const selectedScript = scripts.find((s) => String(s.id) === selectedScriptId)

  useEffect(() => {
    const interval = setInterval(() => {
      fetchAudioTasks().then(setTasks)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleGenerate = async () => {
    if (!selectedScript || !voicePrompt.trim()) return
    setIsGenerating(true)
    try {
      await createAudioTask(selectedScript.id, voicePrompt)
      const updated = await fetchAudioTasks()
      setTasks(updated)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRetry = async (taskId: number) => {
    await retryAudioTask(taskId)
    const updated = await fetchAudioTasks()
    setTasks(updated)
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <h2 className="text-lg font-semibold">{t("workspace.audio")}</h2>

      <div>
        <label className="block text-sm font-medium mb-1">选择引导词</label>
        <Select value={selectedScriptId} onValueChange={setSelectedScriptId}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="请选择已保存的引导词" />
          </SelectTrigger>
          <SelectContent>
            {scripts.map((script) => (
              <SelectItem key={script.id} value={String(script.id)}>
                {script.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedScript && (
        <Textarea
          value={selectedScript.content}
          readOnly
          rows={6}
          className="bg-gray-50"
        />
      )}

      <div className="flex gap-2">
        <Textarea
          value={voicePrompt}
          onChange={(e) => setVoicePrompt(e.target.value)}
          placeholder="描述你想要的声音风格，例如：温柔女声，语速慢，正念风格"
          className="flex-1"
          rows={2}
        />
        <Button onClick={handleGenerate} disabled={isGenerating || !selectedScript}>
          生成音频
        </Button>
      </div>

      <ScrollArea className="flex-1 border rounded-lg p-4">
        <h3 className="font-medium mb-2">任务列表</h3>
        <div className="space-y-2">
          {tasks.map((task) => (
            <TaskItem key={task.id} task={task} onRetry={handleRetry} />
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
```

#### 任务项组件 `frontend/src/components/workspace/TaskItem.tsx`

```tsx
import { Button } from "@/components/ui/button"
import type { AudioTask } from "@/types"

interface TaskItemProps {
  task: AudioTask
  onRetry: (id: number) => void
}

export function TaskItem({ task, onRetry }: TaskItemProps) {
  const statusMap = {
    pending: "排队中",
    processing: "合成中",
    completed: "已完成",
    failed: "失败",
  }

  return (
    <div className="flex items-center justify-between p-3 border rounded-lg">
      <div>
        <div className="font-medium">任务 #{task.id}</div>
        <div className="text-sm text-gray-500">{statusMap[task.status]}</div>
        {task.error_msg && <div className="text-sm text-red-500">{task.error_msg}</div>}
      </div>
      <div className="flex gap-2">
        {task.status === "completed" && (
          <>
            <audio controls src={getAudioDownloadUrl(task.id)} className="h-8 w-48" />
            <a href={getAudioDownloadUrl(task.id)} download>
              <Button size="sm" variant="outline">下载</Button>
            </a>
          </>
        )}
        {task.status === "failed" && (
          <Button size="sm" variant="outline" onClick={() => onRetry(task.id)}>
            重试
          </Button>
        )}
      </div>
    </div>
  )
}
```

### 7.4 Dify 音频参数解析

提交任务前，先调用 `/api/dify/audio/chat` 解析声音提示词为 TTS 参数 JSON。

```tsx
async function parseVoicePrompt(scriptId: number, voicePrompt: string): Promise<Record<string, unknown>> {
  const script = await fetchScript(scriptId)
  const response = await fetch("/api/dify/audio/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      inputs: { script_content: script.content },
      query: voicePrompt,
      response_mode: "blocking",
      conversation_id: "",
      user: "local-user",
    }),
  })
  const data = await response.json()
  // Dify blocking 响应中 answer 字段即为 LLM 输出
  const answer = data.answer || "{}"
  return JSON.parse(answer)
}
```

> 更优做法：将解析逻辑放在后端 `POST /api/audio-tasks` 中，先调 Dify 解析，再创建任务。前端只需传 `script_id` 和 `voice_prompt`。推荐后端处理。

### 7.5 任务轮询优化

当前实现每 3 秒轮询一次。优化点：
- 仅对 `pending` / `processing` 状态任务轮询
- 完成后停止轮询
- 可改为 SSE 推送（T8 可选优化）

### 7.6 错误处理

- 生成失败时显示具体错误信息
- Dify 解析 JSON 失败时，给出"声音描述不清晰，请重试"提示
- 网络错误时允许重试

---

## 关键设计点

- 工作区 2 的引导词选择器从 `/api/scripts` 获取已保存列表。
- 声音提示词先由 Dify App B 解析为结构化 TTS 参数，再创建音频任务。
- 任务列表自动轮询，实时更新状态。
- 已完成的音频使用 HTML5 `<audio>` 控件直接播放，下载走 `/api/audio-tasks/{id}/download`。
- 失败任务支持一键重试。

---

## 验收标准

- [ ] 工作区 2 可看到工作区 1 保存的所有引导词
- [ ] 选择引导词后显示内容预览
- [ ] 输入声音描述后点击"生成音频"，成功创建异步任务
- [ ] 任务列表每 3 秒自动刷新，状态正确显示（排队中/合成中/已完成/失败）
- [ ] 已完成的任务可在线播放和下载
- [ ] 失败的任务显示错误原因并可重试
- [ ] 未选择引导词或空提示词时，生成按钮禁用

---

## 关联文档

- `docs/tech/tech-spec.md` 第 6、7、9、10 章
- `docs/prd/meditation-guide-words-prd.md` 第 4.3、8.2 章

---

## 风险备注

- Dify App B 返回的 JSON 可能包含 markdown 代码块，后端或前端需做清洗。
- 长引导词合成耗时可能超过 30 秒，需确保前端轮询耐心和 Worker 超时设置合理。
- 同时生成多个音频时，Worker 并发数需要限制，避免本地资源耗尽。

---

## 当前进度（2026-08-05 · 已完成）

### 已完成

- [x] `src/types/`：Script / ScriptListResponse / AudioTask（含 `retry_count`）/ AudioTaskStatus
- [x] `src/services/scriptService.ts`（适配 `{items, total}`）、`audioTaskService.ts`（create 支持 `tts_params`、list、retry、download URL）
- [x] 工作区 2：引导词下拉选择 + 内容预览 + 声音描述输入 + 生成按钮禁用逻辑
- [x] 声音提示词解析：前端调 `/api/dify/audio/chat`（blocking）→ 清洗 markdown 代码块 → `JSON.parse` → 作为 `tts_params` 传入 `POST /api/audio-tasks`
- [x] 任务列表：每 3s 轮询（仅存在 pending/processing 时），状态正确显示，已完成可播放/下载，失败显示错误并可重试
- [x] 错误处理：解析失败提示"声音描述不清晰"、创建失败显示后端 `detail`、Dify 未配置提示
- [x] `biome lint` / `biome format` 无错误；`tsc -b && vite build` 通过；冒烟验证通过

### 关键实现决策（已确认）

| 决策点 | 结论 |
|---|---|
| 声音提示词解析位置 | **前端解析**：`/api/dify/audio/chat` blocking → 清洗 markdown → `tts_params` 落库（复用 T5 能力），不改后端 |
| 任务轮询 | 仅当存在 `pending`/`processing` 任务时启用 3s 定时器，完成后自动停止 |
| 状态保持 | 与 T6 一致，工作区常驻挂载，切回后脚本选择/任务列表保留 |

### 与文档差异 / 附带修改

- `createAudioTask` 签名增加可选 `ttsParams`（对应 T5 后端 `tts_params` 字段）
- 任务轮询做了优化：仅在存在活跃任务时轮询（文档 7.5 的优化点已实现）
- 播放器 `<audio>` 增加 `preload="none"`，避免列表加载时预拉全量音频
- 错误文案走 i18n（zh/en 全量）
