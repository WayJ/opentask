# E76 Acceptance：Issue 外链 mid — issue_links · CLI 1.60.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E76-S1`  
基线：`83273b4`（全文 `83273b451265c876d3e53253d8ec334f6252dbd3`；含 E76 design；E75 tip `6de4382` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e76-issue-external-links-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e76-issue-external-links-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | `issue_links` alembic；CRUD；≤50；http(s)；timeline add/remove；跨 WS 404；viewer 写 403 |
| B FE | ⏳ | 详情「链接」区；hostname helper；vitest+build；`f`+`r` |
| C CLI 1.60.0 | ⏳ | `issue link list\|add\|rm`；全钉 1.60.0（含 VERSION 文件） |
| D 安全/邻面/no-emit | ⏳ | ≠附件/VCS/relations；formula no-emit；无新 webhook 名；不改 E63–E75 主表面 |
| E 门禁 | ⏳ | 待填 |

## ADR

D1–D6 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：_pending_
- BE 定向 E76：_pending_
- CLI：_pending_
- FE vitest + build：_pending_

## Tip

- 分支：`sprint/E76-S1`
- tip：_pending_
- **未 push / 未开 PR / 未开 E77**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E77
