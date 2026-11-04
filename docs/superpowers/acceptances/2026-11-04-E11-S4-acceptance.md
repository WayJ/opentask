# E11-S4 Acceptance — 浏览器冒烟 P0 热修 + UX 收紧

**Verdict:** **pass**

**Date:** 2026-11-04（Asia/Shanghai）  
**Worktree:** `/workspace/opentask-worktrees/E11-S4` · `sprint/E11-S4`  
**Baseline:** `sprint/E11-S3` @ `4b27f4ff205361d38b40d3c147fe56d5f07a43aa`  
**Tip (this acceptance):** `sprint/E11-S4` — 以本分支 `git rev-parse HEAD` 为准（回执时写入）  
**Plan:** `docs/superpowers/plans/2026-11-04-E11-S4-plan.md`  
**Design:** `docs/superpowers/specs/2026-11-04-e11-s4-smoke-p0-hotfix-design.md`  
**Push:** **未推远程**（Yuri 待 Way 授权）

## P0 根因与修复

| # | 现象 | 根因 | 修复 |
|---|---|---|---|
| 1 | Issue 详情 attachments 500 | live DB 无 `documents` 表（Alembic 从未建；pytest 靠 create_all） | Alembic `4b27f4ff205361d38b40d3c147fe56d5f07a43aa`；端点防御空列表；FE GET attachments 失败静默 |
| 2 | Profile「查看者」vs Members owner | 注册 `User.role=viewer`，WS member=owner；/me 只回平台 role | 注册 → `developer` + UserRole；`/me`+`getUserInfo` 下发 `workspaceRole`；Profile 优先展示工作区角色 |
| 3 | 改 Issue Key 后序号不重置 | E12 设计「counter 单调」 | 改 key 时 `issue_counter=0` → 下一单 `NEW-1`；创建可显式 `issueKey` |
| 4 | `/home` Soybean 假数据 | 模板首页未替换 | Home 换成工作区 Issue/Inbox/Cycle 摘要；默认路由保持 `issue_list` |

## P1 / UX（同 sprint）

- 看板优先级中文标签（`getIssuePriorityLabel`）
- 属性栏标签 `white-space: nowrap`（避免「负责/人」）
- `route.workspace` / `page.profile.pwd.*` i18n 补齐；Profile 改用 `profile.pwd.*`
- 创建工作区可填 Issue Key；Cycles 文案「更改后下一单从 1」
- `work-management` 导航 `hideInMenu`（空白工作反馈/周视图/工作安排降级）
- **未做（本轮跳过）：** @mention/Inbox 人选、详情 URL KEY-N、Cycle 名称输入、负责人下拉空、Initiative 列表、报告人 admin/-

## Gates

| Gate | Result |
|---|---|
| `cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -q` | **812 passed, 24 skipped, 0 failed** |
| attachments / owner / issue_key 新用例 | 全绿 |
| live smoke `GET …/attachments`（表迁上后） | **200 + []** |
| eslint（touched FE） | 见 commit 后命令输出 |
| `git push` | **未执行** |

## UX 页面改动要点

| 页面 | 改动 |
|---|---|
| Home | 去掉假流量/$/soybean 新闻 → 工作区摘要卡片 + 快捷入口 |
| Issue 看板 | 优先级显示「高」等中文，不再 raw `high` |
| Issue 详情右栏 | 标签不换行；附件 500 不再全局 toast |
| Profile | 工作区·所有者 / 平台·开发者；改密 i18n |
| Workspace 切换器 | 创建可填 Issue Key |
| Cycles 设置 | 改 key 行为文案 |
| 侧栏 | 工作管理整组隐藏 |

## Gaps / residual

- 未重启 E11-S3 前端进程加载本 worktree 代码（DB 表已在共享 PG 建好，附件 500 对旧后端亦已消失）
- 全量 `pnpm run build` 跨 worktree unocss 环境可能仍 flake（不阻塞）
- 若干 P1 功能项未做
- **无 push**
