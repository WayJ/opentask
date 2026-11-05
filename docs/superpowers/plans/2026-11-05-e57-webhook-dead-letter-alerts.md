# E57 Plan：Webhook 死信告警 mid-thick — Inbox/邮件 + 去重 + 可选自动停用 · CLI 1.41.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`5752cb4` · 分支 `sprint/E57-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e57-webhook-dead-letter-alerts-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E58**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Owner 可为 WS（及可选 per-hook）配置死信告警阈值；窗口内 dead≥阈值（或连续 dead）→ 向 WS owners 投递 Inbox（`webhook_dead_letter_alert`）+ E30 邮件钩；去重账本防刷；可选硬顶自动 `enabled=false` + `webhook_auto_disabled` 通知；FE 告警折叠 + mute；CLI **1.41.0**；无 PagerDuty / Push / formula emit。

**Architecture:** `workspaces.webhook_alert_settings` JSON + `workspace_webhooks.alert_settings` 字段级覆盖；纯函数 normalize/merge；`WebhookAlertDelivery` 去重表；评估挂 `run-due-deliveries` 置 dead 后 + `POST /run-alert-eval`；`paused_reason` 列；pref `webhook_delivery_alert`；FE 纯函数 merge/mute；CLI 钉 1.41.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest；alembic。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E58；中文 docs；CLI **1.41.0**
- ADR D1–D7；Q1a–Q6a 全关
- formula 永不 emit；告警路径不 `fire_webhooks`；不改 E51 pack/HMAC、E55 Insights、E56 SLA
- 非目标见 design §2
- `WINDOW_HOURS_MIN=1` `WINDOW_HOURS_MAX=168`；`DEFAULT_WINDOW_HOURS=24`；`DEFAULT_DEAD_THRESHOLD=10`
- rule_kind：`dead_window` | `auto_disable`
- WS `enabled=false` 总闸：任何 scope 不告警（Q2a）

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e57-webhook-dead-letter-alerts.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E57-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e57-webhook-dead-letter-alerts.md \
  docs/superpowers/acceptances/2026-11-05-E57-acceptance.md
git commit -m "docs(E57): plan + acceptance skeleton"
```

---

### Task 2 — A+C：normalize/merge 纯函数 + models + alembic + pref（TDD）

**Files:**
- Create: `backend/opentask/services/workspace_webhook/alert_settings.py`
- Create: `backend/opentask/models/webhook_alert_delivery/model.py` + `__init__.py`
- Modify: `backend/opentask/models/workspace/model.py` — `webhook_alert_settings` JSON nullable
- Modify: `backend/opentask/models/workspace_webhook/model.py` — `alert_settings` JSON + `paused_reason` String nullable
- Modify: `backend/opentask/models/notification_preference/model.py` — `webhook_delivery_alert` bool default True；PREF_KEYS + TYPE_TO_PREF_KEY
- Create: `backend/alembic/versions/2026_11_05_4200-p2e3f4a5b6c0_webhook_dead_letter_alerts.py`（revises `o1d2e3f4a5b9`）
- Modify: `backend/opentask/models/__init__.py` — export
- Create: `backend/tests/unit/test_e57_alert_settings.py`

**Interfaces:**
- Produces:
  - `DEFAULT_ALERT_SETTINGS = {enabled:False, windowHours:24, deadThreshold:10, consecutiveDeadThreshold:None, autoDisable:False, muteUntil:None}`
  - `normalize_alert_settings(raw, *, partial=False) -> dict`
    - partial=True：仅校验出现的字段（钩覆盖）；空/None → `{}` 或 None（全继承）
    - 完整：补默认；enabled bool；windowHours int ∈[1,168]；deadThreshold≥1；consecutiveDeadThreshold null|int≥1；autoDisable bool；muteUntil null|ISO datetime
    - 非法 → `ValueError`
  - `merge_alert_settings(ws_raw, hook_raw=None) -> dict` — normalize WS（完整）再字段覆盖 hook（partial）；**不**改写 WS 总闸语义（调用方另检）
  - `is_muted(settings, *, now=None) -> bool`
  - `bucket_for(window_hours, *, now=None) -> str` — `str(floor(unix / (windowHours*3600)))`
  - `count_consecutive_dead(statuses_newest_first: list[str]) -> int` — 遇 success* 打断
  - Alembic：WS 列 + hook 列 + paused_reason + `webhook_alert_deliveries` 表 + pref 列；SQLite 友好
  - `WebhookAlertDelivery`：unique `(workspace_id, webhook_id_key, rule_kind, bucket)` 其中 webhook_id_key = webhook_id or `""`

- [ ] **Step 1: 红测** `backend/tests/unit/test_e57_alert_settings.py`

```python
"""E57: alert settings normalize/merge/mute/bucket (TDD)."""
from __future__ import annotations
from datetime import datetime, timedelta
import pytest
from opentask.services.workspace_webhook.alert_settings import (
    DEFAULT_ALERT_SETTINGS,
    WINDOW_HOURS_MAX,
    WINDOW_HOURS_MIN,
    bucket_for,
    count_consecutive_dead,
    is_muted,
    merge_alert_settings,
    normalize_alert_settings,
)

