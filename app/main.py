import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import slowapi.middleware as _slowapi_mw

from .database import init_db
from .routes import (
    service_root, account_service, session_service, systems, chassis, managers,
    event_service, update_service, task_service, telemetry_service,
    certificate_service, json_schemas, registries, cables, aggregation_service,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

_ODATA_HEADERS = {'OData-Version': '4.0'}


def _error_body(code: str, message: str) -> dict:
    return {'error': {'code': code, 'message': message, '@Message.ExtendedInfo': []}}


async def _redfish_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        _error_body('Base.1.0.ServiceTemporarilyUnavailable', 'Too many requests. Please retry after a moment.'),
        status_code=429,
        headers=_ODATA_HEADERS,
    )

# SlowAPIMiddleware が内部でこのハンドラーを使うよう上書き
_slowapi_mw._rate_limit_exceeded_handler = _redfish_rate_limit_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


limiter = Limiter(key_func=get_remote_address, default_limits=['600/minute'])

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter

cors_origins = os.environ.get('CORS_ORIGINS', '*')
origins = [o.strip() for o in cors_origins.split(',')] if cors_origins != '*' else ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['*'],
)
app.add_middleware(SlowAPIMiddleware)


@app.middleware('http')
async def log_requests(request: Request, call_next):
    logger.info('%s %s', request.method, request.url.path)
    response = await call_next(request)
    logger.info('%s %s -> %s', request.method, request.url.path, response.status_code)
    return response


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        headers = dict(exc.headers or {})
        headers['OData-Version'] = '4.0'
        return JSONResponse(exc.detail, status_code=exc.status_code, headers=headers)
    return JSONResponse(
        _error_body('Base.1.0.GeneralError', str(exc.detail)),
        status_code=exc.status_code,
        headers=_ODATA_HEADERS,
    )


@app.exception_handler(RateLimitExceeded)
async def handle_429(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        _error_body('Base.1.0.ServiceTemporarilyUnavailable', 'Too many requests. Please retry after a moment.'),
        status_code=429,
        headers=_ODATA_HEADERS,
    )


@app.exception_handler(404)
async def handle_404(request: Request, exc: Exception):
    return JSONResponse(
        _error_body('Base.1.0.ResourceNotFound', 'The requested resource was not found.'),
        status_code=404,
        headers=_ODATA_HEADERS,
    )


@app.exception_handler(405)
async def handle_405(request: Request, exc: Exception):
    return JSONResponse(
        _error_body('Base.1.0.OperationNotAllowed', 'The HTTP method is not allowed for this resource.'),
        status_code=405,
        headers=_ODATA_HEADERS,
    )


@app.exception_handler(500)
async def handle_500(request: Request, exc: Exception):
    return JSONResponse(
        _error_body('Base.1.0.InternalError', 'An internal error has occurred.'),
        status_code=500,
        headers=_ODATA_HEADERS,
    )


for _router in [
    service_root.router,
    account_service.router,
    session_service.router,
    systems.router,
    chassis.router,
    managers.router,
    event_service.router,
    update_service.router,
    task_service.router,
    telemetry_service.router,
    certificate_service.router,
    json_schemas.router,
    registries.router,
    cables.router,
    aggregation_service.router,
]:
    app.include_router(_router)
