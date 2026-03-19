"""enforce order cancel rules and dispatcher consistency

Revision ID: 20260319_0006
Revises: 20260318_0005
Create Date: 2026-03-19 10:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260319_0006"
down_revision = "20260318_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pre-check legacy data before adding hard constraints.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM work_orders wo
                JOIN orders o ON o.id = wo.order_id
                WHERE wo.dispatcher_id <> o.dispatcher_id
            ) THEN
                RAISE EXCEPTION 'Migration blocked: found work_orders with dispatcher mismatch against orders';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM orders o
                WHERE o.status = 'cancelled'
                  AND EXISTS (
                      SELECT 1
                      FROM work_orders wo
                      WHERE wo.order_id = o.id
                        AND wo.status IN ('pending', 'in_progress')
                  )
            ) THEN
                RAISE EXCEPTION 'Migration blocked: found cancelled orders with active work_orders';
            END IF;
        END
        $$;
        """
    )

    op.create_unique_constraint(
        "uq_orders_id_dispatcher_id",
        "orders",
        ["id", "dispatcher_id"],
    )

    op.create_foreign_key(
        "fk_work_orders_order_dispatcher_orders",
        "work_orders",
        "orders",
        ["order_id", "dispatcher_id"],
        ["id", "dispatcher_id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "idx_work_orders_order_status",
        "work_orders",
        ["order_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_orders_dispatcher_status_accepted_at",
        "orders",
        ["dispatcher_id", "status", "accepted_at"],
        unique=False,
    )
    op.create_index(
        "idx_orders_in_progress_accepted_at",
        "orders",
        ["accepted_at"],
        unique=False,
        postgresql_where=sa.text("status = 'in_progress'"),
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_orders_cancel_requires_no_active_work_orders()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.status = 'cancelled' THEN
                IF EXISTS (
                    SELECT 1
                    FROM work_orders wo
                    WHERE wo.order_id = NEW.id
                      AND wo.status IN ('pending', 'in_progress')
                ) THEN
                    RAISE EXCEPTION 'Cannot cancel order % while active work_orders exist', NEW.id
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE CONSTRAINT TRIGGER ck_orders_cancel_requires_no_active_work_orders
        AFTER INSERT OR UPDATE OF status ON orders
        DEFERRABLE INITIALLY IMMEDIATE
        FOR EACH ROW
        EXECUTE FUNCTION fn_orders_cancel_requires_no_active_work_orders();
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_work_orders_block_active_when_order_cancelled()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_order_status TEXT;
        BEGIN
            IF NEW.status IN ('pending', 'in_progress') THEN
                SELECT o.status INTO v_order_status
                FROM orders o
                WHERE o.id = NEW.order_id;

                IF v_order_status = 'cancelled' THEN
                    RAISE EXCEPTION 'Cannot keep active work_order under cancelled order %', NEW.order_id
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE CONSTRAINT TRIGGER ck_work_orders_block_active_when_order_cancelled
        AFTER INSERT OR UPDATE OF order_id, status ON work_orders
        DEFERRABLE INITIALLY IMMEDIATE
        FOR EACH ROW
        EXECUTE FUNCTION fn_work_orders_block_active_when_order_cancelled();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS ck_work_orders_block_active_when_order_cancelled ON work_orders;")
    op.execute("DROP FUNCTION IF EXISTS fn_work_orders_block_active_when_order_cancelled();")

    op.execute("DROP TRIGGER IF EXISTS ck_orders_cancel_requires_no_active_work_orders ON orders;")
    op.execute("DROP FUNCTION IF EXISTS fn_orders_cancel_requires_no_active_work_orders();")

    op.drop_index("idx_orders_in_progress_accepted_at", table_name="orders")
    op.drop_index("idx_orders_dispatcher_status_accepted_at", table_name="orders")
    op.drop_index("idx_work_orders_order_status", table_name="work_orders")

    op.drop_constraint("fk_work_orders_order_dispatcher_orders", "work_orders", type_="foreignkey")
    op.drop_constraint("uq_orders_id_dispatcher_id", "orders", type_="unique")
