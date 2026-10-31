---
epic: E2
status: open
date: 2026-10-31
---

# OpenTask 对接 Orca 任务源集成（模拟 Jira 模式）

## Deliverables

| deliverable | note |
|---|---|
| 任务源契约 API 层 | 暴露 `GET/POST /tasks`、`GET/PATCH/DELETE /tasks/{id}`，支持过滤、分页、`updated_since` 增量游标，字段符合 Orca 通用任务模型（id/title/description/status/assignee/url/timestamps + 可扩展 metadata） |
| 状态映射配置 | OpenTask `IssueStatus`（open/in_progress/feedback/resolved/closed/rejected）↔ Orca 工作流状态的可配置映射，含默认映射表 |
| 鉴权接入 | 复用现有 `access_token` 机制，支持 API Key（Bearer）与 Orca 侧 OAuth2 client credentials 两种模式 |
| 健康/能力检查端点 | `GET /capabilities` 返回端点支持情况与契约版本，供 Orca 注册时校验 |
| OpenAPI 契约文档 | 对外发布 OpenAPI spec，声明状态映射与鉴权方式，作为参考适配器实现 |
| 错误语义规范 | 鉴权失败（401）、schema 违规（422）、端点不可达（503）三类错误在响应体中可辨识，Orca 能明确归因 |

## Definition of Done

- [ ] Orca 用「自定义任务源」注册 OpenTask 后，OpenTask 的 issue 能在 Orca 侧正常列出、读取、创建、更新、状态流转
- [ ] `GET /tasks` 支持 `updated_since` 增量游标，重复拉取同一游标不返回重复数据
- [ ] `POST /tasks` 创建的 issue 回传到 OpenTask 后，字段（title/description/assignee/status/labels）完整落库
- [ ] `PATCH /tasks/{id}` 更新状态后，OpenTask 内部 issue 状态同步变更，并写入既有 timeline 记录
- [ ] `DELETE /tasks/{id}` 采用软删除（OpenTask 现有 `is_deleted` 语义），不物理删除数据
- [ ] 状态映射可通过配置调整，未配置时使用默认映射表且能正确往返（Orca → OpenTask → Orca）
- [ ] 契约 OpenAPI spec 已生成并随代码发布，字段与实现一致
- [ ] 端点不可达、鉴权失败、schema 违规三类错误有独立的错误码与可读消息
- [ ] 该 API 层有单元测试覆盖 CRUD 全路径与增量游标边界

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S4 | started | 契约 API 层 + 字段映射（Issue ↔ 通用任务模型）。编号修订 2026-10-31：原 S1，因 sprint id 全树唯一规则（E1 已物化 S1–S3），E2 stubs 顺延为 S4–S6。go 决定 2026-10-31：用户常设授权「依次推进把E1和E2全部开发完」+「无人值守自行规划」；D6 模拟 Jira 模式、D7 并列路由、D8 软删除、D9 复用 access_token、D10 updated_since 游标均已 ADR 定案；形状三问由 D12 裁定（/tasks 挂根、assignee 字符串+metadata.username、labels↔tags）。sprint 级验收目标：① `GET/POST /tasks` 与 `GET/PATCH/DELETE /tasks/{id}` 可用且字段符合通用任务模型 ② 过滤/分页/updated_since 增量游标可用且重复拉取不重复 ③ CRUD 全路径 + 游标边界有单元测试 ④ 导入图零缺失维持。2026-10-31 started，evidence: `docs/superpowers/sprints/2026-10-31-S4-plan.md` |
| S5 | ready | 状态映射配置 + 鉴权接入 + 能力检查端点。编号修订 2026-10-31：原 S2，同上。go 决定 2026-10-31：用户常设授权 + 明确要求 sprint 级 worktree 并行；S4 已交付契约层与默认状态表，本 sprint 将其配置化并补齐 D9 鉴权（API Key Bearer 与 OAuth2 client credentials 两模式）与 `GET /capabilities` 端点；sprint 级验收目标：① 状态映射可经配置调整且往返正确（epic DoD 6）② access_token 鉴权两模式可用（401 语义独立可辨识）③ /capabilities 返回端点支持与契约版本 ④ tests/tasks 扩展鉴权与映射用例全绿 |
| S6 | started | OpenAPI 文档生成 + 错误语义 + 契约测试与 Orca 侧端到端联调。编号修订 2026-10-31：原 S3，同上。go 决定 2026-10-31：用户指示「继续推进整体迭代」；S4 契约层与 S5 鉴权/映射/capabilities 已落地 main（fb6df35），S6 是 E2 收官前置；受 HC1 约束（错误码沿用 CONTRACT_AUTH_* 命名）。sprint 级验收目标：① 契约 OpenAPI spec 生成且随代码发布、字段与实现一致（epic DoD 7）② 401/403/503 三类错误独立错误码与可读消息（DoD 8）③ 契约测试补全错误路径 ④ Orca 自定义任务源注册联调用例执行并留证（DoD 1——若本机无 Orca 侧注册环境则记录 blocked 项与替代证据）。2026-10-31 started，evidence: `docs/superpowers/sprints/2026-10-31-S6-plan.md` |
| S7 | ready | Jira 线格式兼容层：模拟 Jira REST API 必要子集（/rest/api/2/），Orca 自建 Jira 集成直指 OpenTask。go 决定 2026-10-31：用户确认「orca 可以使用自建的 jira」（ADR D13）；S6 已实证本机无自定义任务源注册面，此为唯一真实验证路径。sprint 级验收目标：① Orca 以自建 Jira 模式注册本机后端成功 ② 列出/读取/创建/更新/状态流转五操作真实走通并留证 ③ Jira 线格式端点有契约测试 ④ 与 /tasks 契约层共用映射鉴权内核无重复实现 |

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D6 | 采用「模拟 Jira」模式：OpenTask 暴露符合 Orca 通用任务源契约的 REST API，而非实现 Orca 侧的 Jira 插件 | Orca 已支持 Jira/GitHub/Linear/GitLab 四种任务源且各有实现成本；issue #8376 提出的正是"客户方暴露符合契约的端点"路径。OpenTask 侧实现成本远低于推动 Orca 新增 first-party 集成 | 2026-10-31 | https://github.com/stablyai/orca/issues/8376 |
| D7 | 任务源契约层与现有 issue API 并列（独立路由前缀），不改造现有 issue 接口 | 现有 issue API 面向前端 UI，字段与分页约定与通用任务契约不同；并列实现避免破坏既有前端与 CLI | 2026-10-31 | `backend/opentask/api/issue/router.py` |
| D8 | 删除采用软删除，沿用 OpenTask 现有 `is_deleted` 语义 | Issue 模型已有 `is_deleted` 字段与软删除查询约定；物理删除会破坏 timeline/comment 的级联关系 | 2026-10-31 | `backend/opentask/models/issue/model.py` Issue.is_deleted |
| D9 | 复用现有 access_token 体系做契约层鉴权 | 后端已有完整的 token 签发/校验/作用域机制，无需新造鉴权体系，也便于 Orca 侧配置 API Key | 2026-10-31 | `backend/opentask/models/access_token/model.py` |
| D10 | 增量同步采用 `updated_since` 时间游标为主，不实现 webhook 推送 | Orca issue 明确将 webhook 列为可选、轮询游标为 fallback；先实现轮询可满足接入需求，webhook 作为后续增强 | 2026-10-31 | https://github.com/stablyai/orca/issues/8376 |
| D12 | 契约层三项形状裁定（关闭 Q5/Q7/Q8）：① 路由前缀 `/tasks` 直接挂根（不加 `/api`，Orca base URL 直指，能力协商走 S5 的 `/capabilities`）；② assignee 为字符串 user ID，metadata 附 `username`；③ labels 双向映射到现有 `tags` 关联表 | ①D7 并列路由且 Orca 侧注册需要稳定简洁 base；②Q7 建议（OpenTask 为 assignee_id 字符串 + user 关联）；③Q8 复用既有 tags 避免 schema 变更；裁定依据为用户常设授权「无人值守自行规划」2026-10-31，沿 epic 各问题行内建议 | 2026-10-31 | 本文档 Q5/Q7/Q8 行内建议；用户常设授权 |
| D13 | 增补 Jira 线格式兼容层（S7）：模拟 Jira REST API 必要子集（`/rest/api/2/` 线格式），使 Orca 现成的自建 Jira 集成直接指向 OpenTask 后端；通用契约层（/tasks）保持不变，两者共用映射与鉴权内核 | 用户 2026-10-31 确认「orca 可以使用自建的 jira」——本机 Orca 构建无自定义任务源注册面（S6 实证），但 Jira 集成支持自建实例（可配 base URL）；这是当前唯一可真实验证的接入路径，同时关闭 Q6 的等待姿态 | 2026-10-31 | 用户指示 2026-10-31；S6 探测证据 `docs/superpowers/sprints/2026-10-31-S6-orca-e2e-evidence.md` |

