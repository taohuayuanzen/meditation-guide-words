# T9：前端 UI/UX 优化与响应式完善

## 任务目标

在不改变现有前端技术栈（React 18 + Vite + Tailwind CSS + shadcn/ui + Zustand + react-i18next）的前提下，系统修复当前 UI/UX 问题，提升暗色模式一致性、交互反馈、两个工作区的可用性，以及设置页体验，并补充响应式布局（侧边栏折叠、移动端适配）。

**预计耗时**：2 ~ 2.5 天

---

## 前置依赖

- T6、T7 完成（两个工作区前端界面已实现）
- T8 完成（设置弹窗、全局状态、主题/语言持久化已实现）
- 当前 `npm run lint` 与 `npm run build` 通过

---

## 详细步骤

### P0：主题一致性与全局基础反馈

#### 1. 修复硬编码颜色，确保暗色模式一致

- 将 `ScriptWorkspace.tsx:147-149` 的 `bg-blue-100` / `bg-gray-100` 改为语义化颜色：
  - 用户消息：`bg-primary text-primary-foreground`
  - AI 消息：`bg-muted text-muted-foreground`
- 检查 `AudioWorkspace.tsx:119` 的 `bg-muted` 使用是否符合预期。
- 全项目搜索硬编码色值（`bg-` / `text-` 非变量类），统一替换为 shadcn 语义 token。

#### 2. 新增全局 Toast 反馈

引入 `sonner` 作为全局 Toast：

```bash
cd frontend
npm install sonner
npx shadcn@2.3.0 add sonner
```

- 在 `frontend/src/main.tsx` 或 `App.tsx` 顶层包裹 `<Toaster />`。
- 新增 `frontend/src/hooks/useToast.ts` 做项目级封装：

```ts
import { toast } from 'sonner';

export function useToast() {
  return {
    toast: (message: string) => toast(message),
    success: (message: string) => toast.success(message),
    error: (message: string) => toast.error(message),
  };
}
```

接入点：
- 设置保存成功/失败
- 工作区 1 保存引导词成功/失败
- 工作区 2 解析失败/创建任务失败
- 全局网络错误兜底

#### 3. 新增全局错误边界

新增 `frontend/src/components/error/ErrorBoundary.tsx`：

- 捕获渲染异常，显示友好错误页（带“刷新页面”按钮）。
- 在 `main.tsx` 包裹 `<App />`。

#### 4. 加载状态补全

- 引入 shadcn `Skeleton` 组件：`npx shadcn@2.3.0 add skeleton`
- 设置弹窗打开且 `settings` 未加载时，用 `Skeleton` 替代“加载中…”文本。
- 工作区 2 首次加载引导词/任务列表时，显示骨架屏或 spinner。

---

### P1：工作区 1 引导词生成交互增强

#### 5. 消息操作：复制 + 保存本条

重构 `ScriptWorkspace.tsx` 消息渲染，新增 `frontend/src/components/workspace/ChatMessage.tsx`：

- 每条 AI 消息 hover 时显示操作栏：复制、保存本条。
- 复制：将消息 `content` 写入剪贴板，成功后 toast 提示。
- 保存本条：调用 `createScript`，toast 反馈结果。
- 移除顶部“保存引导词”按钮，或改为仅对最后一条兜底。

#### 6. 停止生成

- `handleSend` 使用 `AbortController`。
- 流式输出期间，发送按钮变为“停止”按钮（图标 `Square`），点击后 `abort()` 并清理状态。

#### 7. 流式指示器

- AI 正在输出时，消息末尾显示温和闪烁光标或“AI 正在输入…”小字提示。
- 流结束后自动移除。

#### 8. 错误提示升级

- 网络/解析错误不再以 `[...]` 追加到消息正文。
- 改为顶部 `Alert` 组件或 Toast 提示。
- 引入 shadcn `Alert`：`npx shadcn@2.3.0 add alert`

#### 9. 输入区体验优化

