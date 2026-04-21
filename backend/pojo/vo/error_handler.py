from __future__ import annotations

import logging

from flask import Flask
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from pojo.vo.exceptions import BizException
from pojo.vo.result import Result

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    """集中注册：业务异常 / 参数校验 / HTTP 异常 / 兜底异常。"""

    @app.errorhandler(BizException)
    def _handle_biz(exc: BizException):
        return Result.fail(exc.code, exc.description).to_response()

    @app.errorhandler(ValidationError)
    def _handle_validation(exc: ValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = '.'.join(str(x) for x in first.get('loc', []))
        msg = first.get('msg', 'validation error')
        description = f'参数校验失败: {loc} {msg}'.strip()
        return Result.fail(400, description, data={'errors': errors}).to_response()

    @app.errorhandler(HTTPException)
    def _handle_http(exc: HTTPException):
        return Result.fail(exc.code or 500, exc.description or exc.name).to_response()

    @app.errorhandler(Exception)
    def _handle_uncaught(exc: Exception):
        logger.exception('Unhandled exception')
        return Result.server_error(f'{type(exc).__name__}: {exc}').to_response()
