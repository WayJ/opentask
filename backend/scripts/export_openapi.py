"""导出全量 OpenAPI spec 到随代码提交的产物文件。

用途：``backend/openapi.json`` 与 ``backend/openapi_current.json`` 是**随代码发布**的
spec 产物（公开仓库对外可见的接口契约）。新增/变更路由后必须重新导出，否则仓内
spec 与实现漂移（历史债 TD7）。

用法::

    cd backend && uv run python scripts/export_openapi.py

说明：
- 两个产物文件内容一致（全量 spec 的两个副本，历史沿用），一次导出同时写入；
- 导出只需 app 的路由表，不需要数据库连接；
- 若配置校验要求 ``AUTH_SECRET_KEY``（fail-closed），导出进程可用临时随机值，
  该值不写入仓库、不参与任何运行时行为。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILES = (BACKEND_ROOT / "openapi.json", BACKEND_ROOT / "openapi_current.json")


def _ensure_importable() -> None:
    """把 backend 根目录挂进 sys.path，使 `import opentask` 在脚本直跑时可用。"""
    root = str(BACKEND_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def main() -> int:
    _ensure_importable()
    # 配置校验 fail-closed：导出进程用临时随机密钥，不入库、不影响运行时
    os.environ.setdefault("AUTH_SECRET_KEY", "openapi-export-only-not-a-runtime-secret")

    from opentask.main import app  # noqa: PLC0415 - 延迟导入，确保 sys.path 已就位

    spec = app.openapi()
    payload = json.dumps(spec, ensure_ascii=False, indent=2)

    for path in OUTPUT_FILES:
        path.write_text(payload, encoding="utf-8")
        print(f"exported {path.relative_to(BACKEND_ROOT)}: {len(spec.get('paths', {}))} paths")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
