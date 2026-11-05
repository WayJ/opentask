#!/usr/bin/env bash
# E14 CLI 冒烟：对着本地 BE :7377
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
API="${OT_API:-http://127.0.0.1:7377}"
USER="${OT_USER:-smoke_way}"
PASS="${OT_PASS:-SmokeTest123!}"
OT=(uv run opentask --api-url "$API")

echo "== health =="
curl -sf "$API/healthcheck" >/dev/null

echo "== login =="
"${OT[@]}" login -U "$USER" -P "$PASS" >/dev/null

echo "== workspace list/use =="
WS_JSON="$("${OT[@]}" --json workspace list)"
WS_ID=$(python3 -c "import json,sys; d=json.load(sys.stdin); rows=(d.get('data') or {}).get('rows') or d.get('rows') or []; print(rows[0]['id'] if rows else '')" <<<"$WS_JSON")
test -n "$WS_ID"
"${OT[@]}" workspace use "$WS_ID" >/dev/null
echo "workspace=$WS_ID"

echo "== project create/list =="
PROJ="$("${OT[@]}" --json project create -n "E14 Smoke $(date +%s)")"
python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('success') is True or d.get('id'), d; print('project', (d.get('data') or d).get('id'))" <<<"$PROJ"
"${OT[@]}" --json project list | python3 -c "import json,sys; d=json.load(sys.stdin); rows=d.get('rows') or []; assert len(rows)>=1, d; print('projects', len(rows))"

echo "== issue create/show KEY-N =="
ISSUE="$("${OT[@]}" --json issue create --type feature -t "E14 CLI smoke $(date +%s)")"
CODE=$(python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('success') is True, d; print((d.get('data') or {}).get('issue_code') or '')" <<<"$ISSUE")
test -n "$CODE"
"${OT[@]}" --json issue show "$CODE" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('success') is not False; print('show', '$CODE')"

echo "== cycle/label/triage =="
"${OT[@]}" --json cycle list >/dev/null
"${OT[@]}" --json label list >/dev/null
"${OT[@]}" --json triage list >/dev/null

echo "== inbox/favorite/view/member/initiative/doc =="
"${OT[@]}" --json inbox list >/dev/null
"${OT[@]}" --json favorite list >/dev/null
"${OT[@]}" --json view list >/dev/null
"${OT[@]}" --json member list >/dev/null
"${OT[@]}" --json initiative list >/dev/null
# doc 需 parent；冒烟只验证 help 可解析
"${OT[@]}" doc list --help >/dev/null

echo "E14 smoke OK"
