# E10 设计：Initiatives · Docs

日期：2026-11-04  
Epic：E10  
状态：designed（Phase 1；**无**产品实现）  
基线：`sprint/E9-S3` @ `f06dc9f`；worktree `/workspace/opentask-worktrees/E10-S1`（分支 `sprint/E10-S1`）  
北星：OpenTask Linear PRD §E10  
Alembic head：`f2a3b4c5d6e8`（`notifications.snoozed_until`）

## 0. 硬约束（Yuri）

> **Initiatives + Docs 是产品入口；不再与 PGE 双轴。**

- Docs / Initiatives **不要**设计成与遗留 PGE / `requirements` **并行主路径**
- PGE 已在 E12 废弃主路径；E10 以 **Issue / Project** 体系上的 Initiatives + Docs 为准
- **勿复活** PGE（CreatePGE、requirements 列表作规划首页、PGE 文档轴）作为文档或规划入口
- 存量 `requirements` / PGE API 可继续 deprecated 存在；**本 Epic 导航与空状态不指向它们**

## 1. 目标

1. **S1** Initiative 表 + CRUD/list API + 多 Project 关联；FE 列表/详情骨架  
2. **S2** 关联 Project 健康汇总；侧栏/⌘K；可选 Favorites 钉 Initiative  
3. **S3** Docs（附属 Markdown 短文档 **或** KB 深链）+ 打磨 + Epic local-complete  

不做：完整 Wiki、PGE 双轴、Initiative 依赖图精修、Estimates 点体系、E11、远程推送。

## 2. 探索事实（Phase 1 inventory）

### 2.1 Initiative / 战略聚合

| 资产 | 现状 |
|---|---|
| 表 / 模型 | **无** `initiatives` |
| API / FE | **无** |
| 近邻 | `projects`（E3+；E8 milestones/health/timeline）；`favorites`（project/saved_view/issue） |
| 遗留 | `requirements` + PGE 任务仍在库内；E12 主路径 de-PGE；**不得**作 E10 入口 |

结论：绿田新建 Initiative；挂 Project，不挂 Requirement。

### 2.2 Docs / 文档

| 资产 | 路径 | 现状 |
|---|---|---|
| `documents` | `models/document/` | **Document = Attachment**（file_path/MIME）；多态 `entity_type/entity_id`；非 Markdown 正文 Wiki |
| Issue 附件 | `GET/POST /api/issues/{id}/attachments` | 文件附件 |
| Knowledge Base | `/knowledge-base/*` + `api/knowledge*` | Git+MD 知识库（完整文档产品）；可深链 |
| Requirement 文档摘要 | task/requirement schema `documents` | **PGE 轴**；E10 **不用** |

结论：E10 Docs =（首选）新轻量 Markdown 实体文档表，挂 `issue` \| `project` \| `initiative`；或 UI 深链已有 KB。不把附件表升级成 Wiki；不走 requirements 文档。

### 2.3 Project 健康（汇总输入）

| 资产 | 现状 |
|---|---|
| `projects.health_status` | `on_track` \| `at_risk` \| `off_track`（E8） |
| Health 更新流 | `project_health` + Inbox `project_health` |
| Timeline / milestones | E8 已交 |

结论：Initiative 详情展示关联 Project 健康计数/最差状态即可（懒聚合）。

### 2.4 Alembic

当前 head：`f2a3b4c5d6e8`。E10-S1 新 revision：`down_revision = f2a3b4c5d6e8`（建议 id `a1b2c3d4e5f6`）。

## 3. 架构总览

```
Workspace
  └── Project[]          (E3–E8：health / milestones / timeline)
  └── Initiative[]       [E10]
        + initiative_projects (M2M)
        + health_summary = f(projects.health_status)   [S2]
  └── Issue[]
  └── EntityDocument[]   [E10-S3 首选]
        parent: issue | project | initiative
        title, body_md, updated_at
  └── KnowledgeBase      (既有；Docs 可深链，非强制)

禁止主路径：
  requirements / PGE CreateTask / prompt_generator 规划入口
```

## 4. 数据模型

### 4.1 `initiatives`（S1）

| 列 | 说明 |
|---|---|
| id | uuid PK |
| workspace_id | FK workspaces CASCADE |
| name | str(100)；uq (workspace_id, name) |
| description | text nullable |
| status | str：`planned` \| `active` \| `completed` \| `canceled`（默认 active） |
| target_date | datetime nullable |
| owner_user_id | optional |
| sort_order | int default 0 |
| created_by / created_at / updated_at | 审计 |

