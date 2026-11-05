# E43 Design：Formula surfaces v1（过滤 · SmartSearch · 泳道；安全缓存可选）

日期：2026-11-05（Asia/Shanghai）  
Epic：E43  
基线：`sprint/E42-S1` @ `4d52b9a`（feature tip `c478528`；design `a4a03a0`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E43-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E44**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E43-S1`。开放问题 Q1–Q5 均按建议默认关闭  
建议路径：`docs/superpowers/specs/2026-11-05-e43-formula-surfaces-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40 交付 Formula CF v1：受限 AST 沙箱、**读时求值、不物化**（D2）、计算结果 **不**触发 automations / webhooks（D7）。  
E32 已有 `cf.<key>` 列表过滤 + SmartSearch `field:`/`cf:`；E37 已有 Board `cf:<key>` 泳道。  
现状缺口（代码实证）：

| 面 | 现状 |
|----|------|
| `coerce_cf_filter_value` | `type=="formula"` → 恒 `None` → 过滤结果空集 |
| `apply_list_filters` | 只走 `IssueCustomFieldValue` SQL；formula 无存值行 |
| FE `isGroupingCfType('formula')` | **false**（泳道/分组不可选） |
| Display / 详情 | 读时求值已可用（E40） |

E40/E41/E42 附录连续把 **Formula 过滤 / SmartSearch / 泳道 / 可选物化** 标为下一高 ROI；E42 选了 SLA clocks v1，本轮补齐公式「能看也能筛」。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Formula surfaces v1**：list/`cf.` 过滤 + SmartSearch + Board/List `cf:<formula_key>` 分组/泳道；可选 **查询缓存**（非 emit 物化）；保留 E40 D2/D7；CLI **1.27.0** | **中厚且连贯**；闭合多轮附录 #1；安全面用 ADR 收窄 |
| B | Webhook 事件包加厚（`assignee_changed` / `label_*`）+ 投递重试 UI | 偏薄；E41/E42 刚加 webhook 事件，ROI 递减 |
| C | SLA v2 薄片（暂停 / breach→automation；无营业日历） | 刚交 E42；宜先沉淀时钟语义；附录已标 v2 |
| D | WS 全局活动 feed 产品化 | UI 重；E41 CSV export 已够审计 |

**拍板建议：A（Formula surfaces v1）。**  
Webhook 事件包、SLA v2、全局 feed 列入附录供 E44+。

自检：过滤语义、求值/缓存安全、泳道、权限、FE/CLI **1.27.0**、非目标已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Webhook 事件包 | 薄；`issue.updated.changed[]` 已覆盖大半；刚叠 E41 CF / E42 SLA 事件 |
| SLA v2（营业时/暂停/升级） | E42 次日再加厚易溢；先观察 v1 使用 |
| 全局活动 feed | 产品化 UI Epic；审计导出已有 |
| 完整物化 + emit | 明确打破 E40 D7；算杀循环风险；**本 Epic 不做** |

## 1. 目标

成功标准：用户可对 **formula** 自定义字段做与普通 CF 同契约的 **列表过滤**（`cf.<key>`）与 SmartSearch（`field:`/`cf:`）；Board/List 可将 `cf:<formula_key>` 作为分组/泳道维（按 `formulaResultType` 呈现）；跨租户隔离；求值失败/空值有确定语义；**不**因过滤/缓存触发 automations 或 outbound webhooks；FE 过滤器与泳道可选公式字段；CLI **1.27.0**；**不**引入进程内 cron / JS eval / 跨 Issue rollup。

### A · 过滤语义（BE）

- 扩展 `coerce_cf_filter_value`：`formula` 按 `formula_result_type` 走与对应存储类型相同的 coerce  
  - `number` → int/float（同 number）  
  - `text` → string  
  - `boolean` → true/false 集合  
  - 未知/缺失 result_type → 默认 `number`
- 扩展 `apply_list_filters`：**formula 键不走 `IssueCustomFieldValue` SQL**  
  - 路径（**ADR D3 — 批求值后过滤**）：  
    1. 先应用其它非 formula `cf.` 过滤与普通 Issue 过滤，得到候选 ID 集（或可延迟物化的 query）  
    2. 对候选批量 `values_for_issues`（复用 E40 求值器）取出公式计算值  
    3. 内存匹配（AND）；写回 `Issue.id.in_(matched_ids)`  
  - **上限（ADR D4）**：单次请求 formula 过滤时，求值候选硬顶 **`FORMULA_FILTER_CANDIDATE_CAP = 2000`**（先 count；超限 → **400** `formula_filter_too_broad`，提示收窄其它过滤条件）。避免全表算杀。  
  - 无其它过滤、仅 formula 过滤且 WS Issue 总数 > cap → 同样 400（强制先加 status/assignee/project 等）
