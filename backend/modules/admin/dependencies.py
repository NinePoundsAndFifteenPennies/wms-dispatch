from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.dependencies import get_db_session
from modules.admin.services import AdminService

def get_admin_service(session: AsyncSession = Depends(get_db_session)) -> AdminService:
    return AdminService(session)
