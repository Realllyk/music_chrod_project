from __future__ import annotations

from pojo.vo.base import BaseVO


class CaptureSessionVO(BaseVO):
    session_id: str
    source: str | None = None
    status: str | None = None
    audio_name: str | None = None
    file_path: str | None = None
    duration_sec: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_domain(cls, session: dict | None, **extra) -> 'CaptureSessionVO | None':
        if not session:
            return None
        return cls(
            session_id=session.get('session_id'),
            source=session.get('source'),
            status=session.get('status'),
            audio_name=session.get('audio_name'),
            file_path=session.get('file_path'),
            duration_sec=session.get('duration_sec'),
            sample_rate=session.get('sample_rate'),
            channels=session.get('channels'),
            created_at=session.get('created_at').isoformat() if session.get('created_at') else None,
            updated_at=session.get('updated_at').isoformat() if session.get('updated_at') else None,
            **extra,
        )


class ActiveCaptureSessionVO(BaseVO):
    session_id: str | None = None
    status: str | None = None
    source: str | None = None


class StartSessionVO(BaseVO):
    session_id: str
    status: str
    source: str
    created_at: str | None = None


class DeleteSessionVO(BaseVO):
    session_id: str
    deleted: bool


class UpdateSessionResultVO(BaseVO):
    session_id: str
    audio_name: str | None = None
    source: str | None = None
    status: str | None = None


class RecordingActionVO(BaseVO):
    session_id: str
    status: str
    message: str | None = None


class SaveRecordingVO(BaseVO):
    session_id: str
    audio_name: str


class RegisterFileVO(BaseVO):
    session_id: str
    status: str
    audio_name: str | None = None
    file_path: str | None = None


class RecordingVO(BaseVO):
    session_id: str
    audio_name: str | None = None
    file_path: str | None = None
    duration_sec: float | None = None
    created_at: str | None = None

    @classmethod
    def from_domain(cls, session: dict | None, **extra) -> 'RecordingVO | None':
        if not session:
            return None
        return cls(
            session_id=session.get('session_id'),
            audio_name=session.get('audio_name'),
            file_path=session.get('file_path'),
            duration_sec=session.get('duration_sec'),
            created_at=session.get('created_at').isoformat() if session.get('created_at') else None,
            **extra,
        )
