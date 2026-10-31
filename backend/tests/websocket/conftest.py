"""
WebSocket 测试配置

避免运行数据库迁移，使用独立的测试配置
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# 禁用自动迁移（在根 conftest.py 中）
@pytest.fixture(scope="session", autouse=True)
def skip_database_migrations():
    """跳过数据库迁移"""
    # 这个 fixture 会覆盖根 conftest.py 中的 apply_migrations
    yield
