# E72 Design：Project 模板 mid — project_templates · CLI 1.56.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E72  
基线拟：`sprint/E71-S1` @ `b95da6f`（全文 `b95da6fa742aeae490acdd00d602966eb22c0f7a`；E71 design 基线 `f84a233`；E70 tip `5f311f4` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E72-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E73**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e72-project-templates-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E72-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E71 连续闭合 … → childProgress（E70）→ **多指派人 mid（E71：`issue_assignees` · CLI 1.55.0）**。

E71 附录 runners-up（任务硬指引）：

1. **Activity Push** — 仍 **勿默认**  
2. **Customer 门户再厚** — **prefer skip**  
3. **Initiative 甘特** — **prefer skip**  
4. **Recurrence Q2b advance** — **rotate off**  
5. **表单公开附件** — **prefer skip**  
6. **递归孙项进度** — **prefer skip**  
7. **Project 模板** — **本轮候选（若 mid）**  
8. **Bulk/Insights 多指派拆分** — **prefer skip**（刚交多指派）

轮换离开刚闭弧：**门户 / 假日 / Initiative deps / 附件 ACL / TZ·due / Form→Triage / 评论附件 / childProgress / multi-assignee**。

代码实证 @ `b95da6f`：

| 面 | 现状 |
|----|------|
| Issue 模板 | E9-S2 已有 `issue_templates` + CRUD + create `template_id` + FE 设置页 — **模式可复用** |
| Project | CRUD + milestones + timeline/health（E8）；**无** `project_templates`；**无**从模板建项；**无** duplicate |
| 创建路径 | `ProjectService.create` 仅 name/description；不带里程碑种子 |
| CLI | `project list` 等已有；无 template 子命令 |
| Linear 对齐 | Linear Project templates / 从模板开项目；OpenTask 每次手建里程碑 |
| Roadmap | E9-S2 明示 **Out of scope: Project templates** → 本轮收之 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Project 模板 mid**：表 `project_templates`（WS 作用域 + JSON payload）；CRUD API；`POST /projects?template_id=` 或 apply 端点 → 建 Project + **Milestone 种子**（按 `targetOffsetDays` 相对 `starts_at`/`today`）；可选「从现有项目另存为模板」（仅里程碑元数据）；FE 设置页 + 创建对话框选模板；CLI **1.56.0**；**不**复制 Issues / 附件 / 成员 / health 历史 | **中厚**；对齐 E9 Issue 模板模式；单 sprint 可交付 |
| B | Activity Push | 勿默认 |
| C | Customer 门户再厚 | prefer skip |
| D | Initiative 甘特 | prefer skip |
| E | Q2b / 表单附件 / 递归进度 / Bulk·Insights 多指派 | skip / rotate off |
| F | 仅 `POST /projects/{id}/duplicate`（深拷贝 Issues） | 偏厚+数据爆炸；非模板可复用 |
| G | Issue `start_date` 一等字段 | E8 后置项；可另弧；本轮 Project 模板更贴 runners-up #7 |
| H | 仅 FE 本地预设、无 BE 表 | **过薄**；CLI/多端不一致 |

**建议拍板：A（Project 模板 mid）。**  
Push / 门户 / 甘特 / Q2b / 表单附件 / 递归 / Bulk 多指派列入附录 runners-up。

自检：payload 契约、里程碑偏移、不复制 Issues、权限、FE/CLI **1.56.0**、非目标与 no-emit、不重开 E63–E71 邻面已写清。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push | 勿默认 |
| Customer 门户再厚 | prefer skip |
| Initiative 甘特 | prefer skip |
| Q2b / 表单公开附件 / 递归孙项 | rotate off / skip |
| Bulk/Insights 多指派拆分 | 刚交 E71；prefer skip |
| 再开 multi-assignee / childProgress / 评论附件 / Form / TZ / 假日 / Initiative 关系 | 刚闭 |
| 深拷贝 duplicate Issues | 过厚；权限/KEY-N/关系难 |
| Issue start_date | 另弧可后置 |
| Formula children rollup / emit | E40/E43 **永不** |

### Why this Epic now（一句话）

