from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_auth_service, get_current_user
from backend.modules.users.application.dto import (
    AuthTokenView,
    LoginInput,
    RegisterInput,
    UserView,
)
from backend.modules.users.application.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthTokenView)
async def register(
    request: RegisterInput,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenView:
    """Create an account and return a signed token."""
    try:
        return await service.register(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthTokenView)
async def login(
    request: LoginInput,
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenView:
    """Verify credentials and return a signed token."""
    try:
        return await service.login(request)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserView)
async def me(current_user: UserView = Depends(get_current_user)) -> UserView:
    """Return the account for the presented bearer token."""
    return current_user


"""
Purpose:
Expose simple username/password authentication over HTTP.

Endpoints:
- POST /auth/register: create an account, returns a token
- POST /auth/login: verify credentials, returns a token
- GET /auth/me: the current account (requires a bearer token)

What Should Not Live Here:
- Password hashing / token signing (infrastructure/security.py)
- Persistence (infrastructure/repositories.py)
"""
