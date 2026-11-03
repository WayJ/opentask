# Epic 收口笔记 — 2026-11-03（E1 / E2 关闭 + 全树台账对账）

## background

触发：用户问「现在还有什么没完成」。盘点结论是**功能面已全部交付完，欠的是收口**：

- 7 个 sprint 文档 frontmatter 全停在 `merged`，从未走到 `closed`
- E1 / E2 两个 epic `status: open`，DoD 复选框一行未勾
- E2 stub 的 S5 / S7 仍写 `ready`（物化时漏翻），与 sprint 文档的 merged 事实矛盾
- TD5 实际已清偿（openapi 重生成），追踪器里仍列未关闭
- OAuth2 实施计划 31 个复选框全空，尽管实现与真栈验收均已完成
- E1 的三个开放问题（nginx 前缀 / .venv 重建 / 外部域名）悬空

本次动作：supervibe `close` 状态推进 + 逐条核对 DoD + 技术债销账与登记 + 文档口径回填。**不改动任何运行时行为**，全部为文档与台账变更（epic 状态翻转为元数据变更）。

## 门禁复跑（2026-11-03，均在本次会话实测）

| 门禁 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `cd backend && uv run pytest tests/ -q` | **571 passed / 27 skipped / 0 failed**（100.64s） |
| 前端 lint | `npx eslint .` | 0 errors（272 warnings 为仓内存量，新增文件 0 告警） |
| 前端 build | `npx vite build --mode prod` | Build successful |
| CLI | `uv run opentask --version` | `opentask v1.0.6` |
| 导入图（后端） | AST 静态扫描 `backend/opentask` | missing = 0 |
| 导入图（CLI） | AST 静态扫描 `agent-harness/opentask-cli` | missing = 0 |
| 凭据卫生 | `git ls-files` + 高危密钥模式扫描 | 三个真实凭据文件未跟踪；AKIA / ghp_ / 私钥 / JWT 全仓零命中 |
| 品牌残留 | `grep -rIl "vibeking\|VIBE_KING\|Vibe King\|vibe-king"` | 代码与 `backend/openapi*.json` 零命中；残留仅在 `docs/`、`.agents/notes/` 的历史叙述文本 |

**踩坑记录**：首次复跑后端是 **205 passed / 368 errors**（全是 `OSError`），根因不是代码——本机 `opentask-postgres` 容器停在 `Created` 态且未映射端口，DB 连不上。起 `opentask-pg-test`（postgres:15-alpine，`-p 5432:5432`，user/pw=opentask）并 `CREATE DATABASE opentask_test` 后即全绿。**下次跑门禁前先确认 PG 在跑**。

## decisions

1. **7 个 sprint 文档 `merged → closed`**：`close` 的属主是 roadmap skill，前置条件 `state == merged` 全部满足。stub 行状态不在本 skill 权限内，保持 `started`，权威状态在 sprint 文档 frontmatter；stub note 追加 closed 指针（merged-commit 哈希）以便反查。
2. **E2 stub 的 S5 / S7 由 `ready` 更正为 `started`**：这两行在物化时漏翻，与 sprint 文档事实矛盾。此处只做**事实性投影**（不是重新物化、不是 start 的权限动作），并在 note 行内写明更正原因。
3. **E1 Q2（`.venv` / IDE 索引是否需重建）判定「无需重建」并关闭**：`.venv` 由 uv 按 `pyproject.toml` 管理、`opentask` 包为 editable 安装，改名后 `uv run pytest` 全绿即证明环境自愈；IDE 索引属开发者本地事项（清一次缓存即可），不在仓库控制范围。
4. **E1 Q1（nginx 前缀）/ Q3（外部域名）降级为 deferred**：两者都在本仓库控制范围之外——Q1 移交运维 checklist，Q3 移交用户确认。以 deferred 而非 open 收口，不阻塞 epic 关闭。
5. **E2 DoD 1 口径修订**：依据既有 ADR D13，本机 Orca 构建没有「自定义任务源」注册面，唯一可真实验证的路径是 Jira 线格式（S7 已实证五操作走通）。因此修订 DoD 1 文案并标注修订来源，而不是让一条已知的假命题挂在未勾状态。
6. **技术债**：TD5 销账（证据 commit 3f62970 + 2026-11-03 复扫）；TD3 补 owner=WayJ；**新增 TD6/TD7/TD8**（见下）。
7. **OAuth2 计划 31 个复选框全部回填**，并逐条标注 3 处与原计划的偏离：T0.1 分支改名**不适用**（7 个 commit 直落 main，未保留独立分支）；T5.2 同意页实际落在 `frontend/src/views/oauth2/index.vue` 而非计划中的 `consent.vue`；T7 计划的三段式 commit 实际细化为 7 个 commit（含 3 次修复提交）。
8. **DoD 勾选标准**：每条都绑定可复跑的证据（测试名 / 文件路径 / commit 哈希 / 命令输出），不接受「已实现」这类无锚点的打勾。

## 新增技术债

| id | 摘要 | 为什么不是文档问题 |
|---|---|---|
| TD6 | OAuth2「email 自动匹配/建号」未接线：`OAuthIdentityService.resolve_or_create` 已实现但授权流程未调用（`/oauth2/token` 走 `find_by_id(record.user_id)`）；前端用户名正则不允许 `@`，与「email 作 username 种子」冲突 | **功能性缺口**：dsh-saas 侧成员若没有 OpenTask 账号，走不完同意流程。设计文档 §280 已记为「待裁定技术债」但追踪器里没有对应条目——本次补登 |
| TD7 | `backend/openapi*.json` 未包含 `/oauth2/*`（171 路径中 0 条 oauth2） | 生成的 spec 与实现不一致，OAuth2 交付后未重新生成 |
| TD8 | Jira 线格式兼容层（`/rest/api/2/*`）的调用面契约无仓库内长期落点（ASGI catch-all，FastAPI 不建模，唯一权威是 sprint 探测文档） | sprint 台账不是契约的稳定落点，易随归档失联 |

## handover

- **运维**：nginx `location /vibeking/` → `/opentask/`（E1 Q1，仓库内无 nginx 配置，上线前必须核对，否则前端请求 404）
- **用户**：TD6 的产品口径裁定——① 授权流程接入 `resolve_or_create`（需同时裁定 username 落库口径）② 明确「成员须先有 OpenTask 账号」并同步 dsh-saas 引导文案；以及 Q3 外部域名归属
- **WayJ**：TD3（根目录 Dockerfile 重写或删除）、TD7（openapi 重生成）、TD8（Jira 线格式契约固化到 `backend/docs/`）

## lessons

- 台账滞后于 git 是常态：**先扫目录树，再信 frontmatter**。本次四处状态不一致（stub `ready` vs 文档 `merged`、TD5 已偿未销、DoD 全空、计划复选框全空）都是「只做不记账」的结果。
- epic 关闭不等于债务归零：E1/E2 关掉的只是**验收口径内的交付**，TD6 这类功能性缺口必须显式转成可追踪条目，否则会随 epic 一起「消失」。
- 门禁绿的前提是环境在位：DB 容器没起时 pytest 报的是 `OSError`，看着像代码坏了，实际是环境问题——先排环境再动代码。