Issue 模板早已可预填，但 **开新 Project 仍手搓里程碑**——E9 明确 defer 的 Project 模板正好在 E71 协作弧刚闭后轮换离开指派/进度/附件/表单/TZ/门户/假日/依赖，用中厚刀补上 **可复用项目骨架（模板→Project+Milestones）+ FE/CLI**，对齐 Linear Project templates，且不碰深拷贝 Issues / Push / 甘特。

---

## 1. 目标

成功标准：工作区可 CRUD **Project 模板**；从模板 **创建 Project** 时写入 name/description（可覆盖）并种子化 **Milestones**（name/description/position/`target_date` 由 offset 推导）；可选将现有 Project **另存为模板**（仅里程碑骨架，**不**含 Issues）；FE 设置页 + 创建流选模板；CLI **1.56.0**；**不** Activity Push、**不**改 E63–E71 邻面主表面、**不** formula emit、**不**甘特/门户/多指派再开、**不**复制 Issues/附件/watchers。

### A · 数据 / BE

- alembic：表 `project_templates`  
  - `id`, `workspace_id`, `name`, `description?`, `icon?`, `payload` JSON, `sort_order`, `source` (`custom`|`builtin`), `seed_key?`, `created_by?`, timestamps  
  - `UNIQUE(workspace_id, name)`；可选 `UNIQUE(workspace_id, seed_key)` where not null  
- **payload 契约（Q1a）**：
  ```json
  {
    "description": "…",
    "milestones": [
      { "name": "Kickoff", "description": null, "position": 0, "targetOffsetDays": 0 },
      { "name": "Beta", "position": 1, "targetOffsetDays": 30 }
    ]
  }
  ```
- 上限：**Q3a** 每模板 milestones ≤ **30**；name 非空  
- Apply（**Q2a**）：`POST /api/projects` 增可选 `template_id`；或 `POST /api/project-templates/{id}/apply` body `{ name, description?, starts_at? }`  
  - 建 Project（name 必填覆盖；description 默认模板 payload/description）  
  - 对每个 milestone：`target_date = (starts_at or today UTC date) + targetOffsetDays`（null offset → null date）  
  - **不**建 Issues / relations / documents / watchers / health 历史  
- Save-as（**Q4a**）：`POST /api/project-templates/from-project/{project_id}` → 抽 milestones（name/description/position；`targetOffsetDays` 相对 project.starts_at 或首里程碑/today）  
- 权限：member+ 写；viewer 只读列表；跨 WS 404  
- 可选 1–2 个 builtin seed（可空；**Q4a** 不强制 seed，from-project 足够）

### B · API 面

- `GET/POST /api/project-templates`  
- `PATCH/DELETE /api/project-templates/{id}`  
- `POST /api/project-templates/{id}/apply`（若 create 带 `template_id` 已覆盖则可薄封装同一 service）  
- `POST /api/project-templates/from-project/{project_id}`  
- 列表返回 `{ rows, total }`；camelCase 对齐 Issue 模板

### C · FE

- 设置页：`/workspace/project-templates`（对齐 issue-templates）  
- Projects 创建对话框：模板下拉；选中后预填描述、展示将种子的里程碑预览  
- 项目详情：「另存为模板」按钮（member+）  
- vitest：offset→date / payload validate；build ok；守 E63 `f`+`r`

### D · CLI **1.56.0**

- `opentask project-template list|show|create|update|delete`  
- `opentask project-template apply --id … --name …`  
- `opentask project-template from-project --project-id … --name …`  
- `opentask project create --template-id …`（若已有 create 则扩展）  
- pins → **1.56.0**（**Q6a**）

### E · 安全 / 邻面 / no-emit

