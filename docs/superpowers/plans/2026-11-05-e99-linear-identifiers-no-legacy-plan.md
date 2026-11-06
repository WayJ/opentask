# E99 Plan：Linear Issue Identifiers — 无历史环境，删除 legacy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (本会话 inline) + test-driven-development + verification-before-completion。Steps use checkbox (`- [x]`) syntax。禁止 push/PR；不自开 E100。

**Goal:** 全产品表面只认 `KEY-N`；删除年号 legacy 双解析、`legacy_issue_code` 列、E98 年号回填行为、Jira year codec；CLI/FE 校验收紧；FTS 重建去列。

**Architecture:** Q2a 保留 rev `f9a0b1c2d3e4` 改为文档化 no-op；新前向 revision `g0a1b2c3d4e5` drop 列+索引并 rebuild FTS（SQLite FTS5 + PG generated tsvector）；业务路径仅 `issue_code`；Jira 仅 KEY-N↔OPENTASK 高号段；保持 E98 新建/WS 绑定。

**Tech Stack:** FastAPI + SQLAlchemy async；Alembic；pytest/httpx；Click CLI；Vue3/vitest。

## Global Constraints
- 基线：`sprint/E99-S1` @ `f4bd973e9d3ba006676511c526efb4168e02fa9c`（design tip；E98 tip `02af930` ⊂ HEAD）
- Scheme A / Q1a–Q6a；本地 only；不 push/PR；不开下一 Epic；不停 7377/9527
- CLI VERSION **保持 1.81.0**（未要求 bump）
- **保持 E98**：WS 绑定 / 新建仅 KEY-N / `_generate_issue_code` 必填 WS / 禁止年号分配 / 跨租户不猜
- **不动** Requirement `需求{year}-N`；不引入 Team；不重开 E97–E79；formula no-emit
- **禁止改写** E12 `b8c9d0e1f2a4` / E60 `s5b6c7d8e9f3` 历史 revision 正文（checksum）；只用前向 migration
- 守 E63 `f`+`r`；FE build 后恢复 elegant-router；WT 干净
- 夹具禁止年号主码 happy path；测试假码

## File map
| Path | Role |
|------|------|
| `backend/alembic/versions/2026_11_05_5800-f9a0b1c2d3e4_e98_backfill_year_issue_codes.py` | **改** upgrade/backfill → 文档化 no-op |
| `backend/alembic/versions/2026_11_05_5900-g0a1b2c3d4e5_e99_drop_legacy_issue_code.py` | **新增** drop 列+索引 + FTS rebuild |
| `backend/opentask/models/issue/model.py` | 删 `legacy_issue_code` |
| `backend/opentask/services/issue_service.py` | get/list 仅 `issue_code` |
| `backend/opentask/services/vcs/{service,branch_naming}.py` | 去 OR legacy；去 year 分支解析 |
| `backend/opentask/services/search/{service,backend}.py` | 去 ILIKE legacy；`ISSUE_CODE_RE` 收紧 |
| `backend/opentask/services/issue_csv/service.py` | 去 ILIKE legacy |
| `backend/opentask/api/issue/router.py` | docstring KEY-N only |
| `backend/opentask/api/jira/keys.py` | 删 year codec；`< KEY_N_BASE` → ValueError |
| `backend/tests/conftest.py` | PG FTS expr 去 legacy |
| `backend/tests/services/test_e60_search_backend.py` | FTS DDL 去 legacy |
| `backend/tests/api/test_e99_no_legacy_identifiers.py` | **新增** directed 套件 |
| `backend/tests/api/test_e98_backfill_migration.py` | 改 no-op 验 |
| `backend/tests/api/test_issue_key.py` / `test_e98_linear_*.py` | 删/改 legacy happy path |
| `backend/tests/tasks/test_tasks_jira_wire.py` | KEY-N 往返；年号 ValueError |
| CLI helpers / core/issue.py / auto-detect / e14 | 收紧 + KEY-N 文案 |
| FE `command-palette-entities.ts` + vitest | 2–6；`ISSUE2026-32` false |
| README 现行注释 | KEY-N；不改历史 sprint 证据 md |
| acceptance | 填满 |

### Jira / 校验契约
```python
# keys.py — KEY-N only
KEY_N_BASE = 10_000 * 1_000_000_000  # keep constant
# issue_code_to_key: only _KEY_N_RE; ISSUE{year}-N → ValueError
# key_to_issue_code: number < KEY_N_BASE → ValueError (no year decode)

# validate / looksLike / ISSUE_CODE_RE / detect_by_code:
r"^[A-Za-z][A-Za-z0-9]{1,5}-\d+$"  # prefix length 2–6
# ISSUE2026-32 → False (prefix too long)
```

