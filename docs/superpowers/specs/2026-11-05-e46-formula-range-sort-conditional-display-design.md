# E46 Design：Formula query surfaces v2 — range · sort · Display 条件格式

日期：2026-11-05（Asia/Shanghai）  
Epic：E46  
基线：`sprint/E45-S1` @ `3a499af`（design `f6683d2`；acceptance 文件 tip 仍写 `aacc4ec`，属 tip-bump 残余）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E46-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E47**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E46-S1`。开放问题 Q1–Q6 均按建议默认关闭。建议路径  
`docs/superpowers/specs/2026-11-05-e46-formula-range-sort-conditional-display-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40 交付 Formula CF v1（沙箱、读时求值、**不 emit**）。  
E43 交付 Formula surfaces v1：`cf.<formula>` **等值**过滤 + SmartSearch + Board/List 泳道 + 安全 cache（仍不 emit）。  
E42/E45 闭合 SLA clocks → pause + breach→automation；E44 闭合 webhook 事件包+投递可靠性。

E43 ADR **D7** 与 E45 附录明确把下一刀留给：

1. **Formula range / sort-by-formula / Display 条件格式**（接 E43 等值过滤）  
2. WS 全局活动 feed  
3. SLA 营业日历 / first-response / 策略优先级  
4. 其它专用 webhook（cycle/estimate）

代码实证 @ `3a499af`：

| 面 | 现状 |
|----|------|
| `parse_cf_query_items` | 仅 `cf.<key>=value` / `cf=key=value` → 等值；**无** op |
| `apply_list_filters` / `_match_formula_candidates` | 等值 `_formula_values_equal`；stored CF 亦等值 JSON |
| `IssueService` `allowed_sort` | `created_at/updated_at/position/priority/status/title/due_date` — **无** `cf:*` |
| `display_json`（E7） | `fields` / `group_by` / `swimlane_by` / `customFieldKeys` — **无**条件着色规则 |
| Formula cache（E43） | 可加速等值；range/sort 可复用同一 cache，仍 **禁止 emit** |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Formula query surfaces v2**：CF/formula **range 操作符**（number/date）+ **`sort_by=cf:<key>`**（number/text/date/boolean；优先 formula）+ Display **`conditionalFormats[]`**（阈值→行/单元格着色）；守 E40 D2/D7；CLI **1.30.0** | **中厚且连贯**；闭合多轮附录 #1；列表/看板「算得出→筛得出→排得出→看得见」闭环 |
| B | WS 全局活动 feed 产品化 | UI 重；E41 单 Issue/WS timeline CSV 已够审计；非查询面 ROI |
| C | SLA 营业日历 / first-response / 策略优先级 | 运维+新 metric 语义；E45 刚交 v2 thin，宜沉淀；单刀易溢 |
| D | 仅 range **或** 仅 sort（无条件格式） | **偏薄**；不符「加厚 Epic」 |
| E | 完整 spreadsheet 条件格式 + 跨列公式规则引擎 | 单 sprint 必溢 |

**拍板建议：A（Formula query surfaces v2 — range · sort · conditional display）。**  
全局 feed、SLA 日历/first-response、pause timeline、专用 cycle/estimate webhook 列入附录供 E47+。

自检：操作符契约、sort 稳定性与 cap、条件格式 JSON 形状、权限、FE/CLI **1.30.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| WS 全局活动 feed | 产品化 UI Epic；审计导出已有（E41） |
| SLA 营业日历 / first-response | E45 次日再加厚易溢；日历矩阵测试面大 |
| pause timeline（`sla_paused`/`sla_resumed`） | 薄；可挂 E47 小刀或 SLA 日历同包 |
| `issue.cycle_changed` / `estimate_changed` webhook | 薄；`issue.updated.changed[]` + E41 timeline 已覆盖 |
| Formula 物化 emit | 明确打破 E40 D7；算杀循环；**永不本轮** |

