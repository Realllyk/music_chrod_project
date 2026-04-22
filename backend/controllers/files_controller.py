"""
文件 Controller
提供 OSS URL 查询等跨模块文件接口
"""

from flask import Blueprint

from pojo.dto import use_dto
from pojo.dto.audio_sources_dto import FileOssUrlQueryDTO
from pojo.vo import Result
from services.file_service import FileService

files_controller = Blueprint('files', __name__, url_prefix='/api/files')


@files_controller.route('/oss-url', methods=['GET'])
@use_dto(FileOssUrlQueryDTO, source='query')
def get_file_oss_url(dto: FileOssUrlQueryDTO):
    """统一返回资源文件的 OSS 访问地址。"""
    results = {}
    requested_type = dto.type

    if dto.song_id:
        from services.songs_service import SongsService
        song = SongsService.get_song_by_id(dto.song_id)
        if not song:
            return Result.not_found('Song not found').to_response()
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

    if dto.session_id:
        from services.capture_service import CaptureService
        session = CaptureService.get_session(dto.session_id)
        if not session:
            return Result.not_found('Session not found').to_response()
        file_path = session.get('file_path')
        if file_path and (not requested_type or requested_type == 'recording'):
            results['recording_path'] = file_path
            results['recording_url'] = FileService.resolve_public_url(file_path)

    if dto.audio_source_id:
        from services.audio_sources_service import AudioSourcesService
        source = AudioSourcesService.get_audio_source(dto.audio_source_id)
        if not source:
            return Result.not_found('Audio source not found').to_response()
        file_path = source.get('file_path') if isinstance(source, dict) else source[4]
        if file_path and (not requested_type or requested_type == 'source'):
            results['source_path'] = file_path
            results['source_url'] = FileService.resolve_public_url(file_path)

    if not results:
        return Result.not_found('No file matched the requested resource/type').to_response()

    return Result.success({
        'resource': 'song' if dto.song_id else ('capture_session' if dto.session_id else 'audio_source'),
        'requested_type': requested_type,
        'data': results,
    }).to_response()
