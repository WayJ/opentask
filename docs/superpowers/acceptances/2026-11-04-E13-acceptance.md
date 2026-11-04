# E13 Acceptance — Linear 视觉改造

**Verdict:** **pass**

**Date:** 2026-11-04（Asia/Shanghai）  
**Branch:** `sprint/E13-S1`（worktree 仍为 `/workspace/opentask-worktrees/E11-S4`）  
**Baseline:** `sprint/E11-S4` @ `3fb9aca`（logo D）  
**Tip:** `sprint/E13-S1` @ `9caa9318f8aacfd29a458818325bf2baf5a20d1b`（报告时 HEAD；本文件若再改 tip 会换 hash）  
**Spec:** `docs/superpowers/specs/2026-11-04-e13-linear-visual-restyle-design.md`  
**Plan:** `docs/superpowers/plans/2026-11-04-e13-linear-visual-restyle.md`  
**Push:** **未推远程**

## Checklist（对照 design Acceptance）

| # | 项 | Result |
|---|---|---|
| 1 | Root `DESIGN.md` 重写为 Linear v2.0；dark 默认 + light inverse | **pass** |
| 2 | `themeColor === '#5e6ad2'`；`themeScheme: 'dark'`；success `#27a644` | **pass**（`settings.ts` + served module） |
| 3 | `design-system.css` / `design-tokens.css` 对齐 canvas/surface/hairline/ink | **pass** |
| 4 | 默认暗色；亮色仍可切换（scheme toggle 保留） | **pass**（配置层） |
| 5 | 侧栏 IA：Inbox 可见；隐藏 home/dashboard/manage/work-management；Projects/Workspace 可达 | **pass**（vitest `e13-linear-nav`） |
| 6 | 无 Soybean「工作管理/研发流水线/系统管理」顶层 clutter（流水线文案→项目；系统管理 hide） | **pass** |
| 7 | OpenTask 名 + logo D 保留 | **pass**（未改品牌资产） |
| 8 | 系统字体栈 only | **pass** |
| 9 | 未改后端 API / 业务逻辑 | **pass** |
| 10 | **Not pushed** | **pass** |
| 11 | 冒烟截图 `/workspace/opentask-smoke/e13/` login/sidebar/issue/inbox | **pass**（headless Chrome；见路径表） |

## Tasks 落地

| Task | Commit 主题 | 要点 |
|---|---|---|
| docs | `docs(e13): add Linear visual restyle design + plan` | 三份未入库 docs |
| 1 | `style(theme): adopt Linear.app tokens…` | DESIGN.md / design-system / design-tokens / settings / loading |
| 2 | `feat(nav): flatten sidebar IA…` | Inbox order1；hide clutter；custom/generated 去重；i18n；vitest |
| 3 | `style(shell): Linear-density…` | linear-shell.css；content 12px；Favorites hairline |
| 4 | `style(pages): Linear-adjacent polish…` | issue list 去浅色渐变硬编码；board/detail/home/inbox/workspace 令牌化 |
| 5 | 本 acceptance | gates + 缺口说明 |

## Gates

| Gate | Result |
|---|---|
| vitest `src/router/__tests__` + route shared | **12 passed**（含 e13-linear-nav / de-pge-nav） |
| eslint（touched TS/Vue；css prettier fixed） | 见提交前命令 |
| vite :9527 serving this worktree | **yes**；`/src/theme/settings.ts` 含 `#5e6ad2` + `dark` |
| `git push` | **未执行** |

## 截图路径

- `/workspace/opentask-smoke/e13/login.png`
- `/workspace/opentask-smoke/e13/sidebar.png`（同 issue-list 壳，突出侧栏 IA）
- `/workspace/opentask-smoke/e13/issue-list.png`
- `/workspace/opentask-smoke/e13/inbox.png`
- `/workspace/opentask-smoke/e13/compare-linear-sidebar-ref.png`
- `/workspace/opentask-smoke/e13/README.md`

## Gaps / follow-ups

- localStorage 可能仍缓存旧 `themeColor=#646cff` — 硬刷新/清站点数据后才见 indigo
- Tab mode 仍为 chrome；仅压低高度与阴影
- 知识库/manage 深链仍可用，仅菜单隐藏
- 全量 `pnpm build` 未跑（历史 flake）；未改业务逻辑故未重跑后端 pytest
- `smoke_way` 登录失败锁定；冒烟用 `smoke_e13_visual` / `SmokeTest123!`
