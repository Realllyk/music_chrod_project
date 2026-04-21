"""DTO 基础设施导出。

用法示例：
    from pojo.dto import BaseDTO, use_dto

    @use_dto(MyDTO, source='json')
    def create(dto: MyDTO):
        ...
"""

from .base import BaseDTO, use_dto

__all__ = ['BaseDTO', 'use_dto']
