"""
本地文件音乐源实现
"""

import io
import os
from pathlib import Path
from typing import Optional, Dict, Any
from .base import AudioSource


class LocalFileSource(AudioSource):
    """本地文件音乐源"""
    
    SUPPORTED_FORMATS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma'}
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化本地文件源
        
        config 可以包含：
        {
            'music_dir': '/path/to/music',  # 音乐文件夹路径
            'recursive': True               # 是否递归搜索子文件夹
        }
        """
        super().__init__(config)
        self.music_dir = config.get('music_dir', os.path.expanduser('~/Music'))
        self.recursive = config.get('recursive', True)
        self.is_authenticated = True  # 本地文件不需要认证
    
    def authenticate(self) -> bool:
        """本地文件不需要认证"""
        return True
    
    def search(self, query: str, limit: int = 10) -> list:
        """
        在本地文件夹中搜索音乐
        
        Args:
            query: 搜索词（文件名）
            limit: 返回结果数
        
        Returns:
            list: 搜索结果
        """
        try:
            if not os.path.exists(self.music_dir):
                print(f"✗ 音乐文件夹不存在: {self.music_dir}")
                return []
            
            results = []
            search_term = query.lower()
            
            # 搜索文件
            if self.recursive:
                file_pattern = f"**/*"
            else:
                file_pattern = "*"
            
            music_path = Path(self.music_dir)
            for file_path in music_path.glob(file_pattern):
                # 检查是否是支持的音乐文件
                if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                    filename = file_path.stem  # 不含扩展名的文件名
                    
                    # 模糊搜索
                    if search_term in filename.lower():
                        results.append({
                            'id': str(file_path),
                            'title': filename,
                            'artist': 'Local',
                            'duration': 0,  # 本地文件需要读取来获取时长
                            'format': file_path.suffix.lower(),
                            'source': 'local_file',
                            'path': str(file_path)
                        })
                        
                        if len(results) >= limit:
                            break
            
            return results
        
        except Exception as e:
            print(f"✗ 搜索失败: {e}")
            return []
    
    def get_audio_stream(self, music_id: str) -> io.BytesIO:
        """
        获取本地音频文件流
        
        Args:
            music_id: 文件路径
        
        Returns:
            io.BytesIO: 音频流
        """
        try:
            if not os.path.exists(music_id):
                raise FileNotFoundError(f"文件不存在: {music_id}")
            
            with open(music_id, 'rb') as f:
                return io.BytesIO(f.read())
        
        except Exception as e:
            print(f"✗ 获取音频流失败: {e}")
            raise
    
    def get_audio_file(self, music_id: str, save_path: str) -> str:
        """
        复制本地音频文件到指定位置
        
        Args:
            music_id: 源文件路径
            save_path: 目标路径
        
        Returns:
            str: 保存的文件路径
        """
        try:
            if not os.path.exists(music_id):
                raise FileNotFoundError(f"文件不存在: {music_id}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 读取源文件
            with open(music_id, 'rb') as src:
                audio_data = src.read()
            
            # 写入目标文件
            with open(save_path, 'wb') as dst:
                dst.write(audio_data)
            
            print(f"✓ 已复制到: {save_path}")
            return save_path
        
        except Exception as e:
            print(f"✗ 复制失败: {e}")
            raise
    
    def list_available_music(self) -> list:
        """列出所有可用的本地音乐"""
        if not os.path.exists(self.music_dir):
            return []
        
        results = []
        music_path = Path(self.music_dir)
        pattern = "**/*" if self.recursive else "*"
        
        for file_path in music_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                results.append({
                    'id': str(file_path),
                    'title': file_path.stem,
                    'format': file_path.suffix.lower(),
                    'path': str(file_path)
                })
        
        return results
    
    def __repr__(self):
        return f"LocalFileSource(music_dir={self.music_dir}, recursive={self.recursive})"
