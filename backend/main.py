from fastapi import FastAPI

from api.router import router as api_router

app = FastAPI(
    title='WMS Dispatch API',
    version='0.1.0',
    description='Warehouse dispatch backend APIs.',
)

app.include_router(api_router, prefix='/api')


@app.get('/', tags=['system'], summary='Service info')
async def root() -> dict[str, str]:
    return {'service': 'wms-dispatch-backend', 'docs': '/docs'}
