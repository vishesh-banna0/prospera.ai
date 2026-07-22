from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.modules.users.domain.entities import User
from backend.modules.users.domain.repositories import UserRepository
from backend.modules.users.infrastructure.models import UserModel


class SqlUserRepository(UserRepository):
    """SQL-based implementation of the user repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model is not None else None

    async def get_by_id(self, user_id: str) -> User | None:
        stmt = select(UserModel).where(UserModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model is not None else None

    async def add(self, user: User) -> None:
        self._session.add(
            UserModel(
                user_id=user.user_id,
                username=user.username,
                password_hash=user.password_hash,
                created_at=user.created_at,
            )
        )
        await self._session.flush()

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            user_id=model.user_id,
            username=model.username,
            password_hash=model.password_hash,
            created_at=model.created_at,
        )
