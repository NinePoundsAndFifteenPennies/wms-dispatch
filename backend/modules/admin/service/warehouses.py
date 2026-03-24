from datetime import date, datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, or_, select, text

from models.inventory import Inventory
from models.product import Product
from models.warehouse import Warehouse
from modules.admin.schemas import (
    StocktakeAdjustRequest,
    WarehouseCreate,
    WarehouseInboundRequest,
    WarehouseInventoryItemResponse,
    WarehouseUpdate,
)
from modules.shared.storage import delete_resource_file_by_url, save_image_file

from .base import SYSTEM_TIMEZONE


class WarehouseServiceMixin:
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
        result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
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
        warehouse_result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
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

    async def get_inventory_flow_trends(self, days: int = 14):
        if days < 1 or days > 90:
            raise HTTPException(status_code=400, detail="days must be between 1 and 90")

        warehouses_result = await self.session.execute(
            text(
                """
                SELECT id, name
                FROM warehouses
                ORDER BY name ASC, id ASC
                """
            )
        )
        warehouses = [dict(row) for row in warehouses_result.mappings().all()]
        if not warehouses:
            return {"warehouses": []}

        trend_result = await self.session.execute(
            text(
                """
                SELECT
                    im.warehouse_id,
                    TO_CHAR(im.created_at::date, 'YYYY-MM-DD') AS date,
                    COUNT(*)::INTEGER AS movement_count,
                    COALESCE(SUM(ABS(im.delta_on_hand)), 0)::INTEGER AS total_abs_delta
                FROM inventory_movements im
                WHERE im.created_at::date >= ((NOW() AT TIME ZONE 'Asia/Shanghai')::date - (:days - 1))
                  AND im.delta_on_hand <> 0
                GROUP BY im.warehouse_id, im.created_at::date
                ORDER BY im.warehouse_id ASC, im.created_at::date ASC
                """
            ),
            {"days": days},
        )

        trend_map = {}
        for row in trend_result.mappings().all():
            trend_map[(row["warehouse_id"], row["date"])] = {
                "movement_count": row["movement_count"],
                "total_abs_delta": row["total_abs_delta"],
            }

        end_day = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).date()
        date_labels = [
            (end_day - timedelta(days=offset)).isoformat()
            for offset in range(days - 1, -1, -1)
        ]

        warehouse_series = []
        for wh in warehouses:
            points = []
            for label in date_labels:
                summary = trend_map.get((wh["id"], label), {"movement_count": 0, "total_abs_delta": 0})
                points.append(
                    {
                        "date": label,
                        "movement_count": summary["movement_count"],
                        "total_abs_delta": summary["total_abs_delta"],
                    }
                )

            warehouse_series.append(
                {
                    "warehouse_id": wh["id"],
                    "warehouse_name": wh["name"],
                    "points": points,
                }
            )

        return {"warehouses": warehouse_series}

    async def get_warehouse_inventory_flow_node_details(
        self,
        warehouse_id: int,
        target_date: date,
        page: int = 1,
        page_size: int = 20,
    ):
        warehouse_result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        warehouse = warehouse_result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        params = {
            "warehouse_id": warehouse_id,
            "target_date": target_date,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        summary_result = await self.session.execute(
            text(
                """
                SELECT
                    COALESCE(COUNT(*), 0)::INTEGER AS movement_count,
                    COALESCE(SUM(ABS(im.delta_on_hand)), 0)::INTEGER AS total_abs_delta,
                    COALESCE(SUM(CASE WHEN im.delta_on_hand > 0 THEN im.delta_on_hand ELSE 0 END), 0)::INTEGER AS positive_delta_on_hand,
                    COALESCE(SUM(CASE WHEN im.delta_on_hand < 0 THEN -im.delta_on_hand ELSE 0 END), 0)::INTEGER AS negative_delta_on_hand_abs
                FROM inventory_movements im
                WHERE im.warehouse_id = :warehouse_id
                  AND im.created_at::date = CAST(:target_date AS date)
                  AND im.delta_on_hand <> 0
                """
            ),
            params,
        )
        summary = dict(summary_result.mappings().first() or {})

        total_result = await self.session.execute(
            text(
                """
                SELECT COALESCE(COUNT(*), 0)::INTEGER AS total
                FROM inventory_movements im
                WHERE im.warehouse_id = :warehouse_id
                  AND im.created_at::date = CAST(:target_date AS date)
                  AND im.delta_on_hand <> 0
                """
            ),
            params,
        )
        total = total_result.scalar_one() or 0

        rows_result = await self.session.execute(
            text(
                """
                SELECT
                    im.id,
                    im.created_at,
                    im.change_type,
                    im.product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    im.delta_on_hand,
                    im.delta_reserved,
                    im.delta_locked,
                    im.before_on_hand,
                    im.before_reserved,
                    im.before_locked,
                    im.after_on_hand,
                    im.after_reserved,
                    im.after_locked,
                    im.related_type,
                    im.related_id,
                    im.operated_by,
                    u.username AS operated_by_name,
                    CASE
                        WHEN im.related_type = 'order' THEN CONCAT(
                            '订单 ',
                            COALESCE(o.order_no, CONCAT('#', CAST(im.related_id AS TEXT))),
                            CASE WHEN NULLIF(o.cancellation_reason, '') IS NOT NULL THEN CONCAT('（取消原因：', o.cancellation_reason, '）') ELSE '' END,
                            CASE WHEN NULLIF(o.description, '') IS NOT NULL THEN CONCAT('；备注：', o.description) ELSE '' END
                        )
                        WHEN im.related_type = 'transfer_order' THEN CONCAT(
                            '调拨 #',
                            COALESCE(CAST(t.id AS TEXT), CAST(im.related_id AS TEXT)),
                            ' ',
                            COALESCE(wf.name, '?'),
                            ' -> ',
                            COALESCE(wt.name, '?'),
                            '，SKU ',
                            COALESCE(p.sku, '-'),
                            '，数量 ',
                            COALESCE(CAST(t.qty AS TEXT), '-'),
                            CASE WHEN NULLIF(t.rejection_reason, '') IS NOT NULL THEN CONCAT('；驳回：', t.rejection_reason) ELSE '' END,
                            CASE WHEN NULLIF(t.description, '') IS NOT NULL THEN CONCAT('；说明：', t.description) ELSE '' END
                        )
                        WHEN im.related_type = 'inbound_record' THEN CONCAT(
                            '入库 #',
                            COALESCE(CAST(ir.id AS TEXT), CAST(im.related_id AS TEXT)),
                            CASE
                                WHEN tir.id IS NOT NULL THEN CONCAT(
                                    '（来源调拨 #',
                                    CAST(tir.id AS TEXT),
                                    ' ',
                                    COALESCE(iwf.name, '?'),
                                    ' -> ',
                                    COALESCE(iwt.name, '?'),
                                    '）'
                                )
                                ELSE ''
                            END,
                            '，SKU ',
                            COALESCE(p.sku, '-'),
                            '，数量 ',
                            COALESCE(CAST(ir.qty AS TEXT), '-')
                        )
                        WHEN im.related_type = 'stocktake' THEN CONCAT('盘点调整：', COALESCE(NULLIF(st.reason, ''), '无备注'))
                        ELSE COALESCE(
                            NULLIF(st.reason, ''),
                            NULLIF(t.rejection_reason, ''),
                            NULLIF(t.description, ''),
                            NULLIF(o.cancellation_reason, ''),
                            NULLIF(o.description, '')
                        )
                    END AS related_description
                FROM inventory_movements im
                JOIN products p ON p.id = im.product_id
                LEFT JOIN users u ON u.id = im.operated_by
                LEFT JOIN stocktakes st ON im.related_type = 'stocktake' AND st.id = im.related_id
                LEFT JOIN transfer_orders t ON im.related_type = 'transfer_order' AND t.id = im.related_id
                LEFT JOIN warehouses wf ON wf.id = t.from_warehouse_id
                LEFT JOIN warehouses wt ON wt.id = t.to_warehouse_id
                LEFT JOIN inbound_records ir ON im.related_type = 'inbound_record' AND ir.id = im.related_id
                LEFT JOIN transfer_orders tir ON ir.transfer_order_id = tir.id
                LEFT JOIN warehouses iwf ON iwf.id = tir.from_warehouse_id
                LEFT JOIN warehouses iwt ON iwt.id = tir.to_warehouse_id
                LEFT JOIN orders o ON im.related_type = 'order' AND o.id = im.related_id
                WHERE im.warehouse_id = :warehouse_id
                  AND im.created_at::date = CAST(:target_date AS date)
                  AND im.delta_on_hand <> 0
                ORDER BY im.created_at DESC, im.id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        items = [dict(row) for row in rows_result.mappings().all()]

        return {
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name,
            "date": target_date.isoformat(),
            "movement_count": summary.get("movement_count", 0),
            "total_abs_delta": summary.get("total_abs_delta", 0),
            "positive_delta_on_hand": summary.get("positive_delta_on_hand", 0),
            "negative_delta_on_hand_abs": summary.get("negative_delta_on_hand_abs", 0),
            "items": items,
            "total": total,
        }

    async def adjust_warehouse_inventory_stocktake(
        self,
        warehouse_id: int,
        inventory_id: int,
        payload: StocktakeAdjustRequest,
        operated_by: Optional[int] = None,
    ):
        warehouse_result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
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

        product_result = await self.session.execute(select(Product).where(Product.id == inventory.product_id))
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
        warehouse_result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        warehouse = warehouse_result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        if not warehouse.is_active:
            raise HTTPException(status_code=400, detail="禁用仓库不支持进货")

        product_result = await self.session.execute(select(Product).where(Product.id == payload.product_id))
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
        inbound_reason = (
            f"{reason_prefix}：进了{payload.qty}个{product.name}"
            if reason_prefix
            else f"进了{payload.qty}个{product.name}"
        )

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
        result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
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
