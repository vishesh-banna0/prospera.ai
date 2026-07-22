from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.modules.users.application.dto import LoginInput, RegisterInput
from backend.modules.users.application.services import AuthService
from backend.modules.users.infrastructure.models import Base
from backend.modules.users.infrastructure.repositories import SqlUserRepository
from backend.modules.users.infrastructure.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

SECRET = "test-secret"


def test_password_hashing_roundtrip() -> None:
    stored = hash_password("correct horse battery staple")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("correct horse battery staple", stored) is True
    assert verify_password("wrong password", stored) is False
    # A random salt means the same password hashes to different strings.
    assert hash_password("password123") != hash_password("password123")


def test_token_roundtrip_reject_tamper_and_expiry() -> None:
    token = create_token("user-123", SECRET, ttl_hours=1)
    payload = decode_token(token, SECRET)
    assert payload is not None and payload["sub"] == "user-123"

    assert decode_token(token, "different-secret") is None
    assert decode_token(token + "x", SECRET) is None
    assert decode_token(create_token("user-123", SECRET, ttl_hours=-1), SECRET) is None


async def _build_service():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(engine, expire_on_commit=False)()
    service = AuthService(SqlUserRepository(session), SECRET, 1.0, commit=session.commit)
    return engine, session, service


@pytest.mark.asyncio
async def test_register_then_login() -> None:
    engine, session, service = await _build_service()
    try:
        registered = await service.register(
            RegisterInput(username="alice", password="password123")
        )
        assert registered.user.username == "alice"
        assert registered.token_type == "bearer"
        assert decode_token(registered.token, SECRET)["sub"] == registered.user.user_id

        logged_in = await service.login(
            LoginInput(username="alice", password="password123")
        )
        assert logged_in.user.user_id == registered.user.user_id
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_username_is_rejected() -> None:
    engine, session, service = await _build_service()
    try:
        await service.register(RegisterInput(username="bob", password="password123"))
        with pytest.raises(ValueError):
            await service.register(RegisterInput(username="bob", password="password999"))
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_wrong_password_and_unknown_user_are_rejected() -> None:
    engine, session, service = await _build_service()
    try:
        await service.register(RegisterInput(username="carol", password="password123"))
        with pytest.raises(ValueError):
            await service.login(LoginInput(username="carol", password="wrong-one"))
        with pytest.raises(ValueError):
            await service.login(LoginInput(username="nobody", password="password123"))
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_short_credentials_are_rejected() -> None:
    engine, session, service = await _build_service()
    try:
        with pytest.raises(ValueError):
            await service.register(RegisterInput(username="ab", password="password123"))
        with pytest.raises(ValueError):
            await service.register(RegisterInput(username="alice", password="short"))
    finally:
        await session.close()
        await engine.dispose()
