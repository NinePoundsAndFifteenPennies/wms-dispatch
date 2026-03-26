from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


SYSTEM_TZ_SQL = "(NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)"
logger = logging.getLogger(__name__)


async def _run_rule_safely(session: AsyncSession, rule_name: str, handler) -> int:
    try:
        async with session.begin_nested():
            return int(await handler(session) or 0)
    except Exception:
        logger.exception("Notification rule failed: %s", rule_name)
        return 0


async def run_system_notification_rules(session: AsyncSession) -> dict:
    """Run timeout-related sweeps and alert generation rules.

    This function is designed to be called by read-heavy APIs so the system can
    self-heal and raise notifications even without a dedicated scheduler.
    """

    stats = {
        "pending_acceptance_timeout_notified": 0,
        "in_progress_timeout_reverted": 0,
        "inbound_timeout_notified": 0,
        "work_order_deadline_notified": 0,
    }

    stats["pending_acceptance_timeout_notified"] = await _run_rule_safely(
        session,
        "pending_acceptance_timeout",
        _notify_pending_acceptance_timeout,
    )
    stats["in_progress_timeout_reverted"] = await _run_rule_safely(
        session,
        "in_progress_without_work_orders",
        _revert_in_progress_without_work_orders,
    )
    stats["inbound_timeout_notified"] = await _run_rule_safely(
        session,
        "inbound_timeout",
        _notify_inbound_timeout,
    )
    stats["work_order_deadline_notified"] = await _run_rule_safely(
        session,
        "work_order_deadline_overdue",
        _notify_work_order_deadline_overdue,
    )

    try:
        await session.commit()
    except Exception:
        logger.exception("Commit failed after running notification rules")
        await session.rollback()
    return stats


async def _notify_pending_acceptance_timeout(session: AsyncSession) -> int:
    result = await session.execute(
        text(
            f"""
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
                'order_pending_acceptance_timeout',
                '订单待接单超时',
                ('订单 ' || o.order_no || ' 超过24小时无人接单，请尽快处理'),
                o.id,
                'order',
                false,
                {SYSTEM_TZ_SQL}
            FROM orders o
            JOIN users u ON u.role = 'admin' AND u.is_active = true
            WHERE o.status = 'pending_acceptance'
              AND o.dispatcher_id IS NULL
              AND o.created_at <= ({SYSTEM_TZ_SQL} - INTERVAL '24 hours')
              AND NOT EXISTS (
                  SELECT 1
                  FROM notifications n
                  WHERE n.user_id = u.id
                    AND n.type = 'order_pending_acceptance_timeout'
                    AND n.related_type = 'order'
                    AND n.related_id = o.id
              )
                        ON CONFLICT DO NOTHING
            """
        )
    )
    return int(result.rowcount or 0)


