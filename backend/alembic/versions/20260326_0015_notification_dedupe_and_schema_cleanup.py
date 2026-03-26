"""dedupe notifications and cleanup redundant columns

Revision ID: 20260326_0015
Revises: 20260324_0014
Create Date: 2026-03-26 10:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260326_0015"
down_revision = "20260324_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, type, COALESCE(related_type, ''), COALESCE(related_id, -1)
                        ORDER BY created_at DESC, id DESC
                    ) AS rn
                FROM notifications
            )
            DELETE FROM notifications n
            USING ranked r
            WHERE n.id = r.id
              AND r.rn > 1
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_event_dedupe
            ON notifications (user_id, type, COALESCE(related_type, ''), COALESCE(related_id, -1))
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE orders
            ALTER COLUMN last_reverted_at
            TYPE TIMESTAMP(0) WITHOUT TIME ZONE
            USING date_trunc('second', last_reverted_at)
            """
        )
    )

    op.drop_column("transfer_orders", "agent_reason")


def downgrade() -> None:
    op.add_column("transfer_orders", sa.Column("agent_reason", sa.Text(), nullable=True))

    op.execute(
        sa.text(
            """
            ALTER TABLE orders
            ALTER COLUMN last_reverted_at
            TYPE TIMESTAMP WITHOUT TIME ZONE
            """
        )
    )

    op.execute(sa.text("DROP INDEX IF EXISTS uq_notifications_event_dedupe"))
