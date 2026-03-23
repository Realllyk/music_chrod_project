"""
Controllers 包
导出所有 Controller Blueprint
"""

from .home_controller import home_controller
from .songs_controller import songs_controller
from .capture_controller import capture_controller
from .health_controller import health_controller
from .music_controller import music_controller

__all__ = [
    'home_controller',
    'songs_controller',
    'capture_controller',
    'health_controller',
    'music_controller'
]
