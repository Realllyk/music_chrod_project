"""
歌曲 Controller
处理歌曲相关的 API 请求
"""

from flask import Blueprint, request, jsonify, send_file
from services.songs_service import SongsService
from services.artists_service import ArtistsService

# 创建 Blueprint
songs_controller = Blueprint('songs', __name__, url_prefix='/api/songs')


# ============================================================================
# 歌曲 API
# ============================================================================

@songs_controller.route('/list', methods=['GET'])
def list_songs():
    """获取歌曲列表（支持关键词搜索）"""
    keyword = request.args.get('keyword', '')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    if keyword:
        songs, total = SongsService.search_songs(keyword, limit, offset)
    else:
        songs, total = SongsService.get_songs(limit, offset)
    
    return jsonify({
        'songs': songs,
        'total': total
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
    """添加歌曲（支持文件上传或引用录音）"""
    # 支持 JSON 或 multipart/form-data
    if request.content_type and 'multipart/form-data' in request.content_type:
        title = request.form.get('title')
        artist_id = request.form.get('artist_id')
        category = request.form.get('category')
        audio_file = request.files.get('audio_file')
        
        if not title:
            return jsonify({'error': 'title is required'}), 400
        
        audio_path = None
        # 处理文件上传
        if audio_file and audio_file.filename:
            import uuid
            from pathlib import Path
            ext = Path(audio_file.filename).suffix.lower()
            filename = f"audio_{uuid.uuid4().hex}{ext}"
            audio_dir = Path(__file__).parent.parent / 'uploads' / 'audio'
            audio_dir.mkdir(parents=True, exist_ok=True)
            file_path = audio_dir / filename
            audio_file.save(str(file_path))
            audio_path = f"/api/uploads/audio/{filename}"
        
        song_data = {
            'title': title,
            'artist_id': int(artist_id) if artist_id else None,
            'category': category,
            'audio_path': audio_path,
            'source': 'local_mp3' if audio_path else 'manual',
            'status': 'ready'
        }
        
        song_id = SongsService.add_song(song_data)
        if song_id:
            return jsonify({'ok': True, 'song_id': song_id, 'audio_path': audio_path})
        return jsonify({'error': 'Failed to add song'}), 500
    else:
        # JSON 格式：支持 session_id 引用
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        audio_path = None
        if session_id:
            # 从录音会话获取文件路径
            from services.capture_service import CaptureService
            session = CaptureService.get_session(session_id)
            if session:
                audio_path = session.get('file_path')
                data['source'] = 'wasapi_loopback'
        
        if audio_path:
            data['audio_path'] = audio_path
            data['status'] = 'ready'
        
        song_id = SongsService.add_song(data)
        if song_id:
            return jsonify({'ok': True, 'song_id': song_id, 'audio_path': audio_path})
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
    """添加歌手（支持文件上传）"""
    # 支持 JSON 或 multipart/form-data
    if request.content_type and 'multipart/form-data' in request.content_type:
        name = request.form.get('name')
        bio = request.form.get('bio')
        avatar_file = request.files.get('avatar')
        avatar_path = None
        
        # 处理头像上传
        if avatar_file and avatar_file.filename:
            import uuid
            from pathlib import Path
            ext = Path(avatar_file.filename).suffix.lower()
            filename = f"avatar_{uuid.uuid4().hex}{ext}"
            avatar_dir = Path(__file__).parent.parent / 'uploads' / 'avatars'
            avatar_dir.mkdir(parents=True, exist_ok=True)
            file_path = avatar_dir / filename
            avatar_file.save(str(file_path))
            avatar_path = f"/api/uploads/avatars/{filename}"
        
        if not name:
            return jsonify({'error': 'name is required'}), 400
        
        artist_id = ArtistsService.add_artist({
            'name': name,
            'bio': bio,
            'avatar': avatar_path
        })
        if artist_id:
            return jsonify({'ok': True, 'artist_id': artist_id})
        return jsonify({'error': 'Failed to add artist'}), 500
    else:
        data = request.get_json() or {}
        artist_id = ArtistsService.add_artist(data)
        if artist_id:
            return jsonify({'ok': True, 'artist_id': artist_id})
        return jsonify({'error': 'Failed to add artist'}), 500


@songs_controller.route('/artists/<int:artist_id>', methods=['PUT'])
def update_artist(artist_id):
    """更新歌手（支持文件上传）"""
    if request.content_type and 'multipart/form-data' in request.content_type:
        name = request.form.get('name')
        bio = request.form.get('bio')
        avatar_file = request.files.get('avatar')
        
        data = {}
        if name: data['name'] = name
        if bio: data['bio'] = bio
        
        if avatar_file and avatar_file.filename:
            import uuid
            from pathlib import Path
            ext = Path(avatar_file.filename).suffix.lower()
            filename = f"avatar_{uuid.uuid4().hex}{ext}"
            avatar_dir = Path(__file__).parent.parent / 'uploads' / 'avatars'
            avatar_dir.mkdir(parents=True, exist_ok=True)
            file_path = avatar_dir / filename
            avatar_file.save(str(file_path))
            data['avatar'] = f"/api/uploads/avatars/{filename}"
        
        if data and ArtistsService.update_artist(artist_id, data):
            return jsonify({'ok': True, 'message': 'Artist updated'})
        return jsonify({'error': 'Failed to update artist'}), 500
    else:
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


# ============================================================================
# 文件服务
# ============================================================================

@songs_controller.route("/uploads/avatars/<filename>", methods=["GET"])
def serve_avatar(filename):
    """服务头像文件"""
    from pathlib import Path
    avatar_dir = Path(__file__).parent.parent / "uploads" / "avatars"
    file_path = avatar_dir / filename
    if file_path.exists():
        return send_file(file_path)
    return jsonify({"error": "File not found"}), 404


@songs_controller.route("/uploads/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    """服务音频文件"""
    from pathlib import Path
    audio_dir = Path(__file__).parent.parent / "uploads" / "audio"
    file_path = audio_dir / filename
    if file_path.exists():
        return send_file(file_path)
    return jsonify({"error": "File not found"}), 404