def test_normalize_defaults_and_rejects():
    out = normalize_alert_settings(None)
    assert out["enabled"] is False
    assert out["windowHours"] == 24
    assert out["deadThreshold"] == 10
    assert out["consecutiveDeadThreshold"] is None
    assert out["autoDisable"] is False
    assert out["muteUntil"] is None
    with pytest.raises(ValueError):
        normalize_alert_settings({"windowHours": 0})
    with pytest.raises(ValueError):
        normalize_alert_settings({"windowHours": WINDOW_HOURS_MAX + 1})
    with pytest.raises(ValueError):
        normalize_alert_settings({"deadThreshold": 0})
    with pytest.raises(ValueError):
        normalize_alert_settings({"muteUntil": "not-iso"})
    with pytest.raises(ValueError):
        normalize_alert_settings("nope")

def test_partial_overlay_and_merge():
    assert normalize_alert_settings(None, partial=True) is None
    assert normalize_alert_settings({}, partial=True) is None
    part = normalize_alert_settings({"deadThreshold": 3, "enabled": True}, partial=True)
    assert part == {"deadThreshold": 3, "enabled": True}
    merged = merge_alert_settings({"enabled": True, "windowHours": 24, "deadThreshold": 10}, {"deadThreshold": 3})
    assert merged["enabled"] is True and merged["deadThreshold"] == 3
    assert merged["windowHours"] == 24

def test_mute_bucket_consecutive():
    now = datetime(2026, 11, 5, 12, 0, 0)
    assert is_muted({"muteUntil": (now + timedelta(hours=1)).isoformat()}, now=now) is True
    assert is_muted({"muteUntil": (now - timedelta(hours=1)).isoformat()}, now=now) is False
    assert is_muted({"muteUntil": None}, now=now) is False
    b1 = bucket_for(24, now=now)
    b2 = bucket_for(24, now=now + timedelta(hours=25))
    assert b1 != b2
    assert count_consecutive_dead(["dead", "dead", "success", "dead"]) == 2
    assert count_consecutive_dead(["success"]) == 0
    assert WINDOW_HOURS_MIN == 1 and DEFAULT_ALERT_SETTINGS["enabled"] is False
