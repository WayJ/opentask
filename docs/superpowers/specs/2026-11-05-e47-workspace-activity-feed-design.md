# E47 Design：WS Activity Feed v1 — JSON 游标 API · 薄 FE · CLI 1.31.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E47  
基线：`sprint/E46-S1` @ `c37a23e`（全文 `c37a23ed4768f0acba5667327cc170da8d2ad2f5`；design `b5b132e`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E47-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E48**。  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E47-S1`。开放问题 Q1–Q6 均按建议默认关闭。建议路径  
`docs/superpowers/specs/2026-11-05-e47-workspace-activity-feed-design.md`

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E46 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 thin → Formula query surfaces v2。  
E46 附录与 E42–E45 附录反复把下一刀标为：

1. **WS 全局活动 feed**（产品化跨 Issue 时间线；E41 CSV 已够审计导出）  
2. **SLA 营业日历 / first-response / 策略优先级**（E45 已 pause + breach→automation）  
3. pause timeline（`sla_paused` / `sla_resumed`）— 偏薄  
4. 专用 webhook `issue.cycle_changed` / `estimate_changed` — 偏薄（`issue.updated.changed[]` + E41 timeline 已覆盖大半）  
5. Formula 色阶 / 图标集 — UI 抛光

Yuri 既有 runners-up 备注（**不绑定**）：(1) feed UI 重；(2) SLA 日历/first-response = 运维 + 新 metric，且 E45 刚交 thin pause 宜沉淀。

代码实证 @ `c37a23e`：

| 面 | 现状 |
|----|------|
| `issue_timeline` | E41 已写入 CF/cycle/estimate/project 等；单 Issue `GET /api/issues/{id}/timeline` |
| WS CSV | `GET /api/issues/timeline/export.csv`（since / issueId / actionType / cap 10000）— **无** JSON 分页 feed |
| Dashboard「最近动态」 | `dashboard_service._get_recent_activities` = 最近改动的 Issue/需求卡片，**不是** timeline 事件流 |
| CLI | `issue timeline` / `timeline-export`；**无** workspace activity list |
| SLA | E45 pause + breach→automation；**无** `sla_paused`/`sla_resumed` timeline；**无** first-response metric；**无**营业日历 |
| Webhook | E44 已有 assignee/label/CF/sla_breached；**无**专用 cycle/estimate 事件名 |
| Formula | E40 D2/D7 **永不 emit** — 本轮继续守 |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **WS Activity Feed v1（API-first）**：复用 `issue_timeline` 提供 **JSON 游标分页** + 过滤；FE **精简** Activity 页（非仪表盘抛光）；Dashboard 仅链「全部」；CLI **1.31.0** `activity list`；守 no-emit | **中厚且连贯**；闭合多轮附录 #1；用「API+CLI + 薄 FE」回应「UI 重」；不碰 SLA 运维面 / emit |
| B | SLA first-response + pause timeline（**不含**营业日历 / 策略优先级 UI） | 中厚；但 E45 次日再加厚 metric 语义易溢；Yuri 已标沉淀 |
| C | 专用 `cycle_changed`/`estimate_changed` webhook + pause timeline | **偏薄**；事件名可由 `issue.updated.changed[]` 覆盖 |
| D | 完整 Linear Updates（反应、订阅、推送、富媒体）+ 营业日历 | 单 sprint 必溢 |
| E | Formula 色阶 / 图标集 | UI-only 抛光；ROI 低于产品面闭环 |

**拍板：A（WS Activity Feed v1 — JSON · 薄 FE · CLI）。**  
SLA first-response/日历、pause timeline、cycle/estimate 专用 webhook 列入附录供 E48+。

自检：分页/过滤契约、权限、与 E41 CSV 并存、FE 范围上限、CLI **1.31.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| SLA 营业日历 / first-response / 策略优先级 | 运维矩阵 + 新 metric；E45 刚交 pause，宜沉淀；易爆 SLA 设置 UI |
| pause timeline 单独 | 薄；可挂 E48 与 first-response 同包 |
| `issue.cycle_changed` / `estimate_changed` webhook | 薄；timeline + `changed[]` 已覆盖 |
| Formula 色阶/图标集 | UI 抛光；非中厚产品闭环 |
| Formula 物化 emit | 打破 E40 D7；**永不本轮** |

## 1. 目标

成功标准：工作区成员可在 **JSON Activity Feed** 中按时间倒序浏览跨 Issue 的 `issue_timeline` 事件；支持 since / actionType / actor / issue / 游标分页；硬顶防炸；跨租户隔离；FE 提供 **精简** Activity 流（列表 + 跳转 Issue，无反应/无订阅扇出）；Dashboard「最近动态」仅链到完整 Feed（**不**替换现卡片语义）；CLI **1.31.0** 可 list；**不**因读 feed 触发 automation/webhook/timeline；**不**引入营业日历 / first-response / formula emit / 进程内 cron。

### A · JSON Activity API（BE）

路径（**Q1a**）：`GET /api/issues/activity`（与现有 `/api/issues/timeline/export.csv` 同资源族）

查询参数（对齐 E41 CSV 并扩展）：

| 参数 | 含义 |
|------|------|
| `since` | ISO 下界（`created_at`） |
| `until` | ISO 上界（可选） |
| `actionType` | 可重复；`TimelineAction` 枚举子集 |
| `actorId` | 执行者 user id |
| `issueId` | 单 Issue 过滤 |
| `cursor` | 不透明游标（`(created_at, id)` 编码） |
| `limit` | 默认 **50**；硬顶 **200**（页）；与 CSV 的 10000 导出行顶分离 |

响应形状：

```json
{
  "items": [
    {
      "id": "...",
      "issueId": "...",
      "issueCode": "OT-12",
      "issueTitle": "...",
      "actionType": "status_changed",
      "actor": { "id": "...", "username": "...", "displayName": "..." },
      "createdAt": "...",
      "payload": { }
    }
  ],
  "nextCursor": "..." 
}
```

（`nextCursor` 可为 `null`。）

实现要点：

- **只读** `issue_timeline` + Issue 元数据 join；`workspace_id` 强制  
- 复用 / 抽取 E41 `build_timeline_csv` 的过滤逻辑为共享 query helper（CSV 与 JSON 同语义）  
- viewer+ 可读；跨租户 404/空  
- **不**写 timeline、**不** `fire_webhooks` / `fire_automations`  
- 非法 `actionType` → 400；超 limit → **clamp 到 200**（**Q2a**）并文档化

### B · FE（薄 · 非仪表盘抛光）

- 新路由：**顶栏独立** `/activity`（**Q3a**；少扰 Inbox）  
- 无限滚动 / 「加载更多」游标；行：相对时间 · actor · action 文案 · Issue code 可点  
- 过滤条：actionType 多选、since 快捷（24h / 7d）、可选 actor  
- Dashboard `RecentActivity`：**不**改为 timeline 短窗（**Q4a**）；仅加「查看全部活动」链到 `/activity`  
- vitest：action 文案 map；cursor 空态；过滤参数序列化  
- **不做**：反应、评论内嵌、@订阅、推送、富媒体预览、实时 WS

### C · CLI **1.31.0**

- 顶级 `opentask activity list [--since] [--action-type] [--issue] [--limit] [--json]`（**Q5a**）  
- help 示例 1–2 行  
- version → **1.31.0**；pyproject / `__init__` / setup / `opentask_cli.VERSION` 全钉；历史 version 断言同步  
- 既有 `issue timeline` / `timeline-export` 保留

### D · 数据模型摘要

- **无新表 / 无 migration**（**Q6a**；纯读 API + FE + CLI；若日后压测慢再开索引）  
- **不改**：formula emit；SLA 策略模型；webhook 事件集；HMAC

## 2. 安全 / 租户 / 威胁模型

- 一切查询带 `workspace_id`；跨租户不泄漏  
- 页硬顶 200；导出行顶仍走 E41 CSV  
- payload 原样回放 timeline 已存 JSON；**不**执行公式、**不**求值 formula cache 写路径  
- 读路径 spy：无 webhook / automation / timeline append  
- 无进程内 cron / Redis

## 3. 非目标

- Formula 物化 / emit（E40 D2/D7）  
- SLA 营业日历 / 时区矩阵 / 节假日；first-response metric；策略优先级 UI  
- pause timeline 事件（`sla_paused` / `sla_resumed`）— 附录  
- 专用 `issue.cycle_changed` / `estimate_changed` webhook  
- Linear 级 Updates（反应、关注订阅、推送、富媒体）  
- 替换 Dashboard「最近动态」语义（Issue 卡片 ≠ timeline）  
- Redis / 进程内 cron；远程 push / 开 PR / 自开 E48

## 4. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | `GET /api/issues/activity` 返回当前 WS timeline 倒序页；cursor 续页无重叠/无空洞（同插入并发下允许文档化边界） |
| B | `since` / `actionType` / `actorId` / `issueId` 过滤正确；非法 actionType 400；limit>200 clamp |
| C | 跨租户不可见；viewer 可读；非成员 403/404 按现网 workspace 惯例 |
| D | FE `/activity` 可滚加载 + 跳转 Issue；过滤条可用；Dashboard 有「查看全部活动」链；vitest 绿 |
| E | CLI **1.31.0** + `activity list` + version 断言 |
| F | E41 CSV export 回归绿；单 Issue timeline 回归绿 |
| G | spy：activity 读路径 **无** emit / fire_automations / fire_webhooks / timeline 追加 |
| 门禁 | BE 定向+全量记 passed/skip（`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E48 |

