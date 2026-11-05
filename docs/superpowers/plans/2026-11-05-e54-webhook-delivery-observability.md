# E54 Plan：Webhook 投递可观测 mid-thick — stats + dead-letter · CLI 1.38.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`7dc7f56` · 分支 `sprint/E54-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e54-webhook-delivery-observability-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E55**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Owner 可查看按钩子/WS 汇总的投递指标（window 内计数 + successRate + 可选 latency p50/p95）；跨钩子死信箱浏览 `status=dead` 并单条/批量重试（复用 E44）；FE 设置页顶栏指标卡 + 死信箱；CLI **1.38.0**；无 dismiss / 告警 / 扩 pack / formula emit。

**Architecture:** 纯函数扫既有 `WebhookDeliveryLog`（无新表）；挂现有 webhooks router（`/stats`、`/dead-letter` 注册在 `/{id}` 之前）；bulk retry 逐条复用 `retry_delivery`；FE 在 `settings/webhooks` 加厚；CLI 钉 1.38.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E55；中文 docs；CLI **1.38.0**
- ADR D1–D6；Q1a–Q6a 全关（计数+成功率必做；latency 若列已有则做；分母含 pending_retry；bulk cap 50；无 dismiss；默认 7d；CLI 挂 webhook 组）
- formula 永不 emit；不扩 E51 pack；不改 E52 Activity / E53 SLA；HMAC/fire 契约不变；无 Redis/cron
- 非目标见 design §2
- `BULK_RETRY_CAP = 50`；`DEFAULT_WINDOW = "7d"`；windows = `24h|7d|30d`

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e54-webhook-delivery-observability.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E54-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e54-webhook-delivery-observability.md \
  docs/superpowers/acceptances/2026-11-05-E54-acceptance.md
git commit -m "docs(E54): plan + acceptance skeleton"
```

---

### Task 2 — A：stats 纯函数（TDD）

**Files:**
- Create: `backend/opentask/services/workspace_webhook/stats.py`
- Create: `backend/tests/unit/test_e54_webhook_stats.py`

**Interfaces:**
- Produces:
  - `STAT_WINDOWS = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}`
  - `DEFAULT_WINDOW = "7d"`
  - `BULK_RETRY_CAP = 50`
  - `parse_window(raw: str | None) -> str` — 空/None → `DEFAULT_WINDOW`；非法 → `ValueError("invalid_window")`
  - `window_since(window: str, *, now: datetime | None = None) -> datetime`
  - `success_rate(success: int, dead: int, pending_retry: int) -> float | None` — Q2a 分母=三者之和；分母0 → `None`
  - `percentile_nearest_rank(sorted_vals: list[int], p: float) -> int | None` — 空 → None；p in (0,1]
  - `aggregate_totals(rows: list[dict]) -> dict` — 输入每项至少 `{status, latencyMs?}`；输出  
    `{success, pending_retry, dead, attempts, successRate, latencyMs?: {p50,p95}}`  
    - `attempts` = len(rows)（窗口内行数）  
    - status 缺失时：若 `success` True → success，否则 pending_retry（对齐 serialize）  
    - latency：仅收集非 None `latencyMs`；有值则算 p50/p95，否则省略 `latencyMs` 键

- [ ] **Step 1: 红测**

```python
"""E54: webhook delivery stats pure helpers (TDD)."""
from __future__ import annotations
from datetime import datetime, timedelta
import pytest
from opentask.services.workspace_webhook.stats import (
    BULK_RETRY_CAP,
    DEFAULT_WINDOW,
    STAT_WINDOWS,
    aggregate_totals,
    parse_window,
    percentile_nearest_rank,
    success_rate,
    window_since,
)

def test_parse_window_default_and_whitelist():
    assert parse_window(None) == DEFAULT_WINDOW == "7d"
    assert parse_window("") == "7d"
    assert parse_window("24h") == "24h"
    assert parse_window("30d") == "30d"
    with pytest.raises(ValueError, match="invalid_window"):
        parse_window("1h")
    assert set(STAT_WINDOWS) == {"24h", "7d", "30d"}
    assert BULK_RETRY_CAP == 50

def test_window_since_offsets():
    now = datetime(2026, 11, 5, 12, 0, 0)
    assert window_since("24h", now=now) == now - timedelta(hours=24)
    assert window_since("7d", now=now) == now - timedelta(days=7)
    assert window_since("30d", now=now) == now - timedelta(days=30)

def test_success_rate_q2a_includes_pending():
    assert success_rate(8, 1, 1) == 0.8
    assert success_rate(0, 0, 0) is None
    assert success_rate(0, 2, 0) == 0.0

