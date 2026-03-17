from typing import List, Optional
import bcrypt
from fastapi import HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.warehouse import Warehouse
from modules.admin.schemas import UserCreate, UserUpdate, UserStatusUpdate

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode("utf-8")

class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

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
            
        # Check duplicate
        existing = await self.session.execute(select(User).where(or_(User.username == user_data.username, User.email == user_data.email)))
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
            is_active=True
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

        curr_role = user_data.role if user_data.role is not None else user.role
        curr_wh = user_data.warehouse_id if user_data.warehouse_id is not None else user.warehouse_id
        if curr_role != "admin" and not curr_wh:
            raise HTTPException(status_code=400, detail="warehouse_id is required for non-admin users")

        if user_data.username is not None:
            user.username = user_data.username
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.role is not None:
            user.role = user_data.role
        if user_data.warehouse_id is not None:
            user.warehouse_id = user_data.warehouse_id
        if user_data.skill_picking is not None:
            user.skill_picking = user_data.skill_picking
        if user_data.skill_staging is not None:
            user.skill_staging = user_data.skill_staging
        if user_data.skill_shipping is not None:
            user.skill_shipping = user_data.skill_shipping

        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
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

    async def list_warehouses(self) -> List[Warehouse]:
        result = await self.session.execute(select(Warehouse).order_by(Warehouse.id.asc()))
        return result.scalars().all()

