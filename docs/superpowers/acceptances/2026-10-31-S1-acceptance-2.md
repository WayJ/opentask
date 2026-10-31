# Acceptance record — sprint S1 (re-acceptance after main sync), 2026-10-31

## Verdict

pass — 合并 main（含 E1-S2 全部落地内容）后在 sync 后的树上全量重验：五个必需场景全部通过；失败集与同日基线精确一致、零新增（外网集成文件因网络不可达排除，对账见 Obstacles）；无未偿 doc-sync 欠账。本记录为同日第二次评审（后缀 -2），前记录 `2026-10-31-S1-acceptance.md`（fingerprint ed44401d）保留为历史，按 append-only 规则不改动。

## Acceptance Evidence

```supervibe-evidence
{"schema":1,"sprint":"docs/superpowers/sprints/2026-10-31-S1-plan.md","record":"docs/superpowers/acceptances/2026-10-31-S1-acceptance-2.md","fingerprint":"83a52be15a5f579cd101ffb67ac80cd7249de0d98059e1fd0e94253b256a863a"}
```

## Execution Evidence

```supervibe-acceptance-results
{"schema":1,"scope":"sprint","candidate":"83a52be15a5f579cd101ffb67ac80cd7249de0d98059e1fd0e94253b256a863a","environment":"本机 Windows 11；载体 worktree D:/projects/opentask-worktrees/S1（分支 sprint/E1-S1，sync main 后 HEAD 93b95ce：88cef1d + main@520e674 合并，tech-debt-tracker 冲突并集解析）；后端 uv 环境；CLI 验收 venv 同前记录；运行时间 2026-10-31T10:5x–11:07Z UTC","results":[{"id":"S1","status":"passed","modality":"cli","environment":"real","steps":["删除 backend/opentask/api/oauth.py","运行后端导入图静态校验（python -c \"import opentask.api\"）"],"expected":"零缺失，无 ImportError","observed":"oauth.py 保持删除（合并保留）；uv run python -c import opentask.api OK","artifacts":["Scenario Results 表"],"blockers":[]},{"id":"S2","status":"passed","modality":"cli","environment":"real","steps":["cd agent-harness/opentask-cli","pip install -e .","opentask --version"],"expected":"退出码 0，输出版本号","observed":"验收 venv -e 安装指向本载体；opentask v1.0.6，退出码 0","artifacts":["Scenario Results 表"],"blockers":[]},{"id":"S3","status":"passed","modality":"cli","environment":"real","steps":["grep -rn \"cli_anything\" agent-harness/"],"expected":"零命中，或仅命中注释/文档性说明且 repl_skin 测试通过","observed":"零命中；repl_skin 用例含于 383 passed","artifacts":["Scenario Results 表"],"blockers":[]},{"id":"S4","status":"passed","modality":"cli","environment":"real","steps":["全仓 grep \".claude/settings\" 与 .claude 路径引用"],"expected":"无断链引用；若零命中则记录证据","observed":"代码/脚本类零命中","artifacts":["Scenario Results 表"],"blockers":[]},{"id":"S5","status":"passed","modality":"cli","environment":"real","steps":["cd agent-harness/opentask-cli","python -m pytest tests/ -v"],"expected":"与基线失败集一致（基线含同样 8 项存量失败用例），本次改动零新增失败；全量转绿属 S2 门禁范围（修订 A1）","observed":"死 IP 修复后全量套件：6 failed/383 passed/90 skipped（1.50s，无任何排除）；6 个失败 ID 与同日基线失败集逐 ID 一致（基线 8 − test_integration_real_api ×2 现被守卫跳过），零新增；新增 13 个 skip 为 4 个活体集成文件的模块级守卫（OPENTASK_TEST_API_URL 未配置即跳过，原硬编码服务器已下线——用户确认）","artifacts":["Obstacles 外网排除与对账记录","/tmp 后台运行输出"],"blockers":[]}]}
```

## Gate Evidence

- 载体分支 tip（运行时）：`93b95ce`（sync 合并提交）
- 宿主门禁两命令属 E1-S2 范围并在其载体全绿（395P/0F/0E + lint/build）；E1-S2 已落地 main，本 sprint 合并后 main 将具备全绿门禁基线；complete 阶段将按 gate 缓存规则核对。

## Scenario Results

