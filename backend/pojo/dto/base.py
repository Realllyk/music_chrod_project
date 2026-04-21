from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Literal, Type, TypeVar

from flask import request
from pydantic import BaseModel, ConfigDict

T = TypeVar('T', bound='BaseDTO')
Source = Literal['json', 'form', 'query', 'path']


class BaseDTO(BaseModel):
    """所有入参 / 后端内部传参 DTO 的基类。"""

    model_config = ConfigDict(
        extra='ignore',
        str_strip_whitespace=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    @classmethod
    def from_json(cls: Type[T], data: dict[str, Any] | None) -> T:
        return cls.model_validate(data or {})

    @classmethod
    def from_form(cls: Type[T], form: Any, files: Any = None) -> T:
        payload: dict[str, Any] = form.to_dict() if hasattr(form, 'to_dict') else dict(form or {})
        if files is not None:
            file_keys = files.keys() if hasattr(files, 'keys') else files
            for key in file_keys:
                if hasattr(files, 'getlist'):
                    values = files.getlist(key)
                    payload[key] = values if len(values) > 1 else files.get(key)
                else:
                    payload[key] = files.get(key)
        return cls.model_validate(payload)

    @classmethod
    def from_query(cls: Type[T], args: Any) -> T:
        payload: dict[str, Any] = args.to_dict() if hasattr(args, 'to_dict') else dict(args or {})
        return cls.model_validate(payload)

    @classmethod
    def from_path(cls: Type[T], kwargs: dict[str, Any] | None) -> T:
        return cls.model_validate(kwargs or {})


def use_dto(dto_cls: Type[BaseDTO], source: Source = 'json', arg_name: str = 'dto') -> Callable:
    """把 request 解析/校验成 DTO，注入 controller 函数。"""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            resolved = source
            content_type = request.content_type or ''
            if source == 'json' and 'multipart/form-data' in content_type:
                resolved = 'form'

            if resolved == 'json':
                dto = dto_cls.from_json(request.get_json(silent=True))
            elif resolved == 'form':
                dto = dto_cls.from_form(request.form, request.files)
            elif resolved == 'query':
                dto = dto_cls.from_query(request.args)
            elif resolved == 'path':
                dto = dto_cls.from_path(kwargs)
            else:
                raise ValueError(f'Unsupported dto source: {resolved}')

            kwargs[arg_name] = dto
            return fn(*args, **kwargs)

        return wrapper

    return decorator
