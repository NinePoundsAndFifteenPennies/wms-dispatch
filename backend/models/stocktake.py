from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class Stocktake(Base):
    __tablename__ = "stocktakes"
    __table_args__ = (
        CheckConstraint("before_on_hand >= 0", name="ck_stocktakes_before_on_hand_non_negative"),
        CheckConstraint("after_on_hand >= 0", name="ck_stocktakes_after_on_hand_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"), nullable=False)
    before_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    after_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
