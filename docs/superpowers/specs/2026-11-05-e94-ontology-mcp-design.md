# E94：OpenTask Ontology MCP

日期：2026-11-05。采用用户已确认的业务对象、关系和动作建模方式；本期只读，存储沿用 PostgreSQL，不接入 Foundry。

对象为 Issue、Project、Member。属性使用显式白名单，枚举直接来自领域枚举。类型定义说明主键、字段、关系、scope、查询过滤与分页；元数据提供版本号。

MCP 工具为 discover_ontology、describe_object_type、search_objects、get_object、get_related_objects；保留 list_issues 兼容原消费者。MCP 是协议层，查询与授权编排放 services/ontology，类型与工具参数同源生成 JSON Schema。工具执行逐次校验 OAuth scopes。Issue 使用 read:tasks，Project 使用 read:projects；profile 仅允许读取本人 Member，read:members 才能读取可见成员目录。发现本体只需有效 OAuth 身份，工具目录按 scope 暴露旧 list_issues，通用工具执行时检查目标类型权限。

Issue/Project 查询使用既有 RbacService 部门过滤规则及 WorkspaceService 成员工作区集合（兼容 workspace_id=NULL 的存量数据）。Member 目录限启用账号及本人或共享工作区且符合部门范围的成员。每次遍历先校验起点，再对目标应用同样权限与 scope；不可见对象与不存在对象同形 OBJECT_NOT_FOUND（业务状态 404）。对象结果不输出密码、token、第三方密钥或未授权关系的目标标识。

关系包括 Issue 的 project/assignee/reporter/parent/children 与领域 RelationType；Project 的 issues；Member 的 assigned_issues/reported_issues。关系方向、反向名与基数在定义中可查；依赖关系按存储方向及反向枚举投影，先过滤再分页。分页上限 50，排序使用 created_at/id 稳定序；返回 total、has_more、next_offset。描述文本有长度上限并声明截断字段。

实现前红测覆盖：发现及 schema、筛选和分页、原生 issue 状态词表、正反关系、跨部门与跨工作区对象和边的隔离、scope 拒绝、禁用成员、未知工具、畸形参数和 JSON-RPC 请求。兼容 list_issues 输出，不将 todo 映射状态混入原生本体状态。

验收通过现有小蓝 OAuth MCP 代理及真实 harness SDK，不修改平台业务实现。新增 scope 需要重新同意授权，旧令牌继续只获得原有能力。全量后端测试使用独立库；前端 lint 禁止自动修复，报告既有失败。仅在 OpenTask 修改本体实现和文档，保留已有未提交改动，不自动提交混合工作。

MCP 本体工具业务失败返回 HTTP 200 / isError=true / structuredContent.error，状态值 400/403/404 表示参数、scope 或对象失败；不将对象缺失发成 HTTP 404（平台代理将该状态用于会话过期重试）。传输令牌无效仍为 HTTP 401。旧 list_issues 的 HTTP 错误行为保留。


## 2026-11-05 修订：Issue 状态动作

上述只读范围为首版历史记录；现增加类型化 `update_issue_status` 动作。输入为对象主键和原生状态枚举，输出前后状态及是否变更。要求 `read:tasks`、`write:tasks`、`issue:update`、可见数据范围和工作区 member/owner；scope 不会隐式升级。动作通过既有 IssueService 更新以保留时间线和副作用，重复设为当前状态不重复写入。`resolved` 是通用 done 的默认逆映射；`closed` 同样映射 done。此实现借鉴对象、关系、动作建模，并不声称兼容 Palantir OSDK/AIP 或连接 Foundry。对象集的字段表达与组合查询仍是后续能力。
