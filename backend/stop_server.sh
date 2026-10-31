#!/bin/bash
# 停止后端服务

if [ -f .server.pid ]; then
    PID=$(cat .server.pid)
    echo "[*] 停止服务 (PID: $PID)..."
    kill $PID
    rm .server.pid
    echo "[+] 服务已停止"
else
    echo "[!] 未找到 PID 文件"
    echo "    手动停止: pkill -f 'uvicorn opentask.main:app'"
fi