def test_percentile_and_aggregate():
    assert percentile_nearest_rank([], 0.5) is None
    assert percentile_nearest_rank([10, 20, 30, 40], 0.5) == 20
    rows = [
        {"status": "success", "latencyMs": 100},
        {"status": "success", "latencyMs": 200},
        {"status": "dead", "latencyMs": 50},
        {"status": "pending_retry", "latencyMs": None},
        {"status": None, "success": True, "latencyMs": 150},
    ]
    tot = aggregate_totals(rows)
    assert tot["success"] == 3
    assert tot["dead"] == 1
    assert tot["pending_retry"] == 1
    assert tot["attempts"] == 5
    assert tot["successRate"] == 0.6
    assert tot["latencyMs"]["p50"] is not None
    assert tot["latencyMs"]["p95"] is not None
    # no latency → omit key
    bare = aggregate_totals([{"status": "success"}, {"status": "dead"}])
    assert "latencyMs" not in bare
```

- [ ] **Step 2:** Run → FAIL (module missing)
- [ ] **Step 3:** 实现 `stats.py` 最小代码
- [ ] **Step 4:** Run → PASS；commit

```bash
git add backend/opentask/services/workspace_webhook/stats.py backend/tests/unit/test_e54_webhook_stats.py
git commit -m "feat(E54): webhook stats pure helpers (TDD)"
```

---

### Task 3 — A+B：Service 查询 + API 路由（TDD）

**Files:**
- Modify: `backend/opentask/services/workspace_webhook/service.py` — 增 `delivery_stats` / `list_dead_letter` / `bulk_retry_dead_letter`
- Modify: `backend/opentask/api/webhooks/router.py` — 在 `/{webhook_id}` **之前**挂：
  - `GET /stats?window=`
  - `GET /dead-letter?limit=&cursor=&webhook_id=&event=`
  - `POST /dead-letter/retry` body `{deliveryLogIds: string[]}`
  - `GET /{webhook_id}/stats?window=`（可与现有 `/{id}` 共存）
- Create: `backend/tests/api/test_e54_webhook_delivery_observability.py`

**Interfaces:**
- Consumes: Task2 helpers；既有 `retry_delivery` / `serialize_delivery` / `require_owner|reader`
- Produces service methods:
  - `async def delivery_stats(self, *, workspace_id, window: str | None = None, webhook_id: str | None = None) -> dict`
    - parse_window；非法 → HTTP 400 `invalid_window`
    - 若 `webhook_id`：先 `_get_or_404`（跨租户 404）
    - 扫 `WebhookDeliveryLog`：`workspace_id` + `created_at >= since`；可选 `webhook_id`
    - 返回：
      ```
      {
        "window": "7d",
        "totals": {success, pending_retry, dead, attempts, successRate, latencyMs?},
        "byWebhook": [  # 仅 WS 级（webhook_id is None）
          {"webhookId", "name", "url", "totals": {...}}
        ]  # 单钩子省略 byWebhook 或空
      }
      ```
    - `byWebhook`：按 hook 分组；无日志的 hook 可不出现；分解之和 = totals（success/dead/pending/attempts）
  - `async def list_dead_letter(self, *, workspace_id, limit=50, cursor=None, webhook_id=None, event=None) -> dict`
    - 仅 `status == "dead"`；`order_by created_at.desc(), id.desc()`；limit clamp 1..100 默认 50
    - cursor：复用 `encode_activity_cursor` / `decode_activity_cursor`（`created_at|id`）；非法 cursor → 400
    - 可选 filter webhook_id / event_type；跨租户 webhook 过滤若 id 不属本 WS → 空列表（或 404 若显式校验 hook）——**拍板：显式 webhook_id 时 `_get_or_404`**
    - 返回 `{rows: [serialize_delivery + webhookName?], nextCursor, total?}`；`webhookName` join hook.name
  - `async def bulk_retry_dead_letter(self, *, workspace_id, delivery_log_ids: list[str]) -> dict`
    - 空 → 400；`len > BULK_RETRY_CAP` → 400 `bulk_retry_cap`
    - 去重保序；逐条：查 log（须本 WS + status 可为 dead/pending_retry + 有 payload）；调 `retry_delivery`
    - per-id：`{deliveryLogId, ok: bool, error?: str, result?: dict}`；总返回 `{results: [...], succeeded, failed}`

- Router:
  - stats / dead-letter list：`require_reader`
  - bulk retry：`require_owner`
  - Body model：`class DeadLetterRetryBody(BaseModel): deliveryLogIds: list[str] = Field(..., min_length=1)`

- [ ] **Step 1: 红测**（API 集成）

```python
"""E54：Webhook delivery observability — stats + dead-letter."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from opentask.models.workspace_webhook.model import WEBHOOK_EVENTS, WebhookDeliveryLog
from opentask.repositories.base import SessionCreator

# reuse _register/_auth/_FakeResp helpers like E44

@pytest.mark.asyncio
async def test_stats_default_window_7d_and_illegal(test_client: AsyncClient):
    user = await _register(test_client, "e54_st")
    h = _auth(user["token"], user["workspaceId"])
    # create hook + seed logs via direct DB
    ...
    resp = await test_client.get("/api/webhooks/stats", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["window"] == "7d"
    assert "successRate" in data["totals"]
    bad = await test_client.get("/api/webhooks/stats", headers=h, params={"window": "1h"})
    assert bad.status_code == 400

@pytest.mark.asyncio
async def test_stats_by_webhook_sums_and_cross_tenant_404(test_client: AsyncClient):
    ...

@pytest.mark.asyncio
async def test_dead_letter_list_only_dead_filter_retry(test_client: AsyncClient):
    ...

@pytest.mark.asyncio
async def test_bulk_retry_cap_and_partial(test_client: AsyncClient):
    ...

@pytest.mark.asyncio
async def test_stats_read_no_emit(test_client: AsyncClient):
    ...
    with patch("opentask.services.workspace_webhook.service.fire_webhooks", new_callable=AsyncMock) as spy:
        await test_client.get("/api/webhooks/stats", headers=h)
        await test_client.get("/api/webhooks/dead-letter", headers=h)
        spy.assert_not_called()

def test_webhook_events_unchanged_no_new_names():
    # E54 不扩 pack；E51 五事件仍在
    assert "issue.cycle_changed" in WEBHOOK_EVENTS
    assert len(WEBHOOK_EVENTS) == 14
```

- [ ] **Step 2–4:** 红→绿→commit

```bash
git commit -m "feat(E54): webhook stats + dead-letter API (TDD)"
```

---

### Task 4 — C：FE helpers + 顶栏/死信箱（TDD）

**Files:**
- Modify: `frontend/src/service/api/webhooks.ts` — types + fetchers + helpers  
  `normalizeStatsPayload` / `filterDeadLetterRows` / `STAT_WINDOWS` / `DEFAULT_STAT_WINDOW`
- Modify: `frontend/src/service/api/webhooks.test.ts` — vitest
- Modify: `frontend/src/views/settings/webhooks/index.vue` — 顶栏 window 切换 + successRate/dead 卡；死信箱 Modal/抽屉（过滤 + 单条/批量重试）；保留 E44/E51 详情

**Interfaces:**
```ts
export const STAT_WINDOWS = ['24h', '7d', '30d'] as const;
export const DEFAULT_STAT_WINDOW = '7d';
export type StatWindow = (typeof STAT_WINDOWS)[number];
export interface DeliveryTotals {
  success: number; pending_retry: number; dead: number; attempts: number;
  successRate: number | null;
  latencyMs?: { p50: number; p95: number };
}
export interface WebhookStatsPayload {
  window: StatWindow;
  totals: DeliveryTotals;
  byWebhook?: Array<{ webhookId: string; name?: string | null; url?: string; totals: DeliveryTotals }>;
}
export function normalizeStatsPayload(raw: any): WebhookStatsPayload { ... }
export function filterDeadLetterRows<T extends { webhookId: string; eventType: string }>(
  rows: T[], webhookId: string | 'all', eventType: string | 'all'
): T[] { ... }
export function fetchWebhookStats(window?: string) { ... }
export function fetchWebhookStatsById(id: string, window?: string) { ... }
export function fetchDeadLetter(params?: { limit?: number; cursor?: string; webhook_id?: string; event?: string }) { ... }
export function fetchBulkRetryDeadLetter(deliveryLogIds: string[]) { ... }
```

- [ ] **Step 1: 红测** vitest normalize / filter
- [ ] **Step 2–4:** 实现 helpers → 绿 → 改 vue → commit

```bash
git commit -m "feat(E54): FE webhook stats bar + dead-letter drawer"
```

---

### Task 5 — D：CLI 1.38.0

**Files:**
- Bump：`pyproject.toml` / `__init__.py` / `setup.py` / `VERSION` / `opentask_cli.VERSION` → **1.38.0**
- 历史断言：所有 `1.37.0` → `1.38.0`（含 `v1.37.0` / `test_version_1_37_0` 函数名可改 `1_38_0`）
- Modify: `opentask/utils/api_client.py` — `get_webhook_stats` / `list_webhook_dead_letter` / `bulk_retry_webhook_dead_letter`
- Modify: `opentask/core/webhook.py` — `stats` 命令 + `dead-letter` 组（`list` / `retry`）
- Create: `tests/test_e54_webhook_observability.py`

**CLI:**
```
webhook stats [--webhook-id] [--window 24h|7d|30d] [--json]
webhook dead-letter list [--webhook-id] [--event] [--json]
webhook dead-letter retry --id … (multiple) | --ids a,b [--json]
```

- [ ] **Step 1: 红测** version + help
- [ ] **Step 2–4:** bump + 命令 → 绿 → commit

```bash
git commit -m "feat(E54): CLI 1.38.0 webhook stats + dead-letter"
```

---

### Task 6 — 门禁 + acceptance tip

- BE full + targeted `test_e54*` + `test_e44*` + `test_e51*`
- CLI full（pins 全 1.38.0）
- FE vitest + `npm run build`
- 记 flake `test_user_search` 若现
- 写满 acceptance；tip SHA；`superpowers: … = ok`；**STOP**；不 push；不自开 E55

```bash
git commit -m "docs(E54): acceptance tip + gates"
```

---

## Self-review
- Spec A–E / ADR D1–D6 / Q1a–Q6a → Tasks 2–5 覆盖
- 无 placeholder；路由顺序防 `/{id}` 吞掉 `stats`/`dead-letter`
- 不改 HMAC / E51 pack / E52 / E53 / formula emit
