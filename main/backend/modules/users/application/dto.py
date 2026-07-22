from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RegisterInput:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginInput:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class UserView:
    user_id: str
    username: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AuthTokenView:
    token: str
    user: UserView
    token_type: str = "bearer"
