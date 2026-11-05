# E34 设计：CSV × Custom Fields（接 E28/E32）

日期：2026-11-04（Asia/Shanghai）  
Epic：E34  
基线：`sprint/E33-S1` @ `c1764e2`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E34-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E35**。

## 1. 目标

让 Issue CSV 导入/导出带上自定义字段列（`cf.<key>`），与 E25 类型校验 / E28 upsert 语义对齐。

### A · Export
- `GET /api/issues/export.csv`：在固定列后追加 `cf.<key>`（当前 WS **未归档**字段）
- 列顺序：E28 固定列 → CF 按 `position` asc、`created_at` asc（与 `CustomFieldService.list` 一致）
- 仍尊重 list 同过滤 + viewer+ + 10k + `X-Export-Truncated`
- 无值 / 无该字段取值 → 空单元格

### B · Import
- 模板与 import 识别表头 `cf.<key>`（大小写不敏感前缀 `cf.`）
- upsert 成功后按 E25 `validate_value` 写入；`multi_select` 逗号分隔；`boolean` 仅 `true`/`false`（大小写不敏感）
- **未知 key**：Issue 其它列仍创建/更新成功；该单元格记入 `errors[]`（`row` + `message` 含 `cf.<key>`），**不阻断**整行主字段
- **类型校验失败**：同未知 key——主字段已成功则计 created/updated，CF 错误进 `errors[]`
- 空单元格：**跳过**（不写、不清空）

### C · FE
- Import 对话框说明提到 `cf.*`；模板下载含当前 WS CF 列头
- Export 成功提示可轻提「含自定义字段列」（可选）

### D · CLI **1.18.0**
- `issue export|import` help 注明 CSV 含 `cf.<key>`；version → **1.18.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 列名格式固定 `cf.<key>`（与 E32 过滤 `cf.<key>` 对齐）；key 大小写敏感匹配定义（slug 本已小写） |
| D2 | 仅导出/模板 **未归档**字段；归档字段不出现在新模板；旧 CSV 含归档 key → 按未知/归档不可写记 error |
| D3 | 未知 / 校验失败 CF：**partial success**——主列 upsert 计分，CF 写入跳过并 `errors[]`；推荐文案 `cf.<key>: …` |
| D4 | 空 CF 单元格 = 跳过；不提供 CSV 清空语义（清空请用 API / 详情） |
| D5 | `multi_select` 仅 `,` 分隔（与 labels 的 `;`/` ,` 不同，写清） |
| D6 | `boolean` 仅接受 `true`/`false`（trim + lower）；其它记校验错误 |
| D7 | 模板 endpoint 改为按 workspace 动态列头；无 CF 时与 E28 列一致 |
| D8 | CLI 1.18.0；全仓 version 断言同步 bump；help 文案提到 `cf.<key>` |
| D9 | 非目标：附件、公式字段、看板 CF 泳道、Jira/Linear 同步；不 push；不自开 E35 |

## 3. 非目标

附件二进制、公式字段、看板 CF 泳道、Jira/Linear 同步、远程 push、E35。

## 4. 验收摘要

- Export 含 `cf.*` + 过滤/截断；Import 模板/写入/未知 key partial；FE 文案；CLI 1.18.0
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**
