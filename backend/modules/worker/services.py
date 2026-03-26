from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.shared.notification_rules import notify_work_order_note_exception, run_system_notification_rules


class WorkerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_my_work_orders(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        stage_type: Optional[str] = None,
        priority: Optional[str] = None,
    ):
        await run_system_notification_rules(self.session)

        where = ["wo.worker_id = :worker_id"]
        params = {
            "worker_id": user_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        allowed_status = {"pending", "in_progress", "completed", "terminated"}
        if status_filter:
            if status_filter not in allowed_status:
                raise HTTPException(status_code=400, detail="Invalid work order status filter")
            where.append("wo.status = :status")
            params["status"] = status_filter

        allowed_stage_type = {"picking", "staging", "shipping"}
        if stage_type:
            if stage_type not in allowed_stage_type:
                raise HTTPException(status_code=400, detail="Invalid stage type filter")
            where.append("os.stage_type = :stage_type")
            params["stage_type"] = stage_type

        allowed_priority = {"high", "medium", "low"}
        if priority:
            if priority not in allowed_priority:
                raise HTTPException(status_code=400, detail="Invalid priority filter")
            where.append("wo.priority = :priority")
            params["priority"] = priority

        if search:
            where.append(
                """
                (
                    CAST(wo.id AS TEXT) ILIKE :search
                    OR o.order_no ILIKE :search
                    OR COALESCE(wo.description, '') ILIKE :search
                )
                """
            )
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where)

        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)::INTEGER AS total
                FROM work_orders wo
                JOIN orders o ON o.id = wo.order_id
                JOIN order_stages os ON os.id = wo.stage_id
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
                    wo.stage_id,
                    os.stage_type,
                    d.username AS dispatcher_name,
                    wo.status,
                    wo.priority,
                    wo.deadline,
                    wo.description,
                    wo.source,
                    wo.started_at,
                    wo.completed_at,
                    wo.created_at,
                    wo.updated_at
                FROM work_orders wo
                JOIN orders o ON o.id = wo.order_id
                JOIN order_stages os ON os.id = wo.stage_id
                JOIN users d ON d.id = wo.dispatcher_id
                WHERE {where_sql}
                ORDER BY
                    CASE wo.status
                        WHEN 'pending' THEN 1
                        WHEN 'in_progress' THEN 2
                        WHEN 'completed' THEN 3
                        WHEN 'terminated' THEN 4
                        ELSE 99
                    END,
                    wo.deadline ASC NULLS LAST,
                    wo.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        items = [dict(row) for row in rows_result.mappings().all()]
        return {"items": items, "total": total}

    async def get_my_work_order_detail(self, work_order_id: int, user_id: int):
        result = await self.session.execute(
            text(
                """
                SELECT
                    wo.id,
                    wo.order_id,
                    o.order_no,
                    wo.stage_id,
                    os.stage_type,
                    d.username AS dispatcher_name,
                    wu.skill_picking,
                    wu.skill_staging,
                    wu.skill_shipping,
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
                JOIN order_stages os ON os.id = wo.stage_id
                JOIN users d ON d.id = wo.dispatcher_id
                                JOIN users wu ON wu.id = wo.worker_id
                WHERE wo.id = :work_order_id
                  AND wo.worker_id = :worker_id
                LIMIT 1
                """
            ),
            {"work_order_id": work_order_id, "worker_id": user_id},
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Work order not found")

        required_skill_key = {
            "picking": "req_skill_picking",
            "staging": "req_skill_staging",
            "shipping": "req_skill_shipping",
        }.get(row["stage_type"])
        worker_skill_key = {
            "picking": "skill_picking",
            "staging": "skill_staging",
            "shipping": "skill_shipping",
        }.get(row["stage_type"])

        if not required_skill_key or not worker_skill_key:
            raise HTTPException(status_code=400, detail="Invalid stage type on work order")

        worker_stage_skill = int(row[worker_skill_key] or 0)

        items_result = await self.session.execute(
            text(
                """
                SELECT
                    oi.product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    p.cover_image AS product_cover_image,
                    oi.qty,
                    p.req_skill_picking,
                    p.req_skill_staging,
                    p.req_skill_shipping
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = :order_id
                ORDER BY oi.id ASC
                """
            ),
            {"order_id": row["order_id"]},
        )

        order_items = []
        for item_row in items_result.mappings().all():
            item = dict(item_row)
            current_stage_required_skill = int(item.get(required_skill_key) or 0)
            order_items.append(
                {
                    **item,
                    "current_stage_required_skill": current_stage_required_skill,
                    "worker_stage_skill": worker_stage_skill,
                    "is_skill_matched": worker_stage_skill >= current_stage_required_skill,
                }
            )

        stage_skill_levels = [int(item.get("current_stage_required_skill") or 0) for item in order_items]
        stage_required_skill_min = min(stage_skill_levels) if stage_skill_levels else 0
        stage_required_skill_max = max(stage_skill_levels) if stage_skill_levels else 0

        detail = dict(row)
        detail.pop("skill_picking", None)
        detail.pop("skill_staging", None)
        detail.pop("skill_shipping", None)
        detail["worker_stage_skill"] = worker_stage_skill
        detail["stage_required_skill_min"] = stage_required_skill_min
        detail["stage_required_skill_max"] = stage_required_skill_max
        detail["order_items"] = order_items
        return detail

    async def _lock_worker_work_order(self, work_order_id: int, user_id: int):
        result = await self.session.execute(
            text(
                """
                SELECT wo.id, wo.order_id, wo.stage_id, wo.worker_id, wo.status, os.stage_type
                FROM work_orders wo
                JOIN order_stages os ON os.id = wo.stage_id
                WHERE wo.id = :work_order_id
                FOR UPDATE
                """
            ),
            {"work_order_id": work_order_id},
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Work order not found")
        if row["worker_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only assigned worker can operate this work order")
        return row

    async def start_work_order(self, work_order_id: int, user_id: int):
        try:
            row = await self._lock_worker_work_order(work_order_id=work_order_id, user_id=user_id)
            if row["status"] != "pending":
                raise HTTPException(status_code=400, detail="Only pending work order can be started")

            previous_stage_type = {
                "staging": "picking",
                "shipping": "staging",
            }.get(row["stage_type"])
            if previous_stage_type:
                previous_stage_result = await self.session.execute(
                    text(
                        """
                        SELECT status
                        FROM order_stages
                        WHERE order_id = :order_id
                          AND stage_type = :stage_type
                        LIMIT 1
                        """
                    ),
                    {
                        "order_id": row["order_id"],
                        "stage_type": previous_stage_type,
                    },
                )
                previous_stage = previous_stage_result.mappings().first()
                if not previous_stage or previous_stage["status"] != "completed":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Previous stage {previous_stage_type} must be completed before starting this work order",
                    )

            await self.session.execute(
                text(
                    """
                    UPDATE work_orders
                    SET
                        status = 'in_progress',
                        started_at = COALESCE(started_at, (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)),
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :work_order_id
                    """
                ),
                {"work_order_id": work_order_id},
            )

            await self.session.execute(
                text(
                    """
                    UPDATE order_stages
                    SET status = 'in_progress', updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :stage_id
                      AND status = 'not_started'
                    """
                ),
                {"stage_id": row["stage_id"]},
            )

            await self.session.commit()
        except HTTPException:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def complete_work_order(
        self,
        work_order_id: int,
        user_id: int,
        note_type: Optional[str] = None,
        note_content: Optional[str] = None,
    ):
        try:
            row = await self._lock_worker_work_order(work_order_id=work_order_id, user_id=user_id)
            if row["status"] != "in_progress":
                raise HTTPException(status_code=400, detail="Only in-progress work order can be completed")

            await self.session.execute(
                text(
                    """
                    UPDATE work_orders
                    SET
                        status = 'completed',
                        completed_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0),
                        updated_at = (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                    WHERE id = :work_order_id
                    """
                ),
                {"work_order_id": work_order_id},
            )

            if note_type and note_content:
                await self.session.execute(
                    text(
                        """
                        INSERT INTO work_order_notes (
                            work_order_id,
                            note_type,
                            content,
                            created_by,
                            created_at
                        ) VALUES (
                            :work_order_id,
                            :note_type,
                            :content,
                            :created_by,
                            (NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)
                        )
                        """
                    ),
                    {
                        "work_order_id": work_order_id,
                        "note_type": note_type,
                        "content": note_content,
                        "created_by": user_id,
                    },
                )

                await notify_work_order_note_exception(
                    self.session,
                    work_order_id=work_order_id,
                    note_type=note_type,
                    note_content=note_content,
                )

            await self._try_auto_complete_stage(stage_id=row["stage_id"], operated_by=user_id)
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

