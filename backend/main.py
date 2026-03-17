import logging

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from api.router import router as api_router
from modules.auth.dependencies import inject_current_user_from_token
from modules.shared.response import failure, success

app = FastAPI(
    title='WMS Dispatch API',
    version='0.1.0',
    description='Warehouse dispatch backend APIs.',
)

app.include_router(api_router, prefix='/api')
logger = logging.getLogger(__name__)


@app.middleware('http')
async def exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.error('Unhandled server error', exc_info=True)
        return failure(message='internal server error', code=500)


@app.middleware('http')
async def jwt_middleware(request: Request, call_next):
    return await inject_current_user_from_token(request, call_next)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return failure(message=str(exc.detail), code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return failure(message='validation error', code=422, data=exc.errors())


@app.get('/', tags=['system'], summary='Service info')
async def root():
    return success(data={'service': 'wms-dispatch-backend', 'docs': '/docs'})
