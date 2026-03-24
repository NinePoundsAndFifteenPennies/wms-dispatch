from typing import List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, or_, select

from models.product import Product
from modules.admin.schemas import ProductCreate, ProductUpdate
from modules.shared.storage import delete_resource_file_by_url, save_image_file


class ProductServiceMixin:
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

    async def get_product(self, product_id: int) -> Product:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

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
        result = await self.session.execute(select(Product).where(Product.id == product_id))
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
        result = await self.session.execute(select(Product).where(Product.id == product_id))
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
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        old_image_path = product.cover_image
        product.cover_image = None
        await self.session.commit()
        await self.session.refresh(product)

        delete_resource_file_by_url(old_image_path)
        return product
