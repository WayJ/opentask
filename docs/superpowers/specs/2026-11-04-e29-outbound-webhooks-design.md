# E29 设计：Outbound Webhooks（Integrations lite）

日期：2026-11-04（Asia/Shanghai）  
Epic：E29  
基线：`sprint/E28-S1` @ `64c5371`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E29-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E30**。

## 1. 目标

在 Automations（E26）之上补 **工作区出站 Webhook**：订阅事件 → HMAC 签名 POST 到用户 URL。

### A · 模型 + CRUD
- `workspace_webhooks`：url、secret（创建时生成、响应只回一次）、events[]、enabled、created_by；可选 name（列表可读）
- `webhook_delivery_logs`：最近投递记录（成功/失败、status、latency、error）
- `GET/POST /api/webhooks`；`GET/PATCH/DELETE /api/webhooks/{id}`；`POST /api/webhooks/{id}/test`
- 权限：写 = **owner**（WS 无独立 admin）；读 = **owner|member**（viewer 403）；强制 `X-Workspace-Id`；跨租户 403/404

### B · 投递
- 事件：`issue.created` / `issue.updated` / `issue.status_changed` / `comment.created`
- 复用 issue 写路径 after-commit 钩子（与 realtime / automations 并列）
- POST JSON + `X-OpenTask-Signature: sha256=<hex>`（HMAC-SHA256(body, secret)）+ `X-OpenTask-Event`
- 超时短（默认 5s）；失败写 delivery log；轻量重试：即时 1 次 + 失败后再 1 次短延迟（~0.3s）；不做队列/cron

### C · FE
- `/settings/webhooks`：列表、创建（展示一次性 secret）、启停、删、Test；事件多选

### D · CLI **1.13.0**
- `webhook list|create|update|delete|test`

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 路径 `/api/webhooks`（复数）；与既有 `/api/webhook`（知识库入站）及 `/api/webhooks/github` 不冲突 |
| D2 | WS 角色无 admin；**写=owner**；**读=owner\|member**；viewer 全 403 |
| D3 | secret = `secrets.token_urlsafe(32)`；仅 `POST` 创建响应含 `secret`；此后 GET/list 仅 `secretHint`（末 4 位） |
| D4 | events 存 JSON 数组；须为允许枚举非空子集；空数组拒绝 |
| D5 | 投递 body：`{id,type,createdAt,workspaceId,data}`；`data` 为事件摘要（issue id/code/status/changed 等），不塞跨租户字段 |
| D6 | Signature：`hmac.new(secret, body_bytes, sha256).hexdigest()`，头 `X-OpenTask-Signature: sha256=<hex>` |
| D7 | 重试：attempt0 立即；失败则 `asyncio.sleep(0.3)` 再 attempt1；两次都记 log；保留每 hook 最近 **50** 条 |
| D8 | `fire_webhooks` best-effort：异常只打 log，不回滚主写；与 `fire_automations` / realtime 并列挂点 |
| D9 | `issue.status_changed` 时额外再发 `issue.updated`（若 hook 订阅了 updated）— 与 Linear「字段变更也算 updated」对齐 |
| D10 | Test 事件 type=`webhook.test`，**不要求** events 订阅（强制投递）；亦记 delivery log |
| D11 | FE：`/settings/webhooks`；创建成功 Modal 展示 secret（仅一次） |
| D12 | CLI 1.13.0；`webhook create --url --events issue.created,issue.updated` |
| D13 | 非目标：Slack OAuth、邮件、Zapier、入站新通道、队列/cron、远程 push；不自开 E30 |

## 3. 非目标

Slack OAuth、邮件、Zapier 专用、入站 webhook 新通道、多步流水线/cron、远程 push、E30。

## 4. 验收摘要

- CRUD + 权限 + 租户；投递签名/重试/log；FE 设置页；CLI 1.13.0
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**
