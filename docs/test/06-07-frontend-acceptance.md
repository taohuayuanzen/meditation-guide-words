# T6 + T7 前端统一验收测试用例

> 日期：2026-08-05
> 适用范围：工作区 1（引导词生成）与工作区 2（音频生成）前端功能
> 关联任务：`docs/task/06-frontend-workspace1.md`、`docs/task/07-frontend-workspace2.md`
> 说明：本用例用于 T6/T7 完成后统一验收，包含环境准备、自动化回归与手工 E2E 用例。

---

## 一、环境准备

前置条件：

| # | 依赖 | 说明 |
|---|------|------|
| 1 | Dify 运行 | `docker ps` 应显示 15 个容器，`http://localhost` 可访问 |
| 2 | Dify 两个 App 已配置 | App A 引导词生成、App B 音频参数解析，Key 已写入 `backend/.env` |
| 3 | 后端已配置 | 按 `docs/ops/backend/backend-startup.md` 启动，`http://localhost:8000/api/health` 返回 `{"status":"ok"}` |
| 4 | TTS 凭证已配置 | 按 `docs/ops/t5-tts-operations.md` 配置，`test-tts` 返回 ok |
| 5 | 数据库已重建 | T5 新增 `retry_count` 列，开发库需删除重建 |
| 6 | Worker 已启动 | `uv run python -m app.services.audio_worker`（T7 音频生成必需） |

启动步骤：

```powershell
# 终端 1：后端
cd C:\projects\apps\meditation-guide-words\backend
uv run uvicorn app.main:app --port 8000

# 终端 2：Worker（仅 T7 需要）
cd C:\projects\apps\meditation-guide-words\backend
uv run python -m app.services.audio_worker

# 终端 3：前端
cd C:\projects\apps\meditation-guide-words\frontend
npm run dev
```

访问 `http://localhost:5173`。

---

## 二、自动化回归（后端）

```powershell
cd C:\projects\apps\meditation-guide-words\backend
uv run pytest          # 预期 31 个用例全部通过
uv run ruff check .    # 预期无错误
```

```powershell
cd C:\projects\apps\meditation-guide-words\frontend
npx biome lint ./src      # 预期无错误
npx biome format ./src    # 预期无改动
npm run build             # 预期 tsc + vite build 通过
```

---

## 三、验收用例

### A. 公共与布局

| 编号 | 优先级 | 用例标题 | 步骤 | 预期结果 |
|------|--------|----------|------|----------|
| C-01 | 高 | 前端可启动 | 运行 `npm run dev`，访问 `http://localhost:5173` | 页面正常加载，无控制台报错 |
| C-02 | 高 | 侧边栏工作区切换 | 点击"音频生成"再点"引导词生成" | 当前项高亮，内容区随之切换 |
| C-03 | 高 | 切换保持会话状态 | 工作区 1 发一条消息 → 切到工作区 2 → 切回 | 工作区 1 消息历史保留（未清空） |
| C-04 | 中 | 设置占位按钮 | 点击顶栏 `⚙️` | 按钮为禁用态，无响应（T8 实现） |
| C-05 | 中 | 中英文语言包就绪 | 检查 `src/i18n/locales/` | zh/en 均含完整键，i18n 初始化无报错 |

### B. 工作区 1：引导词生成

| 编号 | 优先级 | 用例标题 | 步骤 | 预期结果 |
|------|--------|----------|------|----------|
| W1-01 | 高 | 空输入不可发送 | 不输入内容，直接点击"发送" | 发送按钮禁用 |
| W1-02 | 高 | 发送并流式显示 | 输入"生成一段 10 分钟睡前放松冥想引导词"并发送 | 用户消息上屏；AI 回复逐字追加（打字机效果）；自动滚动到底部 |
| W1-03 | 高 | 多轮对话上下文 | 第一轮后继续输入"把它改成 5 分钟版本" | 第二轮回复基于第一轮内容改写（Dify 通过 `conversation_id` 维持上下文） |
| W1-04 | 中 | 流式期间禁用发送 | 在 AI 回复过程中点击"发送" | 按钮禁用，无法并发发送 |
| W1-05 | 高 | 保存引导词 | AI 回复完成后点击"保存引导词" | 按钮短暂显示"已保存"；`/api/scripts` 新增一条记录（标题为时间戳，内容为 AI 全文） |
| W1-06 | 高 | 保存后可被工作区 2 引用 | 切到工作区 2，打开引导词下拉 | 刚保存的引导词出现在列表 |
| W1-07 | 中 | 无回复不可保存 | 从未对话时点击"保存引导词" | 保存按钮禁用 |
| W1-08 | 中 | Dify 未配置报错 | 清空 Dify Key 后发送 | AI 气泡显示错误信息（`Dify 配置未完成...`），不崩溃 |

