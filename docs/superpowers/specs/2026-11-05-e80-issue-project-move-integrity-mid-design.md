# E80 Design：Issue project-move integrity mid · CLI 1.64.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E80  
基线拟：`sprint/E79-S1` @ `d84f6e4`（全文 `d84f6e40064888c9d879b448c8c049a9e821503d`；E79 design 基线 `c07f94b` ⊂ HEAD；E78 tip `6fe2b57` ⊂ HEAD）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E80-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E81**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e80-issue-project-move-integrity-mid-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E80-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E79 连续闭合 … → Issue 父子转换（E78）→ **Project lead + members mid（E79：roster-only · CLI 1.63.0）**。

E79 附录 runners-up（任务硬指引）：

1. **换项目清无效 milestone** — **真缺口**；偏薄 → **本轮加厚为 mid**（project-move integrity）  
2. **Activity Push** — 仍 **勿默认**  
3. **Customer 门户再厚** — **prefer skip**  
4. **Initiative 甘特** — **prefer skip**  
5. **Recurrence Q2b** — **rotate off**  
6. **表单公开附件** — **prefer skip**  
7. **递归孙项进度** — **prefer skip**  
8. **Bulk/Insights 多指派** — **prefer skip**  
9. **深拷贝 duplicate project** — **prefer skip**  
10. **模板内 Issue stubs** — **prefer skip**  
11. **CSV start_date / start reminders** — **后置**  
12. **depth≥2 threading** — **后置**  
13. **评论版本史 / 编辑加厚** — **另弧**  
14. **G-then-X** — **另弧**  
15. **复制附件/子树** — **过厚**  
16. **Issue merge** — **过厚**  
17. **Timed purge/hard-delete** — **后置**  
18. **`archived_at` dual-track** — **prefer skip**  
19. **Project 私有 ACL** — **另大弧**（E79 非目标，勿跟风）

轮换离开刚闭弧：**lead/members / parent-set / trash / links / duplicate / threading / start_date / templates / multi-assignee / childProgress / 评论附件 / Form→Triage / TZ / 假日 / Initiative deps / 附件 ACL / Search / Insights**。

代码实证 @ `d84f6e4`：

| 面 | 现状 |
|----|------|
| Milestone 作用域 | `milestones.project_id` **必填**；`_validate_milestone_id` 要求 `milestone.project_id == issue.project_id` |
| Update 路径 | FE 详情换项目只 PATCH `{project_id}`；**不**带 `milestone_id` → BE **不**跑 milestone 校验、**不**清旧值 → **跨项目孤儿 milestone_id** 可落库 |
| Duplicate | `create_payload` 固定抄 `source.milestone_id`；若 override `project_id` 跨项目，create 校验易 400 或残留语义不清 |
| Cycle | WS 作用域；换项目通常可保留（本轮 **不清** cycle） |
| FE | `watch(project_id)` 仅 `loadMilestones`；换项目保存后 UI 仍可能短暂显示旧 milestone 名 |
| CLI | `issue update` **无** `--project` / `--milestone`；无法脚本化「换项目并见证清里程碑」 |
| Linear 对齐 | 换 Project 后 Milestone 必须属于新 Project；孤儿引用不合法 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Issue project-move integrity mid**：换 `project_id` 时自动清无效/一律清 milestone；duplicate 跨项目不抄 milestone；FE 清本地选择 + 提示；CLI **1.64.0** `issue update --project`/`--milestone`；timeline  thrift 记清；无新 webhook；cycle 保留 | **中厚**；真缺口；单 sprint；离开 lead/parent/trash |
| B | 仅 BE 一行 `milestone_id=None` | 过薄；缺 FE/CLI/duplicate/验收面 |
| C | Activity Push / 门户 / 甘特 / Q2b / … | 勿默认 / skip / 后置 / 另弧 / 过厚（同 E79 表） |
| D | Project 私有 ACL | 另大弧；禁搭 E79 |
| E | Issue merge / 深拷贝附件子树 | 过厚 |

**建议拍板：A（Issue project-move integrity mid）。**  
其余列入附录 runners-up。

自检：不重开 E79 lead/members、E78 parent、E77 trash、E76 links、E75 duplicate **主语义**（仅修跨项目 milestone 边）、E72 templates；CLI **1.64.0**；formula no-emit；无 Push/甘特/门户。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Activity Push / 门户 / 甘特 | 勿默认 / prefer skip |
| Q2b / 表单附件 / 递归 / Bulk / 深拷贝 / stubs | skip |
| CSV start / depth≥2 / 评论版本 / G-then-X / 复制附件 | 后置 / 另弧 / 过厚 |
| purge / archived_at / merge | 后置 / skip / 过厚 |
| Project 私有 ACL | 另大弧 |
| 再开 lead/members / parent / trash / links / … | 刚闭 |
| 仅薄清 milestone | 任务要求 mid；用 integrity 包 FE+CLI+duplicate 边升厚 |

### Why this Epic now（一句话）

