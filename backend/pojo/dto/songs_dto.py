from __future__ import annotations

from pydantic import Field

from pojo.dto.base import BaseDTO


class AddSongDTO(BaseDTO):
    title: str | None = Field(None, max_length=200)
    artist_id: int | None = Field(None, gt=0)
    category: str | None = Field(None, max_length=100)
    audio_source_id: int = Field(..., gt=0)


class ListSongsQueryDTO(BaseDTO):
    keyword: str = Field('', max_length=100)
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class SongIdPathDTO(BaseDTO):
    song_id: int = Field(..., gt=0)
