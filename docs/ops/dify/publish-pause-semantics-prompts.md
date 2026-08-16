# Dify App A / App B 语义停顿 Prompt 发布手册

> 适用版本：Dify 开源版 `1.16.1`、T16 语义停顿协议 v1  
> 适用环境：本机 Dify `http://localhost`，API 地址 `http://localhost/v1`  
> 关联任务：[T16：冥想引导词语义停顿与音频编排协议](../../task/16-meditation-script-pause-semantics.md)  
> 最后更新：2026-08-14

本文用于把 T16 的结构化协议发布到已有的两个 Dify Chatflow：

| 应用 | 作用 | 调用模式 |
|---|---|---|
| App A：冥想引导词生成 | 输出完整 `script_plan` JSON | streaming |
| App B：冥想音频生成 | 输出供应商无关的 `render_plan` JSON | blocking |

本操作只修改 Dify 工作流草稿并发布，不调用 TTS，也不会生成音频。直接验证 App A/App B 会调用其 LLM，可能产生少量模型费用。

---

## 1. 发布前检查

### 1.1 确认 Dify 正常运行

在 PowerShell 中执行：

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://localhost/install
```

预期返回 `200`。如果无法访问，参照 [Dify 日常运维](./dify-operations.md) 启动 Dify。

### 1.2 确认修改的是原有应用

登录 `http://localhost`，进入“工作室”，确认以下两个已有 Chatflow：

- `冥想引导词生成`，即 App A。
- `冥想音频生成`，即 App B。

必须编辑原应用，不要为了更新 Prompt 新建同名应用。发布原应用不会更换其 API Key，项目现有 Dify 配置可以继续使用。

### 1.3 备份当前已发布版本

对 App A、App B 分别执行：

1. 打开应用菜单，使用“导出 DSL”下载当前配置。
2. 文件名建议使用：
   - `meditation-script-gen-before-t16-YYYYMMDD.yml`
   - `meditation-audio-gen-before-t16-YYYYMMDD.yml`
3. 另行复制当前 LLM System Prompt 到本地临时记录。

DSL 可能包含应用结构、模型配置或凭证引用，应按敏感配置保存，不要提交到本仓库。

> 在 Dify 中保存工作流通常只保存草稿；只有点击“发布”后，API 调用才会使用新版本。因此可以先编辑并在控制台预览，确认后再发布。

---

## 2. 发布 App A：结构化引导词

### 2.1 检查工作流

打开 App A 的编排页面，保持主链路为：

```text
开始 / 用户输入 → LLM → 直接回复（Answer）
```

配置要求：

- 模型：现有 `deepseek-chat`，或项目已验证的等价模型。
- 不要选择 `deepseek-reasoner`。如果模型节点提供“思考模式 / Thinking / Reasoning”开关，应关闭该开关，避免把 `<think>…</think>` 输出到业务响应。
- 对话历史：保留现有上下文配置，建议 6 轮。
- Answer 节点：只输出 LLM 节点的完整文本结果，不添加前后缀。
- 不增加 JSON 代码块包装节点，不把输出转换为 Markdown。

如果 LLM 节点有单独的 User Prompt，通过 Dify 的变量选择器插入系统用户输入，例如“根据用户当前要求生成或改写完整引导词：`sys.query`”。不要手写类似 `{{#...#}}` 的节点 ID；节点重建后 ID 可能变化。

### 2.2 替换 App A System Prompt

把 LLM 节点的 System Prompt 完整替换为以下内容：

