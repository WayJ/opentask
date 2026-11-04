# E52 Design：Activity Feed 加厚 v2 — 关注过滤 · 行内反应 · 薄铃铛 · CLI 1.36.0

日期：2026-11-05（Asia/Shanghai）  
Epic：E52  
基线拟：`sprint/E51-S1` @ `b933852`（全文 `b933852692d1707d2c2583084308d5f43d817dd6`；feature tip `ef82d13`；design 基线 `38bd9c6`）  
worktree：`/workspace/opentask-worktrees/E11-S4` · 拟开分支 `sprint/E52-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E53**。  
**建议入库路径：** `docs/superpowers/specs/2026-11-05-e52-activity-feed-thicken-design.md`  
状态：**Yuri 已拍板（代 Way）** · 入库本文件；大软据此写 plan→TDD，分支 `sprint/E52-S1`。开放问题 Q1–Q6 均按建议默认关闭。

---

## 0. Brainstorming（Yuri 代审上下文）

### 背景

E40–E51 连续闭合 Formula → 审计/outbound → SLA clocks → Formula surfaces → webhook 可靠性 → SLA v2 thin → Formula query surfaces v2 → **WS Activity Feed v1（E47）** → SLA first-response + pause timeline → Formula Display v2 → SLA business hours thin → **专用 webhook pack + 订阅过滤 FE（E51）**。

E51 附录 runners-up（不绑定）：

1. **Activity Feed 加厚**（反应 / 关注订阅 / 推送）— E47 薄 FE 后已隔 **E48–E51 四轮**；产品化缺口仍在  
2. **SLA 节假日/例外日 thin**（仍砍优先级矩阵）— E50 刚交营业时；默认再隔至少一轮  
3. **Webhook 投递可观测加厚**（按钩子成功率仪表 / 死信箱 UI）— 可挂小刀；单列偏薄

代码实证 @ `b933852`：

| 面 | 现状 |
|----|------|
| Activity API | E47 `GET /api/issues/activity`：since/until/actionType/actorId/issueId/cursor；**无** `watching` 过滤 |
| Activity FE | `/activity` 列表 + 过滤条 + 加载更多；**无**「仅关注」；行**无**反应 chips；ActivityNav **无**未读铃铛 |
| IssueWatcher | E18 已有 `issue_watchers` + watch/unwatch API；E19 issue list 已有 `watching=`；**未**接到 Activity |
| Reactions | E27 已有 issue/comment emoji 反应 + timeline `reaction_added/removed`；Activity 行**不**展示摘要、**不**提供快捷反应 |
| Inbox / Notif | E27 prefs（含 `issue_watch_event`）+ E30 邮件；Activity 页与铃铛**未**打通「关注动态未读」 |
| Webhook / SLA / Formula | E51 pack 齐；E50 business hours 齐；E49 Display 齐；**不再**本轮主刀 |
| CLI | **1.35.0**；下一刀 **1.36.0** |

### 方案对比

| 方案 | 做法 | 取舍 |
|------|------|------|
| **A** | **Activity Feed 加厚 v2**：Activity API + FE 接既有 IssueWatcher（`watching` 过滤 +「仅关注」）；行内反应摘要/快捷反应（复用 E27）；ActivityNav **薄铃铛**（关注动态未读游标，非 FCM）；CLI **1.36.0**；守 no-emit | **中厚且连贯**；闭合 E47 明确非目标的产品化缺口；复用已有表，避免新大战；对齐 Linear Updates 的「关注流 + 反应」薄切片 |
| B | SLA 节假日/例外日 thin | E50 次日再开日历面；测试/运维易溢；默认 skip |
| C | Webhook 投递可观测加厚（成功率仪表 / 死信箱 UI） | 有价值但偏运维小刀；撑不起整 Epic 厚度；可并附录或挂后续 |
| D | 完整 Linear Updates（富媒体 + 实时 WS + 浏览器/移动推送） | **单 sprint 必溢** |
| E | Formula emit / 重做 E51 webhook pack | 打破 E40 D7 / 无增量；**永不本轮** |

**拍板：A（Activity Feed 加厚 v2）。**  
节假日 thin、webhook 可观测列入附录供 E53+ / runners-up。

自检：关注过滤、行内反应、薄铃铛边界、CLI **1.36.0**、非目标与 no-emit 已写清；单 sprint 可交付。

### 为何不是其它候选

| 候选 | 为何本轮次之 |
|------|----------------|
| SLA 节假日/例外日 thin | E50 刚交营业时；默认再隔一轮；无强支持台信号 |
| Webhook 投递可观测加厚 | 偏薄运维；E51 刚闭合 pack，宜沉淀 |
| 完整推送/富媒体/实时 WS | 单 sprint 必溢 |
| Formula emit | 打破 E40 D7；永不本轮 |
| 重做 / 扩 E51 webhook 事件包 | 无增量；本轮不碰 |

### Why this Epic now（一句话）

E47 只交付「可读的薄 Feed」；E18/E27/E30 已有关注与反应与通知底座，但 Activity 页仍像审计日志。隔开 E48–E51（SLA/Formula/webhook）四轮后，把 **关注过滤 + 行内反应 + 薄未读铃铛** 捆成中厚 Epic，正好把 Activity 抬到 Linear 对齐的产品面，且不重开节假日或 webhook 运维刀。

---

## 1. 目标

成功标准：工作区成员可在 Activity Feed 中按 **仅我关注的 Issue** 过滤动态；Feed 行可展示既有 issue/comment 反应摘要并支持 **快捷 toggling 反应**（复用 E27 API，不新建反应语义）；ActivityNav 提供 **薄未读铃铛**（基于关注 Issue 的 timeline 游标 / 已读水位，**非**浏览器 Push / FCM）；跨租户隔离；CLI **1.36.0**；**不**引入节假日表 / webhook 仪表盘 / formula emit / 实时 WS / 进程内 cron。

### A · Activity「仅关注」过滤（BE + FE）

- 扩展 `GET /api/issues/activity`：查询参数 `watching: bool`（**Q1**；语义对齐 E19 issue list）  
  - `watching=true` → 仅返回当前用户在本 WS `issue_watchers` 中的 Issue 的 timeline 行  
  - 与既有 since/actionType/actorId/issueId/cursor **可组合**；硬顶 clamp 200 不变  
- FE `/activity`：过滤条增加「仅关注」开关；空态文案区分「无动态」vs「未关注任何 Issue」  
- 无新表；复用 `issue_watchers`  
- vitest：query 序列化含 `watching`

### B · 行内反应（复用 E27）

- Activity item 序列化可选附带 `reactions` 摘要（emoji → count / myReacted；**Q2**）  
  - 数据源：既有 `issue_reactions`（及若 entry 指向 comment 则 `comment_reactions`）  
  - **不**新建 `timeline_entry_reactions` 表（Q2a）  
- FE：行尾 chips；点击调用既有 issue/comment reaction toggle API；乐观更新 + 失败回滚  
- timeline 已有 `reaction_added/removed` 行继续出现在 Feed（过滤仍可用）；本切片不改 timeline 写入语义  
- **不做**富媒体预览、评论内嵌编辑器

### C · 薄铃铛（关注动态未读 · 非推送）

- 已读水位：每用户每 WS 存 Activity 已读游标（**Q3**）  
  - 建议：`user_workspace_prefs` / 小表 `activity_read_cursors(user_id, workspace_id, last_seen_at, last_seen_id)` — **允许 1 个小 migration**（Q3a）  
- `GET /api/issues/activity/unread-count?watching=true`（或挂在现有 me/bootstrap）→ `{ count }`；硬顶（如 99+）  
- ActivityNav：铃铛角标；打开 `/activity`（建议默认 `watching=true`）后标记已读  
- **明确不做**：浏览器 Notification API、FCM/APNs、邮件重发（E30 已有邮件路径）、实时 WebSocket 推送

### D · CLI **1.36.0**

- `activity list` 增加 `--watching` / `--json` 字段对齐新摘要（若有 reactions，json 可选）  
- 可选 `activity unread` 打印未读数  
- 钉 pyproject / `__init__` / setup / `VERSION` / `opentask_cli.VERSION`；历史 version 断言 → **1.36.0**

### E · 安全 / 租户 / no-emit

- 一切查询带 `workspace_id`；跨租户不泄漏 watchers / reactions / unread  
- 读路径（list / unread-count）**不** `fire_webhooks` / `fire_automations` / 不追加 timeline  
- 快捷反应走既有写路径（E27）；本 Epic **不**新增专用 webhook 事件名（E51 已够）  
- formula **no-emit** spy 守住  
- 无 Redis / 进程内 cron

## 2. 非目标

- 节假日 / 例外日 / 国家日历包；SLA policy 优先级矩阵  
- Webhook 成功率仪表 / 死信箱 UI / 历史回放（E51 Q5a 已否）  
- Formula 物化 emit（E40 D2/D7）  
- 浏览器 Push / FCM / 实时 WS / 富媒体预览 / 评论内嵌  
- 新建 timeline-entry 级反应表；重做 E51 事件包  
- 远程 push / 开 PR / 自开 E53

## 3. 验收标准（Acceptance 草图）

| 项 | 标准 |
|----|------|
| A | `watching=true` 仅返回当前用户 watcher 集合内 Issue 的 activity 行；与其它过滤可组合；非法参数 400 |
| B | 未关注任何人时 `watching=true` → `items=[]`；跨租户 watcher 不泄漏 |
| C | Activity item 含反应摘要（若 Q2a）；FE chips toggle 成功并反映在摘要；E27 反应回归绿 |
| D | unread-count 在有新关注动态时 >0；打开 Feed 标记已读后归零；跨租户隔离 |
| E | FE：「仅关注」开关 + 铃铛角标 + vitest；build ok |
| F | CLI **1.36.0** + `--watching`（± `activity unread`）+ version 断言 |
| G | spy：activity **读**路径无 webhook/automation/timeline append；formula no-emit |
| 门禁 | BE 定向（E52+E47+E18/E27 反应相关）+ 全量记 passed/skip（`test_user_search` flake 可记）；CLI 绿；FE vitest+build 绿 |
| 流程 | design/plan/TDD/verify/acceptance；本地 tip；不 push；不自开 E53 |

## 4. ADR（Yuri 已确认）

| ID | 决定 |
|----|------|
| D1 | Epic = **Activity Feed 加厚 v2**（方案 A）：关注过滤 + 行内反应 + 薄铃铛；**无**节假日 / webhook 仪表 / 完整推送 |
| D2 | 关注数据源 = 既有 `issue_watchers`；Activity API 增 `watching`（对齐 E19） |
| D3 | 反应 = 复用 E27 issue/comment reactions；**不**新建 timeline-entry 反应表 |
| D4 | 铃铛 = 已读水位 + unread-count；**非** FCM/浏览器 Push/实时 WS |
| D5 | 允许 **1** 个小 migration 存已读游标（若 Q3a）；否则塞入既有 prefs 行 |
| D6 | CLI = **1.36.0** |
| D7 | 守 E40 D2/D7：本 Epic **永不** formula emit；不扩展 E51 webhook 事件包；非目标见 §2；不 push；不自开 E53 |

## 5. 开放问题（已全部按建议关闭）

| ID | 问题 | 建议默认 |
|----|------|----------|
| Q1 | `watching` 参数名与语义是否对齐 E19？ | **Q1a 对齐**（`watching=true`；布尔） |
| Q2 | 反应摘要挂在 issue 级还是尝试 comment 级？ | **Q2a issue 级为主**；若 activity 行能解析到 `comment_id` 则附 comment 摘要，否则只带 issue 摘要；**不**新建 entry 反应表 |
| Q3 | 已读水位存哪？ | **Q3a 独立小表** `activity_read_cursors`（清晰；单 migration）；备选 Q3b 塞 `notification_preferences` 旁路列 |
| Q4 | 打开 `/activity` 是否默认 `watching=true`？ | **Q4a 否**（默认全量，与 E47 行为兼容）；铃铛点击可带 `?watching=1` |
| Q5 | 是否做浏览器桌面通知？ | **Q5a 不做**（非目标；避免权限/兼容面） |
| Q6 | CLI 是否新增 `activity unread`？ | **Q6a 要**（一行 count；list 已有则加 `--watching`） |

## 6. 切片建议（实现时 plan 用）

1. Docs：plan + acceptance 骨架  
2. BE：`watching` 过滤 + 测试（TDD）  
3. BE：反应摘要序列化 + FE chips（TDD）  
4. BE：已读水位 migration + unread-count + ActivityNav 角标  
5. CLI 1.36.0  
6. 门禁 + acceptance tip  

## 7. 测试要点

- BE：watching 过滤 / 空 watcher / 跨租户；与 actionType+cursor 组合  
- BE：反应摘要正确；toggle 后摘要变化；E27 回归  
- BE：unread-count / mark-read；读路径 no-emit spy  
- FE：开关、chips、角标、query 序列化 vitest  
- CLI 1.36.0 pins + `--watching` + `unread`

---

## 附录 · runners-up（供 E53+；若 Yuri 改选可替换本草案）

1. **SLA 节假日/例外日 thin**（仍砍优先级矩阵）— 仅当支持台强需求；E50 刚交，默认再隔至少一轮。  
2. **Webhook 投递可观测加厚**（按钩子成功率仪表 / 死信箱 UI）— E51 沉淀后再开；可作薄运维刀。  
3. **Activity 实时/推送加厚**（WebSocket 扇出 / 浏览器 Notification）— 本轮刻意砍；本草案铃铛落地后再评估。

（Formula emit — 永不本轮。重做 E51 webhook pack — 无增量，不推。）

## CLI 版本

**1.36.0**