## Asset Disposition

| asset | disposition | note | date | evidence |
|---|---|---|---|---|
| `backend/opentask/api/issue/router.py` | reuse | 契约层复用 issue service 与 model，不重写业务逻辑 | 2026-10-31 | `backend/opentask/services/issue_service.py` |
| `backend/opentask/models/access_token/` | reuse | 直接作为契约层鉴权来源 | 2026-10-31 | D9 |
| OpenAPI spec 生成链路 | reuse | 后端已有 FastAPI 自动生成 openapi.json 的能力，契约 spec 可基于同一机制产出 | 2026-10-31 | `backend/openapi.json` |

## Open Questions

| id | question | status | resolution |
|---|---|---|---|
| Q5 | 契约层与现有 issue API 的路由前缀如何划分（`/tasks` 直接挂根，还是 `/api/tasks`）？ | closed | D12（2026-10-31）：`/tasks` 直接挂根，Orca base URL 直指 |
| Q6 | Orca 的"通用任务源"契约尚未定稿为公开 OpenAPI spec，本项目应完全按 issue 描述实现，还是等待官方 spec 后对齐？ | closed | D13（2026-10-31）：不等上游——通用契约层（S4-S6）+ Jira 线格式兼容层（S7）双轨，后者为当前唯一可真实验证路径 |
| Q7 | assignee 在契约中是字符串还是对象？OpenTask 用 `assignee_id` 字符串 + user 表关联 | closed | D12（2026-10-31）：字符串 user ID + metadata.username |
| Q8 | labels/tags：OpenTask 有独立 `tags` 关联表，契约的 labels 字段如何映射？ | closed | D12（2026-10-31）：labels 双向映射现有 tags 关联表 |

## Cross-cutting

| concern | owning epic | note |
|---|---|---|
| 契约层不得绕过 OpenTask 既有权限模型 | E2 | 契约层复用 issue service，权限校验与 UI 侧一致 |
| 契约字段稳定性 | E2 | Orca 依赖字段契约，破坏性变更需版本号，见 Q6 |
| 公开仓库中不得出现 Orca 侧真实凭据 | E1 | 联调用的 token 走本地 `.env.*.local`，不入库 |
