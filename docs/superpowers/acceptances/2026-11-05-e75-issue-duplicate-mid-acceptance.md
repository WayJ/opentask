# E75 Acceptance：Issue 复制 mid — duplicate · CLI 1.59.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E75-S1`  
基线：`78e12bb`（全文 `78e12bb29300a6e0cd9a84db3e2befd69beb9702`；含 E75 design；E74 tip `98d5bf4` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e75-issue-duplicate-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e75-issue-duplicate-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | `POST /api/issues/{id}/duplicate`；白名单；status=open；Q4a relates_to；无 alembic；timeline `duplicated_from` |
| B FE | ⏳ | 详情「复制 Issue」+ 跳转；`buildDuplicateTitle` vitest；build；`f`+`r` |
| C CLI 1.59.0 | ⏳ | `issue duplicate`；全钉 1.59.0（含 VERSION 文件） |
| D 安全/邻面/no-emit | ⏳ | 跨 WS 404；viewer 403；formula skip；无新 webhook 名；不改 E63–E74 主表面 |
| E 门禁 | ⏳ | 待 verify |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

（verify 后填写）

## Tip

（verify 后填写）

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E76
