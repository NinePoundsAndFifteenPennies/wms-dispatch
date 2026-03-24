from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules.auth.dependencies import get_current_user_required
from modules.dispatcher.dependencies import get_dispatcher_service
from modules.dispatcher.schemas import (
    DispatcherAgentConfirmWorkOrderResponse,
    DispatcherAgentConfirmWorkOrderRequest,
    DispatcherAgentSuggestWorkOrderRequest,
    DispatcherAgentSuggestWorkOrderResponse,
    DispatcherCancelOrderRequest,
    DispatcherInboundRecordListResponse,
    DispatcherInboundRecordResponse,
    DispatcherCreateWorkOrderRequest,
    DispatcherDashboardSummaryResponse,
    DispatcherInventoryFlowNodeDetailResponse,
    DispatcherInventoryFlowTrendResponse,
    DispatcherManualCompleteStageRequest,
    DispatcherOrderDetailResponse,
    DispatcherOrderListResponse,
    DispatcherOrderWorkOrderListResponse,
    DispatcherOrderWorkOrderResponse,
    DispatcherTerminateWorkOrderRequest,
    DispatcherTransferCreateRequest,
    DispatcherTransferExecuteRequest,
    DispatcherTransferDispatcherOptionResponse,
    DispatcherTransferListResponse,
    DispatcherTransferProductOptionResponse,
    DispatcherTransferResponse,
    DispatcherTransferReviewRequest,
    DispatcherTransferWarehouseOptionResponse,
    DispatcherWorkOrderPrecheckRequest,
    DispatcherWorkOrderPrecheckResponse,
    DispatcherWorkerOptionResponse,
    DispatcherWarehouseInventoryResponse,
)
from modules.dispatcher.services import DispatcherService
router = APIRouter(prefix="/dispatcher", tags=["Dispatcher"])


async def require_dispatcher_user(current_user=Depends(get_current_user_required)):
    if current_user.get("role") != "dispatcher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return current_user


dispatcher_only = [Depends(require_dispatcher_user)]

orders_router = APIRouter(prefix="/orders", tags=["Dispatcher Orders"], dependencies=dispatcher_only)
my_orders_router = APIRouter(prefix="/my-orders", tags=["Dispatcher My Orders"], dependencies=dispatcher_only)
transfers_router = APIRouter(prefix="/transfers", tags=["Dispatcher Transfers"], dependencies=dispatcher_only)


