"""DTO 基础设施导出。

用法示例：
    from pojo.dto import BaseDTO, use_dto

    @use_dto(MyDTO, source='json')
    def create(dto: MyDTO):
        ...
"""

from .base import BaseDTO, use_dto
from .capture_dto import (
    ListRecordingsQueryDTO,
    ListSessionsQueryDTO,
    RecordingFilePathDTO,
    RegisterFileDTO,
    RequestRecordingDTO,
    SaveRecordingDTO,
    SessionIdDTO,
    SessionIdPathDTO,
    StartRecordingDTO,
    StartSessionDTO,
    StopRecordingDTO,
    UpdateSessionDTO,
    UploadFileDTO,
)

__all__ = [
    'BaseDTO',
    'use_dto',
    'StartSessionDTO',
    'SessionIdDTO',
    'SessionIdPathDTO',
    'ListSessionsQueryDTO',
    'UpdateSessionDTO',
    'RequestRecordingDTO',
    'StartRecordingDTO',
    'StopRecordingDTO',
    'SaveRecordingDTO',
    'RegisterFileDTO',
    'UploadFileDTO',
    'RecordingFilePathDTO',
    'ListRecordingsQueryDTO',
]
