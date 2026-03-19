"""normalize timestamp precision to seconds

Revision ID: 20260319_0009
Revises: 20260319_0008
Create Date: 2026-03-19 17:05:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260319_0009"
down_revision = "20260319_0008"
branch_labels = None
depends_on = None


_TIMESTAMP_COLUMNS = {
    "users": ["created_at", "updated_at"],
    "warehouses": ["created_at", "updated_at"],
    "products": ["created_at", "updated_at"],
    "customers": ["created_at", "updated_at"],
    "inventory": ["created_at", "updated_at"],
    "inventory_movements": ["created_at"],
    "stocktakes": ["created_at"],
    "orders": ["accepted_at", "completed_at", "cancelled_at", "created_at"],
    "order_stages": ["completed_at", "created_at"],
    "work_orders": ["deadline", "assigned_at", "started_at", "completed_at", "terminated_at", "created_at"],
    "work_order_notes": ["created_at"],
    "transfer_orders": ["approved_at", "executed_at", "completed_at", "created_at"],
    "inbound_records": ["expected_arrival_at", "confirmed_at", "created_at"],
    "notifications": ["created_at"],
}


def _validate_identifier(identifier: str) -> None:
    if not identifier.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQL identifier: {identifier}")


def _truncate_and_convert_to_seconds_precision(table: str, column: str) -> None:
    _validate_identifier(table)
    _validate_identifier(column)
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column}
            TYPE TIMESTAMP(0) WITHOUT TIME ZONE
            USING date_trunc('second', {column})
            """
        )
    )


def _convert_to_default_timestamp_precision(table: str, column: str) -> None:
    _validate_identifier(table)
    _validate_identifier(column)
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column}
            TYPE TIMESTAMP WITHOUT TIME ZONE
            """
        )
    )


def upgrade() -> None:
    for table, columns in _TIMESTAMP_COLUMNS.items():
        for column in columns:
            _truncate_and_convert_to_seconds_precision(table, column)


def downgrade() -> None:
    for table, columns in _TIMESTAMP_COLUMNS.items():
        for column in columns:
            _convert_to_default_timestamp_precision(table, column)

