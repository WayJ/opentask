# source activate py11
# uv run uvicorn opentask.main:app --reload --port=7377
## 当前在docker容器内，对volume挂载的工程目录无法启动reload模式，每次需要手动重启
export AUTH_SECRET_KEY="${AUTH_SECRET_KEY:-dev-only-secret-key}"
uv run uvicorn opentask.main:app --port=7377 --host=0.0.0.0 --reload
