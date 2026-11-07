"""Authenticated, stateless MCP transport for OpenTask's ontology."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user.model import UserModel
from opentask.config import config
from opentask.services.ontology.catalog import Page, TOOLS, tool_definitions
from opentask.services.ontology.service import OntologyService
from .dependencies import get_oauth_session, require_oauth_token
from .metadata import mcp_challenge
from .read_api import read_tasks

router = APIRouter()


class LegacyList(Page):
    limit: int = Field(50, ge=1, le=50)


LEGACY_TOOL = {
    "name": "list_issues",
    "description": "List visible issues using the legacy task representation. For native issue states, filters and relationships use search_objects with object_type=Issue.",
    "inputSchema": LegacyList.model_json_schema(),
    "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
}


def rpc_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def tool_result(data, *, is_error=False):
    data = jsonable_encoder(data)
    return {
        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
        "structuredContent": data,
        "isError": is_error,
    }


def ontology_error(error):
    code = {400: "INVALID_ARGUMENT", 403: "INSUFFICIENT_SCOPE", 404: "OBJECT_NOT_FOUND"}[error.status_code]
    if error.status_code == 403 and not (isinstance(error.detail, dict) and error.detail.get("error") == "insufficient_scope"):
        code = "PERMISSION_DENIED"
    return tool_result({"error": {"code": code, "status": error.status_code, "detail": error.detail}}, is_error=True)


@router.post("/mcp")
async def mcp(
    request: Request,
    identity: tuple[dict, UserModel] = Depends(require_oauth_token),
    session: AsyncSession = Depends(get_oauth_session),
):
    payload, _user = identity
    # RFC 8707 资源令牌不可用于其他 MCP 服务；旧预注册客户端仍兼容历史令牌。
    if payload.get("client_id") and payload.get("aud") != config.frontend_base_url.rstrip("/") + "/mcp":
        raise HTTPException(401, detail="令牌受众不匹配", headers={"WWW-Authenticate": mcp_challenge()})
    try:
        message = await request.json()
    except (ValueError, UnicodeDecodeError):
        return rpc_error(None, -32700, "Parse error")
    if (
        not isinstance(message, dict)
        or message.get("jsonrpc") != "2.0"
        or not isinstance(message.get("method"), str)
        or ("params" in message and not isinstance(message["params"], dict))
        or ("id" in message and type(message["id"]) not in (str, int, type(None)))
    ):
        return rpc_error(None, -32600, "Invalid Request")
    method = message["method"]
    request_id = message.get("id")
    if "id" not in message:
        return Response(status_code=202)
    service = OntologyService(session, identity)
    if method == "initialize":
        result = {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "opentask", "version": "1.1.0"},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": ([LEGACY_TOOL] if "read:tasks" in service.scopes else []) + tool_definitions()}
    elif method == "tools/call":
        params = message.get("params", {})
        name = params.get("name")
        if not isinstance(name, str) or name not in {*TOOLS, "list_issues"}:
            return rpc_error(request_id, -32602, "Unknown tool")
        args = params.get("arguments", {})
        try:
            model = LegacyList if name == "list_issues" else TOOLS[name][0]
            arguments = model.model_validate(args)
        except ValidationError:
            error = HTTPException(400, detail="Invalid tool arguments; consult tools/list inputSchema")
            if name == "list_issues":
                raise error
            return {"jsonrpc": "2.0", "id": request_id, "result": ontology_error(error)}
        if name == "list_issues":
            service.require_type("Issue")
            data = await read_tasks(
                status=None, limit=arguments.limit, offset=arguments.offset, payload_and_user=identity, session=session
            )
        else:
            try:
                data = await service.execute(name, arguments)
            except HTTPException as error:
                if error.status_code not in (400, 403, 404):
                    raise
                return {"jsonrpc": "2.0", "id": request_id, "result": ontology_error(error)}
        result = tool_result(data)
    else:
        return rpc_error(request_id, -32601, "Method not found")
    return {"jsonrpc": "2.0", "id": request_id, "result": result}
