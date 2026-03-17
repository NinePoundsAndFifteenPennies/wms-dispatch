from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "req_skill_picking >= 0 AND req_skill_staging >= 0 AND req_skill_shipping >= 0",
            name="products_required_skills_check",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64))
    unit_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    unit_of_measure: Mapped[str] = mapped_column(String(16), nullable=False, default="piece")
    req_skill_picking: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    req_skill_staging: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    req_skill_shipping: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cover_image: Mapped[Optional[str]] = mapped_column(String(512))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
