# I4：Dify 模型插件接口统一返回 500，工作流模型显示“不兼容”

## 缺陷现象

Dify 1.16.1 的工作流连线修复后，LLM 节点显示：

```text
deepseek-v4-flash
不兼容
```

发布检查清单只剩：

```text
LLM 2：请配置模型
```

页面同时反复弹出 `Internal Server Error`。此前 LLM 预览可以正常调用，工作流中的模型、Prompt 和凭证没有被修改。

## 影响范围

- Dify 工作流无法通过发布检查。
- 模型供应商列表、模型类型列表和模型参数规则无法加载。
- 影响范围不限于 DeepSeek；所有模型相关接口均可能失败。
- 工作流草稿、System Prompt 和已发布版本本身未损坏。

## 排查证据

### 1. 模型相关接口统一返回 500

Nginx 访问日志中以下接口持续返回 HTTP 500：

```text
/console/api/workspaces/current/models/model-types/llm
/console/api/workspaces/current/models/model-types/rerank
/console/api/workspaces/current/models/model-types/text-embedding
/console/api/workspaces/current/models/model-types/tts
/console/api/workspaces/current/model-providers
/console/api/workspaces/current/model-providers/langgenius/deepseek/deepseek/models/parameter-rules
```

因此界面的“不兼容”是模型元数据加载失败后的结果，不代表 `deepseek-v4-flash` 名称错误。

### 2. DeepSeek 模型与凭证仍然存在

- 已安装 DeepSeek 插件版本：`0.0.19`
- 插件文件包含 `deepseek-v4-flash.yaml`
- 插件运行日志曾出现 `Installed model: deepseek` 和 `local runtime ready`
- Dify `providers` 表中的 DeepSeek 供应商记录仍为 `is_valid=true`

不应删除凭证、修改模型名称或重新创建 LLM 节点。

### 3. 插件守护进程存在启动竞态

Dify 启动时，`plugin_daemon` 曾在 PostgreSQL 尚未就绪时反复失败：

```text
failed to connect to database=dify_plugin
database system is starting up
panic: failed to init dify plugin db
```

容器随后虽然恢复运行，但 API、插件注册和本地运行时之间可能保留了不完整状态。

### 4. DeepSeek 升级未真正完成

本地已经下载 `0.0.20` 插件包，但插件数据库和运行目录仍只有 `0.0.19`。

当前 `0.0.19` 的安装来源是：

```text
source = package
install_type = local
```

此前调用的是 Marketplace upgrade 路径。日志显示它查询：

```text
source = marketplace
```

因为找不到对应安装记录，升级请求返回 200 但没有安装 `0.0.20`。

## 根因

DeepSeek 插件的持久化状态不一致：`0.0.20` 本地包已经解包并启动过运行时，但 `dify_plugin` 数据库中的 `plugins` 和 `plugin_installations` 仍登记为 `0.0.19`。插件守护进程因此反复报告：

```text
Plugin table missing for existing PLUGIN_INSTALLED_PATH
plugin_unique_identifier=langgenius/deepseek:0.0.20@...
```

造成不一致的直接原因是原插件来源为 `package`，却曾尝试走 Marketplace upgrade；之后单独调用本地包安装只创建了 `0.0.20` 运行目录，没有完成同一插件的版本切换。API 进程中的模型元数据加载随之持续失败，前端将已有模型误显示为“不兼容”。

该问题与工作流中的模型名称、Prompt、节点业务配置和 DeepSeek 凭证无关。

## 修复方案

### 第一阶段：重建插件运行链路

1. 关闭所有 Dify 编排页，避免旧页面自动保存草稿。
2. 重启以下服务：
   - `plugin_daemon`
   - `api`
   - `worker`
   - `worker_beat`
3. 等待 API 恢复 `healthy`。
4. 确认插件日志重新出现 `local runtime ready`。
5. 重新打开 Dify，检查模型供应商接口和工作流检查清单。

这一阶段不修改数据库、插件文件、模型配置或凭证。

### 第二阶段：仅在第一阶段失败时安装本地包

若模型接口仍持续返回 500：

1. 备份 `dify_plugin` 中 DeepSeek 的安装记录和插件持久化目录。
2. 使用 Dify“安装本地插件”流程安装已经下载的 `0.0.20` 包。
3. 不使用 Marketplace upgrade，因为原安装来源是 `package`。
4. 验证新的插件声明、安装记录和运行目录均为 `0.0.20`。
5. 验证原 DeepSeek 凭证仍有效；仅在 Dify 明确要求时重新验证凭证。

## 不在修复范围内

- 不修改工作流中的模型名称
- 不修改 System Prompt 或 User Prompt
- 不删除 DeepSeek 凭证
- 不直接编辑插件数据库记录
- 不手工删除插件运行目录
- 不删除 Docker volume
- 不发布工作流

## 回滚方案

- 第一阶段只有容器重启，无持久化配置变更，无需数据回滚。
- 若执行第二阶段，应保留 `0.0.19` 插件包、安装记录和持久化目录备份；`0.0.20` 验证失败时通过 Dify 本地包安装流程恢复 `0.0.19`，不得直接拼接数据库记录。

## 实际修复记录

执行日期：2026-08-16

1. 在 `data/dify-backups/plugin-deepseek-20260816-1005/` 备份插件包和插件数据库记录。
2. 重启 `plugin_daemon`、`api`、`api_websocket`、`worker`、`worker_beat`；仅重启不能消除不一致状态。
3. 通过 Dify 自带的 `PluginInstaller.upgrade_plugin` 接口执行版本切换：
   - 原版本：`langgenius/deepseek:0.0.19@1aa3c64e...`
   - 新版本：`langgenius/deepseek:0.0.20@850efe73...`
   - 来源：`package`
4. 升级任务 `01a0085e-d190-71f6-a5d4-fce3306d6c5f` 返回 `success`，消息为 `upgraded`。
5. 核对 `plugins` 与 `plugin_installations`，两表均只登记 `0.0.20`，来源仍为 `package`。
6. 重启插件与 API 相关服务，日志出现：

```text
Installed model: deepseek
local runtime ready plugin=langgenius/deepseek:0.0.20@...
```

7. 重新加载编排页后，`deepseek-v4-flash` 恢复为正常 `CHAT` 模型，检查清单显示“所有问题均已解决”。未点击发布。

修复过程未直接编辑数据库，未删除插件目录，未修改模型凭证、System Prompt、模型配置或业务逻辑。

## 验收标准

- [x] 模型供应商及模型元数据在编排页正常加载
- [x] DeepSeek 参数规则可被 LLM 节点正常解析
- [x] 插件日志出现 `local runtime ready`
- [x] LLM 节点不再显示“不兼容”
- [x] 检查清单不再提示“请配置模型”
- [x] 检查清单显示“所有问题均已解决”
- [x] 工作流完整链路保持有效
- [x] LLM 和 Answer 节点配置未变化
- [x] 草稿未发布
