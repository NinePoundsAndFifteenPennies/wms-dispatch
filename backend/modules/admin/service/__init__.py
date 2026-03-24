from .base import AdminServiceBase, SYSTEM_TIMEZONE, get_password_hash
from .customers import CustomerServiceMixin
from .dashboard import DashboardServiceMixin
from .orders import OrderServiceMixin
from .products import ProductServiceMixin
from .users import UserServiceMixin
from .warehouses import WarehouseServiceMixin
from .work_orders import WorkOrderServiceMixin


class AdminService(
    AdminServiceBase,
    WorkOrderServiceMixin,
    DashboardServiceMixin,
    UserServiceMixin,
    WarehouseServiceMixin,
    CustomerServiceMixin,
    OrderServiceMixin,
    ProductServiceMixin,
):
    pass


__all__ = ["AdminService", "SYSTEM_TIMEZONE", "get_password_hash"]