## 1. 目标

成功标准：用户可对 **number/date**（含 formula 结果类型）自定义字段做 **range 过滤**（`gt/gte/lt/lte`，可与等值并存 AND）；列表可用 **`sort_by=cf:<key>`** 按 CF/formula 计算值排序（稳定二级键）；Display / Saved View 可存 **条件格式规则**，List/Board 行或 CF 单元格按规则着色；跨租户隔离；超宽候选仍受 E43 cap 约束（range/sort 共用）；**不**因过滤/排序/着色触发 automations / outbound webhooks / timeline；FE 过滤器·排序·Display 面板可用；CLI **1.30.0**；**不**引入营业日历 / 全局 feed / 进程内 cron / JS eval。

### A · Range 操作符（BE 过滤）

扩展查询解析（**开放问题 Q1**，建议默认 **Q1a**）：

| 语法 | 含义 |
|------|------|
| `cf.<key>=v` | 等值（既有） |
| `cf.<key>[gt]=v` / `[gte]` / `[lt]` / `[lte]` | 严格/含等比较 |
| `cf=key[gt]=v` | 对称短形 |

实现要点：

- `parse_cf_query_items` → 产出 `(key, op, raw)`，`op ∈ {eq,gt,gte,lt,lte}`，缺省 `eq`  
- **适用类型**：stored `number`/`date`；formula 且 `formulaResultType ∈ {number,date}`  
- **不适用**：text/boolean/select/multi_select/formula-text|boolean → **400** `cf_range_unsupported`（等值仍可用）  
- 比较语义：number 数值比较；date 按 `YYYY-MM-DD` 字典序（与存值一致）；`null`/formula `error` → **不匹配**（同 E43）  
- 同一 key 多 op AND（例：`gte=1` + `lt=10`）；同 key 多 `eq` 保持既有「最后/AND」行为——**建议 AND 全部**（与多 `cf.` 一致）  
- Formula 路径：复用 `_apply_formula_list_filter` / cache；匹配函数由 eq 扩为 op；**仍受 `FORMULA_FILTER_CANDIDATE_CAP=2000`**  
- Stored number/date：SQL JSON 比较（PG JSONB 数值/文本；SQLite 对齐测试）  
- SmartSearch：扩展 `cf:key>5` / `cf:key>=5` 等（**Q2**）；若本轮 FE 芯片足够，parser 可后置——**建议本轮做薄解析**（`>` `>=` `<` `<=` `:`）以免 CLI/SmartSearch 分叉

### B · Sort by CF / formula

- `GET /api/issues`（及等价 list）：`sort_by` 接受  
  - 既有系统键  
  - **`cf:<field_key>`**（小写 key）  
- 校验：字段存在、未归档；类型 ∈ `{number,text,date,boolean}` **或** formula 且 `formulaResultType` 同集合；否则 **400** `cf_sort_unsupported`  
- 算法（ADR D4）：  
  1. 先应用全部过滤（含 range）得候选  
  2. 若候选 count > **`FORMULA_SORT_CANDIDATE_CAP = 2000`**（可与 filter cap 同常量别名）→ **400** `formula_sort_too_broad`（提示先过滤）  
  3. 批量取 CF 值 / formula cache+求值  
  4. 内存排序：`null`/`error` **一律排末**（asc/desc 均 nulls last）；稳定二级键 `created_at` 再 `id`  
- `sort_order=asc|desc` 沿用  
- **不**改默认 `created_at`；Saved View `sort_json` 允许 `{ "by": "cf:score", "order": "desc" }`（读写透传；应用 View 时交给 list API）  
- Board 列内排序：若现网 Board 走同一 list API 则自动生效；不另开 Board 专用 sort API

### C · Display 条件格式（FE + 契约）

扩展 `display_json`（个人 prefs + Saved View `display` 共用）：

