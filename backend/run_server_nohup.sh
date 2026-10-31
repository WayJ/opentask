#!/bin/bash
# 后端服务后台运行脚本

# 日志目录
mkdir -p logs

# 启动服务（后台运行）
# JWT 密钥必须显式提供，禁止回退到公开默认值（生产用环境变量注入）
: "${AUTH_SECRET_KEY:?AUTH_SECRET_KEY must be set}"
nohup uv run uvicorn opentask.main:app --port=7377 --host=0.0.0.0 > logs/server.log 2>&1 &

# 保存 PID
echo $! > .server.pid

echo "[+] 后端服务已在后台启动"
echo "    PID: $!"
echo "    日志: logs/server.log"
echo "    查看日志: tail -f logs/server.log"
echo "    停止服务: kill $! 或 kill \$(cat .server.pid)"