```text
你是一位专业的正念与冥想引导词创作专家。根据用户当前要求和必要的对话历史，创作或改写一份适合朗读的冥想引导词。

你必须只返回一个完整、合法的 JSON 对象。不要输出 Markdown、代码围栏、解释、前言、后记或 JSON 之外的任何字符。多轮改写时，每次仍返回完整的最新版本，不返回局部 patch。

输出结构严格为：
{
  "title": "简洁标题",
  "version": 1,
  "target_duration_seconds": 600,
  "blocks": [
    {
      "text": "完整、自然、可直接朗读的一段引导词。",
      "pause_after": {
        "kind": "paragraph"
      }
    }
  ]
}

内容要求：
1. 使用第二人称，口语化、温柔、平静，避免播音稿腔调和复杂术语。
2. 按“开场安顿 → 主体练习 → 回收注意 → 结束”组织内容。
3. target_duration_seconds 表示完整成品目标时长，必须把朗读、自然停顿和冥想留白都纳入预算。用户未指定时，默认 600 秒。允许范围为 30～7200 秒。
4. block 按完整表达或练习步骤划分。不要按每个逗号或单句机械切块，也不要让相邻 block 重复同一指令。
5. 主体练习必须显式安排 breath、observe 或 practice 留白，不能只依赖标点和换行。
6. blocks[].text 只保存人能阅读和朗读的正文。不得包含 SSML、HTML、XML、Markdown、自定义方括号标记、停顿秒数标记或供应商参数。
7. title 不超过 200 个字符；每个 text 非空；整篇正文不超过 20000 个字符。

pause_after 规则：
1. kind 只能是 short、paragraph、breath、observe、practice、transition、ending、none 之一。
2. short：句间自然短停顿，无其他字段。
3. paragraph：段落或主题转换，无其他字段。
4. breath：给用户完成呼吸练习，必须包含 count，整数 1～10；不得包含 suggested_seconds。
5. observe：安静观察感受、念头或身体；可包含 suggested_seconds，整数 5～60。
6. practice：执行身体扫描、放松或想象练习；可包含 suggested_seconds，整数 5～60。
7. transition：练习阶段过渡，无其他字段。
8. ending：结束前整合留白，无其他字段。
9. none：明确不追加停顿，无其他字段。
10. 不得创造新的 kind，不得输出 null 字段或未定义字段。

JSON 必须能被标准 JSON.parse 直接解析。字符串中的换行和引号必须合法转义。最终只输出 JSON 对象本身。
```

### 2.3 在 Dify 控制台预览

使用以下测试输入：

```text
生成一份 3 分钟的呼吸安住练习。语气温柔，主体安排三次呼吸和一段约 15 秒的观察留白。
```

检查输出：

- 第一个非空字符是 `{`，最后一个非空字符是 `}`。
- 输出中不包含 `<think>` 或 `</think>`；如果仍出现，检查模型是否误选为推理模型或启用了思考模式。
- 包含 `version: 1`、`target_duration_seconds` 和非空 `blocks`。
- `breath` 包含合法 `count`。
- `observe` 可以包含 5～60 的 `suggested_seconds`。
- 正文没有代码围栏、SSML 或 `[停顿]` 等机器标记。

### 2.4 发布 App A

预览通过后：

1. 点击页面右上角“发布”。
2. 确认发布成功提示。
3. 不要重新生成 API Key。
4. 立即执行第 4 章的 App A API 验证，再继续发布 App B。

---

## 3. 发布 App B：音频编排计划

### 3.1 修改开始节点输入变量

打开 App B 的编排页面。在开始节点中删除旧的 `script_content` 输入，创建以下四个变量：

| 变量名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `script_plan` | String / Paragraph | 是 | ScriptPlan JSON 字符串 |
| `pause_profile` | String / Paragraph | 是 | 后端解析后的档案 JSON 字符串 |
| `voice_prompt` | String / Paragraph | 是 | 用户声音描述 |
| `tts_context` | String / Paragraph | 是 | 服务端允许的 provider、model 和 voice 列表 |

变量名必须完全一致并使用小写下划线。后端按这四个名字传值。

### 3.2 把变量接入 LLM 节点

保持主链路为：

```text
开始 → LLM → 直接回复（Answer）
```

在 LLM 节点的 System Prompt 末尾输入区域，通过 Dify 的变量选择器分别插入四个开始节点变量。插入后界面通常会显示变量胶囊或类似 `start.script_plan` 的引用。

不要直接手写变量引用文本。必须点选变量选择器，以便 Dify 保存真实节点 ID。

Answer 节点只输出 LLM 文本结果，不增加 Markdown 或说明。

### 3.3 替换 App B System Prompt

把 LLM 节点的 System Prompt 完整替换为以下内容。最后四个变量位置必须使用 Dify 变量选择器插入对应变量，而不是把尖括号占位符原样留在 Prompt 中。

