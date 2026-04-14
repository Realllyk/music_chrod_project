"""
文件 Controller
提供 OSS URL 查询等跨模块文件接口
"""

from flask import Blueprint, request, jsonify
from utils.aliyun_oss import get_oss_url, list_files

files_controller = Blueprint('files', __name__, url_prefix='/api/files')


@files_controller.route('/oss-url', methods=['GET'])
def get_file_oss_url():
    """
    GET /api/files/oss-url
    根据 song_id / session_id / audio_source_id 查询对应文件的 OSS URL

    Query params:
        song_id: 歌曲ID，查询 songs.audio_path
        session_id: 采集会话ID，查询 capture_sessions.file_path
        audio_source_id: 音源ID，查询 audio_sources.file_path
    """
    song_id = request.args.get('song_id', type=int)
    session_id = request.args.get('session_id')
    audio_source_id = request.args.get('audio_source_id', type=int)
    file_type = request.args.get('type')  # melody, chord, audio, recording

    results = {}

    if song_id:
        from services.songs_service import SongsService
        song = SongsService.get_song_by_id(song_id)
        if song:
            audio_path = song.get('audio_path')
            if audio_path:
                results['audio_path'] = audio_path
                results['audio_url'] = audio_path if audio_path.startswith('http') else get_oss_url(audio_path)
            melody_path = song.get('melody_path')
            if melody_path:
                results['melody_path'] = melody_path
                results['melody_url'] = get_oss_url(melody_path) if not melody_path.startswith('http') else melody_path
            chord_path = song.get('chord_path')
            if chord_path:
                results['chord_path'] = chord_path
                results['chord_url'] = get_oss_url(chord_path) if not chord_path.startswith('http') else chord_path
        else:
            return jsonify({'error': 'Song not found'}), 404

    if session_id:
        from services.capture_service import CaptureService
        session = CaptureService.get_session(session_id)
        if session:
            file_path = session.get('file_path')
            if file_path:
                results['recording_path'] = file_path
                results['recording_url'] = file_path if file_path.startswith('http') else get_oss_url(file_path)
        else:
            return jsonify({'error': 'Session not found'}), 404

    if audio_source_id:
        from services.audio_sources_service import AudioSourcesService
        source = AudioSourcesService.get_audio_source(audio_source_id)
        if source:
            file_path = source.get('file_path') if isinstance(source, dict) else source[4]
            if file_path:
                results['source_path'] = file_path
                results['source_url'] = file_path if file_path.startswith('http') else get_oss_url(file_path)
        else:
            return jsonify({'error': 'Audio source not found'}), 404

    if not results:
        return jsonify({'error': 'At least one id parameter is required'}), 400

    return jsonify(results)
