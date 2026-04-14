"""音源 Service"""
from mappers.audio_sources_mapper import AudioSourcesMapper
from mappers.songs_mapper import SongsMapper
from utils.aliyun_oss import delete_file


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
    def list_audio_sources(limit=100, offset=0):
        """列出音源（不按状态过滤）"""
        return AudioSourcesMapper.find_all(limit, offset)
    
    @staticmethod
    def update_audio_source(audio_id, data):
        """更新音源"""
        return AudioSourcesMapper.update(audio_id, data)
    
    @staticmethod
    def delete_audio_source(audio_id):
        """删除音源"""
        source = AudioSourcesMapper.find_by_id(audio_id)
        if not source:
            return False, 'Audio source not found'

        source_path = source.get('file_path') if isinstance(source, dict) else source[4]

        songs, _ = SongsMapper.find_all(limit=10000, offset=0)
        referenced = [song for song in songs if song.get('audio_path') == source_path]
        if referenced:
            return False, 'Audio source is referenced by songs and cannot be deleted'

        delete_file(source_path)

        return AudioSourcesMapper.delete(audio_id), None
    
    @staticmethod
    def create_from_session(session):
        """从会话创建音源"""
        data = {
            'source_type': 'recording',
            'source_id': session.get('session_id'),
            'audio_name': session.get('audio_name'),
            'file_path': session.get('file_path'),
            'sample_rate': session.get('sample_rate'),
            'channels': session.get('channels'),
            'duration_sec': session.get('duration_sec'),
            'status': 'active'
        }
        
        # 不再依赖本地路径计算 OSS 文件大小；上传后由调用方或异步元数据解析补全
        if session.get('file_size') is not None:
            data['file_size'] = session.get('file_size')
        
        # 提取格式
        if session.get('audio_name'):
            ext = session['audio_name'].split('.')[-1].lower()
            data['format'] = ext
        
        return AudioSourcesMapper.insert(data)
