"""文件存储服务"""
from opentask.services.storage.service import get_storage_service
from opentask.services.storage import service as _service


# 惰性 re-export（PEP 562）：import 不触发 MinIO 连接，首次访问 storage_service 才创建单例
def __getattr__(name: str):
    if name == "storage_service":
        return _service.storage_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ['storage_service', 'get_storage_service']
