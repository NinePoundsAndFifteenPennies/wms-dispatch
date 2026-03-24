from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text


class DispatcherInventoryServiceMixin:
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
