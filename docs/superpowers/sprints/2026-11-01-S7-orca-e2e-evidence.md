# S7 Orca Jira 集成 E2E 证据（D4 必做项）

- 日期：2026-10-31
- 环境：Windows 11 · Orca 1.4.245（桌面运行中，runtimeId `cc454a0a`）·
  OpenTask backend `uvicorn opentask.main:app --port=8000`（APP_ENV=development，
  AUTH_SECRET_KEY=e2e-s7-dev-secret）· Docker opentask-pg（开发库 `opentask`）
- 探测依据：`2026-11-01-S7-orca-jira-probe.md`（下称"探测报告"）
- 结论：**五操作（列出/读取/创建/更新/状态流转）全部经真实 Orca CLI 打通**，
  psql 核验字段/标签/评论/时间线全部落库。

## 0. 连接建立（探测报告 §6 的路径）

站点注册无法手写配置文件（token 在加密 vault），GUI 聚焦受 Windows 前台锁限制；
改走 CLI 同源的本机运行时 RPC（named pipe `\\.\pipe\orca-13268-*` + NDJSON 帧
`{id, authToken, method, params}`，协议还原自 Orca `out/cli/runtime/transport.js`），
等价于 Settings UI 的 `jira:connect` IPC：

```
RPC jira.connect {siteUrl: "http://localhost:8000", email: "", authType: "server",
                  apiToken: "vk_b548…c6505"}   # vk_ 为 OpenTask 契约 API Key
→ {"ok": true, "viewer": {"accountId": "s7_e2e_user", "displayName": "S7E2E用户"}}
```

连接即调 `GET /rest/api/2/myself` 验证（探测报告 §1）——首次真实调用即通过。
API Key 为开发库中 `s7_e2e_user` 用户签发的 access token（服务层签发，非测试桩）。

```
$ orca jira connection --json
"connected": true,
"sites": [{ "id": "--fXTENM5ZzrDjQR91xpKlFE", "siteUrl": "http://localhost:8000",
            "email": "", "displayName": "S7E2E用户", "authType": "server" }]
```

## 1. 五操作转录（真实 `orca jira` CLI，全部 `"ok": true`）

### ① 列出 `orca jira list --filter assigned --limit 5`

```
（连接后首次，库里无分配给当前用户的任务）→ result: []
（创建+分配后复跑）→
  "key": "OPENTASK-2026000000001",
  "title": "S7 E2E：经 Orca Jira 集成创建",
  "status": { "id": "in_progress", "name": "In Progress",
              "categoryKey": "indeterminate", "categoryName": "In Progress" }
```

JQL 搜索同通：

```
$ orca jira search "summary ~ \"Orca Jira\" AND statusCategory != Done ORDER BY updated DESC"
→ "key": "OPENTASK-2026000000001"（summary ~/statusCategory/ORDER BY 翻译均命中）
```

### ② 创建 `orca jira create --project OPENTASK --type bug --title … --body …`

```
→ { "ok": true, "id": "ae35f225-6b84-4feb-b494-8630bc38c4ce",
    "key": "OPENTASK-2026000000001",
    "url": "http://localhost:8000/browse/OPENTASK-2026000000001" }
```

key 编码：`ISSUE2026-1 → OPENTASK-2026000000001`（年*10^9+序号，探测报告 §5.7）。
前置 `project types` / `project fields`（createmeta 端点）均正常返回。

### ③ 读取 `orca jira issue OPENTASK-2026000000001`

```
→ title/description 原文返回；project {key: OPENTASK}；issueType {id: bug, name: Bug}；
  status {id: todo→后变 in_progress, categoryKey…}；reporter/priority 时间戳齐全；
  createdAt "2026-10-31T13:49:08.000+0000"（Jira 时间戳格式）
```

### ④ 更新（三个写端点）

```
$ orca jira priority set OPENTASK-…0001 --to-id high      → ok（PUT /issue/{key} fields.priority）
$ orca jira label add    OPENTASK-…0001 --label s7-e2e --label jira-wire → ok（update.labels add）
$ orca jira assignee set OPENTASK-…0001 --to-id 13cfa341-… → ok（PUT /issue/{key}/assignee）
回读：priority {id: high}；labels [jira-wire, s7-e2e]；assignee.accountId = 用户 ID
```

### ⑤ 状态流转

```
$ orca jira status list OPENTASK-…0001
→ transitions: cancelled/done/in_progress/in_review/todo（不含当前状态；
   name=token、to.name=展示名、to.statusCategory 正确，探测报告 §3）
$ orca jira status set OPENTASK-…0001 --to in_progress     → ok（204）
回读：status.name "In Progress"、categoryKey indeterminate
```

附：评论写入 `orca jira comment add … --body "S7 E2E 证据评论…"` → ok，`comment list` 可读回。

## 2. psql 落库核验（开发库 opentask）

```
issues:      ISSUE2026-1 | S7 E2E：经 Orca Jira 集成创建 | in_progress | high | assignee 13cfa341-…
issue_tags:  jira-wire, s7-e2e
issue_comments: "S7 E2E 证据评论：状态流转与字段更新已验证"
issue_timeline（7 条，既有 service 路径全部生效）:
  created          {title, type: bug, issue_code: ISSUE2026-1}
  priority_changed {from: medium, to: high}
  label_added      {label: jira-wire} / {label: s7-e2e}
  assigned         {to: {id: 13cfa341-…, name: S7E2E用户}}
  status_changed   {from: open, to: in_progress}
  commented        {comment_id, parent_id}
```

## 3. 复核/复跑手册

1. 起后端：`cd backend && AUTH_SECRET_KEY=<key> APP_ENV=development uv run uvicorn opentask.main:app --port=8000`
2. 站点已在用户 Orca 注册（site id `--fXTENM5ZzrDjQR91xpKlFE`，指向
   `http://localhost:8000`，server 模式 PAT=vk_ 契约 API Key）；如需重配：
   Orca Settings → Jira → 移除后按探测报告 §6 重连，或经运行时 RPC `jira.connect`
3. 复跑：`orca jira list --filter assigned` / `issue OPENTASK-2026000000001` /
   `search "<JQL>"` 等（key 形状 `OPENTASK-2026%09d` 段）
4. 遗留状态说明：E2E 数据（ISSUE2026-1 与其标签/评论/时间线）留在开发库作证据；
   E2E 用 API Key（`vk_b548…`，名 s7-e2e-jira）与用户 `s7_e2e_user` 同留；
   后端 8000 端口实例在任务终端后台运行，协调者验收后可停（或直接 kill）。
