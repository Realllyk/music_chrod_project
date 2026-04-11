"""
歌手 Controller
处理歌手相关的 API 请求
"""

from flask import Blueprint, request, jsonify, send_file
from services.artists_service import ArtistsService

artists_controller = Blueprint('artists', __name__, url_prefix='/api/artists')


# ============================================================================
# 歌手 API
# ============================================================================

@artists_controller.route('/list', methods=['GET'])
def list_artists():
    """获取歌手列表"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    artists, total = ArtistsService.get_artists(limit, offset)
    
    return jsonify({
        'artists': artists,
        'total': total
    })


@artists_controller.route('/<int:artist_id>', methods=['GET'])
def get_artist(artist_id):
    """获取单个歌手"""
    artist = ArtistsService.get_artist_by_id(artist_id)
    if artist:
        return jsonify(artist)
    return jsonify({'error': 'Artist not found'}), 404


@artists_controller.route('/add', methods=['POST'])
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
            avatar_path = f"/api/artists/avatars/{filename}"
        
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


@artists_controller.route('/<int:artist_id>', methods=['PUT'])
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
            data['avatar'] = f"/api/artists/avatars/{filename}"
        
        if data and ArtistsService.update_artist(artist_id, data):
            return jsonify({'ok': True, 'message': 'Artist updated'})
        return jsonify({'error': 'Failed to update artist'}), 500
    else:
        data = request.get_json() or {}
        if ArtistsService.update_artist(artist_id, data):
            return jsonify({'ok': True, 'message': 'Artist updated'})
        return jsonify({'error': 'Failed to update artist'}), 500


@artists_controller.route('/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    """删除歌手"""
    if ArtistsService.delete_artist(artist_id):
        return jsonify({'ok': True, 'message': 'Artist deleted'})
    return jsonify({'error': 'Failed to delete artist'}), 500


# ============================================================================
# 头像 API
# ============================================================================

@artists_controller.route('/<int:artist_id>/avatar', methods=['PUT'])
def update_artist_avatar(artist_id):
    """更新歌手头像（ multipart/form-data）"""
    avatar_file = request.files.get('avatar')
    
    if not avatar_file or not avatar_file.filename:
        return jsonify({'error': 'avatar file is required'}), 400
    
    # 检查文件类型
    ext = avatar_file.filename.rsplit('.', 1)[-1].lower() if '.' in avatar_file.filename else ''
    if ext not in ['jpg', 'jpeg', 'png', 'gif']:
        return jsonify({'error': 'Invalid image format'}), 400
    
    # 保存文件
    import uuid
    from pathlib import Path
    filename = f"avatar_{uuid.uuid4().hex}.{ext}"
    avatar_dir = Path(__file__).parent.parent / 'uploads' / 'avatars'
    avatar_dir.mkdir(parents=True, exist_ok=True)
    file_path = avatar_dir / filename
    avatar_file.save(str(file_path))
    
    # 更新数据库
    avatar_url = f"/api/artists/avatars/{filename}"
    if ArtistsService.update_artist(artist_id, {'avatar': avatar_url}):
        return jsonify({'ok': True, 'avatar': avatar_url})
    return jsonify({'error': 'Failed to update avatar'}), 500


@artists_controller.route('/avatars/<filename>', methods=['GET'])
def serve_avatar(filename):
    """服务头像文件"""
    from pathlib import Path
    avatar_dir = Path(__file__).parent.parent / 'uploads' / 'avatars'
    file_path = avatar_dir / filename
    if file_path.exists():
        return send_file(file_path)
    return jsonify({'error': 'File not found'}), 404