E79 名册刚齐后轮换离开 Project ACL/名册面；**换项目仍可留下跨项目孤儿 `milestone_id`**（FE 只传 project、BE 不自清）——用中厚刀一次补上 **BE 自清 + duplicate 边 + FE 同步 + CLI 可写 project/milestone**，对齐 Linear「Milestone 从属于 Project」约束，且不动 cycle、不碰 merge/私有项目。

---

## 1. 目标

成功标准：member+ 将 Issue 换到另一 Project（或清空 Project）后，**不会**再持有不属于新 Project 的 `milestone_id`；duplicate 跨项目 override 不带着旧 milestone 炸校验；FE 换项目后里程碑 UI 一致；CLI **1.64.0** 可 `issue update --project` / `--milestone`；viewer 写 403；跨租户 404；**不**清 cycle；**不** Activity Push；**不**改 E63–E79 邻面主表面；**不** formula emit；**不**自开 E81。

### A · BE

- **Q1a** 换 `project_id`（含 `null`）且值相对持久化有变时：**自动** `milestone_id = null`，除非同请求 **显式** 提供对新 project 合法的 `milestone_id`（**Q2a** 显式优先）  
  - 同值重提 `project_id` → 不触发清  
  - 备选 Q1b「仅当旧 milestone.project_id ≠ 新 project」——行为接近，但 Q1a 更简单可测（换项目即清，避免同名跨项目误留）  
- **Q3a** `duplicate`：若 override `project_id` ≠ source.project_id（或目标 project 下 source milestone 不合法），**不**抄 `source.milestone_id`（置 null；允许 override 另传 milestone——若 API 已有字段则用，否则本轮可不扩 duplicate body）  
- Update / board-move 等一切改 `project_id` 的写路径共用同一 helper（避免只修 PATCH）  
- **Q4a** 读路径 **不**静默改库；序列化仍回存库值。孤儿数据靠下次写自清；可选验收用定向脏数据测「写时清」  
- Timeline：**Q5a** 在既有 `project_changed` 的 `action_data` 增加 `milestone_cleared: true` + `milestone_from`（若有）；**无**新 timeline enum、**无**新 webhook 名  
- formula no-emit；不清 `cycle_id`；不改 label/tag/assignee/parent/trash  

权限：写仍 member+；viewer 403；跨租户 404。

### B · FE

- 详情换项目保存成功后：本地 `tempMilestone` / 展示值清为「无」；`loadMilestones(newProjectId)`  
- 可选轻提示：「已清除原项目里程碑」（不新开 toast 体系也可用现有 message）  
- Milestone 选择器 options 仅新项目列表  
- vitest：抽纯函数更好测（例：`nextMilestoneAfterProjectMove(oldProject, newProject, milestoneId) → null | id`）；build ok；守 E63 `f`+`r`

### C · CLI **1.64.0**

- `opentask issue update <id> --project <projectId>`（空字符串/显式 clear 语义：**Q6a** `--project ""` 或 `--clear-project` 二选一，建议 `--project` + 允许空清）  
- `opentask issue update <id> --milestone <id>` / `--clear-milestone`  
- show/update 输出可见 `project_id` + `milestone_id`；换项目后断言 milestone 已空（定向测）  
- pins → **1.64.0**；历史 epic 断言级联  

### D · 安全 / 邻面 / no-emit

- 跨租户 404；viewer 写 403  
- **不**引入 project-private ACL；不改 E79 roster  
- 不触 parent/trash/links/附件/VCS 主路径；duplicate **仅**修 milestone 边，不扩复制附件/子树  
- 不改 E70 childProgress / E72 template apply  
- 无 Push / 门户 / 甘特；formula no-emit  

---

## 2. 非目标

- Activity Push / FCM / 浏览器 Notification  
- Customer 门户、Initiative 甘特、Q2b、表单公开附件、递归孙项进度、Bulk/Insights 多指派  
- 深拷贝 project、模板 Issue stubs、CSV start_date、depth≥2 评论树、评论版本史、G-then-X、复制附件/子树  
- Issue merge、purge/hard-delete、`archived_at`  
- **清 cycle**（WS 作用域，保留）  
- **Project 私有 ACL / 按 member 过滤 Issue**  
- 再开 lead/members / parent / trash / links / threading / start_date / templates / multi-assignee  
- 批量 `bulk_update` 扩 `project_id`（E20 bulk 现状无 project；本轮可不扩——非目标；若顺手加须同 helper）  
- Formula emit；远程 push / 开 PR / **自开 E81**

---

## 3. 验收标准（Acceptance 草图）

| ID | 标准 |
|----|------|
| A | PATCH 仅改 `project_id`（跨项目）→ 响应/DB `milestone_id is null`；同请求显式合法 milestone → 保留该值 |
| B | project→null → milestone 清；同值重提 project → milestone 不变 |
| C | duplicate 换 project override → 新 Issue milestone 为空（或不炸 400） |
| D | timeline `project_changed.action_data` 含 cleared 信息；无新 webhook 名；formula no-emit |
| E | FE 换项目后里程碑 UI 为空并加载新项目 options；vitest+build；`f`+`r` 仍在 |
| F | CLI **1.64.0** + `issue update --project`/`--milestone` + pins |
| G | 不改 E63–E79 邻面主表面；cycle 保留；无 Push/甘特/门户 |
| 门禁 | BE 定向 e80/project-move；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E81 |

