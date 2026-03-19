"""
音乐源基类 - 定义统一接口
所有音乐源（Spotify、本地文件、YouTube等）都必须实现这个接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import io


class AudioSource(ABC):
    """音乐源基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化音乐源
        
        Args:
            config: 源特定的配置字典
                   例如 Spotify: {"client_id": "...", "client_secret": "..."}
        """
        self.config = config or {}
        self.is_authenticated = False
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        认证音乐源
        
        Returns:
            bool: 认证是否成功
        """
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list:
        """
        搜索音乐
        
        Args:
            query: 搜索关键词（歌曲名、艺术家等）
            limit: 返回结果数量上限
        
        Returns:
            list: 搜索结果列表，每项包含：
                {
                    'id': '音乐唯一ID',
                    'title': '歌曲名',
                    'artist': '艺术家',
                    'duration': 123456,  # 毫秒
                    'source': '来源平台'
                }
        """
        pass
    
    @abstractmethod
    def get_audio_stream(self, music_id: str) -> io.BytesIO:
        """
        获取音频流
        
        Args:
            music_id: 音乐ID
        
        Returns:
            io.BytesIO: 音频二进制流
        
        Raises:
            Exception: 获取失败时抛出异常
        """
        pass
    
    @abstractmethod
    def get_audio_file(self, music_id: str, save_path: str) -> str:
        """
        下载音频文件到本地
        
        Args:
            music_id: 音乐ID
            save_path: 保存路径
        
        Returns:
            str: 保存的文件路径
        """
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(authenticated={self.is_authenticated})"
