from decimal import Decimal
from datetime import date, datetime
from typing import Any, Optional, List, Literal

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
    role: Optional[str] = None
    warehouse_id: Optional[int] = None

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
    avatar: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None

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


class InventoryFlowPointResponse(BaseModel):
    date: str
    movement_count: int
    total_abs_delta: int


class WarehouseInventoryFlowTrendResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    points: List[InventoryFlowPointResponse]


class AdminInventoryFlowTrendListResponse(BaseModel):
    warehouses: List[WarehouseInventoryFlowTrendResponse]


class InventoryFlowNodeRecordResponse(BaseModel):
    id: int
    created_at: datetime
    change_type: str
    product_id: int
    product_sku: str
    product_name: str
    delta_on_hand: int
    delta_reserved: int
    delta_locked: int
    before_on_hand: int
    before_reserved: int
    before_locked: int
    after_on_hand: int
    after_reserved: int
    after_locked: int
    related_type: Optional[str] = None
    related_id: Optional[int] = None
    related_description: Optional[str] = None
    operated_by: Optional[int] = None
    operated_by_name: Optional[str] = None


class InventoryFlowNodeDetailResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    date: str
    movement_count: int
    total_abs_delta: int
    positive_delta_on_hand: int
    negative_delta_on_hand_abs: int
    items: List[InventoryFlowNodeRecordResponse]
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
WorkOrderStatus = Literal["pending", "in_progress", "completed", "terminated"]
StageType = Literal["picking", "staging", "shipping"]


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
    timeout_revert_count: int = 0
    last_reverted_at: Optional[datetime] = None
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


class OrderPendingUpdateRequest(BaseModel):
    priority: OrderPriority
    description: Optional[str] = None
    items: List[OrderItemCreate] = Field(min_length=1)


class OrderCancelRequest(BaseModel):
    cancellation_reason: str = Field(min_length=1, max_length=500)


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
    timeout_revert_count: int = 0
    last_reverted_at: Optional[datetime] = None
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
    timeout_revert_count: int = 0
    last_reverted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    total_amount: int
    total_items: int
    items: List[OrderDetailItemResponse]


class AdminWorkOrderListItemResponse(BaseModel):
    id: int
    order_id: int
    order_no: str
    stage_id: int
    stage_type: StageType
    warehouse_id: int
    warehouse_name: str
    worker_id: int
    worker_name: str
    dispatcher_id: int
    dispatcher_name: str
    status: WorkOrderStatus
    priority: OrderPriority
    source: Literal["manual", "agent"]
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AdminWorkOrderListResponse(BaseModel):
    items: List[AdminWorkOrderListItemResponse]
    total: int


class DashboardKpiResponse(BaseModel):
    pending_acceptance_orders: int
    low_stock_alerts: int
    cancelled_orders_today: int
    accepted_no_dispatch_orders: int


class DashboardDistributionItemResponse(BaseModel):
    key: str
    label: str
    value: int


class DashboardWarehouseLoadItemResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    load_percent: int
    qty_on_hand: int
    capacity: int


class DashboardLowStockItemResponse(BaseModel):
    inventory_id: int
    warehouse_id: int
    warehouse_name: str
    product_id: int
    sku: str
    product_name: str
    qty_available: int
    qty_threshold: int


class DashboardAlertItemResponse(BaseModel):
    alert_type: str
    message: str
    order_id: Optional[int] = None
    order_no: Optional[str] = None
    inventory_id: Optional[int] = None
    warehouse_id: Optional[int] = None


class DashboardWarehouseOrderPerformanceItemResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    total_orders: int
    completed_orders: int
    completion_rate: int


class DashboardProductPopularityItemResponse(BaseModel):
    product_id: int
    sku: str
    product_name: str
    total_qty: int
    order_count: int


class DashboardDispatcherOrderPerformanceItemResponse(BaseModel):
    dispatcher_id: int
    dispatcher_name: str
    total_orders: int
    completed_orders: int
    completion_rate: int


class AdminWarehouseDispatcherPerformanceResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    total_orders: int
    completed_orders: int
    completion_rate: int
    dispatchers: List[DashboardDispatcherOrderPerformanceItemResponse]


class AdminDashboardOverviewResponse(BaseModel):
    kpis: DashboardKpiResponse
    orders_status_distribution: List[DashboardDistributionItemResponse]
    warehouse_loads: List[DashboardWarehouseLoadItemResponse]
    low_stock_top: List[DashboardLowStockItemResponse]
    warehouse_order_performance: List[DashboardWarehouseOrderPerformanceItemResponse]
    product_popularity: List[DashboardProductPopularityItemResponse]
    alerts: List[DashboardAlertItemResponse]


class AdminReportGenerateRequest(BaseModel):
    period_start: date
    period_end: date
    warehouse_id: Optional[int] = Field(default=None, ge=1)
    include_llm_analysis: bool = True


class AdminReportWorkflowTraceItemResponse(BaseModel):
    timestamp: str
    model: Optional[str] = None
    status: str
    detail: Optional[str] = None


class AdminReportResponse(BaseModel):
    id: int
    generated_by: int
    target_user_id: Optional[int] = None
    period_start: date
    period_end: date
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    stats_json: dict[str, Any] = Field(default_factory=dict)
    content: str
    content_format: Literal["markdown"] = "markdown"
    llm_workflow_trace: List[AdminReportWorkflowTraceItemResponse] = Field(default_factory=list)
    created_at: datetime


class AdminReportListItemResponse(BaseModel):
    id: int
    generated_by: int
    generated_by_name: Optional[str] = None
    period_start: date
    period_end: date
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    created_at: datetime


class AdminReportListResponse(BaseModel):
    items: List[AdminReportListItemResponse]
    total: int
