from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from .base import BaseDTO


class ListArtistsQueryDTO(BaseDTO):
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class ArtistIdPathDTO(BaseDTO):
    artist_id: int = Field(..., gt=0)


class AddArtistDTO(BaseDTO):
    name: str = Field(..., min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=5000)
    avatar: Any = None


class UpdateArtistDTO(BaseDTO):
    name: str | None = Field(None, min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=5000)

    @model_validator(mode='after')
    def _check_any_field_provided(self) -> 'UpdateArtistDTO':
        if self.name is None and self.bio is None:
            raise ValueError('name 或 bio 至少提供一个')
        return self


class AvatarUploadDTO(BaseDTO):
    avatar: Any

    @model_validator(mode='after')
    def _check_avatar_required(self) -> 'AvatarUploadDTO':
        avatar = self.avatar
        if avatar is None or not getattr(avatar, 'filename', ''):
            raise ValueError('avatar file is required')
        return self