async def _revert_in_progress_without_work_orders(session: AsyncSession) -> int:
    candidate_result = await session.execute(
        text(
            f"""
            SELECT o.id, o.order_no, o.warehouse_id, o.dispatcher_id
            FROM orders o
            WHERE o.status = 'in_progress'
              AND o.accepted_at IS NOT NULL
              AND o.accepted_at <= ({SYSTEM_TZ_SQL} - INTERVAL '24 hours')
              AND NOT EXISTS (
                  SELECT 1
                  FROM work_orders wo
                  WHERE wo.order_id = o.id
              )
            FOR UPDATE SKIP LOCKED
            """
        )
    )
    candidates = [dict(row) for row in candidate_result.mappings().all()]
    if not candidates:
        return 0

    reverted_count = 0
    for order in candidates:
        order_id = order["id"]
        warehouse_id = order["warehouse_id"]
        dispatcher_id = order.get("dispatcher_id")

        req_result = await session.execute(
            text(
                """
                SELECT oi.product_id, COALESCE(SUM(oi.qty), 0)::INTEGER AS required_qty
                FROM order_items oi
                WHERE oi.order_id = :order_id
                GROUP BY oi.product_id
                """
            ),
            {"order_id": order_id},
        )
        required_items = [dict(row) for row in req_result.mappings().all()]

        for item in required_items:
            inv_result = await session.execute(
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
                    "warehouse_id": warehouse_id,
                    "product_id": item["product_id"],
                },
            )
            inventory = inv_result.mappings().first()
            if not inventory:
                continue

            required_qty = int(item["required_qty"] or 0)
            before_reserved = int(inventory["qty_reserved"] or 0)
            release_qty = min(required_qty, before_reserved)
            if release_qty <= 0:
                continue

            update_inventory_result = await session.execute(
                text(
                    f"""
                    UPDATE inventory
                    SET
                        qty_reserved = qty_reserved - :release_qty,
                        updated_at = {SYSTEM_TZ_SQL}
                    WHERE id = :inventory_id
                    RETURNING qty_on_hand, qty_reserved, qty_locked
                    """
                ),
                {
                    "inventory_id": inventory["id"],
                    "release_qty": release_qty,
                },
            )
            updated_inventory = update_inventory_result.mappings().first()
            if not updated_inventory:
                continue

            await session.execute(
                text(
                    f"""
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
                        operated_by,
                        created_at
                    ) VALUES (
                        :inventory_id,
                        :warehouse_id,
                        :product_id,
                        'reserve_release_timeout',
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
                        :operated_by,
                        {SYSTEM_TZ_SQL}
                    )
                    """
                ),
                {
                    "inventory_id": inventory["id"],
                    "warehouse_id": warehouse_id,
                    "product_id": item["product_id"],
                    "delta_reserved": -release_qty,
                    "before_on_hand": inventory["qty_on_hand"],
                    "before_reserved": inventory["qty_reserved"],
                    "before_locked": inventory["qty_locked"],
                    "after_on_hand": updated_inventory["qty_on_hand"],
                    "after_reserved": updated_inventory["qty_reserved"],
                    "after_locked": updated_inventory["qty_locked"],
                    "related_id": order_id,
                    "operated_by": dispatcher_id,
                },
            )

        update_order_result = await session.execute(
            text(
                f"""
                UPDATE orders
                SET
                    status = 'pending_acceptance',
                    dispatcher_id = NULL,
                    accepted_at = NULL,
                    timeout_revert_count = timeout_revert_count + 1,
                    last_reverted_at = {SYSTEM_TZ_SQL},
                    updated_at = {SYSTEM_TZ_SQL}
                WHERE id = :order_id
                  AND status = 'in_progress'
                RETURNING id
                """
            ),
            {"order_id": order_id},
        )
        updated = update_order_result.mappings().first()
        if not updated:
            continue

        reverted_count += 1

        await session.execute(
            text(
                f"""
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
                    'order_timeout_reverted',
                    '订单已因未派工超时回退',
                    ('订单 ' || :order_no || ' 接单后24小时未派工，系统已自动回退为待接单'),
                    :order_id,
                    'order',
                    false,
                    {SYSTEM_TZ_SQL}
                FROM users u
                WHERE u.role = 'admin'
                  AND u.is_active = true
                  AND NOT EXISTS (
                      SELECT 1
                      FROM notifications n
                      WHERE n.user_id = u.id
                        AND n.type = 'order_timeout_reverted'
                        AND n.related_type = 'order'
                        AND n.related_id = :order_id
                  )
                                ON CONFLICT DO NOTHING
                """
            ),
            {
                "order_id": order_id,
                "order_no": order["order_no"],
            },
        )

        if dispatcher_id:
            await session.execute(
                text(
                    f"""
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
                        'order_timeout_reverted',
                        '订单已因未派工超时回退',
                        ('订单 ' || :order_no || ' 接单后24小时未派工，系统已自动回退为待接单'),
                        :order_id,
                        'order',
                        false,
                        {SYSTEM_TZ_SQL}
                    FROM users u
                    WHERE u.id = :dispatcher_id
                      AND u.is_active = true
                      AND NOT EXISTS (
                          SELECT 1
                          FROM notifications n
                          WHERE n.user_id = u.id
                            AND n.type = 'order_timeout_reverted'
                            AND n.related_type = 'order'
                            AND n.related_id = :order_id
                      )
                                        ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "dispatcher_id": dispatcher_id,
                    "order_id": order_id,
                    "order_no": order["order_no"],
                },
            )

    return reverted_count


async def _notify_inbound_timeout(session: AsyncSession) -> int:
    result = await session.execute(
        text(
            f"""
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
                t.requested_by,
                'inbound_timeout_pending_confirm',
                '调拨入库确认超时',
                ('调拨单 #' || t.id::TEXT || ' 对应入库记录超过48小时未确认'),
                ir.id,
                'inbound_record',
                false,
                {SYSTEM_TZ_SQL}
            FROM inbound_records ir
            JOIN transfer_orders t ON t.id = ir.transfer_order_id
            JOIN users u ON u.id = t.requested_by
            WHERE ir.status = 'pending'
              AND ir.created_at <= ({SYSTEM_TZ_SQL} - INTERVAL '48 hours')
              AND u.role = 'dispatcher'
              AND u.is_active = true
              AND NOT EXISTS (
                  SELECT 1
                  FROM notifications n
                  WHERE n.user_id = t.requested_by
                    AND n.type = 'inbound_timeout_pending_confirm'
                    AND n.related_type = 'inbound_record'
                    AND n.related_id = ir.id
              )
                        ON CONFLICT DO NOTHING
            """
        )
    )
    return int(result.rowcount or 0)


async def _notify_work_order_deadline_overdue(session: AsyncSession) -> int:
    result = await session.execute(
        text(
            f"""
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
                wo.dispatcher_id,
                'work_order_deadline_overdue',
                '工单超时告警',
                ('工单 #' || wo.id::TEXT || ' 已超过截止时间，请尽快处理'),
                wo.id,
                'work_order',
                false,
                {SYSTEM_TZ_SQL}
            FROM work_orders wo
            JOIN users u ON u.id = wo.dispatcher_id
            WHERE wo.status IN ('pending', 'in_progress')
              AND wo.deadline IS NOT NULL
              AND wo.deadline <= {SYSTEM_TZ_SQL}
              AND u.is_active = true
              AND NOT EXISTS (
                  SELECT 1
                  FROM notifications n
                  WHERE n.user_id = wo.dispatcher_id
                    AND n.type = 'work_order_deadline_overdue'
                    AND n.related_type = 'work_order'
                    AND n.related_id = wo.id
              )
                        ON CONFLICT DO NOTHING
            """
        )
    )
    return int(result.rowcount or 0)


async def notify_work_order_note_exception(
    session: AsyncSession,
    *,
    work_order_id: int,
    note_type: Optional[str],
    note_content: Optional[str],
) -> int:
    if note_type not in {"damaged", "qty_mismatch", "other"}:
        return 0

    context_result = await session.execute(
        text(
            """
            SELECT
                wo.id,
                wo.dispatcher_id,
                o.order_no
            FROM work_orders wo
            JOIN orders o ON o.id = wo.order_id
            WHERE wo.id = :work_order_id
            LIMIT 1
            """
        ),
        {"work_order_id": work_order_id},
    )
    row = context_result.mappings().first()
    if not row:
        return 0

    title_map = {
        "damaged": "工单异常：破损",
        "qty_mismatch": "工单异常：数量不符",
        "other": "工单异常：其他",
    }
    severity_type = "work_order_exception_severe" if note_type in {"damaged", "qty_mismatch"} else "work_order_exception_other"
    body = f"订单 {row['order_no']} 的工单 #{work_order_id} 出现异常备注（{note_type}）：{note_content or ''}"

    inserted = 0

    dispatcher_result = await session.execute(
        text(
            f"""
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
                                CAST(:type AS VARCHAR(32)),
                                CAST(:title AS VARCHAR(256)),
                                CAST(:body AS TEXT),
                                CAST(:related_id AS INTEGER),
                'work_order',
                false,
                {SYSTEM_TZ_SQL}
            FROM users u
                        WHERE u.id = CAST(:dispatcher_id AS INTEGER)
              AND u.is_active = true
              AND NOT EXISTS (
                  SELECT 1
                  FROM notifications n
                  WHERE n.user_id = u.id
                                        AND n.type = CAST(:type AS VARCHAR(32))
                    AND n.related_type = 'work_order'
                                        AND n.related_id = CAST(:related_id AS INTEGER)
              )
                        ON CONFLICT DO NOTHING
            """
        ),
        {
            "dispatcher_id": row["dispatcher_id"],
            "type": severity_type,
            "title": title_map[note_type],
            "body": body,
            "related_id": work_order_id,
        },
    )
    inserted += int(dispatcher_result.rowcount or 0)

    if note_type in {"damaged", "qty_mismatch"}:
        admin_result = await session.execute(
            text(
                f"""
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
                    CAST(:type AS VARCHAR(32)),
                    CAST(:title AS VARCHAR(256)),
                    CAST(:body AS TEXT),
                    CAST(:related_id AS INTEGER),
                    'work_order',
                    false,
                    {SYSTEM_TZ_SQL}
                FROM users u
                WHERE u.role = 'admin'
                  AND u.is_active = true
                  AND NOT EXISTS (
                      SELECT 1
                      FROM notifications n
                      WHERE n.user_id = u.id
                                                AND n.type = CAST(:type AS VARCHAR(32))
                        AND n.related_type = 'work_order'
                                                AND n.related_id = CAST(:related_id AS INTEGER)
                  )
                                ON CONFLICT DO NOTHING
                """
            ),
            {
                "type": severity_type,
                "title": title_map[note_type],
                "body": body,
                "related_id": work_order_id,
            },
        )
        inserted += int(admin_result.rowcount or 0)

    return inserted