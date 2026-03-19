from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Literal

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
    product_cover_image: Optional[str] = None
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
    qty_on_hand: Optional[int] = Field(
        default=None,
        ge=0,
        description="盘点后的现存量，且必须不小于当前预留量与锁定量之和",
    )
    qty_threshold: Optional[int] = Field(default=None, ge=0, description="库存阈值")
    reason: Optional[str] = Field(default=None, max_length=500)


class WarehouseInboundRequest(BaseModel):
    product_id: int
    qty: int = Field(gt=0, description="进货数量，必须大于 0")
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


OrderStatus = Literal["pending_acceptance", "in_progress", "completed", "cancelled"]
OrderPriority = Literal["high", "medium", "low"]


class OrderListItemResponse(BaseModel):
    id: int
    order_no: str
    customer_id: int
    customer_name: str
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    dispatcher_id: Optional[int] = None
    dispatcher_name: Optional[str] = None
    description: Optional[str] = None
    status: OrderStatus
    priority: OrderPriority
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    total_amount: int
    total_items: int


class OrderListResponse(BaseModel):
    items: List[OrderListItemResponse]
    total: int


class OrderItemCreate(BaseModel):
    product_id: int
    qty: int = Field(gt=0)
    unit_price: int = Field(ge=0, description="单价（分）")


class OrderCreate(BaseModel):
    customer_id: int
    priority: OrderPriority = "medium"
    description: Optional[str] = None
    items: List[OrderItemCreate] = Field(min_length=1)


class OrderCreateResponse(BaseModel):
    id: int
    order_no: str
    customer_id: int
    warehouse_id: Optional[int] = None
    dispatcher_id: Optional[int] = None
    description: Optional[str] = None
    status: OrderStatus
    priority: OrderPriority
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderDetailItemResponse(BaseModel):
    id: int
    product_id: int
    product_sku: str
    product_name: str
    product_category: Optional[str] = None
    qty: int
    unit_price: int
    subtotal: int


class OrderDetailResponse(BaseModel):
    id: int
    order_no: str
    customer_id: int
    customer_name: str
    customer_contact: str
    customer_address: Optional[str] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    dispatcher_id: Optional[int] = None
    dispatcher_name: Optional[str] = None
    description: Optional[str] = None
    status: OrderStatus
    priority: OrderPriority
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    total_amount: int
    total_items: int
    items: List[OrderDetailItemResponse]
