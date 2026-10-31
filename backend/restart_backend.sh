#!/bin/bash
# 查找并终止占用 7377 端口的进程
PID=$(netstat -ano | grep :7377 | grep LISTENING | awk '{print $5}' | head -1)
if [ -n "$PID" ]; then
  echo "正在终止进程 $PID..."
  cmd.exe //c "taskkill /F /PID $PID" 2>/dev/null
  sleep 3
fi

# 启动后端服务
echo "启动后端服务..."
# JWT 密钥必须显式提供，禁止回退到公开默认值（生产用环境变量注入）
: "${AUTH_SECRET_KEY:?AUTH_SECRET_KEY must be set}"
cd C:/cx-glxc/opentask/backend
nohup uv run uvicorn opentask.main:app --port=7377 --host=0.0.0.0 > backend.log 2>&1 &
echo "后端服务已启动，PID: $!"
sleep 5
echo "检查服务状态..."
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:7377/api/user/me || echo "服务未就绪"
