# T10：设置弹窗改造为独立设置页

## 任务目标

将当前 `frontend/src/components/settings/SettingsDialog.tsx` 的设置弹窗改造为基于 `react-router-dom` 的独立全屏设置页，左侧分类导航 + 右侧内容区，支持子路由 `/settings/llm` 等，每类设置独立保存，并保留主题/语言即时预览与未保存离开确认。

**预计耗时**：0.5 ~ 1 天

---

## 前置依赖

- T8 完成（设置弹窗、Store、Service、类型、校验均已就绪）
- T9 完成或暂停不影响本任务（本任务专注设置页结构改造）

---

## 已确认设计决策

| 决策点 | 结论 |
|---|---|
| 路由方案 | 引入 `react-router-dom@^6.28`，仅设置页使用路由；工作区保持现有 `appStore.currentWorkspace` 切换 |
| 设置页入口 | Header 右上角齿轮图标改为跳转 `/settings`；Sidebar 底部新增“设置”入口 |
| 设置页布局 | 全屏页面，顶部仅返回按钮，无左侧主 Sidebar |
| 子分类组织 | 左侧设置导航菜单 + 右侧内容区；子路由 `/settings/llm`、`/settings/tts`、`/settings/dify`、`/settings/general` |
| 默认路由 | `/settings` 重定向至 `/settings/llm` |
| 设置页内切换 | 允许自由切换分类，各分类未保存状态独立保留 |
| 保存方式 | 手动保存，每类设置独立保存；构造完整 `Settings` 调用现有 `persistSettings` |
| 离开确认 | `beforeunload` + 返回按钮确认弹窗；`react-router` 内部跳转用 `useBlocker` 拦截 |
| 主题/语言预览 | 继续即时预览；在 General 页未保存时离开（返回或切分类）自动恢复为已保存值 |
| 导航未保存提示 | 左侧导航项显示圆点或“已修改”文案 |
| 测试连接状态 | 分类切换后接受重置 |
| 移动端 | 本次仅做桌面端，移动端后续再优化 |
| 目录结构 | 新增 `frontend/src/pages/settings/*`，保留 `frontend/src/components/settings/*` 作为表单组件 |

---

## 详细步骤

### 10.1 安装路由依赖

```bash
cd frontend
npm install react-router-dom@^6.28
```

### 10.2 改造 `frontend/src/App.tsx`

引入 `BrowserRouter`、`Routes`、`Route`，仅增加 `/settings/*` 路由；主工作区仍渲染 `MainLayout`。

```tsx
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';

import { MainLayout } from '@/components/layout/MainLayout';
import { DifySettingsPage } from '@/pages/settings/DifySettingsPage';
import { GeneralSettingsPage } from '@/pages/settings/GeneralSettingsPage';
import { LLMSettingsPage } from '@/pages/settings/LLMSettingsPage';
import { SettingsLayout } from '@/pages/settings/SettingsLayout';
import { TTSSettingsPage } from '@/pages/settings/TTSSettingsPage';
import { useAppBootstrap } from '@/hooks/useAppBootstrap';

const router = createBrowserRouter([
  {
    path: '/settings',
    element: <SettingsLayout />,
    children: [
      { index: true, element: <Navigate to="/settings/llm" replace /> },
      { path: 'llm', element: <LLMSettingsPage /> },
      { path: 'tts', element: <TTSSettingsPage /> },
      { path: 'dify', element: <DifySettingsPage /> },
      { path: 'general', element: <GeneralSettingsPage /> },
    ],
  },
  { path: '*', element: <MainLayout /> },
]);

function App() {
  useAppBootstrap();

  return <RouterProvider router={router} />;
}

export default App;
```

> 使用 `createBrowserRouter` + `RouterProvider`（data router），因为 `useBlocker` 必须在 data router 中才能工作。工作区仍通过 `appStore.currentWorkspace` 切换，不纳入路由。

### 10.3 新增设置页目录与文件

```
frontend/src/pages/settings/
├── SettingsLayout.tsx      # 全屏布局、左侧导航、Outlet、数据加载、未保存拦截
├── SettingsNav.tsx         # 左侧分类导航，高亮当前路由，显示未保存圆点
├── LLMSettingsPage.tsx     # /settings/llm
├── TTSSettingsPage.tsx     # /settings/tts
├── DifySettingsPage.tsx    # /settings/dify
└── GeneralSettingsPage.tsx # /settings/general
```

### 10.4 `SettingsLayout.tsx`

职责：

1. 进入页面时调用 `settingsStore.loadSettings()` 加载一次。
2. 用 `useBlocker` 拦截从 `/settings/*` 离开到其他路由的行为；有任意分类未保存时弹出确认。
3. 监听 `beforeunload`，有未保存时提示。
4. 提供共享上下文：各分类的 draft、校验错误、保存状态、未保存标记。
5. 渲染顶部返回栏 + 左侧 `SettingsNav` + 右侧 `<Outlet />`。

顶部返回栏：左侧返回按钮 + 标题“设置”。返回固定到 `/`。

### 10.5 `SettingsNav.tsx`

导航项：

- 大模型 → `/settings/llm`
- 语音合成 → `/settings/tts`
- Dify → `/settings/dify`
- 通用 → `/settings/general`

每项显示：图标/名称 + 未保存圆点（当该分类有未保存更改时）。

### 10.6 各分类设置页（LLM / TTS / Dify / General）

每个页面：

1. 从 `SettingsLayout` 上下文读取当前分类的 draft 与错误。
2. 复用现有 `components/settings/LLMSettings.tsx` 等表单组件。
3. 右下角固定/吸底放置“保存”按钮（`Button`），禁用条件：保存中 / 无改动 / 校验错误。
4. 保存时构造完整 `Settings`：

