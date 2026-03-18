from typing import List, Optional
import bcrypt
from fastapi import HTTPException, UploadFile
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.customer import Customer
from models.inventory import Inventory
from models.product import Product
from models.user import User
from models.warehouse import Warehouse
from modules.admin.schemas import (
    CustomerCreate,
    CustomerUpdate,
    ProductCreate,
    ProductUpdate,
    StocktakeAdjustRequest,
    UserCreate,
    UserStatusUpdate,
    UserUpdate,
    WarehouseCreate,
    WarehouseInventoryItemResponse,
    WarehouseUpdate,
)
from modules.shared.storage import save_image_file
from modules.shared.storage import delete_resource_file_by_url

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode("utf-8")

class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_users(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(User)
        if search:
            stmt = stmt.where(or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
            
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        
        stmt = stmt.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        
        return {"items": items, "total": total}

    async def create_user(self, user_data: UserCreate) -> User:
        if user_data.role != "admin" and not user_data.warehouse_id:
            raise HTTPException(status_code=400, detail="warehouse_id is required for non-admin users")
            
        # Check duplicate
        existing = await self.session.execute(select(User).where(or_(User.username == user_data.username, User.email == user_data.email)))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username or email already exists")

        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            password=hashed_password,
            email=user_data.email,
            role=user_data.role,
            warehouse_id=user_data.warehouse_id,
            skill_picking=user_data.skill_picking,
            skill_staging=user_data.skill_staging,
            skill_shipping=user_data.skill_shipping,
            is_active=True
        )
        self.session.add(new_user)
        try:
            await self.session.commit()
            await self.session.refresh(new_user)
            return new_user
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        curr_role = user_data.role if user_data.role is not None else user.role
        curr_wh = user_data.warehouse_id if user_data.warehouse_id is not None else user.warehouse_id
        if curr_role != "admin" and not curr_wh:
            raise HTTPException(status_code=400, detail="warehouse_id is required for non-admin users")

        if user_data.username is not None:
            user.username = user_data.username
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.role is not None:
            user.role = user_data.role
        if user_data.warehouse_id is not None:
            user.warehouse_id = user_data.warehouse_id
        if user_data.skill_picking is not None:
            user.skill_picking = user_data.skill_picking
        if user_data.skill_staging is not None:
            user.skill_staging = user_data.skill_staging
        if user_data.skill_shipping is not None:
            user.skill_shipping = user_data.skill_shipping

        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail="Update failed, check for duplicate username/email")

    async def update_user_status(self, user_id: int, status_update: UserStatusUpdate) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.role == "admin" and not status_update.is_active:
            raise HTTPException(status_code=400, detail="Admin account cannot be disabled")

        user.is_active = status_update.is_active
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def batch_disable_users(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(User).where(User.id.in_(ids), User.is_active.is_(True), User.role != "admin")
        )
        users = result.scalars().all()
        if not users:
            return 0

        for user in users:
            user.is_active = False
        await self.session.commit()
        return len(users)

    async def list_warehouses(self) -> List[Warehouse]:
        result = await self.session.execute(select(Warehouse).order_by(Warehouse.id.asc()))
        return result.scalars().all()

    async def list_warehouses_manage(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(Warehouse)
        if search:
            stmt = stmt.where(
                or_(
                    Warehouse.name.ilike(f"%{search}%"),
                    Warehouse.address.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(Warehouse.id.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return {"items": items, "total": total}

    async def create_warehouse(self, warehouse_data: WarehouseCreate) -> Warehouse:
        existing = await self.session.execute(select(Warehouse).where(Warehouse.name == warehouse_data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Warehouse name already exists")

        warehouse = Warehouse(**warehouse_data.model_dump())
        self.session.add(warehouse)
        try:
            await self.session.commit()
            await self.session.refresh(warehouse)
            return warehouse
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_warehouse(self, warehouse_id: int, warehouse_data: WarehouseUpdate) -> Warehouse:
        result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        update_data = warehouse_data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != warehouse.name:
            existing = await self.session.execute(select(Warehouse).where(Warehouse.name == update_data["name"]))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Warehouse name already exists")

        for field_name, value in update_data.items():
            setattr(warehouse, field_name, value)

        try:
            await self.session.commit()
            await self.session.refresh(warehouse)
            return warehouse
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def delete_warehouse(self, warehouse_id: int) -> None:
        result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        warehouse.is_active = False
        await self.session.commit()

    async def update_warehouse_status(self, warehouse_id: int, is_active: bool) -> Warehouse:
        result = await self.session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        warehouse.is_active = is_active
        await self.session.commit()
        await self.session.refresh(warehouse)
        return warehouse

    async def batch_delete_warehouses(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id.in_(ids), Warehouse.is_active.is_(True))
        )
        warehouses = result.scalars().all()
        if not warehouses:
            return 0

        for warehouse in warehouses:
            warehouse.is_active = False
        await self.session.commit()
        return len(warehouses)

    async def upload_warehouse_image(self, warehouse_id: int, image: UploadFile) -> Warehouse:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        old_image_path = warehouse.cover_image
        saved_path = await save_image_file(
            upload_file=image,
            bucket="warehouse_covers",
            entity_prefix="warehouse",
            entity_id=warehouse_id,
        )
        warehouse.cover_image = saved_path

        try:
            await self.session.commit()
            await self.session.refresh(warehouse)
        except Exception as e:
            await self.session.rollback()
            delete_resource_file_by_url(saved_path)
            raise HTTPException(status_code=400, detail=str(e))

        if old_image_path and old_image_path != saved_path:
            delete_resource_file_by_url(old_image_path)
        return warehouse

    async def get_warehouse_inventory(
        self,
        warehouse_id: int,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ):
        warehouse_result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = warehouse_result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        stmt = (
            select(Inventory, Product)
            .join(Product, Product.id == Inventory.product_id)
            .where(Inventory.warehouse_id == warehouse_id)
        )
        if search:
            stmt = stmt.where(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.sku.ilike(f"%{search}%"),
                    Product.category.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(Product.name.asc(), Product.id.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        rows = result.all()
        items = [
            WarehouseInventoryItemResponse(
                id=inventory.id,
                product_id=inventory.product_id,
                sku=product.sku,
                product_name=product.name,
                category=product.category,
                product_is_active=product.is_active,
                qty_on_hand=inventory.qty_on_hand,
                qty_reserved=inventory.qty_reserved,
                qty_locked=inventory.qty_locked,
                qty_threshold=inventory.qty_threshold,
                qty_available=inventory.qty_available,
            )
            for inventory, product in rows
        ]

        return {"warehouse": warehouse, "items": items, "total": total}

    async def adjust_warehouse_inventory_stocktake(
        self,
        warehouse_id: int,
        inventory_id: int,
        payload: StocktakeAdjustRequest,
    ):
        result = await self.session.execute(
            select(Inventory)
            .where(Inventory.id == inventory_id)
            .where(Inventory.warehouse_id == warehouse_id)
        )
        inventory = result.scalar_one_or_none()
        if not inventory:
            raise HTTPException(status_code=404, detail="Inventory record not found")

        min_on_hand = inventory.qty_reserved + inventory.qty_locked
        if payload.qty_on_hand < min_on_hand:
            raise HTTPException(
                status_code=400,
                detail=f"qty_on_hand cannot be less than qty_reserved + qty_locked ({min_on_hand})",
            )

        inventory.qty_on_hand = payload.qty_on_hand
        await self.session.commit()
        await self.session.refresh(inventory)
        return inventory

    async def remove_warehouse_image(self, warehouse_id: int) -> Warehouse:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        old_image_path = warehouse.cover_image
        warehouse.cover_image = None
        if old_image_path and not delete_resource_file_by_url(old_image_path):
            await self.session.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete warehouse image file")
        await self.session.commit()
        await self.session.refresh(warehouse)
        return warehouse

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
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
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

    async def list_products(self, page: int = 1, page_size: int = 10, search: Optional[str] = None):
        stmt = select(Product)
        if search:
            stmt = stmt.where(
                or_(
                    Product.sku.ilike(f"%{search}%"),
                    Product.name.ilike(f"%{search}%"),
                    Product.category.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return {"items": items, "total": total}

    async def create_product(self, product_data: ProductCreate) -> Product:
        existing = await self.session.execute(select(Product).where(Product.sku == product_data.sku))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="SKU already exists")

        product = Product(**product_data.model_dump())
        self.session.add(product)
        try:
            await self.session.commit()
            await self.session.refresh(product)
            return product
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def update_product(self, product_id: int, product_data: ProductUpdate) -> Product:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        update_data = product_data.model_dump(exclude_unset=True)
        if "sku" in update_data and update_data["sku"] != product.sku:
            existing = await self.session.execute(select(Product).where(Product.sku == update_data["sku"]))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="SKU already exists")

        for field_name, value in update_data.items():
            setattr(product, field_name, value)

        try:
            await self.session.commit()
            await self.session.refresh(product)
            return product
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    async def delete_product(self, product_id: int) -> None:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product.is_active = False
        await self.session.commit()

    async def update_product_status(self, product_id: int, is_active: bool) -> Product:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product.is_active = is_active
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def batch_delete_products(self, ids: List[int]) -> int:
        result = await self.session.execute(
            select(Product).where(Product.id.in_(ids), Product.is_active.is_(True))
        )
        products = result.scalars().all()
        if not products:
            return 0

        for product in products:
            product.is_active = False
        await self.session.commit()
        return len(products)

    async def upload_product_image(self, product_id: int, image: UploadFile) -> Product:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        old_image_path = product.cover_image
        saved_path = await save_image_file(
            upload_file=image,
            bucket="product_images",
            entity_prefix="product",
            entity_id=product_id,
        )
        product.cover_image = saved_path

        try:
            await self.session.commit()
            await self.session.refresh(product)
        except Exception as e:
            await self.session.rollback()
            delete_resource_file_by_url(saved_path)
            raise HTTPException(status_code=400, detail=str(e))

        if old_image_path and old_image_path != saved_path:
            delete_resource_file_by_url(old_image_path)
        return product

    async def remove_product_image(self, product_id: int) -> Product:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        old_image_path = product.cover_image
        product.cover_image = None
        await self.session.commit()
        await self.session.refresh(product)

        delete_resource_file_by_url(old_image_path)
        return product
