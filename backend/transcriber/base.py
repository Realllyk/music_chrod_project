"""
提取器基类定义
使用 ABC (Abstract Base Class) 实现接口约束
"""

from abc import ABC, abstractmethod
from enum import Enum


class AnalysisType(Enum):
    """分析类型枚举"""
    MELODY = 'melody'
    CHORD = 'chord'


class TranscriberBase(ABC):
    """顶层抽象基类"""
    
    @property
    @abstractmethod
    def analysis_type(self) -> AnalysisType:
        """必须返回分析类型枚举"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """算法名称"""
        pass
    
    @abstractmethod
    def extract(self, audio_path: str) -> dict:
        """提取旋律或和弦
        Returns:
            {
                'notes': [...],
                'midi_path': str,
            }
        """
        pass


class MelodyTranscriberBase(TranscriberBase):
    """单旋律提取抽象类"""
    
    @property
    def analysis_type(self) -> AnalysisType:
        return AnalysisType.MELODY
    
    @abstractmethod
    def extract_melody(self, audio_path: str) -> dict:
        """提取单旋律"""
        pass
    
    def extract(self, audio_path: str) -> dict:
        return self.extract_melody(audio_path)


class ChordTranscriberBase(TranscriberBase):
    """和弦分离抽象类"""
    
    @property
    def analysis_type(self) -> AnalysisType:
        return AnalysisType.CHORD
    
    @abstractmethod
    def extract_chords(self, audio_path: str) -> dict:
        """提取和弦"""
        pass
    
    def extract(self, audio_path: str) -> dict:
        return self.extract_chords(audio_path)
