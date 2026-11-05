# E37 Design：Board / List 按 Custom Field 分组（CF 泳道）

日期：2026-11-04（Asia/Shanghai）  
Epic：E37  
基线：`sprint/E36-S1` @ `e13254b`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E37-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E38**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E37-S1`

## 0. Brainstorming（Yuri 代审上下文）

### 背景
E7 已交付看板泳道 `assignee|priority|type|label` 与列表 `groupBy`；E25/E32 已交付 CF 定义、详情/列表列、`cf.<key>` 过滤与 SmartSearch `field:`。E32/E34/E36 **反复把「看板按 CF 泳道」标为非目标**。日常 Linear 手感缺口：Severity / Customer Tier / Area 等单选字段无法成为 Board 行维。

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| A | 仅 FE：`groupIssuesBy` / `boardSwimlanes` 读已 include 的 `customFields`，`swimlane_by=cf:<key>` | 实现最快；无服务端校验；Saved View 跨端脆弱 |
| B | **Display prefs + Saved View 一等公民 `cf:<key>`；列表需 CF 时自动 `include=custom_fields`；BE 校验 key 属本 WS 且 type∈{single_select,boolean,text,number,date}**（采纳） | 与 E7/E32 同构；可测；租户安全 |
| C | 服务端返回预聚合泳道矩阵 API | 过重；破坏现有客户端矩阵 |

**拍板建议：B。** 不做公式字段、不做 multi_select 泳道（选项爆炸）、不做自动化 delay（另 Epic）。

自检：无 TBD；单选主路径清晰；范围单 sprint 可交付；CLI 1.21.0。

## 1. 目标

成功标准：用户可把 Board 行维 / List groupBy 设为某个**活跃**自定义字段；Saved View / Display prefs 可持久化；跨租户 key 无效；FE 可操作；CLI **1.21.0**。

### A · Display / Saved View 契约
- 扩展 `SwimlaneBy` / `GroupByKey`：在既有枚举外，允许字符串形态 **`cf:<field_key>`**（小写 slug，与 E25 key 规范一致）
- `display_json` / saved view `display`：
  - `swimlane_by`: `'none'|'assignee'|'priority'|'type'|'label'| 'cf:<key>'`
  - `group_by`: `'none'|'status'|'assignee'|'priority'|'type'|'label'| 'cf:<key>'`
- BE `display_prefs` 规范化：若为 `cf:*`，校验字段存在、未归档、属当前 `workspace_id`；非法 → **400**（写 prefs）或读时回退 `'none'`（容错旧数据，ADR D3）
- Saved View 创建/更新同样校验；应用 View 时恢复 `swimlane_by` / `group_by`

### B · FE Board 泳道 + List 分组
- `groupIssuesBy`：支持 `cf:<key>` —— 从 issue.`customFields`（或等价 enrich）取该 key 的展示桶：
  - `single_select`：按 option `value` 分桶，标签用 `label`；未知/空 → `__empty__`
  - `boolean`：`true` / `false` / `__empty__`
  - `text`|`number`|`date`：按规范化字符串分桶；空 → `__empty__`
  - **`multi_select`：本期不支持作泳道**（选择器隐藏；若 prefs 误存 → 回退 none + toast）
- `boardSwimlanes`：复用上述分组；列维仍为 status；空泳道显隐沿用 E7
- Display 面板：泳道/分组下拉在系统维之后列出 WS 活跃 CF（仅允许类型见上）；选中后 list/board 自动 `include=custom_fields`
- Issue Board / List：切换 CF 泳道后矩阵正确；拖拽改状态行为不变（不跨泳道改 CF，**本期非目标**）

### C · BE 辅助（薄）
- 可选：`GET /api/custom-fields?for=grouping` 或复用现有 list + FE 过滤类型（优先复用，少 API）
- Issue list：当 query/display 暗示 CF 分组时，服务端**不强制**改默认；由 FE 带 `include=custom_fields`（与 E32 一致）
- 负例测试：跨租户 `cf:otherkey` 写 prefs → 400；归档字段 → 400；`cf:` + multi_select key → 400

### D · CLI **1.21.0**
- `opentask issue list --group-by cf:<key>`（若已有 `--group-by` 则扩展 choice；否则新增并透传/本地说明）
- 或：`saved-view` / display 相关命令若存在则支持写入 `swimlane_by=cf:key`；**至少** version bump + help 示例 + 一则契约测证明 `cf:` 被接受
- version → **1.21.0**（全仓历史 version 断言同步）

## 2. 数据模型

**无新表。** 复用：
- `custom_fields` / `issue_custom_field_values`（E25）
- `issue_display_prefs.display_json`（E7）
- `issue_saved_views` 的 display/filter JSON（E4/E7）

值约定：
```json
{
  "group_by": "cf:severity",
  "swimlane_by": "cf:severity",
  "custom_field_keys": ["severity"],
  "fields": { "...": true }
}
```
选中 `cf:<key>` 时，建议自动把该 `key` 并入 `custom_field_keys`（去重），保证列与 include 一致。

## 3. API

| 面 | 行为 |
|----|------|
| `PUT/PATCH` display prefs | 接受 `swimlane_by`/`group_by`=`cf:<key>`；校验 WS+类型 |
| Saved views CRUD | 同左 |
| Issue list | 不变契约；FE `include=custom_fields` |
| 无新公开资源 | 除非复用 list 不够再加 `?usable_for=grouping` 过滤（可选） |

权限：与 E7 相同——member+ 写 prefs/views；viewer 读共享 view；强制 `X-Workspace-Id`。

## 4. FE

- `display-prefs.ts`：`SwimlaneBy` / 校验放宽为 `cf:${string}` + 系统枚举
- `groupIssuesBy.ts` + `boardSwimlanes.ts` + 单测
- Display 面板下拉；Board/List 消费
- Automations / CF 设置页**不改**（非本 Epic）

## 5. CLI

- **1.21.0**
- Help 示例：`opentask issue list --group-by cf:severity`（或等价）
- 测：version 串；非法/帮助含 `cf:`

## 6. 安全 / 租户

- `cf:<key>` 解析后必须 `CustomField.workspace_id == 当前 WS` 且 `archived_at IS NULL`
- 他租户同名 key → 视为不存在 → 写 400 / 读回退 none
- viewer 不能改 prefs（既有）
- 不在泳道拖拽时隐式写 CF（防误改）

## 7. 非目标

- 公式字段、关联实体字段、字段级权限
- multi_select 泳道 / 拖拽改 CF
- 自动化 delay / 多步流水线 / Slack
- due digest / RRULE / 日历 UI
- 远程 push / 开 PR / 自开 E38

## 8. 验收标准（Acceptance）

| 项 | 标准 |
|----|------|
| A | prefs/views 可存 `cf:<key>`；非法 key/类型/跨租户 400；归档拒绝 |
| B | Board 按 single_select（及允许标量）分泳道；List groupBy 同语义；空桶；空泳道开关 |
| C | 选 CF 泳道自动 include + 可选并入 custom_field_keys |
| D | CLI 1.21.0 + 帮助/测 |
| 门禁 | BE 定向+全量绿（记录 passed/skip）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E38 |

## 9. ADR

| ID | 决定 |
|----|------|
| D1 | 编码：`cf:<field_key>` 单字符串，复用 E25 slug；不引入平行 `swimlane_field_id` |
| D2 | 允许类型：`single_select`（主）、`boolean`、`text`、`number`、`date`；**禁止 multi_select** |
| D3 | 写路径严格校验；读到历史非法值 → 回退 `none`（不炸页面） |
| D4 | 矩阵仍客户端计算；不新增聚合 API |
| D5 | 拖拽只改 status（列维）；不改 CF（行维） |
| D6 | CLI **1.21.0** |
| D7 | 非目标见 §7；不 push；不自开 E38 |

## 10. 测试要点

- BE：合法 `cf:key` 写入 prefs；unknown/other-ws/archived/multi_select → 400；viewer 403
- FE unit：`groupIssuesBy('cf:severity')` 分桶；空值；board 矩阵行数
- FE：Display 下拉仅列允许类型
- CLI：version 1.21.0；help 含 cf:
- 回归：原 `assignee|priority|type|label` 泳道不受损

## 11. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. BE 校验 + 测（TDD）  
3. FE groupBy/swimlane + Display + vitest  
4. CLI 1.21.0  
5. 门禁 + acceptance tip  

---

## 附录 · 未选但仍高 ROI 的候选（供 E38+）

1. **Automation delayed / scheduled actions**：`delay_minutes` + `POST /api/automations/run-due`（对齐 E35 外部 tick）；补 E26/E33 非目标。  
2. **Due reminders + digest tick**：到期前提醒 Inbox/email（E27/E30 digest 非目标）；`run-due-reminders`。  
3. **Formula custom fields**：只读计算列；安全求值面大，宜独立厚 Epic。  
4. **Webhook `custom_field_changed` 事件**：接 E36 emit 出站（E29 事件集扩展）。  
