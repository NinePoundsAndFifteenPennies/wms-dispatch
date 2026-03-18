"""create stocktake events table

Revision ID: 20260318_0003
Revises: 20260317_0002
Create Date: 2026-03-18 09:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260318_0003"
down_revision = "20260317_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stocktakes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("before_on_hand", sa.Integer(), nullable=False),
        sa.Column("after_on_hand", sa.Integer(), nullable=False),
        sa.Column("delta_on_hand", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("operated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_stocktakes_warehouse_id_warehouses"),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventory.id"], name="fk_stocktakes_inventory_id_inventory"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_stocktakes_product_id_products"),
        sa.ForeignKeyConstraint(["operated_by"], ["users.id"], name="fk_stocktakes_operated_by_users"),
        sa.CheckConstraint("before_on_hand >= 0", name="ck_stocktakes_before_on_hand_non_negative"),
        sa.CheckConstraint("after_on_hand >= 0", name="ck_stocktakes_after_on_hand_non_negative"),
    )

    op.create_index("idx_stocktakes_created_at", "stocktakes", ["created_at"], unique=False)
    op.create_index("idx_stocktakes_inventory_id", "stocktakes", ["inventory_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_stocktakes_inventory_id", table_name="stocktakes")
    op.drop_index("idx_stocktakes_created_at", table_name="stocktakes")
    op.drop_table("stocktakes")
