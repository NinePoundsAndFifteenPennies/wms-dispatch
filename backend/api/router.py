from fastapi import APIRouter

from modules.auth.router import router as auth_router
from modules.admin.router import router as admin_router
from modules.dispatcher.router import router as dispatcher_router
from modules.worker.router import router as worker_router
from modules.shared.response import success

router = APIRouter()
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(dispatcher_router)
router.include_router(worker_router)

@router.get('/health', tags=['system'], summary='Health check')
async def health_check():
    return success(data={'status': 'ok'})
