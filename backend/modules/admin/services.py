import base64
import csv
from datetime import date, datetime
from io import BytesIO, StringIO
from typing import List, Optional
from zoneinfo import ZoneInfo
import bcrypt
from fastapi import HTTPException, UploadFile
from sqlalchemy import select, func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models.customer import Customer
from models.inventory import Inventory
from models.order import Order
from models.order_item import OrderItem
from models.product import Product
from models.user import User
from models.warehouse import Warehouse
from modules.admin.schemas import (
    CustomerCreate,
    CustomerUpdate,
    OrderCreate,
    OrderPendingUpdateRequest,
    ProductCreate,
    ProductUpdate,
    StocktakeAdjustRequest,
    UserCreate,
    UserStatusUpdate,
    UserUpdate,
    WarehouseCreate,
    WarehouseInboundRequest,
    WarehouseInventoryItemResponse,
    WarehouseUpdate,
)
from modules.shared.storage import save_image_file
from modules.shared.storage import delete_resource_file_by_url

SYSTEM_TIMEZONE = "Asia/Shanghai"

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode("utf-8")

class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _build_work_order_filters(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        stage_type: Optional[str] = None,
        priority: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        worker_id: Optional[int] = None,
        dispatcher_id: Optional[int] = None,
    ):
        clauses = ["1=1"]
        params = {}

        if search:
            clauses.append(
                "(" \
                "o.order_no ILIKE :search OR " \
                "w.username ILIKE :search OR " \
                "d.username ILIKE :search OR " \
                "wh.name ILIKE :search" \
                ")"
            )
            params["search"] = f"%{search}%"

        if status:
            clauses.append("wo.status = :status")
            params["status"] = status

        if stage_type:
            clauses.append("os.stage_type = :stage_type")
            params["stage_type"] = stage_type

        if priority:
            clauses.append("wo.priority = :priority")
            params["priority"] = priority

        if warehouse_id is not None:
            clauses.append("wo.warehouse_id = :warehouse_id")
            params["warehouse_id"] = warehouse_id

        if worker_id is not None:
            clauses.append("wo.worker_id = :worker_id")
            params["worker_id"] = worker_id

        if dispatcher_id is not None:
            clauses.append("wo.dispatcher_id = :dispatcher_id")
            params["dispatcher_id"] = dispatcher_id

        return " AND ".join(clauses), params

    async def list_work_orders(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: Optional[str] = None,
        stage_type: Optional[str] = None,
        priority: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        worker_id: Optional[int] = None,
        dispatcher_id: Optional[int] = None,
    ):
        where_sql, params = self._build_work_order_filters(
            search=search,
            status=status,
            stage_type=stage_type,
            priority=priority,
            warehouse_id=warehouse_id,
            worker_id=worker_id,
            dispatcher_id=dispatcher_id,
        )

        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM work_orders wo
                JOIN orders o ON o.id = wo.order_id
                JOIN order_stages os ON os.id = wo.stage_id
                JOIN users w ON w.id = wo.worker_id
                JOIN users d ON d.id = wo.dispatcher_id
                JOIN warehouses wh ON wh.id = wo.warehouse_id
                WHERE {where_sql}
                """
            ),
            params,
        )
        total = count_result.scalar_one() or 0

        query_params = {
            **params,
            "offset": (page - 1) * page_size,
            "limit": page_size,
        }

        rows = await self.session.execute(
            text(
                f"""
                SELECT
                    wo.id,
                    wo.order_id,
                    o.order_no,
                    wo.stage_id,
                    os.stage_type,
                    wo.warehouse_id,
                    wh.name AS warehouse_name,
                    wo.worker_id,
                    w.username AS worker_name,
                    wo.dispatcher_id,
                    d.username AS dispatcher_name,
                    wo.status,
                    wo.priority,
                    wo.source,
                    wo.description,
                    wo.deadline,
                    wo.assigned_at,
                    wo.started_at,
                    wo.completed_at,
                    wo.terminated_at,
                    wo.created_at,
                    wo.updated_at
                FROM work_orders wo
                JOIN orders o ON o.id = wo.order_id
                JOIN order_stages os ON os.id = wo.stage_id
                JOIN users w ON w.id = wo.worker_id
                JOIN users d ON d.id = wo.dispatcher_id
                JOIN warehouses wh ON wh.id = wo.warehouse_id
                WHERE {where_sql}
                ORDER BY wo.updated_at DESC, wo.id DESC
                OFFSET :offset
                LIMIT :limit
                """
            ),
            query_params,
        )

        return {
            "items": [dict(row) for row in rows.mappings().all()],
            "total": total,
        }

    async def list_users(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(User)
        if search:
            stmt = stmt.where(or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
            
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        
        stmt = stmt.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        
        return {"items": items, "total": total}

    async def create_user(self, user_data: UserCreate) -> User:
        if user_data.role != "admin" and not user_data.warehouse_id:
            raise HTTPException(status_code=400, detail="warehouse_id is required for non-admin users")
            
        # Check duplicate
        existing = await self.session.execute(select(User).where(or_(User.username == user_data.username, User.email == user_data.email)))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username or email already exists")

        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            password=hashed_password,
            email=user_data.email,
            role=user_data.role,
            warehouse_id=user_data.warehouse_id,
            skill_picking=user_data.skill_picking,
            skill_staging=user_data.skill_staging,
            skill_shipping=user_data.skill_shipping,
            is_active=True
        )
        self.session.add(new_user)
        try:
            await self.session.commit()
            await self.session.refresh(new_user)
            return new_user
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        curr_role = user_data.role if user_data.role is not None else user.role
        curr_wh = user_data.warehouse_id if user_data.warehouse_id is not None else user.warehouse_id
        if curr_role != "admin" and not curr_wh:
            raise HTTPException(status_code=400, detail="warehouse_id is required for non-admin users")

        if user_data.username is not None:
            user.username = user_data.username
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.role is not None:
            user.role = user_data.role
        if user_data.warehouse_id is not None:
            user.warehouse_id = user_data.warehouse_id
        if user_data.skill_picking is not None:
            user.skill_picking = user_data.skill_picking
        if user_data.skill_staging is not None:
            user.skill_staging = user_data.skill_staging
        if user_data.skill_shipping is not None:
            user.skill_shipping = user_data.skill_shipping

        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail="Update failed, check for duplicate username/email")

    async def update_user_status(self, user_id: int, status_update: UserStatusUpdate) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.role == "admin" and not status_update.is_active:
            raise HTTPException(status_code=400, detail="Admin account cannot be disabled")

        user.is_active = status_update.is_active
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def batch_disable_users(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(User).where(User.id.in_(ids), User.is_active.is_(True), User.role != "admin")
        )
        users = result.scalars().all()
        if not users:
            return 0

        for user in users:
            user.is_active = False
        await self.session.commit()
        return len(users)

    async def list_warehouses(self) -> List[Warehouse]:
        result = await self.session.execute(select(Warehouse).order_by(Warehouse.id.asc()))
        return result.scalars().all()

    async def list_warehouses_manage(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(Warehouse)
        if search:
            stmt = stmt.where(
                or_(
                    Warehouse.name.ilike(f"%{search}%"),
                    Warehouse.address.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(Warehouse.id.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return {"items": items, "total": total}

    async def create_warehouse(self, warehouse_data: WarehouseCreate) -> Warehouse:
        existing = await self.session.execute(select(Warehouse).where(Warehouse.name == warehouse_data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Warehouse name already exists")

        warehouse = Warehouse(**warehouse_data.model_dump())
        self.session.add(warehouse)
        try:
            await self.session.commit()
            await self.session.refresh(warehouse)
            return warehouse
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_warehouse(self, warehouse_id: int, warehouse_data: WarehouseUpdate) -> Warehouse:
        result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        update_data = warehouse_data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != warehouse.name:
            existing = await self.session.execute(select(Warehouse).where(Warehouse.name == update_data["name"]))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Warehouse name already exists")

        for field_name, value in update_data.items():
            setattr(warehouse, field_name, value)

        try:
            await self.session.commit()
            await self.session.refresh(warehouse)
            return warehouse
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def delete_warehouse(self, warehouse_id: int) -> None:
        result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        warehouse.is_active = False
        await self.session.commit()

    async def update_warehouse_status(self, warehouse_id: int, is_active: bool) -> Warehouse:
        result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        warehouse.is_active = is_active
        await self.session.commit()
        await self.session.refresh(warehouse)
        return warehouse

    async def batch_delete_warehouses(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id.in_(ids), Warehouse.is_active.is_(True))
        )
        warehouses = result.scalars().all()
        if not warehouses:
            return 0

        for warehouse in warehouses:
            warehouse.is_active = False
        await self.session.commit()
        return len(warehouses)

    async def upload_warehouse_image(self, warehouse_id: int, image: UploadFile) -> Warehouse:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        old_image_path = warehouse.cover_image
        saved_path = await save_image_file(
            upload_file=image,
            bucket="warehouse_covers",
            entity_prefix="warehouse",
            entity_id=warehouse_id,
        )
        warehouse.cover_image = saved_path

        try:
            await self.session.commit()
            await self.session.refresh(warehouse)
        except Exception as e:
            await self.session.rollback()
            delete_resource_file_by_url(saved_path)
            raise HTTPException(status_code=400, detail=str(e))

        if old_image_path and old_image_path != saved_path:
            delete_resource_file_by_url(old_image_path)
        return warehouse

    async def get_warehouse_inventory(
        self,
        warehouse_id: int,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ):
        warehouse_result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = warehouse_result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        stmt = (
            select(Inventory, Product)
            .join(Product, Product.id == Inventory.product_id)
            .where(Inventory.warehouse_id == warehouse_id)
        )
        if search:
            stmt = stmt.where(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.sku.ilike(f"%{search}%"),
                    Product.category.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = (
            stmt.order_by(Product.name.asc(), Product.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        items = [
            WarehouseInventoryItemResponse(
                id=inventory.id,
                product_id=inventory.product_id,
                sku=product.sku,
                product_name=product.name,
                category=product.category,
                product_cover_image=product.cover_image,
                product_is_active=product.is_active,
                qty_on_hand=inventory.qty_on_hand,
                qty_reserved=inventory.qty_reserved,
                qty_locked=inventory.qty_locked,
                qty_threshold=inventory.qty_threshold,
                qty_available=inventory.qty_available,
            )
            for inventory, product in rows
        ]

        return {"warehouse": warehouse, "items": items, "total": total}

    async def adjust_warehouse_inventory_stocktake(
        self,
        warehouse_id: int,
        inventory_id: int,
        payload: StocktakeAdjustRequest,
        operated_by: Optional[int] = None,
    ):
        warehouse_result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = warehouse_result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        if not warehouse.is_active:
            raise HTTPException(status_code=400, detail="禁用仓库不支持盘点修正")

        result = await self.session.execute(
            select(Inventory)
            .where(Inventory.id == inventory_id)
            .where(Inventory.warehouse_id == warehouse_id)
        )
        inventory = result.scalar_one_or_none()
        if not inventory:
            raise HTTPException(status_code=404, detail="Inventory record not found")

        product_result = await self.session.execute(
            select(Product).where(Product.id == inventory.product_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if not product.is_active:
            raise HTTPException(status_code=400, detail="下架商品不支持盘点修正")

        if payload.qty_on_hand is None and payload.qty_threshold is None:
            raise HTTPException(status_code=400, detail="请至少修改现存量或阈值中的一项")

        before_on_hand = inventory.qty_on_hand
        before_threshold = inventory.qty_threshold
        after_on_hand = before_on_hand if payload.qty_on_hand is None else payload.qty_on_hand
        after_threshold = before_threshold if payload.qty_threshold is None else payload.qty_threshold

        min_on_hand = inventory.qty_reserved + inventory.qty_locked
        if after_on_hand < min_on_hand:
            raise HTTPException(
                status_code=400,
                detail=f"盘点后的现存量不能低于预留量与锁定量之和（{min_on_hand}）",
            )

        before_reserved = inventory.qty_reserved
        before_locked = inventory.qty_locked
        delta_on_hand = after_on_hand - before_on_hand

        inventory.qty_on_hand = after_on_hand
        inventory.qty_threshold = after_threshold

        try:
            await self.session.flush()

            stocktake_insert = await self.session.execute(
                text(
                    """
                    INSERT INTO stocktakes (
                        inventory_id,
                        before_on_hand,
                        after_on_hand,
                        delta_on_hand,
                        reason
                    ) VALUES (
                        :inventory_id,
                        :before_on_hand,
                        :after_on_hand,
                        :delta_on_hand,
                        :reason
                    )
                    RETURNING id
                    """
                ),
                {
                    "inventory_id": inventory.id,
                    "before_on_hand": before_on_hand,
                    "after_on_hand": after_on_hand,
                    "delta_on_hand": delta_on_hand,
                    "reason": payload.reason,
                },
            )
            stocktake_id = stocktake_insert.scalar_one()

            await self.session.execute(
                text(
                    """
                    INSERT INTO inventory_movements (
                        inventory_id,
                        warehouse_id,
                        product_id,
                        change_type,
                        delta_on_hand,
                        delta_reserved,
                        delta_locked,
                        before_on_hand,
                        before_reserved,
                        before_locked,
                        after_on_hand,
                        after_reserved,
                        after_locked,
                        related_type,
                        related_id,
                        operated_by
                    ) VALUES (
                        :inventory_id,
                        :warehouse_id,
                        :product_id,
                        :change_type,
                        :delta_on_hand,
                        :delta_reserved,
                        :delta_locked,
                        :before_on_hand,
                        :before_reserved,
                        :before_locked,
                        :after_on_hand,
                        :after_reserved,
                        :after_locked,
                        :related_type,
                        :related_id,
                        :operated_by
                    )
                    """
                ),
                {
                    "inventory_id": inventory.id,
                    "warehouse_id": warehouse_id,
                    "product_id": inventory.product_id,
                    "change_type": "stocktake_adjust",
                    "delta_on_hand": delta_on_hand,
                    "delta_reserved": 0,
                    "delta_locked": 0,
                    "before_on_hand": before_on_hand,
                    "before_reserved": before_reserved,
                    "before_locked": before_locked,
                    "after_on_hand": after_on_hand,
                    "after_reserved": before_reserved,
                    "after_locked": before_locked,
                    "related_type": "stocktake",
                    "related_id": stocktake_id,
                    "operated_by": operated_by,
                },
            )

            await self.session.commit()
            await self.session.refresh(inventory)
            return {"inventory": inventory, "stocktake_id": stocktake_id}
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=f"Stocktake adjust failed: {str(e)}")

    async def warehouse_inventory_inbound(
        self,
        warehouse_id: int,
        payload: WarehouseInboundRequest,
        operated_by: Optional[int] = None,
    ):
        warehouse_result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = warehouse_result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        if not warehouse.is_active:
            raise HTTPException(status_code=400, detail="禁用仓库不支持进货")

        product_result = await self.session.execute(
            select(Product).where(Product.id == payload.product_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if not product.is_active:
            raise HTTPException(status_code=400, detail="下架商品不能进货")

        inventory_result = await self.session.execute(
            select(Inventory)
            .where(Inventory.warehouse_id == warehouse_id)
            .where(Inventory.product_id == payload.product_id)
        )
        inventory = inventory_result.scalar_one_or_none()

        if not inventory:
            inventory = Inventory(
                warehouse_id=warehouse_id,
                product_id=payload.product_id,
                qty_on_hand=0,
                qty_reserved=0,
                qty_locked=0,
                qty_threshold=0,
            )
            self.session.add(inventory)
            await self.session.flush()

        before_on_hand = inventory.qty_on_hand
        before_reserved = inventory.qty_reserved
        before_locked = inventory.qty_locked
        after_on_hand = before_on_hand + payload.qty

        inventory.qty_on_hand = after_on_hand

        reason_prefix = payload.reason.strip() if payload.reason else ""
        inbound_reason = f"{reason_prefix}：进了{payload.qty}个{product.name}" if reason_prefix else f"进了{payload.qty}个{product.name}"

        try:
            await self.session.flush()

            stocktake_insert = await self.session.execute(
                text(
                    """
                    INSERT INTO stocktakes (
                        inventory_id,
                        before_on_hand,
                        after_on_hand,
                        delta_on_hand,
                        reason
                    ) VALUES (
                        :inventory_id,
                        :before_on_hand,
                        :after_on_hand,
                        :delta_on_hand,
                        :reason
                    )
                    RETURNING id
                    """
                ),
                {
                    "inventory_id": inventory.id,
                    "before_on_hand": before_on_hand,
                    "after_on_hand": after_on_hand,
                    "delta_on_hand": payload.qty,
                    "reason": inbound_reason,
                },
            )
            stocktake_id = stocktake_insert.scalar_one()

            movement_insert = await self.session.execute(
                text(
                    """
                    INSERT INTO inventory_movements (
                        inventory_id,
                        warehouse_id,
                        product_id,
                        change_type,
                        delta_on_hand,
                        delta_reserved,
                        delta_locked,
                        before_on_hand,
                        before_reserved,
                        before_locked,
                        after_on_hand,
                        after_reserved,
                        after_locked,
                        related_type,
                        related_id,
                        operated_by
                    ) VALUES (
                        :inventory_id,
                        :warehouse_id,
                        :product_id,
                        :change_type,
                        :delta_on_hand,
                        :delta_reserved,
                        :delta_locked,
                        :before_on_hand,
                        :before_reserved,
                        :before_locked,
                        :after_on_hand,
                        :after_reserved,
                        :after_locked,
                        :related_type,
                        :related_id,
                        :operated_by
                    )
                    RETURNING id
                    """
                ),
                {
                    "inventory_id": inventory.id,
                    "warehouse_id": warehouse_id,
                    "product_id": payload.product_id,
                    "change_type": "inbound_confirm",
                    "delta_on_hand": payload.qty,
                    "delta_reserved": 0,
                    "delta_locked": 0,
                    "before_on_hand": before_on_hand,
                    "before_reserved": before_reserved,
                    "before_locked": before_locked,
                    "after_on_hand": after_on_hand,
                    "after_reserved": before_reserved,
                    "after_locked": before_locked,
                    "related_type": "stocktake",
                    "related_id": stocktake_id,
                    "operated_by": operated_by,
                },
            )
            movement_id = movement_insert.scalar_one()

            await self.session.commit()
            await self.session.refresh(inventory)
            return {"inventory": inventory, "movement_id": movement_id}
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=f"Inbound failed: {str(e)}")

    async def remove_warehouse_image(self, warehouse_id: int) -> Warehouse:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        old_image_path = warehouse.cover_image
        warehouse.cover_image = None
        if old_image_path and not delete_resource_file_by_url(old_image_path):
            await self.session.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete warehouse image file")
        await self.session.commit()
        await self.session.refresh(warehouse)
        return warehouse

    async def list_customers(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(Customer)
        if search:
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Customer.contact.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(Customer.id.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return {"items": items, "total": total}

    async def list_customers_options(self, search: Optional[str] = None):
        stmt = select(Customer).order_by(Customer.id.desc())
        if search:
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Customer.contact.ilike(f"%{search}%"),
                )
            )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_customer(self, customer_data: CustomerCreate) -> Customer:
        customer = Customer(
            name=customer_data.name,
            contact=customer_data.contact,
            address=customer_data.address,
            description=customer_data.description,
            is_active=True,
        )
        self.session.add(customer)
        try:
            await self.session.commit()
            await self.session.refresh(customer)
            return customer
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_customer(self, customer_id: int, customer_data: CustomerUpdate) -> Customer:
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        update_data = customer_data.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(customer, field_name, value)

        try:
            await self.session.commit()
            await self.session.refresh(customer)
            return customer
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def delete_customer(self, customer_id: int) -> None:
        result = await self.session.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        customer.is_active = False
        await self.session.commit()

    async def update_customer_status(self, customer_id: int, is_active: bool) -> Customer:
        result = await self.session.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        customer.is_active = is_active
        await self.session.commit()
        await self.session.refresh(customer)
        return customer

    async def batch_delete_customers(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(Customer).where(Customer.id.in_(ids), Customer.is_active.is_(True))
        )
        customers = result.scalars().all()
        if not customers:
            return 0

        for customer in customers:
            customer.is_active = False
        await self.session.commit()
        return len(customers)

    def _build_order_filters(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        clauses = ["1=1"]
        params = {}
        if search:
            clauses.append("(o.order_no ILIKE :search OR c.name ILIKE :search)")
            params["search"] = f"%{search}%"
        if status:
            clauses.append("o.status = :status")
            params["status"] = status
        if start_date:
            clauses.append("DATE(o.created_at) >= :start_date")
            params["start_date"] = start_date
        if end_date:
            clauses.append("DATE(o.created_at) <= :end_date")
            params["end_date"] = end_date
        return " AND ".join(clauses), params

    async def list_orders(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        where_sql, params = self._build_order_filters(
            search=search,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE {where_sql}
                """
            ),
            params,
        )
        total = count_result.scalar_one() or 0

        query_params = {
            **params,
            "offset": (page - 1) * page_size,
            "limit": page_size,
        }
        rows = await self.session.execute(
            text(
                f"""
                SELECT
                    o.id,
                    o.order_no,
                    o.customer_id,
                    c.name AS customer_name,
                    o.warehouse_id,
                    w.name AS warehouse_name,
                    o.dispatcher_id,
                    u.username AS dispatcher_name,
                    o.description,
                    o.status,
                    o.priority,
                    o.accepted_at,
                    o.completed_at,
                    o.cancelled_at,
                    o.created_at,
                    COALESCE(SUM(oi.qty * oi.unit_price), 0)::INTEGER AS total_amount,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_items
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN warehouses w ON w.id = o.warehouse_id
                LEFT JOIN users u ON u.id = o.dispatcher_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE {where_sql}
                GROUP BY o.id, c.name, w.name, u.username
                ORDER BY o.id DESC
                OFFSET :offset
                LIMIT :limit
                """
            ),
            query_params,
        )
        items = [dict(row) for row in rows.mappings().all()]
        return {"items": items, "total": total}

    async def _next_order_no(self) -> str:
        prefix = f"OD-{datetime.now().strftime('%y%m%d')}"
        seq_result = await self.session.execute(
            text(
                """
                SELECT COALESCE(MAX(CAST(split_part(order_no, '-', 3) AS INTEGER)), 0)
                FROM orders
                WHERE order_no LIKE :prefix
                """
            ),
            {"prefix": f"{prefix}-%"},
        )
        seq = (seq_result.scalar_one() or 0) + 1
        return f"{prefix}-{seq:03d}"

    async def create_order(self, payload: OrderCreate) -> Order:
        customer_result = await self.session.execute(select(Customer).where(Customer.id == payload.customer_id))
        customer = customer_result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        if not customer.is_active:
            raise HTTPException(status_code=400, detail="Inactive customer cannot be selected")

        product_ids = [item.product_id for item in payload.items]
        if len(set(product_ids)) != len(product_ids):
            raise HTTPException(status_code=400, detail="Duplicate product in order items is not allowed")

        products_result = await self.session.execute(
            select(Product).where(Product.id.in_(product_ids), Product.is_active.is_(True))
        )
        valid_products = products_result.scalars().all()
        if len(valid_products) != len(product_ids):
            raise HTTPException(status_code=400, detail="Order items contain unavailable products")

        for _ in range(3):
            order_no = await self._next_order_no()
            order = Order(
                order_no=order_no,
                customer_id=payload.customer_id,
                description=payload.description,
                priority=payload.priority,
                status="pending_acceptance",
            )
            self.session.add(order)
            try:
                await self.session.flush()
                for item in payload.items:
                    self.session.add(
                        OrderItem(
                            order_id=order.id,
                            product_id=item.product_id,
                            qty=item.qty,
                            unit_price=item.unit_price,
                        )
                    )
                await self.session.commit()
                await self.session.refresh(order)
                return order
            except IntegrityError:
                await self.session.rollback()
                continue
            except Exception as e:
                await self.session.rollback()
                raise HTTPException(status_code=400, detail=str(e))

        raise HTTPException(status_code=409, detail="Failed to generate unique order number")

    async def update_pending_order(self, order_id: int, payload: OrderPendingUpdateRequest):
        order_result = await self.session.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != "pending_acceptance":
            raise HTTPException(status_code=400, detail="Only pending orders can be edited")

        product_ids = [item.product_id for item in payload.items]
        if len(set(product_ids)) != len(product_ids):
            raise HTTPException(status_code=400, detail="Duplicate product in order items is not allowed")

        products_result = await self.session.execute(select(Product.id).where(Product.id.in_(product_ids)))
        existing_product_ids = {row[0] for row in products_result.all()}
        if existing_product_ids != set(product_ids):
            raise HTTPException(status_code=400, detail="Order items contain invalid products")

        try:
            order.priority = payload.priority
            order.description = payload.description
            order.updated_at = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)

            await self.session.execute(text("DELETE FROM order_items WHERE order_id = :order_id"), {"order_id": order.id})

            for item in payload.items:
                self.session.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=item.product_id,
                        qty=item.qty,
                        unit_price=item.unit_price,
                    )
                )

            await self.session.commit()
            return await self.get_order_detail(order.id)
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=f"Update order failed: {str(e)}")

    async def cancel_pending_order(self, order_id: int, cancellation_reason: str, cancelled_by: Optional[int] = None):
        order_result = await self.session.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != "pending_acceptance":
            raise HTTPException(status_code=400, detail="Only pending orders can be cancelled by admin here")

        reason = (cancellation_reason or "").strip()
        if not reason:
            raise HTTPException(status_code=400, detail="Cancellation reason is required")

        order.status = "cancelled"
        order.cancelled_at = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)
        order.cancelled_by = cancelled_by
        order.cancellation_reason = reason
        order.updated_at = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)

        await self.session.commit()
        return await self.get_order_detail(order.id)

    async def reopen_cancelled_order(self, order_id: int):
        source_order_result = await self.session.execute(select(Order).where(Order.id == order_id))
        source_order = source_order_result.scalar_one_or_none()
        if not source_order:
            raise HTTPException(status_code=404, detail="Order not found")
        if source_order.status != "cancelled":
            raise HTTPException(status_code=400, detail="Only cancelled orders can be reopened")

        source_items_result = await self.session.execute(
            select(OrderItem).where(OrderItem.order_id == source_order.id).order_by(OrderItem.id.asc())
        )
        source_items = source_items_result.scalars().all()
        if not source_items:
            raise HTTPException(status_code=400, detail="Cancelled order has no items to reopen")

        for _ in range(3):
            order_no = await self._next_order_no()
            new_order = Order(
                order_no=order_no,
                customer_id=source_order.customer_id,
                description=source_order.description,
                priority=source_order.priority,
                status="pending_acceptance",
            )
            self.session.add(new_order)
            try:
                await self.session.flush()
                for item in source_items:
                    self.session.add(
                        OrderItem(
                            order_id=new_order.id,
                            product_id=item.product_id,
                            qty=item.qty,
                            unit_price=item.unit_price,
                        )
                    )
                await self.session.commit()
                return await self.get_order_detail(new_order.id)
            except IntegrityError:
                await self.session.rollback()
                continue
            except Exception as e:
                await self.session.rollback()
                raise HTTPException(status_code=400, detail=f"Reopen order failed: {str(e)}")

        raise HTTPException(status_code=409, detail="Failed to generate unique order number")

    async def get_order_detail(self, order_id: int):
        order_result = await self.session.execute(
            text(
                """
                SELECT
                    o.id,
                    o.order_no,
                    o.customer_id,
                    c.name AS customer_name,
                    c.contact AS customer_contact,
                    c.address AS customer_address,
                    o.warehouse_id,
                    w.name AS warehouse_name,
                    o.dispatcher_id,
                    u.username AS dispatcher_name,
                    o.description,
                    o.status,
                    o.priority,
                    o.accepted_at,
                    o.completed_at,
                    o.cancelled_at,
                    o.cancelled_by,
                    o.cancellation_reason,
                    o.created_at,
                    COALESCE(SUM(oi.qty * oi.unit_price), 0)::INTEGER AS total_amount,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_items
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN warehouses w ON w.id = o.warehouse_id
                LEFT JOIN users u ON u.id = o.dispatcher_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.id = :order_id
                GROUP BY o.id, c.name, c.contact, c.address, w.name, u.username
                """
            ),
            {"order_id": order_id},
        )
        order = order_result.mappings().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        items_result = await self.session.execute(
            text(
                """
                SELECT
                    oi.id,
                    oi.product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    p.category AS product_category,
                    oi.qty,
                    oi.unit_price,
                    (oi.qty * oi.unit_price)::INTEGER AS subtotal
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = :order_id
                ORDER BY oi.id ASC
                """
            ),
            {"order_id": order_id},
        )

        return {**dict(order), "items": [dict(row) for row in items_result.mappings().all()]}

    async def export_orders(
        self,
        export_format: str = "csv",
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        where_sql, params = self._build_order_filters(
            search=search,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
        rows = await self.session.execute(
            text(
                f"""
                SELECT
                    o.order_no,
                    c.name AS customer_name,
                    COALESCE(w.name, '-') AS warehouse_name,
                    o.priority,
                    o.status,
                    COALESCE(u.username, '-') AS dispatcher_name,
                    o.created_at,
                    COALESCE(SUM(oi.qty * oi.unit_price), 0)::INTEGER AS total_amount,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_items
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN warehouses w ON w.id = o.warehouse_id
                LEFT JOIN users u ON u.id = o.dispatcher_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE {where_sql}
                GROUP BY o.id, c.name, w.name, u.username
                ORDER BY o.id DESC
                """
            ),
            params,
        )
        items = [dict(row) for row in rows.mappings().all()]

        title_parts = ["orders"]
        if search:
            title_parts.append(f"search-{search}")
        if status:
            title_parts.append(f"status-{status}")
        if start_date:
            title_parts.append(f"from-{start_date}")
        if end_date:
            title_parts.append(f"to-{end_date}")
        title = "_".join(title_parts)

        if export_format == "markdown":
            lines = [
                f"# Orders Export ({len(items)})",
                "",
                "| 订单号 | 客户 | 仓库 | 优先级 | 状态 | 责任调度员 | 创建时间 | 总件数 | 总金额(元) |",
                "|---|---|---|---|---|---|---|---:|---:|",
            ]
            for row in items:
                lines.append(
                    f"| {row['order_no']} | {row['customer_name']} | {row['warehouse_name']} | {row['priority']} | {row['status']} | {row['dispatcher_name']} | {row['created_at']} | {row['total_items']} | {row['total_amount']} |"
                )
            return {
                "filename": f"{title}.md",
                "mime_type": "text/markdown; charset=utf-8",
                "content": "\n".join(lines),
            }

        if export_format == "pdf":
            content = self._build_orders_list_pdf(items)
            return {
                "filename": f"{title}.pdf",
                "mime_type": "application/pdf",
                "content_base64": base64.b64encode(content).decode("utf-8"),
            }

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["order_no", "customer", "warehouse", "priority", "status", "dispatcher", "created_at", "total_items", "total_amount"])
        for row in items:
            writer.writerow(
                [
                    row["order_no"],
                    row["customer_name"],
                    row["warehouse_name"],
                    row["priority"],
                    row["status"],
                    row["dispatcher_name"],
                    row["created_at"],
                    row["total_items"],
                    row["total_amount"],
                ]
            )
        return {
            "filename": f"{title}.csv",
            "mime_type": "text/csv; charset=utf-8",
            "content": f"\ufeff{buffer.getvalue()}",
        }

    async def export_order_detail(self, order_id: int, export_format: str = "pdf"):
        if export_format != "pdf":
            raise HTTPException(status_code=400, detail="Unsupported export format")
        detail = await self.get_order_detail(order_id)
        content = self._build_order_detail_pdf(detail)
        return {
            "filename": f"order_detail_{detail['order_no']}.pdf",
            "mime_type": "application/pdf",
            "content_base64": base64.b64encode(content).decode("utf-8"),
        }

    @staticmethod
    def _register_cn_font():
        try:
            pdfmetrics.getFont("STSong-Light")
        except KeyError:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    @staticmethod
    def _build_pdf_styles():
        styles = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "title_cn",
                parent=styles["Heading1"],
                fontName="STSong-Light",
                fontSize=18,
                leading=24,
                textColor=colors.HexColor("#1f2937"),
            ),
            "subtitle": ParagraphStyle(
                "subtitle_cn",
                parent=styles["Normal"],
                fontName="STSong-Light",
                fontSize=11,
                leading=16,
                textColor=colors.HexColor("#4b5563"),
            ),
            "cell": ParagraphStyle(
                "cell_cn",
                parent=styles["Normal"],
                fontName="STSong-Light",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#111827"),
            ),
            "meta": ParagraphStyle(
                "meta_cn",
                parent=styles["Normal"],
                fontName="STSong-Light",
                fontSize=10.5,
                leading=15,
                textColor=colors.HexColor("#111827"),
            ),
        }

    @staticmethod
    def _safe_pdf_text(value) -> str:
        if value is None:
            return "-"
        text = str(value)
        text = text.replace("\ufeff", "")   # BOM
        text = text.replace("\u200b", "")   # 零宽字符
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _cn_now_str() -> str:
        return datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")

    def _build_orders_list_pdf(self, items: List[dict]) -> bytes:
        self._register_cn_font()
        styles = self._build_pdf_styles()
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=28,
            rightMargin=28,
            topMargin=26,
            bottomMargin=26,
            title="订单列表导出",
            author="WMS Dispatch",
        )

        flowables = [
            Paragraph(self._safe_pdf_text("订单列表导出"), styles["title"]),
            Spacer(1, 8),
            Paragraph(f"导出时间：{self._cn_now_str()}　条数：{len(items)}", styles["subtitle"]),
            Spacer(1, 10),
        ]

        table_rows = [
            ["订单号", "客户", "仓库", "优先级", "状态", "责任调度员", "创建时间", "总件数", "总金额(元)"]
        ]
        for row in items:
            table_rows.append(
                [
                    Paragraph(self._safe_pdf_text(row["order_no"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["customer_name"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["warehouse_name"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["priority"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["status"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["dispatcher_name"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["created_at"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["total_items"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["total_amount"]), styles["cell"]),
                ]
            )

        table = Table(
            table_rows,
            repeatRows=1,
            colWidths=[72, 66, 58, 40, 52, 62, 84, 40, 58],
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10.5),
                    ("FONTSIZE", (0, 1), (-1, -1), 9.5),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                    ("ALIGN", (7, 1), (8, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flowables.append(table)
        doc.build(flowables)
        return buffer.getvalue()

    def _build_order_detail_pdf(self, detail: dict) -> bytes:
        self._register_cn_font()
        styles = self._build_pdf_styles()
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=28,
            rightMargin=28,
            topMargin=26,
            bottomMargin=26,
            title=f"订单详情-{detail['order_no']}",
            author="WMS Dispatch",
        )

        flowables = [
            Paragraph(self._safe_pdf_text(f"订单详情导出 --- {detail['order_no']}"),styles["title"]),
            Spacer(1, 8),
            Paragraph(f"导出时间：{self._cn_now_str()}", styles["subtitle"]),
            Spacer(1, 8),
        ]

        meta_rows = [
            [Paragraph("<b>订单号</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["order_no"]), styles["meta"])],
            [Paragraph("<b>客户</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["customer_name"]), styles["meta"])],
            [Paragraph("<b>客户联系方式</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["customer_contact"]), styles["meta"])],
            [Paragraph("<b>仓库</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["warehouse_name"]), styles["meta"])],
            [Paragraph("<b>责任调度员</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["dispatcher_name"]), styles["meta"])],
            [Paragraph("<b>状态 / 优先级</b>", styles["meta"]), Paragraph(f"{self._safe_pdf_text(detail['status'])} / {self._safe_pdf_text(detail['priority'])}", styles["meta"])],
            [Paragraph("<b>创建时间</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["created_at"]), styles["meta"])],
            [Paragraph("<b>总件数 / 总金额(元)</b>", styles["meta"]), Paragraph(f"{self._safe_pdf_text(detail['total_items'])} / {self._safe_pdf_text(detail['total_amount'])}", styles["meta"])],
        ]
        meta_table = Table(meta_rows, colWidths=[120, 390])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flowables.extend([meta_table, Spacer(1, 12), Paragraph("订单明细", styles["subtitle"]), Spacer(1, 6)])

        detail_rows = [["SKU", "产品名称", "类别", "数量", "单价(元)", "小计(元)"]]
        for item in detail["items"]:
            detail_rows.append(
                [
                    Paragraph(self._safe_pdf_text(item["product_sku"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["product_name"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["product_category"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["qty"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["unit_price"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["subtotal"]), styles["cell"]),
                ]
            )

        detail_table = Table(detail_rows, repeatRows=1, colWidths=[68, 170, 80, 48, 62, 62])
        detail_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
                    ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bfdbfe")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flowables.append(detail_table)
        doc.build(flowables)
        return buffer.getvalue()

    async def list_products(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(Product)
        if search:
            stmt = stmt.where(
                or_(
                    Product.sku.ilike(f"%{search}%"),
                    Product.name.ilike(f"%{search}%"),
                    Product.category.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return {"items": items, "total": total}

    async def create_product(self, product_data: ProductCreate) -> Product:
        existing = await self.session.execute(select(Product).where(Product.sku == product_data.sku))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="SKU already exists")

        product = Product(**product_data.model_dump())
        self.session.add(product)
        try:
            await self.session.commit()
            await self.session.refresh(product)
            return product
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_product(self, product_id: int, product_data: ProductUpdate) -> Product:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        update_data = product_data.model_dump(exclude_unset=True)
        if "sku" in update_data and update_data["sku"] != product.sku:
            existing = await self.session.execute(select(Product).where(Product.sku == update_data["sku"]))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="SKU already exists")

        for field_name, value in update_data.items():
            setattr(product, field_name, value)

        try:
            await self.session.commit()
            await self.session.refresh(product)
            return product
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def delete_product(self, product_id: int) -> None:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product.is_active = False
        await self.session.commit()

    async def update_product_status(self, product_id: int, is_active: bool) -> Product:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product.is_active = is_active
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def batch_delete_products(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(Product).where(Product.id.in_(ids), Product.is_active.is_(True))
        )
        products = result.scalars().all()
        if not products:
            return 0

        for product in products:
            product.is_active = False
        await self.session.commit()
        return len(products)

    async def upload_product_image(self, product_id: int, image: UploadFile) -> Product:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        old_image_path = product.cover_image
        saved_path = await save_image_file(
            upload_file=image,
            bucket="product_images",
            entity_prefix="product",
            entity_id=product_id,
        )
        product.cover_image = saved_path

        try:
            await self.session.commit()
            await self.session.refresh(product)
        except Exception as e:
            await self.session.rollback()
            delete_resource_file_by_url(saved_path)
            raise HTTPException(status_code=400, detail=str(e))

        if old_image_path and old_image_path != saved_path:
            delete_resource_file_by_url(old_image_path)
        return product

    async def remove_product_image(self, product_id: int) -> Product:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        old_image_path = product.cover_image
        product.cover_image = None
        await self.session.commit()
        await self.session.refresh(product)

        delete_resource_file_by_url(old_image_path)
        return product
