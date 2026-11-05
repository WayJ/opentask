# E80 Acceptance：Issue project-move integrity mid · CLI 1.64.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E80-S1`  
基线：`171ae4f`（全文 `171ae4ff5e31ee8336da2e22ed146060f4ccbc6a`；含 E80 design；E79 tip `d84f6e4` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e80-issue-project-move-integrity-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e80-issue-project-move-integrity-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | helper + update/duplicate + timeline action_data |
| B FE | ⏳ | nextMilestoneAfterProjectMove + saveProject |
| C CLI 1.64.0 | ⏳ | `--project` / `--milestone` / `--clear-milestone` + pins |
| D 安全/邻面/no-emit | ⏳ | 不清 cycle；无新 webhook；不重开 E63–E79 |
| E 门禁 | ⏳ | 见下 |

## Tip

- 分支：`sprint/E80-S1`
- tip short：_TBD_
- tip full：_TBD_
- **未 push / 未开 PR / 未开 E81**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E80 BE | _TBD_ |
| Full BE `pytest tests` | _TBD_ |
| CLI suite | _TBD_ |
| FE vitest | _TBD_ |
| FE production build | _TBD_ |
| VERSION | _TBD_ |

## Q1a–Q6a 落地

- Q1a 值变即清 milestone（除非 Q2a）
- Q2a 显式合法 milestone 保留；非法 400
- Q3a duplicate 跨项目不抄
- Q4a 读不改库
- Q5a 扩 `project_changed.action_data`；无新 enum/webhook
- Q6a CLI + pins 1.64.0

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok` — pending verify

**STOP** — 未 push / 未开 PR / 未开 E81
