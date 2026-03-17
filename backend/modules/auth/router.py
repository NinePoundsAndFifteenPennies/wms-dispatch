from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.dependencies import (
    create_access_token,
    get_current_user_required,
    get_db_session,
    verify_password,
)
from modules.shared.response import success

router = APIRouter(prefix='/auth', tags=['auth'])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


@router.post('/login', summary='Login and get JWT token')
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        text(
            """
            SELECT id, username, password, email, role, warehouse_id, is_active
            FROM users
            WHERE username = :username
            LIMIT 1
            """
        ),
        {'username': payload.username},
    )
    user = result.mappings().first()
    if not user or not verify_password(payload.password, user['password']):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid username or password')
    if not user['is_active']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='user is disabled')

    token = create_access_token(dict(user))
    return success(
        data={
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'warehouse_id': user['warehouse_id'],
                'is_active': user['is_active'],
            },
        }
    )


@router.get('/me', summary='Get current authenticated user')
async def me(current_user=Depends(get_current_user_required)):
    return success(data=current_user)
