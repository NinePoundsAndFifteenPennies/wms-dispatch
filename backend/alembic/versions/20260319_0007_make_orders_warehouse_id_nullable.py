"""make orders warehouse_id nullable to defer binding until dispatcher acceptance

Revision ID: 20260319_0007
Revises: 20260319_0006
Create Date: 2026-03-19 XX:XX:XX
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260319_0007"
down_revision = "20260319_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change warehouse_id to nullable
    # Existing orders will have NULL until dispatcher accepts them
    op.alter_column(
        'orders',
        'warehouse_id',
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    # Downgrade only succeeds if no NULL values exist
    # This is intentional: enforces data consistency
    op.alter_column(
        'orders',
        'warehouse_id',
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True,
    )