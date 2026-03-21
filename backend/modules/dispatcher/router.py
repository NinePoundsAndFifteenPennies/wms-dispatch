from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules.auth.dependencies import get_current_user_required
from modules.dispatcher.dependencies import get_dispatcher_service
from modules.dispatcher.schemas import (
    DispatcherCreateWorkOrderRequest,
    DispatcherDashboardSummaryResponse,
    DispatcherManualCompleteStageRequest,
    DispatcherOrderDetailResponse,
    DispatcherOrderListResponse,
    DispatcherOrderWorkOrderListResponse,
    DispatcherOrderWorkOrderResponse,
    DispatcherTerminateWorkOrderRequest,
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
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_orders(
        user_id=current_user.get("id"),
        for_my_orders=True,
        search=search,
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


@router.get("/workers", response_model=list[DispatcherWorkerOptionResponse])
async def list_dispatcher_workers(
    search: Optional[str] = Query(default=None),
    service: DispatcherService = Depends(get_dispatcher_service),
    current_user=Depends(require_dispatcher_user),
):
    return await service.list_workers(user_id=current_user.get("id"), search=search)


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


router.include_router(orders_router)
router.include_router(my_orders_router)
