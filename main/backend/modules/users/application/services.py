from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from backend.modules.users.application.dto import (
    AuthTokenView,
    LoginInput,
    RegisterInput,
    UserView,
)
from backend.modules.users.domain.entities import User
from backend.modules.users.domain.repositories import UserRepository
from backend.modules.users.infrastructure.security import (
    create_token,
    hash_password,
    verify_password,
)

MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 8


class AuthService:
    """Register and authenticate users, issuing a signed token on success."""

    def __init__(
        self,
        user_repository: UserRepository,
        secret_key: str,
        token_ttl_hours: float,
        commit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._user_repository = user_repository
        self._secret_key = secret_key
        self._token_ttl_hours = token_ttl_hours
        self._commit = commit

    async def register(self, request: RegisterInput) -> AuthTokenView:
        username = request.username.strip()
        self._validate_credentials(username, request.password)

        if await self._user_repository.get_by_username(username) is not None:
            raise ValueError(f"Username '{username}' is already taken.")

        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            password_hash=hash_password(request.password),
            created_at=datetime.now(UTC),
        )
        await self._user_repository.add(user)
        await self._commit_changes()
        return self._issue(user)

    async def login(self, request: LoginInput) -> AuthTokenView:
        user = await self._user_repository.get_by_username(request.username.strip())
        # Verify even when the user is missing is not needed here; the single
        # generic message below avoids leaking whether the username exists.
        if user is None or not verify_password(request.password, user.password_hash):
            raise ValueError("Invalid username or password.")
        return self._issue(user)

    async def get_user(self, user_id: str) -> UserView:
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found.")
        return self._to_view(user)

    def _issue(self, user: User) -> AuthTokenView:
        token = create_token(user.user_id, self._secret_key, self._token_ttl_hours)
        return AuthTokenView(token=token, user=self._to_view(user))

    @staticmethod
    def _to_view(user: User) -> UserView:
        return UserView(
            user_id=user.user_id,
            username=user.username,
            created_at=user.created_at,
        )

    @staticmethod
    def _validate_credentials(username: str, password: str) -> None:
        if len(username) < MIN_USERNAME_LENGTH:
            raise ValueError(
                f"Username must be at least {MIN_USERNAME_LENGTH} characters."
            )
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )

    async def _commit_changes(self) -> None:
        if self._commit is not None:
            await self._commit()
