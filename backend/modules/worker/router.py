from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules.auth.dependencies import get_current_user_required
from modules.dispatcher.schemas import (
    WorkerCompleteWorkOrderRequest,
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
    status_filter: Optional[str] = Query(default=None, alias="status"),
    service: WorkerService = Depends(get_worker_service),
    current_user=Depends(require_worker_user),
):
    return await service.list_my_work_orders(user_id=current_user.get("id"), status_filter=status_filter)


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