@orders_router.get("", response_model=DispatcherOrderListResponse)
async def list_pending_orders(
    search: Optional[str] = Query(default=None),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_orders(
        user_id=current_user.get("id"),
        for_my_orders=False,
        search=search,
    )


@orders_router.get("/{order_id}", response_model=DispatcherOrderDetailResponse)
async def get_pending_order_detail(
    order_id: int,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.get_order_detail(
        order_id=order_id,
        user_id=current_user.get("id"),
        for_my_orders=False,
    )


@orders_router.post("/{order_id}/accept", response_model=DispatcherOrderDetailResponse)
async def accept_pending_order(
    order_id: int,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.accept_order(order_id=order_id, user_id=current_user.get("id"))


@my_orders_router.get("", response_model=DispatcherOrderListResponse)
async def list_my_orders(
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_orders(
        user_id=current_user.get("id"),
        for_my_orders=True,
        search=search,
        status_filter=status_filter,
    )


@my_orders_router.get("/{order_id}", response_model=DispatcherOrderDetailResponse)
async def get_my_order_detail(
    order_id: int,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.get_order_detail(
        order_id=order_id,
        user_id=current_user.get("id"),
        for_my_orders=True,
    )


@my_orders_router.post("/{order_id}/cancel", response_model=DispatcherOrderDetailResponse)
async def cancel_my_order(
    order_id: int,
    payload: DispatcherCancelOrderRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.cancel_my_order(
        order_id=order_id,
        user_id=current_user.get("id"),
        cancellation_reason=payload.cancellation_reason,
    )


@router.get("/dashboard-summary", response_model=DispatcherDashboardSummaryResponse)
async def get_dashboard_summary(
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.get_dashboard_summary(user_id=current_user.get("id"))


@router.get("/inventory", response_model=DispatcherWarehouseInventoryResponse)
async def get_dispatcher_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.get_warehouse_inventory(
        user_id=current_user.get("id"),
        page=page,
        page_size=page_size,
        search=search,
    )


@router.get("/inventory-movements/trend", response_model=DispatcherInventoryFlowTrendResponse)
async def get_dispatcher_inventory_flow_trend(
    days: int = Query(14, ge=1, le=90),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.get_inventory_flow_trend(user_id=current_user.get("id"), days=days)


@router.get("/inventory-movements/node-details", response_model=DispatcherInventoryFlowNodeDetailResponse)
async def get_dispatcher_inventory_flow_node_details(
    date: date,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.get_inventory_flow_node_details(
        user_id=current_user.get("id"),
        target_date=date,
        page=page,
        page_size=page_size,
    )


@router.get("/workers", response_model=list[DispatcherWorkerOptionResponse])
async def list_dispatcher_workers(
    search: Optional[str] = Query(default=None),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_workers(user_id=current_user.get("id"), search=search)


@router.get("/work-orders", response_model=DispatcherOrderWorkOrderListResponse)
async def list_dispatcher_work_orders(
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_work_orders(
        user_id=current_user.get("id"),
        search=search,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/orders/{order_id}/work-orders", response_model=DispatcherOrderWorkOrderListResponse)
async def list_order_work_orders(
    order_id: int,
    stage_id: Optional[int] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_order_work_orders(
        order_id=order_id,
        user_id=current_user.get("id"),
        stage_id=stage_id,
        status_filter=status_filter,
    )


@router.post("/orders/{order_id}/work-orders", response_model=DispatcherOrderWorkOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_work_order(
    order_id: int,
    payload: DispatcherCreateWorkOrderRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.create_work_order(
        order_id=order_id,
        user_id=current_user.get("id"),
        payload=payload,
    )


@router.post("/orders/{order_id}/work-orders/precheck", response_model=DispatcherWorkOrderPrecheckResponse)
async def precheck_order_work_order(
    order_id: int,
    payload: DispatcherWorkOrderPrecheckRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.precheck_work_order_assignment(
        order_id=order_id,
        user_id=current_user.get("id"),
        stage_id=payload.stage_id,
        worker_id=payload.worker_id,
    )


@router.post("/agent/orders/{order_id}/work-orders/suggest", response_model=DispatcherAgentSuggestWorkOrderResponse)
async def suggest_order_work_order_by_agent(
    order_id: int,
    payload: DispatcherAgentSuggestWorkOrderRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.suggest_work_order_by_agent(
        order_id=order_id,
        user_id=current_user.get("id"),
        payload=payload,
    )


@router.post("/agent/orders/{order_id}/work-orders/confirm", response_model=DispatcherAgentConfirmWorkOrderResponse)
async def confirm_order_work_order_by_agent(
    order_id: int,
    payload: DispatcherAgentConfirmWorkOrderRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.confirm_agent_work_order(
        order_id=order_id,
        user_id=current_user.get("id"),
        payload=payload,
    )


@router.patch("/work-orders/{work_order_id}/terminate", response_model=DispatcherOrderWorkOrderResponse)
async def terminate_work_order(
    work_order_id: int,
    payload: DispatcherTerminateWorkOrderRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.terminate_work_order(
        work_order_id=work_order_id,
        user_id=current_user.get("id"),
        reason=payload.reason,
    )


@router.post("/orders/{order_id}/stages/{stage_id}/complete", response_model=DispatcherOrderDetailResponse)
async def manual_complete_stage(
    order_id: int,
    stage_id: int,
    payload: DispatcherManualCompleteStageRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    await service.manual_complete_stage(
        order_id=order_id,
        stage_id=stage_id,
        user_id=current_user.get("id"),
        remark=payload.remark,
    )
    return await service.get_order_detail(
        order_id=order_id,
        user_id=current_user.get("id"),
        for_my_orders=True,
    )


@transfers_router.get("", response_model=DispatcherTransferListResponse)
async def list_transfers(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    scope: str = Query(default="all"),
    search: Optional[str] = Query(default=None),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_transfers(
        user_id=current_user.get("id"),
        status_filter=status_filter,
        scope=scope,
        search=search,
    )


@transfers_router.get("/source-warehouses", response_model=list[DispatcherTransferWarehouseOptionResponse])
async def list_transfer_source_warehouses(
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_transfer_source_warehouses(user_id=current_user.get("id"))


@transfers_router.get("/source-inventory", response_model=list[DispatcherTransferProductOptionResponse])
async def list_transfer_source_inventory(
    warehouse_id: int = Query(..., ge=1),
    search: Optional[str] = Query(default=None),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_transfer_source_inventory(
        user_id=current_user.get("id"),
        source_warehouse_id=warehouse_id,
        search=search,
    )


@transfers_router.get("/source-dispatchers", response_model=list[DispatcherTransferDispatcherOptionResponse])
async def list_transfer_source_dispatchers(
    warehouse_id: int = Query(..., ge=1),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_transfer_source_dispatchers(
        user_id=current_user.get("id"),
        source_warehouse_id=warehouse_id,
    )


@transfers_router.post("", response_model=DispatcherTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    payload: DispatcherTransferCreateRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.create_transfer(user_id=current_user.get("id"), payload=payload)


@transfers_router.get("/{transfer_id}", response_model=DispatcherTransferResponse)
async def get_transfer_detail(
    transfer_id: int,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.get_transfer_detail(transfer_id=transfer_id, user_id=current_user.get("id"))


@transfers_router.post("/{transfer_id}/approve", response_model=DispatcherTransferResponse)
async def approve_transfer(
    transfer_id: int,
    payload: DispatcherTransferReviewRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.approve_transfer(
        transfer_id=transfer_id,
        user_id=current_user.get("id"),
        reason=payload.reason,
    )


@transfers_router.post("/{transfer_id}/reject", response_model=DispatcherTransferResponse)
async def reject_transfer(
    transfer_id: int,
    payload: DispatcherTransferReviewRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.reject_transfer(
        transfer_id=transfer_id,
        user_id=current_user.get("id"),
        reason=payload.reason,
    )


@transfers_router.post("/{transfer_id}/execute", response_model=DispatcherTransferResponse)
async def execute_transfer(
    transfer_id: int,
    payload: DispatcherTransferExecuteRequest,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.execute_transfer(
        transfer_id=transfer_id,
        user_id=current_user.get("id"),
        expected_arrival_at=payload.expected_arrival_at,
    )


@router.get("/inbound-records/pending", response_model=DispatcherInboundRecordListResponse)
async def list_pending_inbound_records(
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_pending_inbound_records(user_id=current_user.get("id"))


@router.post("/inbound-records/{record_id}/confirm", response_model=DispatcherInboundRecordResponse)
async def confirm_inbound_record(
    record_id: int,
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.confirm_inbound_record(record_id=record_id, user_id=current_user.get("id"))


router.include_router(orders_router)
router.include_router(my_orders_router)
router.include_router(transfers_router)