- Textarea 改为自动高度：根据内容行数在 2~6 行之间动态调整。
- 支持 `Ctrl/Cmd + Enter` 发送。
- 支持 `Escape` 清空输入（非发送中状态）。

#### 10. 空状态升级

新增 `frontend/src/components/workspace/ScriptEmptyState.tsx`：

- 展示 3 个示例提示词卡片：
  - “生成一段 10 分钟睡前放松冥想引导词”
  - “把刚才的引导词改成 5 分钟版本”
  - “加入更多身体扫描元素”
- 点击卡片自动填入输入框。

---

### P1：工作区 2 音频生成信息展示与反馈

#### 11. 任务项信息增强

改造 `frontend/src/components/workspace/TaskItem.tsx`：

- 显示关联引导词标题（从 `script_id` 反查，AudioWorkspace 传入 `scripts` 映射）。
- 显示创建时间 / 完成时间（如果已完成）。
- 显示声音提示词摘要（过长截断 + Tooltip 完整展示）。
- 失败任务展开显示完整 `error_msg`。
- 引入 shadcn `Tooltip`：`npx shadcn@2.3.0 add tooltip`

#### 12. 音频播放器视觉统一

- 用自定义样式包裹原生 `<audio>`：保留控件功能，但宽度、高度与按钮风格统一。
- 默认 `preload="none"` 保持不变。

#### 13. 手动刷新与状态提示

在 `AudioWorkspace.tsx` 任务列表顶部增加：

- “刷新”按钮（图标 `RefreshCw`），点击立即 `refreshTasks()`。
- “最后更新：X 秒前” 文本，随轮询更新。
- 轮询间隔保持 3 秒，仅存在 `pending` / `processing` 任务时启用。

#### 14. 文案与标签校准

- `AudioWorkspace.tsx:118-120` 引导词预览上方增加标签：使用已有 `t('audio.scriptPreview')`。
- “生成音频”按钮：
  - 调用 Dify 解析阶段显示 `t('audio.parsing')`（新增文案）。
  - 创建任务成功后恢复 `t('audio.generate')`。
- 新增 i18n key：`audio.parsing`。

---

### P1：设置页体验升级

#### 15. 字段校验

各 Settings 子组件在 `onChange` 时做即时校验：

- LLM：`base_url` 必须以 `http://` 或 `https://` 开头；`temperature` 范围 0~2；`max_tokens` 必须为正整数或空。
- TTS：`speed` 0.5~2；`volume` 0~2；火山引擎时 `appid` / `cluster` 必填。
- Dify：`base_url` 必须以 `http://` 或 `https://` 开头；`app_key` 非空提示。
- 通用：`audio_output_dir` 非空。

校验错误在字段下方用 `text-destructive` 小字展示，并禁用“保存全部”按钮。

#### 16. API Key 显示/隐藏切换

新增 `frontend/src/components/ui/password-input.tsx`：

- 组合 `Input type={visible ? 'text' : 'password'}` + 眼睛图标按钮（`Eye` / `EyeOff`）。
- 替换 LLM、TTS、Dify 设置中的 `type="password"` 输入框。

#### 17. Sticky 底部操作栏

`SettingsDialog.tsx` 底部保存/取消/测试按钮改为 sticky footer：

- 长表单滚动时始终可见。
- 错误/成功提示也放在 footer 区域。

#### 18. 未保存提示与即时预览回滚

- 关闭弹窗前检测 `draft` 与原始 `settings` 是否一致；不一致时弹出确认：“有未保存的更改，是否放弃？”。
- 主题/语言切换仍即时预览；若用户取消保存，关闭弹窗时回滚到原始设置。

#### 19. 记忆当前 Tab

- `SettingsDialog` 打开时记忆上次停留的 Tab（可存于 `localStorage` 或 appStore）。

---

### P2：响应式与导航

#### 20. 桌面端可折叠侧边栏

改造 `frontend/src/components/layout/Sidebar.tsx`：

