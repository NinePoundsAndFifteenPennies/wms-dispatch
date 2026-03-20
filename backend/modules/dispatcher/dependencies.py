from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.dependencies import get_db_session
from modules.dispatcher.services import DispatcherService


def get_dispatcher_service(session: AsyncSession = Depends(get_db_session)) -> DispatcherService:
    return DispatcherService(session)
