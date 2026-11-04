# E40 Design：Formula custom fields v1（只读计算列 / 沙箱求值）

日期：2026-11-04（Asia/Shanghai）  
Epic：E40  
基线：`sprint/E39-S1` @ `94e6e20`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E40-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E41**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E40-S1`。建议路径  
`docs/superpowers/specs/2026-11-04-e40-formula-custom-fields-design.md`  

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E25–E37 已交付自定义字段定义、取值、过滤/SmartSearch、CSV、自动化 CF 条件/动作、`custom_field_changed`、Board/List `cf:<key>` 泳道。  
**缺口反复写在 E34/E37/E38/E39 附录与非目标：** 无 **Formula（只读计算列）**。

Linear 手感：SeverityScore = `weight * impact`、SLA 剩余天、`IF(priority==urgent, 1, 0)` 等应出现在详情/列表，**不可手改**，依赖其它字段自动刷新。

E39 附录候选：

1. Formula custom fields（厚，安全求值）
2. Webhook `custom_field_changed` outbound（薄：E29 `events[]` + E36 emit）

另扫仓库缺口：

| 候选 | 现状 | 相对 ROI |
|------|------|----------|
| Project milestones | **E8 已交付** | 不重复 |
| SLA clocks（策略引擎） | 无；E38 仅 delay tick | 厚过单 sprint（策略×状态机×tick） |
| Issue activity/history export | `issue_timeline` + FE「活动」已有；CF/cycle/estimate **未入账**；无 export | 中；可作 E41 薄加厚 |
| Webhook CF outbound | E29 仅 `issue.created/updated/status_changed` + `comment.created`；E36 只打自动化 | 薄；宜插空或并入 webhook 事件包 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| A | **Formula v1 沙箱**：新 type=`formula`；表达式存定义；读时求值；白名单 AST；同 Issue 依赖 DAG | 厚且对齐全线 CF 成熟度；单 sprint 可控若砍跨 Issue/脚本/写入 |
| B | Webhook `custom_field_changed` outbound（+ 可选 assignee/label） | 实现小，但 Epic 偏薄，不符「加厚 Epic」 |
| C | Issue activity 加厚 + CSV/JSON export（补 CF/cycle timeline） | 中厚；不堵 Formula 明示缺口；timeline 面已大半存在 |

**拍板建议：A（Formula v1）。**  
Webhook outbound 与 Activity export 列入附录供 E41+。

自检：无 TBD；表达式语法、求值时机、安全面、FE/CLI **1.24.0**、非目标已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| Webhook `custom_field_changed` outbound | 薄扩展；ROI 低于补齐多轮附录 #1 Formula |
| SLA clocks | 需策略 CRUD + 状态时钟 + 违约 tick；易溢出单 sprint |
| Activity export | timeline 已有主路径；缺 CF 入账可另开薄 Epic |
| 完整 JS/Python eval / 跨 Issue rollup | 安全面过大；明确非目标 |

## 1. 目标

成功标准：WS 可定义 **只读** `formula` 字段；Issue 详情/列表/`customFields` 返回 **计算后的 value**；表达式仅引用白名单标识符；循环依赖拒绝；写路径拒绝改 formula 值；跨租户隔离；FE 可创建/展示；CLI **1.24.0**；**不**引入任意代码执行。

### A · 数据模型 + 校验

- `FIELD_TYPES` 增 **`formula`**
- `custom_fields`：
  - 复用 `options_json` **不**存选项；改用约定：`options_json` 对 formula 存 **空数组 `[]`**
  - 新增列 **`formula_expr`** (`Text`，nullable；仅 `type=formula` 非空)
  - 新增列 **`formula_result_type`** (`String(32)`，nullable；`number` | `boolean` | `text` | `date`；默认 **`number`**)
  - 迁移：`g3b4c5d6e7f1_formula_custom_fields`（命名按仓内 Alembic 惯例落地）
- 创建/更新校验（member+）：
  1. `type=formula` ⇒ 必须提供 `formulaExpr`（≤ 500 字符）+ `formulaResultType`
  2. 解析通过（见 §B）；依赖的 `cf.<key>` 必须存在于同 WS 且 **非 archived**；允许依赖其它 formula（DAG）
  3. **禁止环**：同 WS formula 字段依赖图无环；深度 ≤ **8**
  4. 非 formula 类型禁止带 `formulaExpr`
  5. `issue_custom_field_values`：**不**为 formula 存行（或存了也忽略）；upsert 含 formula fieldId → **400**
- 序列化 `serialize_field` 增：`formulaExpr`、`formulaResultType`（非 formula 为 null）
- `serialize_issue_field`：formula 的 `value` = 求值结果；另附 `computed: true`；`error` 可选短码（求值失败时 `value=null`）

### B · 表达式语言 + 沙箱求值

**解析器：** 手写 / `ast` 白名单（**禁止** `eval`/`exec`/`compile` 用户串进 builtins）。推荐：把表达式解析为受限 AST（仅 Constant / Name / BinOp / UnaryOp / Compare / BoolOp / IfExp / Call(白名单函数)）。

**字面量：** number、string（双引号）、boolean（`true`/`false`）、`null`

**标识符（大小写敏感）：**

| 标识符 | 含义 | 类型 |
|--------|------|------|
| `cf.<key>` | 同 Issue 其它 CF 当前值；formula 则递归求值 | 随源字段 / result_type |
| `issue.estimate_points` | Issue.estimate_points | number \| null |
| `issue.priority` | 优先级字符串 | text |
| `issue.status` | 状态字符串 | text |
| `days_until_due` | `due_date::date - utc_today()` 天数；无 due → null | number \| null |

**运算符：** `+ - * /`；`== != < <= > >=`；`and or not`；三元 `cond ? a : b` **或** 函数 `IF(cond,a,b)`（二选一，**拍板用 `IF` + 比较运算符**，不做 `? :` 以简化 lexer）

**函数白名单（大小写敏感）：**

| 函数 | 语义 |
|------|------|
| `IF(cond, a, b)` | cond 真 → a 否则 b；cond 仅 boolean |
| `COALESCE(a, b, …)` | 首个非 null |
| `ABS(x)` / `MIN(a,b,…)` / `MAX(a,b,…)` / `ROUND(x, n?)` | number |
| `LEN(s)` | text 长度 |
| `LOWER(s)` / `UPPER(s)` | text |
| `DATE_DIFF(a, b)` | 两 date/`YYYY-MM-DD` 差天数（a−b）；任一 null → null |

**求值规则（ADR D3–D6）：**

- 除法 `/`：浮点；除零 → 该字段 `error=div_zero`，value=null
- 类型不合（如 `1 + "x"`）→ `error=type_error`
- 依赖缺失 / 上游 error → 传播 `error=dep_error`（不抛 500）
- **读时计算**（详情、列表批量、`GET …/custom-fields` 挂在 issue 上的 values）；列表批量对可见 formula 字段求值；单 Issue 递归记忆化
- **不**写回 `issue_custom_field_values`；**不**发 `custom_field_changed`（计算结果变不触发自动化——ADR D7）
- 源字段变更后，下次读自然更新；E36 自动化仍只看写路径 CF

**安全硬约束：**

- 无属性穿透、无下标、无 f-string、无推导式、无 lambda、无 import、无名称绑定
- Call 仅白名单；Name 仅上表标识符（`cf.*` 经专用节点，非自由 Name）
- 解析失败 → 创建/更新字段 **400**；已存坏表达式（不应发生）读时 `error=parse_error`

### C · FE

- `/settings/custom-fields`（或现有 CF 管理页）：
  - 类型下拉增 **公式**
  - 选公式后：表达式 textarea + 结果类型 select + 只读说明（可用标识符/函数一览短文）
  - 保存前可可选「校验」按钮 → 调 `POST /api/custom-fields/validate-formula`（见 API）
- Issue 详情 `IssueCustomFieldsEditor`：
  - formula 行：**只读展示**计算结果；不可编辑；旁注 ƒ 或「公式」标签
  - 求值 error 时显示 `—` + tooltip 短错
- 列表 Display 列：已支持 CF 列则展示计算值；**不**要求本 Epic 新做按 formula 过滤（非目标可列 Gaps）
- Board `cf:<key>` 泳道：若 key 为 formula 且 result_type 非 single_select 语义 → **沿用 E37 写严读回退**（不进可选泳道列表，或选了读侧空桶）；**不**做拖拽改 formula

### D · CLI **1.24.0**

- `custom-field create --type formula --name … --expr '…' --result-type number|boolean|text|date [--key]`
- `custom-field update <id|key> --expr … --result-type …`（既有 update 扩展）
- `custom-field validate-formula --expr … [--result-type]` → 调校验 API，打印 deps / ok
- `issue show` / 字段列表：formula 显示计算值
- version → **1.24.0**（全仓历史 version 断言同步 bump）

## 2. 数据模型（摘要）

**改：**`custom_fields` + `formula_expr` + `formula_result_type`；`FIELD_TYPES` + `formula`。  
**不改：**`issue_custom_field_values` 表结构（formula 无行）。  
**复用：**E25 CRUD/权限；E32 列表挂载 `customFields`；E37 泳道对非 select 回退。

伪代码（读路径）：

```
def eval_formula(field, issue, cache, stack):
    if field.id in cache: return cache[field.id]
    if field.id in stack: raise CycleError
    stack.add(field.id)
    ast = parse(field.formula_expr)          # already validated on write
    env = build_env(issue, cf_values, recursive=eval_formula)
    try:
        raw = interpret(ast, env)
        value = coerce(raw, field.formula_result_type)
        cache[field.id] = (value, None)
    except FormulaError as e:
        cache[field.id] = (None, e.code)
    stack.remove(field.id)
    return cache[field.id]
