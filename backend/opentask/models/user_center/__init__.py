"""用户中心模型包，导出全部模型类"""
from opentask.models.user_center.model import (
    Department,
    Position,
    UserDept,
    Role,
    Permission,
    RolePermission,
    UserRole,
    RoleDept,
    RefreshToken,
)

__all__ = [
    "Department",
    "Position",
    "UserDept",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "RoleDept",
    "RefreshToken",
]
