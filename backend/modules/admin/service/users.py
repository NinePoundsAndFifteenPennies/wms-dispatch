from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from models.user import User
from modules.admin.schemas import UserCreate, UserStatusUpdate, UserUpdate

from .base import get_password_hash


class UserServiceMixin:
    async def list_users(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(User)
        if search:
            stmt = stmt.where(or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        return {"items": items, "total": total}

    async def create_user(self, user_data: UserCreate) -> User:
        if user_data.role != "admin" and not user_data.warehouse_id:
            raise HTTPException(status_code=400, detail="warehouse_id is required for non-admin users")

        existing = await self.session.execute(
            select(User).where(or_(User.username == user_data.username, User.email == user_data.email))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username or email already exists")

        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            password=hashed_password,
            email=user_data.email,
            role=user_data.role,
            warehouse_id=user_data.warehouse_id,
            skill_picking=user_data.skill_picking,
            skill_staging=user_data.skill_staging,
            skill_shipping=user_data.skill_shipping,
            is_active=True,
        )
        self.session.add(new_user)
        try:
            await self.session.commit()
            await self.session.refresh(new_user)
            return new_user
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user_data.role is None and user_data.warehouse_id is None:
            raise HTTPException(status_code=400, detail="Only role and warehouse_id can be updated")

        curr_role = user_data.role if user_data.role is not None else user.role
        curr_wh = user_data.warehouse_id if user_data.warehouse_id is not None else user.warehouse_id
        if curr_role != "admin" and not curr_wh:
            raise HTTPException(status_code=400, detail="warehouse_id is required for non-admin users")

        if user_data.role is not None:
            user.role = user_data.role
        if user_data.warehouse_id is not None:
            user.warehouse_id = user_data.warehouse_id

        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail="Update failed, check for duplicate username/email")

    async def update_user_status(self, user_id: int, status_update: UserStatusUpdate) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.role == "admin" and not status_update.is_active:
            raise HTTPException(status_code=400, detail="Admin account cannot be disabled")

        user.is_active = status_update.is_active
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def batch_disable_users(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(User).where(User.id.in_(ids), User.is_active.is_(True), User.role != "admin")
        )
        users = result.scalars().all()
        if not users:
            return 0

        for user in users:
            user.is_active = False
        await self.session.commit()
        return len(users)
