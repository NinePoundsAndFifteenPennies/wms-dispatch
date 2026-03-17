from fastapi import APIRouter

from modules.shared.response import success

router = APIRouter()


@router.get('/health', tags=['system'], summary='Health check')
async def health_check():
    return success(data={'status': 'ok'})
