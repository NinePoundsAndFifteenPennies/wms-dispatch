"""unify remaining business timestamps to cn time and drop work_orders.assigned_at

Revision ID: 20260322_0012
Revises: 20260319_0011
Create Date: 2026-03-22 10:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260322_0012"
down_revision = "20260319_0011"
branch_labels = None
depends_on = None


CN_NOW = "(NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)"

SHIFT_COLUMNS: dict[str, list[str]] = {
    "orders": ["last_reverted_at"],
    "order_stages": ["created_at", "updated_at", "completed_at"],
    "work_orders": ["deadline", "created_at", "updated_at", "started_at", "completed_at", "terminated_at"],
    "work_order_notes": ["created_at"],
    "transfer_orders": ["created_at", "updated_at", "approved_at", "executed_at", "completed_at"],
    "inbound_records": ["created_at", "updated_at", "expected_arrival_at", "confirmed_at"],
    "notifications": ["created_at"],
    "reports": ["created_at"],
}

DEFAULT_COLUMNS: dict[str, list[str]] = {
    "order_stages": ["created_at", "updated_at"],
    "work_orders": ["created_at", "updated_at"],
    "work_order_notes": ["created_at"],
    "transfer_orders": ["created_at", "updated_at"],
    "inbound_records": ["created_at", "updated_at"],
    "notifications": ["created_at"],
    "reports": ["created_at"],
}


def _shift_hours(hours: int) -> None:
    for table, columns in SHIFT_COLUMNS.items():
        for col in columns:
            op.execute(
                sa.text(
                    f"""
                    UPDATE {table}
                    SET {col} = {col} + INTERVAL '{hours} hours'
                    WHERE {col} IS NOT NULL
                    """
                )
            )


def _set_defaults(expr: str) -> None:
    for table, columns in DEFAULT_COLUMNS.items():
        for col in columns:
            op.alter_column(
                table,
                col,
                existing_type=sa.DateTime(),
                server_default=sa.text(expr),
                existing_nullable=False,
            )


def upgrade() -> None:
    # Only convert remaining tables/columns that were not shifted in revision 20260319_0008.
    _shift_hours(8)
    _set_defaults(CN_NOW)

    op.drop_column("work_orders", "assigned_at")


def downgrade() -> None:
    op.add_column("work_orders", sa.Column("assigned_at", sa.DateTime(), nullable=True))

    _shift_hours(-8)
    _set_defaults("NOW()")