- 新增折叠状态（存于 `appStore` 或本地 state）。
- 折叠后宽度约 `w-16`，仅显示图标/首字母；展开后恢复 `w-64`。
- 工作区按钮使用图标 + 文字，折叠时只显示图标（使用 `lucide-react` 图标：`FileText` / `Headphones`）。
- 在 Sidebar 底部增加折叠/展开切换按钮。

#### 21. 移动端 Sheet 导航

- 小屏（`< md`）下隐藏固定侧边栏。
- 顶栏左侧增加菜单按钮，点击打开左侧 `Sheet` 抽屉导航。
- 复用现有 `frontend/src/components/ui/sheet.tsx`。

#### 22. 顶栏当前工作区标识

`Header.tsx`：

- 小屏下显示当前工作区标题（已有 `title`）。
- 增加当前工作区图标，与 Sidebar 图标保持一致。

#### 23. 工作区布局响应式兜底

- 工作区 1/2 主内容区在侧边栏折叠后自动占满剩余宽度。
- 输入区、任务列表在小屏下保持可用（最小宽度、触控目标 ≥ 44px）。

---

## 关键设计点

- **Toast 使用 Sonner**：直接引入 `sonner` + shadcn wrapper，统一项目提示风格。
- **颜色语义化**：所有自定义颜色统一使用 shadcn CSS 变量，确保 light/dark 一致。
- **消息操作克制**：仅实现“复制”和“保存本条”，不引入编辑/重发/删除，避免后端接口改动。
- **工作区 2 保持单栏**：只做信息密度增强和反馈优化，不动整体布局。
- **设置即时预览 + 取消回滚**：主题/语言可即时预览，但关闭弹窗未保存时回滚，避免“看起来改了实际没改”。
- **响应式渐进增强**：桌面折叠侧边栏 + 移动端 Sheet，主布局不推翻。
- **可引入少量 shadcn 组件**：`Skeleton`、`Tooltip`、`Alert`；`Sonner` 与自研 Toast 重复，本次不引入。

---

## 验收标准

- [ ] `npm run lint` 与 `npm run build` 无错误
- [ ] 暗色模式下工作区 1 聊天气泡、工作区 2 预览区颜色正常
- [ ] 设置保存、工作区 1 保存、工作区 2 错误均通过 Toast 反馈
- [ ] 工作区 1 每条 AI 消息可复制、可单条保存
- [ ] 工作区 1 流式输出时可点击“停止”中断
- [ ] 工作区 1 输入框自动增高，支持 `Ctrl+Enter` 发送
- [ ] 工作区 2 任务项显示引导词标题、创建时间、声音提示词摘要
- [ ] 工作区 2 任务列表可手动刷新，显示“最后更新于 X 秒前”
- [ ] 设置页 API Key 输入框支持显示/隐藏切换
- [ ] 设置页字段校验生效，非法输入禁用保存按钮
- [ ] 设置页关闭时有未保存提示，取消保存后主题/语言回滚
- [ ] 桌面端侧边栏可折叠/展开，移动端使用 Sheet 导航
- [ ] i18n 文案覆盖新增 key（zh/en）

---

## 新增与修改文件清单

### 新增文件

- `frontend/src/components/ui/sonner.tsx`（shadcn wrapper）
- `frontend/src/hooks/useToast.ts`
- `frontend/src/components/error/ErrorBoundary.tsx`
- `frontend/src/components/workspace/ChatMessage.tsx`
- `frontend/src/components/workspace/ScriptEmptyState.tsx`
- `frontend/src/components/ui/password-input.tsx`
- `frontend/src/components/ui/skeleton.tsx`（shadcn）
- `frontend/src/components/ui/tooltip.tsx`（shadcn）
- `frontend/src/components/ui/alert.tsx`（shadcn）

### 修改文件

