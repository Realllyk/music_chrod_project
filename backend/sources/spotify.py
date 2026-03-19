"""
Spotify 音乐源实现
"""

import io
import os
import requests
import json
from pathlib import Path
from typing import Optional, Dict, Any
from .base import AudioSource


class SpotifySource(AudioSource):
    """Spotify 音乐源"""
    
    # 从配置文件读取 API 端点
    _CONFIG = None
    
    @classmethod
    def _load_config(cls):
        """加载配置文件"""
        if cls._CONFIG is None:
            config_path = Path(__file__).parent.parent / 'config.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._CONFIG = json.load(f)
        return cls._CONFIG
    
    @property
    def AUTH_URL(self):
        """获取认证 URL 从配置文件"""
        config = self._load_config()
        return config['spotify']['auth_url']
    
    @property
    def API_URL(self):
        """获取 API URL 从配置文件"""
        config = self._load_config()
        return config['spotify']['api_url']
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Spotify 源
        
        config 需要包含：
        {
            'client_id': 'your_client_id',
            'client_secret': 'your_client_secret'
        }
        """
        super().__init__(config)
        self.access_token = None
        self.token_type = "Bearer"
    
    def authenticate(self) -> bool:
        """
        Spotify OAuth 认证
        
        使用 Client Credentials Flow 获取访问令牌
        """
        try:
            if not self.config.get('client_id') or not self.config.get('client_secret'):
                raise ValueError("缺少 Spotify 凭证：client_id 和 client_secret")
            
            # 准备认证请求
            auth = (self.config['client_id'], self.config['client_secret'])
            data = {'grant_type': 'client_credentials'}
            
            # 获取访问令牌
            response = requests.post(self.AUTH_URL, auth=auth, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            self.access_token = result['access_token']
            self.token_type = result.get('token_type', 'Bearer')
            self.is_authenticated = True
            
            print("✓ Spotify 认证成功")
            return True
        
        except Exception as e:
            print(f"✗ Spotify 认证失败: {e}")
            self.is_authenticated = False
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """获取 API 请求头"""
        if not self.access_token:
            raise RuntimeError("未认证，请先调用 authenticate()")
        
        return {
            'Authorization': f'{self.token_type} {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def search(self, query: str, limit: int = 10) -> list:
        """
        搜索 Spotify 上的音乐
        
        Args:
            query: 搜索词（歌曲名、艺术家等）
            limit: 返回结果数
        
        Returns:
            list: 搜索结果，每项包含：
                {
                    'id': str,              # 音乐唯一 ID
                    'title': str,           # 歌曲名
                    'artist': str,          # 艺术家
                    'duration': int,        # 时长（毫秒）
                    'preview_url': str,     # 预览 URL（30秒）
                    'source': 'spotify',    # 来源
                    'url': str              # Spotify 链接
                }
        """
        if not self.is_authenticated:
            raise RuntimeError("未认证")
        
        try:
            config = self._load_config()
            max_limit = config['spotify']['search_limit']
            
            params = {
                'q': query,
                'type': 'track',
                'limit': min(limit, max_limit)
            }
            
            response = requests.get(
                f'{self.API_URL}/search',
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            results = []
            for track in response.json().get('tracks', {}).get('items', []):
                results.append({
                    'id': track['id'],
                    'title': track['name'],
                    'artist': ', '.join([a['name'] for a in track['artists']]),
                    'duration': track['duration_ms'],
                    'preview_url': track.get('preview_url'),
                    'source': 'spotify',
                    'url': track['external_urls'].get('spotify')
                })
            
            return results
        
        except Exception as e:
            print(f"✗ 搜索失败: {e}")
            return []
    
    def get_audio_stream(self, music_id: str) -> io.BytesIO:
        """
        获取音频流
        
        ⚠️ 注意：Spotify API 不提供原始音频文件
        只能获取预览 URL（30 秒片段）
        """
        if not self.is_authenticated:
            raise RuntimeError("未认证")
        
        try:
            # 获取音乐信息
            response = requests.get(
                f'{self.API_URL}/tracks/{music_id}',
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            preview_url = response.json().get('preview_url')
            if not preview_url:
                raise RuntimeError(f"音乐 {music_id} 无预览链接")
            
            # 下载预览音频
            config = self._load_config()
            timeout = config['spotify']['preview_timeout']
            audio_response = requests.get(preview_url, timeout=timeout)
            audio_response.raise_for_status()
            
            return io.BytesIO(audio_response.content)
        
        except Exception as e:
            print(f"✗ 获取音频流失败: {e}")
            raise
    
    def get_audio_file(self, music_id: str, save_path: str) -> str:
        """
        下载音频文件
        
        ⚠️ 注意：Spotify API 限制
        - 只能获取 30 秒预览
        - 需要 Premium 账户获取完整音频（需要用户授权）
        - 这里实现预览版本下载
        """
        try:
            audio_stream = self.get_audio_stream(music_id)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(audio_stream.getvalue())
            
            print(f"✓ 已下载到: {save_path}")
            return save_path
        
        except Exception as e:
            print(f"✗ 下载失败: {e}")
            raise
    
    def __repr__(self):
        return f"SpotifySource(authenticated={self.is_authenticated}, client_id={self.config.get('client_id', 'N/A')[:10]}...)"
