from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class TransferOrder(Base):
    __tablename__ = "transfer_orders"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_transfer_orders_qty_positive"),
        CheckConstraint("from_warehouse_id != to_warehouse_id", name="ck_transfer_orders_from_to_different"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled', 'completed')",
            name="ck_transfer_orders_status_valid",
        ),
        CheckConstraint("source IN ('manual', 'agent')", name="ck_transfer_orders_source_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    from_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    to_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    review_dispatcher_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    description: Mapped[Optional[str]] = mapped_column(Text)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(8), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
