"""
音乐源模块
支持可切换的音乐输入源
"""

from .base import AudioSource
from .spotify import SpotifySource
from .local_file import LocalFileSource


class SourceFactory:
    """音乐源工厂 - 管理和切换不同的音乐源"""
    
    _sources = {
        'spotify': SpotifySource,
        'local_file': LocalFileSource,
    }
    
    _current_source = None
    
    @classmethod
    def register_source(cls, name: str, source_class):
        """
        注册新的音乐源
        
        Args:
            name: 源名称（如 'youtube'）
            source_class: 源类（必须继承 AudioSource）
        """
        if not issubclass(source_class, AudioSource):
            raise TypeError(f"{source_class} 必须继承 AudioSource")
        cls._sources[name] = source_class
        print(f"✓ 已注册音乐源: {name}")
    
    @classmethod
    def create(cls, source_name: str, config=None) -> AudioSource:
        """
        创建音乐源实例
        
        Args:
            source_name: 源名称（'spotify', 'local_file' 等）
            config: 源配置字典
        
        Returns:
            AudioSource: 音乐源实例
        
        Raises:
            ValueError: 未知的源名称
        """
        if source_name not in cls._sources:
            raise ValueError(f"未知的音乐源: {source_name}。可用源: {list(cls._sources.keys())}")
        
        source_class = cls._sources[source_name]
        return source_class(config)
    
    @classmethod
    def get_available_sources(cls) -> list:
        """获取所有可用的音乐源"""
        return list(cls._sources.keys())
    
    @classmethod
    def set_current(cls, source_name: str, config=None) -> AudioSource:
        """
        切换当前使用的音乐源
        
        Args:
            source_name: 源名称
            config: 源配置
        
        Returns:
            AudioSource: 当前使用的音乐源
        """
        cls._current_source = cls.create(source_name, config)
        print(f"✓ 已切换到音乐源: {source_name}")
        return cls._current_source
    
    @classmethod
    def get_current(cls) -> AudioSource:
        """获取当前使用的音乐源"""
        if cls._current_source is None:
            raise RuntimeError("未设置音乐源，请先调用 set_current()")
        return cls._current_source


__all__ = ['AudioSource', 'SpotifySource', 'LocalFileSource', 'SourceFactory']
