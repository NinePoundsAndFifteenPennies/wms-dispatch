from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


OrderStatus = Literal["pending_acceptance", "in_progress", "completed", "cancelled"]
OrderPriority = Literal["high", "medium", "low"]
StageType = Literal["picking", "staging", "shipping"]
StageStatus = Literal["not_started", "in_progress", "completed"]
CompletionType = Literal["auto", "manual"]
WorkOrderStatus = Literal["pending", "in_progress", "completed", "terminated"]
WorkOrderSource = Literal["manual", "agent"]
WorkOrderNoteType = Literal["normal", "damaged", "qty_mismatch", "other"]


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


class DispatcherWorkerOptionResponse(BaseModel):
    id: int
    username: str
    email: str
    skill_picking: int
    skill_staging: int
    skill_shipping: int


class DispatcherCreateWorkOrderRequest(BaseModel):
    stage_id: int
    worker_id: int
    priority: OrderPriority = "medium"
    deadline: Optional[datetime] = None
    description: Optional[str] = None


class DispatcherTerminateWorkOrderRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class DispatcherManualCompleteStageRequest(BaseModel):
    remark: str = Field(min_length=1, max_length=1000)


class DispatcherCancelOrderRequest(BaseModel):
    cancellation_reason: str = Field(min_length=1, max_length=500)


class DispatcherOrderWorkOrderResponse(BaseModel):
    id: int
    order_id: int
    stage_id: int
    stage_type: StageType
    worker_id: int
    worker_name: str
    dispatcher_id: int
    warehouse_id: int
    status: WorkOrderStatus
    priority: OrderPriority
    deadline: Optional[datetime] = None
    description: Optional[str] = None
    source: WorkOrderSource
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    terminated_by: Optional[int] = None
    termination_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DispatcherOrderWorkOrderListResponse(BaseModel):
    items: List[DispatcherOrderWorkOrderResponse]
    total: int


class WorkerWorkOrderNotePayload(BaseModel):
    note_type: WorkOrderNoteType = "normal"
    content: str = Field(min_length=1, max_length=2000)


class WorkerWorkOrderResponse(BaseModel):
    id: int
    order_id: int
    order_no: str
    stage_id: int
    stage_type: StageType
    dispatcher_name: Optional[str] = None
    status: WorkOrderStatus
    priority: OrderPriority
    deadline: Optional[datetime] = None
    description: Optional[str] = None
    source: WorkOrderSource
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WorkerWorkOrderListResponse(BaseModel):
    items: List[WorkerWorkOrderResponse]
    total: int


class WorkerCompleteWorkOrderRequest(BaseModel):
    note: Optional[WorkerWorkOrderNotePayload] = None
