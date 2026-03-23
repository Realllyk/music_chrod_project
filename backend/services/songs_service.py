"""
歌曲 Service
负责歌曲业务的逻辑处理
"""

from mappers.songs_mapper import SongsMapper
from database import DatabaseConnection


class SongsService:
    """歌曲业务逻辑类"""
    
    @staticmethod
    def add_song(song_data):
        """添加歌曲"""
        return SongsMapper.insert(song_data)
    
    @staticmethod
    def get_songs(limit=100, offset=0):
        """获取歌曲列表"""
        return SongsMapper.find_all(limit, offset)
    
    @staticmethod
    def get_song_by_id(song_id):
        """根据ID获取歌曲"""
        return SongsMapper.find_by_id(song_id)
    
    @staticmethod
    def get_song_by_session(session_id):
        """根据会话ID获取歌曲"""
        return SongsMapper.find_by_session_id(session_id)
    
    @staticmethod
    def update_song(song_id, song_data):
        """更新歌曲信息"""
        return SongsMapper.update(song_id, song_data)
    
    @staticmethod
    def delete_song(song_id):
        """删除歌曲"""
        return SongsMapper.delete(song_id)
    
    @staticmethod
    def create_song_from_session(session_data, midi_path=None):
        """从采集会话创建歌曲记录"""
        song_data = {
            'title': session_data.get('file_name', '未命名'),
            'source': 'wasapi_loopback',
            'source_id': session_data.get('session_id'),
            'audio_path': session_data.get('file_path'),
            'midi_path': midi_path,
            'duration': int(session_data.get('duration_sec', 0) * 1000),
            'status': 'completed' if midi_path else 'pending',
            'session_id': session_data.get('session_id')
        }
        return SongsMapper.insert(song_data)
