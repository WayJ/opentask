"""业务表 dept_id 历史回填服务（Phase 6 Task 1，spec 4.3）

7 张带部门归属快照列（dept_id）的业务表逐表回填历史数据：
requirements / issues / projects / knowledge_bases / documents / tasks / agent_tasks

回填规则：
- 只处理 dept_id IS NULL 的行（幂等：重跑 updated=0）；
- 有 created_by 列且语义为「创建用户」的表（requirements/issues/documents）
  按 created_by 匹配用户，优先级：UUID 精确 id > username > name（name 重名跳过）；
  匹配到 → 该用户主部门（user_dept.is_primary=true），无任何归属保持 NULL；
  匹配不到（'admin'/'system'/脏值/已删用户）保持 NULL 并计入 dirty 样本；
- 无 created_by 列或语义不符的表（projects/knowledge_bases/tasks/agent_tasks，
  created_by 实为 Agent 名等）不回填，全表报告 skipped_no_owner——
  历史留 NULL = 仅 ALL 数据范围可见，符合 spec 4.3 的预期行为；
- 分批处理：每表按 1000 行批次更新 + flush/commit，避免长事务大锁。
"""
import sqlalchemy
from sqlalchemy import func, select, update

from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import UserDept
from opentask.repositories.base import AsyncSession

# 显式 import 各业务模型，保证 7 张表在 DBModel.metadata 完成注册
# （部分模型不在 opentask.models.__init__ 全量导出内）
from opentask.models.requirement.model import Project, Requirement  # noqa: F401
from opentask.models.issue.model import Issue  # noqa: F401
from opentask.models.knowledge_base.model import KnowledgeBase  # noqa: F401
from opentask.models.document.model import Document  # noqa: F401
from opentask.models.task.model import Task  # noqa: F401
from opentask.models.mission_center.model import AgentTask  # noqa: F401

# 每表批次大小
BATCH_SIZE = 1000
# dirty 样本上限（前 N 条不同值）
DIRTY_SAMPLE_LIMIT = 20

# 7 张业务表（表名以 DBModel.metadata 实际为准）
BACKFILL_TABLES = (
    "requirements",
    "issues",
    "projects",
    "knowledge_bases",
    "documents",
    "tasks",
    "agent_tasks",
)


