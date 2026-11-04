# Acceptance record — sprint E5-S1（命令面板壳 + ⌘K + 动作跳转）, 2026-11-04

## Verdict

**pass** — S1 范围交付：`useCommandPalette` 单例、Actions/Menus 分组面板、base-layout 无条件挂载 + Meta/Ctrl+K、header 图标共享 `open()`。门禁：vitest 定向 **16 passed**；`npm run lint` **0 errors** / 248 warnings（存量）；`npm run build` 成功；全量 pytest **621 passed, 27 skipped, 0 failed**。未做实体搜索（S2）与 C/A/S/P/I/⌘B 焦点热键（S3）。未推远程。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-11-04-E5-S1-plan.md","record":"docs/superpowers/acceptances/2026-11-04-E5-S1-acceptance.md","fingerprint":"0063b589d4695fe76373e5d2e859dbb13955bcaa"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"0063b589d4695fe76373e5d2e859dbb13955bcaa","environment":"共享 box Linux；worktree /workspace/opentask-worktrees/E5-S1；分支 sprint/E5-S1（基 E4-S3 tip 1e03724）；PostgreSQL Docker opentask-pg-test；backend .venv；frontend npm/vite/vitest；Asia/Shanghai 2026-11-04 09:26–09:33 CST","results":[{"id":"S1","status":"passed","modality":"unit","environment":"real","steps":["vitest useCommandPalette open/toggle","code: useAppHotkeys isModK"],"expected":"⌘K 契约可测；host 挂 base-layout","observed":"16 vitest passed；host+hotkeys 已挂","artifacts":[],"blockers":[]},{"id":"S2","status":"passed","modality":"unit","environment":"real","steps":["close() clears query"],"expected":"Esc/close 清空","observed":"composable close 测通过；modal Esc→close","artifacts":[],"blockers":[]},{"id":"S3","status":"passed","modality":"code","environment":"real","steps":["GlobalSearch v-if 仅图标；CommandPaletteHost 无条件"],"expected":"隐藏按钮仍可 ⌘K","observed":"base-layout 无条件 host；header 仅 ButtonIcon","artifacts":[],"blockers":[]},{"id":"S4","status":"passed","modality":"unit","environment":"real","steps":["buildNavActions nav.issues"],"expected":"/issue/list","observed":"vitest buildNavActions","artifacts":[],"blockers":[]},{"id":"S5","status":"passed","modality":"unit","environment":"real","steps":["nav.create_issue"],"expected":"/issue/create","observed":"vitest","artifacts":[],"blockers":[]},{"id":"S6","status":"passed","modality":"unit","environment":"real","steps":["nav.projects / nav.inbox"],"expected":"/workflow/projects / /inbox","observed":"vitest four actions","artifacts":[],"blockers":[]},{"id":"S7","status":"passed","modality":"unit","environment":"real","steps":["menusToPaletteItems + buildPaletteGroups with query"],"expected":"Menus 分组可过滤","observed":"vitest Menus group","artifacts":[],"blockers":[]},{"id":"S8","status":"passed","modality":"cli","environment":"real","steps":["npm run lint","npm run build"],"expected":"0 errors；build ok","observed":"0 errors / 248 warnings；Build successful","artifacts":["/tmp/e5s1-lint2.txt","/tmp/e5s1-build2.txt"],"blockers":[]},{"id":"R-browser","status":"blocked","modality":"browser","environment":"real","steps":["未跑完整前后端浏览器联调"],"expected":"R1–R3 手感","observed":"单元+静态门禁覆盖；浏览器可选不阻塞 S1 pass","artifacts":[],"blockers":["本轮无浏览器 E2E 会话"]}]}
```

## Gate Evidence

| gate | command | result |
|---|---|---|
| vitest 定向 | `cd frontend && npm test -- --run src/utils/hotkeys.test.ts src/utils/command-palette.test.ts src/composables/use-command-palette.test.ts` | **16 passed** |
| 前端 lint | `cd frontend && npm run lint` | **0 errors, 248 warnings** |
| 前端 build | `cd frontend && npm run build`（`.env.prod` 本地拷贝，不入库） | **Build successful** |
| 全量 pytest | `cd backend && uv run pytest tests/ -q` | **621 passed, 27 skipped, 0 failed**（210.77s） |

## Scenario Results

| id | expected | actual | pass |
|---|---|---|---|
| S1 ⌘K 打开契约 | host + isModK + toggle | code + vitest | yes |
| S2 Esc/close | 关闭并清 query | vitest close | yes |
| S3 隐藏图标仍可 ⌘K | host 无条件 | base-layout | yes |
| S4 Issues | /issue/list | vitest | yes |
| S5 Create | /issue/create | vitest | yes |
| S6 Projects/Inbox | 对应路由 | vitest | yes |
| S7 Menus 过滤 | query 后 Menus 组 | vitest | yes |
| S8 lint/build | 0 error / build ok | 通过 | yes |
| 浏览器 R1–R3 | 可选 | **blocked** | n/a |

## DoD Checklist

- [x] Wave 计划 / palette 壳 / 菜单 i18n / 门禁
- [x] ⌘K / Ctrl+K 开关面板；Esc 关闭清 query
- [x] 主题隐藏搜索图标不卸载热键与 modal
- [x] Actions：Issue 列表 / Create / Projects / Inbox；Menus 来自 searchMenus
- [x] 全量 pytest 无新增失败；lint 0 errors；build 成功
- [x] acceptance 写入；sprint state=closed；**不推远程**
- [x] 未实现 S2 实体搜索；未实现 S3 C/A/S/P/I 与 ⌘B（Board↔List，归 S3）

## Obstacles (verbatim)

- 2026-11-04 — 浏览器 E2E 未跑；不阻塞 S1 pass。
- 2026-11-04 — worktree 缺 `.env.prod`（gitignore）；从 E4-S3 拷贝后 build 成功，未入库。
- 2026-11-04 — 未推远程；Epic E5 仍 active（S2/S3 待做）。
- 2026-11-04 — 北星补充 ⌘B Board↔List 明确归 **S3**，本 Sprint 未改热键面。

## Doc-Drift Audit

| map row | matched | detail |
|---|---|---|
| useCommandPalette singleton | yes | composables/use-command-palette.ts |
| useAppHotkeys Meta/Ctrl+K | yes | composables/use-app-hotkeys.ts |
| CommandPaletteHost on base-layout | yes | global-search/command-palette-host.vue |
| GlobalSearch button-only | yes | index.vue open() |
| Actions + Menus groups | yes | utils/command-palette.ts + modal |
| Entity search / focus / C/A/S/P/I / ⌘B | excluded | S2/S3 |
