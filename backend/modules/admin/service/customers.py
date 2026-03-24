from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from models.customer import Customer
from modules.admin.schemas import CustomerCreate, CustomerUpdate


class CustomerServiceMixin:
    async def list_customers(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(Customer)
        if search:
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Customer.contact.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(Customer.id.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return {"items": items, "total": total}

    async def list_customers_options(self, search: Optional[str] = None):
        stmt = select(Customer).order_by(Customer.id.desc())
        if search:
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Customer.contact.ilike(f"%{search}%"),
                )
            )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_customer(self, customer_data: CustomerCreate) -> Customer:
        customer = Customer(
            name=customer_data.name,
            contact=customer_data.contact,
            address=customer_data.address,
            description=customer_data.description,
            is_active=True,
        )
        self.session.add(customer)
        try:
            await self.session.commit()
            await self.session.refresh(customer)
            return customer
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_customer(self, customer_id: int, customer_data: CustomerUpdate) -> Customer:
        result = await self.session.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        update_data = customer_data.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(customer, field_name, value)

        try:
            await self.session.commit()
            await self.session.refresh(customer)
            return customer
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def delete_customer(self, customer_id: int) -> None:
        result = await self.session.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        customer.is_active = False
        await self.session.commit()

    async def update_customer_status(self, customer_id: int, is_active: bool) -> Customer:
        result = await self.session.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        customer.is_active = is_active
        await self.session.commit()
        await self.session.refresh(customer)
        return customer

    async def batch_delete_customers(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(Customer).where(Customer.id.in_(ids), Customer.is_active.is_(True))
        )
        customers = result.scalars().all()
        if not customers:
            return 0

        for customer in customers:
            customer.is_active = False
        await self.session.commit()
        return len(customers)
