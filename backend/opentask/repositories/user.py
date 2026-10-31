from typing import Optional, Type

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from opentask.models.user.model import UserModel
from opentask.repositories.base import AsyncSession, BaseRepository, NotFoundError


class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    name: Optional[str] = None
    password: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_base_url: str | None = None
    langsmith_api_key: Optional[str] = None
    preferred_openai_model: Optional[str] = None
    sentry_enabled: Optional[bool] = False
    analytics_enabled: Optional[bool] = True
    hide_sql_preference: Optional[bool] = False


class UserUpdate(UserCreate):
    sentry_enabled: Optional[bool] = False
    analytics_enabled: Optional[bool] = None
    hide_sql_preference: Optional[bool] = None


class UserRepository(BaseRepository[UserModel, UserCreate, UserUpdate]):
    @property
    def model(self) -> Type[UserModel]:
        return UserModel

    async def get_one_or_none(self, session: AsyncSession) -> Optional[UserModel]:
        query = select(self.model)
        try:
            return await self.first(session, query=query)
        except NotFoundError:
            return None

    async def get_by_name(self, session: AsyncSession, name: str) -> UserModel:
        query = select(self.model).where(self.model.name == name)
        return await self.get(session, query=query)

    async def get_by_username(self, session: AsyncSession, username: str) -> Optional[UserModel]:
        """按登录用户名（username 列）查用户，找不到返回 None（由调用方决定是否回退 name 列）"""
        query = select(self.model).where(self.model.username == username)
        try:
            return await self.first(session, query=query)
        except NotFoundError:
            return None
