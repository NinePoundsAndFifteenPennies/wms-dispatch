from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


OrderStatus = Literal["pending_acceptance", "in_progress", "completed", "cancelled"]
OrderPriority = Literal["high", "medium", "low"]
StageType = Literal["picking", "staging", "shipping"]
StageStatus = Literal["not_started", "in_progress", "completed"]
CompletionType = Literal["auto", "manual"]
WorkOrderStatus = Literal["pending", "in_progress", "completed", "terminated"]


class DispatcherOrderListItemResponse(BaseModel):
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
    updated_at: datetime
    total_amount: int
    total_items: int


class DispatcherOrderListResponse(BaseModel):
    items: List[DispatcherOrderListItemResponse]
    total: int


class DispatcherOrderDetailItemResponse(BaseModel):
    id: int
    product_id: int
    product_sku: str
    product_name: str
    product_category: Optional[str] = None
    qty: int
    unit_price: int
    subtotal: int


class StageWorkOrderSummaryResponse(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    terminated: int


class DispatcherOrderStageResponse(BaseModel):
    id: int
    stage_type: StageType
    status: StageStatus
    completion_type: Optional[CompletionType] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[int] = None
    remark: Optional[str] = None
    created_at: datetime
    work_orders: StageWorkOrderSummaryResponse


class DispatcherOrderWorkOrderSummaryResponse(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    terminated: int


class DispatcherOrderDetailResponse(BaseModel):
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
    updated_at: datetime
    total_amount: int
    total_items: int
    items: List[DispatcherOrderDetailItemResponse]
    stages: List[DispatcherOrderStageResponse]
    work_order_summary: DispatcherOrderWorkOrderSummaryResponse


class DispatcherDashboardSummaryResponse(BaseModel):
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    pending_count: int
    my_orders_count: int
    my_in_progress_count: int
    my_completed_count: int
    my_cancelled_count: int


class DispatcherWarehouseInventoryItemResponse(BaseModel):
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


class DispatcherWarehouseSummaryResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    is_active: bool


class DispatcherWarehouseInventoryResponse(BaseModel):
    warehouse: DispatcherWarehouseSummaryResponse
    items: List[DispatcherWarehouseInventoryItemResponse]
    total: int