- `frontend/src/main.tsx`（接入 ErrorBoundary）
- `frontend/src/App.tsx`（接入 ToastProvider）
- `frontend/src/index.css`（如有需要微调暗色变量）
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/components/layout/MainLayout.tsx`
- `frontend/src/components/workspace/ScriptWorkspace.tsx`
- `frontend/src/components/workspace/AudioWorkspace.tsx`
- `frontend/src/components/workspace/TaskItem.tsx`
- `frontend/src/components/settings/SettingsDialog.tsx`
- `frontend/src/components/settings/LLMSettings.tsx`
- `frontend/src/components/settings/TTSSettings.tsx`
- `frontend/src/components/settings/DifySettings.tsx`
- `frontend/src/components/settings/GeneralSettings.tsx`
- `frontend/src/stores/appStore.ts`（增加 sidebarCollapsed / 当前 tab 记忆）
- `frontend/src/i18n/locales/zh.json`
- `frontend/src/i18n/locales/en.json`

---

## 新增 i18n Key 参考

```json
{
  "chat": {
    "copy": "复制",
    "copied": "已复制",
    "saveThis": "保存本条",
    "stop": "停止",
    "emptyTitle": "开始生成你的第一条冥想引导词",
    "emptyExample1": "生成一段 10 分钟睡前放松冥想引导词",
    "emptyExample2": "把刚才的引导词改成 5 分钟版本",
    "emptyExample3": "加入更多身体扫描元素"
  },
  "audio": {
    "parsing": "正在解析声音参数…",
    "refresh": "刷新",
    "lastUpdated": "最后更新：{{seconds}} 秒前",
    "scriptTitle": "引导词",
    "createdAt": "创建于",
    "completedAt": "完成于",
    "voicePrompt": "声音描述"
  },
  "common": {
    "confirm": "确认",
    "discard": "放弃",
    "unsavedChanges": "有未保存的更改，是否放弃？",
    "refreshPage": "刷新页面"
  },
  "settings": {
    "show": "显示",
    "hide": "隐藏",
    "invalidUrl": "请输入以 http:// 或 https:// 开头的 URL",
    "required": "此项为必填"
  }
}
```

（`en.json` 需同步补充对应英文。）

---

## 关联文档

- `docs/prd/meditation-guide-words-prd.md` 第 4、8 章
- `docs/tech/tech-spec.md` 第 3、12 章
- `docs/task/06-frontend-workspace1.md`
- `docs/task/07-frontend-workspace2.md`
- `docs/task/08-settings-and-polish.md`

---

## 风险备注

- Sonner 已内置堆叠、焦点、ARIA 等能力，注意主题跟随与位置配置（建议 `position: top-right`，`richColors`）。
- 新增 `sonner` 依赖后需重新运行 `npm install` 并确认 `npm run build` 通过。
- 侧边栏折叠后需确保 lucide 图标在两个工作区语义清晰。
- 移动端 Sheet 导航与桌面折叠是两套逻辑，避免代码重复，可抽象 `WorkspaceNav` 组件。
- 工作区 2 任务项增强依赖 `scripts` 映射传入，注意任务列表为空/脚本被删除时的兜底显示。
- 引入 shadcn 新组件时继续沿用 `shadcn@2.3.0`（Tailwind v3 兼容版本），避免官方最新版 workspace 配置 bug。

---

## 决策确认清单（本次已确认）

| 编号 | 决策项 | 结论 |
|---|---|---|
| 1 | 优化范围 | **P0 + P1 + P2 全量**：暗色/反馈 + 工作区交互 + 设置页 + 响应式 |
| 2 | 全局反馈组件 | **引入 Sonner** 替代自研 Toast |
| 3 | 工作区 1 消息操作 | **仅复制 + 保存本条**，不做编辑/重发/删除 |
| 4 | 工作区 2 布局 | **保持当前单栏垂直布局**，仅增强任务项信息与反馈 |
| 5 | API Key 展示 | **增加显示/隐藏切换按钮** |
| 6 | shadcn 新组件 | **可引入 Skeleton、Tooltip、Alert、Sonner** |

---

## 当前进度

- [x] 问题梳理与优化方案确认
- [x] 任务文档评审通过
- [x] 代码实现
- [x] `npm run lint` 通过
- [x] `npm run build` 通过
- [ ] 手动验收（E2E）
