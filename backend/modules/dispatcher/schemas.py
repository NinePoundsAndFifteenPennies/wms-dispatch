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
AssignmentRiskCode = Literal["skill_gap", "worker_overload"]
TransferStatus = Literal["pending", "approved", "rejected", "cancelled", "completed"]
InboundStatus = Literal["pending", "confirmed"]


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
    req_skill_picking: int
    req_skill_staging: int
    req_skill_shipping: int
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


class DispatcherInventoryFlowPointResponse(BaseModel):
    date: str
    movement_count: int
    total_abs_delta: int


class DispatcherInventoryFlowTrendResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    points: List[DispatcherInventoryFlowPointResponse]


class DispatcherInventoryFlowNodeRecordResponse(BaseModel):
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


class DispatcherInventoryFlowNodeDetailResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    date: str
    movement_count: int
    total_abs_delta: int
    positive_delta_on_hand: int
    negative_delta_on_hand_abs: int
    items: List[DispatcherInventoryFlowNodeRecordResponse]
    total: int


class DispatcherWorkerOptionResponse(BaseModel):
    id: int
    username: str
    email: str
    skill_picking: int
    skill_staging: int
    skill_shipping: int
    pending_count: int = 0
    in_progress_count: int = 0
    active_work_order_count: int = 0
    active_work_order_limit: int = 5


class DispatcherWorkOrderPrecheckRequest(BaseModel):
    stage_id: int
    worker_id: int


class DispatcherWorkOrderRiskResponse(BaseModel):
    code: AssignmentRiskCode
    message: str


