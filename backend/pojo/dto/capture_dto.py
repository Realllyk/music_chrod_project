from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from pojo.dto.base import BaseDTO


class StartSessionDTO(BaseDTO):
    source: str = Field('system_loopback', min_length=1, description='采集来源')


class SessionIdDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='会话 ID')


class SessionIdPathDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='路径中的会话 ID')


class ListSessionsQueryDTO(BaseDTO):
    limit: int = Field(50, ge=1, le=100, description='分页大小')
    offset: int = Field(0, ge=0, description='分页偏移量')
    status: str | None = Field(None, min_length=1, description='状态过滤')
    source: str | None = Field(None, min_length=1, description='来源过滤')


class UpdateSessionDTO(BaseDTO):
    audio_name: str | None = Field(None, min_length=1, description='录音文件名')
    source: str | None = Field(None, min_length=1, description='采集来源')
    status: str | None = Field(None, min_length=1, description='会话状态')

    @model_validator(mode='after')
    def _validate_non_empty_update(self) -> 'UpdateSessionDTO':
        if self.audio_name is None and self.source is None and self.status is None:
            raise ValueError('至少提供一个可更新字段')
        return self


class RequestRecordingDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='目标会话 ID')


class StartRecordingDTO(BaseDTO):
    source: str = Field('system_loopback', min_length=1, description='采集来源')


class StopRecordingDTO(BaseDTO):
    session_id: str | None = Field(None, min_length=1, description='会话 ID')
    audio_name: str | None = Field(None, min_length=1, description='录音文件名')


class SaveRecordingDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='会话 ID')
    audio_name: str = Field(..., min_length=1, description='录音文件名')


class RegisterFileDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='会话 ID')
    audio_name: str | None = Field(None, min_length=1, description='文件名')
    file_path: str | None = Field(None, min_length=1, description='文件存储路径')
    duration_sec: float | None = Field(None, ge=0, description='时长（秒）')
    sample_rate: int | None = Field(None, gt=0, description='采样率')
    channels: int | None = Field(None, ge=1, description='声道数')


class UploadFileDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='会话 ID')
    audio_file: Any = Field(..., description='上传的音频文件对象')
    audio_name: str | None = Field(None, min_length=1, description='自定义音频名称')

    @model_validator(mode='after')
    def _validate_file(self) -> 'UploadFileDTO':
        if self.audio_file is None:
            raise ValueError('audio_file is required')
        filename = getattr(self.audio_file, 'filename', '') or ''
        if not filename.strip():
            raise ValueError('audio_file filename is empty')
        return self


class RecordingFilePathDTO(BaseDTO):
    filename: str = Field(..., min_length=1, description='录音文件名')

    @field_validator('filename')
    @classmethod
    def _validate_filename(cls, value: str) -> str:
        if '..' in value or '/' in value or '\\' in value:
            raise ValueError('filename 非法，禁止路径穿越')
        return value


class ListRecordingsQueryDTO(BaseDTO):
    limit: int = Field(100, ge=1, le=200, description='返回条数')
    offset: int = Field(0, ge=0, description='偏移量')
    session_id: str | None = Field(None, min_length=1, description='会话过滤')
    audio_name: str | None = Field(None, min_length=1, description='文件名过滤')
