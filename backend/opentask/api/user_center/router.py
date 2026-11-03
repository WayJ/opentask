"""用户中心迁移 API（SSO 存量用户迁移 / 业务表 dept_id 历史回填）

POST /api/user-center/migrate/sso：
把从未设置过本地密码的存量用户批量迁移为可本地登录的账号，
响应体返回 CSV 文本（username,temp_password）供管理员下载分发。

POST /api/user-center/backfill/dept-id：
对 7 张业务表（requirements/issues/projects/knowledge_bases/
documents/tasks/agent_tasks）的 dept_id IS NULL 历史行按创建人主部门回填，
返回逐表报告（幂等，可重复执行）。

双门槛（缺一 403，错误信息区分原因）：
1. config.sso_enabled == true（需开启 SSO 兼容模式；仅迁移命令需要）
2. 当前用户持有 manage:user:migrate 权限（admin 专属权限码）
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from opentask.api.user_center.deps import require_permission
from opentask.config import config
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.user_center.backfill_service import BackfillService
from opentask.services.user_center.migrate_service import MigrateService

router = APIRouter(prefix="/api/user-center", tags=["用户中心迁移"])


@router.post("/migrate/sso")
async def migrate_sso(
    current_user: UserModel = require_permission("manage:user:migrate"),
    session=Depends(get_session),
) -> dict:
    """SSO 存量用户迁移命令（幂等，可重复执行）

    逻辑：扫描 password_hash 为空的存量用户 → 回填 username（缺失时）→
    生成 12 位随机临时密码 bcrypt 落库 → must_change_password=True。

    响应 data：{migrated: n, csv: "username,temp_password\\n..."}
    临时密码只出现在响应体（供管理员下载分发），不写日志、不落盘。
    """
    # 门槛 1：必须开启 SSO 兼容模式
    # （门槛 2：manage:user:migrate 权限，由 require_permission 依赖先行校验）
    if not config.sso_enabled:
        raise HTTPException(
            status_code=403,
            detail="需开启 SSO 兼容模式（配置 AUTH_SSO_ENABLED=true）后才能执行迁移",
        )

    result = await MigrateService(session).migrate_sso_users()
    return {
        "code": 200,
        "message": "success",
        "data": result,
        "timestamp": int(datetime.now().timestamp() * 1000),
    }


@router.post("/backfill/dept-id")
async def backfill_dept_id(
    current_user: UserModel = require_permission("manage:user:migrate"),
    session=Depends(get_session),
) -> dict:
    """业务表 dept_id 历史回填命令（幂等，可重复执行）

    对 7 张带部门归属快照列的业务表，把 dept_id IS NULL 的历史行按
    创建人（created_by → 用户 → 主部门）回填：
    - requirements/issues/documents 有 created_by，逐行匹配
      （UUID id > username > name，name 重名跳过）；
    - projects/knowledge_bases/tasks/agent_tasks 无 created_by 或语义不符
      （Agent 名等），不回填、全表报告 skipped_no_owner（历史留 NULL = 仅 ALL 可见）。

    响应 data：{table: {total_null, updated, skipped_no_dept, skipped_no_owner,
    skipped_ambiguous, skipped_dirty_count, dirty_samples, table_missing}}
    """
    report = await BackfillService(session).backfill_dept_id()
    return {
        "code": 200,
        "message": "success",
        "data": report,
        "timestamp": int(datetime.now().timestamp() * 1000),
    }
