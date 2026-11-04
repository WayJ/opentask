"""GitHub-compatible PR webhook (E11-S2). Mockable; optional HMAC."""
from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.services.vcs.github_webhook import (
    extract_pr_fields,
    map_github_pr_status,
    verify_github_signature,
)
from opentask.services.vcs.service import IssueVcsService, serialize_vcs_link
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/webhooks/github", tags=["GitHub Webhooks"])


@router.post("/pull-request")
async def github_pull_request_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
):
    body = await request.body()
    secret = os.getenv("WEBHOOK_GITHUB_SECRET", "")
    if not verify_github_signature(body, x_hub_signature_256, secret):
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub signature",
        )
    try:
        payload: dict[str, Any] = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    fields = extract_pr_fields(payload)
    if not fields.get("pr_url"):
        raise HTTPException(status_code=400, detail="pull_request.html_url required")

    status_val = map_github_pr_status(
        state=str(fields.get("state") or "open"),
        merged=bool(fields.get("merged")),
        draft=bool(fields.get("draft")),
    )
    row = await IssueVcsService(session).upsert_github_pr(
        pr_url=fields["pr_url"],
        external_id=str(fields["number"]) if fields.get("number") is not None else None,
        status=status_val,
        title=fields.get("title"),
        head_ref=fields.get("head_ref"),
    )
    return success_response(
        data=serialize_vcs_link(row),
        message="webhook ingested",
    )
