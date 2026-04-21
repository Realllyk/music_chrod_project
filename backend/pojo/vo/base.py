from __future__ import annotations

from typing import Any, Type, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar('T', bound='BaseVO')


class BaseVO(BaseModel):
    """所有响应 VO 的基类。"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
    )

    @classmethod
    def from_domain(cls: Type[T], domain: Any, **extra: Any) -> T:
        if isinstance(domain, dict):
            return cls.model_validate({**domain, **extra})
        if extra:
            return cls.model_validate({**extra, **cls.model_validate(domain).model_dump()})
        return cls.model_validate(domain)

    @classmethod
    def from_domain_list(cls: Type[T], items: list[Any], **extra: Any) -> list[T]:
        return [cls.from_domain(item, **extra) for item in items]
