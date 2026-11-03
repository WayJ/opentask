"""生成登录口令加密用的 RSA 密钥对（RSA-OAEP / 2048 位）。

用途：登录口令在提交前由前端用**公钥**加密，私钥只留在服务端——即使链路是明文
HTTP，截获的也只是解不开的密文（详见 ``opentask/utils/login_crypto.py``）。

用法::

    # 在后端容器内执行（密钥落在 DATA_DIRECTORY 下，随 data 卷持久化）
    docker compose -f docker-compose.prod.yml exec backend \
        python scripts/generate_login_keys.py

    # 打印公钥（给前端构建注入 VITE_LOGIN_PUBLIC_KEY 用）
    python scripts/generate_login_keys.py --print-public

行为：
- **幂等**：密钥已存在时默认不覆盖（覆盖会导致已构建的前端 bundle 用旧公钥，
  新前端登录会解不开）；要轮换用 ``--force``，且**必须同步重新构建前端**。
- 私钥 chmod 600，公钥 644。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from opentask.utils.login_crypto import (  # noqa: E402
    private_key_path,
    public_key_b64,
    public_key_path,
    generate_keypair,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成/查看登录口令加密密钥对")
    parser.add_argument("--force", action="store_true", help="密钥已存在时覆盖（轮换）")
    parser.add_argument("--print-public", action="store_true", help="只打印公钥（base64 SPKI DER）")
    args = parser.parse_args(argv)

    priv = private_key_path()
    pub = public_key_path()

    if args.print_public:
        b64 = public_key_b64()
        if not b64:
            print(f"公钥不存在：{pub}", file=sys.stderr)
            return 1
        print(b64)
        return 0

    if priv.is_file() and not args.force:
        print(f"私钥已存在，未改动：{priv}")
    else:
        generate_keypair(priv, pub)
        print(f"已生成密钥对：\n  私钥 {priv}（600）\n  公钥 {pub}（644）")
        if args.force:
            print("⚠ 已轮换——**必须重新构建前端**（VITE_LOGIN_PUBLIC_KEY 变了），否则新前端登录会解不开")

    b64 = public_key_b64()
    if b64:
        print(f"公钥（base64 SPKI DER，注入 VITE_LOGIN_PUBLIC_KEY）：\n{b64}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
