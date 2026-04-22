"""
歌手 Service
负责歌手业务的逻辑处理
"""

from mappers.artists_mapper import ArtistsMapper
from mappers.songs_mapper import SongsMapper
from pojo.vo.exceptions import BadRequestException, ConflictException, NotFoundException


class ArtistsService:
    """歌手业务逻辑类"""

    @staticmethod
    def add_artist(artist_data):
        """添加歌手"""
        name = (artist_data.get('name') or '').strip()
        if not name:
            raise BadRequestException('name is required')
        if ArtistsMapper.find_by_name(name):
            raise ConflictException('Artist name already exists')
        artist_data['name'] = name
        artist_id = ArtistsMapper.insert(artist_data)
        if not artist_id:
            raise RuntimeError('Failed to add artist')
        return artist_id

    @staticmethod
    def get_artists(limit=100, offset=0):
        """获取歌手列表"""
        return ArtistsMapper.find_all(limit, offset)

    @staticmethod
    def count_artists():
        """获取歌手总数"""
        return ArtistsMapper.count()

    @staticmethod
    def get_artist_by_id(artist_id):
        """根据ID获取歌手"""
        artist = ArtistsMapper.find_by_id(artist_id)
        if not artist:
            raise NotFoundException('Artist not found')
        return artist

    @staticmethod
    def get_artist_by_name(name):
        """根据名字获取歌手"""
        return ArtistsMapper.find_by_name(name)

    @staticmethod
    def update_artist(artist_id, artist_data):
        """更新歌手信息"""
        existing_artist = ArtistsMapper.find_by_id(artist_id)
        if not existing_artist:
            raise NotFoundException('Artist not found')

        name = artist_data.get('name')
        if name is not None:
            name = name.strip()
            if not name:
                raise BadRequestException('name is required')
            existing = ArtistsMapper.find_by_name(name)
            if existing and existing.get('id') != artist_id:
                raise ConflictException('Artist name already exists')
            artist_data['name'] = name

        if not artist_data:
            raise BadRequestException('name 或 bio 至少提供一个')

        if not ArtistsMapper.update(artist_id, artist_data):
            raise RuntimeError('Failed to update artist')
        return ArtistsMapper.find_by_id(artist_id)

    @staticmethod
    def delete_artist(artist_id):
        """删除歌手"""
        existing_artist = ArtistsMapper.find_by_id(artist_id)
        if not existing_artist:
            raise NotFoundException('Artist not found')

        songs, _ = SongsMapper.find_all(limit=10000, offset=0)
        if any(song.get('artist_id') == artist_id for song in songs):
            raise ConflictException('Artist is referenced by songs and cannot be deleted')

        if not ArtistsMapper.delete(artist_id):
            raise RuntimeError('Failed to delete artist')
        return True

    @staticmethod
    def get_or_create(name, avatar=None):
        """获取或创建歌手"""
        artist = ArtistsMapper.find_by_name(name)
        if artist:
            return artist['id']
        return ArtistsMapper.insert({'name': name, 'avatar': avatar})
