"""钉钉通讯录全量同步对账服务（Phase 4 Task 2）

幂等全量对账，钉钉为准：
1. 部门：从根(1) BFS 拉全部子部门 → 按 dingtalk_dept_id upsert；
   新建 path 按 dept_service 同款算法（flush 取 id 后父path + /id）。
2. 用户：每部门拉用户 + get_user_detail → 按 dingtalk_user_id upsert
   user（新建 role=viewer、password_hash=None、username 唯一化）与
   user_dept（覆盖式，主部门取 detail 主部门或第一个）。
3. 对账（离职/删部门闭环）：
   - 本地 department 有 dingtalk_dept_id 不在钉钉集 → status=0；
   - 本地 user 有 dingtalk_user_id 不在钉钉集 → status=0 +
     TokenService.revoke_all_user_refresh（吊销全部 refresh token）。

已有用户更新只写 jnpf_name（钉钉姓名写这列），不覆盖 status/role/username。
"""
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, UserDept
from opentask.services.user_center.dingtalk.client import DingTalkClient
from opentask.services.user_center.token_service import TokenService
from opentask.services.user_center.utils import unique_username

logger = logging.getLogger(__name__)

# 钉钉根部门固定为 1（BFS 起点，本地不为其建 department 行）
_DINGTALK_ROOT_DEPT_ID = 1


