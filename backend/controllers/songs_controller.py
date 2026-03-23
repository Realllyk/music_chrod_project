"""
歌曲 Controller
处理歌曲相关的 API 请求
"""

from flask import Blueprint, request, jsonify
from services.songs_service import SongsService
from services.artists_service import ArtistsService

# 创建 Blueprint
songs_controller = Blueprint('songs', __name__, url_prefix='/api/songs')


# ============================================================================
# 歌曲 API
# ============================================================================

@songs_controller.route('/list', methods=['GET'])
def list_songs():
    """获取歌曲列表"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    songs, total = SongsService.get_songs(limit, offset)
    
    return jsonify({
        'songs': songs,
        'total': total,
        'limit': limit,
        'offset': offset
    })


@songs_controller.route('/<int:song_id>', methods=['GET'])
def get_song(song_id):
    """获取单个歌曲"""
    song = SongsService.get_song_by_id(song_id)
    if song:
        return jsonify(song)
    return jsonify({'error': 'Song not found'}), 404


@songs_controller.route('/add', methods=['POST'])
def add_song():
    """添加歌曲"""
    data = request.get_json() or {}
    
    song_id = SongsService.add_song(data)
    if song_id:
        return jsonify({
            'ok': True,
            'song_id': song_id,
            'message': 'Song added successfully'
        })
    return jsonify({'error': 'Failed to add song'}), 500


@songs_controller.route('/<int:song_id>', methods=['PUT'])
def update_song(song_id):
    """更新歌曲"""
    data = request.get_json() or {}
    
    if SongsService.update_song(song_id, data):
        return jsonify({'ok': True, 'message': 'Song updated'})
    return jsonify({'error': 'Failed to update song'}), 500


@songs_controller.route('/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    """删除歌曲"""
    if SongsService.delete_song(song_id):
        return jsonify({'ok': True, 'message': 'Song deleted'})
    return jsonify({'error': 'Failed to delete song'}), 500


# ============================================================================
# 歌手 API
# ============================================================================

@songs_controller.route('/artists/list', methods=['GET'])
def list_artists():
    """获取歌手列表"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    artists, total = ArtistsService.get_artists(limit, offset)
    
    return jsonify({
        'artists': artists,
        'total': total
    })


@songs_controller.route('/artists/<int:artist_id>', methods=['GET'])
def get_artist(artist_id):
    """获取单个歌手"""
    artist = ArtistsService.get_artist_by_id(artist_id)
    if artist:
        return jsonify(artist)
    return jsonify({'error': 'Artist not found'}), 404


@songs_controller.route('/artists/add', methods=['POST'])
def add_artist():
    """添加歌手"""
    data = request.get_json() or {}
    
    artist_id = ArtistsService.add_artist(data)
    if artist_id:
        return jsonify({
            'ok': True,
            'artist_id': artist_id
        })
    return jsonify({'error': 'Failed to add artist'}), 500


@songs_controller.route('/artists/<int:artist_id>', methods=['PUT'])
def update_artist(artist_id):
    """更新歌手"""
    data = request.get_json() or {}
    
    if ArtistsService.update_artist(artist_id, data):
        return jsonify({'ok': True, 'message': 'Artist updated'})
    return jsonify({'error': 'Failed to update artist'}), 500


@songs_controller.route('/artists/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    """删除歌手"""
    if ArtistsService.delete_artist(artist_id):
        return jsonify({'ok': True, 'message': 'Artist deleted'})
    return jsonify({'error': 'Failed to delete artist'}), 500
