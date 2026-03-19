"""fix updated_at fields format in orders, order_stages, work_orders, inbound_records, transfer_orders
Revision ID: 20260319_0010
Revises: 20260319_0009
Create Date: 2026-03-19 22:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260319_0010"
down_revision = "20260319_0009"
branch_labels = None
depends_on = None

# 中国时区当前时间（无小数秒）
CN_NOW = "(NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)"

TABLES = ["orders", "order_stages", "work_orders", "transfer_orders", "inbound_records"]


def upgrade() -> None:
    for table in TABLES:
        # 添加 updated_at 列，默认值为中国时间，无小数秒
        op.execute(text(f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP(0) WITHOUT TIME ZONE
            DEFAULT {CN_NOW} NOT NULL
        """))

        # 将现有记录的 updated_at 回填为 created_at（转换为无小数秒）
        op.execute(text(f"""
            UPDATE {table}
            SET updated_at = date_trunc('second', created_at)
            WHERE updated_at IS NOT NULL
              AND date_trunc('second', updated_at) = date_trunc('second', {CN_NOW})
        """))


def downgrade() -> None:
    for table in TABLES:
        op.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS updated_at"))