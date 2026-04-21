from __future__ import annotations

from typing import Optional

from pojo.vo.base import BaseVO


class StartTranscribeVO(BaseVO):
    task_id: str
    status: Optional[str] = None


class TranscribeTaskVO(BaseVO):
    task_id: str
    song_id: int
    mode: str
    status: str
    progress: Optional[int] = None
    result_path: Optional[str] = None
    error: Optional[str] = None
    vocal_stem_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_domain(cls, task: dict, **extra) -> 'TranscribeTaskVO | None':
        if not task:
            return None
        return cls(
            task_id=task.get('task_id'),
            song_id=task.get('song_id'),
            mode=task.get('mode'),
            status=task.get('status'),
            progress=task.get('progress'),
            result_path=task.get('result_path'),
            error=task.get('error'),
            vocal_stem_path=task.get('vocal_stem_path'),
            created_at=task.get('created_at').isoformat() if task.get('created_at') else None,
            updated_at=task.get('updated_at').isoformat() if task.get('updated_at') else None,
            **extra,
        )


class SongTranscribeTasksVO(BaseVO):
    song_id: int
    tasks: list[TranscribeTaskVO]
