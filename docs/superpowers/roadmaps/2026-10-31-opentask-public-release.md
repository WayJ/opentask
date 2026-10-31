---
epic: E1
status: open
date: 2026-10-31
---

# OpenTask 改名收尾与公开发布到 GitHub

## Deliverables

| deliverable | note |
|---|---|
| 项目改名落地（vibe_king/vibeking/Vibe King → opentask/OpenTask） | 目录名、Python 包名、CLI 命令名、URL 前缀、品牌文案四类均已替换 |
| 凭据脱敏，公开仓库不含真实密钥 | API Key、数据库密码、JNPF 加密密钥已移入被忽略的 `config/local.yaml` 与 `.env.*.local` |
| 企业名与个人邮箱清除 | 「天穹智能」→「WayJ」；QQ 邮箱 → GitHub noreply；保留 soybeanjs 上游 MIT 声明 |
| 代码可运行性验证通过 | 导入图无断链；后端 pytest 与前端 lint/build 通过 |
| 首次提交并推送到 github.com/WayJ/opentask | 仓库当前零提交，推送前需建首个 commit |
| CLAUDE.md → AGENTS.md 迁移 | 根目录、frontend、backend 三处，并修正文内自引用与代码引用 |

## Definition of Done

- [ ] `git log` 显示首次提交，且 `git ls-files` 中不含 `config/local.yaml`、`.env.prod.local`、`extensions/chatapp/.env.prod` 等含真实凭据文件
- [ ] 全仓库扫描 `vibeking|Vibe King|VIBE_KING|vibe-king|vibe_king` 仅命中 `backend/openapi*.json`（自动生成产物）
- [ ] 全仓库扫描高危密钥模式（AKIA/sk-/ghp_/私钥/JWT）零命中
- [ ] `cd backend && uv run pytest tests/ -v` 通过
- [ ] `cd frontend && npm run lint && npm run build` 通过
- [ ] `cd agent-harness/opentask-cli && pip install -e . && opentask --version` 输出正确版本号
- [ ] 后端与 CLI 的导入图静态校验零缺失（改名引入的）
- [ ] 推送后 `git ls-remote origin` 显示远端分支与本地一致

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | ready | go 决定：S1 交付内容已被 epic DoD 第 28 行（导入图静态校验零缺失）与第 27 行（CLI 可安装运行）覆盖。范围：修复改名遗留 —— 断链符号链接 `api/oauth.py`、CLI 内 `cli_anything.*` 失效导入、`.claude/settings.json` 路径 |
| S2 | planned | 门禁验证：修复历史遗留死引用（agent_task / file_storage / agent_v3），使 pytest 与 lint/build 全绿 |
| S3 | planned | 首次提交 + 推送 GitHub，核对远端文件清单确认无凭据泄露 |

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | 真实凭据从已跟踪配置移入 `backend/config/local.yaml`，而非仅依赖 .gitignore | `config.py` 已支持 local.yaml 最后加载并深度覆盖，无需改代码即可脱敏，且本地开发体验不变 | 2026-10-31 | `backend/opentask/config.py` load_config_file |
| D2 | 统一替换 `vibeking` 标识符为 `opentask`（含后端 Python 包 `backend/vibeking` → `backend/opentask`） | 用户要求全量改名；后端包名与 CLI 包名同名会造成 import 混淆 | 2026-10-31 | 本文档 |
| D3 | URL 前缀 `/vibeking` → `/opentask` 一并改名 | 用户确认；但需同步更新部署侧 nginx 配置（不在本仓库），上线前必须核对 | 2026-10-31 | 用户确认 2026-10-31 |
| D4 | 品牌名统一为 OpenTask，示例域名改用 `api.example.com` | 权限策略拒绝引入未批准的新端点；`api.opentask.com` 为真实占位域名，改用 RFC 2606 保留域名 | 2026-10-31 | 本文档 |
| D5 | 历史遗留死引用（agent_task/file_storage/agent_v3 模块不存在）不阻塞发布 | 源目录本就不存在，属改名前遗留问题，与改名无关；记为技术债单独偿还 | 2026-10-31 | 导入图静态校验结果 |

## Asset Disposition

| asset | disposition | note | date | evidence |
|---|---|---|---|---|
| `backend/config/local.yaml` | reuse | 承载全部真实凭据，已被 .gitignore 忽略 | 2026-10-31 | `.gitignore` config/local.yaml |
| `frontend/.env.prod.local` | reuse | 承载本地内网地址，已被 .gitignore 忽略 | 2026-10-31 | `.gitignore` .env.*.local |
| `extensions/chatapp/` | retire | 目录在改名过程中被清空，用户确认不发布；仅保留 `.env.prod.example` | 2026-10-31 | 用户确认 2026-10-31 |
| `backend/opentask/api/oauth.py`（断链符号链接） | retire | 指向已不存在的 `oauth/router.py`，改名无关的死链 | 2026-10-31 | `find -type l` 检查 |
| 根目录 `Dockerfile` / `docker-compose.yml` | watch | Node+Prisma 模板残留，与 Python 后端不匹配，发布不依赖，待评估 | 2026-10-31 | Dockerfile 内容 |

## Open Questions

| id | question | status | resolution |
|---|---|---|---|
| Q1 | 部署侧 nginx 是否同步把 `/vibeking/` location 改为 `/opentask/`？ | open | 仓库内无 nginx 配置，需运维确认；否则线上前端请求 404 |
| Q2 | 后端包 `backend/vibeking` → `backend/opentask` 改名后，已有的 `.venv` 环境与 IDE 索引是否需要重建？ | open | 待本地验证 |
| Q3 | `docs.vibeking.com` / `support@vibeking.com` 等外部链接是否需要指向新域名？ | open | 域名归属未知，需用户确认 |
| Q4 | 根目录 Node/Prisma 模板 Dockerfile 是删除还是重写为 Python 版？ | deferred | 不阻塞发布，后续单独处理 |

## Cross-cutting

| concern | owning epic | note |
|---|---|---|
| 公开仓库的凭据卫生 | E1 | S1–S3 每个 sprint 结束前须重扫密钥模式 |
| 改名后前后端契约（URL 前缀、CLI 命令名）| E1 | D3 决定，需与部署侧同步 |
| 本地开发体验不因脱敏而退化 | E1 | D1 的 local.yaml 覆盖机制保障 |
| 契约层鉴权不得成为凭据泄露面 | E2 | E2 的 D9 复用 access_token 体系，凭据走本地忽略文件 |
