# S1 改名遗留修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清除改名遗留 —— 删 oauth 断链残留、cli_anything 品牌彻底去化（含前端文案）、CLI 元数据诚实化，使后端与 CLI 导入图零缺失、CLI 可安装运行。

**Architecture:** 纯清理类 sprint：删除一个无引用死文件；对 vendored 的 `repl_skin.py` 做行为保持的品牌重命名（env var / 目录约定 / banner 文案 / docstring），测试先行同步修改；元数据与用户可见文案逐字替换。无新功能、无接口变更。

**Tech Stack:** Python（CLI: click/httpx/pytest）、FastAPI 后端（只读校验）、Vue3 前端（纯文案）。

**Spec:** `docs/superpowers/specs/2026-10-31-s1-rename-leftovers-design.md`

## Global Constraints

- 所有代码提交在 worktree `../opentask-worktrees/S1`（分支 `sprint/E1-S1`）；main 只收台账文档提交
- 命名定死：环境变量 `OPENTASK_NO_COLOR`；历史目录 `~/.opentask-<software>`；banner 品牌字样 `OpenTask`
- 行为保持：除上述三个重命名外不改任何逻辑；`str | None` 等语法不动
- PostgreSQL 切换（S2）、门禁修复（S2）、推送（S3）不在本计划内
- 提交信息 conventional 风格，尾行 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- sprint 台账 `docs/superpowers/sprints/2026-10-31-S1-plan.md` 五段结构与逐字 DoD 不可变

## Review Focus

- 旧环境变量 `CLI_ANYTHING_NO_COLOR` 被静默忽略 —— 仓库未发布无外部用户（设计 A 理由），新变量行为由 Task 2 的 `test_opentask_no_color_env` 钉住
- 历史目录改名丢失已有用户历史 —— 全新公开仓库无存量用户，新目录行为由 Task 2 的 `test_init_creates_history_dir`（断言 `.opentask-test`）钉住
- banner 品牌字样更换破坏断言 —— banner 测试只断言软件名/版本/help（`test_repl_skin.py:142-144`），Task 2 全量跑测试文件钉住
- `requires-python` 提到 3.10 后 3.8/3.9 用户装不上 —— 这是诚实化目的本身（代码用了 `str | None`），Task 3 以真实 `pip install -e .` + `opentask --version` 验证
- 前端文案替换漂移到命令语法 —— 只替换前缀 token `cli-anything-opentask ` → `opentask `，命令体不动，Task 4 以 grep 零残留钉住

---

### 预备：worktree 与解释器

- [ ] **P1: 台账文档提交到 main**（在主检出 `D:/projects/opentask`）