- 匹配：等值（与 E32 一致）；`null`/求值 `error` → **不匹配**（除非显式约定；v1 不支持 `cf.key=` 空串匹配 error）
- **不**新增 range 操作符（`gt`/`lt`）——与现网 CF 等值契约对齐；列入 Gaps / 开放问题

### B · 可选查询缓存（安全物化 · 非 emit）

- **拍板默认：做薄缓存（ADR D5）**，否则大列表过滤难达验收手感  
- 新表 **`issue_formula_cache`**（WS 作用域）：  
  - `issue_id` + `field_id` PK（或 uuid PK + unique(issue_id, field_id)）  
  - `workspace_id` FK CASCADE  
  - `value_json` (nullable JSON)  
  - `error` (nullable str：`parse_error`/`type_error`/`dep_error`/`div_zero`…)  
  - `computed_at` DateTime UTC naive  
  - 索引：`(workspace_id, field_id)`；过滤可 `value_json` 等值（PG JSONB；SQLite JSON）
- **写入时机（仅这些，禁止其它）**：  
  1. 依赖 CF 值 upsert 成功后（同请求 best-effort）：重算「依赖该 key 的」formula 行并 upsert cache  
  2. formula 定义 create/update（expr / result_type 变更）：异步或同请求 **失效**（删 cache 行）该 field 全 WS；下次读/过滤再填  
  3. Issue 影响公式的原生字段变更（`priority` / `status` / `due_date` / `estimate_points`——以 E40 `issue_get` 白名单为准）：best-effort 刷新依赖这些标识符的 formula cache  
- **明确禁止**：cache 写入 **不**调用 `_emit_custom_field_changed` / `fire_automations` / `fire_webhooks` / timeline（守住 E40 D7）  
- 过滤路径：有 cache 行且 `error is null` → 可走 SQL/半 SQL；miss 或 error → 回退批求值并回填 cache  
- Display 读路径：**可继续纯读时求值**（E40）；允许读 cache 作加速但结果不一致时以求值器为准（或统一「cache hit 则用 cache」——**开放问题 Q1**，建议：过滤用 cache+回退；详情/include 仍走现网 `values_for_issues` 以求稳）

### C · SmartSearch / FE 过滤 UI

- SmartSearch：现有 `field:key:value` / `cf:key:value` → `cf.<key>`；**后端一旦接受 formula key 即自动生效**；parser 无需新语法  
- FE：过滤芯片 / 字段选择器对 `type==='formula'` **解禁**（按 `formulaResultType` 渲染 number/text/boolean 控件）  
- 文案：标明「计算值（只读）」；error 态 Issue 不会出现在等值命中里

### D · Board / List 分组与泳道

- FE：`isGroupingCfType` — `formula` 当 `formulaResultType ∈ {number,text,boolean}` 时视为可分组（映射到既有呈现）；**禁止**把 formula 当 multi_select  
- 分组桶键 = 序列化后的计算值字符串；`null`/error → `__empty__` / `__error__`（与无标签桶风格一致；**ADR D6**：error 独立桶，避免与空值合并）  
- Board 行维 `cf:<formula_key>`：复用 E37 路径；数据来自 list `include=custom_fields` 的计算值（不必为泳道单独 API）  
- **拖拽改公式值**：不可能（只读）——跨泳道拖拽对 formula 维 **禁用** 或 no-op + toast（对齐「展示-only」）

### E · API / 错误面

| 场景 | 行为 |
|------|------|
| `cf.<formula_key>=x` 正常 | 等值过滤计算值 |
| 未知 key | 空结果（E32 既有） |
| 候选超 cap | **400** + 稳定 `detail`/`code` |
| formula 已归档 | 同未知/空（或 400；**建议空结果**与归档 CF 过滤一致——实现时对齐 E32 归档行为） |
| 跨 WS | 既有 X-Workspace-Id；不泄漏 |

无新公开 REST 资源亦可交付；若做 cache，**不**暴露 cache CRUD API（内部表）。

### F · CLI **1.27.0**

- `issue list --cf <formula_key>=<value>` 对公式键生效（契约不变，行为修复）  
- help / 文档示例补一行 formula 过滤  
- version → **1.27.0**；全仓历史 version 断言同步  
- 可选：`custom-field show` 已见计算值则不动

### G · 数据模型摘要

**新增（若采纳 D5 缓存）：** `issue_formula_cache` + Alembic revision（down_revision = E42 `i5d6e7f8a9b3`）

**修改：** `coerce_cf_filter_value` / `apply_list_filters`；FE grouping 白名单；依赖写路径挂钩 cache 失效/刷新

**不改：** `issue_custom_field_values` 仍禁止写 formula；WEBHOOK_EVENTS / automation triggers **不**因公式结果变化新增

**复用：** E40 `parse_formula` / `eval_parsed` / `values_for_issues`；E32 `cf.` 契约；E37 `cf:` 泳道

## 2. 安全 / 租户 / 威胁模型

