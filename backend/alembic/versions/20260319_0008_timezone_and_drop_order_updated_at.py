"""normalize timestamps to cn timezone style and drop redundant updated_at columns

Revision ID: 20260319_0008
Revises: 20260319_0007
Create Date: 2026-03-19 15:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260319_0008"
down_revision = "20260319_0007"
branch_labels = None
depends_on = None


def _shift_to_cn_time(table_name: str, columns: list[str]) -> None:
    allowed_tables = {
        "users",
        "warehouses",
        "products",
        "customers",
        "inventory",
        "stocktakes",
        "inventory_movements",
        "orders",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported table for migration shift: {table_name}")

    for col in columns:
        if not col.replace("_", "").isalnum():
            raise ValueError(f"Unsafe column name: {col}")
        op.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                SET {col} = {col} + INTERVAL '8 hours'
                WHERE {col} IS NOT NULL
                """
            )
        )


def _shift_from_cn_time(table_name: str, columns: list[str]) -> None:
    allowed_tables = {
        "users",
        "warehouses",
        "products",
        "customers",
        "inventory",
        "stocktakes",
        "inventory_movements",
        "orders",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported table for migration shift: {table_name}")

    for col in columns:
        if not col.replace("_", "").isalnum():
            raise ValueError(f"Unsafe column name: {col}")
        op.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                SET {col} = {col} - INTERVAL '8 hours'
                WHERE {col} IS NOT NULL
                """
            )
        )


def upgrade() -> None:
    # 1) 统一默认时间口径：改为国区时区下的当前时间（timestamp without time zone）
    for table, column in [
        ("users", "created_at"),
        ("users", "updated_at"),
        ("warehouses", "created_at"),
        ("warehouses", "updated_at"),
        ("products", "created_at"),
        ("products", "updated_at"),
        ("customers", "created_at"),
        ("customers", "updated_at"),
        ("inventory", "created_at"),
        ("inventory", "updated_at"),
        ("stocktakes", "created_at"),
        ("inventory_movements", "created_at"),
        ("orders", "created_at"),
    ]:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(),
            server_default=sa.text("timezone('Asia/Shanghai', now())"),
            existing_nullable=False,
        )

    # 2) 已有数据按 +8 小时换算（用户表、仓库表、产品表、客户表、库存表、stocktakes、库存流水、订单表）
    _shift_to_cn_time("users", ["created_at", "updated_at"])
    _shift_to_cn_time("warehouses", ["created_at", "updated_at"])
    _shift_to_cn_time("products", ["created_at", "updated_at"])
    _shift_to_cn_time("customers", ["created_at", "updated_at"])
    _shift_to_cn_time("inventory", ["created_at", "updated_at"])
    _shift_to_cn_time("stocktakes", ["created_at"])
    _shift_to_cn_time("inventory_movements", ["created_at"])
    _shift_to_cn_time(
        "orders",
        ["accepted_at", "completed_at", "cancelled_at", "created_at", "updated_at"],
    )

    # 3) 去掉冗余 updated_at（订单表/订单阶段表/工作订单表/调拨单表/待入库记录表）
    op.drop_column("orders", "updated_at")
    op.drop_column("order_stages", "updated_at")
    op.drop_column("work_orders", "updated_at")
    op.drop_column("transfer_orders", "updated_at")
    op.drop_column("inbound_records", "updated_at")


def downgrade() -> None:
    # 恢复列
    op.add_column("orders", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False))
    op.add_column("order_stages", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False))
    op.add_column("work_orders", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False))
    op.add_column("transfer_orders", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False))
    op.add_column("inbound_records", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False))

    # 数据回退 -8 小时（与 upgrade 对称）
    _shift_from_cn_time("users", ["created_at", "updated_at"])
    _shift_from_cn_time("warehouses", ["created_at", "updated_at"])
    _shift_from_cn_time("products", ["created_at", "updated_at"])
    _shift_from_cn_time("customers", ["created_at", "updated_at"])
    _shift_from_cn_time("inventory", ["created_at", "updated_at"])
    _shift_from_cn_time("stocktakes", ["created_at"])
    _shift_from_cn_time("inventory_movements", ["created_at"])
    _shift_from_cn_time(
        "orders",
        ["accepted_at", "completed_at", "cancelled_at", "created_at", "updated_at"],
    )

    # 恢复默认
    for table, column in [
        ("users", "created_at"),
        ("users", "updated_at"),
        ("warehouses", "created_at"),
        ("warehouses", "updated_at"),
        ("products", "created_at"),
        ("products", "updated_at"),
        ("customers", "created_at"),
        ("customers", "updated_at"),
        ("inventory", "created_at"),
        ("inventory", "updated_at"),
        ("stocktakes", "created_at"),
        ("inventory_movements", "created_at"),
        ("orders", "created_at"),
    ]:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(),
            server_default=sa.text("NOW()"),
            existing_nullable=False,
        )
