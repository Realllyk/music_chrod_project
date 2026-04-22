"""音源 Controller"""

from flask import Blueprint, jsonify

from pojo.dto import use_dto
from pojo.dto.audio_sources_dto import AudioSourceIdPathDTO, ListAudioSourcesQueryDTO, UploadAudioSourceDTO
from pojo.vo import PageVO, Result
from pojo.vo.audio_sources_vo import AudioSourceVO
from services.audio_sources_service import AudioSourcesService
from utils.aliyun_oss import list_files, upload_file

audio_sources_controller = Blueprint('audio_sources', __name__, url_prefix='/api/audio-sources')


@audio_sources_controller.route('/list', methods=['GET'])
@use_dto(ListAudioSourcesQueryDTO, source='query')
def list_audio_sources(dto: ListAudioSourcesQueryDTO):
    sources, total = AudioSourcesService.list_audio_sources(dto.limit, dto.offset)
    items = [AudioSourceVO.from_domain(source) for source in sources]
    return jsonify(PageVO(items=items, total=total, limit=dto.limit, offset=dto.offset).model_dump(mode='json'))


@audio_sources_controller.route('/count', methods=['GET'])
def get_audio_sources_count():
    count = AudioSourcesService.count_audio_sources()
    return Result.success({'total': count}).to_response()


@audio_sources_controller.route('/oss-files', methods=['GET'])
def list_oss_audio_files():
    files = list_files('audio-sources/')
    return jsonify({'items': files, 'total': len(files)})


@audio_sources_controller.route('/<int:audio_id>', methods=['GET'])
@use_dto(AudioSourceIdPathDTO, source='path')
def get_audio_source(dto: AudioSourceIdPathDTO):
    source = AudioSourcesService.get_audio_source(dto.audio_id)
    if not source:
        return Result.not_found('Audio source not found').to_response()
    return jsonify(AudioSourceVO.from_domain(source).model_dump(mode='json'))


@audio_sources_controller.route('/<int:audio_id>', methods=['DELETE'])
@use_dto(AudioSourceIdPathDTO, source='path')
def delete_audio_source(dto: AudioSourceIdPathDTO):
    success, error = AudioSourcesService.delete_audio_source(dto.audio_id)
    if not success:
        if error == 'Audio source not found':
            return Result.not_found(error).to_response()
        return Result.bad_request(error or 'Delete failed').to_response()
    return Result.success({'ok': True}).to_response()


@audio_sources_controller.route('/upload', methods=['POST'])
@use_dto(UploadAudioSourceDTO, source='form')
def upload_audio_source(dto: UploadAudioSourceDTO):
    audio_file = dto.audio_file
    file_url = upload_file(audio_file, 'audio-sources')
    file_size = getattr(audio_file, 'content_length', None) or 0
    ext = audio_file.filename.rsplit('.', 1)[-1].lower() if '.' in audio_file.filename else 'wav'

    source_data = {
        'source_type': 'upload',
        'audio_name': dto.audio_name,
        'file_path': file_url,
        'file_size': file_size,
        'format': ext,
        'status': 'active',
    }
    source_id = AudioSourcesService.create_audio_source(source_data)

    return jsonify({
        'ok': True,
        'audio_source_id': source_id,
        'audio_name': dto.audio_name,
        'file_path': file_url,
        'format': ext,
    })
