from __future__ import annotations

from typing import Literal

from pydantic import Field

from pojo.dto.base import BaseDTO


class StartTranscribeDTO(BaseDTO):
    song_id: int = Field(..., gt=0, description='目标歌曲 ID')
    mode: Literal['melody', 'chord'] = Field('melody', description='提取模式')


class TranscribeTaskQueryDTO(BaseDTO):
    task_id: str = Field(..., min_length=1, description='转写任务 ID')


class SongTasksQueryDTO(BaseDTO):
    song_id: int = Field(..., gt=0, description='歌曲 ID')
