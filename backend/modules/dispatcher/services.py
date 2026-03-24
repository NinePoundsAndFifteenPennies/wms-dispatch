from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.dispatcher.schemas import (
    DispatcherCreateWorkOrderRequest,
    DispatcherSkillProductBreakdownResponse,
    DispatcherTransferCreateRequest,
    DispatcherWorkOrderPrecheckResponse,
    DispatcherWorkOrderRiskResponse,
)
from modules.shared.config import settings


class DispatcherService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.active_work_order_limit = settings.dispatcher_active_work_order_limit

    @staticmethod
    def _stage_skill_column(stage_type: str):
        mapping = {
            "picking": "skill_picking",
            "staging": "skill_staging",
            "shipping": "skill_shipping",
        }
        if stage_type not in mapping:
            raise HTTPException(status_code=400, detail="Invalid stage type")
        return mapping[stage_type]

    @staticmethod
    def _stage_required_skill_column(stage_type: str):
        mapping = {
            "picking": "req_skill_picking",
            "staging": "req_skill_staging",
            "shipping": "req_skill_shipping",
        }
        if stage_type not in mapping:
            raise HTTPException(status_code=400, detail="Invalid stage type")
        return mapping[stage_type]

    def _build_order_filters(
        self,
        user_id: int,
        for_my_orders: bool = False,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
    ):
        clauses = ["1=1"]
        params = {"user_id": user_id}

        if for_my_orders:
            clauses.append("o.dispatcher_id = :user_id")
            clauses.append("o.status IN ('in_progress', 'completed', 'cancelled')")
            if status_filter:
                if status_filter not in {"in_progress", "completed", "cancelled"}:
                    raise HTTPException(status_code=400, detail="Invalid status filter")
                clauses.append("o.status = :status_filter")
                params["status_filter"] = status_filter
        else:
            clauses.append("o.status = 'pending_acceptance'")

        if search:
            clauses.append("(o.order_no ILIKE :search OR c.name ILIKE :search)")
            params["search"] = f"%{search}%"

        return " AND ".join(clauses), params

    async def list_orders(
        self,
        user_id: int,
        for_my_orders: bool = False,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
    ):
        where_sql, params = self._build_order_filters(
            user_id=user_id,
            for_my_orders=for_my_orders,
            search=search,
            status_filter=status_filter,
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
                    o.updated_at,
                    COALESCE(SUM(oi.qty * oi.unit_price), 0)::INTEGER AS total_amount,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_items
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN warehouses w ON w.id = o.warehouse_id
                LEFT JOIN users u ON u.id = o.dispatcher_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE {where_sql}
                GROUP BY o.id, c.name, w.name, u.username
                ORDER BY o.updated_at DESC, o.id DESC
                """
            ),
            params,
        )
        items = [dict(row) for row in rows.mappings().all()]
        return {"items": items, "total": total}

    async def get_dashboard_summary(self, user_id: int):
        user_result = await self.session.execute(
            text(
                """
                SELECT u.id, u.warehouse_id, w.name AS warehouse_name
                FROM users u
                LEFT JOIN warehouses w ON w.id = u.warehouse_id
                WHERE u.id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        user = user_result.mappings().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        stats_result = await self.session.execute(
            text(
                """
                SELECT
                    COALESCE(COUNT(*) FILTER (WHERE o.status = 'pending_acceptance'), 0)::INTEGER AS pending_count,
                    COALESCE(COUNT(*) FILTER (
                        WHERE o.dispatcher_id = :user_id
                          AND o.status IN ('in_progress', 'completed', 'cancelled')
                    ), 0)::INTEGER AS my_orders_count,
                    COALESCE(COUNT(*) FILTER (WHERE o.dispatcher_id = :user_id AND o.status = 'in_progress'), 0)::INTEGER AS my_in_progress_count,
                    COALESCE(COUNT(*) FILTER (WHERE o.dispatcher_id = :user_id AND o.status = 'completed'), 0)::INTEGER AS my_completed_count,
                    COALESCE(COUNT(*) FILTER (WHERE o.dispatcher_id = :user_id AND o.status = 'cancelled'), 0)::INTEGER AS my_cancelled_count
                FROM orders o
                """
            ),
            {"user_id": user_id},
        )
        stats = dict(stats_result.mappings().first() or {})
        return {
            "warehouse_id": user["warehouse_id"],
            "warehouse_name": user["warehouse_name"],
            "pending_count": stats.get("pending_count", 0),
            "my_orders_count": stats.get("my_orders_count", 0),
            "my_in_progress_count": stats.get("my_in_progress_count", 0),
            "my_completed_count": stats.get("my_completed_count", 0),
            "my_cancelled_count": stats.get("my_cancelled_count", 0),
        }

    async def get_order_detail(self, order_id: int, user_id: int, for_my_orders: bool = False):
        where_sql, params = self._build_order_filters(
            user_id=user_id,
            for_my_orders=for_my_orders,
            search=None,
            status_filter=None,
        )
        params["order_id"] = order_id

        order_result = await self.session.execute(
            text(
                f"""
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
                    o.timeout_revert_count,
                    o.last_reverted_at,
                    o.completed_at,
                    o.cancelled_at,
                    o.cancelled_by,
                    o.cancellation_reason,
                    o.created_at,
                    o.updated_at,
                    COALESCE(SUM(oi.qty * oi.unit_price), 0)::INTEGER AS total_amount,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_items
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN warehouses w ON w.id = o.warehouse_id
                LEFT JOIN users u ON u.id = o.dispatcher_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.id = :order_id
                  AND {where_sql}
                GROUP BY o.id, c.name, c.contact, c.address, w.name, u.username
                """
            ),
            params,
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
                    p.req_skill_picking,
                    p.req_skill_staging,
                    p.req_skill_shipping,
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
        items = [dict(row) for row in items_result.mappings().all()]

        stage_result = await self.session.execute(
            text(
                """
                SELECT
                    os.id,
                    os.stage_type,
                    os.status,
                    os.completion_type,
                    os.completed_at,
                    os.completed_by,
                    os.remark,
                    os.created_at,
                    COALESCE(COUNT(wo.id), 0)::INTEGER AS work_orders_total,
                    COALESCE(COUNT(wo.id) FILTER (WHERE wo.status = 'pending'), 0)::INTEGER AS work_orders_pending,
                    COALESCE(COUNT(wo.id) FILTER (WHERE wo.status = 'in_progress'), 0)::INTEGER AS work_orders_in_progress,
                    COALESCE(COUNT(wo.id) FILTER (WHERE wo.status = 'completed'), 0)::INTEGER AS work_orders_completed,
                    COALESCE(COUNT(wo.id) FILTER (WHERE wo.status = 'terminated'), 0)::INTEGER AS work_orders_terminated
                FROM order_stages os
                LEFT JOIN work_orders wo ON wo.stage_id = os.id
                WHERE os.order_id = :order_id
                GROUP BY os.id
                ORDER BY CASE os.stage_type
                    WHEN 'picking' THEN 1
                    WHEN 'staging' THEN 2
                    WHEN 'shipping' THEN 3
                    ELSE 99
                END
                """
            ),
            {"order_id": order_id},
        )
        stages = []
        for row in stage_result.mappings().all():
            stage = dict(row)
            stage["work_orders"] = {
                "total": stage.pop("work_orders_total"),
                "pending": stage.pop("work_orders_pending"),
                "in_progress": stage.pop("work_orders_in_progress"),
                "completed": stage.pop("work_orders_completed"),
                "terminated": stage.pop("work_orders_terminated"),
            }
            stages.append(stage)

        work_order_summary_result = await self.session.execute(
            text(
                """
                SELECT
                    COALESCE(COUNT(*), 0)::INTEGER AS total,
                    COALESCE(COUNT(*) FILTER (WHERE wo.status = 'pending'), 0)::INTEGER AS pending,
                    COALESCE(COUNT(*) FILTER (WHERE wo.status = 'in_progress'), 0)::INTEGER AS in_progress,
                    COALESCE(COUNT(*) FILTER (WHERE wo.status = 'completed'), 0)::INTEGER AS completed,
                    COALESCE(COUNT(*) FILTER (WHERE wo.status = 'terminated'), 0)::INTEGER AS terminated
                FROM work_orders wo
                WHERE wo.order_id = :order_id
                """
            ),
            {"order_id": order_id},
        )
        work_order_summary = dict(work_order_summary_result.mappings().first() or {})
        if not work_order_summary:
            work_order_summary = {"total": 0, "pending": 0, "in_progress": 0, "completed": 0, "terminated": 0}

        return {
            **dict(order),
            "items": items,
            "stages": stages,
            "work_order_summary": work_order_summary,
        }

    async def accept_order(self, order_id: int, user_id: int):
        try:
            user_result = await self.session.execute(
                text(
                    """
                    SELECT id, role, warehouse_id, is_active
                    FROM users
                    WHERE id = :user_id
                    LIMIT 1
                    """
                ),
                {"user_id": user_id},
            )
            user = user_result.mappings().first()
            if not user or user["role"] != "dispatcher":
                raise HTTPException(status_code=403, detail="Access denied")
            if not user["is_active"]:
                raise HTTPException(status_code=403, detail="User is disabled")
            if user["warehouse_id"] is None:
                raise HTTPException(status_code=400, detail="Dispatcher warehouse is required")

            order_lock_result = await self.session.execute(
                text(
                    """
                    SELECT id, status, dispatcher_id, warehouse_id
                    FROM orders
                    WHERE id = :order_id
                    FOR UPDATE
                    """
                ),
                {"order_id": order_id},
            )
            order_row = order_lock_result.mappings().first()
            if not order_row:
                raise HTTPException(status_code=404, detail="Order not found")
            if order_row["status"] != "pending_acceptance":
                raise HTTPException(status_code=400, detail="Order is not pending acceptance")
            if order_row["dispatcher_id"] is not None:
                raise HTTPException(status_code=400, detail="Order is already assigned")
            if order_row["warehouse_id"] is not None and order_row["warehouse_id"] != user["warehouse_id"]:
                raise HTTPException(
                    status_code=400,
                    detail="Order warehouse does not match dispatcher warehouse",
                )

            required_items_result = await self.session.execute(
                text(
                    """
                    SELECT
                        oi.product_id,
                        p.sku,
                        p.name AS product_name,
                        COALESCE(SUM(oi.qty), 0)::INTEGER AS required_qty
                    FROM order_items oi
                    JOIN products p ON p.id = oi.product_id
                    WHERE oi.order_id = :order_id
                    GROUP BY oi.product_id, p.sku, p.name
                    ORDER BY oi.product_id
                    """
                ),
                {"order_id": order_id},
            )
            required_items = [dict(row) for row in required_items_result.mappings().all()]
            if not required_items:
                raise HTTPException(status_code=400, detail="Order has no items")

            required_by_product = {row["product_id"]: row for row in required_items}

            inventory_lock_result = await self.session.execute(
                text(
                    """
                    SELECT
                        i.id AS inventory_id,
                        i.product_id,
                        i.qty_on_hand,
                        i.qty_reserved,
                        i.qty_locked,
                        i.qty_available
                    FROM inventory i
                    WHERE i.warehouse_id = :warehouse_id
                      AND i.product_id IN (
                          SELECT DISTINCT oi.product_id
                          FROM order_items oi
                          WHERE oi.order_id = :order_id
                      )
                    ORDER BY i.product_id
                    FOR UPDATE
                    """
                ),
                {"order_id": order_id, "warehouse_id": user["warehouse_id"]},
            )
            inventory_rows = [dict(row) for row in inventory_lock_result.mappings().all()]
            inventory_by_product = {row["product_id"]: row for row in inventory_rows}

            missing_products = sorted(set(required_by_product.keys()) - set(inventory_by_product.keys()))
            shortages = []
            for product_id in missing_products:
                required_row = required_by_product[product_id]
                required_qty = required_row["required_qty"]
                shortages.append(
                    {
                        "product_id": product_id,
                        "sku": required_row["sku"],
                        "product_name": required_row["product_name"],
                        "required_qty": required_qty,
                        "available_qty": 0,
                        "shortage_qty": required_qty,
                    }
                )

            for row in inventory_rows:
                required_row = required_by_product[row["product_id"]]
                required_qty = required_row["required_qty"]
                if row["qty_available"] < required_qty:
                    shortages.append(
                        {
                            "product_id": row["product_id"],
                            "sku": required_row["sku"],
                            "product_name": required_row["product_name"],
                            "required_qty": required_qty,
                            "available_qty": row["qty_available"],
                            "shortage_qty": required_qty - row["qty_available"],
                        }
                    )
                    continue

                before_on_hand = row["qty_on_hand"]
                before_reserved = row["qty_reserved"]
                before_locked = row["qty_locked"]

                update_result = await self.session.execute(
                    text(
                        """
                        UPDATE inventory
                        SET
                            qty_reserved = qty_reserved + :qty,
                            updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                        WHERE id = :inventory_id
                        RETURNING qty_on_hand, qty_reserved, qty_locked
                        """
                    ),
                    {"inventory_id": row["inventory_id"], "qty": required_qty},
                )
                updated_inventory = update_result.mappings().first()
                if not updated_inventory:
                    raise HTTPException(status_code=409, detail="Inventory update conflict during order acceptance")

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
                        "inventory_id": row["inventory_id"],
                        "warehouse_id": user["warehouse_id"],
                        "product_id": row["product_id"],
                        "change_type": "reserve",
                        "delta_on_hand": 0,
                        "delta_reserved": required_qty,
                        "delta_locked": 0,
                        "before_on_hand": before_on_hand,
                        "before_reserved": before_reserved,
                        "before_locked": before_locked,
                        "after_on_hand": updated_inventory["qty_on_hand"],
                        "after_reserved": updated_inventory["qty_reserved"],
                        "after_locked": updated_inventory["qty_locked"],
                        "related_type": "order",
                        "related_id": order_id,
                        "operated_by": user_id,
                    },
                )

            if shortages:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "可用库存不足，请先调拨补货后再接单",
                        "shortages": shortages,
                    },
                )

            order_update_result = await self.session.execute(
                text(
                    """
                    UPDATE orders
                    SET
                        status = 'in_progress',
                        dispatcher_id = :dispatcher_id,
                        warehouse_id = :warehouse_id,
                        accepted_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :order_id
                      AND status = 'pending_acceptance'
                      AND dispatcher_id IS NULL
                    RETURNING id
                    """
                ),
                {
                    "order_id": order_id,
                    "dispatcher_id": user_id,
                    "warehouse_id": user["warehouse_id"],
                },
            )
            updated_order = order_update_result.mappings().first()
            if not updated_order:
                raise HTTPException(status_code=409, detail="Order acceptance conflict")

            await self.session.execute(
                text(
                    """
                    INSERT INTO order_stages (order_id, stage_type, status, created_at, updated_at)
                    SELECT :order_id, stage_type, 'not_started', (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0), (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    FROM (VALUES ('picking'), ('staging'), ('shipping')) AS s(stage_type)
                    ON CONFLICT (order_id, stage_type) DO NOTHING
                    """
                ),
                {"order_id": order_id},
            )

            stage_count_result = await self.session.execute(
                text(
                    """
                    SELECT COUNT(*)::INTEGER AS stage_count
                    FROM order_stages
                    WHERE order_id = :order_id
                      AND stage_type IN ('picking', 'staging', 'shipping')
                    """
                ),
                {"order_id": order_id},
            )
            stage_count = stage_count_result.scalar_one() or 0
            if stage_count != 3:
                raise HTTPException(status_code=409, detail="Order stage initialization incomplete")

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        return await self.get_order_detail(order_id=order_id, user_id=user_id, for_my_orders=True)

    async def cancel_my_order(self, order_id: int, user_id: int, cancellation_reason: str):
        try:
            reason = (cancellation_reason or "").strip()
            if not reason:
                raise HTTPException(status_code=400, detail="Cancellation reason is required")

            await self._get_dispatcher_order(order_id=order_id, user_id=user_id)

            order_lock_result = await self.session.execute(
                text(
                    """
                    SELECT id, order_no, status, dispatcher_id, warehouse_id
                    FROM orders
                    WHERE id = :order_id
                    FOR UPDATE
                    """
                ),
                {"order_id": order_id},
            )
            order_row = order_lock_result.mappings().first()
            if not order_row:
                raise HTTPException(status_code=404, detail="Order not found")
            if order_row["dispatcher_id"] != user_id:
                raise HTTPException(status_code=403, detail="Only responsible dispatcher can operate this order")
            if order_row["status"] == "cancelled":
                raise HTTPException(status_code=400, detail="Order is already cancelled")
            if order_row["status"] != "in_progress":
                raise HTTPException(status_code=400, detail="Only in-progress orders can be cancelled")
            if order_row["warehouse_id"] is None:
                raise HTTPException(status_code=409, detail="Order warehouse is missing")

            open_work_orders_result = await self.session.execute(
                text(
                    """
                    SELECT COALESCE(COUNT(*), 0)::INTEGER AS open_count
                    FROM work_orders
                    WHERE order_id = :order_id
                      AND status IN ('pending', 'in_progress')
                    """
                ),
                {"order_id": order_id},
            )
            open_count = open_work_orders_result.scalar_one() or 0
            if open_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Please terminate all pending/in-progress work orders before cancelling the order",
                )

            required_items_result = await self.session.execute(
                text(
                    """
                    SELECT
                        oi.product_id,
                        COALESCE(SUM(oi.qty), 0)::INTEGER AS required_qty
                    FROM order_items oi
                    WHERE oi.order_id = :order_id
                    GROUP BY oi.product_id
                    ORDER BY oi.product_id
                    """
                ),
                {"order_id": order_id},
            )
            required_items = [dict(row) for row in required_items_result.mappings().all()]
            if not required_items:
                raise HTTPException(status_code=400, detail="Order has no items")
            required_by_product = {row["product_id"]: row["required_qty"] for row in required_items}

            inventory_rows_result = await self.session.execute(
                text(
                    """
                    SELECT
                        i.id AS inventory_id,
                        i.product_id,
                        i.qty_on_hand,
                        i.qty_reserved,
                        i.qty_locked
                    FROM inventory i
                    WHERE i.warehouse_id = :warehouse_id
                      AND i.product_id IN (
                          SELECT DISTINCT oi.product_id
                          FROM order_items oi
                          WHERE oi.order_id = :order_id
                      )
                    ORDER BY i.product_id
                    FOR UPDATE
                    """
                ),
                {
                    "warehouse_id": order_row["warehouse_id"],
                    "order_id": order_id,
                },
            )
            inventory_rows = [dict(row) for row in inventory_rows_result.mappings().all()]
            inventory_by_product = {row["product_id"]: row for row in inventory_rows}

            missing_products = sorted(set(required_by_product.keys()) - set(inventory_by_product.keys()))
            if missing_products:
                raise HTTPException(status_code=409, detail="Inventory rows missing for cancellation release")

            for product_id, required_qty in required_by_product.items():
                inventory_row = inventory_by_product[product_id]
                if inventory_row["qty_reserved"] < required_qty:
                    raise HTTPException(status_code=409, detail="Insufficient reserved inventory for cancellation release")

                before_on_hand = inventory_row["qty_on_hand"]
                before_reserved = inventory_row["qty_reserved"]
                before_locked = inventory_row["qty_locked"]

                updated_inventory_result = await self.session.execute(
                    text(
                        """
                        UPDATE inventory
                        SET
                            qty_reserved = qty_reserved - :qty,
                            updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                        WHERE id = :inventory_id
                        RETURNING qty_on_hand, qty_reserved, qty_locked
                        """
                    ),
                    {
                        "inventory_id": inventory_row["inventory_id"],
                        "qty": required_qty,
                    },
                )
                updated_inventory = updated_inventory_result.mappings().first()
                if not updated_inventory:
                    raise HTTPException(status_code=409, detail="Inventory update conflict during order cancellation")

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
                            'reserve_release',
                            0,
                            :delta_reserved,
                            0,
                            :before_on_hand,
                            :before_reserved,
                            :before_locked,
                            :after_on_hand,
                            :after_reserved,
                            :after_locked,
                            'order',
                            :related_id,
                            :operated_by
                        )
                        """
                    ),
                    {
                        "inventory_id": inventory_row["inventory_id"],
                        "warehouse_id": order_row["warehouse_id"],
                        "product_id": product_id,
                        "delta_reserved": -required_qty,
                        "before_on_hand": before_on_hand,
                        "before_reserved": before_reserved,
                        "before_locked": before_locked,
                        "after_on_hand": updated_inventory["qty_on_hand"],
                        "after_reserved": updated_inventory["qty_reserved"],
                        "after_locked": updated_inventory["qty_locked"],
                        "related_id": order_id,
                        "operated_by": user_id,
                    },
                )

            order_update_result = await self.session.execute(
                text(
                    """
                    UPDATE orders
                    SET
                        status = 'cancelled',
                        cancelled_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        cancelled_by = :cancelled_by,
                        cancellation_reason = :cancellation_reason,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :order_id
                      AND status = 'in_progress'
                      AND dispatcher_id = :dispatcher_id
                    RETURNING id
                    """
                ),
                {
                    "order_id": order_id,
                    "dispatcher_id": user_id,
                    "cancelled_by": user_id,
                    "cancellation_reason": reason,
                },
            )
            updated_order = order_update_result.mappings().first()
            if not updated_order:
                raise HTTPException(status_code=409, detail="Order cancellation conflict")

            await self.session.execute(
                text(
                    """
                    INSERT INTO notifications (
                        user_id,
                        type,
                        title,
                        body,
                        related_id,
                        related_type,
                        is_read,
                        created_at
                    )
                    SELECT
                        u.id,
                        'order_cancelled',
                        :title,
                        :body,
                        :related_id,
                        'order',
                        false,
                        (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    FROM users u
                    WHERE u.role = 'admin'
                      AND u.is_active = true
                    """
                ),
                {
                    "title": "订单已取消",
                    "body": f"订单 {order_row['order_no']} 已由调度员取消，原因：{reason}",
                    "related_id": order_id,
                },
            )

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        return await self.get_order_detail(order_id=order_id, user_id=user_id, for_my_orders=True)

    async def get_warehouse_inventory(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ):
        user_result = await self.session.execute(
            text(
                """
                SELECT u.id, u.role, u.warehouse_id, w.name, w.address, w.description, w.cover_image, w.is_active
                FROM users u
                LEFT JOIN warehouses w ON w.id = u.warehouse_id
                WHERE u.id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        user = user_result.mappings().first()
        if not user or user["role"] != "dispatcher":
            raise HTTPException(status_code=403, detail="Access denied")
        if not user["warehouse_id"]:
            raise HTTPException(status_code=400, detail="Dispatcher warehouse is required")
        if not user["name"]:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        where_clauses = ["i.warehouse_id = :warehouse_id"]
        params = {
            "warehouse_id": user["warehouse_id"],
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if search:
            where_clauses.append("(p.name ILIKE :search OR p.sku ILIKE :search OR p.category ILIKE :search)")
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where_clauses)

        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)::INTEGER AS total
                FROM inventory i
                JOIN products p ON p.id = i.product_id
                WHERE {where_sql}
                """
            ),
            params,
        )
        total = count_result.scalar_one() or 0

        rows_result = await self.session.execute(
            text(
                f"""
                SELECT
                    i.id,
                    i.product_id,
                    p.sku,
                    p.name AS product_name,
                    p.category,
                    p.cover_image AS product_cover_image,
                    p.is_active AS product_is_active,
                    i.qty_on_hand,
                    i.qty_reserved,
                    i.qty_locked,
                    i.qty_threshold,
                    i.qty_available
                FROM inventory i
                JOIN products p ON p.id = i.product_id
                WHERE {where_sql}
                ORDER BY p.name ASC, p.id ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )

        items = [dict(row) for row in rows_result.mappings().all()]
        warehouse = {
            "id": user["warehouse_id"],
            "name": user["name"],
            "address": user["address"],
            "description": user["description"],
            "cover_image": user["cover_image"],
            "is_active": user["is_active"],
        }
        return {"warehouse": warehouse, "items": items, "total": total}

    async def get_inventory_flow_trend(self, user_id: int, days: int = 14):
        if days < 1 or days > 90:
            raise HTTPException(status_code=400, detail="days must be between 1 and 90")

        user_result = await self.session.execute(
            text(
                """
                SELECT u.id, u.role, u.warehouse_id, w.name AS warehouse_name
                FROM users u
                LEFT JOIN warehouses w ON w.id = u.warehouse_id
                WHERE u.id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        user = user_result.mappings().first()
        if not user or user["role"] != "dispatcher":
            raise HTTPException(status_code=403, detail="Access denied")
        if not user["warehouse_id"] or not user["warehouse_name"]:
            raise HTTPException(status_code=400, detail="Dispatcher warehouse is required")

        date_rows = await self.session.execute(
            text(
                """
                SELECT TO_CHAR(gs::date, 'YYYY-MM-DD') AS date
                FROM generate_series(
                    ((NOW() AT TIME ZONE 'Asia/Shanghai')::date - (:days - 1)),
                    (NOW() AT TIME ZONE 'Asia/Shanghai')::date,
                    interval '1 day'
                ) gs
                ORDER BY gs ASC
                """
            ),
            {"days": days},
        )
        date_labels = [row["date"] for row in date_rows.mappings().all()]

        trend_result = await self.session.execute(
            text(
                """
                SELECT
                    TO_CHAR(im.created_at::date, 'YYYY-MM-DD') AS date,
                    COUNT(*)::INTEGER AS movement_count,
                                        COALESCE(SUM(ABS(im.delta_on_hand)), 0)::INTEGER AS total_abs_delta
                FROM inventory_movements im
                WHERE im.warehouse_id = :warehouse_id
                  AND im.created_at::date >= ((NOW() AT TIME ZONE 'Asia/Shanghai')::date - (:days - 1))
                                    AND im.delta_on_hand <> 0
                GROUP BY im.created_at::date
                ORDER BY im.created_at::date ASC
                """
            ),
            {
                "warehouse_id": user["warehouse_id"],
                "days": days,
            },
        )

        trend_map = {
            row["date"]: {
                "movement_count": row["movement_count"],
                "total_abs_delta": row["total_abs_delta"],
            }
            for row in trend_result.mappings().all()
        }

        points = []
        for label in date_labels:
            summary = trend_map.get(label, {"movement_count": 0, "total_abs_delta": 0})
            points.append(
                {
                    "date": label,
                    "movement_count": summary["movement_count"],
                    "total_abs_delta": summary["total_abs_delta"],
                }
            )

        return {
            "warehouse_id": user["warehouse_id"],
            "warehouse_name": user["warehouse_name"],
            "points": points,
        }

    async def get_inventory_flow_node_details(
        self,
        user_id: int,
        target_date: date,
        page: int = 1,
        page_size: int = 20,
    ):
        user_result = await self.session.execute(
            text(
                """
                SELECT u.id, u.role, u.warehouse_id, w.name AS warehouse_name
                FROM users u
                LEFT JOIN warehouses w ON w.id = u.warehouse_id
                WHERE u.id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        user = user_result.mappings().first()
        if not user or user["role"] != "dispatcher":
            raise HTTPException(status_code=403, detail="Access denied")
        if not user["warehouse_id"] or not user["warehouse_name"]:
            raise HTTPException(status_code=400, detail="Dispatcher warehouse is required")

        params = {
            "warehouse_id": user["warehouse_id"],
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
                            CASE WHEN NULLIF(t.description, '') IS NOT NULL THEN CONCAT('；说明：', t.description) ELSE '' END,
                            CASE WHEN NULLIF(t.agent_reason, '') IS NOT NULL THEN CONCAT('；AI建议：', t.agent_reason) ELSE '' END
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
                            NULLIF(t.agent_reason, ''),
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
            "warehouse_id": user["warehouse_id"],
            "warehouse_name": user["warehouse_name"],
            "date": target_date.isoformat(),
            "movement_count": summary.get("movement_count", 0),
            "total_abs_delta": summary.get("total_abs_delta", 0),
            "positive_delta_on_hand": summary.get("positive_delta_on_hand", 0),
            "negative_delta_on_hand_abs": summary.get("negative_delta_on_hand_abs", 0),
            "items": items,
            "total": total,
        }

    async def list_workers(self, user_id: int, search: Optional[str] = None):
        user_result = await self.session.execute(
            text(
                """
                SELECT id, role, warehouse_id
                FROM users
                WHERE id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        user = user_result.mappings().first()
        if not user or user["role"] != "dispatcher":
            raise HTTPException(status_code=403, detail="Access denied")
        if not user["warehouse_id"]:
            raise HTTPException(status_code=400, detail="Dispatcher warehouse is required")

        where = ["u.role = 'worker'", "u.warehouse_id = :warehouse_id", "u.is_active = true"]
        params = {"warehouse_id": user["warehouse_id"]}
        if search:
            where.append("(u.username ILIKE :search OR u.email ILIKE :search)")
            params["search"] = f"%{search}%"

        result = await self.session.execute(
            text(
                f"""
                SELECT
                    u.id,
                    u.username,
                    u.email,
                    u.skill_picking,
                    u.skill_staging,
                    u.skill_shipping,
                    COALESCE(wo.active_work_order_count, 0)::INTEGER AS active_work_order_count,
                    CAST(:active_work_order_limit AS INTEGER) AS active_work_order_limit
                FROM users u
                LEFT JOIN (
                    SELECT
                        worker_id,
                        COUNT(*)::INTEGER AS active_work_order_count
                    FROM work_orders
                    WHERE status IN ('pending', 'in_progress')
                    GROUP BY worker_id
                ) wo ON wo.worker_id = u.id
                WHERE {' AND '.join(where)}
                ORDER BY u.username ASC, u.id ASC
                """
            ),
            {
                **params,
                "active_work_order_limit": self.active_work_order_limit,
            },
        )
        return [dict(row) for row in result.mappings().all()]

    async def list_work_orders(
        self,
        user_id: int,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ):
        user_result = await self.session.execute(
            text(
                """
                SELECT id, role, warehouse_id
                FROM users
                WHERE id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        user = user_result.mappings().first()
        if not user or user["role"] != "dispatcher":
            raise HTTPException(status_code=403, detail="Access denied")
        if not user["warehouse_id"]:
            raise HTTPException(status_code=400, detail="Dispatcher warehouse is required")

        where = ["wo.warehouse_id = :warehouse_id", "wo.dispatcher_id = :user_id"]
        params = {"warehouse_id": user["warehouse_id"], "user_id": user_id}

        allowed_status = {"pending", "in_progress", "completed", "terminated"}
        if status_filter:
            if status_filter not in allowed_status:
                raise HTTPException(status_code=400, detail="Invalid work order status filter")
            where.append("wo.status = :status")
            params["status"] = status_filter

        if search:
            where.append(
                """
                (
                    CAST(wo.id AS TEXT) ILIKE :search
                    OR o.order_no ILIKE :search
                    OR c.name ILIKE :search
                    OR wu.username ILIKE :search
                )
                """
            )
            params["search"] = f"%{search}%"

        sort_field_map = {
            "created_at": "wo.created_at",
            "updated_at": "wo.updated_at",
            "deadline": "wo.deadline",
        }
        sort_expr = sort_field_map.get(sort_by)
        if sort_expr is None:
            raise HTTPException(status_code=400, detail="Invalid sort_by")

        normalized_sort_order = sort_order.lower()
        if normalized_sort_order not in {"asc", "desc"}:
            raise HTTPException(status_code=400, detail="Invalid sort_order")

        where_sql = " AND ".join(where)
        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)::INTEGER AS total
                FROM work_orders wo
                JOIN orders o ON o.id = wo.order_id
                JOIN customers c ON c.id = o.customer_id
                JOIN users wu ON wu.id = wo.worker_id
                WHERE {where_sql}
                """
            ),
            params,
        )
        total = count_result.scalar_one() or 0

        rows_result = await self.session.execute(
            text(
                f"""
                SELECT
                    wo.id,
                    wo.order_id,
                    o.order_no,
                    c.name AS customer_name,
                    wo.stage_id,
                    os.stage_type,
                    wo.worker_id,
                    wu.username AS worker_name,
                    wo.dispatcher_id,
                    wo.warehouse_id,
                    wo.status,
                    wo.priority,
                    wo.deadline,
                    wo.description,
                    wo.source,
                    wo.started_at,
                    wo.completed_at,
                    wo.terminated_at,
                    wo.terminated_by,
                    wo.termination_reason,
                    wo.created_at,
                    wo.updated_at
                FROM work_orders wo
                JOIN orders o ON o.id = wo.order_id
                JOIN customers c ON c.id = o.customer_id
                JOIN users wu ON wu.id = wo.worker_id
                JOIN order_stages os ON os.id = wo.stage_id
                WHERE {where_sql}
                ORDER BY {sort_expr} {normalized_sort_order.upper()} NULLS LAST, wo.id DESC
                """
            ),
            params,
        )
        items = [dict(row) for row in rows_result.mappings().all()]
        return {"items": items, "total": total}

    async def _assess_work_order_assignment(self, order_id: int, user_id: int, stage_id: int, worker_id: int):
        order_row = await self._get_dispatcher_order(order_id=order_id, user_id=user_id)
        if order_row["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="Only in-progress orders can create work orders")

        stage_result = await self.session.execute(
            text(
                """
                SELECT id, order_id, stage_type, status
                FROM order_stages
                WHERE id = :stage_id
                  AND order_id = :order_id
                LIMIT 1
                """
            ),
            {"stage_id": stage_id, "order_id": order_id},
        )
        stage_row = stage_result.mappings().first()
        if not stage_row:
            raise HTTPException(status_code=400, detail="Stage does not belong to the target order")
        if stage_row["status"] == "completed":
            raise HTTPException(status_code=400, detail="Stage is completed and locked for new work orders")

        worker_result = await self.session.execute(
            text(
                """
                SELECT
                    id,
                    role,
                    warehouse_id,
                    is_active,
                    skill_picking,
                    skill_staging,
                    skill_shipping
                FROM users
                WHERE id = :worker_id
                LIMIT 1
                """
            ),
            {"worker_id": worker_id},
        )
        worker = worker_result.mappings().first()
        if not worker or worker["role"] != "worker":
            raise HTTPException(status_code=400, detail="Invalid worker")
        if not worker["is_active"]:
            raise HTTPException(status_code=400, detail="Worker is disabled")
        if worker["warehouse_id"] != order_row["warehouse_id"]:
            raise HTTPException(status_code=400, detail="Worker warehouse does not match order warehouse")

        required_skill_column = self._stage_required_skill_column(stage_row["stage_type"])
        skill_items_result = await self.session.execute(
            text(
                f"""
                SELECT
                    p.id AS product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    p.{required_skill_column}::INTEGER AS required_skill
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = :order_id
                GROUP BY p.id, p.sku, p.name, p.{required_skill_column}
                ORDER BY p.id ASC
                """
            ),
            {"order_id": order_id},
        )
        skill_items = [dict(row) for row in skill_items_result.mappings().all()]

        required_skill_min = min((item["required_skill"] for item in skill_items), default=0)
        required_skill_max = max((item["required_skill"] for item in skill_items), default=0)

        worker_skill_column = self._stage_skill_column(stage_row["stage_type"])
        worker_skill = int(worker[worker_skill_column])

        if worker_skill < required_skill_min:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        f"当前工人阶段技能({worker_skill})低于该阶段最低技能要求({required_skill_min})，禁止派单"
                    ),
                    "code": "worker_skill_below_stage_min",
                    "required_skill_min": required_skill_min,
                    "required_skill_max": required_skill_max,
                    "worker_skill": worker_skill,
                },
            )

        skill_products = []
        for item in skill_items:
            required_skill = int(item["required_skill"])
            skill_products.append(
                {
                    "product_id": item["product_id"],
                    "product_sku": item["product_sku"],
                    "product_name": item["product_name"],
                    "required_skill": required_skill,
                    "worker_skill": worker_skill,
                    "is_qualified": worker_skill >= required_skill,
                }
            )

        active_count_result = await self.session.execute(
            text(
                """
                SELECT COALESCE(COUNT(*), 0)::INTEGER
                FROM work_orders
                WHERE worker_id = :worker_id
                  AND status IN ('pending', 'in_progress')
                """
            ),
            {"worker_id": worker_id},
        )
        active_work_order_count = active_count_result.scalar_one() or 0

        risks = []
        if worker_skill < required_skill_max:
            risks.append(
                {
                    "code": "skill_gap",
                    "message": f"当前工人阶段技能({worker_skill})低于该阶段最高技能要求({required_skill_max})",
                }
            )
        if active_work_order_count >= self.active_work_order_limit:
            risks.append(
                {
                    "code": "worker_overload",
                    "message": f"当前工人在途工单数({active_work_order_count})已达到上限({self.active_work_order_limit})",
                }
            )

        return {
            "order_row": order_row,
            "stage_row": stage_row,
            "worker": worker,
            "required_skill_min": required_skill_min,
            "required_skill_max": required_skill_max,
            "worker_skill": worker_skill,
            "active_work_order_count": active_work_order_count,
            "risks": risks,
            "skill_products": skill_products,
        }

    async def precheck_work_order_assignment(
        self,
        order_id: int,
        user_id: int,
        stage_id: int,
        worker_id: int,
    ) -> DispatcherWorkOrderPrecheckResponse:
        assessment = await self._assess_work_order_assignment(
            order_id=order_id,
            user_id=user_id,
            stage_id=stage_id,
            worker_id=worker_id,
        )
        risks = [DispatcherWorkOrderRiskResponse(**item) for item in assessment["risks"]]
        skill_products = [DispatcherSkillProductBreakdownResponse(**item) for item in assessment["skill_products"]]
        return DispatcherWorkOrderPrecheckResponse(
            stage_id=assessment["stage_row"]["id"],
            stage_type=assessment["stage_row"]["stage_type"],
            required_skill_min=assessment["required_skill_min"],
            required_skill_max=assessment["required_skill_max"],
            worker_skill=assessment["worker_skill"],
            active_work_order_count=assessment["active_work_order_count"],
            active_work_order_limit=self.active_work_order_limit,
            has_risk=len(risks) > 0,
            risks=risks,
            skill_products=skill_products,
        )

    async def _get_dispatcher_order(self, order_id: int, user_id: int):
        result = await self.session.execute(
            text(
                """
                SELECT id, status, dispatcher_id, warehouse_id
                FROM orders
                WHERE id = :order_id
                LIMIT 1
                """
            ),
            {"order_id": order_id},
        )
        order_row = result.mappings().first()
        if not order_row:
            raise HTTPException(status_code=404, detail="Order not found")
        if order_row["dispatcher_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only responsible dispatcher can operate this order")
        return order_row

    async def list_order_work_orders(
        self,
        order_id: int,
        user_id: int,
        stage_id: Optional[int] = None,
        status_filter: Optional[str] = None,
    ):
        await self._get_dispatcher_order(order_id=order_id, user_id=user_id)

        where = ["wo.order_id = :order_id"]
        params = {"order_id": order_id}

        if stage_id is not None:
            where.append("wo.stage_id = :stage_id")
            params["stage_id"] = stage_id

        allowed_status = {"pending", "in_progress", "completed", "terminated"}
        if status_filter:
            if status_filter not in allowed_status:
                raise HTTPException(status_code=400, detail="Invalid work order status filter")
            where.append("wo.status = :status")
            params["status"] = status_filter

        query_where = " AND ".join(where)
        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)::INTEGER AS total
                FROM work_orders wo
                WHERE {query_where}
                """
            ),
            params,
        )
        total = count_result.scalar_one() or 0

        rows_result = await self.session.execute(
            text(
                f"""
                SELECT
                    wo.id,
                    wo.order_id,
                    wo.stage_id,
                    os.stage_type,
                    wo.worker_id,
                    wu.username AS worker_name,
                    wo.dispatcher_id,
                    wo.warehouse_id,
                    wo.status,
                    wo.priority,
                    wo.deadline,
                    wo.description,
                    wo.source,
                    wo.started_at,
                    wo.completed_at,
                    wo.terminated_at,
                    wo.terminated_by,
                    wo.termination_reason,
                    wo.created_at,
                    wo.updated_at
                FROM work_orders wo
                JOIN users wu ON wu.id = wo.worker_id
                JOIN order_stages os ON os.id = wo.stage_id
                WHERE {query_where}
                ORDER BY wo.created_at DESC, wo.id DESC
                """
            ),
            params,
        )

        items = [dict(row) for row in rows_result.mappings().all()]
        return {"items": items, "total": total}

    async def _get_work_order_detail(self, work_order_id: int):
        result = await self.session.execute(
            text(
                """
                SELECT
                    wo.id,
                    wo.order_id,
                    wo.stage_id,
                    os.stage_type,
                    wo.worker_id,
                    wu.username AS worker_name,
                    wo.dispatcher_id,
                    wo.warehouse_id,
                    wo.status,
                    wo.priority,
                    wo.deadline,
                    wo.description,
                    wo.source,
                    wo.started_at,
                    wo.completed_at,
                    wo.terminated_at,
                    wo.terminated_by,
                    wo.termination_reason,
                    wo.created_at,
                    wo.updated_at
                FROM work_orders wo
                JOIN users wu ON wu.id = wo.worker_id
                JOIN order_stages os ON os.id = wo.stage_id
                WHERE wo.id = :work_order_id
                LIMIT 1
                """
            ),
            {"work_order_id": work_order_id},
        )
        work_order = result.mappings().first()
        if not work_order:
            raise HTTPException(status_code=404, detail="Work order not found")
        return dict(work_order)

    async def create_work_order(self, order_id: int, user_id: int, payload: DispatcherCreateWorkOrderRequest):
        try:
            assessment = await self._assess_work_order_assignment(
                order_id=order_id,
                user_id=user_id,
                stage_id=payload.stage_id,
                worker_id=payload.worker_id,
            )
            order_row = assessment["order_row"]
            stage_row = assessment["stage_row"]
            risks = assessment["risks"]

            override_reason = (payload.override_reason or "").strip()
            if risks and not override_reason:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "存在派单风险，必须填写强制派单原因",
                        "risk_codes": [item["code"] for item in risks],
                        "risks": risks,
                    },
                )

            previous_stage_type = {
                "staging": "picking",
                "shipping": "staging",
            }.get(stage_row["stage_type"])
            previous_stage_id = None
            if previous_stage_type:
                previous_stage_result = await self.session.execute(
                    text(
                        """
                        SELECT id
                        FROM order_stages
                        WHERE order_id = :order_id
                          AND stage_type = :stage_type
                        LIMIT 1
                        """
                    ),
                    {
                        "order_id": order_id,
                        "stage_type": previous_stage_type,
                    },
                )
                previous_stage = previous_stage_result.mappings().first()
                previous_stage_id = previous_stage["id"] if previous_stage else None

            description = payload.description.strip() if payload.description else None
            if risks:
                risk_codes = ",".join(item["code"] for item in risks)
                audit_prefix = f"[override][{risk_codes}] {override_reason}"
                description = f"{audit_prefix}\n{description}" if description else audit_prefix

            insert_result = await self.session.execute(
                text(
                    """
                    INSERT INTO work_orders (
                        order_id,
                        stage_id,
                        worker_id,
                        dispatcher_id,
                        warehouse_id,
                        status,
                        priority,
                        deadline,
                        description,
                        source,
                        created_at,
                        updated_at
                    ) VALUES (
                        :order_id,
                        :stage_id,
                        :worker_id,
                        :dispatcher_id,
                        :warehouse_id,
                        'pending',
                        :priority,
                        :deadline,
                        :description,
                        'manual',
                        (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    )
                    RETURNING id
                    """
                ),
                {
                    "order_id": order_id,
                    "stage_id": payload.stage_id,
                    "worker_id": payload.worker_id,
                    "dispatcher_id": user_id,
                    "warehouse_id": order_row["warehouse_id"],
                    "priority": payload.priority,
                    "deadline": payload.deadline,
                    "description": description,
                },
            )
            new_row = insert_result.mappings().first()
            if not new_row:
                raise HTTPException(status_code=409, detail="Failed to create work order")

            if previous_stage_id is not None:
                await self._try_auto_complete_stage(stage_id=previous_stage_id, operated_by=user_id)

            await self.session.commit()
            return await self._get_work_order_detail(work_order_id=new_row["id"])
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def terminate_work_order(self, work_order_id: int, user_id: int, reason: str):
        try:
            lock_result = await self.session.execute(
                text(
                    """
                    SELECT id, order_id, stage_id, dispatcher_id, status
                    FROM work_orders
                    WHERE id = :work_order_id
                    FOR UPDATE
                    """
                ),
                {"work_order_id": work_order_id},
            )
            work_order = lock_result.mappings().first()
            if not work_order:
                raise HTTPException(status_code=404, detail="Work order not found")
            if work_order["dispatcher_id"] != user_id:
                raise HTTPException(status_code=403, detail="Only responsible dispatcher can terminate this work order")
            if work_order["status"] not in ("pending", "in_progress"):
                raise HTTPException(status_code=400, detail="Only pending or in-progress work orders can be terminated")

            await self.session.execute(
                text(
                    """
                    UPDATE work_orders
                    SET
                        status = 'terminated',
                        terminated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        terminated_by = :terminated_by,
                        termination_reason = :reason,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :work_order_id
                    """
                ),
                {
                    "work_order_id": work_order_id,
                    "terminated_by": user_id,
                    "reason": reason,
                },
            )

            await self._try_auto_complete_stage(stage_id=work_order["stage_id"], operated_by=user_id)

            await self.session.commit()
            return await self._get_work_order_detail(work_order_id=work_order_id)
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def manual_complete_stage(self, order_id: int, stage_id: int, user_id: int, remark: str):
        try:
            order_row = await self._get_dispatcher_order(order_id=order_id, user_id=user_id)
            if order_row["status"] != "in_progress":
                raise HTTPException(status_code=400, detail="Only in-progress orders can complete stages")

            stage_result = await self.session.execute(
                text(
                    """
                    SELECT id, stage_type, status
                    FROM order_stages
                    WHERE id = :stage_id
                      AND order_id = :order_id
                    FOR UPDATE
                    """
                ),
                {"stage_id": stage_id, "order_id": order_id},
            )
            stage_row = stage_result.mappings().first()
            if not stage_row:
                raise HTTPException(status_code=404, detail="Stage not found")
            if stage_row["status"] == "completed":
                raise HTTPException(status_code=400, detail="Stage is already completed")

            stats_result = await self.session.execute(
                text(
                    """
                    SELECT
                        COALESCE(COUNT(*) FILTER (WHERE status = 'completed'), 0)::INTEGER AS completed_count,
                        COALESCE(COUNT(*) FILTER (WHERE status IN ('pending', 'in_progress')), 0)::INTEGER AS open_count
                    FROM work_orders
                    WHERE stage_id = :stage_id
                    """
                ),
                {"stage_id": stage_id},
            )
            stats = stats_result.mappings().first()
            if not stats or stats["completed_count"] < 1:
                raise HTTPException(status_code=400, detail="Manual completion requires at least one completed work order")
            if stats["open_count"] > 0:
                raise HTTPException(status_code=400, detail="Manual completion requires no pending or in-progress work orders")

            await self.session.execute(
                text(
                    """
                    UPDATE order_stages
                    SET
                        status = 'completed',
                        completion_type = 'manual',
                        completed_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        completed_by = :completed_by,
                        remark = :remark,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :stage_id
                    """
                ),
                {
                    "stage_id": stage_id,
                    "completed_by": user_id,
                    "remark": remark,
                },
            )

            if stage_row["stage_type"] == "shipping":
                await self._finalize_order_if_shipping_completed(order_id=order_id, operated_by=user_id)

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def _try_auto_complete_stage(self, stage_id: int, operated_by: Optional[int] = None):
        stage_result = await self.session.execute(
            text(
                """
                SELECT id, order_id, stage_type, status
                FROM order_stages
                WHERE id = :stage_id
                FOR UPDATE
                """
            ),
            {"stage_id": stage_id},
        )
        stage_row = stage_result.mappings().first()
        if not stage_row or stage_row["status"] == "completed":
            return

        stats_result = await self.session.execute(
            text(
                """
                SELECT
                    COALESCE(COUNT(*), 0)::INTEGER AS total_count,
                    COALESCE(COUNT(*) FILTER (WHERE status = 'completed'), 0)::INTEGER AS completed_count,
                    COALESCE(COUNT(*) FILTER (WHERE status IN ('pending', 'in_progress')), 0)::INTEGER AS open_count
                FROM work_orders
                WHERE stage_id = :stage_id
                """
            ),
            {"stage_id": stage_id},
        )
        stats = stats_result.mappings().first()
        if not stats:
            return

        if stats["total_count"] < 1:
            return

        if stats["completed_count"] != stats["total_count"] or stats["open_count"] > 0:
            return

        if stage_row["stage_type"] != "shipping":
            next_stage_type = {
                "picking": "staging",
                "staging": "shipping",
            }.get(stage_row["stage_type"])
            if not next_stage_type:
                return

            next_stage_result = await self.session.execute(
                text(
                    """
                    SELECT id
                    FROM order_stages
                    WHERE order_id = :order_id
                      AND stage_type = :stage_type
                    LIMIT 1
                    """
                ),
                {
                    "order_id": stage_row["order_id"],
                    "stage_type": next_stage_type,
                },
            )
            next_stage = next_stage_result.mappings().first()
            if not next_stage:
                return

            next_stage_work_order_count_result = await self.session.execute(
                text(
                    """
                    SELECT COUNT(*)::INTEGER AS total
                    FROM work_orders
                    WHERE stage_id = :stage_id
                    """
                ),
                {"stage_id": next_stage["id"]},
            )
            next_stage_work_order_count = next_stage_work_order_count_result.scalar_one() or 0
            if next_stage_work_order_count < 1:
                return

        await self.session.execute(
            text(
                """
                UPDATE order_stages
                SET
                    status = 'completed',
                    completion_type = 'auto',
                    completed_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                    completed_by = NULL,
                    updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                WHERE id = :stage_id
                  AND status <> 'completed'
                """
            ),
            {"stage_id": stage_id},
        )

        if stage_row["stage_type"] == "shipping":
            await self._finalize_order_if_shipping_completed(order_id=stage_row["order_id"], operated_by=operated_by)

    async def _finalize_order_if_shipping_completed(self, order_id: int, operated_by: Optional[int] = None):
        order_result = await self.session.execute(
            text(
                """
                SELECT id, status, warehouse_id
                FROM orders
                WHERE id = :order_id
                FOR UPDATE
                """
            ),
            {"order_id": order_id},
        )
        order_row = order_result.mappings().first()
        if not order_row or order_row["status"] != "in_progress":
            return

        shipping_stage_result = await self.session.execute(
            text(
                """
                SELECT status
                FROM order_stages
                WHERE order_id = :order_id
                  AND stage_type = 'shipping'
                LIMIT 1
                """
            ),
            {"order_id": order_id},
        )
        shipping_stage = shipping_stage_result.mappings().first()
        if not shipping_stage or shipping_stage["status"] != "completed":
            return

        required_items_result = await self.session.execute(
            text(
                """
                SELECT
                    oi.product_id,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS required_qty
                FROM order_items oi
                WHERE oi.order_id = :order_id
                GROUP BY oi.product_id
                ORDER BY oi.product_id
                """
            ),
            {"order_id": order_id},
        )
        required_items = [dict(row) for row in required_items_result.mappings().all()]
        if not required_items:
            raise HTTPException(status_code=400, detail="Order has no items")

        required_by_product = {row["product_id"]: row["required_qty"] for row in required_items}

        inventory_rows_result = await self.session.execute(
            text(
                """
                SELECT
                    i.id AS inventory_id,
                    i.product_id,
                    i.qty_on_hand,
                    i.qty_reserved,
                    i.qty_locked
                FROM inventory i
                WHERE i.warehouse_id = :warehouse_id
                  AND i.product_id IN (
                      SELECT DISTINCT oi.product_id
                      FROM order_items oi
                      WHERE oi.order_id = :order_id
                  )
                ORDER BY i.product_id
                FOR UPDATE
                """
            ),
            {
                "warehouse_id": order_row["warehouse_id"],
                "order_id": order_id,
            },
        )
        inventory_rows = [dict(row) for row in inventory_rows_result.mappings().all()]
        inventory_by_product = {row["product_id"]: row for row in inventory_rows}

        missing_products = sorted(set(required_by_product.keys()) - set(inventory_by_product.keys()))
        if missing_products:
            raise HTTPException(status_code=409, detail="Inventory rows missing for shipping deduction")

        for product_id, required_qty in required_by_product.items():
            inventory_row = inventory_by_product[product_id]
            if inventory_row["qty_on_hand"] < required_qty or inventory_row["qty_reserved"] < required_qty:
                raise HTTPException(status_code=409, detail="Insufficient inventory quantities for shipping deduction")

            before_on_hand = inventory_row["qty_on_hand"]
            before_reserved = inventory_row["qty_reserved"]
            before_locked = inventory_row["qty_locked"]

            updated_inventory_result = await self.session.execute(
                text(
                    """
                    UPDATE inventory
                    SET
                        qty_on_hand = qty_on_hand - :qty,
                        qty_reserved = qty_reserved - :qty,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :inventory_id
                    RETURNING qty_on_hand, qty_reserved, qty_locked
                    """
                ),
                {
                    "inventory_id": inventory_row["inventory_id"],
                    "qty": required_qty,
                },
            )
            updated_inventory = updated_inventory_result.mappings().first()
            if not updated_inventory:
                raise HTTPException(status_code=409, detail="Inventory update conflict during shipping completion")

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
                        'ship_deduct',
                        :delta_on_hand,
                        :delta_reserved,
                        0,
                        :before_on_hand,
                        :before_reserved,
                        :before_locked,
                        :after_on_hand,
                        :after_reserved,
                        :after_locked,
                        'order',
                        :related_id,
                        :operated_by
                    )
                    """
                ),
                {
                    "inventory_id": inventory_row["inventory_id"],
                    "warehouse_id": order_row["warehouse_id"],
                    "product_id": product_id,
                    "delta_on_hand": -required_qty,
                    "delta_reserved": -required_qty,
                    "before_on_hand": before_on_hand,
                    "before_reserved": before_reserved,
                    "before_locked": before_locked,
                    "after_on_hand": updated_inventory["qty_on_hand"],
                    "after_reserved": updated_inventory["qty_reserved"],
                    "after_locked": updated_inventory["qty_locked"],
                    "related_id": order_id,
                    "operated_by": operated_by,
                },
            )

        await self.session.execute(
            text(
                """
                UPDATE orders
                SET
                    status = 'completed',
                    completed_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                    updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                WHERE id = :order_id
                  AND status = 'in_progress'
                """
            ),
            {"order_id": order_id},
        )

    @staticmethod
    def _transfer_code(transfer_id: int, created_at):
        if created_at:
            return f"TR-{created_at.strftime('%Y%m%d')}-{transfer_id:04d}"
        return f"TR-{transfer_id:04d}"

    @staticmethod
    def _build_inbound_response(row: dict):
        if not row.get("inbound_id"):
            return None

        return {
            "id": row["inbound_id"],
            "transfer_order_id": row["id"],
            "warehouse_id": row["inbound_warehouse_id"],
            "warehouse_name": row.get("inbound_warehouse_name"),
            "product_id": row["product_id"],
            "product_sku": row["product_sku"],
            "product_name": row["product_name"],
            "qty": row["inbound_qty"],
            "status": row["inbound_status"],
            "expected_arrival_at": row.get("expected_arrival_at"),
            "confirmed_by": row.get("confirmed_by"),
            "confirmed_by_name": row.get("confirmed_by_name"),
            "confirmed_at": row.get("confirmed_at"),
            "created_at": row["inbound_created_at"],
        }

    def _build_transfer_response(self, row: dict):
        return {
            "id": row["id"],
            "code": self._transfer_code(row["id"], row.get("created_at")),
            "product_id": row["product_id"],
            "product_sku": row["product_sku"],
            "product_name": row["product_name"],
            "from_warehouse_id": row["from_warehouse_id"],
            "from_warehouse_name": row["from_warehouse_name"],
            "to_warehouse_id": row["to_warehouse_id"],
            "to_warehouse_name": row["to_warehouse_name"],
            "requested_by": row["requested_by"],
            "requested_by_name": row.get("requested_by_name"),
            "review_dispatcher_id": row.get("review_dispatcher_id"),
            "review_dispatcher_name": row.get("review_dispatcher_name"),
            "approved_by": row.get("approved_by"),
            "approved_by_name": row.get("approved_by_name"),
            "qty": row["qty"],
            "status": row["status"],
            "description": row.get("description"),
            "rejection_reason": row.get("rejection_reason"),
            "source": row["source"],
            "agent_reason": row.get("agent_reason"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "approved_at": row.get("approved_at"),
            "executed_at": row.get("executed_at"),
            "completed_at": row.get("completed_at"),
            "inbound_record": self._build_inbound_response(row),
        }

    async def _get_dispatcher_context(self, user_id: int):
        result = await self.session.execute(
            text(
                """
                SELECT id, role, warehouse_id, is_active
                FROM users
                WHERE id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        user = result.mappings().first()
        if not user or user["role"] != "dispatcher":
            raise HTTPException(status_code=403, detail="Access denied")
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Dispatcher is disabled")
        if not user["warehouse_id"]:
            raise HTTPException(status_code=400, detail="Dispatcher warehouse is required")
        return dict(user)

    async def list_transfer_source_warehouses(self, user_id: int):
        user = await self._get_dispatcher_context(user_id=user_id)
        result = await self.session.execute(
            text(
                """
                SELECT id, name, address
                FROM warehouses
                WHERE is_active = true
                  AND id <> :warehouse_id
                ORDER BY name ASC, id ASC
                """
            ),
            {"warehouse_id": user["warehouse_id"]},
        )
        return [dict(row) for row in result.mappings().all()]

    async def list_transfer_source_dispatchers(self, user_id: int, source_warehouse_id: int):
        user = await self._get_dispatcher_context(user_id=user_id)
        if source_warehouse_id == user["warehouse_id"]:
            raise HTTPException(status_code=400, detail="Source warehouse must differ from requester warehouse")

        result = await self.session.execute(
            text(
                """
                SELECT id, username, email
                FROM users
                WHERE role = 'dispatcher'
                  AND is_active = true
                  AND warehouse_id = :warehouse_id
                ORDER BY username ASC, id ASC
                """
            ),
            {"warehouse_id": source_warehouse_id},
        )
        return [dict(row) for row in result.mappings().all()]

    async def list_transfer_source_inventory(self, user_id: int, source_warehouse_id: int, search: Optional[str] = None):
        user = await self._get_dispatcher_context(user_id=user_id)
        if source_warehouse_id == user["warehouse_id"]:
            raise HTTPException(status_code=400, detail="Source warehouse must differ from requester warehouse")

        where = ["i.warehouse_id = :warehouse_id", "i.qty_available > 0"]
        params = {"warehouse_id": source_warehouse_id}
        if search:
            where.append("(p.sku ILIKE :search OR p.name ILIKE :search)")
            params["search"] = f"%{search}%"

        rows = await self.session.execute(
            text(
                f"""
                SELECT
                    p.id AS product_id,
                    p.sku,
                    p.name AS product_name,
                    i.qty_available
                FROM inventory i
                JOIN products p ON p.id = i.product_id
                WHERE {' AND '.join(where)}
                ORDER BY p.name ASC, p.id ASC
                """
            ),
            params,
        )
        return [dict(row) for row in rows.mappings().all()]

    async def create_transfer(self, user_id: int, payload: DispatcherTransferCreateRequest):
        try:
            user = await self._get_dispatcher_context(user_id=user_id)
            to_warehouse_id = user["warehouse_id"]
            from_warehouse_id = payload.from_warehouse_id
            if from_warehouse_id == to_warehouse_id:
                raise HTTPException(status_code=400, detail="Source and destination warehouses must differ")

            reviewer_result = await self.session.execute(
                text(
                    """
                    SELECT id, role, warehouse_id, is_active
                    FROM users
                    WHERE id = :review_dispatcher_id
                    LIMIT 1
                    """
                ),
                {"review_dispatcher_id": payload.review_dispatcher_id},
            )
            reviewer = reviewer_result.mappings().first()
            if not reviewer or reviewer["role"] != "dispatcher" or not reviewer["is_active"]:
                raise HTTPException(status_code=400, detail="Selected review dispatcher is invalid")
            if reviewer["warehouse_id"] != from_warehouse_id:
                raise HTTPException(status_code=400, detail="Selected review dispatcher does not belong to source warehouse")

            inventory_result = await self.session.execute(
                text(
                    """
                    SELECT id, qty_on_hand, qty_reserved, qty_locked, qty_available
                    FROM inventory
                    WHERE warehouse_id = :warehouse_id
                      AND product_id = :product_id
                    FOR UPDATE
                    """
                ),
                {
                    "warehouse_id": from_warehouse_id,
                    "product_id": payload.product_id,
                },
            )
            inventory_row = inventory_result.mappings().first()
            if not inventory_row:
                raise HTTPException(status_code=400, detail="Source warehouse inventory not found for selected product")
            if inventory_row["qty_available"] < payload.qty:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Source warehouse available inventory is insufficient",
                        "required_qty": payload.qty,
                        "available_qty": inventory_row["qty_available"],
                    },
                )

            update_result = await self.session.execute(
                text(
                    """
                    UPDATE inventory
                    SET
                        qty_locked = qty_locked + :qty,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :inventory_id
                    RETURNING qty_on_hand, qty_reserved, qty_locked
                    """
                ),
                {
                    "inventory_id": inventory_row["id"],
                    "qty": payload.qty,
                },
            )
            updated_inventory = update_result.mappings().first()
            if not updated_inventory:
                raise HTTPException(status_code=409, detail="Failed to lock source inventory")

            insert_transfer_result = await self.session.execute(
                text(
                    """
                    INSERT INTO transfer_orders (
                        product_id,
                        from_warehouse_id,
                        to_warehouse_id,
                        requested_by,
                        review_dispatcher_id,
                        qty,
                        status,
                        description,
                        source,
                        created_at,
                        updated_at
                    ) VALUES (
                        :product_id,
                        :from_warehouse_id,
                        :to_warehouse_id,
                        :requested_by,
                        :review_dispatcher_id,
                        :qty,
                        'pending',
                        :description,
                        'manual',
                        (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    )
                    RETURNING id
                    """
                ),
                {
                    "product_id": payload.product_id,
                    "from_warehouse_id": from_warehouse_id,
                    "to_warehouse_id": to_warehouse_id,
                    "requested_by": user_id,
                    "review_dispatcher_id": payload.review_dispatcher_id,
                    "qty": payload.qty,
                    "description": payload.description.strip() if payload.description else None,
                },
            )
            transfer_row = insert_transfer_result.mappings().first()
            if not transfer_row:
                raise HTTPException(status_code=409, detail="Failed to create transfer order")
            transfer_id = transfer_row["id"]

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
                        'transfer_lock',
                        0,
                        0,
                        :delta_locked,
                        :before_on_hand,
                        :before_reserved,
                        :before_locked,
                        :after_on_hand,
                        :after_reserved,
                        :after_locked,
                        'transfer_order',
                        :related_id,
                        :operated_by
                    )
                    """
                ),
                {
                    "inventory_id": inventory_row["id"],
                    "warehouse_id": from_warehouse_id,
                    "product_id": payload.product_id,
                    "delta_locked": payload.qty,
                    "before_on_hand": inventory_row["qty_on_hand"],
                    "before_reserved": inventory_row["qty_reserved"],
                    "before_locked": inventory_row["qty_locked"],
                    "after_on_hand": updated_inventory["qty_on_hand"],
                    "after_reserved": updated_inventory["qty_reserved"],
                    "after_locked": updated_inventory["qty_locked"],
                    "related_id": transfer_id,
                    "operated_by": user_id,
                },
            )

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        return await self.get_transfer_detail(transfer_id=transfer_id, user_id=user_id)

    async def list_transfers(
        self,
        user_id: int,
        status_filter: Optional[str] = None,
        scope: str = "all",
        search: Optional[str] = None,
    ):
        user = await self._get_dispatcher_context(user_id=user_id)
        warehouse_id = user["warehouse_id"]

        allowed_scope = {"all", "requested", "approval", "inbound"}
        if scope not in allowed_scope:
            raise HTTPException(status_code=400, detail="Invalid transfer scope")

        allowed_status = {"pending", "approved", "rejected", "cancelled", "completed"}
        if status_filter and status_filter not in allowed_status:
            raise HTTPException(status_code=400, detail="Invalid transfer status filter")

        where = []
        params = {
            "user_id": user_id,
            "warehouse_id": warehouse_id,
        }

        if scope == "requested":
            where.append("t.requested_by = :user_id")
        elif scope == "approval":
            where.append("t.review_dispatcher_id = :user_id")
            where.append("t.status IN ('pending', 'approved', 'rejected', 'completed')")
        elif scope == "inbound":
            where.append("t.to_warehouse_id = :warehouse_id")
            where.append("t.requested_by = :user_id")
            where.append("ir.id IS NOT NULL")
            where.append("ir.status = 'pending'")
        else:
            where.append("(t.requested_by = :user_id OR t.from_warehouse_id = :warehouse_id OR t.to_warehouse_id = :warehouse_id)")

        if status_filter:
            where.append("t.status = :status")
            params["status"] = status_filter

        if search:
            where.append(
                "(CAST(t.id AS TEXT) ILIKE :search OR p.sku ILIKE :search OR p.name ILIKE :search OR wf.name ILIKE :search OR wt.name ILIKE :search)"
            )
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where) if where else "1=1"

        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)::INTEGER
                FROM transfer_orders t
                JOIN products p ON p.id = t.product_id
                JOIN warehouses wf ON wf.id = t.from_warehouse_id
                JOIN warehouses wt ON wt.id = t.to_warehouse_id
                LEFT JOIN inbound_records ir ON ir.transfer_order_id = t.id
                WHERE {where_sql}
                """
            ),
            params,
        )
        total = count_result.scalar_one() or 0

        rows_result = await self.session.execute(
            text(
                f"""
                SELECT
                    t.id,
                    t.product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    t.from_warehouse_id,
                    wf.name AS from_warehouse_name,
                    t.to_warehouse_id,
                    wt.name AS to_warehouse_name,
                    t.requested_by,
                    ur.username AS requested_by_name,
                    t.review_dispatcher_id,
                    rv.username AS review_dispatcher_name,
                    t.approved_by,
                    ua.username AS approved_by_name,
                    t.qty,
                    t.status,
                    t.description,
                    t.rejection_reason,
                    t.source,
                    t.agent_reason,
                    t.created_at,
                    t.updated_at,
                    t.approved_at,
                    t.executed_at,
                    t.completed_at,
                    ir.id AS inbound_id,
                    ir.warehouse_id AS inbound_warehouse_id,
                    wir.name AS inbound_warehouse_name,
                    ir.qty AS inbound_qty,
                    ir.status AS inbound_status,
                    ir.expected_arrival_at,
                    ir.confirmed_by,
                    uc.username AS confirmed_by_name,
                    ir.confirmed_at,
                    ir.created_at AS inbound_created_at
                FROM transfer_orders t
                JOIN products p ON p.id = t.product_id
                JOIN warehouses wf ON wf.id = t.from_warehouse_id
                JOIN warehouses wt ON wt.id = t.to_warehouse_id
                JOIN users ur ON ur.id = t.requested_by
                LEFT JOIN users rv ON rv.id = t.review_dispatcher_id
                LEFT JOIN users ua ON ua.id = t.approved_by
                LEFT JOIN inbound_records ir ON ir.transfer_order_id = t.id
                LEFT JOIN warehouses wir ON wir.id = ir.warehouse_id
                LEFT JOIN users uc ON uc.id = ir.confirmed_by
                WHERE {where_sql}
                ORDER BY t.created_at DESC, t.id DESC
                """
            ),
            params,
        )
        items = [self._build_transfer_response(dict(row)) for row in rows_result.mappings().all()]
        return {"items": items, "total": total}

    async def get_transfer_detail(self, transfer_id: int, user_id: int):
        user = await self._get_dispatcher_context(user_id=user_id)
        row_result = await self.session.execute(
            text(
                """
                SELECT
                    t.id,
                    t.product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    t.from_warehouse_id,
                    wf.name AS from_warehouse_name,
                    t.to_warehouse_id,
                    wt.name AS to_warehouse_name,
                    t.requested_by,
                    ur.username AS requested_by_name,
                    t.review_dispatcher_id,
                    rv.username AS review_dispatcher_name,
                    t.approved_by,
                    ua.username AS approved_by_name,
                    t.qty,
                    t.status,
                    t.description,
                    t.rejection_reason,
                    t.source,
                    t.agent_reason,
                    t.created_at,
                    t.updated_at,
                    t.approved_at,
                    t.executed_at,
                    t.completed_at,
                    ir.id AS inbound_id,
                    ir.warehouse_id AS inbound_warehouse_id,
                    wir.name AS inbound_warehouse_name,
                    ir.qty AS inbound_qty,
                    ir.status AS inbound_status,
                    ir.expected_arrival_at,
                    ir.confirmed_by,
                    uc.username AS confirmed_by_name,
                    ir.confirmed_at,
                    ir.created_at AS inbound_created_at
                FROM transfer_orders t
                JOIN products p ON p.id = t.product_id
                JOIN warehouses wf ON wf.id = t.from_warehouse_id
                JOIN warehouses wt ON wt.id = t.to_warehouse_id
                JOIN users ur ON ur.id = t.requested_by
                LEFT JOIN users rv ON rv.id = t.review_dispatcher_id
                LEFT JOIN users ua ON ua.id = t.approved_by
                LEFT JOIN inbound_records ir ON ir.transfer_order_id = t.id
                LEFT JOIN warehouses wir ON wir.id = ir.warehouse_id
                LEFT JOIN users uc ON uc.id = ir.confirmed_by
                WHERE t.id = :transfer_id
                  AND (t.requested_by = :user_id OR t.from_warehouse_id = :warehouse_id OR t.to_warehouse_id = :warehouse_id)
                LIMIT 1
                """
            ),
            {
                "transfer_id": transfer_id,
                "user_id": user_id,
                "warehouse_id": user["warehouse_id"],
            },
        )
        row = row_result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Transfer order not found")
        return self._build_transfer_response(dict(row))

    async def approve_transfer(self, transfer_id: int, user_id: int, reason: Optional[str] = None):
        try:
            user = await self._get_dispatcher_context(user_id=user_id)
            transfer_result = await self.session.execute(
                text(
                    """
                    SELECT id, product_id, from_warehouse_id, to_warehouse_id, requested_by, review_dispatcher_id, qty, status
                    FROM transfer_orders
                    WHERE id = :transfer_id
                    FOR UPDATE
                    """
                ),
                {"transfer_id": transfer_id},
            )
            transfer = transfer_result.mappings().first()
            if not transfer:
                raise HTTPException(status_code=404, detail="Transfer order not found")
            if transfer.get("review_dispatcher_id") is not None and transfer["review_dispatcher_id"] != user_id:
                raise HTTPException(status_code=403, detail="Only the designated dispatcher can approve")
            if transfer.get("review_dispatcher_id") is None and user["warehouse_id"] != transfer["from_warehouse_id"]:
                raise HTTPException(status_code=403, detail="Only source warehouse dispatchers can approve")
            if transfer["status"] != "pending":
                raise HTTPException(status_code=400, detail="Only pending transfer orders can be approved")

            inventory_result = await self.session.execute(
                text(
                    """
                    SELECT qty_on_hand, qty_reserved, qty_locked
                    FROM inventory
                    WHERE warehouse_id = :warehouse_id
                      AND product_id = :product_id
                    FOR UPDATE
                    """
                ),
                {
                    "warehouse_id": transfer["from_warehouse_id"],
                    "product_id": transfer["product_id"],
                },
            )
            inventory_row = inventory_result.mappings().first()
            if not inventory_row:
                raise HTTPException(status_code=409, detail="Source inventory row not found during approval")
            if inventory_row["qty_locked"] < transfer["qty"]:
                raise HTTPException(
                    status_code=409,
                    detail="Approval check failed: locked quantity is insufficient",
                )
            if inventory_row["qty_on_hand"] < transfer["qty"]:
                raise HTTPException(
                    status_code=409,
                    detail="Approval check failed: on-hand quantity is insufficient",
                )

            check_value = inventory_row["qty_on_hand"] - inventory_row["qty_reserved"] - inventory_row["qty_locked"]
            if check_value < 0:
                raise HTTPException(
                    status_code=409,
                    detail="Approval check failed: source inventory became inconsistent",
                )

            await self.session.execute(
                text(
                    """
                    UPDATE transfer_orders
                    SET
                        status = 'approved',
                        approved_by = :approved_by,
                        approved_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        rejection_reason = NULL,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :transfer_id
                    """
                ),
                {
                    "transfer_id": transfer_id,
                    "approved_by": user_id,
                },
            )
            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        return await self.get_transfer_detail(transfer_id=transfer_id, user_id=user_id)

    async def reject_transfer(self, transfer_id: int, user_id: int, reason: Optional[str] = None):
        try:
            reject_reason = (reason or "").strip()
            if not reject_reason:
                raise HTTPException(status_code=400, detail="Rejection reason is required")

            user = await self._get_dispatcher_context(user_id=user_id)
            transfer_result = await self.session.execute(
                text(
                    """
                    SELECT id, product_id, from_warehouse_id, review_dispatcher_id, qty, status
                    FROM transfer_orders
                    WHERE id = :transfer_id
                    FOR UPDATE
                    """
                ),
                {"transfer_id": transfer_id},
            )
            transfer = transfer_result.mappings().first()
            if not transfer:
                raise HTTPException(status_code=404, detail="Transfer order not found")
            if transfer.get("review_dispatcher_id") is not None and transfer["review_dispatcher_id"] != user_id:
                raise HTTPException(status_code=403, detail="Only the designated dispatcher can reject")
            if transfer.get("review_dispatcher_id") is None and user["warehouse_id"] != transfer["from_warehouse_id"]:
                raise HTTPException(status_code=403, detail="Only source warehouse dispatchers can reject")
            if transfer["status"] != "pending":
                raise HTTPException(status_code=400, detail="Only pending transfer orders can be rejected")

            inventory_result = await self.session.execute(
                text(
                    """
                    SELECT id, qty_on_hand, qty_reserved, qty_locked
                    FROM inventory
                    WHERE warehouse_id = :warehouse_id
                      AND product_id = :product_id
                    FOR UPDATE
                    """
                ),
                {
                    "warehouse_id": transfer["from_warehouse_id"],
                    "product_id": transfer["product_id"],
                },
            )
            inventory_row = inventory_result.mappings().first()
            if not inventory_row:
                raise HTTPException(status_code=409, detail="Source inventory row not found during rejection")
            if inventory_row["qty_locked"] < transfer["qty"]:
                raise HTTPException(status_code=409, detail="Locked quantity is insufficient for unlock")

            update_result = await self.session.execute(
                text(
                    """
                    UPDATE inventory
                    SET
                        qty_locked = qty_locked - :qty,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :inventory_id
                    RETURNING qty_on_hand, qty_reserved, qty_locked
                    """
                ),
                {
                    "inventory_id": inventory_row["id"],
                    "qty": transfer["qty"],
                },
            )
            updated_inventory = update_result.mappings().first()
            if not updated_inventory:
                raise HTTPException(status_code=409, detail="Failed to unlock source inventory")

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
                        'transfer_unlock',
                        0,
                        0,
                        :delta_locked,
                        :before_on_hand,
                        :before_reserved,
                        :before_locked,
                        :after_on_hand,
                        :after_reserved,
                        :after_locked,
                        'transfer_order',
                        :related_id,
                        :operated_by
                    )
                    """
                ),
                {
                    "inventory_id": inventory_row["id"],
                    "warehouse_id": transfer["from_warehouse_id"],
                    "product_id": transfer["product_id"],
                    "delta_locked": -transfer["qty"],
                    "before_on_hand": inventory_row["qty_on_hand"],
                    "before_reserved": inventory_row["qty_reserved"],
                    "before_locked": inventory_row["qty_locked"],
                    "after_on_hand": updated_inventory["qty_on_hand"],
                    "after_reserved": updated_inventory["qty_reserved"],
                    "after_locked": updated_inventory["qty_locked"],
                    "related_id": transfer_id,
                    "operated_by": user_id,
                },
            )

            await self.session.execute(
                text(
                    """
                    UPDATE transfer_orders
                    SET
                        status = 'rejected',
                        approved_by = :approved_by,
                        approved_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        rejection_reason = :rejection_reason,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :transfer_id
                    """
                ),
                {
                    "transfer_id": transfer_id,
                    "approved_by": user_id,
                    "rejection_reason": reject_reason,
                },
            )

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        return await self.get_transfer_detail(transfer_id=transfer_id, user_id=user_id)

    async def execute_transfer(self, transfer_id: int, user_id: int, expected_arrival_at=None):
        try:
            user = await self._get_dispatcher_context(user_id=user_id)
            transfer_result = await self.session.execute(
                text(
                    """
                    SELECT id, product_id, from_warehouse_id, to_warehouse_id, qty, status, executed_at, approved_by
                    FROM transfer_orders
                    WHERE id = :transfer_id
                    FOR UPDATE
                    """
                ),
                {"transfer_id": transfer_id},
            )
            transfer = transfer_result.mappings().first()
            if not transfer:
                raise HTTPException(status_code=404, detail="Transfer order not found")
            if transfer["approved_by"] != user_id:
                raise HTTPException(status_code=403, detail="Only the approver can execute transfer")
            if transfer["status"] != "approved":
                raise HTTPException(status_code=400, detail="Only approved transfer orders can be executed")
            if transfer["executed_at"] is not None:
                raise HTTPException(status_code=400, detail="Transfer order has already been executed")

            inventory_result = await self.session.execute(
                text(
                    """
                    SELECT id, qty_on_hand, qty_reserved, qty_locked
                    FROM inventory
                    WHERE warehouse_id = :warehouse_id
                      AND product_id = :product_id
                    FOR UPDATE
                    """
                ),
                {
                    "warehouse_id": transfer["from_warehouse_id"],
                    "product_id": transfer["product_id"],
                },
            )
            inventory_row = inventory_result.mappings().first()
            if not inventory_row:
                raise HTTPException(status_code=409, detail="Source inventory row not found during execution")
            if inventory_row["qty_locked"] < transfer["qty"]:
                raise HTTPException(status_code=409, detail="Locked quantity is insufficient for execution")
            if inventory_row["qty_on_hand"] < transfer["qty"]:
                raise HTTPException(status_code=409, detail="On-hand quantity is insufficient for execution")

            update_result = await self.session.execute(
                text(
                    """
                    UPDATE inventory
                    SET
                        qty_on_hand = qty_on_hand - :qty,
                        qty_locked = qty_locked - :qty,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :inventory_id
                    RETURNING qty_on_hand, qty_reserved, qty_locked
                    """
                ),
                {
                    "inventory_id": inventory_row["id"],
                    "qty": transfer["qty"],
                },
            )
            updated_inventory = update_result.mappings().first()
            if not updated_inventory:
                raise HTTPException(status_code=409, detail="Inventory deduction conflict during execution")

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
                        'transfer_deduct',
                        :delta_on_hand,
                        0,
                        :delta_locked,
                        :before_on_hand,
                        :before_reserved,
                        :before_locked,
                        :after_on_hand,
                        :after_reserved,
                        :after_locked,
                        'transfer_order',
                        :related_id,
                        :operated_by
                    )
                    """
                ),
                {
                    "inventory_id": inventory_row["id"],
                    "warehouse_id": transfer["from_warehouse_id"],
                    "product_id": transfer["product_id"],
                    "delta_on_hand": -transfer["qty"],
                    "delta_locked": -transfer["qty"],
                    "before_on_hand": inventory_row["qty_on_hand"],
                    "before_reserved": inventory_row["qty_reserved"],
                    "before_locked": inventory_row["qty_locked"],
                    "after_on_hand": updated_inventory["qty_on_hand"],
                    "after_reserved": updated_inventory["qty_reserved"],
                    "after_locked": updated_inventory["qty_locked"],
                    "related_id": transfer_id,
                    "operated_by": user_id,
                },
            )

            await self.session.execute(
                text(
                    """
                    INSERT INTO inbound_records (
                        transfer_order_id,
                        warehouse_id,
                        product_id,
                        qty,
                        status,
                        expected_arrival_at,
                        created_at,
                        updated_at
                    ) VALUES (
                        :transfer_order_id,
                        :warehouse_id,
                        :product_id,
                        :qty,
                        'pending',
                        :expected_arrival_at,
                        (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    )
                    ON CONFLICT (transfer_order_id) DO UPDATE
                    SET
                        expected_arrival_at = COALESCE(EXCLUDED.expected_arrival_at, inbound_records.expected_arrival_at),
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    """
                ),
                {
                    "transfer_order_id": transfer_id,
                    "warehouse_id": transfer["to_warehouse_id"],
                    "product_id": transfer["product_id"],
                    "qty": transfer["qty"],
                    "expected_arrival_at": expected_arrival_at,
                },
            )

            await self.session.execute(
                text(
                    """
                    UPDATE transfer_orders
                    SET
                        executed_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :transfer_id
                    """
                ),
                {"transfer_id": transfer_id},
            )

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        return await self.get_transfer_detail(transfer_id=transfer_id, user_id=user_id)

    async def list_pending_inbound_records(self, user_id: int):
        user = await self._get_dispatcher_context(user_id=user_id)
        rows_result = await self.session.execute(
            text(
                """
                SELECT
                    ir.id,
                    ir.transfer_order_id,
                    ir.warehouse_id,
                    w.name AS warehouse_name,
                    ir.product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    ir.qty,
                    ir.status,
                    ir.expected_arrival_at,
                    ir.confirmed_by,
                    uc.username AS confirmed_by_name,
                    ir.confirmed_at,
                    ir.created_at
                FROM inbound_records ir
                JOIN transfer_orders t ON t.id = ir.transfer_order_id
                JOIN warehouses w ON w.id = ir.warehouse_id
                JOIN products p ON p.id = ir.product_id
                LEFT JOIN users uc ON uc.id = ir.confirmed_by
                WHERE ir.status = 'pending'
                  AND t.requested_by = :user_id
                  AND t.to_warehouse_id = :warehouse_id
                ORDER BY ir.created_at DESC, ir.id DESC
                """
            ),
            {
                "user_id": user_id,
                "warehouse_id": user["warehouse_id"],
            },
        )
        items = [dict(row) for row in rows_result.mappings().all()]
        return {"items": items, "total": len(items)}

    async def confirm_inbound_record(self, record_id: int, user_id: int):
        try:
            user = await self._get_dispatcher_context(user_id=user_id)

            inbound_result = await self.session.execute(
                text(
                    """
                    SELECT
                        ir.id,
                        ir.transfer_order_id,
                        ir.warehouse_id,
                        ir.product_id,
                        ir.qty,
                        ir.status,
                        ir.expected_arrival_at,
                        ir.confirmed_by,
                        ir.confirmed_at,
                        ir.created_at,
                        t.requested_by,
                        t.to_warehouse_id,
                        t.status AS transfer_status,
                        t.executed_at
                    FROM inbound_records ir
                    JOIN transfer_orders t ON t.id = ir.transfer_order_id
                    WHERE ir.id = :record_id
                    FOR UPDATE
                    """
                ),
                {"record_id": record_id},
            )
            inbound = inbound_result.mappings().first()
            if not inbound:
                raise HTTPException(status_code=404, detail="Inbound record not found")
            if inbound["status"] != "pending":
                raise HTTPException(status_code=400, detail="Inbound record is already confirmed")
            if inbound["requested_by"] != user_id:
                raise HTTPException(status_code=403, detail="Only the original requester can confirm inbound")
            if inbound["to_warehouse_id"] != user["warehouse_id"]:
                raise HTTPException(status_code=403, detail="Current dispatcher warehouse cannot confirm this inbound")
            if inbound["executed_at"] is None:
                raise HTTPException(status_code=400, detail="Transfer order has not been executed")

            inventory_result = await self.session.execute(
                text(
                    """
                    SELECT id, qty_on_hand, qty_reserved, qty_locked
                    FROM inventory
                    WHERE warehouse_id = :warehouse_id
                      AND product_id = :product_id
                    FOR UPDATE
                    """
                ),
                {
                    "warehouse_id": inbound["warehouse_id"],
                    "product_id": inbound["product_id"],
                },
            )
            inventory_row = inventory_result.mappings().first()

            if not inventory_row:
                insert_inventory_result = await self.session.execute(
                    text(
                        """
                        INSERT INTO inventory (
                            warehouse_id,
                            product_id,
                            qty_on_hand,
                            qty_reserved,
                            qty_locked,
                            qty_threshold,
                            created_at,
                            updated_at
                        ) VALUES (
                            :warehouse_id,
                            :product_id,
                            0,
                            0,
                            0,
                            0,
                            (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                            (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                        )
                        RETURNING id, qty_on_hand, qty_reserved, qty_locked
                        """
                    ),
                    {
                        "warehouse_id": inbound["warehouse_id"],
                        "product_id": inbound["product_id"],
                    },
                )
                inventory_row = insert_inventory_result.mappings().first()

            update_result = await self.session.execute(
                text(
                    """
                    UPDATE inventory
                    SET
                        qty_on_hand = qty_on_hand + :qty,
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :inventory_id
                    RETURNING qty_on_hand, qty_reserved, qty_locked
                    """
                ),
                {
                    "inventory_id": inventory_row["id"],
                    "qty": inbound["qty"],
                },
            )
            updated_inventory = update_result.mappings().first()
            if not updated_inventory:
                raise HTTPException(status_code=409, detail="Failed to confirm inbound inventory update")

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
                        'inbound_confirm',
                        :delta_on_hand,
                        0,
                        0,
                        :before_on_hand,
                        :before_reserved,
                        :before_locked,
                        :after_on_hand,
                        :after_reserved,
                        :after_locked,
                        'inbound_record',
                        :related_id,
                        :operated_by
                    )
                    """
                ),
                {
                    "inventory_id": inventory_row["id"],
                    "warehouse_id": inbound["warehouse_id"],
                    "product_id": inbound["product_id"],
                    "delta_on_hand": inbound["qty"],
                    "before_on_hand": inventory_row["qty_on_hand"],
                    "before_reserved": inventory_row["qty_reserved"],
                    "before_locked": inventory_row["qty_locked"],
                    "after_on_hand": updated_inventory["qty_on_hand"],
                    "after_reserved": updated_inventory["qty_reserved"],
                    "after_locked": updated_inventory["qty_locked"],
                    "related_id": record_id,
                    "operated_by": user_id,
                },
            )

            await self.session.execute(
                text(
                    """
                    UPDATE inbound_records
                    SET
                        status = 'confirmed',
                        confirmed_by = :confirmed_by,
                        confirmed_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :record_id
                    """
                ),
                {
                    "record_id": record_id,
                    "confirmed_by": user_id,
                },
            )

            transfer_update_result = await self.session.execute(
                text(
                    """
                    UPDATE transfer_orders
                    SET
                        status = 'completed',
                        completed_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :transfer_order_id
                      AND status = 'approved'
                      AND executed_at IS NOT NULL
                    RETURNING id
                    """
                ),
                {"transfer_order_id": inbound["transfer_order_id"]},
            )
            if not transfer_update_result.mappings().first():
                raise HTTPException(status_code=409, detail="Transfer order status conflict during inbound confirmation")

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

        row_result = await self.session.execute(
            text(
                """
                SELECT
                    ir.id,
                    ir.transfer_order_id,
                    ir.warehouse_id,
                    w.name AS warehouse_name,
                    ir.product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    ir.qty,
                    ir.status,
                    ir.expected_arrival_at,
                    ir.confirmed_by,
                    u.username AS confirmed_by_name,
                    ir.confirmed_at,
                    ir.created_at
                FROM inbound_records ir
                JOIN warehouses w ON w.id = ir.warehouse_id
                JOIN products p ON p.id = ir.product_id
                LEFT JOIN users u ON u.id = ir.confirmed_by
                WHERE ir.id = :record_id
                LIMIT 1
                """
            ),
            {"record_id": record_id},
        )
        row = row_result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Inbound record not found after confirmation")
        return dict(row)

