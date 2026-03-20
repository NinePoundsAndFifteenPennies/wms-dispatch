from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DispatcherService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _build_order_filters(
        self,
        user_id: int,
        for_my_orders: bool = False,
        search: Optional[str] = None,
    ):
        clauses = ["1=1"]
        params = {"user_id": user_id}

        if for_my_orders:
            clauses.append("o.dispatcher_id = :user_id")
            clauses.append("o.status IN ('in_progress', 'completed', 'cancelled')")
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
    ):
        where_sql, params = self._build_order_filters(
            user_id=user_id,
            for_my_orders=for_my_orders,
            search=search,
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
                SELECT id, status, dispatcher_id
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

        inventory_rows_result = await self.session.execute(
            text(
                """
                SELECT
                    i.id AS inventory_id,
                    i.qty_available,
                    oi.qty
                FROM order_items oi
                LEFT JOIN inventory i
                  ON i.product_id = oi.product_id
                 AND i.warehouse_id = :warehouse_id
                WHERE oi.order_id = :order_id
                """
            ),
            {"order_id": order_id, "warehouse_id": user["warehouse_id"]},
        )
        inventory_rows = [dict(row) for row in inventory_rows_result.mappings().all()]

        for row in inventory_rows:
            if row["inventory_id"] is None:
                raise HTTPException(status_code=400, detail="Insufficient inventory for order acceptance")
            if (row.get("qty_available") or 0) < row["qty"]:
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient inventory for order acceptance: available quantity is not enough",
                )

        for row in inventory_rows:
            update_result = await self.session.execute(
                text(
                    """
                    UPDATE inventory
                    SET
                        qty_reserved = qty_reserved + :qty,
                        updated_at = NOW()
                    WHERE id = :inventory_id
                      AND qty_available >= :qty
                    """
                ),
                {"inventory_id": row["inventory_id"], "qty": row["qty"]},
            )
            if (update_result.rowcount or 0) == 0:
                raise HTTPException(status_code=400, detail="Insufficient inventory for order acceptance")

        await self.session.execute(
            text(
                """
                UPDATE orders
                SET
                    status = 'in_progress',
                    dispatcher_id = :dispatcher_id,
                    warehouse_id = :warehouse_id,
                    accepted_at = NOW(),
                    updated_at = NOW()
                WHERE id = :order_id
                """
            ),
            {
                "order_id": order_id,
                "dispatcher_id": user_id,
                "warehouse_id": user["warehouse_id"],
            },
        )

        await self.session.execute(
            text(
                """
                INSERT INTO order_stages (order_id, stage_type, status, created_at, updated_at)
                SELECT :order_id, stage_type, 'not_started', NOW(), NOW()
                FROM (VALUES ('picking'), ('staging'), ('shipping')) AS s(stage_type)
                ON CONFLICT (order_id, stage_type) DO NOTHING
                """
            ),
            {"order_id": order_id},
        )

        await self.session.commit()
        return await self.get_order_detail(order_id=order_id, user_id=user_id, for_my_orders=True)
