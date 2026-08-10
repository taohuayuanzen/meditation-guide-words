# T11：工作台「产物」页 —— 音频与引导词产物管理

## 任务目标

在工作台左侧 sidebar 新增「产物」入口（位于「音频生成」下方），提供统一的产物管理页：

- 展示两类产物：引导音频（`backend/data/audio`）与引导词文档（`backend/data/scripts`）
- 按类型分类展示（全部 / 音频 / 引导词）
- 支持下载、真实重命名、删除
- 引导词保存时同步落盘为 Markdown 文件

**预计耗时**：1 ~ 1.5 天

---

## 前置依赖

- T6、T7 完成（前端两个工作区已实现）
- T8 完成（设置页、通用配置、音频输出目录已就绪）
- T5 完成（Worker 已能把音频写入磁盘，数据库记录 `file_path`）

---

## 详细步骤

### 1.1 后端：引导词保存时落盘

修改 `backend/app/routers/scripts.py` 的 `create_script`：

- 在写入数据库并 commit 后，根据返回的 `script.id` 生成文件
- 落盘路径：`backend/data/scripts/{title}_{id}.md`
- 文件名需做安全处理：去除非法字符、限制长度，避免路径穿越
- 文件内容模板示例：

  ```markdown
  # {title}

  创建时间：{created_at}
  会话 ID：{session_id}

  ---

  {content}
  ```

- 若 `data/scripts` 目录不存在则自动创建

> 注意：后续更新 `title` 或 `content` 时是否需要同步更新落盘文件，见「关键设计点」。

### 1.2 后端：新增产物模块

#### 1.2.1 路由 `backend/app/routers/artifacts.py`

挂载到 `/api/artifacts`。

**`GET /api/artifacts`**

扫描磁盘并聚合两类产物：

- 音频：读取 `backend/data/audio/*`，按文件名排序；同时关联 `audio_tasks` 表，补充 `script_title`、`created_at`、`task_id`
- 引导词：读取 `backend/data/scripts/*.md`，按文件名排序；同时关联 `scripts` 表，补充 `title`、`script_id`、`created_at`

统一返回：

```json
[
  {
    "id": "audio_1",
    "type": "audio",
    "name": "1.mp3",
    "script_title": "睡前放松引导词",
    "created_at": "2026-08-10T12:00:00Z",
    "task_id": 1
  },
  {
    "id": "script_2",
    "type": "script",
    "name": "睡前放松引导词_2.md",
    "title": "睡前放松引导词",
    "created_at": "2026-08-10T11:00:00Z",
    "script_id": 2
  }
]
```

**`POST /api/artifacts/{artifact_id}/rename`**

请求体：`{ "new_name": "睡前冥想" }`（不带后缀）

- 音频：
  - 解析 artifact_id → `audio_{task_id}`
  - 查询 `audio_tasks` 获取 `file_path`
  - 新文件名：`{new_name}.{ext}`
  - 检查目标文件是否已存在，若存在返回 `409 Conflict`，提示「文件名已存在」
  - 否则 `os.rename` 并更新数据库 `file_path`
- 引导词：
  - 解析 artifact_id → `script_{script_id}`
  - 更新 `scripts.title = new_name`
  - 同步更新磁盘文件名为 `{new_name}_{script_id}.md`
  - 同样检查目标文件是否已存在，存在则返回 `409`

**`GET /api/artifacts/{artifact_id}/download`**

- 音频：`FileResponse(file_path, filename=name)`
- 引导词：从数据库读取内容，以 `text/markdown` 流式返回，文件名使用 `title.md`

**`DELETE /api/artifacts/{artifact_id}`**

- 音频：
  - 删除磁盘文件
  - 删除 `audio_tasks` 对应记录
- 引导词：
  - 删除磁盘 `.md` 文件
  - 删除 `scripts` 对应记录

#### 1.2.2 挂载路由

在 `backend/app/main.py` 中新增：

```python
from app.routers import artifacts

app.include_router(artifacts.router, prefix="/api/artifacts", tags=["artifacts"])
```

### 1.3 后端：工具函数

新增 `backend/app/utils/file_utils.py`（如不存在）：

- `sanitize_filename(name: str) -> str`：去除非法字符、替换空格为下划线、限制长度
- `ensure_dir(path: str) -> None`
- 辅助函数：从产物 id 解析类型和数据库 id

### 1.4 后端：数据库字段

- 音频重命名需要更新 `audio_tasks.file_path`，无需新增字段
- 引导词重命名需要更新 `scripts.title`，无需新增字段

### 1.5 前端：新增产物工作区

#### 1.5.1 扩展 Workspace 类型

`frontend/src/stores/appStore.ts`：

```ts
export type Workspace = 'script' | 'audio' | 'artifact';
```

#### 1.5.2 Sidebar 导航

`frontend/src/components/layout/WorkspaceNav.tsx`：

- 引入图标 `Archive` 或 `FolderOpen`
- 在 `ITEMS` 中追加 `{ value: 'artifact', icon: Archive, labelKey: 'workspace.artifact' }`

#### 1.5.3 MainLayout 渲染

`frontend/src/components/layout/MainLayout.tsx`：

```tsx
import { ArtifactWorkspace } from '@/components/workspace/ArtifactWorkspace';

<div className={currentWorkspace === 'artifact' ? 'h-full' : 'hidden'}>
  <ArtifactWorkspace active={currentWorkspace === 'artifact'} />
</div>
```

#### 1.5.4 产物页组件

