from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.dependencies import get_db_session
from modules.worker.services import WorkerService


def get_worker_service(session: AsyncSession = Depends(get_db_session)) -> WorkerService:
    return WorkerService(session)