class BackfillService:
    """业务表 dept_id 历史回填"""

    def __init__(self, session: AsyncSession):
        self.session = session
        # 用户索引 / 主部门映射（backfill_dept_id 入口一次性加载）
        self._by_id: dict[str, str] = {}
        self._by_username: dict[str, str] = {}
        self._by_name: dict[str, str] = {}
        self._ambiguous_names: set[str] = set()
        self._primary_depts: dict[str, str] = {}

    @staticmethod
    def _empty_report() -> dict:
        """单表报告骨架"""
        return {
            "total_null": 0,
            "updated": 0,
            "skipped_no_dept": 0,
            "skipped_no_owner": 0,
            "skipped_ambiguous": 0,
            "skipped_dirty_count": 0,
            "dirty_samples": [],
            "table_missing": False,
        }

    async def _load_user_index(self) -> None:
        """加载用户索引：id / username（唯一索引）/ name（重名标记为歧义）"""
        name_users: dict[str, set[str]] = {}
        rows = await self.session.execute(
            select(UserModel.id, UserModel.username, UserModel.name)
        )
        for id_, username, name in rows.all():
            uid = str(id_)
            self._by_id[uid] = uid
            if username:
                # username 有唯一索引；防御性保留首个
                self._by_username.setdefault(username, uid)
            if name:
                name_users.setdefault(name, set()).add(uid)
        self._by_name = {n: next(iter(s)) for n, s in name_users.items() if len(s) == 1}
        self._ambiguous_names = {n for n, s in name_users.items() if len(s) > 1}

    async def _load_primary_depts(self) -> None:
        """加载用户主部门映射（user_dept.is_primary=true，每用户一行由应用层保证）"""
        rows = await self.session.execute(
            select(UserDept.user_id, UserDept.dept_id).where(UserDept.is_primary == True)  # noqa: E712
        )
        for user_id, dept_id in rows.all():
            self._primary_depts.setdefault(str(user_id), str(dept_id))

    def _resolve(self, created_by: str | None) -> tuple[str, str | None]:
        """created_by → (分类, 部门 ID)

        分类：dept（可回填）/ no_dept（匹配到用户但无主部门）/
        no_owner（值为空）/ ambiguous（name 重名）/ dirty（匹配不到）
        """
        value = created_by.strip() if isinstance(created_by, str) else ""
        if not value:
            return "no_owner", None
        # 优先级：UUID 精确 id > username > name
        user_id = self._by_id.get(value) or self._by_username.get(value)
        if user_id is None:
            if value in self._ambiguous_names:
                return "ambiguous", None
            user_id = self._by_name.get(value)
            if user_id is None:
                return "dirty", None
        dept_id = self._primary_depts.get(user_id)
        if dept_id is None:
            return "no_dept", None
        return "dept", dept_id

    async def _has_table(self, table_name: str) -> bool:
        """当前库中表是否存在（SQLite 测试库缺 mysql ENUM 表时防御）"""
        conn = await self.session.connection()
        return await conn.run_sync(
            lambda sync_conn: sqlalchemy.inspect(sync_conn).has_table(table_name)
        )

    async def _count_null(self, table: sqlalchemy.Table) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(table).where(table.c.dept_id.is_(None))
        )
        return int(result.scalar_one())

    async def _backfill_owner_table(
        self, table: sqlalchemy.Table, report: dict
    ) -> None:
        """有 created_by 列的表：keyset 分批扫描 NULL 行并按主部门回填"""
        pk = table.primary_key.columns[0]
        owner_col = table.c.created_by
        dirty_seen: set[str] = set()
        cache: dict[str | None, tuple[str, str | None]] = {}
        last_pk: str | None = None

        while True:
            query = (
                select(pk, owner_col)
                .where(table.c.dept_id.is_(None))
                .order_by(pk.asc())
                .limit(BATCH_SIZE)
            )
            if last_pk is not None:
                # keyset 翻页：跳过已处理主键（含保持 NULL 的跳过行，避免死循环）
                query = query.where(pk > last_pk)
            rows = (await self.session.execute(query)).all()
            if not rows:
                break
            last_pk = rows[-1][0]
            report["total_null"] += len(rows)

            pks_by_dept: dict[str, list] = {}
            for pk_value, created_by in rows:
                if created_by not in cache:
                    cache[created_by] = self._resolve(created_by)
                category, dept_id = cache[created_by]
                if category == "dept":
                    pks_by_dept.setdefault(dept_id, []).append(pk_value)
                    report["updated"] += 1
                elif category == "no_dept":
                    report["skipped_no_dept"] += 1
                elif category == "no_owner":
                    report["skipped_no_owner"] += 1
                elif category == "ambiguous":
                    report["skipped_ambiguous"] += 1
                else:  # dirty
                    report["skipped_dirty_count"] += 1
                    if created_by not in dirty_seen and len(dirty_seen) < DIRTY_SAMPLE_LIMIT:
                        dirty_seen.add(created_by)
                        report["dirty_samples"].append(created_by)

            # 按部门分组批量更新（每批次一次 flush/commit）
            for dept_id, pk_values in pks_by_dept.items():
                await self.session.execute(
                    update(table)
                    .where(pk.in_(pk_values))
                    .values(dept_id=dept_id)
                )
            await self.session.flush()
            await self.session.commit()

    async def backfill_dept_id(self) -> dict[str, dict]:
        """回填 7 张业务表的 dept_id 历史数据，返回逐表报告

        幂等：只处理 dept_id IS NULL 的行，重跑 updated=0。
        """
        await self._load_user_index()
        await self._load_primary_depts()

        report: dict[str, dict] = {}
        for table_name in BACKFILL_TABLES:
            entry = self._empty_report()
            report[table_name] = entry

            table = DBModel.metadata.tables.get(table_name)
            if table is None or not await self._has_table(table_name):
                # 库里没这张表（如 SQLite 测试库建不了 mysql ENUM 表）：如实上报
                entry["table_missing"] = True
                continue

            if "created_by" not in table.c:
                # projects/knowledge_bases/tasks/agent_tasks：
                # 无 created_by 或语义为 Agent 名，不回填，历史留 NULL（仅 ALL 可见）
                total = await self._count_null(table)
                entry["total_null"] = total
                entry["skipped_no_owner"] = total
                continue

            await self._backfill_owner_table(table, entry)

        return report
