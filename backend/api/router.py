from fastapi import APIRouter

router = APIRouter()


@router.get('/health', tags=['system'], summary='Health check')
async def health_check() -> dict[str, str]:
    return {'status': 'ok'}
