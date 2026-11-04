# E32 设计：Custom Fields surfaces（列表列 + SmartSearch）

日期：2026-11-04（Asia/Shanghai）  
Epic：E32  
基线：`sprint/E31-S1` @ `6923085`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E32-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E33**。

## 1. 目标

接 E25 非目标：让自定义字段进入日常列表过滤、SmartSearch 与 Display 列。

### A · BE 列表 / 过滤
- 保持 `include=custom_fields` 语义
- Issue list 支持按字段过滤（见 ADR D1）
- 类型匹配：text/number/single_select/date → 等值；boolean → true/false；multi_select → 包含
- 字段必须属当前 workspace；跨租户 key 视为无匹配

### B · SmartSearch
- 语法 `field:<key>:<value>`（别名 `cf:<key>:<value>`）
- 无效 key → **空结果**（不 400）
- 深链仍走 `?q=` 原串

### C · FE Display + 列表
- Display prefs 扩展 `custom_field_keys: string[]`
- 显示面板可勾选 WS 内活跃自定义字段；列表勾选后渲染列并自动 `include=custom_fields`
- SmartSearch 建议含 `field:key:value` 提示

### D · CLI **1.16.0**
- `issue list --cf key=value`（可重复）
- version → 1.16.0

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | List API 过滤用扁平 query **`cf.<field_key>=value`**（可多键）；另接受重复 `cf=key=value` 作 CLI/脚本兼容 |
| D2 | SmartSearch 主语法 **`field:key:value`**；`cf:key:value` 为别名；value 取首个 `:` 之后全部 |
| D3 | 未知 / 他租户 key → AND 空集（0 行），**不 400**（对齐未知 label 体验） |
| D4 | 匹配：scalar JSON 等值；boolean 接受 `true/false/1/0/yes/no`；multi_select 用 JSONB `contains([value])` |
| D5 | Display `display_json.custom_field_keys: string[]`（有序）；与现有 prefs / saved view 同键，不平行系统 |
| D6 | 勾选 CF 列或存在 cf 过滤时 list 带 `include=custom_fields` |
| D7 | CLI 1.16.0；`--cf key=value` → `cf.<key>=value`；无独立 `issue search` 契约变更则 `list --search` 可透传含 `field:` 的文本（服务端仍靠 cf.* 过滤，不解析 search 串） |
| D8 | 不做公式/字段级权限/CSV CF 列/看板 CF 泳道/Automations 条件深化；不 push；不自开 E33 |

## 3. 非目标

公式字段、字段级权限、CSV 自定义列、看板按 CF 泳道、Automations 条件深化、远程 push、E33。

## 4. 验收摘要

- BE：`cf.<key>` 过滤 + 租户隔离 + include 保持；pytest
- FE：prefs 列 + SmartSearch `field:` + list 列
- CLI 1.16.0 `--cf`；本地 tip；**不 push**
