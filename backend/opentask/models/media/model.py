from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel, UUIDMixin


class MediaModel(DBModel, UUIDMixin, kw_only=True):
    __tablename__ = "media"
    key: Mapped[str] = mapped_column("key", String(255), nullable=False)
    blob: Mapped[bytes] = mapped_column("blob", LargeBinary, nullable=False)