```

## 3. API

| 面 | 行为 |
|----|------|
| `POST /api/custom-fields` | body 增 `formulaExpr` / `formulaResultType`；type=formula 时校验 |
| `PATCH /api/custom-fields/{id}` | 可改 expr / result_type；重跑依赖图校验（若被其它 formula 依赖且 result_type 变更 → 仍允许，下游读时 type_error） |
| `POST /api/custom-fields/validate-formula` | body `{ formulaExpr, formulaResultType? }`；返回 `{ ok, dependencies:["cf.x",…], error? }`；member+ |
| `GET` 字段列表 / Issue 详情·列表 `customFields` | formula 带计算 `value` + `computed:true` + 可选 `error` |
| `PUT/PATCH` Issue CF values | 含 formula field → **400** `公式字段只读` |

权限：与 E25 同（member+ 写定义；viewer 读计算值）；强制 `X-Workspace-Id`；跨租户 404。

## 4. FE

- CF 设置：公式类型 + expr + result type + 校验
- 详情：只读 ƒ 行
- 列表列：显示计算值（有 Display 钩则接；无则最小可用）
- 不改 Automations / Webhooks / Due reminders 主路径

## 5. CLI

- **1.24.0**
- `custom-field create|update` formula 参数；`validate-formula`；version 断言全仓同步
- help 示例：`--expr 'IF(issue.priority == "urgent", 10, COALESCE(cf.weight, 0) * COALESCE(cf.impact, 0))'`

## 6. 安全 / 租户

- **无** `eval`/`exec`/子进程；仅白名单 AST 解释器
- 表达式长度 ≤ 500；函数参数个数 ≤ 8；AST 节点数 ≤ 200（超限 400）
- 依赖仅当前 WS 字段；`cf.<key>` 解析不到 → 校验失败（写）或读时 `dep_error`
- 计算结果 **不**经自动化 emit、**不**经 outbound webhook（避免算杀循环）
- 租户：一切查询带 `workspace_id`
- 公式定义写入仍 require_writer；viewer 不能改 expr

## 7. 非目标

- 跨 Issue / Project rollup、`SUM(children.*)`、关联图聚合
- JavaScript/Python 任意脚本、正则、网络、时间 sleep
- 将 formula 结果物化写入 DB / 触发 `custom_field_changed` / webhook
- 按 formula 值过滤、SmartSearch `field:`、Board 泳道主路径（读回退即可）
- 可写公式、循环赋值、用户自定义函数
- Webhook `custom_field_changed` outbound（附录）
- SLA 策略引擎；Activity CSV export
- 进程内 cron；远程 push / 开 PR / 自开 E41

## 8. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | `formula` 类型 + 列；环/深度拒绝；非 formula 无 expr；values upsert 拒写 formula |
| B | 白名单求值；`IF`/`COALESCE`/算术；除零与类型错误 → value null + error；依赖 formula 记忆化 |
| C | FE 可建公式字段；详情只读展示；校验 API 可用 |
| D | CLI 1.24.0 + create/update/validate-formula + version 断言 |
| 门禁 | BE 定向+全量绿（记 passed/skip）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E41 |

## 9. ADR

| ID | 决定 |
|----|------|
| D1 | 新 type=`formula`；expr 存在 `formula_expr` 列（不用 options_json 塞字符串） |
| D2 | **读时求值、不物化**；不写 `issue_custom_field_values` |
| D3 | 受限 AST 解释器；禁止 eval/exec；节点/长度上限 |
| D4 | 标识符仅 `cf.*` + `issue.estimate_points|priority|status` + `days_until_due` |
| D5 | 函数白名单：IF/COALESCE/ABS/MIN/MAX/ROUND/LEN/LOWER/UPPER/DATE_DIFF |
| D6 | 同 WS formula DAG 无环，深度 ≤ 8；校验在 create/update |
| D7 | 计算结果 **不**触发 automations / webhooks |
| D8 | upsert formula 值 → 400 只读 |
| D9 | CLI **1.24.0**；全仓 version 断言同步 |
| D10 | 非目标见 §7；不 push；不自开 E41 |

## 10. 测试要点

- BE：create formula ok；环依赖 400；深度超限 400；非法 AST 400
- BE：读写 Issue：number 公式计算正确；`IF`/`COALESCE`；除零 error
- BE：依赖另一 formula 链式求值；源 number 变更后再次 GET 值变
- BE：upsert 试图写 formula → 400；viewer 读 ok、写定义 403；跨 WS 404
- BE：列表批量多 Issue 求值无串租户
- FE：创建设置 + 详情只读；校验按钮
- CLI：version 1.24.0；create formula；validate-formula；show 见计算值
- 回归：E25 非 formula 类型；E32 过滤；E36 emit（改 number 仍 emit，改「计算结果」不发）；E37 泳道

## 11. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. Migration + FIELD_TYPES + create/update 校验（TDD，含环检测）  
3. Parser/interpreter + validate-formula API + Issue 序列化求值  
4. FE 设置 + 详情只读  
5. CLI 1.24.0  
6. 门禁 + acceptance tip  

---

## 附录 · 本轮未选但仍高 ROI（供 E41+）

1. **Webhook `custom_field_changed` outbound**：E29 `WEBHOOK_EVENTS` 增事件；在 E36 `_emit_custom_field_changed` 旁路 `fire_webhooks`；FE 多选 + CLI（**薄**，可插空）。  
2. **Issue activity 加厚 + export**：CF/cycle/estimate/project 变更写入 `issue_timeline`；`GET …/timeline/export.csv` + CLI；补今日「活动」与审计面。  
3. **SLA clocks**：策略 × 状态时钟 × 外部 tick（厚，需独立 Epic）。  
