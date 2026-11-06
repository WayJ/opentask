"""权限点字典：代码即真源，管理端只读展示（spec D9）

约定：
- type=menu 时 route_key 对应前端静态路由 name；
- type=button 时 route_key 为 None，code 即业务操作权限码；
- 字典演进（增/改/删权限码）由 seed_user_center 幂等同步到数据库。
"""

# type: menu（route_key 对应前端静态路由 name） / button（业务操作权限码）
PERMISSIONS: list[dict] = [
    # ---- 管理端菜单 ----
    {"code": "menu:manage_user",   "name": "用户管理", "type": "menu", "route_key": "manage_user"},
    {"code": "menu:manage_dept",   "name": "部门管理", "type": "menu", "route_key": "manage_dept"},
    {"code": "menu:manage_role",   "name": "角色管理", "type": "menu", "route_key": "manage_role"},
    {"code": "menu:manage_perm",   "name": "权限点管理", "type": "menu", "route_key": "manage_perm"},
    {"code": "menu:manage_oauth2", "name": "OAuth 客户端", "type": "menu", "route_key": "manage_oauth2"},
    # ---- 管理端按钮 ----
    {"code": "manage:user:create", "name": "创建用户", "type": "button", "route_key": None},
    {"code": "manage:user:update", "name": "编辑用户", "type": "button", "route_key": None},
    {"code": "manage:user:delete", "name": "删除用户", "type": "button", "route_key": None},
    {"code": "manage:user:reset_password", "name": "重置密码", "type": "button", "route_key": None},
    {"code": "manage:user:status", "name": "启禁用户", "type": "button", "route_key": None},
    {"code": "manage:user:role", "name": "分配角色", "type": "button", "route_key": None},
    {"code": "manage:user:migrate", "name": "SSO用户迁移", "type": "button", "route_key": None},
    {"code": "manage:dept:create", "name": "创建部门", "type": "button", "route_key": None},
    {"code": "manage:dept:update", "name": "编辑部门", "type": "button", "route_key": None},
    {"code": "manage:dept:delete", "name": "删除部门", "type": "button", "route_key": None},
    {"code": "manage:role:create", "name": "创建角色", "type": "button", "route_key": None},
    {"code": "manage:role:update", "name": "编辑角色", "type": "button", "route_key": None},
    {"code": "manage:role:delete", "name": "删除角色", "type": "button", "route_key": None},
    {"code": "manage:role:perm", "name": "配置角色权限", "type": "button", "route_key": None},
    {"code": "manage:dingtalk:sync", "name": "触发钉钉同步", "type": "button", "route_key": None},
    # ---- 业务模块：requirement/issue/project/knowledge/task 各 view/create/update/delete ----
    {"code": "requirement:view", "name": "查看需求", "type": "button", "route_key": None},
    {"code": "requirement:create", "name": "创建需求", "type": "button", "route_key": None},
    {"code": "requirement:update", "name": "编辑需求", "type": "button", "route_key": None},
    {"code": "requirement:delete", "name": "删除需求", "type": "button", "route_key": None},
    {"code": "issue:view", "name": "查看Issue", "type": "button", "route_key": None},
    {"code": "issue:create", "name": "创建Issue", "type": "button", "route_key": None},
    {"code": "issue:update", "name": "编辑Issue", "type": "button", "route_key": None},
    {"code": "issue:delete", "name": "删除Issue", "type": "button", "route_key": None},
    {"code": "project:view", "name": "查看项目", "type": "button", "route_key": None},
    {"code": "project:create", "name": "创建项目", "type": "button", "route_key": None},
    {"code": "project:update", "name": "编辑项目", "type": "button", "route_key": None},
    {"code": "project:delete", "name": "删除项目", "type": "button", "route_key": None},
    {"code": "knowledge:view", "name": "查看知识库", "type": "button", "route_key": None},
    {"code": "knowledge:create", "name": "创建知识库", "type": "button", "route_key": None},
    {"code": "knowledge:update", "name": "编辑知识库", "type": "button", "route_key": None},
    {"code": "knowledge:delete", "name": "删除知识库", "type": "button", "route_key": None},
    {"code": "task:view", "name": "查看任务", "type": "button", "route_key": None},
    {"code": "task:create", "name": "创建任务", "type": "button", "route_key": None},
    {"code": "task:update", "name": "编辑任务", "type": "button", "route_key": None},
    {"code": "task:delete", "name": "删除任务", "type": "button", "route_key": None},
    # ---- 个人 ----
    {"code": "profile:view", "name": "查看个人中心", "type": "button", "route_key": None},
    {"code": "profile:update", "name": "修改个人资料", "type": "button", "route_key": None},
]


def permission_codes() -> set[str]:
    """返回全部权限码集合"""
    return {p["code"] for p in PERMISSIONS}
