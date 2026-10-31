"""添加 comments 表 is_deleted 字段"""
import asyncio
from sqlalchemy import text
from opentask.repositories.base import get_session


async def upgrade():
    """添加 is_deleted 字段到 comments 表"""
    async with get_session() as db:
        try:
            # 添加 is_deleted 字段
            await db.execute(text("""
                ALTER TABLE comments
                ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL
            """))

            # 添加索引
            await db.execute(text("""
                CREATE INDEX idx_comments_is_deleted
                ON comments(is_deleted)
            """))

            await db.commit()
            print("✅ 成功添加 is_deleted 字段和索引")

        except Exception as e:
            await db.rollback()
            print(f"❌ 迁移失败: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(upgrade())
