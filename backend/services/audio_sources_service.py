"""音源 Service"""
from mappers.audio_sources_mapper import AudioSourcesMapper


class AudioSourcesService:
    
    @staticmethod
    def create_audio_source(data):
        """创建音源"""
        return AudioSourcesMapper.insert(data)
    
    @staticmethod
    def get_audio_source(audio_id):
        """获取音源"""
        return AudioSourcesMapper.find_by_id(audio_id)
    
    @staticmethod
    def list_audio_sources(limit=100, offset=0, status='active'):
        """列出音源"""
        return AudioSourcesMapper.find_all(limit, offset, status)
    
    @staticmethod
    def update_audio_source(audio_id, data):
        """更新音源"""
        return AudioSourcesMapper.update(audio_id, data)
    
    @staticmethod
    def delete_audio_source(audio_id):
        """删除音源"""
        return AudioSourcesMapper.delete(audio_id)
    
    @staticmethod
    def create_from_session(session):
        """从会话创建音源"""
        data = {
            'source_type': 'recording',
            'source_id': session.get('session_id'),
            'file_name': session.get('file_name'),
            'file_path': session.get('file_path'),
            'sample_rate': session.get('sample_rate'),
            'channels': session.get('channels'),
            'duration_sec': session.get('duration_sec'),
            'status': 'active'
        }
        
        # 尝试获取文件大小
        if session.get('file_path'):
            import os
            if os.path.exists(session['file_path']):
                data['file_size'] = os.path.getsize(session['file_path'])
        
        # 提取格式
        if session.get('file_name'):
            ext = session['file_name'].split('.')[-1].lower()
            data['format'] = ext
        
        return AudioSourcesMapper.insert(data)
