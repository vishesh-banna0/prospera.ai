from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class User:
    """An account that can sign in. The password is only ever held as a hash."""

    user_id: str
    username: str
    password_hash: str
    created_at: datetime
