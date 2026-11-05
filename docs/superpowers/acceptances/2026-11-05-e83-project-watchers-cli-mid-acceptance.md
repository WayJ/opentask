# E83 Acceptance：Project Watchers CLI mid · CLI 1.67.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E83-S1`  
基线：`dd3e920`（全文 `dd3e920ec92ba93e6c841199cc22d8a913ca8c95`；含 E83 design；E82 tip `bcd8f88` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e83-project-watchers-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e83-project-watchers-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | Q3a enrich；既有三端点；跨租户/缺项目 404 |
| B FE | ⏳ | 零产品 FE；build + f+r |
| C CLI 1.67.0 | ⏳ | `project watch\|unwatch\|watchers` + show `watching_count` + api_client + pins |
| D 安全/邻面/no-emit | ⏳ | 未改 E82/E81/E80/E79；无新表/webhook；formula no-emit |
| E 门禁 | ⏳ | 见下 |

## Tip

- 分支：`sprint/E83-S1`
- tip short：_pending_
- tip full：_pending_
- **未 push / 未开 PR / 未开 E84**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E83 BE | _pending_ |
| Full BE `pytest tests` | _pending_ |
| CLI suite | _pending_ |
| FE vitest / build | _pending_ |
| VERSION | _pending_ → **1.67.0** |

## Q1a–Q6a 落地

- Q1a 复用既有三端点（无新路由）
- Q2a 扁平 `project watch\|unwatch\|watchers`
- Q3a list/watch enrich username/name
- Q4a `project show` → `watching_count`（失败降级）
- Q5a pins **1.67.0**
- Q6a 零产品 FE

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E84