| id | command | expected | actual | pass |
|---|---|---|---|---|
| S1 | `uv run python -c "import opentask.api"` | 零缺失 | import OK | yes |
| S2 | `opentask --version` | 退出 0 + 版本号 | opentask v1.0.6 | yes |
| S3 | `grep -rn "cli_anything" agent-harness/` | 零命中 | 0 | yes |
| S4 | 全仓 `.claude/settings` grep | 无断链 | 0 | yes |
| S5 | CLI pytest（外网文件排除，见障碍） | 基线一致零新增 | 6F/383P/4S；对账一致 | yes |

## DoD Checklist

同前记录 `2026-10-31-S1-acceptance.md` 的逐项裁定（S1 所属项全证据通过；backend pytest/frontend 门禁由 S2 承接且已在 main 全绿落地；首提交/ls-remote 由 S3 承接）。本次重验未改变任何 DoD 项的归属与结论；vibeking 代码零命中在 sync 后树上维持（websocket 修复已随 main 并入本树）。

## Obstacles (verbatim)

- 2026-10-31 10:4xZ — sync main 进 sprint/E1-S1 冲突 1 处：docs/tech-debt-tracker.md（本侧关闭 TD2/TD4，main 侧经 S2 关闭 TD1）。按 handwritten 双路径规则先出逐项清单后解析：并集（open 区仅剩 TD3/TD5；closed 区 TD1+TD2+TD4，列格式统一为 6 列 resolution 形）。无生成物冲突。
- 2026-10-31 10:5x–11:0xZ — CLI pytest 全量首跑挂起（>10 分钟无进展）：定位为 tests/test_integration_{authenticated,crud,real_api,scenarios}.py 四文件硬编码真实外网服务器 `http://39.183.172.160:28000/opentask`，当前网络对该 IP 不可达（curl -m 5 → 000/exit 28），客户端 30s 超时 × 重试致每个用例爬行 1–2 分钟。临时处置（narrowest workaround）：`--ignore` 排除该 4 文件重跑得 6F/383P/4S/1.29s；失败集与同日基线（8F/394P/77S 全量）精确对账：6 = 8 −（被排除文件中的 test_integration_real_api ×2 失败），逐 ID 一致零新增。教训（建议入 notes/技术债）：① CLI 集成测试直连生产外网 IP 且无快速跳过守卫（后端同类已由 S2 加守卫），建议加「服务器不可达即 skip」守卫并把目标地址移出测试常量；② 该公网 IP 出现在将公开的仓库测试代码中，S3 推送评审需裁定是否脱敏。
- 2026-10-31 11:07Z — after-snapshot 与 before（f62f60e7）一致；pytest 产生的 .pytest_cache 为 ignored 不入指纹。

## Doc-Drift Audit

| map row (change, owes) | matched this sprint | doc state | detail |
|---|---|---|---|
| `backend/config/*.yaml` → backend/README.md | 无（S1 未改 config yaml；sync 并入的 S2 变更其欠账已在 S2 记录核销） | n/a | 未触发 |
| `docs/superpowers/roadmaps/*.md` → roadmaps/ | 无 | n/a | 未触发 |
| `frontend/.env.prod` → frontend/README.md | 无 | n/a | 未触发 |

## 追加：死 IP 修复（本评审内处置，用户指示）

- 2026-10-31 19:3xZ — 用户确认 `39.183.172.160:28000` 服务器已不存在并指示修复。处置（协调者按验收期窄修复惯例执行，全部改动入指纹树）：
  - `tests/test_integration_{authenticated,crud,real_api,scenarios}.py`：`API_BASE_URL` 改 `OPENTASK_TEST_API_URL` 环境变量驱动 + 模块级 skipif 守卫（未配置即跳过）
  - `opentask/core/{collection,issue,project}.py` ×6 处：删除引导链接与 `web_ui_url` 由硬编码 IP 改为 `obj.config.api_url.rstrip('/')` 拼接（同源部署语义不变）
  - `opentask/core/update.py`：`DEFAULT_MARKETPLACE_URL` 改 `OPENTASK_MARKETPLACE_URL` 环境变量驱动
  - 验证：8 文件 ast 全过；全量 CLI 套件 6F/383P/90S/1.50s（失败集与基线逐 ID 一致）；源码 grep 死 IP 零命中（余量为 gitignored .pyc 缓存，已清）
  - 指纹随之更新 f62f60e7 → 83a52be1；上节 Obstacles 中的 --ignore 排除对账被本修复取代（全量无排除运行）