---

### Task 1 — Docs：plan + acceptance 骨架

- [x] **Step 1:** 入库本 plan；写 acceptance 骨架（后填满，禁止 `_pending_`）
- [x] **Step 2:** commit `docs(E99): plan + acceptance skeleton`

---

### Task 2 — TDD：Jira keys KEY-N only + year ValueError

**Files:**
- Modify: `backend/opentask/api/jira/keys.py`
- Modify: `backend/tests/tasks/test_tasks_jira_wire.py::TestKeyCodec`
- Create directed asserts in `backend/tests/api/test_e99_no_legacy_identifiers.py`

- [x] **Step 1: RED** — 改 TestKeyCodec 期望 KEY-N 往返；`issue_code_to_key("ISSUE2026-3")` / `key_to_issue_code("OPENTASK-2026000000003")` → ValueError
- [x] **Step 2:** 跑测确认红
- [x] **Step 3: GREEN** — 删 `_ISSUE_CODE_RE` / year 分支；`< KEY_N_BASE` → ValueError；更新模块 docstring
- [x] **Step 4:** 绿；commit `feat(E99): jira keys KEY-N only`

---

### Task 3 — TDD：by_code / search / VCS 去 legacy OR

**Files:** issue_service, vcs/service, vcs/branch_naming, search/*, issue_csv, router docstring, model

- [x] **Step 1: RED** — `test_e99_year_by_code_404`（不插年号行）；改写/删除 `test_by_code_matches_legacy_issue_code`、`test_legacy_by_code_still_works` 为 404 负例；branch_naming `test_parse_legacy` → None
- [x] **Step 2:** 红确认
- [x] **Step 3: GREEN** — ORM 删字段；所有 `or_(…legacy…)` / ILIKE legacy 删除；branch_naming 删 `_LEGACY_CODE`；search `ISSUE_CODE_RE` 收紧
- [x] **Step 4:** 绿；commit `feat(E99): drop legacy dual-read paths`

---

### Task 4 — TDD：E98 backfill no-op + E99 drop migration + FTS

**Files:**
- Modify f9a0 revision → no-op
- Create `2026_11_05_5900-g0a1b2c3d4e5_e99_drop_legacy_issue_code.py`
- Rewrite `test_e98_backfill_migration.py` → no-op
- Add `test_e99_drop_legacy_column` / FTS DDL sync in e60 + conftest

Migration `g0a1b2c3d4e5` outline:
```python
revision = "g0a1b2c3d4e5"
down_revision = "f9a0b1c2d3e4"

def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        # drop GIN + generated search_tsv; drop ix + column; recreate tsv without legacy
        ...
    elif dialect == "sqlite":
        # DROP TRIGGER issues_*; DROP TABLE issues_fts;
        # DROP INDEX; ALTER TABLE issues DROP COLUMN legacy_issue_code;
        # recreate FTS5 without legacy_issue_code + triggers + backfill
        ...
```

- [x] RED directed drop/no-op tests → GREEN → commit `feat(E99): no-op E98 backfill + drop legacy_issue_code`

---

### Task 5 — CLI / FE 校验收紧 + 文案

- helpers.validate_issue_code：仅 2–6 KEY-N；doctest 去 ISSUE2026 True
- test_issue_auto_detect / test_e14_key_n：年号 → False；保留 OT-1/WAY-42
- core/issue.py help：一律 KEY-N；删「legacy still resolves」
- FE regex + vitest：`ISSUE2026-32` false；`ABC-1` true
- 夹具：oauth2 `_next_issue_code`、tasks_contract、CLI mock → KEY-N
- README 现行 Jira 说明 → KEY-N（不改历史 sprint md）

- [x] RED then GREEN；commit `feat(E99): CLI/FE KEY-N only validation`

---

### Task 6 — Verify + acceptance + 收尾

- Directed：e99 + e98 create/WS + jira keys + e60 FTS + issue_key + branch_naming
- Full BE `pytest tests`（flake `test_user_search` 记录不阻塞）
- CLI full；FE vitest + production build；恢复 f+r；`rg legacy_issue_code` 门禁
- 填满 acceptance；WT 干净；STOP

---

## Self-review
1. Spec coverage：Q1a–Q6a、§2.1 锚点、§3.3/3.4 migration、§6 验收 → 均有 Task
2. 无 placeholder / TBD
3. E98 绑定保留；E12/E60 历史 revision 不改写；Requirement 不动
