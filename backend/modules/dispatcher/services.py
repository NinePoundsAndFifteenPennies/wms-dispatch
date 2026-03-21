from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.dispatcher.schemas import DispatcherCreateWorkOrderRequest


class DispatcherService:
    def __init__(self, session: AsyncSession):
        self.session = session

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
                            updated_at = NOW()
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
                        accepted_at = NOW(),
                        updated_at = NOW()
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
                    SELECT :order_id, stage_type, 'not_started', NOW(), NOW()
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
                    u.skill_shipping
                FROM users u
                WHERE {' AND '.join(where)}
                ORDER BY u.username ASC, u.id ASC
                """
            ),
            params,
        )
        return [dict(row) for row in result.mappings().all()]

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
                    wo.assigned_at,
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
                    wo.assigned_at,
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
                {"stage_id": payload.stage_id, "order_id": order_id},
            )
            stage_row = stage_result.mappings().first()
            if not stage_row:
                raise HTTPException(status_code=400, detail="Stage does not belong to the target order")
            if stage_row["status"] == "completed":
                raise HTTPException(status_code=400, detail="Stage is completed and locked for new work orders")

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

            worker_result = await self.session.execute(
                text(
                    """
                    SELECT id, role, warehouse_id, is_active
                    FROM users
                    WHERE id = :worker_id
                    LIMIT 1
                    """
                ),
                {"worker_id": payload.worker_id},
            )
            worker = worker_result.mappings().first()
            if not worker or worker["role"] != "worker":
                raise HTTPException(status_code=400, detail="Invalid worker")
            if not worker["is_active"]:
                raise HTTPException(status_code=400, detail="Worker is disabled")
            if worker["warehouse_id"] != order_row["warehouse_id"]:
                raise HTTPException(status_code=400, detail="Worker warehouse does not match order warehouse")

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
                        assigned_at,
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
                        NOW(),
                        NOW(),
                        NOW()
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
                    "description": payload.description,
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
                        terminated_at = NOW(),
                        terminated_by = :terminated_by,
                        termination_reason = :reason,
                        updated_at = NOW()
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
                        completed_at = NOW(),
                        completed_by = :completed_by,
                        remark = :remark,
                        updated_at = NOW()
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
                    completed_at = NOW(),
                    completed_by = NULL,
                    updated_at = NOW()
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
                        updated_at = NOW()
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
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = :order_id
                  AND status = 'in_progress'
                """
            ),
            {"order_id": order_id},
        )