class DispatcherSkillProductBreakdownResponse(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    required_skill: int
    worker_skill: int
    is_qualified: bool


class DispatcherCreateWorkOrderRequest(BaseModel):
    stage_id: int
    worker_id: int
    priority: OrderPriority = "medium"
    deadline: Optional[datetime] = None
    description: Optional[str] = None
    override_reason: Optional[str] = Field(default=None, max_length=500)
    source: WorkOrderSource = "manual"


class DispatcherWorkOrderPrecheckResponse(BaseModel):
    stage_id: int
    stage_type: StageType
    required_skill_min: int
    required_skill_max: int
    worker_skill: int
    active_work_order_count: int
    active_work_order_limit: int
    has_risk: bool
    risks: List[DispatcherWorkOrderRiskResponse]
    skill_products: List[DispatcherSkillProductBreakdownResponse] = Field(default_factory=list)


class DispatcherTerminateWorkOrderRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class DispatcherManualCompleteStageRequest(BaseModel):
    remark: str = Field(min_length=1, max_length=1000)


class DispatcherCancelOrderRequest(BaseModel):
    cancellation_reason: str = Field(min_length=1, max_length=500)


class DispatcherOrderWorkOrderResponse(BaseModel):
    id: int
    order_id: int
    order_no: Optional[str] = None
    customer_name: Optional[str] = None
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
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WorkerWorkOrderListResponse(BaseModel):
    items: List[WorkerWorkOrderResponse]
    total: int


class WorkerWorkOrderDetailItemResponse(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    product_cover_image: Optional[str] = None
    qty: int
    req_skill_picking: int
    req_skill_staging: int
    req_skill_shipping: int
    current_stage_required_skill: int
    worker_stage_skill: int
    is_skill_matched: bool


class WorkerWorkOrderDetailResponse(WorkerWorkOrderResponse):
    terminated_at: Optional[datetime] = None
    terminated_by: Optional[int] = None
    termination_reason: Optional[str] = None
    worker_stage_skill: int = 0
    stage_required_skill_min: int = 0
    stage_required_skill_max: int = 0
    order_items: List[WorkerWorkOrderDetailItemResponse] = Field(default_factory=list)


class WorkerCompleteWorkOrderRequest(BaseModel):
    note: Optional[WorkerWorkOrderNotePayload] = None


class DispatcherAgentSuggestWorkOrderRequest(BaseModel):
    intent: Optional[str] = Field(default=None, max_length=500)
    search_worker: Optional[str] = Field(default=None, max_length=100)


class DispatcherAgentWorkerScoreResponse(BaseModel):
    speedup: float
    load: float
    load_penalty: float
    final_score: float


class DispatcherAgentWorkerSummaryResponse(BaseModel):
    worker_id: int
    worker_name: str
    worker_skill: int
    pending_count: int
    in_progress_count: int
    active_work_order_count: int
    active_work_order_limit: int


class DispatcherAgentStageSuggestionResponse(BaseModel):
    stage_id: int
    stage_type: StageType
    assignable: bool
    reason: Optional[str] = None
    required_skill_min: int
    required_skill_max: int
    has_risk: bool
    risks: List[DispatcherWorkOrderRiskResponse] = Field(default_factory=list)
    worker: Optional[DispatcherAgentWorkerSummaryResponse] = None
    score: Optional[DispatcherAgentWorkerScoreResponse] = None
    priority: Optional[OrderPriority] = None
    suggested_description: Optional[str] = None


class DispatcherAgentSuggestWorkOrderResponse(BaseModel):
    order_id: int
    stages: List[DispatcherAgentStageSuggestionResponse]


class DispatcherAgentConfirmStageOverrideRequest(BaseModel):
    stage_id: int
    override_reason: Optional[str] = Field(default=None, max_length=500)


class DispatcherAgentConfirmWorkOrderRequest(BaseModel):
    intent: Optional[str] = Field(default=None, max_length=500)
    stage_overrides: List[DispatcherAgentConfirmStageOverrideRequest] = Field(default_factory=list)


class DispatcherAgentConfirmStageResultResponse(BaseModel):
    stage_id: int
    stage_type: StageType
    status: Literal["created", "unassignable"]
    reason: Optional[str] = None
    has_risk: bool = False
    risks: List[DispatcherWorkOrderRiskResponse] = Field(default_factory=list)
    work_order_id: Optional[int] = None


class DispatcherAgentConfirmWorkOrderResponse(BaseModel):
    order_id: int
    created_work_orders: List[DispatcherOrderWorkOrderResponse] = Field(default_factory=list)
    stages: List[DispatcherAgentConfirmStageResultResponse] = Field(default_factory=list)


class DispatcherTransferCreateRequest(BaseModel):
    from_warehouse_id: int
    review_dispatcher_id: int
    product_id: int
    qty: int = Field(gt=0)
    description: Optional[str] = Field(default=None, max_length=1000)


class DispatcherTransferReviewRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)


class DispatcherTransferExecuteRequest(BaseModel):
    expected_arrival_at: Optional[datetime] = None


class DispatcherTransferProductOptionResponse(BaseModel):
    product_id: int
    sku: str
    product_name: str
    qty_available: int


class DispatcherTransferWarehouseOptionResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None


class DispatcherTransferDispatcherOptionResponse(BaseModel):
    id: int
    username: str
    email: str


class DispatcherInboundRecordResponse(BaseModel):
    id: int
    transfer_order_id: int
    warehouse_id: int
    warehouse_name: Optional[str] = None
    product_id: int
    product_sku: str
    product_name: str
    qty: int
    status: InboundStatus
    expected_arrival_at: Optional[datetime] = None
    confirmed_by: Optional[int] = None
    confirmed_by_name: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class DispatcherTransferResponse(BaseModel):
    id: int
    code: str
    product_id: int
    product_sku: str
    product_name: str
    from_warehouse_id: int
    from_warehouse_name: str
    to_warehouse_id: int
    to_warehouse_name: str
    requested_by: int
    requested_by_name: Optional[str] = None
    review_dispatcher_id: Optional[int] = None
    review_dispatcher_name: Optional[str] = None
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    qty: int
    status: TransferStatus
    description: Optional[str] = None
    rejection_reason: Optional[str] = None
    source: Literal["manual", "agent"]
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    inbound_record: Optional[DispatcherInboundRecordResponse] = None


class DispatcherTransferListResponse(BaseModel):
    items: List[DispatcherTransferResponse]
    total: int


class DispatcherInboundRecordListResponse(BaseModel):
    items: List[DispatcherInboundRecordResponse]
    total: int
