"""init core tables

Revision ID: 20260317_0001
Revises:
Create Date: 2026-03-17 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260317_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("capacity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cover_image", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_warehouses_name"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
        sa.Column("skill_picking", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skill_staging", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skill_shipping", sa.Integer(), server_default="0", nullable=False),
        sa.Column("avatar", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_users_warehouse_id_warehouses"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(
            "role IN ('admin', 'dispatcher', 'worker')",
            name="ck_users_role_valid",
        ),
        sa.CheckConstraint(
            "role = 'admin' OR warehouse_id IS NOT NULL",
            name="ck_users_warehouse_required_for_non_admin",
        ),
        sa.CheckConstraint(
            "skill_picking >= 0 AND skill_staging >= 0 AND skill_shipping >= 0",
            name="ck_users_skills_non_negative",
        ),
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("contact", sa.String(length=128), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("unit_weight", sa.Numeric(10, 2), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=16), server_default="piece", nullable=False),
        sa.Column("req_skill_picking", sa.Integer(), server_default="0", nullable=False),
        sa.Column("req_skill_staging", sa.Integer(), server_default="0", nullable=False),
        sa.Column("req_skill_shipping", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cover_image", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
        sa.CheckConstraint(
            "req_skill_picking >= 0 AND req_skill_staging >= 0 AND req_skill_shipping >= 0",
            name="ck_products_required_skills_non_negative",
        ),
    )

    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("qty_on_hand", sa.Integer(), server_default="0", nullable=False),
        sa.Column("qty_reserved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("qty_locked", sa.Integer(), server_default="0", nullable=False),
        sa.Column("qty_threshold", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "qty_available",
            sa.Integer(),
            sa.Computed("qty_on_hand - qty_reserved - qty_locked", persisted=True),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_inventory_warehouse_id_warehouses"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_inventory_product_id_products"),
        sa.UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_warehouse_product"),
        sa.CheckConstraint(
            "qty_on_hand >= 0 AND qty_reserved >= 0 AND qty_locked >= 0",
            name="ck_inventory_qty_non_negative",
        ),
        sa.CheckConstraint("qty_on_hand >= qty_locked", name="ck_inventory_on_hand_ge_locked"),
        sa.CheckConstraint(
            "qty_on_hand - qty_reserved - qty_locked >= 0",
            name="ck_inventory_available_non_negative",
        ),
    )


def downgrade() -> None:
    op.drop_table("inventory")
    op.drop_table("products")
    op.drop_table("customers")
    op.drop_table("users")
    op.drop_table("warehouses")