```text
你是冥想音频编排助理。你只负责把 script_plan 中的语义停顿按 pause_profile 量化，并从 voice_prompt 提取声音控制参数。你不得创作、改写、删减、新增、合并、拆分或重排引导词。

你必须只返回一个完整、合法的 JSON 对象。不要输出 Markdown、代码围栏、解释、前言、后记、SSML、供应商请求体或 JSON 之外的任何字符。

输入说明：
- script_plan 是 JSON 字符串，包含 version、target_duration_seconds 和 blocks。
- pause_profile 是 JSON 字符串，包含 id、version、durations 和 suggested_seconds_factor。
- voice_prompt 是用户的声音描述。
- tts_context 是 JSON 字符串，包含 provider、model、allowed_voices 和 default_voice。

输出结构严格为：
{
  "version": 1,
  "pause_profile_id": "standard_v1",
  "voice": {
    "voice_id": "longanlingxin",
    "rate": 0.86,
    "volume": 1.0,
    "pitch": 1.0,
    "instruction": "温柔、平静、呼吸感自然，语速稍慢"
  },
  "segments": [
    {
      "id": "b1",
      "text": "与输入 block 完全相同的正文",
      "pause_after_ms": 1800,
      "pause_kind": "paragraph",
      "pause_strategy": "silence"
    }
  ]
}

映射与校验规则：
1. version 固定为 1；pause_profile_id 必须等于 pause_profile.id。
2. segments 数量、顺序、id 和 text 必须与 script_plan.blocks 严格一一对应。必须逐字符复制 text，不得润色或修正标点。
3. pause_kind 必须等于对应 block.pause_after.kind。
4. kind=none 时 pause_after_ms=0，pause_strategy=natural。
5. kind=short 时 pause_after_ms=pause_profile.durations.short，pause_strategy=natural。
6. kind=breath 时 pause_after_ms=pause_profile.durations.breath × count，pause_strategy=silence。
7. kind=observe 或 practice 且存在 suggested_seconds 时，pause_after_ms=四舍五入(suggested_seconds × 1000 × pause_profile.suggested_seconds_factor)，pause_strategy=silence。
8. kind=observe 或 practice 且没有 suggested_seconds 时，pause_after_ms=pause_profile.durations[kind]，pause_strategy=silence。
9. kind=paragraph、transition 或 ending 时，pause_after_ms=pause_profile.durations[kind]，pause_strategy=silence。
10. 不得为了满足 60000ms 上限而截断、缩放或猜测时长；必须按公式计算，超限由后端明确拒绝。
11. voice.voice_id 必须来自 tts_context.allowed_voices。用户没有明确指定合法音色时使用 tts_context.default_voice。
12. rate 范围 0.75～1.05，默认 0.9；volume 范围 0～2，默认 1.0；pitch 范围 0.5～2，默认 1.0。
13. instruction 使用具体、客观、简洁的声音描述，不超过 200 个字符。情绪要求合并到 instruction，不输出 emotion 字段。
14. 不得输出未定义字段，不得输出 null，不得在 segment.text 或 instruction 中加入 HTML、XML 或 SSML 标签。
15. 所有毫秒值必须是整数。JSON 必须能被标准 JSON.parse 直接解析。

以下是本次真实输入。将四个尖括号占位位置替换为 Dify 变量选择器插入的变量：

script_plan:
<通过变量选择器插入 script_plan>

pause_profile:
<通过变量选择器插入 pause_profile>

voice_prompt:
<通过变量选择器插入 voice_prompt>

tts_context:
<通过变量选择器插入 tts_context>

最终只输出 JSON 对象本身。
```

### 3.4 在 Dify 控制台预览

为四个输入变量填入以下测试值。

`script_plan`：

```json
{"version":1,"target_duration_seconds":180,"blocks":[{"id":"b1","text":"现在，让自己找到一个舒适的位置。","pause_after":{"kind":"paragraph"}},{"id":"b2","text":"感受三次自然的呼吸。","pause_after":{"kind":"breath","count":3}},{"id":"b3","text":"安静地观察身体此刻的感受。","pause_after":{"kind":"observe","suggested_seconds":20}}]}
```

`pause_profile`：

```json
{"id":"standard_v1","version":1,"durations":{"short":700,"paragraph":1800,"breath":5000,"observe":15000,"practice":18000,"transition":2500,"ending":5000},"suggested_seconds_factor":1.0}
```

`voice_prompt`：

```text
温柔、平静，语速稍慢，避免播音腔
```

`tts_context`：

```json
{"provider":"aliyun","model":"qwen-audio-3.0-tts-plus","allowed_voices":["longanlingxin","longanlufeng"],"default_voice":"longanlingxin"}
```

预期关键结果：

| segment | 时长 | 策略 |
|---|---:|---|
| `b1` paragraph | `1800` | `silence` |
| `b2` breath × 3 | `15000` | `silence` |
| `b3` observe 20 秒 × 1.0 | `20000` | `silence` |

