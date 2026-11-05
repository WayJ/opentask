# E94：OpenTask Ontology MCP 验收

日期：2026-11-05。源码基线 `86773b8`，本轮工作区变更未提交。

设计：[E94 设计](../specs/2026-11-05-e94-ontology-mcp-design.md)。计划：[E94 计划](../plans/2026-11-05-e94-ontology-mcp.md)。

## 交付行为

本体版本 `1.0.0` 提供 Issue、Project、Member 类型，五个本体工具和原有 list_issues。字段、原生状态枚举、关系方向与基数按需发现；结果有界分页，列表/详情长文本分别限制为 1000/8000 字符并注明截断。只读，不新增数据存储或数据库迁移。

Issue 和 Project 同时执行部门数据范围与成员工作区过滤，兼容 NULL 工作区的存量记录。Member 使用最小身份白名单，profile 仅本人，read:members 才能读取共享工作区且符合部门范围的启用成员。关系读取校验两端，计数和分页只包含可见目标。

业务失败使用 MCP isError 和结构化错误；无效令牌仍 HTTP 401。小蓝通用 MCP 代理修复了上游 isError 在 MCP 出口丢失的问题；REST 和 MCP 均保留真实工具结局。

## 自动验证

| 验证 | 结果 |
|---|---|
| 新本体红测（实现前） | 11 failed，确认缺失行为 |
| OpenTask 全量后端隔离测试 | 1452 passed / 24 skipped / 10 warnings；无失败 |
| 最终 OAuth + 本体专项 | 53 passed / 2 warnings；覆盖最终业务错误契约、跨部门/跨工作区、停用成员、双端关系过滤、原生状态、分页、scope、JSON-RPC 和文本边界 |
| 小蓝 MCP/REST 代理回归 | 36 passed；包含 isError + 失败审计的 HTTP 红测与修复后复验 |
| 小蓝 scripts/check-all.sh | 通过（默认增量预检） |
| OpenTask 前端构建 | 通过；构建生成的三份无关前端文件已恢复 |
| OpenTask 前端只读 lint（无 --fix） | 213 errors / 822 warnings，当前前端存量问题，未改界面代码；仓库整体门禁仍非全绿 |
| git diff --check | 两仓通过 |

全量后端检查先完成，随后对最终 MCP 业务错误和文本边界做 53 项定向复验。没有把后续定向测试计数叠加成全量测试数。存量全量套件中的现场脚本仍可能返回布尔值而非断言，相关 pytest warning 不作为额外业务验收证据；真实链路另行验证如下。

## 真实工作台与 harness

本地小蓝测试应用 `app-1d65ad945f29a003` 保持已连接，OpenTask 测试账号 `xiaolanc8aa16` 通过正常授权码流程重新同意 `profile read:tasks read:projects read:members`。旧令牌不会自动扩权。

真实 harness 使用已注入成员凭据，经小蓝 MCP 代理发现：list_issues、discover_ontology、describe_object_type、search_objects、get_object、get_related_objects。使用 harness 自带 MCP SDK 和 lcowork CLI 验证：

- 本体发现返回版本 1.0.0 与三个对象类型。
- 测试问题 ISSUE2026-722588 的本体状态为 open。
- project 关系返回“OpenTask Ontology MCP 项目”。
- assignee 关系返回“Ontology 测试负责人”。
- blocks 关系返回 ISSUE2026-1182694“等待测试问题解除阻塞”。
- is_blocked_by 反向关系返回原问题；项目筛选 total=2，limit=1 返回下一页。
- 不存在对象返回 OBJECT_NOT_FOUND / 业务 status=404 / isError=true，未被平台误报成功或会话过期。
- lcowork app call 执行 discover_ontology 返回 OpenTask 1.0.0。

联调数据保存在独立开发库，签名配置和测试客户端文件保存在已有 gitignore 规则覆盖的本地文件中；不把密钥写入文档或提交。现有 harness 的 OpenTask MCP 配置已刷新以重新发现新工具。

## 上下文开销

以 cl100k_base 对序列化 tools 目录估算：原单工具约 78 tokens，最终六工具目录约 1511 tokens。详细对象属性和关系不放进初始工具目录，通过 describe_object_type 按需读取。

## 后续范围

本期不提供业务写动作。主负责人关系不包含额外协作者；增加协作者、多跳查询或业务动作时需扩展本体版本、授权与测试。前端 lint 存量失败待独立清理。

## 2026-11-05 增量：Issue 状态动作

- OAuth/MCP 隔离测试：54 passed；覆盖缺失写入 scope、缺失 issue:update、viewer、跨部门/工作区、已删除 Issue、非法枚举、重复调用和状态时间线。
- 通过工作台运行环境内的 MCP SDK，经小蓝代理发现 `update_issue_status` 并实际调用：ISSUE2026-722588 从 `open` 更新为 `resolved`，随后 `get_object` 回读 `resolved`。通用任务状态映射 `resolved` 为 `done`。
- 工作台对话中已提交模型测试请求，但会话未返回结果；上述写入由 SDK 发起，不能作为模型实际调用动作的证据。
- 本增量替代上文“本期不提供业务写动作”的范围描述；对象集字段表达式仍未实现。
