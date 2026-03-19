"""add reason back to stocktakes

Revision ID: 20260318_0005
Revises: 20260318_0004
Create Date: 2026-03-18 15:15:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260318_0005"
down_revision = "20260318_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stocktakes", sa.Column("reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("stocktakes", "reason")
