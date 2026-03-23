"""
Services 包
导出所有 Service 类
"""

from .songs_service import SongsService
from .capture_service import CaptureService

__all__ = ['SongsService', 'CaptureService']