```

- [ ] **Step 2: 跑红** → FAIL（缺符号）
- [ ] **Step 3: 最小实现** + models + alembic + pref 列/映射
- [ ] **Step 4: 绿** + commit `feat(E57): alert settings normalize + alembic + pref`

---

### Task 3 — B：评估器 + API + run-due 挂钩 + autoDisable（TDD）

**Files:**
- Create: `backend/opentask/services/workspace_webhook/alerts.py` — eval / notify / dedup / auto-disable
- Modify: `backend/opentask/services/workspace_webhook/service.py`
  - `serialize_webhook` 含 `alertSettings`/`pausedReason`
  - `update`：`alert_settings`/`set_alert_settings`；`enabled=True` → 清 `paused_reason`
  - `run_due_deliveries`：某条变 dead 后 `evaluate_after_dead(workspace_id, webhook_id)`
  - `get/set_ws_alert_settings`；`run_alert_eval`
  - `list_dead_letter` 附 `pausedReason` / `autoDisabled`
- Modify: `backend/opentask/api/webhooks/router.py`
  - `GET/PATCH /api/webhooks/alerts`（WS；`?webhook_id=` 钩覆盖）
  - `POST /api/webhooks/alerts/mute` `{until}` / `POST .../unmute`
  - `POST /api/webhooks/run-alert-eval`
  - WebhookUpdate 加 `alertSettings` / `setAlertSettings`
- Modify: `backend/opentask/services/notification/service.py` — serialize 含新 pref（已随 PREF_KEYS）
- Create: `backend/tests/api/test_e57_webhook_dead_letter_alerts.py`

**Interfaces:**
- `evaluate_webhook_alerts(db, *, workspace_id, webhook_id=None, now=None) -> dict`
  - 若 webhook_id：评估该钩 effective + WS 汇总
  - 若 None：扫全部 hooks + WS 汇总（run-alert-eval）
  - 总闸关闭 / muted → skip
  - dead 计数达阈值 → try_claim_dedup(`dead_window`) → 成功则 notify owners `webhook_dead_letter_alert`
  - autoDisable 硬顶（consecutive 优先若设，否则 window deadThreshold）→ disable + paused_reason + try_claim(`auto_disable`) → `webhook_auto_disabled`
  - **不**调用 `fire_webhooks`
- mute：写 WS settings.muteUntil（或 hook overlay）

- [ ] **Step 1: 红测** API 用例：opt-in off 不告警；threshold 边界；同桶去重；mute；autoDisable；跨租户 404；非法 400；spy 无 fire_webhooks；WEBHOOK_EVENTS 仍 14
- [ ] **Step 2–4:** 实现 → 绿 → commit `feat(E57): alert eval + API + autoDisable`

---

### Task 4 — D：FE 告警折叠 + 停用标签 + vitest

**Files:**
- Modify: `frontend/src/service/api/webhooks.ts` — types + normalize/merge/mute helpers + API
- Modify: `frontend/src/service/api/webhooks.test.ts`
- Modify: `frontend/src/service/api/notif-prefs.ts` + test — `webhook_delivery_alert`
- Modify: `frontend/src/views/settings/webhooks/index.vue` — 「死信告警」折叠；死信行「已自动停用」+ 一键启用

- [ ] **Step 1: 红测** merge inherit / mute 期内 `isAlertPending` false
- [ ] **Step 2–4:** 实现 → vitest 绿 → commit `feat(E57): FE alert settings + auto-disabled badge`

---

### Task 5 — E：CLI 1.41.0

**Files:**
- Bump：`VERSION` / `__init__.py` / `opentask/__init__.py` / `opentask_cli.py` / `setup.py` / `pyproject.toml` → **1.41.0**；全仓历史 `1.40.0` 断言 → `1.41.0`
- Modify: `opentask/core/webhook.py` — `alerts` group show|set|mute|unmute；`run-alert-eval`
- Modify: `opentask/utils/api_client.py` — 对应 methods
- Create: `tests/test_e57_webhook_alerts.py`

- [ ] 红测 help + version → 实现 → 绿 → commit `feat(E57): CLI 1.41.0 alerts + run-alert-eval`

---

### Task 6 — 门禁 + acceptance tip

- BE full + 定向 E57+E54+E51/E44；CLI；FE vitest+build
- 记 flake `test_user_search` 若现
- 确认 pins 全 **1.41.0**
- 填 acceptance tip SHA；commit；**STOP**；不 push；不自开 E58

---

## Self-review
- A–F / D1–D7 / Q1a–Q6a 均有 task
- 无 placeholder
- CLI 1.41.0 全钉
