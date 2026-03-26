from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success(data=None, message: str = 'ok', code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content=jsonable_encoder({'code': code, 'message': message, 'data': data}),
    )


def failure(message: str = 'internal server error', code: int = 500, data=None) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content=jsonable_encoder({'code': code, 'message': message, 'data': data}),
    )