```json
{
  "conditionalFormats": [
    {
      "id": "cfmt_1",
      "when": { "field": "cf:risk", "op": "gte", "value": 8 },
      "style": { "rowTint": "danger" | "warning" | "success" | "info" | "neutral" },
      "target": "row" | "cell"
    }
  ]
}
```

约束（ADR D5）：

- 最多 **10** 条 / display；超出 normalize 截断或写时 400（**建议写时 400**）  
- `field`：系统少量白名单（`priority`/`status`/`due_date`/`estimate_points`）**或** `cf:<key>`（含 formula）  
- `op`：`eq|neq|gt|gte|lt|lte`；text/select 仅 `eq|neq`；boolean 仅 `eq`  
- `style.rowTint`：枚举语义色（映射 DESIGN.md/Naive 令牌，**不**收任意 CSS）  
- `target=row`：整行背景淡色；`target=cell`：仅该 CF 单元格（系统字段则映射对应列）  
- 求值：**纯客户端**基于 list payload 的 `customFields` / 系统列（与 E43 展示一致）；**不**新开 BE 着色 API  
- normalize：未知 field/op/tint → 丢弃该条；保数组稳定  
- FE：Display 面板可增删改规则；List/Board 应用；vitest 覆盖 normalize + tint 映射  
- **不做**：公式表达式写在 when 里、图标集、多 style 合并冲突 UI（冲突时 **先匹配先生效**，文档说明）

### D · FE

- 过滤芯片：number/date（含 formula 结果）提供比较符选择（= / > / ≥ / < / ≤）  
- 列表排序菜单：CF/formula 字段可选（只读标识）  
- Display：条件格式小节；预览色点  
- 最小 vitest：parse op；sort key；conditionalFormats normalize；徽标/着色分支

### E · CLI **1.30.0**

- `issue list --cf 'score[gte]=8'` 或重复 flag 文档化（与解析器对齐）  
- `issue list --sort cf:score --order desc`  
- help 示例 1–2 行；version → **1.30.0**；全仓 version 断言同步  
- 不强制 CLI 管理 conditionalFormats（prefs 仍走 API/FE；可选 `--json` 透传 display 留给 Gaps）

### F · 数据模型摘要

**修改（预期无强制新表）**：

- 过滤/排序纯行为扩展 + 测试  
- `display_json` / prefs normalize 认知扩展（JSON 形状，无 migration）  
- 若 Q1 选键名含 `[]`，注意网关/客户端编码；单测覆盖

**复用**：E43 formula cache + cap；E32 `cf.` 过滤；E7 display_prefs；E4 saved views sort_json  
**不改**：formula emit 禁令；HMAC；SLA；webhook 事件集

## 2. 安全 / 租户 / 威胁模型

- 一切 list/sort/filter 带 `workspace_id`；跨租户 404/空  
- range/sort 候选硬顶防算杀（复用/对齐 2000）  
- conditionalFormats 不接受任意 CSS/URL；仅枚举 tint  
- formula cache 读写路径 **仍禁止** `_emit_custom_field_changed` / `fire_automations` / `fire_webhooks` / timeline（E40 D7 / E43）  
- 非法 op/类型 → 400，不静默当 eq  
- 无进程内 cron；无营业时注入

## 3. 非目标

- Formula 物化写入 `issue_custom_field_values` 或 emit automation/webhook/timeline  
- 跨 Issue rollup / JS·Python eval / 新公式函数大礼包  
- 完整 Excel 级条件格式（图标集、色阶梯度连续映射、公式规则 DSL）  
- WS 全局活动 feed；SLA 营业日历 / first-response / 策略优先级  
- pause timeline；`issue.cycle_changed` / `estimate_changed` 专用 webhook  
- Redis / 进程内 cron；远程 push / 开 PR / 自开 E47

