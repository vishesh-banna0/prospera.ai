from __future__ import annotations

from abc import ABC, abstractmethod

from backend.modules.users.domain.entities import User


class UserRepository(ABC):
    """Persistence contract for user accounts."""

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def add(self, user: User) -> None:
        raise NotImplementedError
