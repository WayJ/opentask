# E95 验收记录（进行中）

- 红测：2 项新增对象集测试在实现前失败，原因是工具不存在。
- 首轮本体定向测试：16 passed，覆盖字段选择、枚举校验、排序、分页、分组、隐藏关系目标及跨类型 scope。
- 真实小蓝工作台 MCP 网关：发现 `query_object_set`、`describe_action`；按项目关系筛选返回 2 条 Issue（open、resolved），状态分组返回各 1 条；动作 schema 返回原生状态枚举及权限。
- 小蓝运行环境直连 MCP SDK 验证，并不等于模型调用；工作台会话页面打开超时，模型端验证仍在排查。
- 对象集支持 eq/in AND 条件、字段选择、单字段排序、单字段分组 count、最多一条 Issue 关系过滤；不支持自由 SQL、多跳、聚合函数或集合 union/intersect。offset 分页不提供跨页快照保证。
- 工具目录共 9 个约 2690 cl100k_base tokens；新增两个工具约 1098 tokens。基线六工具的历史估算约 1511 tokens，历史数据未覆盖后来新增的状态动作，故不直接作为本次精确差值。
- 前端 `npm run build` 通过；只读 eslint 存量 213 errors / 822 warnings，不运行带 `--fix` 的 lint。构建改写的三份原先干净的生成文件已恢复。
- 全量后端隔离测试：1457 passed / 24 skipped / 10 warnings；前端构建通过，前端只读 lint 为 213 errors / 822 warnings（存量问题）。
- 模型验收未通过：工作台会话页导航超时；隔离 headless harness 复用插件时缺少 webServer、credentials、pluginInventory 服务，企业模型适配器未注册（NO_ADAPTER）。没有将 SDK 调用或未执行的提示词记为模型调用。

## 2026-11-05 工作台真实模型复验

- 工作台入口 smoke：`WB PASS`。会话 Web 进程重启并恢复后，新会话能够正常运行企业默认模型 DeepSeek-V4.1-Flash。
- 工作台会话“OpenTask MCP 验收与状态更新”第一轮的模型工具轨迹实际调用 `discover_ontology`、`describe_object_type`、`describe_action`、`search_objects`、三次 `query_object_set`、`update_issue_status` 和 `get_object`。按项目筛选并选择 `issue_code`、`status` 得到 ISSUE2026-1182694/open、ISSUE2026-722588/resolved；按状态分组为 open=1、resolved=1（该结果产生于新建下述专用测试 Issue 之前）。对 ISSUE2026-722588 重复调用状态动作返回 previous_status=resolved、status=resolved、changed=false，回读仍为 resolved。
- 为验证真实写入，在隔离开发库新建一次性测试 Issue ISSUE2026-8917718（初始 open）。第二轮模型实际调用 `search_objects`、`update_issue_status`、`get_object`；动作返回 previous_status=open、status=resolved、changed=true，模型回读 resolved。独立数据库检查确认该 Issue 状态为 resolved，恰有一条 status_changed 时间线，内容为 open → resolved。
- Web 页面此前的请求可能迟到：恢复原会话后发现 22:13 的旧模型调用已成功执行幂等动作；不能因页面暂时无响应断言请求未执行。
- E95 的真实模型调用与持久化验收通过。全量后端与前端构建证据见上；前端 lint 仍有已记录的存量失败，不能宣称仓库所有门禁全绿。