---

## 4. ADR（建议默认；Yuri 拍板即确认）

| ID | 决策 |
|----|------|
| D1 | Epic = **Issue project-move integrity mid**（方案 A） |
| D2 | 换 project 自动清 milestone（显式合法 milestone 例外）；cycle 保留 |
| D3 | 无新 webhook / 无新 timeline enum；`project_changed` action_data 扩字段 |
| D4 | duplicate 跨项目不抄 source milestone |
| D5 | CLI = **1.64.0** |
| D6 | 守 E40 D2/D7；不改 E63–E79 邻面；不 push；不自开 E81 |

---

## 5. 开放问题（均附建议默认，Yuri 可一键全收）

| Q | 问题 | 建议默认 |
|---|------|----------|
| Q1 | 清 milestone 策略？ | **Q1a** 任意 `project_id` **值变化**即清（除非 Q2 显式新值）；备选 Q1b 仅当旧 milestone 不属于新 project |
| Q2 | 同请求带新 milestone？ | **Q2a** 显式 `milestone_id` 且通过 `_validate_milestone_id(新 project)` → 采用；非法 → 400（不清成静默错） |
| Q3 | duplicate？ | **Q3a** 跨项目（或目标下非法）不抄 source milestone；同项目仍抄 |
| Q4 | 历史孤儿读路径？ | **Q4a** 读不改库；靠写时清；备选 Q4b get 时 lazy heal（本轮不做） |
| Q5 | timeline / webhook？ | **Q5a** 扩 `project_changed.action_data`；无新枚举/无新 webhook 名 |
| Q6 | CLI？ | **Q6a** `issue update --project` + `--milestone` / `--clear-milestone` + pins **1.64.0**；备选 Q6b 仅文档说明无新旗标（不选） |

---

## 6. 切片建议（实现时 plan 用）

1. Design 入库（Yuri 拍板后）+ plan  
2. BE helper：`apply_project_move_integrity(update_data, existing)` + update/duplicate 接入（TDD）  
3. timeline action_data 扩字段（无 alembic enum）  
4. FE 换项目 UX + vitest helper  
5. CLI 1.64.0 `issue update --project|--milestone`  
6. 邻面不动 / f+r / acceptance  

---

## 7. 测试要点

- 仅改 project A→B 且旧 milestone 属 A → milestone null；cycle 不变  
- 同 PATCH：`project_id=B, milestone_id=<B的里程碑>` → 保留  
- `project_id=B, milestone_id=<A的里程碑>` → 400  
- project→null → milestone null  
- 同值 project 重提 → milestone 不变  
- duplicate `--project`/`override` 跨项目 → 新 issue milestone null  
- spy：无新 webhook 事件名；formula no-emit；E79 lead/members API 未改行为  
- CLI 1.64.0 pins；FE vitest；build ok；`f`+`r` 仍在  

---

## 附录 · runners-up（供 E81+；若 Yuri 改选可替换本草案）

1. **Activity 实时/推送加厚** — 仍勿默认。  
2. **Customer 门户再厚** — prefer skip。  
3. **Initiative 甘特精修** — prefer skip。  
4. **Recurrence Q2b advance** — rotate off。  
5. **表单公开附件** — prefer skip。  
6. **递归孙项进度** — prefer skip。  
7. **Bulk/Insights 多指派** — prefer skip。  
8. **深拷贝 duplicate project** — prefer skip。  
9. **模板内 Issue stubs** — prefer skip。  
10. **CSV start_date / start 提醒** — 后置。  
11. **depth≥2 / 服务端树** — 后置。  
12. **评论版本史 / 评论编辑 UX 加厚** — 另弧。  
13. **G-then-X 导航热键** — 另弧。  
14. **复制附件/子树** — 过厚。  
15. **Issue merge** — 过厚。  
16. **定时 purge / hard-delete** — 后置。  
17. **`archived_at` 双轨** — prefer skip。  
18. **Project 私有 ACL / 按 member 过滤 Issue** — 另大弧。  
19. **bulk_update 支持 project_id + 同 integrity helper** — 可作 E80 后薄刀。  
20. **读路径 orphan milestone lazy-heal（Q4b）** — 后置。  

（备选扫描但本轮不推：再开 lead/members/parent/trash/links/duplicate 主面/threading/start_date/templates/multi-assignee/childProgress/评论附件/Form/TZ/假日/Search/Insights/Initiative 关系 — 刚闭。Webhook/PagerDuty — 出站弧已闭。真 GitHub App / SSO / formula children rollup — 过厚或禁。Formula emit — 永不。）

## CLI 版本

**1.64.0**

## 基线 / 分支（拍板后）

- Baseline tip：`sprint/E79-S1` @ `d84f6e40064888c9d879b448c8c049a9e821503d`  
- 拟开：`sprint/E80-S1`  
- 入库：`docs/superpowers/specs/2026-11-05-e80-issue-project-move-integrity-mid-design.md`  
- **本地 only**；不 push / 不开 PR；**大软不自开 E81**
