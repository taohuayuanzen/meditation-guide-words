# T16：冥想引导词语义停顿与音频编排协议

> 任务状态：✅ 已完成（2026-08-16）  
> 交付边界：已完成结构化脚本、停顿编排预览和预计时长；实际 TTS、静音拼接和音频下载由 T17 实施。

## 任务目标

改造“先生成引导词，再生成引导语音”的内容协议，使 App A 在创作引导词时同时表达冥想练习所需的语义停顿，App B 将语义停顿和用户选择的停顿档案量化为供应商无关的 `render_plan`。

本任务只负责内容结构、数据契约、校验和预计时长，不调用 TTS、不生成或拼接音频。完成后的链路为：

```text
App A 生成引导词正文 + 语义停顿
  → 保存可读正文 + script_plan
  → 用户选择停顿档案并填写声音描述
  → App B 生成结构化 render_plan
  → 后端校验并计算预计时长
  → 交给 T17 渲染
```

## 实施结果

| 模块 | 实施结果 |
|---|---|
| Script 协议 | 新增强类型 `ScriptPlan`、`ScriptBlock`、`SemanticPause`；服务端根据 blocks 统一生成可读 `content` |
| 数据迁移 | `scripts` 增加可空 `script_plan`，迁移幂等；历史数据保持 `null`，不推断、不改写 |
| App A 链路 | 支持流式接收完整 JSON，结束后解析为可读正文；结构不完整或非法时禁止保存 |
| 模型输出兼容 | 可安全剥离完整闭合的前置 `<think>…</think>` 和 JSON 代码围栏；未闭合思考或夹杂其他文字仍拒绝 |
| 停顿档案 | 后端集中定义 `gentle_v1`、`standard_v1`、`deep_v1`，并通过只读 API 暴露 |
| App B 链路 | 新增供应商无关的 `AudioRenderPlan`、声音参数和 segment 强校验；App B 不得改写正文、顺序或策略 |
| Preview API | 新增 `POST /api/audio-render-plans/preview`，负责读取 Script、调用 App B、复算停顿和返回 `zh_v1` 时长摘要 |
| 安全约束 | 校验版本、档案、voice/model、参数范围、SSML/XML、段落对应关系、停顿误差和产品时长上限 |
| 前端工作区 | 可选择三档停顿档案、填写声音描述、预览朗读/自然停顿/确定性留白和预计总时长 |
| 旧脚本 | 返回 `pause_capable=false`，仍可查看、编辑和删除，但不能进入可控留白 preview |
| 运维文档 | 已提供 Dify Prompt 发布、工作流同步故障修复和 API 验证手册 |

### 已验证链路

```text
App A 结构化输出
  → 前端解析并保存 ScriptPlan
  → Script API 生成纯文本 content
  → 音频工作区选择停顿档案
  → App B 返回 render_plan
  → 后端强校验与标准化
  → 前端显示预计时长
```

实际工作区已能完成 App A 结构化脚本保存和 App B 编排预览。Preview 完成后不显示“生成音频”步骤属于本任务设计边界，并非 T16 缺陷；后续链路见 [T17：冥想音频分段合成、静音拼接与任务快照](./17-meditation-audio-render-pipeline.md)。

### 验证结果

- 后端全量测试：`138 passed`。
- 前端 TypeScript/Vite 构建通过。
- 前端 Biome 检查通过。
- 新增测试不访问真实 Dify、TTS 或付费模型。
- 前端构建仍有既存的单 chunk 超过 500 kB 警告，不影响 T16 功能验收。

### 运维入口

- [App A / App B Prompt 发布手册](../ops/dify/publish-pause-semantics-prompts.md)
- [Dify 编排页同步故障修复手册](../ops/dify/fix-workflow-sync-secret-key.md)

---

## 前置依赖

- 现有工作区 1、工作区 2、Script CRUD、Dify App A / App B 可用。
- T9 已完成，阿里云 Qwen-Audio-TTS 接入可用。
- Dify App A / App B 的 System Prompt 和工作流允许调整。

参考：

