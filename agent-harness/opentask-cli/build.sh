#!/bin/bash
# OpenTask CLI 打包脚本

echo "🧹 清理旧文件..."
rm -rf dist build *.egg-info

echo "📦 开始打包..."
python -m build

echo "✅ 打包完成！"
echo ""
echo "构建产物："
ls -lh dist/

echo ""
echo "安装命令："
echo "  pip install dist/opentask_cli-*.whl"
