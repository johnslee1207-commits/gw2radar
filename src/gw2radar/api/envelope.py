from typing import Any

from pydantic import BaseModel, Field
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiErrorEnvelope(BaseModel):
    ok: bool = False
    error: ApiError


class ApiDataEnvelope(BaseModel):
    ok: bool = True
    data: dict[str, Any]


def error_code_for_status(status_code: int) -> str:
    if status_code == 400:
        return "bad_request"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    if status_code == 422:
        return "validation_error"
    return "http_error"


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    details = {"path": request.url.path}
    if isinstance(exc.detail, dict):
        detail_payload = dict(exc.detail)
        message = str(detail_payload.pop("message", "Request failed."))
        code = str(detail_payload.pop("code", error_code_for_status(exc.status_code)))
        details.update(detail_payload)
    else:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        code = error_code_for_status(exc.status_code)
    envelope = ApiErrorEnvelope(
        error=ApiError(
            code=code,
            message=message,
            details=details,
        )
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump(mode="json"))
