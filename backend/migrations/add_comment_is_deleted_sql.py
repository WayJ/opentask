"""使用 SQL 直接添加 is_deleted 字段"""
import asyncio
import pymysql
import os

async def upgrade():
    """使用 pymysql 直接执行 SQL"""
    # 从环境变量或配置文件获取数据库连接信息
    # 这里使用本地配置
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', 'opentask'),
        charset='utf8mb4'
    )

    try:
        with conn.cursor() as cursor:
            # 检查字段是否已存在
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'opentask'
                AND TABLE_NAME = 'comments'
                AND COLUMN_NAME = 'is_deleted'
            """)

            if cursor.fetchone():
                print("ℹ️  is_deleted 字段已存在，跳过迁移")
                return

            # 添加 is_deleted 字段
            print("正在添加 is_deleted 字段...")
            cursor.execute("""
                ALTER TABLE comments
                ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL
            """)
            print("✅ is_deleted 字段添加成功")

            # 添加索引
            print("正在添加索引...")
            cursor.execute("""
                CREATE INDEX idx_comments_is_deleted
                ON comments(is_deleted)
            """)
            print("✅ 索引创建成功")

        conn.commit()
        print("\n✅ 迁移完成！")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(upgrade())
