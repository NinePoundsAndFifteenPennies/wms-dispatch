from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules.auth.dependencies import get_current_user_required
from modules.dispatcher.schemas import (
    WorkerCompleteWorkOrderRequest,
    WorkerWorkOrderDetailResponse,
    WorkerWorkOrderListResponse,
)
from modules.worker.dependencies import get_worker_service
from modules.worker.services import WorkerService


router = APIRouter(prefix="/worker", tags=["Worker"])


async def require_worker_user(current_user=Depends(get_current_user_required)):
    if current_user.get("role") != "worker":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return current_user


worker_only = [Depends(require_worker_user)]
work_orders_router = APIRouter(prefix="/work-orders", tags=["Worker Work Orders"], dependencies=worker_only)


@work_orders_router.get("", response_model=WorkerWorkOrderListResponse)
async def list_my_work_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    stage_type: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    service: WorkerService = Depends(get_worker_service),
    current_user=Depends(require_worker_user),
):
    return await service.list_my_work_orders(
        user_id=current_user.get("id"),
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        stage_type=stage_type,
        priority=priority,
    )


@work_orders_router.get("/{work_order_id}", response_model=WorkerWorkOrderDetailResponse)
async def get_my_work_order_detail(
    work_order_id: int,
    service: WorkerService = Depends(get_worker_service),
    current_user=Depends(require_worker_user),
):
    return await service.get_my_work_order_detail(work_order_id=work_order_id, user_id=current_user.get("id"))


@work_orders_router.patch("/{work_order_id}/start")
async def start_work_order(
    work_order_id: int,
    service: WorkerService = Depends(get_worker_service),
    current_user=Depends(require_worker_user),
):
    await service.start_work_order(work_order_id=work_order_id, user_id=current_user.get("id"))
    return {"id": work_order_id, "status": "in_progress"}


@work_orders_router.patch("/{work_order_id}/complete")
async def complete_work_order(
    work_order_id: int,
    payload: WorkerCompleteWorkOrderRequest,
    service: WorkerService = Depends(get_worker_service),
    current_user=Depends(require_worker_user),
):
    await service.complete_work_order(
        work_order_id=work_order_id,
        user_id=current_user.get("id"),
        note_type=payload.note.note_type if payload.note else None,
        note_content=payload.note.content if payload.note else None,
    )
    return {"id": work_order_id, "status": "completed"}


router.include_router(work_orders_router)
