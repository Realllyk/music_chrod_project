"""
WASAPI 录音文件音乐源

专门用于读取从 Windows Agent 采集的 WAV 文件
"""

import io
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from .base import AudioSource


class WavFileSource(AudioSource):
    """
    WASAPI 录音文件源
    
    专门用于读取 agent/recordings/ 目录下的 WAV 文件
    支持自动扫描采集会话文件
    """
    
    SUPPORTED_FORMATS = {'.wav'}
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 WASAPI 录音源
        
        config 可以包含：
        {
            'recordings_dir': '/path/to/agent/recordings',  # 录音目录
            'recursive': True                                 # 是否递归搜索子文件夹
        }
        """
        config = config or {}
        super().__init__(config)
        
        # 默认路径：项目根目录下的 agent/recordings
        default_recordings = Path(__file__).parent.parent.parent / 'agent' / 'recordings'
        
        self.recordings_dir = config.get('recordings_dir', str(default_recordings))
        self.recursive = config.get('recursive', True)
        self.is_authenticated = True  # 本地文件不需要认证
    
    def authenticate(self) -> bool:
        """本地文件不需要认证"""
        return True
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        在录音目录中搜索 WAV 文件
        
        Args:
            query: 搜索词（文件名中的关键词）
            limit: 返回结果数量限制
        
        Returns:
            List[Dict]: 搜索结果列表
        """
        results = []
        query_lower = query.lower()
        
        try:
            recordings_path = Path(self.recordings_dir)
            
            if not recordings_path.exists():
                return results
            
            # 搜索模式
            if self.recursive:
                wav_files = recordings_path.rglob('*.wav')
            else:
                wav_files = recordings_path.glob('*.wav')
            
            for wav_file in wav_files:
                # 检查文件名是否包含搜索词
                if query_lower and query_lower not in wav_file.stem.lower():
                    continue
                
                # 查找对应的 JSON 元数据文件
                json_file = wav_file.with_suffix('.json')
                meta = {}
                if json_file.exists():
                    import json
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                    except:
                        pass
                
                results.append({
                    'id': str(wav_file),
                    'name': wav_file.stem,
                    'file_name': wav_file.name,
                    'file_path': str(wav_file),
                    'title': wav_file.stem,  # 兼容基类接口
                    'duration_sec': meta.get('duration_sec', 0),
                    'duration': int(meta.get('duration_sec', 0) * 1000),  # 毫秒
                    'sample_rate': meta.get('sample_rate', 0),
                    'channels': meta.get('channels', 0),
                    'device_name': meta.get('device_name', ''),
                    'recorded_at': meta.get('start_time', ''),
                    'source': 'wasapi_loopback'
                })
                
                if len(results) >= limit:
                    break
                    
        except Exception as e:
            print(f"搜索 WAV 文件失败: {e}")
        
        return results
    
    def get_audio_stream(self, music_id: str) -> io.BytesIO:
        """
        获取音频流
        
        Args:
            music_id: 文件路径或文件 ID
        
        Returns:
            io.BytesIO: 音频二进制流
        """
        file_path = self.get_audio_path(music_id)
        if not file_path:
            raise FileNotFoundError(f"音频文件不存在: {music_id}")
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        return io.BytesIO(data)
    
    def get_audio_file(self, music_id: str, save_path: str) -> str:
        """
        获取音频文件（本地文件直接返回路径）
        
        Args:
            music_id: 文件路径或文件 ID
            save_path: 保存路径（可选）
        
        Returns:
            str: 文件路径
        """
        file_path = self.get_audio_path(music_id)
        if not file_path:
            raise FileNotFoundError(f"音频文件不存在: {music_id}")
        
        # 本地文件直接返回路径
        if not save_path:
            return file_path
        
        # 如果指定了保存路径，复制文件
        import shutil
        shutil.copy2(file_path, save_path)
        return save_path
    
    def get_audio_path(self, audio_id: str) -> Optional[str]:
        """
        获取音频文件路径
        
        Args:
            audio_id: 文件 ID（通常是完整路径）
        
        Returns:
            str: 音频文件路径，如果不存在返回 None
        """
        if os.path.exists(audio_id):
            return audio_id
        return None
    
    def get_audio_data(self, audio_id: str) -> Optional[bytes]:
        """
        获取音频文件数据
        
        Args:
            audio_id: 文件 ID
        
        Returns:
            bytes: 音频数据，如果不存在返回 None
        """
        file_path = self.get_audio_path(audio_id)
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                print(f"读取音频文件失败: {e}")
        return None
    
    def list_recordings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出所有录音文件
        
        Args:
            limit: 返回数量限制
        
        Returns:
            List[Dict]: 录音列表
        """
        return self.search('', limit=limit)
    
    def get_recording_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        根据会话 ID 获取录音
        
        Args:
            session_id: 会话 ID
        
        Returns:
            Dict: 录音信息，不存在返回 None
        """
        results = self.search(session_id, limit=1)
        return results[0] if results else None


# 注册源名称
WavFileSource.SOURCE_NAME = 'wav_file'
