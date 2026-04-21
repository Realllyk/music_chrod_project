from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from flask import Response, jsonify
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class Result(BaseModel, Generic[T]):
    """统一响应体 wrapper。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    code: int = 200
    description: str = 'success'
    result: Optional[T] = None

    @classmethod
    def success(cls, data: Any = None, description: str = 'success') -> 'Result[Any]':
        return cls(code=200, description=description, result=data)

    @classmethod
    def fail(cls, code: int, description: str, data: Any = None) -> 'Result[Any]':
        return cls(code=code, description=description, result=data)

    @classmethod
    def not_found(cls, description: str = 'Not found') -> 'Result[Any]':
        return cls(code=404, description=description, result=None)

    @classmethod
    def bad_request(cls, description: str = 'Bad request', data: Any = None) -> 'Result[Any]':
        return cls(code=400, description=description, result=data)

    @classmethod
    def server_error(cls, description: str = 'Internal server error') -> 'Result[Any]':
        return cls(code=500, description=description, result=None)

    def to_response(self) -> tuple[Response, int]:
        http_status = 200 if 200 <= self.code < 400 else self.code
        return jsonify(self.model_dump(mode='json')), http_status


class PageVO(BaseModel, Generic[T]):
    """分页结构，作为 Result.result 的典型形态之一。"""

    items: list[T]
    total: int
    limit: Optional[int] = None
    offset: Optional[int] = None
