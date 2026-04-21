from __future__ import annotations

from typing import Optional

from services.file_service import FileService

from pojo.vo.base import BaseVO


class AddSongVO(BaseVO):
    song_id: int
    audio_path: Optional[str] = None


class SongVO(BaseVO):
    id: int
    title: Optional[str] = None
    artist_id: Optional[int] = None
    artist_name: Optional[str] = None
    category: Optional[str] = None
    duration: Optional[float] = None
    source: Optional[str] = None
    source_id: Optional[str] = None
    session_id: Optional[str] = None
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    melody_path: Optional[str] = None
    melody_url: Optional[str] = None
    melody_key: Optional[str] = None
    chord_path: Optional[str] = None
    chord_url: Optional[str] = None
    chord_key: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_domain(cls, song: dict, **extra) -> 'SongVO | None':
        if not song:
            return None
        return cls(
            id=song.get('id'),
            title=song.get('title'),
            artist_id=song.get('artist_id'),
            artist_name=song.get('artist_name'),
            category=song.get('category'),
            duration=song.get('duration'),
            source=song.get('source'),
            source_id=song.get('source_id'),
            session_id=song.get('session_id'),
            audio_path=song.get('audio_path'),
            audio_url=FileService.resolve_public_url(song.get('audio_path')) if song.get('audio_path') else None,
            melody_path=song.get('melody_path'),
            melody_url=FileService.resolve_public_url(song.get('melody_path')) if song.get('melody_path') else None,
            melody_key=song.get('melody_key'),
            chord_path=song.get('chord_path'),
            chord_url=FileService.resolve_public_url(song.get('chord_path')) if song.get('chord_path') else None,
            chord_key=song.get('chord_key'),
            status=song.get('status'),
            created_at=song.get('created_at').isoformat() if song.get('created_at') else None,
            updated_at=song.get('updated_at').isoformat() if song.get('updated_at') else None,
            **extra,
        )
