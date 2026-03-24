import base64
import csv
from datetime import date, datetime
from io import BytesIO, StringIO
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from models.customer import Customer
from models.order import Order
from models.order_item import OrderItem
from models.product import Product
from modules.admin.schemas import OrderCreate, OrderPendingUpdateRequest

from .base import SYSTEM_TIMEZONE


class OrderServiceMixin:
    def _build_order_filters(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        clauses = ["1=1"]
        params = {}
        if search:
            clauses.append("(o.order_no ILIKE :search OR c.name ILIKE :search)")
            params["search"] = f"%{search}%"
        if status:
            clauses.append("o.status = :status")
            params["status"] = status
        if start_date:
            clauses.append("DATE(o.created_at) >= :start_date")
            params["start_date"] = start_date
        if end_date:
            clauses.append("DATE(o.created_at) <= :end_date")
            params["end_date"] = end_date
        return " AND ".join(clauses), params

    async def list_orders(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        where_sql, params = self._build_order_filters(
            search=search,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

        count_result = await self.session.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE {where_sql}
                """
            ),
            params,
        )
        total = count_result.scalar_one() or 0

        query_params = {
            **params,
            "offset": (page - 1) * page_size,
            "limit": page_size,
        }
        rows = await self.session.execute(
            text(
                f"""
                SELECT
                    o.id,
                    o.order_no,
                    o.customer_id,
                    c.name AS customer_name,
                    o.warehouse_id,
                    w.name AS warehouse_name,
                    o.dispatcher_id,
                    u.username AS dispatcher_name,
                    o.description,
                    o.status,
                    o.priority,
                    o.accepted_at,
                    o.completed_at,
                    o.cancelled_at,
                    o.created_at,
                    COALESCE(SUM(oi.qty * oi.unit_price), 0)::INTEGER AS total_amount,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_items
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN warehouses w ON w.id = o.warehouse_id
                LEFT JOIN users u ON u.id = o.dispatcher_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE {where_sql}
                GROUP BY o.id, c.name, w.name, u.username
                ORDER BY o.id DESC
                OFFSET :offset
                LIMIT :limit
                """
            ),
            query_params,
        )
        items = [dict(row) for row in rows.mappings().all()]
        return {"items": items, "total": total}

    async def _next_order_no(self) -> str:
        prefix = f"OD-{datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).strftime('%y%m%d')}"
        seq_result = await self.session.execute(
            text(
                """
                SELECT COALESCE(MAX(CAST(split_part(order_no, '-', 3) AS INTEGER)), 0)
                FROM orders
                WHERE order_no LIKE :prefix
                """
            ),
            {"prefix": f"{prefix}-%"},
        )
        seq = (seq_result.scalar_one() or 0) + 1
        return f"{prefix}-{seq:03d}"

    async def create_order(self, payload: OrderCreate) -> Order:
        customer_result = await self.session.execute(select(Customer).where(Customer.id == payload.customer_id))
        customer = customer_result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        if not customer.is_active:
            raise HTTPException(status_code=400, detail="Inactive customer cannot be selected")

        product_ids = [item.product_id for item in payload.items]
        if len(set(product_ids)) != len(product_ids):
            raise HTTPException(status_code=400, detail="Duplicate product in order items is not allowed")

        products_result = await self.session.execute(
            select(Product).where(Product.id.in_(product_ids), Product.is_active.is_(True))
        )
        valid_products = products_result.scalars().all()
        if len(valid_products) != len(product_ids):
            raise HTTPException(status_code=400, detail="Order items contain unavailable products")

        for _ in range(3):
            order_no = await self._next_order_no()
            order = Order(
                order_no=order_no,
                customer_id=payload.customer_id,
                description=payload.description,
                priority=payload.priority,
                status="pending_acceptance",
            )
            self.session.add(order)
            try:
                await self.session.flush()
                for item in payload.items:
                    self.session.add(
                        OrderItem(
                            order_id=order.id,
                            product_id=item.product_id,
                            qty=item.qty,
                            unit_price=item.unit_price,
                        )
                    )
                await self.session.commit()
                await self.session.refresh(order)
                return order
            except IntegrityError:
                await self.session.rollback()
                continue
            except Exception as e:
                await self.session.rollback()
                raise HTTPException(status_code=400, detail=str(e))

        raise HTTPException(status_code=409, detail="Failed to generate unique order number")

    async def update_pending_order(self, order_id: int, payload: OrderPendingUpdateRequest):
        order_result = await self.session.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != "pending_acceptance":
            raise HTTPException(status_code=400, detail="Only pending orders can be edited")

        product_ids = [item.product_id for item in payload.items]
        if len(set(product_ids)) != len(product_ids):
            raise HTTPException(status_code=400, detail="Duplicate product in order items is not allowed")

        products_result = await self.session.execute(select(Product.id).where(Product.id.in_(product_ids)))
        existing_product_ids = {row[0] for row in products_result.all()}
        if existing_product_ids != set(product_ids):
            raise HTTPException(status_code=400, detail="Order items contain invalid products")

        try:
            order.priority = payload.priority
            order.description = payload.description
            order.updated_at = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)

            await self.session.execute(text("DELETE FROM order_items WHERE order_id = :order_id"), {"order_id": order.id})

            for item in payload.items:
                self.session.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=item.product_id,
                        qty=item.qty,
                        unit_price=item.unit_price,
                    )
                )

            await self.session.commit()
            return await self.get_order_detail(order.id)
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=f"Update order failed: {str(e)}")

    async def cancel_pending_order(self, order_id: int, cancellation_reason: str, cancelled_by: Optional[int] = None):
        order_result = await self.session.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != "pending_acceptance":
            raise HTTPException(status_code=400, detail="Only pending orders can be cancelled by admin here")

        reason = (cancellation_reason or "").strip()
        if not reason:
            raise HTTPException(status_code=400, detail="Cancellation reason is required")

        order.status = "cancelled"
        order.cancelled_at = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)
        order.cancelled_by = cancelled_by
        order.cancellation_reason = reason
        order.updated_at = datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).replace(tzinfo=None)

        await self.session.commit()
        return await self.get_order_detail(order.id)

    async def reopen_cancelled_order(self, order_id: int):
        source_order_result = await self.session.execute(select(Order).where(Order.id == order_id))
        source_order = source_order_result.scalar_one_or_none()
        if not source_order:
            raise HTTPException(status_code=404, detail="Order not found")
        if source_order.status != "cancelled":
            raise HTTPException(status_code=400, detail="Only cancelled orders can be reopened")

        source_items_result = await self.session.execute(
            select(OrderItem).where(OrderItem.order_id == source_order.id).order_by(OrderItem.id.asc())
        )
        source_items = source_items_result.scalars().all()
        if not source_items:
            raise HTTPException(status_code=400, detail="Cancelled order has no items to reopen")

        for _ in range(3):
            order_no = await self._next_order_no()
            new_order = Order(
                order_no=order_no,
                customer_id=source_order.customer_id,
                description=source_order.description,
                priority=source_order.priority,
                status="pending_acceptance",
            )
            self.session.add(new_order)
            try:
                await self.session.flush()
                for item in source_items:
                    self.session.add(
                        OrderItem(
                            order_id=new_order.id,
                            product_id=item.product_id,
                            qty=item.qty,
                            unit_price=item.unit_price,
                        )
                    )
                await self.session.commit()
                return await self.get_order_detail(new_order.id)
            except IntegrityError:
                await self.session.rollback()
                continue
            except Exception as e:
                await self.session.rollback()
                raise HTTPException(status_code=400, detail=f"Reopen order failed: {str(e)}")

        raise HTTPException(status_code=409, detail="Failed to generate unique order number")

    async def get_order_detail(self, order_id: int):
        order_result = await self.session.execute(
            text(
                """
                SELECT
                    o.id,
                    o.order_no,
                    o.customer_id,
                    c.name AS customer_name,
                    c.contact AS customer_contact,
                    c.address AS customer_address,
                    o.warehouse_id,
                    w.name AS warehouse_name,
                    o.dispatcher_id,
                    u.username AS dispatcher_name,
                    o.description,
                    o.status,
                    o.priority,
                    o.accepted_at,
                    o.completed_at,
                    o.cancelled_at,
                    o.cancelled_by,
                    o.cancellation_reason,
                    o.created_at,
                    COALESCE(SUM(oi.qty * oi.unit_price), 0)::INTEGER AS total_amount,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_items
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN warehouses w ON w.id = o.warehouse_id
                LEFT JOIN users u ON u.id = o.dispatcher_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.id = :order_id
                GROUP BY o.id, c.name, c.contact, c.address, w.name, u.username
                """
            ),
            {"order_id": order_id},
        )
        order = order_result.mappings().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        items_result = await self.session.execute(
            text(
                """
                SELECT
                    oi.id,
                    oi.product_id,
                    p.sku AS product_sku,
                    p.name AS product_name,
                    p.category AS product_category,
                    oi.qty,
                    oi.unit_price,
                    (oi.qty * oi.unit_price)::INTEGER AS subtotal
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = :order_id
                ORDER BY oi.id ASC
                """
            ),
            {"order_id": order_id},
        )

        return {**dict(order), "items": [dict(row) for row in items_result.mappings().all()]}

    async def export_orders(
        self,
        export_format: str = "csv",
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        where_sql, params = self._build_order_filters(
            search=search,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
        rows = await self.session.execute(
            text(
                f"""
                SELECT
                    o.order_no,
                    c.name AS customer_name,
                    COALESCE(w.name, '-') AS warehouse_name,
                    o.priority,
                    o.status,
                    COALESCE(u.username, '-') AS dispatcher_name,
                    o.created_at,
                    COALESCE(SUM(oi.qty * oi.unit_price), 0)::INTEGER AS total_amount,
                    COALESCE(SUM(oi.qty), 0)::INTEGER AS total_items
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN warehouses w ON w.id = o.warehouse_id
                LEFT JOIN users u ON u.id = o.dispatcher_id
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE {where_sql}
                GROUP BY o.id, c.name, w.name, u.username
                ORDER BY o.id DESC
                """
            ),
            params,
        )
        items = [dict(row) for row in rows.mappings().all()]

        title_parts = ["orders"]
        if search:
            title_parts.append(f"search-{search}")
        if status:
            title_parts.append(f"status-{status}")
        if start_date:
            title_parts.append(f"from-{start_date}")
        if end_date:
            title_parts.append(f"to-{end_date}")
        title = "_".join(title_parts)

        if export_format == "markdown":
            lines = [
                f"# Orders Export ({len(items)})",
                "",
                "| 订单号 | 客户 | 仓库 | 优先级 | 状态 | 责任调度员 | 创建时间 | 总件数 | 总金额(元) |",
                "|---|---|---|---|---|---|---|---:|---:|",
            ]
            for row in items:
                lines.append(
                    f"| {row['order_no']} | {row['customer_name']} | {row['warehouse_name']} | {row['priority']} | {row['status']} | {row['dispatcher_name']} | {row['created_at']} | {row['total_items']} | {row['total_amount']} |"
                )
            return {
                "filename": f"{title}.md",
                "mime_type": "text/markdown; charset=utf-8",
                "content": "\n".join(lines),
            }

        if export_format == "pdf":
            content = self._build_orders_list_pdf(items)
            return {
                "filename": f"{title}.pdf",
                "mime_type": "application/pdf",
                "content_base64": base64.b64encode(content).decode("utf-8"),
            }

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "order_no",
                "customer",
                "warehouse",
                "priority",
                "status",
                "dispatcher",
                "created_at",
                "total_items",
                "total_amount",
            ]
        )
        for row in items:
            writer.writerow(
                [
                    row["order_no"],
                    row["customer_name"],
                    row["warehouse_name"],
                    row["priority"],
                    row["status"],
                    row["dispatcher_name"],
                    row["created_at"],
                    row["total_items"],
                    row["total_amount"],
                ]
            )
        return {
            "filename": f"{title}.csv",
            "mime_type": "text/csv; charset=utf-8",
            "content": f"\ufeff{buffer.getvalue()}",
        }

    async def export_order_detail(self, order_id: int, export_format: str = "pdf"):
        if export_format != "pdf":
            raise HTTPException(status_code=400, detail="Unsupported export format")
        detail = await self.get_order_detail(order_id)
        content = self._build_order_detail_pdf(detail)
        return {
            "filename": f"order_detail_{detail['order_no']}.pdf",
            "mime_type": "application/pdf",
            "content_base64": base64.b64encode(content).decode("utf-8"),
        }

    @staticmethod
    def _register_cn_font():
        try:
            pdfmetrics.getFont("STSong-Light")
        except KeyError:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    @staticmethod
    def _build_pdf_styles():
        styles = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "title_cn",
                parent=styles["Heading1"],
                fontName="STSong-Light",
                fontSize=18,
                leading=24,
                textColor=colors.HexColor("#1f2937"),
            ),
            "subtitle": ParagraphStyle(
                "subtitle_cn",
                parent=styles["Normal"],
                fontName="STSong-Light",
                fontSize=11,
                leading=16,
                textColor=colors.HexColor("#4b5563"),
            ),
            "cell": ParagraphStyle(
                "cell_cn",
                parent=styles["Normal"],
                fontName="STSong-Light",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#111827"),
            ),
            "meta": ParagraphStyle(
                "meta_cn",
                parent=styles["Normal"],
                fontName="STSong-Light",
                fontSize=10.5,
                leading=15,
                textColor=colors.HexColor("#111827"),
            ),
        }

    @staticmethod
    def _safe_pdf_text(value) -> str:
        if value is None:
            return "-"
        text = str(value)
        text = text.replace("\ufeff", "")
        text = text.replace("\u200b", "")
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _cn_now_str() -> str:
        return datetime.now(ZoneInfo(SYSTEM_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")

    def _build_orders_list_pdf(self, items: List[dict]) -> bytes:
        self._register_cn_font()
        styles = self._build_pdf_styles()
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=28,
            rightMargin=28,
            topMargin=26,
            bottomMargin=26,
            title="订单列表导出",
            author="WMS Dispatch",
        )

        flowables = [
            Paragraph(self._safe_pdf_text("订单列表导出"), styles["title"]),
            Spacer(1, 8),
            Paragraph(f"导出时间：{self._cn_now_str()}　条数：{len(items)}", styles["subtitle"]),
            Spacer(1, 10),
        ]

        table_rows = [["订单号", "客户", "仓库", "优先级", "状态", "责任调度员", "创建时间", "总件数", "总金额(元)"]]
        for row in items:
            table_rows.append(
                [
                    Paragraph(self._safe_pdf_text(row["order_no"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["customer_name"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["warehouse_name"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["priority"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["status"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["dispatcher_name"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["created_at"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["total_items"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(row["total_amount"]), styles["cell"]),
                ]
            )

        table = Table(
            table_rows,
            repeatRows=1,
            colWidths=[72, 66, 58, 40, 52, 62, 84, 40, 58],
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10.5),
                    ("FONTSIZE", (0, 1), (-1, -1), 9.5),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                    ("ALIGN", (7, 1), (8, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flowables.append(table)
        doc.build(flowables)
        return buffer.getvalue()

    def _build_order_detail_pdf(self, detail: dict) -> bytes:
        self._register_cn_font()
        styles = self._build_pdf_styles()
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=28,
            rightMargin=28,
            topMargin=26,
            bottomMargin=26,
            title=f"订单详情-{detail['order_no']}",
            author="WMS Dispatch",
        )

        flowables = [
            Paragraph(self._safe_pdf_text(f"订单详情导出 --- {detail['order_no']}"), styles["title"]),
            Spacer(1, 8),
            Paragraph(f"导出时间：{self._cn_now_str()}", styles["subtitle"]),
            Spacer(1, 8),
        ]

        meta_rows = [
            [Paragraph("<b>订单号</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["order_no"]), styles["meta"])],
            [Paragraph("<b>客户</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["customer_name"]), styles["meta"])],
            [Paragraph("<b>客户联系方式</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["customer_contact"]), styles["meta"])],
            [Paragraph("<b>仓库</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["warehouse_name"]), styles["meta"])],
            [Paragraph("<b>责任调度员</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["dispatcher_name"]), styles["meta"])],
            [Paragraph("<b>状态 / 优先级</b>", styles["meta"]), Paragraph(f"{self._safe_pdf_text(detail['status'])} / {self._safe_pdf_text(detail['priority'])}", styles["meta"])],
            [Paragraph("<b>创建时间</b>", styles["meta"]), Paragraph(self._safe_pdf_text(detail["created_at"]), styles["meta"])],
            [Paragraph("<b>总件数 / 总金额(元)</b>", styles["meta"]), Paragraph(f"{self._safe_pdf_text(detail['total_items'])} / {self._safe_pdf_text(detail['total_amount'])}", styles["meta"])],
        ]
        meta_table = Table(meta_rows, colWidths=[120, 390])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flowables.extend([meta_table, Spacer(1, 12), Paragraph("订单明细", styles["subtitle"]), Spacer(1, 6)])

        detail_rows = [["SKU", "产品名称", "类别", "数量", "单价(元)", "小计(元)"]]
        for item in detail["items"]:
            detail_rows.append(
                [
                    Paragraph(self._safe_pdf_text(item["product_sku"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["product_name"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["product_category"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["qty"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["unit_price"]), styles["cell"]),
                    Paragraph(self._safe_pdf_text(item["subtotal"]), styles["cell"]),
                ]
            )

        detail_table = Table(detail_rows, repeatRows=1, colWidths=[68, 170, 80, 48, 62, 62])
        detail_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
                    ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bfdbfe")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        flowables.append(detail_table)
        doc.build(flowables)
        return buffer.getvalue()
