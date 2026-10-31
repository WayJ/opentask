#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查并创建 repositories 表"""
import asyncio
import sys

# 设置 UTF-8 输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from sqlalchemy import text
from opentask.repositories.base import SessionCreator

async def check_and_create_repositories_table():
    """检查并创建 repositories 表"""
    async with SessionCreator() as db:
        try:
            # 检查表是否存在
            result = await db.execute(text("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'opentask'
                AND TABLE_NAME = 'repositories'
            """))

            if result.fetchone():
                print('✅ repositories 表已存在')
                return

            # 创建表
            print('正在创建 repositories 表...')

            await db.execute(text("""
                CREATE TABLE repositories (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    url VARCHAR(500) NOT NULL,
                    local_path TEXT,
                    project_id VARCHAR(36) NOT NULL,
                    requirement_id VARCHAR(255),
                    branch VARCHAR(255) NOT NULL DEFAULT 'main',
                    provider VARCHAR(50) NOT NULL DEFAULT 'custom',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    status VARCHAR(50) NOT NULL DEFAULT 'idle',
                    auth_token TEXT,
                    ssh_key_id VARCHAR(255),
                    last_clone_at DATETIME,
                    last_pull_at DATETIME,
                    last_commit VARCHAR(255),
                    error_message TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    INDEX idx_repositories_project_id (project_id),
                    INDEX idx_repositories_requirement_id (requirement_id),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE
                )
            """))

            await db.commit()
            print('✅ repositories 表创建成功')

        except Exception as e:
            await db.rollback()
            print(f'❌ 错误: {e}')
            raise

if __name__ == '__main__':
    asyncio.run(check_and_create_repositories_table())
