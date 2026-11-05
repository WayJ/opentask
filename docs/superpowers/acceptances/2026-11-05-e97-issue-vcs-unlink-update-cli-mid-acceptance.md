# E97 Acceptance：Issue VCS unlink + update CLI mid · CLI 1.81.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E97-S1`  
基线：`0f6248c`（全文 `0f6248cb3ae695e6ab8ed5ebe0ea8429b53d4743`；含 E97 design；E96 tip `d864818` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⬜ | Q1a 无新路由；复用 DELETE/PATCH；邻面 spy |
| B FE | ⬜ | 零产品 FE；vitest + build；f+r |
| C CLI 1.81.0 | ⬜ | unlink-vcs(+vcs-unlink) / update-vcs；update helper；pins |
| D 安全/邻面/no-emit | ⬜ | 未改邻面；无新表/路由/webhook；formula no-emit |
| E 门禁 | ⬜ | 见下 |

## Tip

- 分支：`sprint/E97-S1`
- tip short：_TBD_
- tip full：_TBD_
- **未 push / 未开 PR / 未开 E98**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E97 BE | _TBD_ |
| Directed E97 CLI | _TBD_ |
| Full BE `pytest tests` | _TBD_ |
| CLI suite | _TBD_ |
| FE vitest | _TBD_ |
| FE production build | _TBD_ |
| VERSION | _TBD_ |

## Q1a–Q6a 落地

- Q1a …
- Q2a …
- Q3a …
- Q4a …
- Q5a …
- Q6a …

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = pending`

## 禁区

未触碰：…（填满）

## 未做 / flake

- 未做：…
- flake：…
