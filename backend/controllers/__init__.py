"""
Controllers 包
导出所有 Controller Blueprint
"""

from .home_controller import home_controller
from .songs_controller import songs_controller
from .capture_controller import capture_controller
from .health_controller import health_controller
from .artists_controller import artists_controller
from .transcribe_controller import transcribe_controller
from .audio_sources_controller import audio_sources_controller
from .sources_controller import sources_controller
from .music_controller import music_controller

__all__ = [
    'home_controller',
    'songs_controller',
    'capture_controller',
    'health_controller',
    'artists_controller',
    'transcribe_controller',
    'audio_sources_controller',
    'sources_controller',
    'music_controller',
]
