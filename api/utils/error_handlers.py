from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from utils.exceptions import BaseAppException, InvalidRequestException
from utils.logger import get_logger

log = get_logger(__name__)


def _error(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


async def app_exception_handler(_: Request, exc: BaseAppException) -> JSONResponse:
    log.warning("app_error code=%s message=%s", exc.error_code, exc.message)
    return _error(exc.http_status, exc.error_code, exc.message, exc.details)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"campo": ".".join(str(p) for p in err["loc"]), "erro": err["msg"]}
        for err in exc.errors()
    ]
    invalid = InvalidRequestException({"fields": fields})
    return _error(invalid.http_status, invalid.error_code, invalid.message, invalid.details)


async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_error", exc_info=exc)  # the traceback stays in the logs
    return _error(500, "INTERNAL_SERVER_ERROR", "Erro interno do servidor")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BaseAppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
