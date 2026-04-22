from __future__ import annotations

from .base import BaseVO


class ArtistVO(BaseVO):
    id: int
    name: str
    avatar: str | None = None
    bio: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_domain(cls, artist: dict, **extra) -> 'ArtistVO | None':
        if not artist:
            return None
        return cls(
            id=artist.get('id'),
            name=artist.get('name'),
            avatar=artist.get('avatar'),
            bio=artist.get('bio'),
            created_at=artist.get('created_at').isoformat() if artist.get('created_at') else None,
            updated_at=artist.get('updated_at').isoformat() if artist.get('updated_at') else None,
        )
