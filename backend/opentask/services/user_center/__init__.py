"""用户中心服务包：权限点字典（代码即真源）与系统角色幂等播种"""
from opentask.services.user_center.permission_defs import PERMISSIONS, permission_codes
from opentask.services.user_center.seed import seed_user_center

__all__ = ["PERMISSIONS", "permission_codes", "seed_user_center"]
