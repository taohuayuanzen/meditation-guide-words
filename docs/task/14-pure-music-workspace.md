# T14：纯音乐工作区、音乐设置与产物集成

## 任务目标

在 T12、T13 后端能力完成后，新增独立「纯音乐」工作区和「音乐模型」设置，提供结构化 Prompt、目标时长、费用提示、任务进度、试听、格式选择下载和产物管理的完整用户链路。

本任务是纯音乐 MVP 的产品交付与端到端验收任务。

**预计耗时**：1 ～ 1.5 天

---

## 前置依赖

- T12 已完成：音乐配置、任务模型、Fun-Music 调用和源 WAV 下载可用。
- T13 已完成：FFmpeg 后处理、最终 MP3、任务恢复、下载和删除 API 可用。

---

## 范围

### 包含

- 独立「纯音乐」工作区
- 音乐模型设置 UI
- 复制现有阿里云 TTS API Key
- 静态结构化选项
- Prompt 自动拼装、预览和编辑
- 目标时长预设与自定义时长
- 提交前和完成后费用提示
- 任务状态、阶段轮询、试听和重试
- 非持久化播放器音量
- WAV / MP3 下载选择弹窗
- AI 生成标识
- 产物页新增纯音乐类型
- 删除确认、重命名和文件管理
- 中英文文案
- README / 运维说明
- 真实联调前检查与端到端验收

### 不包含

- 引导音频与音乐混合
- 人声 ducking
- 服务端音量处理
- 多段模型生成拼接
- 可编辑预设管理后台
- 生成中强制取消
- MP3 ID3 AI 标签

---

## 1. 导航与工作区

扩展：

```ts
export type Workspace = 'script' | 'audio' | 'music' | 'artifact';
```

导航顺序：

1. 引导词
2. 引导音频
3. 纯音乐
4. 产物

新增：

```text
frontend/src/components/workspace/MusicWorkspace.tsx
frontend/src/components/workspace/MusicTaskItem.tsx
frontend/src/services/musicTaskService.ts
```

整体沿用现有 Audio Workspace 的左右分栏：

- 左侧：音乐创作表单。
- 右侧：可折叠任务列表。

---

## 2. 音乐模型设置

新增：

```text
frontend/src/components/settings/MusicSettings.tsx
frontend/src/pages/settings/MusicSettingsPage.tsx
```

字段：

- Workspace ID
- API Key
- Base URL
- 模型：只读 `fun-music-v1`
- 源格式：只读 WAV
- 最终格式：只读 MP3
- AIGC 尾部水印：默认关闭并展示说明
- “复制当前阿里云 TTS API Key”按钮

复制规则：

- 仅用户点击时复制。
- 复制后作为独立 `music_config.api_key` 保存。
- 后续 TTS Key 改动不自动同步。

连接测试：

- 不隐式调用计费生成。
- 检查配置完整性和 capabilities。
- 若无法通过免费接口验证邀测权限，显示“配置已保存，实际权限将在首次生成时验证”。

---

## 3. 静态预设与 Prompt

新增：

```text
frontend/src/config/musicPresets.ts
```

### 3.1 情绪，可多选

- 平静
- 温暖
- 空灵
- 沉静
- 安全
- 清澈

### 3.2 乐器，可多选

- 钢琴
- 颂钵
- 柔和弦乐
- 长笛
- Drone持续音
- 木质打击乐
- 无明显乐器

### 3.3 环境，可多选

- 雨声
- 海浪
- 溪流
- 森林
- 夜晚
- 篝火
- 风声
- 无自然声

### 3.4 节奏

- 无节拍
- 自由流动
- 极慢
- 缓慢稳定

### 3.5 动态

- 极低动态
- 平稳
- 轻微起伏

### 3.6 Prompt 模板

```text
创作一首纯音乐。
整体情绪{情绪列表}。
使用{乐器列表}，并加入{环境}。
节奏{节奏}，动态{动态}，无突然变化，无强烈高潮。
旋律克制、重复性自然，适合长时间循环播放。
不要人声、吟唱、念白、歌词或任何语言片段。
{用户自由描述}
```

要求：

- 结构化字段变化后更新 Prompt 预览。
- Prompt 预览允许用户继续编辑。
- 提交时发送最终编辑后的 `effective_prompt` 和结构化 `preset_params`。
- 后端仍强制 `is_instrumental=true`。
- 显示版权提示：不要要求模仿具体艺术家、歌曲或标志性旋律。
- 新任务的 `preset_params` 不包含 `scene`。历史任务中已有的 `scene` 原样保留但不在新界面展示，不执行数据迁移。
- 默认值：平静、柔和弦乐、无自然声、无节拍、平稳、5 分钟。
- 情绪、乐器、环境至少各选择一项；“无明显乐器”和“无自然声”分别与同组其他选项互斥。
- 未手工编辑 Prompt 时，结构化字段变化立即同步预览；手工编辑后，字段变化只提示“预设已变化”，由用户点击“应用新预设”后才覆盖当前 Prompt。
- Prompt 模板随当前界面语言切换，`preset_params` 始终保存稳定英文枚举值。

