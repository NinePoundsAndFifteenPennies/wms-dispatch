from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text


class DispatcherOrderServiceMixin:
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