## 5. ADR

| ID | 决定 |
|----|------|
| D1 | Epic = **WS Activity Feed v1：JSON 游标 API + 薄 FE + CLI**（方案 A） |
| D2 | 数据源 = 既有 `issue_timeline`；**只读**；与 E41 CSV 过滤语义对齐 |
| D3 | 分页 = cursor `(created_at, id)`；页 limit 默认 50 / 硬顶 200；超顶 **clamp**（Q2a） |
| D4 | API 路径 = `GET /api/issues/activity`（Q1a） |
| D5 | FE = 顶栏 `/activity` 精简列表流；**不做**反应/订阅/推送/富媒体；Dashboard 仅链「全部」（Q3a/Q4a） |
| D6 | CLI = 顶级 `activity list`；版本 **1.31.0**（Q5a） |
| D7 | 无新表 / **无**索引 migration（Q6a） |
| D8 | 守 E40 D2/D7：本 Epic **永不** emit |
| D9 | 非目标见 §3；不 push；不自开 E48 |

## 6. 测试要点

- BE：空 WS → `items=[]`；写入 status/CF/cycle timeline 后 feed 可见  
- BE：actionType / since / actor / issue 过滤；cursor 第二页  
- BE：跨 WS 隔离；limit clamp  
- BE：spy 无副作用  
- FE：文案 map；空态；加载更多；「查看全部」链  
- CLI：1.31.0；`--json` 含 actionType  
- 回归：E41 export；E46 range/sort；E45 SLA pause

