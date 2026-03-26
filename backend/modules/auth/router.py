from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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
from modules.shared.notification_rules import run_system_notification_rules
from modules.shared.storage import delete_resource_file_by_url, save_image_file

router = APIRouter(prefix='/auth', tags=['auth'])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class MeUpdateRequest(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=1000)


def _to_user_payload(user_row: dict) -> dict:
    return {
        'id': user_row['id'],
        'username': user_row['username'],
        'email': user_row['email'],
        'role': user_row['role'],
        'warehouse_id': user_row['warehouse_id'],
        'avatar': user_row.get('avatar'),
        'phone': user_row.get('phone'),
        'description': user_row.get('description'),
        'is_active': user_row['is_active'],
    }


@router.post('/login', summary='Login and get JWT token')
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        text(
            """
            SELECT id, username, password, email, role, warehouse_id, avatar, phone, description, is_active
            FROM users
            WHERE username = :username
            LIMIT 1
            """
        ),
        {'username': payload.username},
    )
    user = result.mappings().first()
    if not user or not verify_password(payload.password, user['password']):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')
    if not user['is_active']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User is disabled')

    token = create_access_token({'id': user['id'], 'username': user['username'], 'role': user['role']})
    return success(
        data={
            'token': token,
            'user': _to_user_payload(dict(user)),
        }
    )


@router.get('/me', summary='Get current authenticated user')
async def me(current_user=Depends(get_current_user_required)):
    return success(data=current_user)


@router.patch('/me', summary='Update current user profile')
async def update_me(
    payload: MeUpdateRequest,
    current_user=Depends(get_current_user_required),
    session: AsyncSession = Depends(get_db_session),
):
    user_id = int(current_user['id'])
    values = payload.model_dump(exclude_unset=True)
    if not values:
        return success(data=current_user)

    allowed_columns = {'phone', 'description'}
    set_fragments: list[str] = []
    bind_values: dict[str, object] = {'id': user_id}

    for key, value in values.items():
        if key not in allowed_columns:
            continue
        set_fragments.append(f"{key} = :{key}")
        bind_values[key] = value

    if not set_fragments:
        return success(data=current_user)

    set_clause = ",\n                    ".join(set_fragments)
    result = await session.execute(
        text(
            f"""
            UPDATE users
            SET {set_clause},
                updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
            WHERE id = :id
            RETURNING id, username, email, role, warehouse_id, avatar, phone, description, is_active
            """
        ),
        bind_values,
    )
    updated = result.mappings().first()
    if not updated:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    await session.commit()
    return success(data=_to_user_payload(dict(updated)))


@router.post('/me/avatar', summary='Upload current user avatar')
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user_required),
    session: AsyncSession = Depends(get_db_session),
):
    user_id = int(current_user['id'])

    user_result = await session.execute(
        text("SELECT avatar FROM users WHERE id = :id LIMIT 1"),
        {'id': user_id},
    )
    user_row = user_result.mappings().first()
    if not user_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    old_avatar = user_row.get('avatar')
    avatar_url = await save_image_file(file, 'user_avatars', 'user', user_id)

    updated_result = await session.execute(
        text(
            """
            UPDATE users
            SET avatar = :avatar,
                updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
            WHERE id = :id
            RETURNING id, username, email, role, warehouse_id, avatar, phone, description, is_active
            """
        ),
        {'id': user_id, 'avatar': avatar_url},
    )
    updated = updated_result.mappings().first()
    if not updated:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    await session.commit()

    if old_avatar and old_avatar != avatar_url:
        delete_resource_file_by_url(old_avatar)

    return success(data=_to_user_payload(dict(updated)))


@router.get('/me/notifications', summary='List current user notifications')
async def list_my_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user_required),
    session: AsyncSession = Depends(get_db_session),
):
    await run_system_notification_rules(session)

    where = ["n.user_id = :user_id"]
    params: dict[str, object] = {
        "user_id": int(current_user['id']),
        "limit": limit,
    }
    if unread_only:
        where.append("n.is_read = false")

    where_sql = " AND ".join(where)

    rows_result = await session.execute(
        text(
            f"""
            SELECT
                n.id,
                n.type,
                n.title,
                n.body,
                n.related_id,
                n.related_type,
                n.is_read,
                n.created_at
            FROM notifications n
            WHERE {where_sql}
            ORDER BY n.created_at DESC, n.id DESC
            LIMIT :limit
            """
        ),
        params,
    )
    items = [dict(row) for row in rows_result.mappings().all()]

    unread_count_result = await session.execute(
        text(
            """
            SELECT COUNT(*)::INTEGER AS unread_count
            FROM notifications
            WHERE user_id = :user_id
              AND is_read = false
            """
        ),
        {"user_id": int(current_user['id'])},
    )
    unread_count = int(unread_count_result.scalar_one() or 0)

    return success(
        data={
            "items": items,
            "total": len(items),
            "unread_count": unread_count,
        }
    )


@router.patch('/me/notifications/{notification_id}/read', summary='Mark one notification as read')
async def mark_notification_read(
    notification_id: int,
    current_user=Depends(get_current_user_required),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        text(
            """
            UPDATE notifications
            SET is_read = true
            WHERE id = :id
              AND user_id = :user_id
            RETURNING id
            """
        ),
        {
            "id": notification_id,
            "user_id": int(current_user['id']),
        },
    )
    updated = result.mappings().first()
    if not updated:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notification not found')

    await session.commit()
    return success(data={"id": notification_id, "is_read": True})


@router.patch('/me/notifications/read-all', summary='Mark all notifications as read')
async def mark_all_notifications_read(
    current_user=Depends(get_current_user_required),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        text(
            """
            UPDATE notifications
            SET is_read = true
            WHERE user_id = :user_id
              AND is_read = false
            """
        ),
        {"user_id": int(current_user['id'])},
    )
    await session.commit()
    return success(data={"updated": int(result.rowcount or 0)})
