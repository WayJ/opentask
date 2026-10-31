#!/bin/bash
# ============================================
# OpenTask 数据库初始化脚本
# ============================================

set -e

echo "========================================"
echo "OpenTask 数据库初始化"
echo "========================================"
echo ""

# 检查 Docker 容器是否运行
if ! docker ps | grep -q "opentask-mysql"; then
    echo "❌ MySQL 容器未运行"
    echo "请先启动 MySQL 容器:"
    echo "  docker run -d --name opentask-mysql \\"
    echo "    -e MYSQL_ROOT_PASSWORD=<你的 root 密码> \\"
    echo "    -e MYSQL_DATABASE=opentask \\"
    echo "    -e MYSQL_USER=<数据库用户> \\"
    echo "    -e MYSQL_PASSWORD=<数据库密码> \\"
    echo "    -p 3306:3306 \\"
    echo "    mysql:8.0"
    exit 1
fi

# 数据库凭据：优先取环境变量，未设置时回退到本地开发默认值
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root123}"

echo "✅ MySQL 容器运行中"
echo ""

# 执行初始化脚本
echo "📝 正在初始化数据库..."
docker exec opentask-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" opentask < init_database.sql

echo ""
echo "========================================"
echo "✅ 数据库初始化完成！"
echo "========================================"
echo ""
echo "📊 表列表:"
docker exec opentask-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" opentask -e "SHOW TABLES;" 2>&1 | grep -v "warning"
echo ""
echo "👤 默认用户:"
echo "   用户名: admin"
echo "   密码: 123456"
echo ""
echo "🔗 连接信息:"
echo "   主机: 127.0.0.1:3306"
echo "   数据库: opentask"
echo ""
