from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text

from modules.dispatcher.schemas import (
    DispatcherCreateWorkOrderRequest,
    DispatcherSkillProductBreakdownResponse,
    DispatcherWorkOrderPrecheckResponse,
    DispatcherWorkOrderRiskResponse,
)


class DispatcherWorkOrderServiceMixin:
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
                    COALESCE(wo.pending_count, 0)::INTEGER AS pending_count,
                    COALESCE(wo.in_progress_count, 0)::INTEGER AS in_progress_count,
                    COALESCE(wo.active_work_order_count, 0)::INTEGER AS active_work_order_count,
                    CAST(:active_work_order_limit AS INTEGER) AS active_work_order_limit
                FROM users u
                LEFT JOIN (
                    SELECT
                        worker_id,
                        COUNT(*) FILTER (WHERE status = 'pending')::INTEGER AS pending_count,
                        COUNT(*) FILTER (WHERE status = 'in_progress')::INTEGER AS in_progress_count,
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
                SELECT
                    COALESCE(COUNT(*) FILTER (WHERE status = 'pending'), 0)::INTEGER AS pending_count,
                    COALESCE(COUNT(*) FILTER (WHERE status = 'in_progress'), 0)::INTEGER AS in_progress_count,
                    COALESCE(COUNT(*), 0)::INTEGER AS active_work_order_count
                FROM work_orders
                WHERE worker_id = :worker_id
                  AND status IN ('pending', 'in_progress')
                """
            ),
            {"worker_id": worker_id},
        )
        active_counts = active_count_result.mappings().first() or {}
        pending_count = int(active_counts.get("pending_count", 0))
        in_progress_count = int(active_counts.get("in_progress_count", 0))
        active_work_order_count = int(active_counts.get("active_work_order_count", 0))

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
            "pending_count": pending_count,
            "in_progress_count": in_progress_count,
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
                        :source,
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
                    "source": payload.source,
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
