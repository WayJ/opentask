---
epic: E10
status: active
date: 2026-11-04
---

# OpenTask Linear 进进阶：Initiatives + Docs（厚）

产品参考 Linear [Initiatives](https://linear.app/docs/initiatives) / Projects 上的战略聚合，以及轻量 Documents。在 **E9 local-complete**（Triage / Templates / Inbox snooze）之上交付：**Initiative**（跨多 Project 的目标容器 + 健康汇总）与 **Docs**（Issue/Project/Initiative 附属短文档或深链既有知识库）。本 Epic 为整包一个 Roadmap。

**Yuri / PRD 硬约束：Initiatives + Docs 是产品入口；不再与 PGE 双轴。** Docs/Initiatives **不得**设计成与遗留 `requirements` / PGE 任务框架并行的主路径；E12 已废弃 PGE 主路径，E10 只建立在 **Issue / Project** 体系之上，**勿复活** PGE 作为文档或规划入口。

北星：[OpenTask · Linear 对齐完整 PRD](https://cursor.com/canvas/store-adddb90c-33cd-496c-a6c4-08755560f586/656f4217-cbf0-48a3-9edb-168b4a36cbee) §E10。

基线 tip：`sprint/E9-S3` @ `f06dc9f`；worktree `/workspace/opentask-worktrees/E10-S1` · 分支 `sprint/E10-S1`。本地不推远程。E10 整包后接 **E11 Git/PR**（本 Phase **不**启动）。

## Deliverables

| deliverable | note |
|---|---|
| **Initiative CRUD** | 工作区级 Initiative：名称、描述、状态、目标日等；member+ 写；viewer 只读 |
| **多 Project 关联** | Initiative ↔ Project 多对多；列表/详情可挂/卸 Project；跨 WS 隔离 |
| **健康汇总** | 自关联 Project 的 `health_status`（E8）汇总展示（最差优先或计数）；不新建第二套健康模型 |
| **Docs 入口** | Issue / Project / Initiative 附属 **轻量 Markdown 短文档**（标题+正文），或深链既有 Knowledge Base；**不是**第二套完整 Wiki；**不是** Requirement/PGE 文档轴 |
| **导航 / ⌘K** | 侧栏或工作区入口；⌘K 可跳 Initiative / Docs |
| **打磨** | 空状态；权限；DESIGN.md / Naive；Epic local-complete |

## PRD ACs（摘录）

- [ ] Initiative CRUD；多 Project 关联
- [ ] 不再写「与 PGE 双轴并存」；Initiative 即战略聚合（Issue/Project 之上）
- [ ] Docs：附属文档或深链知识库（非完整 Wiki；非 PGE 入口）

## Definition of Done

- [ ] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed；merged-commit 仍 null / 未推远程
- [ ] `cd backend && pytest` 全绿（含 Initiative ACL/跨租户、Docs CRUD、健康汇总）
- [ ] FE eslint touched 0 errors；`pnpm run build` 通过
- [ ] Initiative：CRUD + 挂 Project；viewer 403 写；跨 WS 404
- [ ] Docs：可在 Issue/Project/Initiative 上创建/打开短文档或深链 KB；主导航无 PGE/requirements 规划入口
- [ ] **无** Initiative↔PGE 双轴文案或路由；**无** 复活 CreatePGE / requirements 主路径
- [ ] 整 Epic 一次回执 Yuri/Way

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 ✅ | planned | Initiative 表/API + 多 Project 关联 + 列表/详情 FE 骨架 |
| S2 | planned | 健康汇总 + 侧栏/⌘K + Favorites 可钉 Initiative（可选） |
| S3 | planned | Docs（附属 MD 或 KB 深链）+ 打磨 + Epic local-complete |

推荐顺序理由：无存量 Initiative 实体，先立模型与多 Project 关联（S1）；健康汇总依赖 E8 Project health 与 S1 关联数据（S2）；Docs 可独立但需挂接实体类型，放 S3 与整包验收同频，避免与 S1 API 夹具互相打断。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | **禁止 PGE 双轴**：Initiatives/Docs 只挂 Issue/Project（及 Initiative 自身）；不挂 Requirement/PGE Task 作主入口 | Yuri 2026-11-04；E12 de-PGE | 2026-11-04 | 指派 steering；PRD §E10 |
| D2 | 新表 `initiatives` + `initiative_projects`（M2M）；不复用 `requirements` | 探索无 initiative；Requirement 属遗留 PGE 轴 | 2026-11-04 | models inventory |
| D3 | Initiative 健康 = 聚合关联 Project.`health_status`（E8），懒计算 | 不重复造 health 流 | 2026-11-04 | E8 health |
| D4 | Docs = 轻量 `entity_documents`（Markdown body）**或**深链 KB；复用附件 `documents` 表仅作文件附件，不作 Wiki | PRD「不做第二套完整 Wiki」；现有 Document=Attachment | 2026-11-04 | document/model.py；KB 路由 |
| D5 | Alembic `down_revision = f2a3b4c5d6e8`（E9 snooze tip） | E9-S3 tip | 2026-11-04 | alembic versions |
| D6 | Estimates（故事点）**不**纳入本 Epic 主范围 | PRD 标 E6/E10；E6 已有小时粗算；点估算可后置 | 2026-11-04 | PRD matrix |
| D7 | 排除：完整 Wiki、PGE/requirements 主路径复活、Initiative 依赖图精修、Slack、E11 Git、远程 push | 指派 / PRD | 2026-11-04 | 指派 |

## Out of scope

- PGE / Requirement 规划入口复活或「双轴并存」文案
- 第二套完整 Wiki / 与 KB 对等的文档产品
- Initiative 依赖图 / 甘特精修（可后置）
- Estimates 点体系（另议）
- E11 Git/PR；计费；SSO；远程 push

## Explore gaps（Phase 1）

| gap | note |
|---|---|
| 无 `initiatives` 表/API/FE | 绿田；S1 新建 |
| `documents` = 附件元数据 | 非 Markdown Wiki；Docs 需新轻量表或 KB 深链 |
| Knowledge Base 已存在 | 可作 Docs「深链」目标；勿强制迁 KB |
| Project 已有 health / milestones / timeline（E8） | Initiative 汇总其上 |
| Favorites `TARGET_TYPES` 无 initiative | S2 可扩展 |
| Project.requirements relationship 仍在 | 遗留；E10 UI **不**引导走 requirements |

## Changelog

| date | note |
|---|---|
| 2026-11-04 | Phase 1：roadmap + design + S1 stub；基线 E9-S3 `f06dc9f`；Yuri 禁 PGE 双轴写入 |
| 2026-11-04 | **S1 local-complete**：CRUD+M2M+FE；Alembic `b2c3d4e5f6a7`；758 pytest；无 PGE/push |

## Sprint status

- [x] E10-S1 Initiative CRUD local-complete
- [ ] E10-S2 health rollup + nav
- [ ] E10-S3 Docs + Epic DoD