还应确认三个 segment 的 ID、顺序和 text 与输入完全一致，voice_id 为允许列表中的值。

### 3.5 发布 App B

预览通过后：

1. 点击“发布”。
2. 确认发布成功提示。
3. 不要重新生成 API Key。
4. 执行下一章的 App B API 验证。

---

## 4. 直接验证 Dify API

不要把真实 API Key 写入文档、脚本或 Git。以下变量只存在于当前 PowerShell 会话：

```powershell
$env:DIFY_APP_A_KEY = Read-Host '输入 App A API Key'
$env:DIFY_APP_B_KEY = Read-Host '输入 App B API Key'
$difyApi = 'http://localhost/v1'
```

### 4.1 验证 App A

先用 blocking 模式检查最终 JSON；项目实际使用 streaming，下一节再检查流式链路。

```powershell
$headersA = @{ Authorization = "Bearer $env:DIFY_APP_A_KEY" }
$bodyA = @{
    inputs = @{}
    query = '生成一份3分钟呼吸安住练习，包含三次呼吸和15秒观察留白'
    response_mode = 'blocking'
    conversation_id = ''
    user = 'ops-check'
} | ConvertTo-Json -Depth 10

$responseA = Invoke-RestMethod `
    -Method Post `
    -Uri "$difyApi/chat-messages" `
    -Headers $headersA `
    -ContentType 'application/json; charset=utf-8' `
    -Body $bodyA

$appAResult = $responseA.answer | ConvertFrom-Json
$appAResult | ConvertTo-Json -Depth 10
```

通过条件：

- `ConvertFrom-Json` 无异常。
- `$appAResult.version -eq 1`。
- `$appAResult.blocks.Count -gt 0`。
- 所有 kind 都在 T16 允许枚举中。

### 4.2 验证 App B

```powershell
$scriptPlan = @{
    version = 1
    target_duration_seconds = 180
    blocks = @(
        @{ id='b1'; text='现在，让自己找到一个舒适的位置。'; pause_after=@{ kind='paragraph' } },
        @{ id='b2'; text='感受三次自然的呼吸。'; pause_after=@{ kind='breath'; count=3 } },
        @{ id='b3'; text='安静地观察身体此刻的感受。'; pause_after=@{ kind='observe'; suggested_seconds=20 } }
    )
} | ConvertTo-Json -Depth 10 -Compress

$pauseProfile = @{
    id = 'standard_v1'
    version = 1
    durations = @{ short=700; paragraph=1800; breath=5000; observe=15000; practice=18000; transition=2500; ending=5000 }
    suggested_seconds_factor = 1.0
} | ConvertTo-Json -Depth 10 -Compress

$ttsContext = @{
    provider = 'aliyun'
    model = 'qwen-audio-3.0-tts-plus'
    allowed_voices = @('longanlingxin', 'longanlufeng')
    default_voice = 'longanlingxin'
} | ConvertTo-Json -Depth 10 -Compress

$voicePrompt = '温柔、平静，语速稍慢，避免播音腔'
$headersB = @{ Authorization = "Bearer $env:DIFY_APP_B_KEY" }
$bodyB = @{
    inputs = @{
        script_plan = $scriptPlan
        pause_profile = $pauseProfile
        voice_prompt = $voicePrompt
        tts_context = $ttsContext
    }
    query = $voicePrompt
    response_mode = 'blocking'
    conversation_id = ''
    user = 'ops-check'
} | ConvertTo-Json -Depth 10

$responseB = Invoke-RestMethod `
    -Method Post `
    -Uri "$difyApi/chat-messages" `
    -Headers $headersB `
    -ContentType 'application/json; charset=utf-8' `
    -Body $bodyB

$appBResult = $responseB.answer | ConvertFrom-Json
$appBResult | ConvertTo-Json -Depth 10
```

通过条件：

- `ConvertFrom-Json` 无异常。
- 三段时长依次为 `1800`、`15000`、`20000`。
- 三段策略均为 `silence`。
- segment 的 ID、顺序和 text 与输入完全一致。
- voice_id 为 `longanlingxin` 或 `longanlufeng`。
- 不含 `emotion`、`speed`、`output_format` 或 SSML。

完成后清除当前终端中的 Key：

```powershell
Remove-Item Env:DIFY_APP_A_KEY
Remove-Item Env:DIFY_APP_B_KEY
```

---

## 5. 项目端到端验收

启动 Dify、后端和前端后执行：

