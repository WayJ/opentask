# E96 Acceptance：Access Token CLI mid · CLI 1.80.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E96-S1`  
基线：`0f8b28f`（全文 `0f8b28f1a7f0afcce59bd4a5cd399f525f0180f1`；含 E96 design；E95 tip `2809068` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e96-access-token-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e96-access-token-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | Q1a 无新路由；复用既有三端点；邻面 spy |
| B FE | ⏳ | 零产品 FE；vitest + build；f+r |
| C CLI 1.80.0 | ⏳ | access-token list\|create\|revoke(+rm)；三 helpers；--save opt-in |
| D 安全/邻面/no-emit | ⏳ | fake token only；默认不写 config；未改邻面 |
| E 门禁 | ⏳ | 见下 |

## Tip

- 分支：`sprint/E96-S1`
- tip short：_pending_
- tip full：_pending_
- **未 push / 未开 PR / 未开 E97**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E96 BE | _pending_ |
| Full BE `pytest tests` | _pending_ |
| CLI suite | _pending_ |
| FE vitest | _pending_ |
| FE production build | _pending_ |
| VERSION | _pending_ |

## Q1a–Q6a 落地

- Q1a _pending_
- Q2a _pending_
- Q3a _pending_
- Q4a _pending_
- Q5a _pending_
- Q6a _pending_

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = _pending_`

## 安全确认

_pending_

## 禁区

_pending_

## 未做 / flake

_pending_