- 继续：**无** `eval`/`exec`/子进程；沿用 E40 AST 上限  
- 过滤 cap 防 DoS（全 WS 逐 Issue 求值）  
- cache 刷新失败 → 记 log，不阻断主写路径；下次过滤回退求值  
- **禁止** cache/求值结果进入 automation / webhook / timeline（回归测必须覆盖）  
- 租户：一切 query/cache 带 `workspace_id`；跨租户 404/空  
- 无 SSRF 新面；无任意代码

## 3. 非目标

- 将公式结果写入 `issue_custom_field_values` 或触发 `custom_field_changed` / webhook / timeline  
- 跨 Issue / children rollup、JS/Python 脚本、用户自定义函数  
- 过滤 range 操作符（`>`/`<`）、排序 by formula（可后置）  
- SLA v2（营业日历 / first-response / 暂停 / breach→automation）  
- Webhook 事件包加厚；WS 全局活动 feed  
- 进程内 cron；远程 push / 开 PR / 自开 E44

## 4. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | `cf.<formula_key>` 等值过滤命中计算值；error/null 不命中；与 number CF 过滤共存 AND |
| B | 超 cap → 400；跨 WS 不泄漏；归档/未知 key 行为与 E32 对齐 |
| C | SmartSearch `field:formulaKey:value` → 同过滤 |
| D | Board/List `cf:<formula_key>` 分组/泳道可见；error 独立桶；不可拖拽改值 |
| E | 改依赖 number **不**发「公式结果」automation/webhook；改 number 本身仍发 E36/E41（回归） |
| F | 若启用 cache：依赖变更后过滤结果更新；cache 写不打 webhook |
| G | FE 过滤器可选 formula；CLI **1.27.0** + version 断言 |
| 门禁 | BE 定向+全量绿（记 passed/skip；`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E44 |

## 5. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = Formula surfaces **v1**（方案 A）；闭合 E40 非目标「过滤/泳道」 |
| D2 | **延续** E40：读时求值为真相来源之一；**禁止** emit（automation/webhook/timeline） |
| D3 | formula 过滤 = 批求值（或 cache）后等值匹配；不假装有 `IssueCustomFieldValue` 行 |
| D4 | 单请求候选硬顶 2000；超限 400 `formula_filter_too_broad` |
| D5 | **做** `issue_formula_cache` 查询缓存；写路径 best-effort 刷新/失效；非值物化 |
| D6 | 泳道/分组：error → `__error__` 桶；空 → `__empty__`；禁止拖拽写公式 |
| D7 | 等值 only；无 range/sort-by-formula |
| D8 | CLI **1.27.0**；全仓 version 断言同步 |
| D9 | 非目标见 §3；不 push；不自开 E44 |

## 6. 测试要点

- BE：建 number 依赖公式；`cf.score=10` 命中/不命中；改依赖后再次过滤变结果  
- BE：仅 formula 过滤且 Issue 很多 → 400 cap  
- BE：formula + 普通 `cf.` AND；跨 WS 404/空  
- BE：依赖 CF upsert 后 **无** 额外 `issue.custom_field_changed` 因公式结果发出（spy/计数）  
- BE：cache miss 回退求值；定义变更失效 cache  
- FE：`isGroupingCfType('formula')` true（在允许的 result_type 下）；过滤控件  
- CLI：version 1.27.0；`issue list --cf …` 对公式键  
- 回归：E32 非 formula 过滤；E37 非 formula 泳道；E40 详情求值；E36/E41 emit；E42 SLA 无关

## 7. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. coerce + apply_list_filters 批求值路径 + cap（TDD）  
3. Migration `issue_formula_cache` + 写路径刷新/失效（TDD；emit 负例）  
4. FE 过滤解禁 + grouping/swimlane + 拖拽禁用  
5. CLI 1.27.0  
6. 门禁 + acceptance tip  

## 8. 开放问题（Yuri 已拍板关闭）

| ID | 问题 | 拍板 |
|----|------|------|
| Q1 | 详情/list `include=custom_fields` 是否改读 cache？ | **否**；保持 `values_for_issues`；cache 仅服务过滤加速 |
| Q2 | 是否本轮就做 cache，还是先纯批求值？ | **做 cache（D5）** |
| Q3 | number 公式要不要 `gt`/`lt`？ | **不要**（D7）；E44+ |
| Q4 | cap 2000 是否改成可配 WS 设置？ | **否**；常量即可 |
| Q5 | `text` 公式过滤大小写？ | 与 text CF 一致（区分大小写，除非 E32 已规范化） |

---

## 附录 · 本轮未选但仍高 ROI（供 E44+）

1. **Webhook 事件包加厚**：`issue.assignee_changed` / `label_added` / `label_removed` 等专用事件 + 投递重试/死信 UI。  
2. **SLA v2**：营业日历、first-response metric、暂停（waiting-on-customer）、breach → automation 动作链。  
3. **WS 全局活动 feed**：产品化时间线（E41 CSV 已够审计导出）。  
4. **Formula range / sort-by-formula / Display 条件格式**。
