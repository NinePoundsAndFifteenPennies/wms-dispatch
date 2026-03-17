from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.shared.config import settings
from modules.shared.database import AsyncSessionLocal

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
ALGORITHM = settings.jwt_algorithm
TOKEN_EXPIRE_HOURS = settings.jwt_expire_hours
JWT_SECRET_KEY = settings.jwt_secret_key


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user: dict[str, Any]) -> str:
    expires_at = datetime.now(UTC) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        'sub': str(user['id']),
        'username': user['username'],
        'role': user['role'],
        'exp': expires_at,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


async def fetch_user_by_id(session: AsyncSession, user_id: int):
    result = await session.execute(
        text(
            """
            SELECT id, username, email, role, warehouse_id, is_active
            FROM users
            WHERE id = :id
            LIMIT 1
            """
        ),
        {'id': user_id},
    )
    return result.mappings().first()


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db_session)):
    user_data = getattr(request.state, 'current_user', None)
    if user_data is None:
        return None

    user_id = user_data.get('id')
    if user_id is None:
        return None

    user = await fetch_user_by_id(session, int(user_id))
    if not user:
        return None
    return dict(user)


async def get_current_user_required(current_user=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='unauthorized')
    if not current_user['is_active']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='user is disabled')
    return current_user


def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='request not found')

            current_user = getattr(request.state, 'current_user', None)
            if current_user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='unauthorized')
            if current_user.get('role') != required_role:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='forbidden')
            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def inject_current_user_from_token(request: Request, call_next):
    request.state.current_user = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.removeprefix('Bearer ').strip()
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
            sub = payload.get('sub')
            if sub is not None:
                request.state.current_user = {'id': int(sub), 'role': payload.get('role')}
        except (JWTError, ValueError):
            request.state.current_user = None
    return await call_next(request)
