import uuid
from uuid import UUID

from sqlalchemy import CHAR, MetaData, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column


class DBModel(MappedAsDataclass, DeclarativeBase, init=False, kw_only=True):
    __abstract__ = True
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_`%(constraint_name)s`",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class CustomUUIDType(TypeDecorator):
    """UUID 类型，统一使用 CHAR(36) 带连字符格式存储

    数据库列类型为 CHAR(36)，Python 层使用 uuid.UUID 对象。
    读取时兼容旧的32位无连字符格式。
    """
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, str):
                # 兼容旧数据：32位无连字符 -> 36位带连字符
                if len(value) == 32:
                    value = f"{value[0:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:32]}"
                return uuid.UUID(value)
            return value
        return value


class UUIDMixin(MappedAsDataclass, init=False, kw_only=True):
    id: Mapped[UUID] = mapped_column("id", CustomUUIDType, primary_key=True, insert_default=uuid.uuid4, init=False)
