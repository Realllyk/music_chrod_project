"""
枚举类定义
定义所有状态枚举
"""

from enum import Enum


class SongStatus(Enum):
    """歌曲状态枚举"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    
    @classmethod
    def values(cls):
        return [e.value for e in cls]


class CaptureStatus(Enum):
    """采集会话状态枚举"""
    READY = 'ready'
    RECORDING_REQUESTED = 'recording_requested'
    RECORDING = 'recording'
    RECORDED = 'recorded'
    TRANSCRIBING = 'transcribing'
    DONE = 'done'
    FAILED = 'failed'
    STOPPED = 'stopped'
    
    @classmethod
    def values(cls):
        return [e.value for e in cls]


class AnalysisType(Enum):
    """分析类型枚举"""
    MELODY = 'melody'
    CHORD = 'chord'
    LYRICS = 'lyrics'
    
    @classmethod
    def values(cls):
        return [e.value for e in cls]