---

## 4. 目标时长与费用提示

时长预设：

- 5 分钟
- 10 分钟
- 15 分钟
- 20 分钟
- 30 分钟

自定义：

- 整数分钟。
- 范围 1～60 分钟。
- 前后端均校验。

提交前提示：

```text
模型按实际生成的源音乐秒数计费；目标长音乐由本地循环生成，不会按目标时长重复调用模型。
参考：若源音乐为 200 秒，按当前公示原价估算约 0.40 元。
```

完成后显示：

```text
源音乐 198 秒 · 估算费用 ¥0.40 · 以阿里云账单为准
```

要求：

- 提交前不得直接用 30 / 60 分钟目标时长计算模型费用。
- 实际估算使用后端返回的 `source_duration_seconds` 和 `estimated_cost`。
- 所有金额标注“估算”，实际以阿里云账单为准。

---

## 5. 配置和环境缺失

纯音乐工作区始终可访问。

进入页面后同时获取：

- `music_config` 配置状态。
- T13 capabilities 状态。

以下情况禁用生成：

- API Key 缺失。
- Workspace ID 缺失。
- FFmpeg 不可用。
- FFprobe 不可用。

页面仍允许：

- 编辑预设和 Prompt。
- 查看已有任务。
- 试听和下载已有产物。

提示必须指出具体缺失项，并提供前往音乐设置的按钮。

---

## 6. 任务列表与播放器

任务 active 时每 3 秒轮询，全部进入 completed / failed 后停止。

任务项展示：

- 结构化标签
- 目标时长
- 状态
- 当前阶段：生成中 / 下载中 / 时长处理中
- 创建和完成时间
- AI 生成徽标
- 源音乐时长
- 估算费用
- 错误信息
- 重试、下载、删除

完成后展示浏览器 `<audio>` 播放器。

音量要求：

- 只修改 HTMLAudioElement 的 `volume`。
- 不调用服务端 API。
- 不写数据库或 localStorage。
- 页面刷新后恢复浏览器或组件默认值。
- 不作为音乐生成参数展示。

MVP 不提供 processing 任务取消按钮；删除 processing 任务时显示后端返回的不可取消提示。

---

## 7. 下载格式选择

点击下载后先调用：

```text
GET /api/music-tasks/{id}/downloads
```

弹窗列出后端返回的全部可用文件：

- 原始 WAV
- 目标时长 MP3

每项展示：

- 格式
- 用途
- 时长
- 文件大小
- 下载按钮

不得假设两个格式一定都存在；失败或处理中任务可能只有 WAV。

---

## 8. 产物页集成

扩展产物类型：

```ts
type ArtifactType = 'audio' | 'music' | 'script';
```

显示名称：

- `audio`：引导音频
- `music`：纯音乐
- `script`：引导词

新增筛选：

- 全部
- 引导音频
- 纯音乐
- 引导词

纯音乐产物展示：

- 最终 MP3 名称
- 目标时长
- 模型
- AI 生成标识
- 创建时间
- 播放器
- 下载、重命名、删除

后端 `artifacts.py` 需要增加 `music` 聚合，并复用 Music Task 下载和删除逻辑，避免出现两套文件生命周期实现。

### 8.1 重命名

- 只重命名最终 MP3 和更新 `file_path`。
- 原始 WAV 保持内部 `{task_id}.wav` 名称。
- 检查目标文件冲突。
- 默认最终文件名保持 `{task_id}_{target_minutes}min.mp3`，不根据 Prompt 或标签自动命名。

### 8.2 删除

确认弹窗必须说明：

- 将删除原始 WAV、最终 MP3 和任务记录。
- 操作不可恢复。
- 以后重新生成会再次调用模型并可能产生费用。

确认后调用 Music Task 删除 API，不直接在前端拼装文件删除请求。

---

## 9. AI 标识

显示位置：

- 音乐任务卡
- 产物卡
- 任务详情 / 下载弹窗

依据后端 `is_ai_generated=true` 展示。

不执行：

- 不修改文件名。
- 不写 MP3 ID3。
- 不向音频尾部追加摩尔斯水印。

---

## 10. i18n、README 与运维说明

更新中英文文案：

- 工作区与设置名称
- 所有预设和结构化选项
- Prompt 预览
- 时长与费用
- 任务阶段
- AI 生成
- WAV / MP3 下载
- FFmpeg 缺失
- 邀测权限错误
- 删除不可恢复

README / 运维文档补充：

