from typing import Optional

from sqlalchemy import text


class WorkOrderServiceMixin:
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
