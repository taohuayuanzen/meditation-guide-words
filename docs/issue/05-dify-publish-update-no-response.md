# I5：Dify 点击“发布更新”无响应

## 缺陷现象

- 发布检查清单显示“所有问题均已解决”。
- 点击“发布更新”后菜单不关闭、无成功或错误提示，发布时间仍为旧值。
- 草稿自动保存正常。

## 排查证据

1. 当前草稿图为完整链路：开始 → 生成引导词 → 回复 → 结束；三条边的 `sourceHandle` 和 `targetHandle` 均有效。
2. 模型供应商、LLM 模型和参数规则接口均返回 HTTP 200。
3. 点击发布后，`POST /workflows/draft` 返回 200，但没有随后产生 `POST /workflows/publish`。
4. `api_websocket` 持续记录 `Cannot receive from redis`，旧连接重连期间还出现过 `/socket.io` 502。
5. Dify 前端启用协作模式时，发布前会等待协作层返回草稿同步结果；该结果为空时直接抛出 `Workflow draft sync failed`，外层只写浏览器警告，不向用户显示错误，因此表现为“没有响应”。

## 根因

Dify 1.16.1 前端发布链路在“详细校验 → 强制同步草稿 → 发布”中的强制同步阶段返回空结果。草稿 REST 保存实际已经成功，但前端仍抛出 `Workflow draft sync failed`，且 `app-publisher` 外层只写浏览器 `console.warn`，没有显示错误提示，所以用户看到的是“没有响应”。

实例同时启用了 `ENABLE_COLLABORATION_MODE=true`，`api_websocket` 的 Redis 订阅异常会放大该问题；关闭协作模式后，当前版本的按钮仍能复现静默终止，因此协作异常是诱因，不是唯一根因。

## 最小修复方案

1. 将单机实例 `docker/.env` 中 `ENABLE_COLLABORATION_MODE` 设置为 `false`，避免继续依赖异常的协作回执。
2. 重建读取该环境变量的 API、WebSocket、Worker 服务。
3. 当前版本按钮仍静默失败时，通过 Dify 自带的 `WorkflowService.publish_workflow` 发布已保存草稿，不直接编辑数据库。
4. 核对应用的 `workflow_id`、新发布版本及图内容，并刷新编排页确认发布时间更新。

该调整适用于当前单机、单人维护场景，不改变工作流、Prompt、模型、凭证或业务逻辑。若以后需要多人实时协作，应先修复 Redis Pub/Sub 链路，再重新启用协作模式。

## 实际修复记录

执行日期：2026-08-16

1. 已将 `ENABLE_COLLABORATION_MODE` 从 `true` 调整为 `false`，并重建相关服务；API 恢复 healthy。
2. 已通过 Dify 官方 `WorkflowService.publish_workflow` 发布当前草稿，发布版本 ID：

```text
406564ba-878b-4a09-b04f-71b757343ad9
```

3. 数据库核验 `apps.workflow_id` 已指向该版本，且新发布版本的 `graph` 与当前 draft 完全一致。
4. 编排页“最新发布”已更新为“几秒前”。
5. 未修改工作流节点、连线、Prompt、模型、凭证或业务逻辑。

## 验收标准

- [x] 当前草稿已通过 Dify 官方发布服务成功发布
- [x] 应用已指向新发布版本
- [x] 页面“最新发布”时间更新
- [x] 已发布工作流与当前草稿一致
- [x] 工作流配置和业务逻辑未变化
- [ ] Dify 1.16.1 前端按钮的静默失败应在后续升级或前端补丁中修复