```bash
git add docs/superpowers/ .agents/ AGENTS.md 2>/dev/null; git status --short
git commit -m "chore(supervibe): E1/S1 物化、设计文档与执行计划

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **P2: 建 worktree**（主检出执行）

```bash
git worktree add ../opentask-worktrees/S1 -b sprint/E1-S1
cd ../opentask-worktrees/S1 && git log --oneline -1
```
Expected: HEAD 为刚提交的台账 commit

- [ ] **P3: 确认可用 Python 解释器**

```bash
python --version && python -c "print('ok')"
```
Expected: 版本号 ≥3.10 且输出 ok。若 `python` 是 WindowsApps 空桩（无输出），依次试 `py -3 --version`、`python3 --version`，选定一个记为 `$PY`，后续命令中把 `$PY` 直接替换为该解释器（每次 Bash 调用相互独立，环境变量不跨调用保留）。

---

### Task 1: 删除 oauth.py 断链残留（backend）

**Files:**
- Delete: `backend/opentask/api/oauth.py`

**Interfaces:**
- Consumes: 无（15 字节降级符号链接，内容为 `oauth/router.py`，目标不存在）
- Produces: 后端导入图少一个死路径；Task 5 的静态扫描以零缺失通过

- [ ] **Step 1: 确认零引用**（worktree 内）

```bash
cd /d/projects/opentask-worktrees/S1
grep -rn "api\.oauth\|api/oauth" backend/opentask/ --include="*.py" | grep -v "sso_base_url"
```
Expected: 无输出（命中的 `/api/oauth/*` 全是 SSO 外部 URL，已被过滤）

- [ ] **Step 2: 删除文件**

```bash
git rm backend/opentask/api/oauth.py
```

- [ ] **Step 3: 后端导入图静态校验**（脚本同时供 Task 5 复用，保存为临时文件 `/tmp/import_scan.py`）

```bash
cat > /tmp/import_scan.py <<'EOF'
import ast, sys
from pathlib import Path

def scan(root: Path, pkg: str) -> int:
    root = root.resolve()
    missing = []
    for f in sorted(root.rglob("*.py")):
        rel = f.relative_to(root)
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        parts = list(rel.with_suffix("").parts)
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [(0, a.name) for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    targets = [(node.level, node.module)]
            for level, mod in targets:
                mod_parts = mod.split(".")
                if level == 0:
                    if mod_parts[0] != pkg:
                        continue  # 外部依赖不在改名校验范围
                    p = root.joinpath(*mod_parts)
                    ok = p.with_suffix(".py").exists() or (p / "__init__.py").exists()
                    # 父包必须存在
                    for i in range(1, len(mod_parts)):
                        q = root.joinpath(*mod_parts[:i])
                        if not (q.with_suffix(".py").exists() or (q / "__init__.py").exists()):
                            ok = False
                else:
                    cur = f.parent
                    for _ in range(level - 1):
                        cur = cur.parent
                    p = cur.joinpath(*mod_parts)
                    ok = p.with_suffix(".py").exists() or (p / "__init__.py").exists()
                if not ok:
                    missing.append(f"{rel}: {mod}")
    for m in missing:
        print("MISSING:", m)
    print(f"scan {pkg}: {len(missing)} missing")
    return len(missing)

if __name__ == "__main__":
    sys.exit(scan(Path(sys.argv[1]), sys.argv[2]))
EOF
python /tmp/import_scan.py backend opentask
```
Expected: `scan opentask: 0 missing`，退出码 0

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: 删除 oauth.py 断链符号链接残留

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
（`git rm` 已暂存，直接 commit）

---

### Task 2: repl_skin.py 去品牌（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/repl_skin.py:1-19,33,62,107-110,121,131,144,171,173`
- Modify: `agent-harness/opentask-cli/tests/test_repl_skin.py:85-91,113-117`
- Modify: `agent-harness/opentask-cli/opentask/tests/TEST.md:155`

**Interfaces:**
- Consumes: 现有 `ReplSkin`（签名不变）
- Produces: env var `OPENTASK_NO_COLOR`（替代 `CLI_ANYTHING_NO_COLOR`）；默认历史目录 `~/.opentask-<software>/history`；banner 品牌字样 `OpenTask`

- [ ] **Step 1: 先改测试（制造失败）**

`tests/test_repl_skin.py` 两处：

```python
# :89
hist_dir = tmp_path / ".opentask-test"
# :113-115
def test_opentask_no_color_env(self, monkeypatch):
    """测试 OPENTASK_NO_COLOR 环境变量"""
    monkeypatch.setenv("OPENTASK_NO_COLOR", "1")
```

- [ ] **Step 2: 跑这两个测试确认失败**

```bash
cd agent-harness/opentask-cli && $PY -m pytest tests/test_repl_skin.py -k "opentask_no_color_env or init_creates_history_dir" -v
```
Expected: FAIL（env var 测试：代码仍读 `CLI_ANYTHING_NO_COLOR`，颜色未被禁用；hist 测试：仍建 `.cli-anything-test`）

- [ ] **Step 3: 实现 repl_skin.py 重命名**

行为三处 + 文案若干：
- `:144` `os.environ.get("CLI_ANYTHING_NO_COLOR")` → `os.environ.get("OPENTASK_NO_COLOR")`
- `:131` `Path.home() / f".cli-anything-{self.software}"` → `f".opentask-{self.software}"`
- `:173` `brand = self._c(_CYAN + _BOLD, "cli-anything")` → `"OpenTask"`
- docstring `:1-19`：标题与用法示例改写为 opentask 语境（`from opentask.utils.repl_skin import ReplSkin`；删除 `cli_anything/<software>/` 复制指引）
- 注释 `:33,62,121,171` 与类 docstring `:107,110` 中 `cli-anything` → `OpenTask`/`opentask`（按语义）
- `opentask/tests/TEST.md:155` `--cov=cli_anything.opentask` → `--cov=opentask`

- [ ] **Step 4: 跑 repl_skin 全部测试确认通过**

```bash
$PY -m pytest tests/test_repl_skin.py tests/test_repl_skin_extended.py -v
```
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add opentask/utils/repl_skin.py tests/test_repl_skin.py opentask/tests/TEST.md
git commit -m "refactor: repl_skin 品牌 cli-anything 彻底去化为 OpenTask

env var CLI_ANYTHING_NO_COLOR → OPENTASK_NO_COLOR
历史目录 ~/.cli-anything-<sw> → ~/.opentask-<sw>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: CLI 元数据诚实化

**Files:**
- Modify: `agent-harness/opentask-cli/pyproject.toml:10,21-22`

**Interfaces:**
- Produces: `requires-python >= 3.10`（代码用 `str | None` 语法，3.8/3.9 实际不可装）

- [ ] **Step 1: 改元数据**

- `:10` `requires-python = ">=3.8"` → `">=3.10"`
- `:21-22` 删除 `"Programming Language :: Python :: 3.8"`、`":: 3.9"` 两行

- [ ] **Step 2: 安装验证**

```bash
cd agent-harness/opentask-cli && $PY -m pip install -e . && opentask --version
```
Expected: 安装成功；输出版本号（1.0.6），退出码 0。若 `opentask` 不在 PATH：用 `$PY -m pip show -f opentask` 找到 Scripts 目录，以全路径执行 `opentask.exe --version`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "fix: requires-python 提升至 3.10 并同步 classifiers

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: 前端 AgentPromptModal 文案去品牌

**Files:**
- Modify: `frontend/src/components/AgentPromptModal.vue:58,79,85,88,99,105,108,113,118`

**Interfaces:**
- Produces: 用户可见命令示例前缀 `cli-anything-opentask ` → `opentask `（仅前缀 token，命令体不动）

- [ ] **Step 1: 替换前缀（8 处）**

```bash
cd /d/projects/opentask-worktrees/S1
sed -i 's/cli-anything-opentask /opentask /g' frontend/src/components/AgentPromptModal.vue
```

- [ ] **Step 2: 验证零残留**

```bash
grep -rn "cli[-_]anything" frontend/ --include="*.vue" --include="*.ts"
git diff --stat frontend/src/components/AgentPromptModal.vue
```
Expected: grep 无输出；diff 仅该文件、仅 8 行

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AgentPromptModal.vue
git commit -m "fix: AgentPromptModal 命令示例前缀改为 opentask

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: 全局校验 + 台账收尾

**Files:**
- Modify: `docs/tech-debt-tracker.md`（关 TD4）
- Modify: `docs/superpowers/sprints/2026-10-31-S1-plan.md`（勾选 checkbox，附证据）

**Interfaces:**
- Consumes: Task 1–4 的提交；`/tmp/import_scan.py`

- [ ] **Step 1: CLI 测试全量**

```bash
cd agent-harness/opentask-cli && $PY -m pytest tests/ -q
```
Expected: 全部通过。若有个别失败：先判定是否改名相关 —— 相关则本任务内修复；无关的历史遗留则记录到 sprint 文档（不扩 scope，S2 处理）

- [ ] **Step 2: 双侧导入图静态扫描**

```bash
$PY /tmp/import_scan.py backend opentask
$PY /tmp/import_scan.py agent-harness/opentask-cli opentask
```
Expected: 均 `0 missing`

- [ ] **Step 3: 全仓残留终扫**

```bash
grep -rni "cli[-_]anything" . 2>/dev/null | grep -v "\.git/" | grep -v node_modules | grep -v "docs/superpowers" | grep -v "\.agents/notes"
```
Expected: 仅剩 `docs/tech-debt-tracker.md` 的 TD4 历史行（Step 4 处理后允许保留为历史记录）

```bash
grep -rn "\.claude" . 2>/dev/null | grep -v "\.git/" | grep -v node_modules | grep -v "docs/superpowers" | grep -v "\.agents/notes"
```
Expected: 无输出（`.claude` 残留任务以零命中证据关闭）

- [ ] **Step 4: 关闭 TD4**

先找证据提交：

```bash
git log --oneline -S "cli_anything" -- agent-harness/opentask-cli | head -5
```
在 `docs/tech-debt-tracker.md` TD4 行补 `repaid` 标记与证据（提交哈希 + 本次验证输出摘要）。

- [ ] **Step 5: 勾选 sprint 文档 checkbox（附证据）并提交**

```bash
git add docs/tech-debt-tracker.md docs/superpowers/sprints/2026-10-31-S1-plan.md
git commit -m "chore: S1 校验收尾，关闭 TD4

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