## 4. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | `cf.<num>[gte]=` / `[lt]=` 对 stored number 与 formula(number) 生效；非法类型 400；等值回归绿 |
| B | date range 生效；null/error 不命中 |
| C | `sort_by=cf:<formula_key>` asc/desc；nulls last；超 cap 400；系统 sort 回归 |
| D | Saved View `sort_json` 含 `cf:` 可保存并应用 |
| E | `conditionalFormats` 读写 normalize；List/Board 行/单元格 tint；>10 条写失败或截断按 ADR |
| F | FE：过滤比较符 + 排序项 + Display 规则编辑；vitest 绿 |
| G | CLI **1.30.0** + range/sort 示例 + version 断言 |
| H | 回归：E43 等值过滤/泳道/cache；E40 no-emit；E45 SLA pause；E44 webhook 可靠性 |
| 门禁 | BE 定向+全量记 passed/skip（`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E47 |

## 5. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = **Formula query surfaces v2：range + sort-by-cf + Display conditionalFormats**（方案 A） |
| D2 | 守 E40 D2/D7：读时/cache 求值；**永不**因本 Epic 路径 emit |
| D3 | Range 仅 number/date（含对应 formulaResultType）；其它类型等值 only |
| D4 | `sort_by=cf:<key>`；候选硬顶 2000；null/error nulls last；稳定二级 `created_at`,`id` |
| D5 | `conditionalFormats` ≤10；枚举 tint；客户端求值；先匹配先生效 |
| D6 | 过滤 op 默认语法 **`cf.<key>[op]=value`**（Q1a）；SmartSearch 薄扩展（Q2a） |
| D7 | 无新表/migration（除非实现中发现 prefs 校验必须版本戳——默认不要） |
| D8 | CLI **1.30.0**；全仓 version 断言同步 |
| D9 | 非目标见 §3；不 push；不自开 E47 |

## 6. 测试要点

- BE：number formula `gte`/`lt` 命中集正确；与 eq AND  
- BE：date range；unsupported type 400  
- BE：sort cf:score desc；error 行在末；cap 超限 400  
- BE：stored number range SQL 路径  
- BE：spy — range/sort/cache 路径 **无** webhook/automation/timeline emit  
- FE：op 芯片；sort 菜单；conditionalFormats normalize + rowTint  
- CLI：1.30.0；`--cf 's[gte]=1'`；`--sort cf:s`  
- 回归：E43 eq filter + swimlane；E45 SLA；E44 deliveries

## 7. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. parse op + stored number/date range（TDD）  
3. formula range match + cap（TDD）  
4. sort_by=cf: + cap + saved view sort_json（TDD）  
5. display_json conditionalFormats normalize + FE Display/List/Board  
6. SmartSearch 薄 op（若 Q2a）+ CLI 1.30.0  
7. 门禁 + acceptance tip  

## 8. 开放问题（Yuri 已拍板关闭）

| ID | 问题 | 拍板 |
|----|------|------|
| Q1 | Range 查询语法 | **Q1a** `cf.<key>[op]=value` |
| Q2 | SmartSearch 是否本轮支持 `cf:score>=8`？ | **是（Q2a）** 薄解析 |
| Q3 | `sort_by=cf:` 类型 | **text/boolean/date/number 允许**；multi_select **否**（400） |
| Q4 | conditionalFormats 冲突 | **数组序先匹配先生效** |
| Q5 | 条件格式进 CSV export？ | **否**；仅 UI |
| Q6 | range 开放给 stored number/date？ | **是** |

---

## 附录 · 本轮未选但仍高 ROI（供 E47+）

1. **WS 全局活动 feed**：产品化跨 Issue 时间线（E41 CSV 已够审计导出）。  
2. **SLA 营业日历 / first-response metric / 策略优先级**（E45 已 pause+breach→automation）。  
3. pause timeline 事件（`sla_paused` / `sla_resumed`）。  
4. 其它专用 webhook（`issue.cycle_changed` / `estimate_changed`）。  
5. Formula 色阶（连续 color scale）/ 图标集条件格式。
