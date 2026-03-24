from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from modules.admin.schemas import (
    ActiveStatusUpdate,
    AdminDashboardOverviewResponse,
    AdminInventoryFlowTrendListResponse,
    AdminWarehouseDispatcherPerformanceResponse,
    AdminWorkOrderListResponse,
    BatchDeleteRequest,
    CustomerCreate,
    OrderCreate,
    OrderCancelRequest,
    OrderCreateResponse,
    OrderDetailResponse,
    OrderListResponse,
    OrderPendingUpdateRequest,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    StocktakeAdjustRequest,
    InventoryFlowNodeDetailResponse,
    WarehouseInboundRequest,
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
from modules.auth.dependencies import get_current_user_required, require_admin_user

router = APIRouter()
admin_only = [Depends(require_admin_user)]
users_router = APIRouter(prefix="/admin/users", tags=["Admin Users"], dependencies=admin_only)
warehouses_router = APIRouter(prefix="/admin/warehouses", tags=["Admin Warehouses"], dependencies=admin_only)
customers_router = APIRouter(prefix="/admin/customers", tags=["Admin Customers"], dependencies=admin_only)
products_router = APIRouter(prefix="/admin/products", tags=["Admin Products"], dependencies=admin_only)
orders_router = APIRouter(prefix="/admin/orders", tags=["Admin Orders"], dependencies=admin_only)
work_orders_router = APIRouter(prefix="/admin/work-orders", tags=["Admin Work Orders"], dependencies=admin_only)


@router.get("/admin/dashboard-overview", response_model=AdminDashboardOverviewResponse, dependencies=admin_only)
async def get_admin_dashboard_overview(service: AdminService = Depends(get_admin_service)):
    return await service.get_dashboard_overview()


@router.get(
    "/admin/dashboard-overview/warehouse-performance/{warehouse_id}",
    response_model=AdminWarehouseDispatcherPerformanceResponse,
    dependencies=admin_only,
)
async def get_dashboard_warehouse_dispatcher_performance(
    warehouse_id: int,
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_warehouse_dispatcher_performance(warehouse_id)

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


@warehouses_router.get("/inventory-movements/trends", response_model=AdminInventoryFlowTrendListResponse)
async def get_inventory_flow_trends(
    days: int = Query(14, ge=1, le=90),
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_inventory_flow_trends(days=days)


@warehouses_router.get("/{warehouse_id}/inventory-movements/node-details", response_model=InventoryFlowNodeDetailResponse)
async def get_warehouse_inventory_flow_node_details(
    warehouse_id: int,
    date: date,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_warehouse_inventory_flow_node_details(
        warehouse_id=warehouse_id,
        target_date=date,
        page=page,
        page_size=page_size,
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
        "qty_threshold": inventory.qty_threshold,
        "qty_available": inventory.qty_available,
        "stocktake_id": updated["stocktake_id"],
    }


@warehouses_router.post("/{warehouse_id}/inventory/inbound")
async def warehouse_inventory_inbound(
    warehouse_id: int,
    payload: WarehouseInboundRequest,
    service: AdminService = Depends(get_admin_service),
    current_user=Depends(get_current_user_required),
):
    updated = await service.warehouse_inventory_inbound(
        warehouse_id=warehouse_id,
        payload=payload,
        operated_by=current_user.get("id"),
    )
    inventory = updated["inventory"]
    return {
        "id": inventory.id,
        "qty_on_hand": inventory.qty_on_hand,
        "qty_threshold": inventory.qty_threshold,
        "qty_available": inventory.qty_available,
        "movement_id": updated["movement_id"],
    }


@customers_router.get("", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_customers(page=page, page_size=page_size, search=search)


@customers_router.get("/options", response_model=List[CustomerResponse])
async def list_customer_options(
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_customers_options(search=search)


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


@products_router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, service: AdminService = Depends(get_admin_service)):
    return await service.get_product(product_id)


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


@orders_router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = Query(default=None, pattern="^(pending_acceptance|in_progress|completed|cancelled)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_orders(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )


@orders_router.get("/export")
async def export_orders(
    export_format: str = Query(default="csv", pattern="^(csv|markdown|pdf)$"),
    search: Optional[str] = None,
    status: Optional[str] = Query(default=None, pattern="^(pending_acceptance|in_progress|completed|cancelled)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    service: AdminService = Depends(get_admin_service),
):
    return await service.export_orders(
        export_format=export_format,
        search=search,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )


@orders_router.get("/{order_id}/export")
async def export_order_detail(
    order_id: int,
    export_format: str = Query(default="pdf", pattern="^(pdf)$"),
    service: AdminService = Depends(get_admin_service),
):
    return await service.export_order_detail(order_id, export_format=export_format)


@orders_router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(order_id: int, service: AdminService = Depends(get_admin_service)):
    return await service.get_order_detail(order_id)


@orders_router.post("", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, service: AdminService = Depends(get_admin_service)):
    return await service.create_order(payload)


@orders_router.patch("/{order_id}/pending", response_model=OrderDetailResponse)
async def update_pending_order(
    order_id: int,
    payload: OrderPendingUpdateRequest,
    service: AdminService = Depends(get_admin_service),
):
    return await service.update_pending_order(order_id, payload)


@orders_router.post("/{order_id}/cancel", response_model=OrderDetailResponse)
async def cancel_pending_order(
    order_id: int,
    payload: OrderCancelRequest,
    service: AdminService = Depends(get_admin_service),
    current_user=Depends(get_current_user_required),
):
    return await service.cancel_pending_order(
        order_id,
        payload.cancellation_reason,
        cancelled_by=current_user.get("id"),
    )


@orders_router.post("/{order_id}/reopen", response_model=OrderDetailResponse)
async def reopen_cancelled_order(
    order_id: int,
    service: AdminService = Depends(get_admin_service),
):
    return await service.reopen_cancelled_order(order_id)


@work_orders_router.get("", response_model=AdminWorkOrderListResponse)
async def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None, pattern="^(pending|in_progress|completed|terminated)$"),
    stage_type: Optional[str] = Query(default=None, pattern="^(picking|staging|shipping)$"),
    priority: Optional[str] = Query(default=None, pattern="^(high|medium|low)$"),
    warehouse_id: Optional[int] = Query(default=None, ge=1),
    worker_id: Optional[int] = Query(default=None, ge=1),
    dispatcher_id: Optional[int] = Query(default=None, ge=1),
    service: AdminService = Depends(get_admin_service),
):
    return await service.list_work_orders(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        stage_type=stage_type,
        priority=priority,
        warehouse_id=warehouse_id,
        worker_id=worker_id,
        dispatcher_id=dispatcher_id,
    )

router.include_router(users_router)
router.include_router(warehouses_router)
router.include_router(customers_router)
router.include_router(products_router)
router.include_router(orders_router)
router.include_router(work_orders_router)
