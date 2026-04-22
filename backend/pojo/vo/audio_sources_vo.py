from __future__ import annotations

from pojo.vo.base import BaseVO


class AudioSourceVO(BaseVO):
    id: int | None = None
    source_type: str | None = None
    source_id: str | int | None = None
    audio_name: str | None = None
    file_path: str | None = None
    file_size: int | None = None
    duration_sec: int | float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    format: str | None = None
    status: str | None = None
    created_at: str | None = None

    @classmethod
    def from_domain(cls, source: dict | tuple | None, **extra):
        if not source:
            return None
        if isinstance(source, tuple):
            source = {
                'id': source[0] if len(source) > 0 else None,
                'source_type': source[1] if len(source) > 1 else None,
                'source_id': source[2] if len(source) > 2 else None,
                'audio_name': source[3] if len(source) > 3 else None,
                'file_path': source[4] if len(source) > 4 else None,
                'file_size': source[5] if len(source) > 5 else None,
                'duration_sec': source[6] if len(source) > 6 else None,
                'sample_rate': source[7] if len(source) > 7 else None,
                'channels': source[8] if len(source) > 8 else None,
                'format': source[9] if len(source) > 9 else None,
                'status': source[11] if len(source) > 11 else None,
                'created_at': str(source[13]) if len(source) > 13 and source[13] else None,
            }
        elif isinstance(source, dict) and source.get('created_at') is not None:
            source = {**source, 'created_at': str(source.get('created_at'))}
        return super().from_domain(source, **extra)
