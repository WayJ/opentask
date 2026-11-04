# E11 VCS HTTP 契约（FE = CLI = Agent）

日期：2026-11-04  
Epic：E11  
范围：分支名、PR 关联、可选状态钩子。**禁止**私有 RPC / 直写 DB；CodingWorker 与 opentask-cli 只走下列 HTTP。

## 鉴权

| 调用方 | 头 |
|---|---|
| FE / CLI / Agent | `Authorization: Bearer <token>` + `X-Workspace-Id: <ws>` |
| GitHub webhook | 无 JWT；可选 `X-Hub-Signature-256`（`WEBHOOK_GITHUB_SECRET` 空则跳过验签，仅 local/dev） |

Body / 响应字段：**camelCase**（与既有 Issue API 一致）。

## 端点

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/issues/{id}/vcs/branch-name` | 建议分支名 `{issue_code}-{slug}` |
| GET | `/api/issues/{id}/vcs/links` | 列表 `{ rows, total }` |
| POST | `/api/issues/{id}/vcs/links` | 创建；`kind`: `branch` \| `pull_request` |
| PATCH | `/api/issues/{id}/vcs/links/{linkId}` | 更新 status / prUrl / title… |
| DELETE | `/api/issues/{id}/vcs/links/{linkId}` | 解除关联 |
| POST | `/api/webhooks/github/pull-request` | fixture-friendly GitHub PR event 子集 |
| PATCH | `/api/workspaces/{id}` | `gitStatusHooksEnabled`（默认 `false`）等 |

### POST links body（PR）

```json
{
  "kind": "pull_request",
  "prUrl": "https://github.com/org/repo/pull/12",
  "provider": "github",
  "status": "open",
  "title": "optional"
}
```

### Webhook 行为

1. Upsert `issue_vcs_links`（match `head.ref` → issue_code，否则 `pr_url` / `external_id`）
2. 若 Workspace `gitStatusHooksEnabled`：
   - PR `open`/`draft` 且 Issue 当前为 `open` → `gitHookOnPrOpen`（默认 `in_progress`）
   - PR `merged` 且 Issue 非 `closed`/`rejected` → `gitHookOnPrMerged`（默认 `resolved`）
   - PR `closed` 未合并 → **不**改 Issue

## CLI 对照

| CLI | HTTP |
|---|---|
| `opentask issue branch-name CODE` | GET `.../vcs/branch-name` |
| `opentask issue link-branch CODE NAME` | POST links `kind=branch` |
| `opentask issue link-pr CODE URL` | POST links `kind=pull_request` |
| `opentask issue vcs-links CODE` | GET links |

## Agent / CodingWorker

见仓库根 `CodingWorker.md` §「Git / PR（E11）」——与上表同一路径；勿另起 schema。
