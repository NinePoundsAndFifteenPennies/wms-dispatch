"""create remaining business tables

Revision ID: 20260317_0002
Revises: 20260317_0001
Create Date: 2026-03-17 00:20:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260317_0002"
down_revision = "20260317_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_users_skills",
        "users",
        ["skill_picking", "skill_staging", "skill_shipping"],
        unique=False,
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("delta_on_hand", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delta_reserved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delta_locked", sa.Integer(), server_default="0", nullable=False),
        sa.Column("before_on_hand", sa.Integer(), nullable=False),
        sa.Column("before_reserved", sa.Integer(), nullable=False),
        sa.Column("before_locked", sa.Integer(), nullable=False),
        sa.Column("after_on_hand", sa.Integer(), nullable=False),
        sa.Column("after_reserved", sa.Integer(), nullable=False),
        sa.Column("after_locked", sa.Integer(), nullable=False),
        sa.Column("related_type", sa.String(length=32), nullable=True),
        sa.Column("related_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("operated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["inventory_id"], ["inventory.id"], name="fk_inventory_movements_inventory_id_inventory"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_inventory_movements_warehouse_id_warehouses"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_inventory_movements_product_id_products"),
        sa.ForeignKeyConstraint(["operated_by"], ["users.id"], name="fk_inventory_movements_operated_by_users"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_no", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("dispatcher_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending_acceptance", nullable=False),
        sa.Column("priority", sa.String(length=8), server_default="medium", nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_by", sa.Integer(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_orders_customer_id_customers"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_orders_warehouse_id_warehouses"),
        sa.ForeignKeyConstraint(["dispatcher_id"], ["users.id"], name="fk_orders_dispatcher_id_users"),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"], name="fk_orders_cancelled_by_users"),
        sa.UniqueConstraint("order_no", name="uq_orders_order_no"),
        sa.CheckConstraint(
            "status IN ('pending_acceptance', 'in_progress', 'completed', 'cancelled')",
            name="ck_orders_status_valid",
        ),
        sa.CheckConstraint("priority IN ('high', 'medium', 'low')", name="ck_orders_priority_valid"),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name="fk_order_items_order_id_orders"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_order_items_product_id_products"),
        sa.CheckConstraint("qty > 0", name="ck_order_items_qty_gt_zero"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_non_negative"),
    )

    op.create_table(
        "order_stages",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("stage_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="not_started", nullable=False),
        sa.Column("completion_type", sa.String(length=8), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_by", sa.Integer(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name="fk_order_stages_order_id_orders"),
        sa.ForeignKeyConstraint(["completed_by"], ["users.id"], name="fk_order_stages_completed_by_users"),
        sa.UniqueConstraint("order_id", "stage_type", name="uq_order_stages_order_stage_type"),
        sa.CheckConstraint("stage_type IN ('picking', 'staging', 'shipping')", name="ck_order_stages_stage_type_valid"),
        sa.CheckConstraint("status IN ('not_started', 'in_progress', 'completed')", name="ck_order_stages_status_valid"),
        sa.CheckConstraint("completion_type IS NULL OR completion_type IN ('auto', 'manual')", name="ck_order_stages_completion_type_valid"),
    )

    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("stage_type", sa.String(length=16), nullable=False),
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column("dispatcher_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("priority", sa.String(length=8), server_default="medium", nullable=False),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=8), server_default="manual", nullable=False),
        sa.Column("agent_reason", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("terminated_at", sa.DateTime(), nullable=True),
        sa.Column("terminated_by", sa.Integer(), nullable=True),
        sa.Column("termination_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name="fk_work_orders_order_id_orders"),
        sa.ForeignKeyConstraint(["worker_id"], ["users.id"], name="fk_work_orders_worker_id_users"),
        sa.ForeignKeyConstraint(["dispatcher_id"], ["users.id"], name="fk_work_orders_dispatcher_id_users"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_work_orders_warehouse_id_warehouses"),
        sa.ForeignKeyConstraint(["terminated_by"], ["users.id"], name="fk_work_orders_terminated_by_users"),
        sa.CheckConstraint("stage_type IN ('picking', 'staging', 'shipping')", name="ck_work_orders_stage_type_valid"),
        sa.CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'terminated')", name="ck_work_orders_status_valid"),
        sa.CheckConstraint("priority IN ('high', 'medium', 'low')", name="ck_work_orders_priority_valid"),
        sa.CheckConstraint("source IN ('manual', 'agent')", name="ck_work_orders_source_valid"),
    )

    op.create_table(
        "work_order_notes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("note_type", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], name="fk_work_order_notes_work_order_id_work_orders"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_work_order_notes_created_by_users"),
        sa.CheckConstraint("note_type IN ('normal', 'damaged', 'qty_mismatch', 'other')", name="ck_work_order_notes_note_type_valid"),
    )

    op.create_table(
        "transfer_orders",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("from_warehouse_id", sa.Integer(), nullable=False),
        sa.Column("to_warehouse_id", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=8), server_default="manual", nullable=False),
        sa.Column("agent_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_transfer_orders_product_id_products"),
        sa.ForeignKeyConstraint(["from_warehouse_id"], ["warehouses.id"], name="fk_transfer_orders_from_warehouse_id_warehouses"),
        sa.ForeignKeyConstraint(["to_warehouse_id"], ["warehouses.id"], name="fk_transfer_orders_to_warehouse_id_warehouses"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], name="fk_transfer_orders_requested_by_users"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], name="fk_transfer_orders_approved_by_users"),
        sa.CheckConstraint("qty > 0", name="ck_transfer_orders_qty_gt_zero"),
        sa.CheckConstraint("from_warehouse_id != to_warehouse_id", name="ck_transfer_orders_diff_warehouse"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'cancelled', 'completed')", name="ck_transfer_orders_status_valid"),
        sa.CheckConstraint("source IN ('manual', 'agent')", name="ck_transfer_orders_source_valid"),
    )

    op.create_table(
        "inbound_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("transfer_order_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("expected_arrival_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["transfer_order_id"], ["transfer_orders.id"], name="fk_inbound_records_transfer_order_id_transfer_orders"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], name="fk_inbound_records_warehouse_id_warehouses"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_inbound_records_product_id_products"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], name="fk_inbound_records_confirmed_by_users"),
        sa.UniqueConstraint("transfer_order_id", name="uq_inbound_records_transfer_order_id"),
        sa.CheckConstraint("qty > 0", name="ck_inbound_records_qty_gt_zero"),
        sa.CheckConstraint("status IN ('pending', 'confirmed')", name="ck_inbound_records_status_valid"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("related_id", sa.Integer(), nullable=True),
        sa.Column("related_type", sa.String(length=32), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_notifications_user_id_users"),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("generated_by", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("stats_json", postgresql.JSONB(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], name="fk_reports_generated_by_users"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], name="fk_reports_target_user_id_users"),
        sa.CheckConstraint("period_end >= period_start", name="ck_reports_period_valid"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("notifications")
    op.drop_table("inbound_records")
    op.drop_table("transfer_orders")
    op.drop_table("work_order_notes")
    op.drop_table("work_orders")
    op.drop_table("order_stages")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("inventory_movements")
    op.drop_index("idx_users_skills", table_name="users")
