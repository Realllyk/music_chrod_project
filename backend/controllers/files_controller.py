"""
文件 Controller
提供 OSS URL 查询等跨模块文件接口
"""

from flask import Blueprint, request, jsonify
from services.file_service import FileService

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

    requested_type = (file_type or '').strip().lower()
    allowed_types = {'audio', 'melody', 'chord', 'recording', 'source'}
    if requested_type and requested_type not in allowed_types:
        return jsonify({'error': 'type must be one of audio, melody, chord, recording, source'}), 400

    id_params = [value for value in [song_id, session_id, audio_source_id] if value]
    if len(id_params) != 1:
        return jsonify({'error': 'Exactly one of song_id, session_id, audio_source_id is required'}), 400

    results = {}

    if song_id:
        from services.songs_service import SongsService
        song = SongsService.get_song_by_id(song_id)
        if song:
            audio_path = song.get('audio_path')
            if audio_path and (not requested_type or requested_type == 'audio'):
                results['audio_path'] = audio_path
                results['audio_url'] = FileService.resolve_public_url(audio_path)
            melody_path = song.get('melody_path')
            if melody_path and (not requested_type or requested_type == 'melody'):
                results['melody_path'] = melody_path
                results['melody_url'] = FileService.resolve_public_url(melody_path)
            chord_path = song.get('chord_path')
            if chord_path and (not requested_type or requested_type == 'chord'):
                results['chord_path'] = chord_path
                results['chord_url'] = FileService.resolve_public_url(chord_path)
        else:
            return jsonify({'error': 'Song not found'}), 404

    if session_id:
        from services.capture_service import CaptureService
        session = CaptureService.get_session(session_id)
        if session:
            file_path = session.get('file_path')
            if file_path and (not requested_type or requested_type == 'recording'):
                results['recording_path'] = file_path
                results['recording_url'] = FileService.resolve_public_url(file_path)
        else:
            return jsonify({'error': 'Session not found'}), 404

    if audio_source_id:
        from services.audio_sources_service import AudioSourcesService
        source = AudioSourcesService.get_audio_source(audio_source_id)
        if source:
            file_path = source.get('file_path') if isinstance(source, dict) else source[4]
            if file_path and (not requested_type or requested_type == 'source'):
                results['source_path'] = file_path
                results['source_url'] = FileService.resolve_public_url(file_path)
        else:
            return jsonify({'error': 'Audio source not found'}), 404

    if not results:
        return jsonify({'error': 'No file matched the requested resource/type'}), 404

    return jsonify({
        'resource': 'song' if song_id else ('capture_session' if session_id else 'audio_source'),
        'requested_type': requested_type or None,
        'data': results
    })
