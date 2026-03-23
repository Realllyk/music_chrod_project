"""
歌手 Service
负责歌手业务的逻辑处理
"""

from mappers.artists_mapper import ArtistsMapper


class ArtistsService:
    """歌手业务逻辑类"""
    
    @staticmethod
    def add_artist(artist_data):
        """添加歌手"""
        return ArtistsMapper.insert(artist_data)
    
    @staticmethod
    def get_artists(limit=100, offset=0):
        """获取歌手列表"""
        return ArtistsMapper.find_all(limit, offset)
    
    @staticmethod
    def get_artist_by_id(artist_id):
        """根据ID获取歌手"""
        return ArtistsMapper.find_by_id(artist_id)
    
    @staticmethod
    def get_artist_by_name(name):
        """根据名字获取歌手"""
        return ArtistsMapper.find_by_name(name)
    
    @staticmethod
    def update_artist(artist_id, artist_data):
        """更新歌手信息"""
        return ArtistsMapper.update(artist_id, artist_data)
    
    @staticmethod
    def delete_artist(artist_id):
        """删除歌手"""
        return ArtistsMapper.delete(artist_id)
    
    @staticmethod
    def get_or_create(name, avatar=None):
        """获取或创建歌手"""
        artist = ArtistsMapper.find_by_name(name)
        if artist:
            return artist['id']
        return ArtistsMapper.insert({'name': name, 'avatar': avatar})
