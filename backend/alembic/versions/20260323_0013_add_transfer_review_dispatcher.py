"""add transfer review dispatcher field

Revision ID: 20260323_0013
Revises: 20260322_0012
Create Date: 2026-03-23 13:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_0013"
down_revision = "20260322_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transfer_orders", sa.Column("review_dispatcher_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_transfer_orders_review_dispatcher_id_users",
        "transfer_orders",
        "users",
        ["review_dispatcher_id"],
        ["id"],
    )

    op.execute(
        sa.text(
            """
            UPDATE transfer_orders
            SET review_dispatcher_id = approved_by
            WHERE review_dispatcher_id IS NULL
              AND approved_by IS NOT NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE transfer_orders t
            SET review_dispatcher_id = u.id
            FROM users u
            WHERE t.review_dispatcher_id IS NULL
              AND u.role = 'dispatcher'
              AND u.is_active = true
              AND u.warehouse_id = t.from_warehouse_id
            """
        )
    )

def downgrade() -> None:
    op.drop_constraint("fk_transfer_orders_review_dispatcher_id_users", "transfer_orders", type_="foreignkey")
    op.drop_column("transfer_orders", "review_dispatcher_id")