### C. 工作区 2：音频生成

| 编号 | 优先级 | 用例标题 | 步骤 | 预期结果 |
|------|--------|----------|------|----------|
| W2-01 | 高 | 显示已保存引导词 | 打开工作区 2 | 下拉列出工作区 1 保存的所有引导词；无数据时显示提示文案 |
| W2-02 | 高 | 选择引导词显示预览 | 下拉选择一条引导词 | 只读文本框展示对应内容 |
| W2-03 | 高 | 生成按钮禁用逻辑 | 未选引导词 / 声音描述为空 | 按钮禁用；两项就绪后启用 |
| W2-04 | 高 | 提交生成任务 | 选引导词 + 输入"温柔女声，语速慢，正念风格"→ 生成 | 前端先调 Dify App B 解析 → 创建 `/api/audio-tasks`（status=pending）→ 任务列表新增记录"排队中" |
| W2-05 | 高 | 任务状态轮询 | 观察任务从 pending → processing → completed | 每 3s 自动刷新，状态文案依次变化，完成后停止轮询 |
| W2-06 | 高 | 播放与下载 | 任务完成后 | `<audio>` 控件可在线播放；"下载"可下载到本地文件 |
| W2-07 | 高 | 失败显示与重试 | 配置错误音色触发失败 | 任务显示"失败"与 `error_msg`；点击"重试"后任务回到排队并重新处理 |
| W2-08 | 中 | 声音描述解析失败 | 输入无法解析的声音描述 | 提示"声音描述不清晰，请重试"，**不**创建任务 |
| W2-09 | 中 | Dify 未配置报错 | 清空 Dify Key 后点生成 | 提示创建失败及后端 `detail`，不创建任务 |

### D. 数据一致性（可配合后端接口验证）

| 编号 | 优先级 | 用例标题 | 步骤 | 预期结果 |
|------|--------|----------|------|----------|
| D-01 | 中 | 保存的引导词落库 | 保存后 `curl http://localhost:8000/api/scripts` | 列表含新增记录，`session_id` 为对话 id |
| D-02 | 中 | 任务带 tts_params | 生成后 `curl http://localhost:8000/api/audio-tasks/{id}` | `tts_params` 含 Dify 解析出的 voice_id/speed/volume 等 |
| D-03 | 中 | 下载接口一致性 | 对 completed 任务请求 `/api/audio-tasks/{id}/download` | 返回音频文件（文件头校验：MP3 为 `ID3` 或 `0xFF Ex`） |

---

## 四、用例执行记录

| 编号 | 结果 | 执行人 | 日期 | 备注 |
|------|------|--------|------|------|
| C-01 | ☐ | | | |
| C-02 | ☐ | | | |
| C-03 | ☐ | | | |
| C-04 | ☐ | | | |
| C-05 | ☐ | | | |
| W1-01 | ☐ | | | |
| W1-02 | ☐ | | | |
| W1-03 | ☐ | | | |
| W1-04 | ☐ | | | |
| W1-05 | ☐ | | | |
| W1-06 | ☐ | | | |
| W1-07 | ☐ | | | |
| W1-08 | ☐ | | | |
| W2-01 | ☐ | | | |
| W2-02 | ☐ | | | |
| W2-03 | ☐ | | | |
| W2-04 | ☐ | | | |
| W2-05 | ☐ | | | |
| W2-06 | ☐ | | | |
| W2-07 | ☐ | | | |
| W2-08 | ☐ | | | |
| W2-09 | ☐ | | | |
| D-01 | ☐ | | | |
| D-02 | ☐ | | | |
| D-03 | ☐ | | | |

---

## 五、已知限制

- 工作区 2 依赖 Dify App B 与 TTS 真实凭证，未配置时无法完成生成链路（有对应错误提示）
- 长文本（>5000 字）会由 Worker 置为失败，前端仅显示错误信息
- 任务列表为轮询刷新（3s），非实时推送；T8 可选优化为 SSE 推送
- 语言切换 UI 在 T8 设置页实现，本期仅完成 i18n 框架与全量语言包

## 相关文档

- [T6 任务文档](../task/06-frontend-workspace1.md)
- [T7 任务文档](../task/07-frontend-workspace2.md)
- [T5 操作文档（TTS 凭证）](../ops/t5-tts-operations.md)
- [后端启动与运维指南](../ops/backend/backend-startup.md)
