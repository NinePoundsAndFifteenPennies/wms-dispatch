from typing import List, Optional

from fastapi import APIRouter, Depends, status, Query

from modules.admin.schemas import (
    UserCreate, 
    UserUpdate, 
    UserStatusUpdate, 
    UserResponse, 
    WarehouseResponse,
    UserListResponse
)
from modules.admin.services import AdminService
from modules.admin.dependencies import get_admin_service

router = APIRouter()
users_router = APIRouter(prefix="/admin/users", tags=["Admin Users"])
warehouses_router = APIRouter(prefix="/admin/warehouses", tags=["Admin Warehouses"])

@users_router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service)
):
    return await service.list_users(page=page, page_size=page_size, search=search)

@users_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate, 
    service: AdminService = Depends(get_admin_service)
):
    return await service.create_user(user_data)

@users_router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, 
    user_data: UserUpdate, 
    service: AdminService = Depends(get_admin_service)
):
    return await service.update_user(user_id, user_data)

@users_router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int, 
    status_update: UserStatusUpdate, 
    service: AdminService = Depends(get_admin_service)
):
    return await service.update_user_status(user_id, status_update)


@warehouses_router.get("", response_model=List[WarehouseResponse])
async def list_warehouses(service: AdminService = Depends(get_admin_service)):
    return await service.list_warehouses()

router.include_router(users_router)
router.include_router(warehouses_router)

