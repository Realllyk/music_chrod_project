from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from werkzeug.datastructures import FileStorage

from .base import BaseDTO


class ListAudioSourcesQueryDTO(BaseDTO):
    limit: int = Field(default=100, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class AudioSourceIdPathDTO(BaseDTO):
    audio_id: int = Field(alias='audio_id', gt=0)


class UploadAudioSourceDTO(BaseDTO):
    audio_name: str = Field(min_length=1, max_length=255)
    audio_file: FileStorage

    @model_validator(mode='after')
    def _validate_file(self) -> 'UploadAudioSourceDTO':
        if not self.audio_file or not getattr(self.audio_file, 'filename', ''):
            raise ValueError('请选择音频文件')
        return self


class FileOssUrlQueryDTO(BaseDTO):
    song_id: int | None = Field(default=None, gt=0)
    session_id: str | None = None
    audio_source_id: int | None = Field(default=None, gt=0)
    type: Literal['audio', 'melody', 'chord', 'recording', 'source'] | None = None

    @model_validator(mode='after')
    def _validate_one_resource(self) -> 'FileOssUrlQueryDTO':
        provided = [value for value in (self.song_id, self.session_id, self.audio_source_id) if value]
        if len(provided) != 1:
            raise ValueError('Exactly one of song_id, session_id, audio_source_id is required')
        return self
