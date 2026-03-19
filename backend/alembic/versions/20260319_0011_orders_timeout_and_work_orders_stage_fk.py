"""add order timeout audit fields and link work_orders to order_stages

Revision ID: 20260319_0011
Revises: 20260319_0010
Create Date: 2026-03-19 23:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260319_0011"
down_revision = "20260319_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("timeout_revert_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "orders",
        sa.Column("last_reverted_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "work_orders",
        sa.Column("stage_id", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE work_orders wo
        SET stage_id = os.id
        FROM order_stages os
        WHERE os.order_id = wo.order_id
          AND os.stage_type = wo.stage_type
          AND wo.stage_id IS NULL;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM work_orders
                WHERE stage_id IS NULL
            ) THEN
                RAISE EXCEPTION 'Migration blocked: found work_orders that cannot map to order_stages by (order_id, stage_type)';
            END IF;
        END
        $$;
        """
    )

    op.create_foreign_key(
        "fk_work_orders_stage_id_order_stages",
        "work_orders",
        "order_stages",
        ["stage_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "idx_work_orders_stage_id",
        "work_orders",
        ["stage_id"],
        unique=False,
    )

    op.alter_column("work_orders", "stage_id", nullable=False)

    op.drop_constraint("ck_work_orders_stage_type_valid", "work_orders", type_="check")
    op.drop_column("work_orders", "stage_type")


def downgrade() -> None:
    op.add_column(
        "work_orders",
        sa.Column("stage_type", sa.String(length=16), nullable=True),
    )

    op.execute(
        """
        UPDATE work_orders wo
        SET stage_type = os.stage_type
        FROM order_stages os
        WHERE os.id = wo.stage_id
          AND wo.stage_type IS NULL;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM work_orders
                WHERE stage_type IS NULL
            ) THEN
                RAISE EXCEPTION 'Downgrade blocked: found work_orders without resolvable stage_type from stage_id';
            END IF;
        END
        $$;
        """
    )

    op.alter_column("work_orders", "stage_type", nullable=False)

    op.create_check_constraint(
        "ck_work_orders_stage_type_valid",
        "work_orders",
        "stage_type IN ('picking', 'staging', 'shipping')",
    )

    op.drop_index("idx_work_orders_stage_id", table_name="work_orders")
    op.drop_constraint("fk_work_orders_stage_id_order_stages", "work_orders", type_="foreignkey")
    op.drop_column("work_orders", "stage_id")

    op.drop_column("orders", "last_reverted_at")
    op.drop_column("orders", "timeout_revert_count")