### 4.2 `initiative_projects`（S1）

| 列 | 说明 |
|---|---|
| initiative_id | FK CASCADE |
| project_id | FK CASCADE |
| PK / uq | (initiative_id, project_id) |
| 校验 | 同 workspace |

### 4.3 `entity_documents`（S3，首选）

| 列 | 说明 |
|---|---|
| id | uuid |
| workspace_id | FK |
| parent_type | `issue` \| `project` \| `initiative` |
| parent_id | str |
| title | str |
| body_md | text |
| created_by / updated_* | 审计 |
| uq | 可选 (workspace_id, parent_type, parent_id, title) |

备选：不做新表，仅在 FE 提供「打开知识库」深链 + 可选 `kb_link` JSON 字段挂父实体——若选备选，S3 design 实现时在 plan 锁定一种，**禁止**第三条 PGE 文档轴。

## 5. API 草图

### 5.1 Initiatives（S1）

| method | path | 行为 |
|---|---|---|
| GET | `/api/initiatives` | WS 列表；含 projectIds 摘要 |
| POST | `/api/initiatives` | 创建；member+ |
| GET | `/api/initiatives/{id}` | 详情 + projects +（S2）healthSummary |
| PATCH | `/api/initiatives/{id}` | 更新字段 |
| DELETE | `/api/initiatives/{id}` | 删除（级联 M2M） |
| PUT | `/api/initiatives/{id}/projects` | body `{ projectIds: [] }` 全量替换或 |
| POST/DELETE | `/api/initiatives/{id}/projects/{projectId}` | 挂/卸 |

ACL：`X-Workspace-Id` + member；viewer GET；跨 WS id → 404。

### 5.2 Docs（S3）

| method | path | 行为 |
|---|---|---|
| GET | `/api/entity-documents?parentType=&parentId=` | 列表 |
| POST | `/api/entity-documents` | 创建 |
| PATCH/DELETE | `/api/entity-documents/{id}` | 改/删 |

或深链-only：无新 API，仅 FE。

## 6. FE

- **S1**：路由 `/initiatives` 列表 + `/initiatives/detail?id=`；创建/编辑；关联 Project 多选（现有 project list API）
- **S2**：详情健康摘要；侧栏入口；⌘K `nav.initiatives`；Favorites `target_type=initiative`（可选）
- **S3**：父实体页「文档」Tab：短 MD 编辑器 **或**「在知识库中打开」；空状态引导 Issue/Project，**不**引导 PGE

遵守 DESIGN.md / Naive / soybean；中文 UI。

## 7. 测试要点

- Initiative CRUD ACL；跨 WS 404；同名冲突
- 挂 Project：异 WS project 拒绝；卸挂后列表更新
- 健康汇总：无 project / 混合 health 的断言
- Docs：挂 initiative/issue/project；跨父 404
- 回归：E8 project health、E9 triage/templates/snooze；**无**新测试依赖 PGE create

## 8. Sprint 切分与依赖

| Sprint | 范围 | 依赖 |
|---|---|---|
| S1 | initiatives + M2M + FE 骨架 | E9 tip；Alembic on snooze head |
| S2 | health 汇总 + 导航/⌘K（+ favorites） | S1；E8 health |
| S3 | Docs + 打磨 + Epic DoD | S1（父类型含 initiative） |

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 产品把 Initiative 当成 PGE 替代流程引擎 | 文案：战略聚合 / 跨项目目标；状态仅 planned/active/… |
| Docs 做成第二 Wiki | 短 MD + 深链 KB；范围写死 |
| 误加 requirements 导航 | 设计/验收检查清单显式禁止 |
| Favorites 未扩 initiative | S2 可选；不阻塞 DoD |

## 10. 排除

完整 Wiki、PGE/requirements 主路径、Initiative 依赖图精修、Estimates 点、Slack、E11 Git、SSO、计费、远程 push。

## 11. Phase 1 产出清单

- [x] explore inventory（本文 §2）
- [x] roadmap `docs/superpowers/roadmaps/2026-11-04-opentask-initiatives-docs.md`
- [x] 本 design（含 Yuri 禁双轴）
- [x] S1 stub `docs/superpowers/sprints/2026-11-04-E10-S1-plan.md`
- [ ] **产品实现** → 待后续 Phase（TDD plan + impl）；本 Phase **停止**
