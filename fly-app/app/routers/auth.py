from fastapi import APIRouter, Depends, HTTPException, Response, Request, Header
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
from datetime import datetime, timedelta
import httpx
import secrets

from app.database import get_db
from app.models import User
from app.schemas import UserResponse
from app.config import get_settings
from app.oauth import oauth

router = APIRouter()
settings = get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get("access_token")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_printer_api_key(api_key: str | None = Depends(api_key_header)) -> str:
    """Validate the printer API key from X-API-Key header."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    if not settings.printer_api_key:
        raise HTTPException(status_code=500, detail="Printer API key not configured")

    if not secrets.compare_digest(api_key, settings.printer_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key


async def get_or_create_user(
    db: AsyncSession,
    email: str,
    name: str | None,
    avatar_url: str | None,
    oauth_provider: str,
    oauth_id: str,
) -> User:
    result = await db.execute(
        select(User).where(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update user info
        user.email = email
        user.name = name
        user.avatar_url = avatar_url
        await db.commit()
        return user

    # Create new user
    user = User(
        email=email,
        name=name,
        avatar_url=avatar_url,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/google")
async def google_login(request: Request):
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")

    user = await get_or_create_user(
        db=db,
        email=user_info["email"],
        name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
        oauth_provider="google",
        oauth_id=user_info["sub"],
    )

    access_token = create_access_token(user.id)
    response = Response(status_code=302)
    response.headers["Location"] = settings.frontend_url
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.get("/github")
async def github_login(request: Request):
    redirect_uri = f"{settings.backend_url}/auth/github/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback")
async def github_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.github.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

    # Get user info from GitHub API
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
        user_data = resp.json()

        # Get user email (may need separate API call if email is private)
        email = user_data.get("email")
        if not email:
            resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {token['access_token']}"},
            )
            emails = resp.json()
            primary_email = next((e for e in emails if e.get("primary")), None)
            email = primary_email["email"] if primary_email else emails[0]["email"]

    user = await get_or_create_user(
        db=db,
        email=email,
        name=user_data.get("name") or user_data.get("login"),
        avatar_url=user_data.get("avatar_url"),
        oauth_provider="github",
        oauth_id=str(user_data["id"]),
    )

    access_token = create_access_token(user.id)
    response = Response(status_code=302)
    response.headers["Location"] = settings.frontend_url
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}
