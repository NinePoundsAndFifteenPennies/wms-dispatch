from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field

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
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    capacity: Optional[int] = None
    cover_image: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True


class WarehouseOptionResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    address: str = Field(min_length=1)
    latitude: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(default=None, ge=-180, le=180)
    capacity: int = Field(default=0, ge=0)
    description: Optional[str] = None


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    address: Optional[str] = Field(default=None, min_length=1)
    latitude: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(default=None, ge=-180, le=180)
    capacity: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None


class WarehouseListResponse(BaseModel):
    items: List[WarehouseResponse]
    total: int


class WarehouseInventoryItemResponse(BaseModel):
    id: int
    product_id: int
    sku: str
    product_name: str
    category: Optional[str] = None
    product_is_active: bool
    qty_on_hand: int
    qty_reserved: int
    qty_locked: int
    qty_threshold: int
    qty_available: int


class WarehouseInventoryResponse(BaseModel):
    warehouse: WarehouseResponse
    items: List[WarehouseInventoryItemResponse]
    total: int


class StocktakeAdjustRequest(BaseModel):
    qty_on_hand: int = Field(
        ge=0,
        description="盘点后的现存量，且必须不小于当前预留量与锁定量之和",
    )
    reason: Optional[str] = Field(default=None, max_length=500)


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    contact: str = Field(min_length=1, max_length=128)
    address: Optional[str] = None
    description: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    contact: Optional[str] = Field(default=None, min_length=1, max_length=128)
    address: Optional[str] = None
    description: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    contact: str
    address: Optional[str] = None
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    items: List[CustomerResponse]
    total: int


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    category: Optional[str] = Field(default=None, max_length=64)
    unit_weight: Optional[Decimal] = None
    unit_of_measure: str = Field(default="piece", min_length=1, max_length=16)
    req_skill_picking: int = Field(default=0, ge=0)
    req_skill_staging: int = Field(default=0, ge=0)
    req_skill_shipping: int = Field(default=0, ge=0)
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    category: Optional[str] = Field(default=None, max_length=64)
    unit_weight: Optional[Decimal] = None
    unit_of_measure: Optional[str] = Field(default=None, min_length=1, max_length=16)
    req_skill_picking: Optional[int] = Field(default=None, ge=0)
    req_skill_staging: Optional[int] = Field(default=None, ge=0)
    req_skill_shipping: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    category: Optional[str] = None
    unit_weight: Optional[Decimal] = None
    unit_of_measure: str
    req_skill_picking: int
    req_skill_staging: int
    req_skill_shipping: int
    cover_image: Optional[str] = None
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int


class BatchDeleteRequest(BaseModel):
    ids: List[int] = Field(min_length=1)


class ActiveStatusUpdate(BaseModel):
    is_active: bool
