from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str
    warehouse_id: Optional[int] = None
    skill_picking: Optional[int] = 0
    skill_staging: Optional[int] = 0
    skill_shipping: Optional[int] = 0

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    warehouse_id: Optional[int] = None
    skill_picking: Optional[int] = 0
    skill_staging: Optional[int] = 0
    skill_shipping: Optional[int] = 0

class UserStatusUpdate(BaseModel):
    is_active: bool

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    warehouse_id: Optional[int] = None
    skill_picking: int
    skill_staging: int
    skill_shipping: int

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int

class WarehouseResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