- `fun-music-v1` 邀测申请说明
- 北京地域 Workspace ID 和 API Key
- Windows / macOS / Linux 的 FFmpeg 安装和验证
- Music Worker 启停方式
- 原始 WAV 和最终 MP3 目录
- 模型按源音乐秒数计费
- 自动测试不会调用真实模型

---

## 11. 测试与端到端验收

前端不新增自动测试框架。完成后执行 `npm run lint`、`npm run build`，并按 `docs/test/` 中的人工验收清单验证：

1. 导航和 Header 正确切换。
2. 预设生成符合模板的 Prompt。
3. Prompt 编辑结果作为最终内容提交。
4. 预设时长和自定义 1～60 分钟校验。
5. 缺少 Key / Workspace / FFmpeg 时禁用生成。
6. 缺少配置时已有任务仍可查看和下载。
7. active 任务轮询，结束后停止。
8. 生成、下载、处理阶段显示正确。
9. 播放器音量不触发 API 写入。
10. 下载弹窗按真实文件列表展示 WAV / MP3。
11. AI 生成徽标可见。
12. 产物筛选区分引导音频、纯音乐和引导词。
13. 重命名只影响最终 MP3。
14. 删除弹窗包含不可恢复和费用提示。
15. 中英文文案完整。

真实联调已获允许，但仅在全部非计费检查通过后执行：

1. 确认邀测权限、北京地域 Key 和 Workspace ID。
2. 使用默认结构化预设创建一条目标 5 分钟的纯音乐。
3. 最多执行一次模型生成请求；首次失败即停止，不执行付费重试。
4. 确认原始 WAV 与最终 MP3 均存在。
5. 确认 MP3 时长误差不超过 1 秒。
6. 保留真实 MP3，由用户人工试听并确认无可辨识人声、吟唱、歌词或念白；试听不通过时不自动再次生成。
7. 验证播放器、两种格式下载、费用和 AI 标识。
8. 真实计费产物保留；删除生命周期使用本地非计费任务验证。

---

## 验收标准

- [ ] 左侧导航新增独立「纯音乐」工作区
- [ ] 设置页支持独立音乐配置和复制 TTS API Key
- [ ] 复制后的 Key 独立保存，不与 TTS 自动同步
- [ ] 页面提供全部已确认静态预设（不包含场景）
- [ ] Prompt 可自动拼装、预览和编辑
- [ ] 支持 5 / 10 / 15 / 20 / 30 分钟预设
- [ ] 支持自定义 1～60 分钟
- [ ] 提交前费用说明不使用目标时长误算模型费用
- [ ] 完成后显示源时长和实际估算费用
- [ ] 缺少配置或 FFmpeg 时页面可访问但生成禁用
- [ ] 任务列表显示生成、下载和时长处理阶段
- [ ] 完成任务可试听
- [ ] 播放器音量不持久化、不修改文件
- [ ] 下载弹窗列出全部真实存在格式
- [ ] UI 显示 AI 生成标识
- [ ] 文件名和 MP3 ID3 不写 AI 标识
- [ ] 产物页区分引导音频、纯音乐和引导词
- [ ] 重命名只修改最终 MP3
- [ ] 删除弹窗明确说明不可恢复和再次生成费用
- [ ] 删除后源 WAV、最终 MP3 和任务记录均不存在
- [ ] MVP 不提供生成中强制取消
- [ ] 中英文文案、README、`docs/ops/` Windows FFmpeg 安装说明和 `docs/test/` 人工验收清单完整
- [ ] 前端 lint 和生产构建通过，不新增前端自动测试框架
- [ ] 自动测试不调用真实付费接口

---

## 预计涉及文件

### 新增

```text
frontend/src/components/workspace/MusicWorkspace.tsx
frontend/src/components/workspace/MusicTaskItem.tsx
frontend/src/components/settings/MusicSettings.tsx
frontend/src/pages/settings/MusicSettingsPage.tsx
frontend/src/config/musicPresets.ts
frontend/src/services/musicTaskService.ts
```

### 修改

```text
frontend/src/App.tsx
frontend/src/stores/appStore.ts
frontend/src/components/layout/WorkspaceNav.tsx
frontend/src/components/layout/MainLayout.tsx
frontend/src/components/layout/Header.tsx
frontend/src/components/workspace/ArtifactWorkspace.tsx
frontend/src/services/artifactService.ts
frontend/src/services/settingsService.ts
frontend/src/types/index.ts
frontend/src/i18n/locales/zh.json
frontend/src/i18n/locales/en.json
backend/app/routers/artifacts.py
README.md
docs/ops/（新增或更新音乐模型与 FFmpeg 操作说明）
```

---

## MVP 后续候选

- 引导音频与纯音乐混合导出
- 人声 ducking 与响度标准化
- 同一源 WAV 派生多个目标时长文件
- 多段音乐生成与低重复长音频拼接
- 用户自定义预设管理
- 收藏、播放列表和睡眠定时器
- 自动检测生成音乐中的人声片段
