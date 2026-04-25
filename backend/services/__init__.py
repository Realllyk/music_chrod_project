"""
Services 包
导出所有 Service 类
"""

from .songs_service import SongsService
from .capture_service import CaptureService
from .artists_service import ArtistsService
from .transcribe_service import TranscribeService

__all__ = ['SongsService', 'CaptureService', 'ArtistsService', 'TranscribeService']
