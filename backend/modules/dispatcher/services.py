from sqlalchemy.ext.asyncio import AsyncSession

from modules.agent.service.dispatch_agent_service import DispatcherAgentServiceMixin
from modules.dispatcher.service.inventory_service import DispatcherInventoryServiceMixin
from modules.dispatcher.service.order_service import DispatcherOrderServiceMixin
from modules.dispatcher.service.transfer_service import DispatcherTransferServiceMixin
from modules.dispatcher.service.work_order_service import DispatcherWorkOrderServiceMixin
from modules.shared.config import settings


class DispatcherService(
    DispatcherOrderServiceMixin,
    DispatcherInventoryServiceMixin,
    DispatcherWorkOrderServiceMixin,
    DispatcherAgentServiceMixin,
    DispatcherTransferServiceMixin,
):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.active_work_order_limit = settings.dispatcher_active_work_order_limit
