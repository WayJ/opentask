"""
迁移脚本：将数据库中 32 位无连字符 UUID 转为 36 位带连字符格式

执行方式：
    cd backend && uv run python migrations/fix_uuid_32_to_36.py --dry-run   # 预览
    cd backend && uv run python migrations/fix_uuid_32_to_36.py             # 执行

仅影响通过 CustomUUIDType 写入的32位数据，36位数据不受影响。
"""
import argparse
import re
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymysql import connect


def add_hyphens(uuid32: str) -> str:
    """32位UUID -> 36位带连字符"""
    return f"{uuid32[0:8]}-{uuid32[8:12]}-{uuid32[12:16]}-{uuid32[16:20]}-{uuid32[20:32]}"


UUID32_PATTERN = re.compile(r'^[0-9a-f]{32}$')

# 需要迁移的表和字段
# 格式: (表名, 字段名列表)
TABLES = [
    # 使用 UUIDMixin 的表（id 字段）
    ("user", ["id"]),
    ("access_tokens", ["id"]),
    ("conversations", ["id"]),
    ("messages", ["id"]),
    ("media", ["id"]),
]

# 引用用户的外键字段（存储在 String 列中，不会是32位，但做安全检查）
USER_REF_TABLES = [
    ("issues", ["assignee_id", "reporter_id"]),
    ("issue_comments", ["user_id"]),
    ("issue_timeline", ["user_id"]),
    ("issue_reactions", ["user_id"]),
    ("issue_collections", ["creator_id"]),
    ("requirements", ["assignee_id"]),
    ("requirement_comments", ["user_id"]),
    ("rd_groups", ["director_id", "leader_id"]),
    ("rd_group_members", ["user_id"]),
    ("work_assignments", ["assignee_id"]),
    ("work_feedback", ["user_id"]),
    ("cost_projects", ["manager_id"]),
    ("access_tokens", ["user_id"]),
]


def get_connection(config):
    """获取数据库连接"""
    from opentask.config import config as app_config
    return connect(
        host=app_config.mysql_host,
        port=int(app_config.mysql_port),
        user=app_config.mysql_user,
        password=app_config.mysql_password,
        database=app_config.mysql_database,
        charset='utf8mb4',
    )


def check_and_fix(conn, table: str, columns: list[str], dry_run: bool):
    """检查并修复指定表的列"""
    cursor = conn.cursor()

    for col in columns:
        # 查找32位UUID（无连字符）
        sql = f"SELECT `{col}` FROM `{table}` WHERE CHAR_LENGTH(`{col}`) = 32 AND `{col}` REGEXP '^[0-9a-f]{32}$'"
        cursor.execute(sql)
        rows = cursor.fetchall()

        if not rows:
            print(f"  {table}.{col}: 无32位数据，跳过")
            continue

        print(f"  {table}.{col}: 发现 {len(rows)} 条32位记录")

        if dry_run:
            for (old_val,) in rows[:3]:
                print(f"    {old_val} -> {add_hyphens(old_val)}")
            if len(rows) > 3:
                print(f"    ... 共 {len(rows)} 条")
        else:
            for (old_val,) in rows:
                new_val = add_hyphens(old_val)
                update_sql = f"UPDATE `{table}` SET `{col}` = %s WHERE `{col}` = %s"
                cursor.execute(update_sql, (new_val, old_val))
            print(f"    已修复 {len(rows)} 条")

    cursor.close()


def main():
    parser = argparse.ArgumentParser(description="修复32位UUID为36位带连字符格式")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不执行")
    args = parser.parse_args()

    print(f"模式: {'预览' if args.dry_run else '执行'}")
    print()

    conn = get_connection(args)

    try:
        print("=== UUIDMixin 表（id 字段）===")
        for table, cols in TABLES:
            try:
                check_and_fix(conn, table, cols, args.dry_run)
            except Exception as e:
                print(f"  {table}: 跳过 ({e})")

        print()
        print("=== 用户引用字段 ===")
        for table, cols in USER_REF_TABLES:
            try:
                check_and_fix(conn, table, cols, args.dry_run)
            except Exception as e:
                print(f"  {table}: 跳过 ({e})")

        if not args.dry_run:
            conn.commit()
            print()
            print("迁移完成，已提交事务。")
        else:
            print()
            print("预览完成，使用不带 --dry-run 参数执行实际迁移。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
