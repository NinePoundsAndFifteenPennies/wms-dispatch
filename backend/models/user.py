from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base
import models.warehouse # For relationship

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'dispatcher', 'worker')", name="users_role_check"),
        CheckConstraint("role = 'admin' OR warehouse_id IS NOT NULL", name="users_warehouse_check"),
        CheckConstraint("skill_picking >= 0 AND skill_staging >= 0 AND skill_shipping >= 0", name="users_skills_check")
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"))
    skill_picking: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skill_staging: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skill_shipping: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avatar: Mapped[Optional[str]] = mapped_column(String(512))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    warehouse = relationship("Warehouse", back_populates="users")