- [阿里云语音合成模型说明](https://help.aliyun.com/zh/model-studio/tts-model)
- [非实时语音合成](https://help.aliyun.com/zh/model-studio/non-realtime-tts-user-guide)
- [Qwen-Audio-TTS/CosyVoice HTTP API](https://help.aliyun.com/zh/model-studio/cosyvoice-tts-http-api)

---

## 已确认决策

| 决策项 | 结果 |
|---|---|
| 首期目标 | 优先保证冥想留白可控，同时改善自然微停顿 |
| 默认模型 | 保留 `qwen-audio-3.0-tts-plus` |
| 停顿来源 | App A 输出语义停顿，App B 负责量化 |
| 数据表达 | 正文保持可读；结构化计划单独保存；业务数据不保存原始 SSML |
| 总时长口径 | 预计总时长包含语音、自然停顿和冥想留白 |
| 停顿档案 | 提供“轻柔 / 标准 / 深度”三档 |
| 用户控制 | 首期只选择档案并查看预计时长，不做逐段时间轴编辑 |
| 旧脚本 | 首期不兼容旧格式脚本，不要求自动推断或批量迁移 |
| 多供应商 | `render_plan` 保持供应商无关 |

> 旧脚本规则以“不兼容”为最终结论：`script_plan` 为空的历史脚本仍可查看、编辑、删除，但不能进入新的可控留白生成链路。历史音频任务及已生成文件不受影响。App B 自动推断旧脚本停顿不属于本任务范围。

---

## 范围

### 包含

- App A 的语义停顿类型和结构化输出协议
- Script 的纯文本正文与 `script_plan` 分离存储
- 三档停顿档案及版本化配置
- App B 的 `render_plan` 输出协议
- `render_plan` 后端强校验、标准化和预计时长计算
- 新旧脚本能力标识
- Dify Prompt、前后端类型、接口与单元测试

### 不包含

- TTS 模型调用、静音生成、FFmpeg 拼接和最终音频编码
- 逐段停顿编辑器或时间轴 UI
- 旧脚本自动推断、批量迁移或自动改写
- 把 SSML 写入 Script 或 `render_plan`
- 切换默认模型到 CosyVoice
- 真实付费 TTS 联调

---

## 1. Script 内容模型

扩展 `scripts`，增加可空 JSON 字段 `script_plan`。建议的数据结构：

```json
{
  "version": 1,
  "target_duration_seconds": 600,
  "blocks": [
    {
      "id": "b1",
      "text": "慢慢地，让身体找到一个稳定而舒适的位置。",
      "pause_after": {
        "kind": "paragraph"
      }
    },
    {
      "id": "b2",
      "text": "感受一次自然的吸气，再感受一次自然的呼气。",
      "pause_after": {
        "kind": "breath",
        "count": 3
      }
    },
    {
      "id": "b3",
      "text": "暂时不需要改变什么，只是安静地观察。",
      "pause_after": {
        "kind": "observe",
        "suggested_seconds": 20
      }
    }
  ]
}
```

约束：

- `Script.content` 继续保存不含机器标签、SSML 或停顿标记的可读正文。
- `Script.script_plan.blocks[].text` 与正文内容一致；保存时由服务端根据 blocks 规范化生成 `content`，避免双份内容漂移。
- `block.id` 在单个脚本内唯一，修改脚本结构时重新生成即可；首期不承担跨版本逐块追踪。
- `target_duration_seconds` 表示完整成品音频目标时长，不是纯朗读时长。
- `script_plan=null` 表示旧格式脚本。
- 不在 `script_plan` 中存放具体毫秒值；毫秒值由 App B 按停顿档案量化。

### 1.1 语义停顿类型

首期固定支持：

| `kind` | 含义 | 可选参数 |
|---|---|---|
| `short` | 句间自然短停顿 | 无 |
| `paragraph` | 段落或主题转换 | 无 |
| `breath` | 给用户完成呼吸练习 | `count: 1～10` |
| `observe` | 安静观察感受、念头或身体 | `suggested_seconds: 5～60` |
| `practice` | 执行身体扫描、放松或想象练习 | `suggested_seconds: 5～60` |
| `transition` | 从一个练习阶段过渡到下一阶段 | 无 |
| `ending` | 结束前的整合留白 | 无 |
| `none` | 明确不追加停顿 | 无 |

要求：

- App A 只允许输出上述枚举，不得创造自由文本类型。
- `suggested_seconds` 是内容作者建议，不是最终时长；App B 可结合档案调整，但必须保留在允许范围内。
- 微观逗号节奏不逐个建 block，由标点、语音指令和 TTS 模型自然处理。
- block 应按完整表达或练习步骤划分，避免一句一段导致过多 TTS 请求。

---

## 2. App A：引导词生成协议

调整 Dify App A，使模型输出严格 JSON，而不是直接把混有停顿标记的文本作为最终业务数据。建议响应：

```json
{
  "title": "十分钟呼吸安住练习",
  "target_duration_seconds": 600,
  "blocks": [
    {
      "text": "现在，让自己找到一个舒适的位置。",
      "pause_after": { "kind": "paragraph" }
    }
  ]
}
```

Prompt 要求：

- 使用第二人称、口语化、温柔且避免播音稿腔调。
- 按“开场安顿 → 主体练习 → 回收注意 → 结束”组织内容。
- 多轮改写时，每次返回完整的最新结构，不返回局部 patch；工作区始终以最后一次完整响应作为待保存版本。
- 目标时长预算必须包含停顿与留白，不能继续按全文朗读时长生成文字。
- 主体练习必须显式安排呼吸、观察或练习留白；不能只依靠句号和换行。
- 避免相邻 block 重复表达同一指令。
- 只输出允许的语义类型和有效参数。
- 不输出 SSML、Markdown、XML、自定义方括号标记或具体音频供应商参数。

### 2.1 流式体验

现有 App A 使用 streaming。实现时可采用以下任一种方式，但最终落库协议必须一致：

1. Dify 工作流流式返回完整 JSON，前端增量提取并渲染已完成的 `blocks[].text`。
2. Dify 工作流分别输出可展示正文和最终结构化结果，由结束事件提交完整 `script_plan`。

推荐优先采用第 1 种，避免额外 LLM 调用。解析失败时不得只保存一份无法关联停顿的纯文本；应提示用户重新生成或继续改写。

---

## 3. 停顿档案

停顿档案使用稳定 ID 和版本号，显示名称走 i18n：

```text
gentle_v1   轻柔
standard_v1 标准
deep_v1     深度
```

建议首版基线：

| 语义类型 | 轻柔 | 标准 | 深度 |
|---|---:|---:|---:|
| `short` | 500ms | 700ms | 900ms |
| `paragraph` | 1200ms | 1800ms | 2500ms |
| `breath` 每次 | 4000ms | 5000ms | 6500ms |
| `observe` 默认 | 8000ms | 15000ms | 25000ms |
| `practice` 默认 | 10000ms | 18000ms | 30000ms |
| `transition` | 1800ms | 2500ms | 3500ms |
| `ending` | 3000ms | 5000ms | 8000ms |

档案规则：

- `suggested_seconds` 存在时，以建议值为基准，并按档案系数调整：轻柔 `0.75`、标准 `1.0`、深度 `1.35`。
- 单次量化结果限制在 `0～60000ms`；超过范围直接校验失败，不静默接受。
- `breath.count × 每次呼吸时长` 可超过 10 秒，T17 负责后端静音拼接。
- 档案定义集中在后端单一模块，并通过只读 API 提供给前端；Dify 只接收档案 ID 和已解析的档案参数，避免 Prompt 内另存一份漂移配置。
- 档案 ID 必须写入 `render_plan`，后续调整 v2 时不能改变已有 v1 任务。

---

## 4. App B：音频编排输出

App B 不再只返回松散的 `voice_id/speed/volume/emotion`。输入至少包含：

```json
{
  "script_plan": {},
  "pause_profile": {
    "id": "standard_v1",
    "durations": {}
  },
  "voice_prompt": "温柔、平静，语速稍慢，避免播音腔",
  "tts_context": {
    "provider": "aliyun",
    "model": "qwen-audio-3.0-tts-plus",
    "allowed_voices": ["longanlingxin", "longanlufeng"],
    "default_voice": "longanlingxin"
  }
}
```

输出严格遵循：

```json
{
  "version": 1,
  "pause_profile_id": "standard_v1",
  "voice": {
    "voice_id": "longanlingxin",
    "rate": 0.86,
    "volume": 1.0,
    "pitch": 1.0,
    "instruction": "温柔、平静、呼吸感自然，语速稍慢，避免播音腔"
  },
  "segments": [
    {
      "id": "b1",
      "text": "现在，让自己找到一个舒适的位置。",
      "pause_after_ms": 1800,
      "pause_kind": "paragraph",
      "pause_strategy": "silence"
    }
  ]
}
```

规则：

- `segments` 顺序和文本必须与 `script_plan.blocks` 一一对应；App B 不得改写、删减或新增引导词。
- App B 只负责量化停顿和提取声音控制参数。
- `pause_strategy` 只允许 `natural` 或 `silence`：`short` 固定为 `natural`，其余有时长的语义停顿固定为 `silence`。App B 不得自行改变策略。
- `natural` 的毫秒值用于预计时长与节奏提示，不要求后端插入等长静音；`silence` 的毫秒值必须由 T17 确定性渲染。
- `voice_id` 必须来自服务端传入的允许列表；不再允许生成描述性占位符。
- `rate` 限制为 `0.5～2.0`，冥想首期建议限制为 `0.75～1.05`。
- `volume` 限制为 `0～2.0`，`pitch` 限制为 `0.5～2.0`。
- `instruction` 使用具体、客观、简洁的声音描述；不得包含供应商不支持的虚构参数。
- `emotion` 不再作为独立无消费字段输出，情绪要求合并到 `instruction`。
- 不输出 SSML 或最终供应商请求体。

---

## 5. 后端校验与标准化

新增强类型 Pydantic 模型，禁止 API 继续接收未经约束的任意 `dict` 作为可信计划。建议包括：

```text
ScriptPlan
ScriptBlock
SemanticPause
PauseProfile
AudioRenderPlan
AudioRenderSegment
VoiceRenderParams
```

服务端校验至少覆盖：

1. 版本号受支持。
2. 档案 ID 存在且版本匹配。
3. segment 数量、ID、顺序和文本与 script plan 完全一致。
4. 每段文本非空，整篇总字符数不超过服务端安全上限。
5. `pause_after_ms` 为整数且在范围内，`pause_strategy` 与 pause kind 的固定映射一致。
6. App B 的停顿时长与档案计算结果一致；允许的舍入误差不超过 50ms。
7. voice/model 组合有效。
8. rate、volume、pitch、instruction 长度符合当前模型能力。
9. 禁止 HTML、XML 和 SSML 标签混入 segment 文本。
10. 总停顿时长和预计总时长在产品限制内。

App B 返回无效数据时返回明确、可诊断的错误，不得静默回退到“整篇一次合成”。

---

## 6. 预计时长

预计总时长统一定义为：

```text
estimated_total_ms
  = estimated_speech_ms
  + natural_pause_budget_ms
  + deterministic_pause_ms
```

其中：

- `deterministic_pause_ms` 为 `pause_strategy=silence` 的 `segments[].pause_after_ms` 之和。
- `estimated_speech_ms` 根据正文字符、语言、rate 和校准后的中文基础语速估算。
- `natural_pause_budget_ms` 包含 `pause_strategy=natural` 的语义短停顿，以及逗号、句号等模型内部微停顿的校准预算，避免预计时长系统性偏短。
- 首版估算算法集中在后端，返回 `estimation_version`；不能由前端自行重复计算。

建议响应摘要：

```json
{
  "estimated_speech_seconds": 412,
  "estimated_natural_pause_seconds": 34,
  "deterministic_pause_seconds": 146,
  "estimated_total_seconds": 592,
  "target_duration_seconds": 600,
  "duration_delta_seconds": -8,
  "estimation_version": "zh_v1"
}
```

验收容差：首期预计总时长与最终实测时长误差目标为 `±10%`；完成一轮真实样本后允许单独校准估算常量，不改写历史任务的估算快照。

---

## 7. API 与数据迁移

### Script API

- 创建、更新和详情响应增加 `script_plan`、`pause_capable`。
- `pause_capable = script_plan != null && version_supported`。
- 列表接口可只返回 `pause_capable` 和目标时长，避免重复传输完整 plan；详情接口返回完整 plan。
- 服务端根据 plan 生成 `content`，客户端不得提交互相冲突的两份正文。

### Render plan API

建议新增后端业务端点：

```text
POST /api/audio-render-plans/preview
```

职责：

1. 读取 Script 和当前非敏感 TTS 上下文。
2. 解析停顿档案。
3. 调用 Dify App B。
4. 校验并标准化 `render_plan`。
5. 返回计划和预计时长摘要。
6. 不创建 AudioTask、不调用 TTS。

前端不再直接信任 `/api/dify/audio/chat` 返回的 JSON。

### 迁移

- 为 `scripts` 增加可空 `script_plan`，迁移必须幂等。
- 现有记录保持 `null`，不自动推断、不改写正文。
- 不改变历史 Script ID、标题、内容和时间字段。

---

## 8. 自动测试要求

至少覆盖：

1. App A 合法结构可生成纯文本 content 和 script plan。
2. 非法 JSON、未知 pause kind、非法 count/seconds 被拒绝。
3. content 与 blocks 不会产生双份内容漂移。
4. 三档停顿档案映射和 suggested seconds 系数正确。
5. 档案版本升级不会改写 v1 定义。
6. App B 不得改写 segment 文本或顺序。
7. 非法 voice、rate、volume、pitch、instruction 被拒绝。
8. SSML/XML 混入业务文本时被拒绝。
9. 预计时长包含自然停顿和确定性留白。
10. preview API 不创建任务、不调用 TTS。
11. 旧脚本 `pause_capable=false`，不能创建新 render plan。
12. 数据迁移幂等并保持旧脚本内容不变。
13. 日志不包含完整引导词、API Key 或完整 render plan。
14. 所有 Dify 调用使用 Mock，不访问真实外部服务。

---

## 9. 验收标准

- [x] App A 可稳定生成纯文本正文和版本化 `script_plan`
- [x] Script 正文不包含 SSML、XML 或机器停顿标记
- [x] 语义停顿类型和参数均经过后端强校验
- [x] 三档停顿档案具有稳定 ID、版本和集中定义
- [x] App B 只量化停顿和声音参数，不改写正文
- [x] `render_plan` 与供应商无关且不包含 SSML
- [x] voice/model 组合由服务端允许列表约束
- [x] 预计总时长包含语音、自然停顿和冥想留白
- [x] preview API 不调用 TTS、不创建 AudioTask
- [x] 旧脚本明确标记为不支持可控留白，不自动迁移
- [x] 自动测试不调用真实 Dify 或付费模型

---

## 预计涉及文件

### 新增

```text
backend/app/schemas/script_plan.py
backend/app/schemas/audio_render_plan.py
backend/app/services/pause_profiles.py
backend/app/services/render_plan_service.py
backend/app/routers/audio_render_plans.py
backend/tests/test_pause_profiles.py
backend/tests/test_render_plan_service.py
backend/tests/test_audio_render_plans.py
docs/task/16-meditation-script-pause-semantics.md
```

### 修改

```text
backend/app/db_migrations.py
backend/app/models/script.py
backend/app/schemas/script.py
backend/app/routers/scripts.py
backend/app/routers/dify_proxy.py
backend/tests/test_scripts.py
backend/tests/test_dify_proxy.py
frontend/src/types/index.ts
frontend/src/services/scriptService.ts
frontend/src/services/difyService.ts
frontend/src/components/workspace/ScriptWorkspace.tsx
docs/task/03-dify-setup.md
docs/tech/tech-spec.md
```

---

## 实施顺序

1. 定义 `script_plan`、语义停顿和三档档案的强类型协议。
2. 增加 Script 数据字段、迁移和 CRUD 校验。
3. 调整 App A Prompt 与前端流式解析/保存逻辑。
4. 调整 App B Prompt，使其输出 `render_plan`。
5. 新增 preview 服务，校验 App B 输出并计算预计时长。
6. 完成迁移、服务和 API 自动测试。
7. 更新 Dify 配置说明与技术文档。

---

## 风险备注

- Dify 流式 JSON 可能出现中途不可解析状态，前端应只在结构完整后允许保存。
- App A 生成的目标时长只是内容预算，最终时长仍受音色、rate 和模型韵律影响。
- 停顿档案数值是首版基线，需要用 T18 的真实 A/B 样本校准。
- 不兼容旧脚本会使历史脚本无法进入新生成链路，界面必须给出明确说明，不能表现为系统故障。