class DingTalkSyncService:
    """钉钉通讯录全量同步对账（幂等）"""

    def __init__(self, session: AsyncSession, client: DingTalkClient):
        self.session = session
        self.client = client
        self.token_service = TokenService(session)

    async def sync_all(self) -> dict:
        """全量对账，返回 {depts: {created, updated, disabled}, users: {created, updated, disabled}}"""
        dept_diff = {"created": 0, "updated": 0, "disabled": 0}
        user_diff = {"created": 0, "updated": 0, "disabled": 0}

        # ---- 1. 部门 BFS：钉钉全量部门（含层级顺序，父先于子） ----
        remote_depts = await self._fetch_all_depts()

        # 本地已映射部门：dingtalk_dept_id(str) -> Department
        existing_depts = await self._load_local_depts()

        for dept in remote_depts:
            dt_id = str(dept["dept_id"])
            local = existing_depts.get(dt_id)
            if local is None:
                await self._create_dept(dept, existing_depts)
                dept_diff["created"] += 1
            else:
                if await self._update_dept(local, dept, existing_depts):
                    dept_diff["updated"] += 1
        await self.session.flush()

        # ---- 2. 用户：每部门拉用户，按 dingtalk_user_id upsert ----
        # 含根部门(1)直属用户（其 dept_id_list 若只有 1 则无本地归属，仅建用户行）
        remote_user_details = await self._fetch_all_users(
            [_DINGTALK_ROOT_DEPT_ID] + [d["dept_id"] for d in remote_depts]
        )
        existing_users = await self._load_local_users()
        # username 唯一化基准：现有全量 username + name（lower 归一化）
        existing_names = existing_users["names"]

        for userid in remote_user_details:
            detail = remote_user_details[userid]
            local = existing_users["by_dt_id"].get(userid)
            if local is None:
                await self._create_user(detail, existing_names, existing_depts)
                user_diff["created"] += 1
            else:
                if await self._update_user(local, detail, existing_depts):
                    user_diff["updated"] += 1
        await self.session.flush()

        # ---- 3. 对账：钉钉侧已删除 → 本地禁用 ----
        remote_dept_ids = {str(d["dept_id"]) for d in remote_depts}
        for dt_id, local in existing_depts.items():
            if dt_id not in remote_dept_ids and local.status == 1:
                local.status = 0
                dept_diff["disabled"] += 1

        remote_userids = set(remote_user_details)
        for userid, local in existing_users["by_dt_id"].items():
            if userid not in remote_userids and local.status == 1:
                local.status = 0
                revoked = await self.token_service.revoke_all_user_refresh(str(local.id))
                user_diff["disabled"] += 1
                logger.info(
                    f"钉钉离职对账: 禁用用户 {local.username or local.id}，"
                    f"吊销 {revoked} 个 refresh token"
                )

        await self.session.commit()
        return {"depts": dept_diff, "users": user_diff}

    # ---- 部门 ----

    async def _fetch_all_depts(self) -> list[dict]:
        """从根(1) BFS 拉全部子部门，结果父先于子（保证新建时父 path 已就绪）。

        seen 防御钉钉数据异常的部门循环引用（A 是 B 的子、B 又是 A 的子）
        导致 BFS 死循环；已见过的 dept_id 直接跳过（首次出现为准）。
        """
        ordered: list[dict] = []
        seen: set[int] = {_DINGTALK_ROOT_DEPT_ID}
        queue = [_DINGTALK_ROOT_DEPT_ID]
        while queue:
            parent = queue.pop(0)
            children = await self.client.list_sub_depts(parent)
            for child in children:
                dept_id = int(child["dept_id"])
                if dept_id in seen:
                    continue
                seen.add(dept_id)
                ordered.append(child)
                queue.append(dept_id)
        return ordered

    async def _load_local_depts(self) -> dict[str, Department]:
        """本地全部已映射钉钉的部门：dingtalk_dept_id -> Department"""
        result = await self.session.execute(
            select(Department).where(Department.dingtalk_dept_id.isnot(None))
        )
        return {str(d.dingtalk_dept_id): d for d in result.scalars().all()}

    async def _create_dept(self, dept: dict, existing: dict[str, Department]) -> None:
        """新建部门（path 按 dept_service 算法：flush 取 id 后拼接）"""
        dt_id = str(dept["dept_id"])
        parent_dt_id = str(dept.get("parent_id") or "")
        parent_local = existing.get(parent_dt_id)
        row = Department(
            name=dept.get("name") or f"钉钉部门-{dt_id}",
            parent_id=str(parent_local.id) if parent_local else None,
            sort=int(dept.get("order") or 0),
            dingtalk_dept_id=dt_id,
            path="",
        )
        self.session.add(row)
        # 先 flush 取回 insert_default 生成的 id，才能计算 path（dept_service 同款）
        await self.session.flush()
        row.path = (parent_local.path if parent_local else "") + f"/{row.id}"
        await self.session.flush()
        existing[dt_id] = row

    async def _update_dept(self, local: Department, dept: dict, existing: dict[str, Department]) -> bool:
        """按钉钉数据更新部门（name/parent/sort），有实质变化返回 True。

        status 不在此覆盖（禁用由对账分支负责，人工启禁不被同步冲掉）。
        """
        changed = False
        new_name = dept.get("name")
        if new_name and new_name != local.name:
            local.name = new_name
            changed = True
        new_sort = int(dept.get("order") or 0)
        if new_sort != local.sort:
            local.sort = new_sort
            changed = True
        # 父部门变化 = 移动子树（钉钉侧只可能整树重建，此处按 dept_service 语义重算 path）
        parent_dt_id = str(dept.get("parent_id") or "")
        parent_local = existing.get(parent_dt_id) if parent_dt_id else None
        new_parent_id = str(parent_local.id) if parent_local else None
        current_parent_id = str(local.parent_id) if local.parent_id else None
        if new_parent_id != current_parent_id:
            local.parent_id = new_parent_id
            await self._recalc_subtree_paths(local, parent_local)
            changed = True
        return changed

    async def _recalc_subtree_paths(self, dept: Department, parent: Department | None) -> None:
        """重算 dept 及其全部子孙 path（移动子树，dept_service 同款内存前缀替换）"""
        old_path = dept.path
        new_path = (parent.path if parent else "") + f"/{dept.id}"
        result = await self.session.execute(
            select(Department).where(
                (Department.path == old_path) | Department.path.like(old_path + "/%")
            )
        )
        for node in result.scalars().all():
            node.path = new_path + node.path[len(old_path):]
        await self.session.flush()

    # ---- 用户 ----

    async def _fetch_all_users(self, dept_ids: list[int]) -> dict[str, dict]:
        """拉全部用户详情：{userid: detail}；仅保留在遍历到的部门中出现的用户"""
        found: set[str] = set()
        for dept_id in dept_ids:
            for u in await self.client.list_dept_users(dept_id):
                if u.get("userid"):
                    found.add(u["userid"])
        details: dict[str, dict] = {}
        for userid in found:
            detail = await self.client.get_user_detail(userid)
            detail.setdefault("userid", userid)
            details[userid] = detail
        return details

    async def _load_local_users(self) -> dict:
        """本地全部用户索引：by_dt_id 映射 + names 唯一化基准集合"""
        result = await self.session.execute(select(UserModel))
        users = list(result.scalars().all())
        by_dt_id = {
            str(u.dingtalk_user_id): u
            for u in users
            if u.dingtalk_user_id
        }
        names = {
            str(v).lower()
            for u in users
            for v in (u.username, u.name)
            if v
        }
        return {"by_dt_id": by_dt_id, "names": names}

    async def _create_user(
        self, detail: dict, existing_names: set[str], existing_depts: dict[str, Department]
    ) -> None:
        """新建用户：role=viewer、password_hash=None、username 唯一化 + 覆盖式 user_dept"""
        userid = detail["userid"]
        name = detail.get("name") or userid
        username = unique_username(existing_names, name)
        existing_names.add(username.lower())
        user = UserModel(
            name=name,
            username=username,
            jnpf_name=name,
            password_hash=None,
            role="viewer",
            dingtalk_user_id=userid,
        )
        self.session.add(user)
        await self.session.flush()
        await self._overwrite_user_depts(user, detail, existing_depts)

    async def _update_user(
        self, local: UserModel, detail: dict, existing_depts: dict[str, Department]
    ) -> bool:
        """已有用户更新：只写 jnpf_name，不覆盖 status/role/username；user_dept 覆盖式跟随"""
        changed = False
        name = detail.get("name")
        if name and name != local.jnpf_name:
            local.jnpf_name = name
            changed = True
        dept_changed = await self._overwrite_user_depts(local, detail, existing_depts)
        return changed or dept_changed

    async def _overwrite_user_depts(
        self, user: UserModel, detail: dict, existing_depts: dict[str, Department]
    ) -> bool:
        """覆盖式写 user_dept：以钉钉 dept_id_list 为准，主部门取 detail 主部门或第一个。

        返回是否有实质变化（行集合或主部门标记不同）。
        """
        dt_ids = [int(d) for d in (detail.get("dept_id_list") or []) if d]
        # 钉钉 dept_id → 本地 department id（未映射的部门跳过，如根部门 1）
        mapped = [existing_depts[str(d)] for d in dt_ids if str(d) in existing_depts]
        if not mapped:
            return False
        main_dt = detail.get("main_dept_id")
        primary = next(
            (d for d in mapped if str(d.dingtalk_dept_id) == str(main_dt)),
            mapped[0],
        )

        result = await self.session.execute(
            select(UserDept).where(UserDept.user_id == str(user.id))
        )
        current = {
            str(r.dept_id): bool(r.is_primary) for r in result.scalars().all()
        }
        desired = {str(d.id): d is primary for d in mapped}
        if current == desired:
            return False

        await self.session.execute(
            delete(UserDept).where(UserDept.user_id == str(user.id))
        )
        for d in mapped:
            self.session.add(
                UserDept(
                    user_id=str(user.id),
                    dept_id=str(d.id),
                    is_primary=d is primary,
                )
            )
        await self.session.flush()
        return True
