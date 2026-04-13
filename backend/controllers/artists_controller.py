"""
歌手 Controller
处理歌手相关的 API 请求
"""

from flask import Blueprint, request, jsonify
from services.artists_service import ArtistsService

artists_controller = Blueprint('artists', __name__, url_prefix='/api/artists')

# 允许的头像格式
ALLOWED_AVATAR_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


def _save_avatar_to_oss(avatar_file):
    """
    将头像文件上传到 OSS，返回公网 URL
    """
    from utils.aliyun_oss import upload_file

    ext = avatar_file.filename.rsplit('.', 1)[-1].lower() if '.' in avatar_file.filename else ''
    if ext not in ALLOWED_AVATAR_EXTS:
        raise ValueError(f'不支持的图片格式: {ext}')

    avatar_url = upload_file(avatar_file)
    return avatar_url


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
        avatar_url = None

        # 处理头像上传 -> OSS
        if avatar_file and avatar_file.filename:
            try:
                avatar_url = _save_avatar_to_oss(avatar_file)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'OSS upload failed: {e}'}), 500

        if not name:
            return jsonify({'error': 'name is required'}), 400

        artist_id = ArtistsService.add_artist({
            'name': name,
            'bio': bio,
            'avatar': avatar_url
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
        if name:
            data['name'] = name
        if bio:
            data['bio'] = bio

        # 头像上传 -> OSS
        if avatar_file and avatar_file.filename:
            try:
                data['avatar'] = _save_avatar_to_oss(avatar_file)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'OSS upload failed: {e}'}), 500

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
    """更新歌手头像（multipart/form-data，上传到 OSS）"""
    avatar_file = request.files.get('avatar')

    if not avatar_file or not avatar_file.filename:
        return jsonify({'error': 'avatar file is required'}), 400

    try:
        avatar_url = _save_avatar_to_oss(avatar_file)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'OSS upload failed: {e}'}), 500

    if ArtistsService.update_artist(artist_id, {'avatar': avatar_url}):
        return jsonify({'ok': True, 'avatar': avatar_url})
    return jsonify({'error': 'Failed to update avatar'}), 500
