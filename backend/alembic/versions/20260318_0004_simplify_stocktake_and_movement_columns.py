"""simplify stocktake and movement columns

Revision ID: 20260318_0004
Revises: 20260318_0003
Create Date: 2026-03-18 14:50:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260318_0004"
down_revision = "20260318_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("inventory_movements", "reason", existing_type=sa.Text(), nullable=True)
    op.drop_column("inventory_movements", "reason")

    op.drop_constraint("fk_stocktakes_warehouse_id_warehouses", "stocktakes", type_="foreignkey")
    op.drop_constraint("fk_stocktakes_product_id_products", "stocktakes", type_="foreignkey")
    op.drop_constraint("fk_stocktakes_operated_by_users", "stocktakes", type_="foreignkey")
    op.drop_column("stocktakes", "warehouse_id")
    op.drop_column("stocktakes", "product_id")
    op.drop_column("stocktakes", "reason")
    op.drop_column("stocktakes", "operated_by")


def downgrade() -> None:
    op.add_column("stocktakes", sa.Column("operated_by", sa.Integer(), nullable=True))
    op.add_column("stocktakes", sa.Column("reason", sa.Text(), nullable=True))
    op.add_column("stocktakes", sa.Column("product_id", sa.Integer(), nullable=True))
    op.add_column("stocktakes", sa.Column("warehouse_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_stocktakes_warehouse_id_warehouses",
        "stocktakes",
        "warehouses",
        ["warehouse_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_stocktakes_product_id_products",
        "stocktakes",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_stocktakes_operated_by_users",
        "stocktakes",
        "users",
        ["operated_by"],
        ["id"],
    )

    op.add_column("inventory_movements", sa.Column("reason", sa.Text(), nullable=True))