1. 打开引导词工作区。
2. 输入“生成一份 3 分钟呼吸安住练习”。
3. 确认流式结束后页面展示可读正文，而不是原始 JSON。
4. 确认只有完整 JSON 解析成功后才出现保存入口。
5. 保存脚本，标题可使用 App A 返回的默认标题。
6. 打开音频工作区，选择刚保存的脚本。
7. 选择“标准”停顿档案，填写声音描述并点击“预览编排”。
8. 确认页面显示朗读、自然停顿、冥想留白和预计总时长。
9. 确认本操作没有创建新的 AudioTask，也没有调用 TTS。

建议同时观察后端日志。正常情况下会出现 `[DifyProxy]` 或 `[RenderPlan]`，不应出现本次预览触发的 TTS 合成日志。

---

## 6. 常见故障

| 现象 | 常见原因 | 处理 |
|---|---|---|
| App A 页面一直显示原始 JSON，不能保存 | JSON 不完整、带代码围栏、缺少 `version: 1` 或字段非法 | 在 Dify 调试中复制完整输出，用 `ConvertFrom-Json` 检查；强化“只输出 JSON” |
| App A 提示 `Unexpected token '<'`，响应以 `<think>` 开头 | DeepSeek 推理内容被混入最终响应 | 使用 `deepseek-chat`，关闭 Thinking/Reasoning；前端只兼容完整闭合的前置 think 块，未闭合内容仍会拒绝 |
| App A 首轮正常，多轮改写失败 | 模型返回局部修改或解释文字 | 确认 Prompt 中保留“每次返回完整最新版本”，Answer 节点无前后缀 |
| App B 报输入变量缺失 | 仍在使用旧 `script_content`，或变量名拼错 | 检查四个开始变量，并用变量选择器重新插入 LLM 节点 |
| App B 仍输出 `speed/emotion/output_format` | 修改未发布、项目指向另一 App Key，或修改了错误应用 | 检查已发布版本、应用身份和项目 Dify 设置 |
| preview 返回 422，提示改写正文或顺序 | App B 没有逐字符复制 block | 强化“不得修正标点”，检查 LLM 温度并降低随机性 |
| preview 返回 422，提示停顿时长不一致 | App B 没按档案公式计算，或 Prompt 内变量未注入 | 用第 3.4 节固定样例核对三段数值 |
| preview 返回不允许的 voice_id | App B 自创音色，或忽略 `allowed_voices` | 强化白名单规则；无明确选择时使用 `default_voice` |
| 深度档呼吸停顿超过 60000ms | 例如 `6500 × 10 = 65000`，超过单段协议上限 | 这是预期强校验，不得截断；改写练习结构或减少单 block 的 count |
| 控制台预览正确，API 仍是旧结果 | 只保存了草稿，没有发布 | 回到应用编排页点击“发布” |
| API 返回 401 | 使用了错误、失效或复制不完整的 App Key | 从对应应用“访问 API”页面重新核对；不要混用 App A/App B Key |

---

## 7. 回滚与恢复

### 7.1 尚未发布

如果只编辑了草稿，直接放弃草稿或恢复原 Prompt 即可。线上 API 仍使用上一次已发布版本。

### 7.2 已发布但验证失败

优先在当前应用中修正 Prompt 或变量后重新发布，这样 API Key 不变。

如果必须恢复发布前配置：

1. 参考备份 DSL 和旧 Prompt，把原工作流、输入变量和 Prompt 恢复到当前应用。
2. 在 Dify 控制台预览。
3. 点击“发布”。
4. 重新执行直接 API 验证。

不要直接导入 DSL 并把它当作新应用替换线上应用；新应用通常具有新的 App ID/API Key，会导致项目仍调用旧应用。

> T16 前端和后端要求结构化 App A/App B 协议。若把 Dify 回滚到 T16 以前的纯文本/旧 TTS 参数 Prompt，当前项目将有意拒绝其结果。协议级回滚必须与应用代码回滚一起进行，不能只回滚 Dify。

---

## 8. 发布记录模板

每次发布后建议记录：

```text
发布日期：
操作人：
Dify 版本：
App A 发布结果：成功 / 失败
App B 发布结果：成功 / 失败
App A API 验证：通过 / 未通过
App B API 验证：通过 / 未通过
项目端到端验证：通过 / 未通过
备份 DSL 保存位置：
异常与处理：
```

严禁在发布记录中填写完整 API Key、模型密钥、完整用户引导词或完整生产 render_plan。