## 7. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. 共享 timeline query helper + JSON activity API（TDD）  
3. FE Activity 页 + 路由 + 过滤（TDD vitest）  
4. CLI 1.31.0 + activity list  
5. Dashboard「查看全部活动」链  
6. 门禁 + acceptance tip  

## 8. 开放问题（Yuri 已拍板关闭）

| ID | 问题 | 拍板 |
|----|------|------|
| Q1 | API 路径 | **Q1a** `GET /api/issues/activity` |
| Q2 | `limit` 超硬顶 | **Q2a** clamp 到 200 |
| Q3 | FE 挂载 | **Q3a** 顶栏独立 `/activity` |
| Q4 | Dashboard「最近动态」是否改 timeline 短窗 | **Q4a** **否**；仅加「查看全部活动」链接 |
| Q5 | CLI 命令名 | **Q5a** 顶级 `activity list` |
| Q6 | 是否加 DB 复合索引 migration | **Q6a** **否** |

---

## 附录 · 本轮未选但仍高 ROI（供 E48+ / runners-up）

1. **SLA first-response metric + pause timeline**（`sla_paused`/`sla_resumed`）— **不含**营业日历 / 策略优先级大战；E45 沉淀后再开。  
2. **专用 webhook** `issue.cycle_changed` / `issue.estimate_changed`（+ 可选 `project_changed`）— 薄；订阅方强需求时再拆。  
3. SLA 营业日历 / 时区 / 节假日 / 策略优先级（完整运维面）。  
4. Formula 色阶（连续 color scale）/ 图标集条件格式。  
5. Formula 物化 emit — **明确永不**（除非单独立项重审 E40 D7）。

## CLI 版本

**1.31.0**
