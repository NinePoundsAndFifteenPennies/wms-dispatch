from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class InboundRecord(Base):
    __tablename__ = "inbound_records"
    __table_args__ = (
        UniqueConstraint("transfer_order_id", name="uq_inbound_records_transfer_order_id"),
        CheckConstraint("qty > 0", name="ck_inbound_records_qty_positive"),
        CheckConstraint("status IN ('pending', 'confirmed')", name="ck_inbound_records_status_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_order_id: Mapped[int] = mapped_column(ForeignKey("transfer_orders.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    expected_arrival_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    confirmed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
