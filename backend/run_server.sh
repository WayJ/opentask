# JWT 密钥必须显式提供，禁止回退到公开默认值（生产用环境变量注入）
: "${AUTH_SECRET_KEY:?AUTH_SECRET_KEY must be set}"
uv run uvicorn opentask.main:app --port=7377 --host=0.0.0.0