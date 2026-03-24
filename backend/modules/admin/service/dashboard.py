from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text

from .base import SYSTEM_TIMEZONE


class DashboardServiceMixin:
    async def get_dashboard_overview(self):
        today_start = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None,
        )
        tomorrow_start = today_start + timedelta(days=1)
        now_time = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)
        order_pending_before = now_time - timedelta(hours=3)
        accepted_no_dispatch_before = now_time - timedelta(hours=2)
        cancelled_recent_after = now_time - timedelta(hours=24)

        kpi_result = await self.session.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM orders WHERE status = 'pending_acceptance')::INTEGER AS pending_acceptance_orders,
                    (
                        SELECT COUNT(*)
                        FROM inventory i
                        JOIN products p ON p.id = i.product_id
                        JOIN warehouses w ON w.id = i.warehouse_id
                        WHERE p.is_active = TRUE
                          AND w.is_active = TRUE
                          AND i.qty_available < i.qty_threshold
                    )::INTEGER AS low_stock_alerts,
                    (
                        SELECT COUNT(*)
                        FROM orders o
                        WHERE o.status = 'cancelled'
                          AND o.cancelled_at >= :today_start
                          AND o.cancelled_at < :tomorrow_start
                    )::INTEGER AS cancelled_orders_today,
                    (
                        SELECT COUNT(*)
                        FROM orders o
                        WHERE o.status = 'in_progress'
                          AND o.accepted_at IS NOT NULL
                          AND o.accepted_at <= :accepted_no_dispatch_before
                          AND NOT EXISTS (
                              SELECT 1
                              FROM work_orders wo
                              WHERE wo.order_id = o.id
                          )
                    )::INTEGER AS accepted_no_dispatch_orders
                """
            ),
            {
                "today_start": today_start,
                "tomorrow_start": tomorrow_start,
                "accepted_no_dispatch_before": accepted_no_dispatch_before,
            },
        )
        kpi_row = kpi_result.mappings().first() or {}

        orders_distribution_result = await self.session.execute(
            text(
                """
                SELECT
                    o.status AS key,
                    CASE o.status
                        WHEN 'pending_acceptance' THEN '待接单'
                        WHEN 'in_progress' THEN '进行中'
                        WHEN 'completed' THEN '已完成'
                        WHEN 'cancelled' THEN '已取消'
                        ELSE o.status
                    END AS label,
                    COUNT(*)::INTEGER AS value
                FROM orders o
                GROUP BY o.status
                """
            )
        )
        distribution_map = {
            "pending_acceptance": {"key": "pending_acceptance", "label": "待接单", "value": 0},
            "in_progress": {"key": "in_progress", "label": "进行中", "value": 0},
            "completed": {"key": "completed", "label": "已完成", "value": 0},
            "cancelled": {"key": "cancelled", "label": "已取消", "value": 0},
        }
        for row in orders_distribution_result.mappings().all():
            key = row.get("key")
            if key in distribution_map:
                distribution_map[key]["value"] = int(row.get("value") or 0)

        warehouse_loads_result = await self.session.execute(
            text(
                """
                SELECT
                    w.id AS warehouse_id,
                    w.name AS warehouse_name,
                    COALESCE(SUM(i.qty_on_hand), 0)::INTEGER AS qty_on_hand,
                    COALESCE(w.capacity, 0)::INTEGER AS capacity,
                    CASE
                        WHEN COALESCE(w.capacity, 0) <= 0 THEN 0
                        ELSE LEAST(100, ROUND((COALESCE(SUM(i.qty_on_hand), 0)::NUMERIC / w.capacity::NUMERIC) * 100))::INTEGER
                    END AS load_percent
                FROM warehouses w
                LEFT JOIN inventory i ON i.warehouse_id = w.id
                WHERE w.is_active = TRUE
                GROUP BY w.id, w.name, w.capacity
                ORDER BY load_percent DESC, w.id ASC
                """
            )
        )

        warehouse_order_performance_result = await self.session.execute(
            text(
                """
                SELECT
                    w.id AS warehouse_id,
                    w.name AS warehouse_name,
                    COUNT(o.id)::INTEGER AS total_orders,
                    COUNT(*) FILTER (WHERE o.status = 'completed')::INTEGER AS completed_orders,
                    CASE
                        WHEN COUNT(o.id) = 0 THEN 0
                        ELSE ROUND((COUNT(*) FILTER (WHERE o.status = 'completed')::NUMERIC / COUNT(o.id)::NUMERIC) * 100)::INTEGER
                    END AS completion_rate
                FROM warehouses w
                LEFT JOIN orders o ON o.warehouse_id = w.id
                WHERE w.is_active = TRUE
                GROUP BY w.id, w.name
                ORDER BY completion_rate DESC, completed_orders DESC, w.id ASC
                """
            )
        )

        product_popularity_result = await self.session.execute(
            text(
                """
                SELECT
                    p.id AS product_id,
                    p.sku,
                    p.name AS product_name,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_qty,
                    COUNT(DISTINCT oi.order_id)::INTEGER AS order_count
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                JOIN products p ON p.id = oi.product_id
                WHERE o.status = 'completed'
                GROUP BY p.id, p.sku, p.name
                HAVING COALESCE(SUM(oi.qty), 0) > 0
                ORDER BY total_qty DESC, order_count DESC, p.id ASC
                LIMIT 10
                """
            )
        )

        low_stock_result = await self.session.execute(
            text(
                """
                SELECT
                    i.id AS inventory_id,
                    i.warehouse_id,
                    w.name AS warehouse_name,
                    i.product_id,
                    p.sku,
                    p.name AS product_name,
                    i.qty_available,
                    i.qty_threshold
                FROM inventory i
                JOIN products p ON p.id = i.product_id
                JOIN warehouses w ON w.id = i.warehouse_id
                WHERE p.is_active = TRUE
                  AND w.is_active = TRUE
                  AND i.qty_available < i.qty_threshold
                ORDER BY (i.qty_threshold - i.qty_available) DESC, i.qty_available ASC, i.id ASC
                LIMIT 8
                """
            )
        )

        alerts_result = await self.session.execute(
            text(
                """
                (
                    SELECT
                        'order_pending'::TEXT AS alert_type,
                        ('订单 ' || o.order_no || ' 超过 3 小时未接单')::TEXT AS message,
                        o.id AS order_id,
                        o.order_no,
                        NULL::INTEGER AS inventory_id,
                        o.warehouse_id AS warehouse_id,
                        o.created_at AS sort_time
                    FROM orders o
                    WHERE o.status = 'pending_acceptance'
                      AND o.created_at <= :order_pending_before
                    ORDER BY o.created_at ASC
                    LIMIT 8
                )
                UNION ALL
                (
                    SELECT
                        'accepted_no_dispatch'::TEXT AS alert_type,
                        ('订单 ' || o.order_no || ' 已接单超过 2 小时但未创建工单')::TEXT AS message,
                        o.id AS order_id,
                        o.order_no,
                        NULL::INTEGER AS inventory_id,
                        o.warehouse_id AS warehouse_id,
                        o.accepted_at AS sort_time
                    FROM orders o
                    WHERE o.status = 'in_progress'
                      AND o.accepted_at IS NOT NULL
                      AND o.accepted_at <= :accepted_no_dispatch_before
                      AND NOT EXISTS (
                          SELECT 1
                          FROM work_orders wo
                          WHERE wo.order_id = o.id
                      )
                    ORDER BY o.accepted_at ASC
                    LIMIT 8
                )
                UNION ALL
                (
                    SELECT
                        'order_cancelled'::TEXT AS alert_type,
                        ('订单 ' || o.order_no || ' 已取消，请关注取消原因')::TEXT AS message,
                        o.id AS order_id,
                        o.order_no,
                        NULL::INTEGER AS inventory_id,
                        o.warehouse_id AS warehouse_id,
                        o.cancelled_at AS sort_time
                    FROM orders o
                    WHERE o.status = 'cancelled'
                      AND o.cancelled_at >= :cancelled_recent_after
                    ORDER BY o.cancelled_at DESC
                    LIMIT 8
                )
                UNION ALL
                (
                    SELECT
                        'low_stock'::TEXT AS alert_type,
                        ('SKU ' || p.sku || ' 在 ' || w.name || ' 低于阈值')::TEXT AS message,
                        NULL::INTEGER AS order_id,
                        NULL::TEXT AS order_no,
                        i.id AS inventory_id,
                        i.warehouse_id AS warehouse_id,
                        i.updated_at AS sort_time
                    FROM inventory i
                    JOIN products p ON p.id = i.product_id
                    JOIN warehouses w ON w.id = i.warehouse_id
                    WHERE p.is_active = TRUE
                      AND w.is_active = TRUE
                      AND i.qty_available < i.qty_threshold
                    ORDER BY (i.qty_threshold - i.qty_available) DESC, i.updated_at DESC
                    LIMIT 8
                )
                ORDER BY sort_time DESC NULLS LAST
                LIMIT 30
                """
            ),
            {
                "order_pending_before": order_pending_before,
                "accepted_no_dispatch_before": accepted_no_dispatch_before,
                "cancelled_recent_after": cancelled_recent_after,
            },
        )

        return {
            "kpis": {
                "pending_acceptance_orders": int(kpi_row.get("pending_acceptance_orders") or 0),
                "low_stock_alerts": int(kpi_row.get("low_stock_alerts") or 0),
                "cancelled_orders_today": int(kpi_row.get("cancelled_orders_today") or 0),
                "accepted_no_dispatch_orders": int(kpi_row.get("accepted_no_dispatch_orders") or 0),
            },
            "orders_status_distribution": [
                distribution_map["pending_acceptance"],
                distribution_map["in_progress"],
                distribution_map["completed"],
                distribution_map["cancelled"],
            ],
            "warehouse_loads": [dict(row) for row in warehouse_loads_result.mappings().all()],
            "warehouse_order_performance": [dict(row) for row in warehouse_order_performance_result.mappings().all()],
            "product_popularity": [dict(row) for row in product_popularity_result.mappings().all()],
            "low_stock_top": [dict(row) for row in low_stock_result.mappings().all()],
            "alerts": [
                {
                    "alert_type": row.get("alert_type"),
                    "message": row.get("message"),
                    "order_id": row.get("order_id"),
                    "order_no": row.get("order_no"),
                    "inventory_id": row.get("inventory_id"),
                    "warehouse_id": row.get("warehouse_id"),
                }
                for row in alerts_result.mappings().all()
            ],
        }

    async def get_warehouse_dispatcher_performance(self, warehouse_id: int):
        warehouse_result = await self.session.execute(
            text(
                """
                SELECT id, name
                FROM warehouses
                WHERE id = :warehouse_id
                """
            ),
            {"warehouse_id": warehouse_id},
        )
        warehouse = warehouse_result.mappings().first()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        summary_result = await self.session.execute(
            text(
                """
                SELECT
                    COUNT(o.id)::INTEGER AS total_orders,
                    COUNT(*) FILTER (WHERE o.status = 'completed')::INTEGER AS completed_orders
                FROM orders o
                WHERE o.warehouse_id = :warehouse_id
                """
            ),
            {"warehouse_id": warehouse_id},
        )
        summary = summary_result.mappings().first() or {}
        total_orders = int(summary.get("total_orders") or 0)
        completed_orders = int(summary.get("completed_orders") or 0)
        completion_rate = 0
        if total_orders > 0:
            completion_rate = int(round((completed_orders / total_orders) * 100))

        dispatchers_result = await self.session.execute(
            text(
                """
                SELECT
                    u.id AS dispatcher_id,
                    u.username AS dispatcher_name,
                    COUNT(o.id)::INTEGER AS total_orders,
                    COUNT(*) FILTER (WHERE o.status = 'completed')::INTEGER AS completed_orders,
                    CASE
                        WHEN COUNT(o.id) = 0 THEN 0
                        ELSE ROUND((COUNT(*) FILTER (WHERE o.status = 'completed')::NUMERIC / COUNT(o.id)::NUMERIC) * 100)::INTEGER
                    END AS completion_rate
                FROM users u
                JOIN orders o ON o.dispatcher_id = u.id
                WHERE o.warehouse_id = :warehouse_id
                  AND u.role = 'dispatcher'
                GROUP BY u.id, u.username
                ORDER BY completion_rate DESC, completed_orders DESC, u.id ASC
                """
            ),
            {"warehouse_id": warehouse_id},
        )

        return {
            "warehouse_id": warehouse["id"],
            "warehouse_name": warehouse["name"],
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "completion_rate": completion_rate,
            "dispatchers": [dict(row) for row in dispatchers_result.mappings().all()],
        }
