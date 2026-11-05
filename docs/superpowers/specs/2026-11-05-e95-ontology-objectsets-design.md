# E95：对象集与类型化动作

目标：保留 PostgreSQL 与既有权限模型，以 OSDK 的类型、字段选择、过滤、排序、聚合及动作定义为参考，经 MCP 提供有界查询；不声称 OSDK 协议兼容。参考 Palantir 开源 osdk-ts 的对象集与动作模型（https://github.com/palantir/osdk-ts），不引入 Foundry 依赖。

对象集查询支持 Issue、Project、Member；条件 AND 组合、eq/in，字段白名单和类型校验；选择字段、排序、稳定分页、count 按字段分组。关联筛选限制为 Issue 指向可见 Project、Member 或 Issue，且两端 scope 和可见性均检查。过滤/计数均在数据库端，关系仅以存在性判断，避免隐藏对象影响结果。上限限制以阻止无界查询。

动作详情由现有状态动作参数模型生成 schema，提供权限、workspace 角色、幂等性和副作用，避免工具与元数据漂移。调用沿用现有 scope、角色和业务服务；其他写动作不凭空实现。每次查询和动作独立使用 OAuth 身份校验。旧工具保持兼容。工作台验收必须由模型真实调用，辅助 SDK 调用不可冒充模型调用。
