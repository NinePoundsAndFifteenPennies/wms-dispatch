from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from modules.admin.schemas import (
    ActiveStatusUpdate,
    BatchDeleteRequest,
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    StocktakeAdjustRequest,
    UserCreate, 
    UserUpdate, 
    UserStatusUpdate, 
    UserResponse, 
    WarehouseCreate,
    WarehouseInventoryResponse,
    WarehouseListResponse,
    WarehouseOptionResponse,
    WarehouseResponse,
    WarehouseUpdate,
    UserListResponse
)
from modules.admin.services import AdminService
from modules.admin.dependencies import get_admin_service
from modules.auth.dependencies import get_current_user_required

router = APIRouter()
users_router = APIRouter(prefix="/admin/users", tags=["Admin Users"])
warehouses_router = APIRouter(prefix="/admin/warehouses", tags=["Admin Warehouses"])
customers_router = APIRouter(prefix="/admin/customers", tags=["Admin Customers"])
products_router = APIRouter(prefix="/admin/products", tags=["Admin Products"])

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


@users_router.post("/batch-disable")
async def batch_disable_users(payload: BatchDeleteRequest, service: AdminService = Depends(get_admin_service)):
    disabled = await service.batch_disable_users(payload.ids)
    return {"disabled": disabled}


@warehouses_router.get("", response_model=List[WarehouseResponse])
async def list_warehouses(service: AdminService = Depends(get_admin_service)):
    return await service.list_warehouses()


@warehouses_router.get("/options", response_model=List[WarehouseOptionResponse])
async def list_warehouse_options(service: AdminService = Depends(get_admin_service)):
    return await service.list_warehouses()


@warehouses_router.get("/manage", response_model=WarehouseListResponse)
async def list_warehouses_manage(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_warehouses_manage(page=page, page_size=page_size, search=search)


@warehouses_router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    service: AdminService = Depends(get_admin_service),
):
    return await service.create_warehouse(warehouse_data)


@warehouses_router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: int,
    warehouse_data: WarehouseUpdate,
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_warehouse(warehouse_id, warehouse_data)


@warehouses_router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(warehouse_id: int, service: AdminService = Depends(get_admin_service)):
    await service.delete_warehouse(warehouse_id)


@warehouses_router.post("/batch-delete")
async def batch_delete_warehouses(payload: BatchDeleteRequest, service: AdminService = Depends(get_admin_service)):
    deleted = await service.batch_delete_warehouses(payload.ids)
    return {"deleted": deleted}


@warehouses_router.patch("/{warehouse_id}/status", response_model=WarehouseResponse)
async def update_warehouse_status(
    warehouse_id: int,
    status_update: ActiveStatusUpdate,
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_warehouse_status(warehouse_id, status_update.is_active)


@warehouses_router.post("/{warehouse_id}/image", response_model=WarehouseResponse)
async def upload_warehouse_image(
    warehouse_id: int,
    image: UploadFile = File(...),
    service: AdminService = Depends(get_admin_service),
):
    return await service.upload_warehouse_image(warehouse_id, image)


@warehouses_router.delete("/{warehouse_id}/image", response_model=WarehouseResponse)
async def remove_warehouse_image(
    warehouse_id: int,
    service: AdminService = Depends(get_admin_service),
):
    return await service.remove_warehouse_image(warehouse_id)


@warehouses_router.get("/{warehouse_id}/inventory", response_model=WarehouseInventoryResponse)
async def get_warehouse_inventory(
    warehouse_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_warehouse_inventory(
        warehouse_id=warehouse_id,
        page=page,
        page_size=page_size,
        search=search,
    )


@warehouses_router.patch("/{warehouse_id}/inventory/{inventory_id}/stocktake")
async def adjust_inventory_stocktake(
    warehouse_id: int,
    inventory_id: int,
    payload: StocktakeAdjustRequest,
    service: AdminService = Depends(get_admin_service),
    current_user=Depends(get_current_user_required),
):
    updated = await service.adjust_warehouse_inventory_stocktake(
        warehouse_id=warehouse_id,
        inventory_id=inventory_id,
        payload=payload,
        operated_by=current_user.get("id"),
    )
    inventory = updated["inventory"]
    return {
        "id": inventory.id,
        "qty_on_hand": inventory.qty_on_hand,
        "qty_available": inventory.qty_available,
        "stocktake_id": updated["stocktake_id"],
    }


@customers_router.get("", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_customers(page=page, page_size=page_size, search=search)


@customers_router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(customer_data: CustomerCreate, service: AdminService = Depends(get_admin_service)):
    return await service.create_customer(customer_data)


@customers_router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_customer(customer_id, customer_data)


@customers_router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: int, service: AdminService = Depends(get_admin_service)):
    await service.delete_customer(customer_id)


@customers_router.post("/batch-delete")
async def batch_delete_customers(payload: BatchDeleteRequest, service: AdminService = Depends(get_admin_service)):
    deleted = await service.batch_delete_customers(payload.ids)
    return {"deleted": deleted}


@customers_router.patch("/{customer_id}/status", response_model=CustomerResponse)
async def update_customer_status(
    customer_id: int,
    status_update: ActiveStatusUpdate,
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_customer_status(customer_id, status_update.is_active)


@products_router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_products(page=page, page_size=page_size, search=search)


@products_router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(product_data: ProductCreate, service: AdminService = Depends(get_admin_service)):
    return await service.create_product(product_data)


@products_router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_product(product_id, product_data)


@products_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, service: AdminService = Depends(get_admin_service)):
    await service.delete_product(product_id)


@products_router.post("/batch-delete")
async def batch_delete_products(payload: BatchDeleteRequest, service: AdminService = Depends(get_admin_service)):
    deleted = await service.batch_delete_products(payload.ids)
    return {"deleted": deleted}


@products_router.patch("/{product_id}/status", response_model=ProductResponse)
async def update_product_status(
    product_id: int,
    status_update: ActiveStatusUpdate,
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_product_status(product_id, status_update.is_active)


@products_router.post("/{product_id}/image", response_model=ProductResponse)
async def upload_product_image(
    product_id: int,
    image: UploadFile = File(...),
    service: AdminService = Depends(get_admin_service),
):
    return await service.upload_product_image(product_id, image)


@products_router.delete("/{product_id}/image", response_model=ProductResponse)
async def remove_product_image(
    product_id: int,
    service: AdminService = Depends(get_admin_service),
):
    return await service.remove_product_image(product_id)

router.include_router(users_router)
router.include_router(warehouses_router)
router.include_router(customers_router)
router.include_router(products_router)