新建 `frontend/src/components/workspace/ArtifactWorkspace.tsx`：

- 使用 Tabs：全部 / 音频 / 引导词
- 列表使用 `ScrollArea` + 卡片/行布局
- 每个产物项展示：名称、类型、创建时间、关联引导词标题
- 操作按钮：
  - 下载
  - 重命名（点击弹出 Dialog，输入新名称，校验非空、去重失败时 toast 提示）
  - 删除（二次确认 Dialog）
- 音频项额外展示 inline `audio` 播放器
- 顶部提供刷新按钮

#### 1.5.5 服务层

新建 `frontend/src/services/artifactService.ts`：

```ts
export interface Artifact {
  id: string;
  type: 'audio' | 'script';
  name: string;
  created_at: string;
  // audio
  script_title?: string;
  task_id?: number;
  // script
  title?: string;
  script_id?: number;
}

export async function fetchArtifacts(type?: 'audio' | 'script'): Promise<Artifact[]>;
export async function renameArtifact(id: string, newName: string): Promise<void>;
export function getArtifactDownloadUrl(id: string): string;
export async function deleteArtifact(id: string): Promise<void>;
```

### 1.6 前端：i18n 文案

在 `frontend/src/i18n/locales/zh.json` 和 `en.json` 中补充：

```json
{
  "workspace": {
    "script": "引导词生成",
    "audio": "音频生成",
    "artifact": "产物"
  },
  "artifact": {
    "title": "产物",
    "all": "全部",
    "audio": "音频",
    "script": "引导词",
    "empty": "暂无产物",
    "download": "下载",
    "rename": "重命名",
    "delete": "删除",
    "confirmDelete": "确定删除「{{name}}」？此操作不可恢复。",
    "renameTitle": "重命名",
    "renamePlaceholder": "请输入新名称",
    "renameDuplicate": "该名称已存在，请使用其他名称",
    "createdAt": "创建于"
  }
}
```

### 1.7 测试

后端新增 `backend/tests/test_artifacts.py`：

- 创建脚本后检查 `.md` 文件落盘
- 重命名音频：文件名变更、`file_path` 更新
- 重命名引导词：`title` 变更、磁盘文件名变更
- 重名时返回 409
- 下载音频返回 200
- 下载引导词返回 markdown 内容
- 删除后磁盘文件和数据库记录均不存在

运行：

```bash
cd backend
uv run pytest
```

### 1.8 代码检查

```bash
# 后端
cd backend
uv run ruff check .
uv run ruff format .

# 前端
cd frontend
npm run lint
npm run format
npm run build
```

---

## 关键设计点

| 设计点 | 结论 |
|---|---|
| 引导词是否落盘 | **落盘保存**：保存时写入 `backend/data/scripts/{title}_{id}.md` |
| 产物分类展示 | **Tabs 切换**：全部 / 音频 / 引导词 |
| 重命名范围 | **真实重命名文件**：音频改磁盘文件名并更新 `file_path`；引导词改 `title` 并同步更新磁盘文件名 |
| 引导词下载格式 | **Markdown**：保留标题、创建时间、会话 ID、正文 |
| 删除功能 | **支持**：音频删文件 + 数据库记录；引导词删文件 + 数据库记录 |
| 重名处理 | **不允许覆盖**：目标文件名已存在时返回 `409`，前端 toast 提示「文件名已存在」 |
| 产物 ID 规则 | `audio_{task_id}` / `script_{script_id}`，前端拆分后调用对应逻辑 |
| 更新脚本时是否同步落盘文件 | **不同步**：产物文件是「生成时刻的快照」，后续在产物页重命名/删除不影响原 `scripts` 内容；若需要可后续迭代「重新导出」功能 |

---

## 验收标准

- [ ] Sidebar 出现「产物」入口，位于「音频生成」下方
- [ ] 点击「产物」切换到产物管理页，默认展示全部产物
- [ ] 产物按「音频 / 引导词」Tabs 分类，列表展示名称、创建时间、关联引导词标题
- [ ] 音频产物可在线播放、下载、重命名、删除
- [ ] 引导词产物可下载（Markdown）、重命名、删除
- [ ] 重命名时不允许覆盖已有文件，提示明确
- [ ] 删除后产物从列表、磁盘、数据库中同时移除
- [ ] 保存引导词时自动在 `backend/data/scripts` 生成 `.md` 文件
- [ ] 后端新增 `/api/artifacts` 相关接口并通过测试
- [ ] `uv run pytest` 全部通过
- [ ] `npm run build` 通过，Biome / Ruff 无错误

---

## 关联文档

- `docs/tech/tech-spec.md`
- `docs/prd/meditation-guide-words-prd.md`
- `docs/task/05-tts-and-worker.md`
- `docs/task/07-frontend-workspace2.md`
- `docs/task/08-settings-and-polish.md`

---

## 风险备注

- 文件名安全：必须对 `title` / 用户输入做 `sanitize_filename` 处理，防止路径穿越和非法字符
- 并发重命名：两个请求同时重命名为同名文件时，磁盘检查和重命名之间可能有竞态，可通过数据库唯一约束或异常捕获兜底
- 音频文件与数据库记录不一致：若用户手动删除了 `data/audio` 中的文件，数据库 `file_path` 仍指向缺失文件，产物页下载时应给出清晰提示
- 引导词重命名后，原文件名为 `{旧title}_{id}.md`，新文件名为 `{新title}_{id}.md`，需保证旧文件被正确删除或重命名

---

## 当前进度

- [ ] 待开始
