"""
歌曲 Controller
处理歌曲相关的 API 请求
"""

from flask import Blueprint, request, jsonify, send_file, redirect
from services.songs_service import SongsService
from services.file_service import FileService
from utils.aliyun_oss import upload_file, get_oss_url

songs_controller = Blueprint('songs', __name__, url_prefix='/api/songs')


def _serialize_song(song):
    if not song:
        return None
    return {
        'id': song.get('id'),
        'title': song.get('title'),
        'artist_id': song.get('artist_id'),
        'artist_name': song.get('artist_name'),
        'category': song.get('category'),
        'duration': song.get('duration'),
        'source': song.get('source'),
        'source_id': song.get('source_id'),
        'session_id': song.get('session_id'),
        'audio_path': song.get('audio_path'),
        'audio_url': FileService.resolve_public_url(song.get('audio_path')) if song.get('audio_path') else None,
        'melody_path': song.get('melody_path'),
        'melody_url': FileService.resolve_public_url(song.get('melody_path')) if song.get('melody_path') else None,
        'chord_path': song.get('chord_path'),
        'chord_url': FileService.resolve_public_url(song.get('chord_path')) if song.get('chord_path') else None,
        'status': song.get('status'),
        'created_at': song.get('created_at').isoformat() if song.get('created_at') else None,
        'updated_at': song.get('updated_at').isoformat() if song.get('updated_at') else None,
    }


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
        'songs': [_serialize_song(song) for song in songs],
        'total': total
    })


@songs_controller.route('/<int:song_id>', methods=['GET'])
def get_song(song_id):
    """获取单个歌曲"""
    song = SongsService.get_song_by_id(song_id)
    if song:
        return jsonify(_serialize_song(song))
    return jsonify({'error': 'Song not found'}), 404


@songs_controller.route('/add', methods=['POST'])
def add_song():
    """添加歌曲（支持文件上传到 OSS 或引用录音）"""
    # 支持 JSON 或 multipart/form-data
    if request.content_type and 'multipart/form-data' in request.content_type:
        title = request.form.get('title')
        artist_id = request.form.get('artist_id')
        category = request.form.get('category')
        audio_file = request.files.get('audio_file')

        if not title:
            return jsonify({'error': 'title is required'}), 400

        audio_path = None
        # 处理文件上传到 OSS
        if audio_file and audio_file.filename:
            try:
                audio_path = upload_file(audio_file, directory="songs")
            except Exception as e:
                return jsonify({'error': f'OSS upload failed: {str(e)}'}), 500

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
        # JSON 格式：支持 session_id 或 audio_source_id 引用
        data = request.get_json() or {}
        session_id = data.get('session_id')
        audio_source_id = data.get('audio_source_id')

        if bool(session_id) == bool(audio_source_id):
            return jsonify({'error': 'Exactly one of session_id or audio_source_id is required for JSON create mode'}), 400
        
        audio_path = None
        if audio_source_id:
            # 从音源表获取文件路径
            from services.audio_sources_service import AudioSourcesService
            source = AudioSourcesService.get_audio_source(audio_source_id)
            if source:
                if isinstance(source, dict):
                    audio_path = source.get('file_path')
                else:
                    audio_path = source[4]  # file_path 在第5列
                data['source'] = 'recording'
        elif session_id:
            # 兼容旧的 session_id 方式
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
# 文件服务
# ============================================================================

@songs_controller.route("/uploads/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    """兼容层：服务歌曲音频文件。正式消费应直接使用 songs.audio_url。"""
    song = SongsService.get_song_by_id(request.args.get('song_id', type=int)) if request.args.get('song_id') else None
    if song and song.get('audio_path'):
        return redirect(FileService.resolve_public_url(song.get('audio_path')))

    if filename.startswith('http://') or filename.startswith('https://'):
        return redirect(filename)

    audio_path = f"songs/{filename}"
    try:
        local_path = FileService.fetch_local_file(audio_path)
        return send_file(local_path)
    except Exception:
        return jsonify({"error": "File not found"}), 404
