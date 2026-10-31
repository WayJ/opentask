"""
存储服务工厂
统一使用 MinIO 对象存储
"""
from opentask.config import config


# 全局单例
_storage_service_instance = None


def get_storage_service():
    """
    获取存储服务实例（工厂函数）
    统一使用 MinIO 对象存储

    Returns:
        MinIOStorageService 实例
    """
    global _storage_service_instance

    if _storage_service_instance is None:
        from opentask.services.storage.minio_service import MinIOStorageService
        _storage_service_instance = MinIOStorageService()
        print(f"[Storage] Using MinIO: {config.minio_endpoint}")

    return _storage_service_instance


# 向后兼容的全局单例（已废弃，建议使用 get_storage_service()）
# 惰性代理（PEP 562）：import 不再触发 MinIO 连接，首次访问才创建单例
def __getattr__(name: str):
    if name == "storage_service":
        return get_storage_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
