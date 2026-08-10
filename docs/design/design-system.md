# 冥想引导工作台 · PC 端设计系统

> 版本：v1.0  
> 适用范围：`frontend/src` 全部页面与组件  
> 设计基调：基于 [Codex](https://www.typeui.sh/design-skills/codex) 的极简、排版驱动、无阴影、pill 形状风格；主题色替换为「自然疗愈绿（鼠尾草绿 Sage）」。

---

## 1. 设计原则

1. **白/深绿灰画布即界面**
   - 浅色模式以纯白为底，深色模式以带绿调的深灰为底。
   - 不使用灰色大色块、渐变、装饰插画或彩色图标集。
2. **鼠尾草绿是唯一品牌填充色**
   - 绿色用于主按钮、选中态、核心强调、成功反馈。
   - 黑色/白色用于文本与结构分隔；红色、琥珀色仅用于错误/警告语义。
3. **排版即层级**
   - 通过字号、字重、间距和对齐建立层级，不用颜色补偿。
4. **Pill 形状创造对话感**
   - 按钮、输入框、选择器、Tab 等交互元素统一使用 pill（`rounded-full`）。
   - 卡片、面板、弹窗使用 `16–20px` 大圆角。
5. **无阴影层级**
   - UI 表面不浮起；层级通过间距、边框、填充、backdrop 区分。
6. **WCAG 2.2 AA**
   - 所有文本与交互元素满足对比度要求；颜色不作为唯一状态指示器。

---

## 2. 色彩系统

### 2.1 色彩格式

所有颜色以 **OKLCH** 函数形式落地，与现有 shadcn/ui Tailwind 配置保持一致。CSS 变量只存储函数参数（不含 `oklch(...)` 外壳），例如：

```css
--primary: 0.53 0.085 158;
```

Tailwind 中消费为：

```js
colors: {
  primary: {
    DEFAULT: 'oklch(var(--primary))',
    foreground: 'oklch(var(--primary-foreground))',
  },
}
```

### 2.2 品牌主色（Sage Green）

| Token | 浅色模式 | 深色模式 | 用途 |
|---|---|---|---|
| `--primary` | `0.53 0.085 158` | `0.80 0.06 158` | 主按钮填充、选中态、核心强调 |
| `--primary-foreground` | `0.99 0 0` | `0.10 0.02 160` | 主色上的文字 |
| `--ring` | `0.62 0.09 158` | `0.80 0.06 158` | focus-visible 光环 |

> 完整色阶（用于 hover、light tint、图表等）：

| 色阶 | OKLCH |
|---|---|
| 50 | `0.97 0.01 158` |
| 100 | `0.93 0.02 158` |
| 200 | `0.88 0.03 158` |
| 300 | `0.80 0.05 158` |
| 400 | `0.72 0.07 158` |
| 500 | `0.62 0.09 158` |
| 600 | `0.53 0.085 158` |
| 700 | `0.45 0.075 158` |
| 800 | `0.35 0.06 158` |
| 900 | `0.25 0.05 158` |
| 950 | `0.15 0.04 158` |

### 2.3 中性色

```css
:root {
  --background: 1 0 0;
  --foreground: 0.14 0.01 160;

  --card: 1 0 0;
  --card-foreground: 0.14 0.01 160;

  --popover: 1 0 0;
  --popover-foreground: 0.14 0.01 160;

  --secondary: 0.97 0.005 160;
  --secondary-foreground: 0.14 0.01 160;

  --muted: 0.97 0.005 160;
  --muted-foreground: 0.50 0.015 160;

  --accent: 0.96 0.008 160;
  --accent-foreground: 0.14 0.01 160;

  --border: 0.90 0.005 160;
  --input: 0.90 0.005 160;

  --sidebar: 0.985 0.005 160;
  --sidebar-foreground: 0.14 0.01 160;
  --sidebar-primary: 0.53 0.085 158;
  --sidebar-primary-foreground: 0.99 0 0;
  --sidebar-accent: 0.96 0.008 160;
  --sidebar-accent-foreground: 0.14 0.01 160;
  --sidebar-border: 0.90 0.005 160;
  --sidebar-ring: 0.62 0.09 158;

  --radius: 1rem;
}

.dark {
  --background: 0.12 0.015 160;
  --foreground: 0.95 0.005 160;

  --card: 0.16 0.015 160;
  --card-foreground: 0.95 0.005 160;

  --popover: 0.16 0.015 160;
  --popover-foreground: 0.95 0.005 160;

  --primary: 0.80 0.06 158;
  --primary-foreground: 0.10 0.02 160;

  --secondary: 0.18 0.01 160;
  --secondary-foreground: 0.95 0.005 160;

  --muted: 0.18 0.01 160;
  --muted-foreground: 0.65 0.015 160;

  --accent: 0.20 0.012 160;
  --accent-foreground: 0.95 0.005 160;

  --border: 1 0 0 / 10%;
  --input: 1 0 0 / 15%;
  --ring: 0.80 0.06 158;

  --sidebar: 0.14 0.015 160;
  --sidebar-foreground: 0.95 0.005 160;
  --sidebar-primary: 0.80 0.06 158;
  --sidebar-primary-foreground: 0.10 0.02 160;
  --sidebar-accent: 0.20 0.012 160;
  --sidebar-accent-foreground: 0.95 0.005 160;
  --sidebar-border: 1 0 0 / 10%;
  --sidebar-ring: 0.80 0.06 158;
}
```

### 2.4 语义色

```css
:root {
  --success: 0.62 0.09 158;
  --success-foreground: 0.99 0 0;
  --warning: 0.70 0.14 80;
  --warning-foreground: 0.10 0.01 80;
  --info: 0.72 0.07 158;
  --info-foreground: 0.10 0.02 160;
  --destructive: 0.57 0.22 25;
  --destructive-foreground: 0.99 0 0;
}

.dark {
  --success: 0.80 0.06 158;
  --success-foreground: 0.10 0.02 160;
  --warning: 0.75 0.12 80;
  --warning-foreground: 0.10 0.01 80;
  --info: 0.80 0.06 158;
  --info-foreground: 0.10 0.02 160;
  --destructive: 0.70 0.19 25;
  --destructive-foreground: 0.99 0 0;
}
```

Tailwind 扩展：

```js
colors: {
  success: {
    DEFAULT: 'oklch(var(--success))',
    foreground: 'oklch(var(--success-foreground))',
  },
  warning: {
    DEFAULT: 'oklch(var(--warning))',
    foreground: 'oklch(var(--warning-foreground))',
  },
  info: {
    DEFAULT: 'oklch(var(--info))',
    foreground: 'oklch(var(--info-foreground))',
  },
}
```

### 2.5 用色规则

- **绿色只出现在**：主按钮、当前选中项、成功状态、核心强调图标、空状态主图标。
- **文本层级**：标题用 `foreground`，辅助文本用 `muted-foreground`，不用彩色文本来制造层级。
- **边框**：统一使用 `border`，避免一重一浅反复变化。
- **状态不单独依赖颜色**：例如选中态同时改变填充色 + 字重；错误态同时显示颜色 + 图标 + 文字说明。

---

## 3. 字体与排版

### 3.1 字体栈

```css
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --font-sans: 'Open Sans', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', 'Source Code Pro', monospace;
}
```

Tailwind 扩展：

```js
fontFamily: {
  sans: ['var(--font-sans)'],
  mono: ['var(--font-mono)'],
}
```

### 3.2 字阶

| Token | 尺寸 | 行高 | 用途 |
|---|---|---|---|
| `text-xs` | 12px | 16px | 时间戳、元数据、helper text |
| `text-sm` | 14px | 20px | 标签、导航、次要文本 |
| `text-base` | 16px | 24px | 正文、输入框、按钮 |
| `text-lg` | 20px | 28px | 卡片标题、区块标题 |
| `text-xl` | 24px | 32px | 页面副标题、弹窗标题 |
| `text-2xl` | 32px | 40px | 页面大标题 |

Tailwind 扩展（覆盖默认）：

```js
fontSize: {
  xs: ['12px', { lineHeight: '16px' }],
  sm: ['14px', { lineHeight: '20px' }],
  base: ['16px', { lineHeight: '24px' }],
  lg: ['20px', { lineHeight: '28px' }],
  xl: ['24px', { lineHeight: '32px' }],
  '2xl': ['32px', { lineHeight: '40px' }],
}
```

### 3.3 字重

| 字重 | 用途 |
|---|---|
| 400 | 正文、段落 |
| 500 | 标签、导航、按钮 |
| 600 | 卡片标题、区块标题 |
| 700 | 页面标题、强强调 |

避免使用 100–300 超细体，避免滥用 800/900。

### 3.4 排版规则

- 页面标题：`text-2xl font-bold`。
- 区块标题：`text-lg font-semibold`。
- 标签：`text-sm font-medium`。
- 正文段落最大宽度控制在 `65ch` 左右，避免一行过长。
- 等宽字体仅用于：ID、时间戳、版本号、技术参数。

---

## 4. 间距与尺寸

### 4.1 间距 Token

基于 4px 网格，沿用 Tailwind 默认间距：

| Token | 值 | 用途 |
|---|---|---|
| `1` | 4px | 图标与文字间隙、紧凑内联 |
| `2` | 8px | 小堆叠、紧凑控件 |
| `3` | 12px | 表单字段内部、小卡片内边距 |
| `4` | 16px | 默认组件内边距、控件组 |
| `6` | 24px | 区块间距、卡片网格 |
| `8` | 32px | 页面级节奏、主要区块 |
| `10` | 40px | 页面大标题上下留白 |
| `12` | 48px | 设置页/空状态大留白 |

### 4.2 布局尺寸

| 元素 | 尺寸 |
|---|---|
| 侧边栏展开 | `w-64` (256px) |
| 侧边栏折叠 | `w-20` (80px) |
| 顶栏高度 | `h-14` (56px) |
| 设置页左侧导航 | `w-56` (224px) |
| 内容区最大宽度 | `max-w-3xl` / `max-w-5xl` 按页面 |
| 按钮最小高度 | `h-9` (36px) |
| 输入框最小高度 | `h-10` (40px) |
| 触控目标 | ≥ 44×44px |

---

## 5. 圆角与形状

| Token | 值 | 用途 |
|---|---|---|
| `--radius` | `1rem` (16px) | 卡片、面板、弹窗、Sheet |
| `rounded-full` | 9999px | 按钮、输入框、选择器、Tab、Badge |
| `rounded-2xl` | `1rem` | Textarea、大卡片、图片缩略图 |
| `rounded-xl` | `0.75rem` | Alert、小面板 |

**规则**：
- 所有交互元素（可点击、可输入）优先使用 pill。
- 多行文本域和大型媒体容器使用大圆角，避免过高胶囊感。
- 不使用尖角矩形按钮。

---

## 6. 阴影与层级

### 6.1 无阴影原则

- UI 组件不使用 `box-shadow` 制造 elevation。
- 按钮、输入框、卡片、Tab 均移除 `shadow-sm` / `shadow`。
- 弹窗/Sheet 的分离感通过以下方式实现：
  - 居中布局 + 充足留白
  - `backdrop`：`bg-black/40`（浅色模式）、`bg-black/60`（深色模式）
  - 1px 边框

### 6.2 唯一例外

原生 `<audio>` 控件不可自定义，保持浏览器默认外观，仅通过外层容器约束尺寸。

### 6.3 Z-Index

| 层级 | 值 |
|---|---|
| Dropdown / Select / Popover | 50 |
| Dialog / Sheet / Toast | 50–100 |
| Tooltip | 100 |

---

## 7. 组件规范

### 7.1 Button

**形态**
- pill，无阴影，`h-9 px-4`，文字 `text-sm font-medium`。
- 图标尺寸 `16px`，与文字间距 `8px`。

**变体**

| 变体 | 样式 |
|---|---|
| Primary | `bg-primary text-primary-foreground hover:bg-primary/90` |
| Secondary | `border border-border bg-transparent text-foreground hover:bg-secondary` |
| Ghost | `hover:bg-secondary hover:text-foreground` |
| Destructive | `bg-destructive text-destructive-foreground hover:bg-destructive/90` |
| Outline | `border border-border bg-background hover:bg-secondary` |
| Link | `text-foreground underline-offset-4 hover:underline` |
| Disabled | `disabled:opacity-50 disabled:pointer-events-none` |

**Focus-visible**

```css
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

**尺寸**

| 尺寸 | 样式 |
|---|---|
| sm | `h-8 rounded-full px-3 text-xs` |
| default | `h-9 rounded-full px-4 text-sm` |
| lg | `h-10 rounded-full px-6 text-base` |
| icon | `h-9 w-9 rounded-full` |

### 7.2 Input / PasswordInput

```css
flex h-10 w-full items-center rounded-full border border-input bg-transparent px-4 text-base
placeholder:text-muted-foreground
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
disabled:cursor-not-allowed disabled:opacity-50
md:text-sm
```

- 无 `shadow-sm`。
- 密码框的眼睛按钮使用 `ghost` icon button，位于输入框右侧内部。

### 7.3 Textarea

```css
flex min-h-[80px] w-full rounded-2xl border border-input bg-transparent px-4 py-3 text-base
placeholder:text-muted-foreground
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

### 7.4 Select

- Trigger 与 Input 同形，右侧 `ChevronDown` 图标 `16px`。
- Content 使用 `rounded-2xl border bg-popover p-1`。
- Item hover 使用 `bg-accent text-accent-foreground`。

### 7.5 Tabs

```css
/* TabsList */
inline-flex h-10 items-center rounded-full bg-muted p-1 text-muted-foreground

/* TabsTrigger */
inline-flex items-center justify-center rounded-full px-4 py-1.5 text-sm font-medium transition-all
data-[state=active]:bg-primary data-[state=active]:text-primary-foreground
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

- 选中态同时填充 + 字色反转；不依赖下划线。

### 7.6 Card

```css
rounded-2xl border border-border bg-card p-5 text-card-foreground
```

- 无阴影。
- 逆色卡片（Inverse Card）用于高强调空状态或 CTA：

```css
rounded-2xl bg-primary p-6 text-primary-foreground
```

### 7.7 Alert

```css
relative w-full rounded-xl border px-4 py-3 text-sm
```

| 变体 | 样式 |
|---|---|
| Default | `bg-background text-foreground` |
| Success | `border-success/50 text-success` |
| Warning | `border-warning/50 text-warning` |
| Destructive | `border-destructive/50 text-destructive` |

- 必须伴随图标 + 标题/描述，不单独用颜色表达状态。

### 7.8 Dialog / Sheet

```css
/* Overlay */
bg-black/40 dark:bg-black/60

/* Content */
rounded-2xl border bg-card p-6
```

- 关闭按钮使用 ghost icon button。
- 无阴影。

### 7.9 Toast（Sonner）

- 位置：右上角。
- 成功使用 `bg-primary text-primary-foreground`；错误使用 `bg-destructive text-destructive-foreground`。
- 重写 `sonner.tsx` 移除默认阴影，使用 border + bg-card。

### 7.10 Badge / Tag

```css
inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium
```

| 变体 | 样式 |
|---|---|
| Default | `border-border bg-transparent text-foreground` |
| Filled | `bg-primary text-primary-foreground` |
| Success | `bg-success text-success-foreground` |
| Warning | `bg-warning text-warning-foreground` |
| Destructive | `bg-destructive text-destructive-foreground` |

### 7.11 Tooltip

```css
rounded-full border bg-popover px-3 py-1.5 text-sm text-popover-foreground
```

- 无阴影，使用边框与 popover 背景。

---

## 8. 布局规范

### 8.1 应用外壳

```
┌──────────────────────────────────────────────────────────────┐
│  Sidebar (256px)  │  Header (56px)                             │
│                   ├───────────────────────────────────────────┤
│                   │                                           │
│                   │  Main Content                             │
│                   │                                           │
└──────────────────────────────────────────────────────────────┘
```

```tsx
<div className="flex h-screen">
  <Sidebar />
  <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
    <Header />
    <main className="flex-1 overflow-hidden">
      {/* workspace */}
    </main>
  </div>
</div>
```

### 8.2 侧边栏

- 浅色：`bg-sidebar border-r border-sidebar-border`
- 深色：`bg-sidebar border-r border-sidebar-border`
- Logo 区：`text-lg font-bold`
- 工作区按钮：pill，宽度 100%，`justify-start gap-3`。
- 当前选中：`bg-primary text-primary-foreground`。
- Hover：`hover:bg-sidebar-accent hover:text-sidebar-accent-foreground`。
- 折叠态宽度 `w-20`，只显示图标。

### 8.3 顶栏

```css
flex h-14 shrink-0 items-center justify-between border-b px-4
```

- 左侧：当前工作区图标 + 标题 `text-lg font-semibold`。
- 右侧：设置入口 ghost icon button。
- 移动端显示汉堡菜单，打开左侧 Sheet。

### 8.4 工作区 1：引导词生成

- 消息列表容器：`flex-1 overflow-y-auto`，内容最大宽度 `max-w-3xl mx-auto`。
- 用户气泡：右对齐，`bg-primary text-primary-foreground rounded-2xl px-4 py-3 max-w-[80%]`。
- AI 气泡：左对齐，`bg-secondary text-foreground rounded-2xl px-4 py-3 max-w-[80%]`。
- 操作栏（复制/保存）：`rounded-full border bg-background p-1`，hover 出现。
- 输入区：底部固定，`AutoResizeTextarea` + Primary Button（pill）。
- 空状态：居中，Inverse Card 或主色图标圆圈 + 标题 + 示例 pill 按钮。

### 8.5 工作区 2：音频生成

- 垂直单栏，内容最大宽度 `max-w-3xl`（任务列表可放宽到 `max-w-4xl`）。
- 引导词选择器、预览区、声音提示输入按顺序排列。
- 生成按钮：Primary pill，高度与 Textarea 对齐或 self-stretch。
- 任务卡片：`rounded-2xl border bg-card p-4`。
- 状态徽章：pill。
- 音频播放器外层容器约束宽度 `w-44`。

### 8.6 工作区 3：产物

- 顶部 Tab 过滤器 + 刷新按钮。
- 产物卡片：`rounded-2xl border bg-card p-4`。
- 桌面端卡片内部使用 flex row 左右分栏；小屏换行。
- 操作按钮组使用 outline/ghost pill button。

### 8.7 设置页

```
┌──────────────────────────────────────────────────────────────┐
│  ←  返回    设置                                             │
├─────────────┬────────────────────────────────────────────────┤
│             │                                                │
│  Nav (224px)│  Main Content (max-w-3xl)                      │
│             │                                                │
│             │  ┌────────────────────────────────────────┐    │
│             │  │ Sticky Footer                           │    │
│             │  └────────────────────────────────────────┘    │
└─────────────┴────────────────────────────────────────────────┘
```

- 页面占满全屏，左侧导航固定 `w-56`。
- 导航项 pill，当前项 `bg-primary text-primary-foreground`。
- 表单内容 `max-w-3xl mx-auto pb-24`（给 sticky footer 留空间）。
- 底部操作栏：

```css
fixed bottom-0 right-0 left-56 flex items-center justify-end gap-4 border-t
bg-background/95 px-6 py-4 backdrop-blur supports-[backdrop-filter]:bg-background/60
```

- 保存按钮 Primary pill，测试按钮 Secondary pill。

---

## 9. 暗色模式

- 通过 `.dark` class 切换（与现有 `applyTheme` 一致）。
- 深色背景使用带绿调的深灰（`#121B18` 附近），避免纯黑压抑。
- 主色在暗色下变浅（sage 300），与深色背景形成足够对比。
- 边框使用半透明白（`1 0 0 / 10%`），保持细微分隔。
- 禁用状态保持可读，不依赖低对比灰。

---

## 10. 动效

### 10.1 时长

| 类型 | 时长 |
|---|---|
| Hover / Active | 100–160ms |
| Popover / Menu | 120–200ms |
| Modal / Sheet | 160–240ms |

### 10.2 缓动

- 默认：`ease-in-out`。
- 颜色/背景过渡：`transition-colors`。
- 尺寸/位置过渡：`transition-all`。

### 10.3 减少动画

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 11. 无障碍

1. **对比度**：所有文本与背景对比度 ≥ 4.5:1；大文本 ≥ 3:1。
2. **Focus-visible**：每个交互元素都有 `2px ring + 2px offset`，颜色 `ring`。
3. **颜色不是唯一状态指示器**：
   - 选中态同时改变填充与字重。
   - 错误态同时显示颜色、图标与文字。
4. **触控目标**：按钮/图标最小 `44×44px`。
5. **表单**：每个输入框关联 `<label>`；错误信息通过 `aria-describedby` 关联。
6. **键盘**：Tab 顺序符合视觉顺序；弹窗焦点捕获；Escape 关闭。
7. **屏幕阅读器**：图标按钮必须有 `aria-label`；加载状态朗读状态变化。

---

## 12. 实施清单

### 12.1 配置与 Token

- [ ] 在 `frontend/src/index.css` 顶部加入 Google Fonts import。
- [ ] 替换 `:root` / `.dark` CSS 变量为本文档色彩系统。
- [ ] 在 `frontend/src/index.css` `@layer base` 中设置 `font-family: var(--font-sans)`。
- [ ] 扩展 `frontend/tailwind.config.js`：
  - `colors.success` / `warning` / `info`
  - `fontFamily.sans` / `mono`
  - `fontSize` 覆盖为 12/14/16/20/24/32px

### 12.2 shadcn 组件覆写

按本文档规范重写以下组件的 className（保留 Radix 行为）：

- [ ] `components/ui/button.tsx`
- [ ] `components/ui/input.tsx`
- [ ] `components/ui/textarea.tsx`
- [ ] `components/ui/select.tsx`
- [ ] `components/ui/tabs.tsx`
- [ ] `components/ui/alert.tsx`（增加 success / warning 变体）
- [ ] `components/ui/dialog.tsx`
- [ ] `components/ui/sheet.tsx`
- [ ] `components/ui/sonner.tsx`（移除阴影，应用主题色）
- [ ] `components/ui/badge.tsx`（如不存在则新增）

### 12.3 业务组件与页面

- [ ] `components/layout/Sidebar.tsx`
- [ ] `components/layout/Header.tsx`
- [ ] `components/layout/MainLayout.tsx`
- [ ] `components/layout/WorkspaceNav.tsx`
- [ ] `components/workspace/ScriptWorkspace.tsx`
- [ ] `components/workspace/ChatMessage.tsx`
- [ ] `components/workspace/ScriptEmptyState.tsx`
- [ ] `components/workspace/AudioWorkspace.tsx`
- [ ] `components/workspace/TaskItem.tsx`
- [ ] `components/workspace/ArtifactWorkspace.tsx`
- [ ] `pages/settings/SettingsLayout.tsx`
- [ ] `pages/settings/SettingsNav.tsx`
- [ ] `pages/settings/SettingsSectionPage.tsx`
- [ ] `components/settings/*.tsx`

### 12.4 检查

- [ ] `npm run lint` 通过。
- [ ] `npm run build` 通过。
- [ ] 浅色/深色模式切换正常。
- [ ] 所有按钮、输入框、Tab 为 pill 形状且无阴影。
- [ ] 主按钮为鼠尾草绿，文字可读。
- [ ] 设置页 sticky footer 正常工作。
- [ ] 键盘 Tab 可以遍历所有交互元素并看到 focus ring。

---

## 13. 验收标准

- [ ] 全局无装饰性阴影、渐变、插画。
- [ ] 主色在所有页面保持一致，绿色仅用于品牌/成功/强调。
- [ ] 浅色模式使用纯白画布，深色模式使用带绿调深灰画布。
- [ ] 所有交互元素为 pill 或 16–20px 大圆角。
- [ ] 文本层级通过字号/字重/间距表达，非颜色。
- [ ] 侧边栏、顶栏、工作区、设置页全部按新系统呈现。
- [ ] 暗色模式下绿色主按钮/选中态对比度满足 WCAG AA。
- [ ] 键盘 focus-visible 状态清晰可见。
- [ ] 构建与 Lint 无错误。
