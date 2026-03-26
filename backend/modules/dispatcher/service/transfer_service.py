from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text

from modules.dispatcher.schemas import DispatcherTransferCreateRequest
from modules.shared.notification_rules import run_system_notification_rules


class DispatcherTransferServiceMixin:
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
        await run_system_notification_rules(self.session)

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
        await run_system_notification_rules(self.session)

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