```ts
const nextSettings: Settings = {
  ...settings,
  llm_config: draft.llm_config, // 以当前分类 draft 替换
};
await persistSettings(nextSettings);
```

5. 保存成功后 toast 提示 `settings.saved`。
6. 保存失败显示错误信息。

### 10.7 主题/语言预览恢复逻辑

`GeneralSettingsPage` / `GeneralSettings` 保持现有即时预览行为：

- 切换语言立即 `i18n.changeLanguage(lang)`。
- 切换主题立即 `applyTheme(theme)`。

在以下时机恢复为已保存值：

- 用户从 General 页切换到其他设置分类（未保存时）。
- 用户点击返回按钮离开设置页（未保存且确认放弃后）。
- 保存失败时（可选，但建议恢复）。

恢复函数复用：

```ts
const revertPreview = () => {
  if (!settings) return;
  applyTheme(settings.general_config.theme);
  void i18n.changeLanguage(settings.general_config.language);
};
```

### 10.8 未保存状态管理

在 `SettingsLayout` 中维护一个对象：

```ts
const [dirtySections, setDirtySections] = useState<Record<SettingsSection, boolean>>({
  llm_config: false,
  tts_config: false,
  dify_config: false,
  general_config: false,
});
```

每个分类页独立比较自己的 draft 与 `settings` 中对应块，通过上下文更新 dirty 标记。

### 10.9 `Header.tsx` 改造

移除 `SettingsDialog` 导入，齿轮图标改为路由跳转：

```tsx
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

<Button
  variant="ghost"
  size="icon"
  aria-label={t('settings.title')}
  onClick={() => navigate('/settings')}
>
  <Settings className="h-5 w-5" />
</Button>
```

### 10.10 `Sidebar.tsx` 改造

在底部折叠按钮上方新增“设置”入口：

```tsx
import { Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

<Button
  variant="ghost"
  className="w-full justify-start gap-2"
  onClick={() => navigate('/settings')}
>
  <Settings className="h-5 w-5" />
  {!sidebarCollapsed && <span>{t('settings.title')}</span>}
</Button>
```

折叠状态下仅显示图标，hover/tooltip 显示“设置”。

### 10.11 删除旧弹窗

- 删除 `frontend/src/components/settings/SettingsDialog.tsx`。
- 检查是否还有其他文件引用该组件（确认只有 `Header.tsx`）。

### 10.12 i18n 文案补充

在 `zh.json` / `en.json` 的 `settings` 命名空间下补充：

- `settings.back`：返回
- `settings.nav.llm`：大模型（可复用现有 `settings.llm`）
- `settings.nav.tts`：语音合成（可复用现有 `settings.tts`）
- `settings.nav.dify`：Dify（可复用现有 `settings.dify`）
- `settings.nav.general`：通用（可复用现有 `settings.general`）
- `settings.unsavedLeave`：有未保存的更改，是否放弃并离开？
- `settings.discardChanges`：放弃更改

### 10.13 代码检查

```bash
# 前端
cd frontend
npm run lint
npm run format
npx tsc -b

# 可选：本地构建验证
npm run build
```

---

## 关键设计点

- 路由仅用于设置页，不破坏现有工作区 store 切换逻辑。
- 设置页全屏布局，左侧导航清晰对应四大配置模块；子路由使浏览器前进/后退可用。
- 每类设置独立保存，减少用户误操作范围；保存时仍调用现有全量接口，避免后端改动。
- 未保存状态按分类追踪，设置页内可自由切换分类；离开设置页时统一拦截确认。
- 主题/语言保持即时预览，离开 General 页未保存时自动恢复，避免界面状态与持久化数据不一致。
- 复用现有 `components/settings/*` 表单组件，改动聚焦于页面壳层与路由。

---

## 验收标准

- [ ] `npm install react-router-dom@^6.28` 成功写入 `package.json`
- [ ] 点击 Header 齿轮图标或 Sidebar“设置”进入 `/settings`，并自动重定向到 `/settings/llm`
- [ ] 设置页为全屏布局，左侧导航，右侧内容区，顶部有返回按钮可回到 `/`
- [ ] 四个子路由 `/settings/llm`、`/settings/tts`、`/settings/dify`、`/settings/general` 可正常切换
- [ ] 每类设置可独立编辑、独立保存，保存成功后持久化并 toast 提示
- [ ] 左侧导航在对应分类有未保存更改时显示圆点/已修改标记
- [ ] 未保存时点击浏览器刷新/关闭触发 `beforeunload` 提示
- [ ] 未保存时点击返回按钮弹出确认弹窗，确认放弃后才离开
- [ ] General 页切换主题/语言即时生效，未保存离开 General 时恢复为已保存值
- [ ] 删除 `SettingsDialog.tsx`，无残留引用
- [ ] `npm run lint`、`npm run format`、`tsc -b` 通过
- [ ] `vite build` 通过

---

## 关联文档

- `docs/task/08-settings-and-polish.md`
- `docs/tech/tech-spec.md` 第 11、12、13、14 章
- `docs/prd/meditation-guide-words-prd.md` 第 4.4、4.5 章

---

## 风险备注

- `react-router-dom v6.28` 的 `useBlocker` 在稳定版中可用，但需确保用于拦截“从设置页跳转到外部路由”而非同设置页内子路由切换。
- 主题/语言预览恢复逻辑需要精确挂载在离开 General 页或离开设置页时，避免恢复时机错误导致闪烁。
- 各分类独立保存后，若两个分类同时有未保存更改，用户离开设置页时提示应明确是“所有未保存更改”。
- 移动端本次不处理，后续若需移动端需重新设计左侧导航的响应式表现。
