# I3：Dify 工作流视觉连线存在但草稿端口关系无效

## 缺陷现象

在 Dify 1.16.1 的“引导词智能体”Chatflow 中，画布视觉上存在：

```text
开始 → LLM 2 → 直接回复 2
```

预览时 LLM 可以正常返回内容，但保存或发布检查清单持续提示：

```text
LLM 2：此节点尚未连接到其他节点
直接回复 2：此节点尚未连接到其他节点
```

删除并重新拖拽“开始 → LLM 2”连线后问题仍然存在。

## 影响范围

- 受影响应用：`引导词智能体`
- Dify App ID：`b9f7e107-3684-488e-9850-ca0ed1d25fef`
- 受影响对象：当前 `draft` 工作流
- 不影响当前已发布版本；线上 API 仍使用上一次发布的工作流
- 不影响 LLM 预览、System Prompt 或模型调用本身

## 排查证据

### 1. 画布渲染了两条边

React Flow DOM 中存在：

```text
start-null-1786843450454-target
1786843450454-source-1786843505444-target
```

这说明视觉连线不等于 Dify 发布校验器认可的有效端口关系。

### 2. 开始节点输出端口没有保存

草稿 graph 中“开始 → LLM 2”的边为：

```json
{
  "source": "start",
  "target": "1786843450454",
  "sourceHandle": null,
  "targetHandle": "target",
  "data": {
    "sourceType": "start",
    "targetType": "llm"
  }
}
```

已发布版本和其他正常草稿中的对应字段均为：

```json
"sourceHandle": "source"
```

在当前画布上重新拖线仍会生成 `sourceHandle: null`，因此单纯重连无法修复。

开始节点还保留了旧 DSL 的顶层 React Flow 类型：

```json
{
  "type": "start",
  "data": { "type": "start" }
}
```

Dify 1.16.1 的发布检查器只把顶层 `type == "custom"` 的节点纳入连通图，再通过 `data.type` 识别 Start、LLM、Answer 和 End。旧格式 Start 因此在检查前就被过滤，导致从 Start 出发的有效节点集合为空。

### 3. Answer 的变量引用正确

“直接回复 2”的回复模板已经真实指向 LLM 输出：

```text
{{#1786843450454.text#}}
```

无需修改 Answer 内容，也无需重新插入变量。

### 4. 草稿缺少结束节点

当前草稿只有 `start`、`llm`、`answer` 三个节点。上一次可发布版本的完整链路为：

```text
开始 → LLM → 直接回复 → 结束
```

当前“直接回复 2”没有出边，因而也被发布检查器判为未连接。

## 根因分析

本缺陷由两个独立的图结构问题共同导致：

1. Start 仍使用旧 DSL 顶层类型 `type: "start"`，不满足 Dify 1.16.1 检查器要求的 `type: "custom"`，因此整个链路不会进入连通性遍历。
2. “开始 → LLM 2”虽然被 React Flow 绘制，但草稿边的 `sourceHandle` 为 `null`，不是有效的 Dify 输出端口。
3. 重建业务节点时没有恢复“结束”节点，导致 Answer 不在完整的可发布链路中。

由于开始节点在当前编辑器中生成的输出 handle 本身没有 ID，重复删除和拖拽只会再次保存 `null`。问题位于草稿 graph，不位于 Prompt、模型配置或业务输出。

## 修复方案

使用一次性受控脚本 `scripts/dify/repair-workflow-edges.ps1` 修复当前应用的草稿 graph：

1. 执行写入前必须关闭所有打开该应用编排页的浏览器标签，防止页面内存中的旧 graph 通过自动保存覆盖修复结果。
2. 默认只执行 dry-run，显示目标工作流、节点、边和计划变更。
3. `-Apply` 前把完整草稿 graph 备份到被 Git 忽略的 `data/dify-backups/`。
4. 在 PostgreSQL 单个事务中锁定目标草稿。
5. 校验目标应用只有一个草稿，并且恰好包含一个 start、一个 llm 和一个 answer 节点。
6. 把 Start 的顶层 React Flow 类型规范化为 `custom`，保持 `data.type = "start"` 不变。
7. 只把 `start → llm` 边修正为：
   - `sourceHandle = "source"`
   - `targetHandle = "target"`
   - 同步规范化边 ID
8. 若缺少 End 节点，则按 `type = "custom"`、`data.type = "end"` 补充节点和 `answer → end` 边。
9. End 的输出继续引用现有 LLM 的 `text`，不改变业务输出。
10. 事务内验证完整链路存在；任一断言失败则回滚。

## 不在修复范围内

- 不修改 System Prompt、User Prompt 或上下文配置
- 不修改模型、温度、重试策略等 LLM 配置
- 不修改开始节点输入变量
- 不修改 Answer 模板
- 不修改已发布工作流
- 不发布工作流
- 不更换 App ID 或 API Key

## 执行方式

```powershell
# 只读预检（默认）
powershell -ExecutionPolicy Bypass -File scripts/dify/repair-workflow-edges.ps1

# 确认 dry-run 后执行草稿修复
# 先关闭所有打开该应用编排页的浏览器标签
powershell -ExecutionPolicy Bypass -File scripts/dify/repair-workflow-edges.ps1 -Apply

# 修复后的只读校验
powershell -ExecutionPolicy Bypass -File scripts/dify/repair-workflow-edges.ps1 -VerifyOnly
```

## 回滚方案

`-Apply` 会在写入前生成 UTF-8 JSON 备份。若界面验证异常，应停止发布，并从备份恢复该应用的 `draft` graph。恢复操作同样应在事务中进行，并再次核对 App ID 和 `version='draft'`，不得覆盖已发布版本。

## 验收标准

- [ ] `start → llm` 边的 `sourceHandle` 为 `source`
- [ ] Start 和 End 的顶层 `type` 均为 `custom`
- [ ] `llm → answer` 边的端口为 `source → target`
- [ ] `answer → end` 边的端口为 `source → target`
- [ ] Answer 仍引用原 LLM 的 `text`
- [ ] Dify 检查清单问题数为 0
- [ ] 控制台预览结果与修复前一致
- [ ] System Prompt 和模型配置没有变化
- [ ] 只修改草稿，发布动作仍由人工执行

## 修复记录

2026-08-16 已对目标应用草稿执行修复：

- Start 和 End 顶层类型已规范化为 `custom`
- `start → llm → answer → end` 三条边均通过端口校验
- Dify 检查清单中 LLM/Answer 的“此节点尚未连接到其他节点”均已消失
- 写入前后的 LLM 节点和 Answer 节点 JSON 逐项比较一致
- 草稿未发布

修复后检查清单仍有一项独立错误：`LLM 2：请配置模型`，界面同时显示 `deepseek-v4-flash 不兼容`。该问题不属于连线缺陷，且本次按约束未修改模型配置。

执行过程中确认了一个额外注意事项：若编排页在数据库修复期间保持打开，页面会用内存中的旧 graph 自动保存并覆盖修复结果。因此正式修复是在关闭旧编排页后执行，再通过全新页面验证。