- 跨租户 404；模板与源 project 必须同 WS  
- **Q5a**：不新增 webhook 事件名；apply 仅走既有 project create 路径（若已有 `project.created` 则照旧；**无** `project_template.*`）  
- formula **no-emit**  
- **不**改 E63–E71 主表面（multi-assignee / childProgress / 评论附件 / Form / TZ / Initiative / 假日 / 门户 / 附件 ACL 仅 pins）

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户再厚、Initiative 甘特、Recurrence Q2b、表单公开附件、递归孙项进度  
- Bulk/Insights 多指派拆分；再开 multi-assignee / childProgress / 评论附件 / Form→Triage / TZ / 假日 / Search / Initiative 关系  
- 从模板 **复制 Issues** / 附件 / 文档 / watchers / CF 值 / automations  
- 深拷贝 `duplicate project`（含 Issue 图）  
- Issue `start_date` 一等字段；公式跨 Issue rollup；Formula emit  
- 远程 push / 开 PR / **自开 E73**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | alembic `project_templates`；CRUD；payload milestones 校验（≤30） |
| B | apply → Project + milestones；offset 日期正确；**0** Issues 被创建 |
| C | from-project 另存为模板；跨 WS 404；viewer 只读 |
| D | FE 设置页 + 创建选模板 + 另存；vitest+build；`f`+`r` 仍在 |
| E | CLI **1.56.0** + list/apply/from-project/create --template-id + pins |
| F | 无新 webhook 事件名；不改 E63–E71 邻面；formula no-emit |
| 门禁 | BE 定向 project-templates；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E73 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Project 模板 mid**（方案 A）；骨架模板 + milestones 种子；**无** Issues 深拷贝 / Push / 甘特 / 门户 |
| D2 | 表 `project_templates` + alembic；payload JSON 同构 Issue 模板风格 |
| D3 | Apply 只建 Project + Milestones；日期 = base + `targetOffsetDays` |
| D4 | 支持 from-project 另存（仅里程碑元数据） |
| D5 | 不新增 webhook 事件名 |
| D6 | CLI = **1.56.0** |
| D7 | 守 E40 D2/D7：永不 formula emit；不改 E63–E71 邻面；不 push；不自开 E73 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | payload 形状？ | **Q1a** `{ description?, milestones:[{name, description?, position?, targetOffsetDays?}] }`；备选 Q1b 再塞 default issue stubs（偏厚，易变深拷贝） |
| Q2 | apply 入口？ | **Q2a** `POST /projects` 可选 `template_id` + 同构 service apply；备选 Q2b 仅独立 `/apply`（创建流分叉） |
| Q3 | milestones 上限？ | **Q3a** 30；备选 Q3b 10（偏紧） / Q3c 无上限 |
| Q4 | 另存为 / builtin？ | **Q4a** 做 from-project；**不做**强制 builtin seed（可空）；备选 Q4b 再加 1–2 builtin（可后置） |
| Q5 | webhook？ | **Q5a** 不新增事件名；沿用既有 project create 行为；备选 Q5b `project_template.applied`（噪） |
| Q6 | CLI？ | **Q6a** project-template 子命令 + `project create --template-id` + pins **1.56.0**；备选 Q6b 仅 pins（过薄） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. alembic + model + payload validate helper（TDD）  
3. Service CRUD + apply（建 Project+Milestones）+ from-project（TDD）  
4. API routers + ProjectCreate.template_id（TDD）  
5. FE 设置页 + 创建选模板 + 另存  
6. CLI 1.56.0  
7. 邻面不动 / f+r / acceptance

---

## 7. 测试要点

- CRUD 同名冲突 400/409；跨 WS 404  
- apply：2 milestones offsets 0/30 → target_date 差 30 天；Issues count 仍 0  
- apply 覆盖 name/description  
- from-project：3 milestones → payload 3 项；再 apply 得到同构骨架  
- milestones 31 → 400  
- viewer POST → 403  
- spy：无新 webhook **事件名**；不触 E71 assignees / E70 childProgress 写 / E69 attach / E68 enqueue / E67 TZ / E66 ACL 主路径；formula no-emit  
- CLI 1.56.0 pins；FE vitest；build ok；`f`+`r` 仍在

---

## 附录 · runners-up（供 E73+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件** — E31 非目标。  
6. **递归孙项进度** — prefer skip。  
7. **Bulk/Insights 多指派拆分** — E71 刚交；prefer skip。  
8. **Issue start_date 一等字段** — E8 后置；另弧。  
9. **深拷贝 duplicate project（含 Issues）** — 过厚；有模板后再议。  
10. **模板内 Issue stubs** — Q1b；易变深拷贝，后置。

（备选扫描但本轮不推：再开 multi-assignee/childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.56.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E71-S1` @ `b95da6fa742aeae490acdd00d602966eb22c0f7a`  
- 拟开：`sprint/E72-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e72-project-templates-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E73**
